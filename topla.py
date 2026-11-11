#!/usr/bin/env python3
"""TFF arsivinden lig maclarini toplar.

  python3 topla.py indir --deneme   # birkac sayfalik deneme
  python3 topla.py indir            # tum arsiv (yarim kalirsa kaldigi yerden surer)
  python3 topla.py kur              # raw/ klasorunden futbol.db dosyasini kurar

Yalnizca Python standart kutuphanesi ve curl kullanir.
"""
import argparse, collections, glob, html, os, re, sqlite3, subprocess, sys, time

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "tff")
UA = "turk-futbol-db/0.1 (kisisel arsiv)"
BEKLE = 2.0
TAB = "https://www.tff.org/Default.aspx"
ARSIV = {  # kaynak: arsiv sayfasi dosyasi
    "superlig": "tff_arsiv_superlig.html",
    "1lig": "tff_arsiv_1lig.html",
    "2lig": "tff_arsiv_2lig_a.html",
    "3lig": "tff_arsiv_3lig.html",
}
AYLAR = {a: i + 1 for i, a in enumerate(
    "Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık".split())}


def oku(yol):
    with open(yol, "rb") as f:
        return f.read().decode("cp1254", "replace")


def temiz(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def kademe(kaynak, yil):
    if kaynak == "superlig":
        return 1
    if kaynak == "1lig":
        return 2
    if kaynak == "2lig":
        return 2 if yil < 2001 else 3
    return 3 if yil < 2001 else 4


def sezonlar():
    """Arsiv sayfalarindan (kaynak, baslangic yili, etiket, pageID) listesi."""
    out = []
    for kaynak, dosya in ARSIV.items():
        t = oku(os.path.join(KOK, "raw", "pilot", dosya))
        gorulen = set()
        for pid, ic in re.findall(r'<a\b[^>]*href="[^"]*pageI[Dd]=(\d+)[^"]*"[^>]*>(.*?)</a>', t, re.I | re.S):
            ad = temiz(ic)
            if re.search(r"UEFA|Dünya|EURO", ad):
                continue
            m = re.fullmatch(r"(?:.*?)((?:19|20)\d\d)\s*[-/–]\s*((?:19|20)\d\d|\d\d)\b.*", ad)
            if m:
                bas, bit = int(m.group(1)), m.group(2)
                etiket = f"{bas}-{bit if len(bit) == 4 else str(bas)[:2] + bit}"
            elif ad == "1959":
                bas, etiket = 1959, "1959"
            else:
                continue
            if pid in gorulen:
                continue
            gorulen.add(pid)
            out.append((kaynak, bas, etiket, pid))
    return out


class Indirici:
    def __init__(self):
        self.ardisik_hata = 0
        self.indirilen = 0

    def al(self, url, yol):
        if os.path.exists(yol) and os.path.getsize(yol) > 5000:
            return oku(yol)
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        gecici = yol + ".tmp"
        r = subprocess.run(["curl", "-sL", "-m", "60", "-A", UA, "-o", gecici, "-w", "%{http_code}", url],
                           capture_output=True, text=True)
        time.sleep(BEKLE)
        kod = r.stdout.strip()
        if kod != "200" or not os.path.exists(gecici) or os.path.getsize(gecici) <= 5000:
            self.ardisik_hata += 1
            with open(os.path.join(KOK, "hatalar.log"), "a") as f:
                f.write(f"{time.strftime('%F %T')} {kod} {url}\n")
            if os.path.exists(gecici):
                os.remove(gecici)
            if self.ardisik_hata >= 10:
                sys.exit("Art arda 10 hata alindi, duruyorum. Ayrinti: hatalar.log")
            return None
        self.ardisik_hata = 0
        self.indirilen += 1
        os.replace(gecici, yol)
        return oku(yol)


def gruplar(t):
    return collections.OrderedDict(
        (g, temiz(ad)) for g, ad in re.findall(r'<a href="Default\.aspx\?pageID=\d+&(?:amp;)?grupID=(\d+)[^"]*"[^>]*_gl">(.*?)</a>', t, re.S))


def ana_yukselme(t):
    """2007-08..2009-10 2. Lig: Yukselme Grubu'nun kendi grup kodu yok, sezonun ana sayfasi (grupID'siz) odur;
    grup listesinde yalnizca klasman ve ilk asama gruplari gorunur."""
    x = temiz(re.sub(r"(?s)<script.*?</script>", "", t))
    return bool(re.search(r"(?i)yükselme grubu\s+(?:genel iç saha dış saha\s+)?1\. devre", x))


def grup_tam_ad(kod):
    """TFF'nin grup baglantilarindaki kisaltmalar: F = Yukselme Grubu, K1 = 1. Klasman Grubu."""
    if kod == "F":
        return "Yükselme Grubu"
    m = re.fullmatch(r"K(\d+)", kod)
    return f"{m.group(1)}. Klasman Grubu" if m else kod


def haftalar(t):
    return sorted({int(h) for h in re.findall(r"<a href=Default\.aspx\?[^ >]*hafta=(\d+)", t)}
                  | {int(h) for h in re.findall(r'class=haftaNo\w+><a href="?Default\.aspx\?[^ >"]*hafta=(\d+)', t)})


def sezon_indir(d, kaynak, etiket, pid, deneme=False):
    """Bir sezonun giris, grup ve hafta sayfalarini raw/tff/<kaynak>_<etiket>_<pid>/ altina indirir (var olani atlar)."""
    klasor = os.path.join(HAM, f"{kaynak}_{etiket}_{pid}")
    t = d.al(f"{TAB}?pageID={pid}", os.path.join(klasor, "giris.html"))
    if t is None:
        return
    if not gruplar(t) and not haftalar(t) and not maclar(t):
        # Bazi eski sezonlarin arsiv sayfasi yalnizca taranmis puan tablosu resmi iceriyor (orn. Super Lig 1959, 1975-76)
        resim = re.search(r'src="([^"]*Arsiv[^"]*\.(?:jpe?g|png|gif))"', t, re.I)
        satir = f"{kaynak}\t{etiket}\tpageID={pid}\t{resim.group(1) if resim else '-'}\n"
        yol = os.path.join(HAM, "veri_yok.txt")
        if not (os.path.exists(yol) and satir in open(yol, encoding="utf-8").read()):
            with open(yol, "a", encoding="utf-8") as f:
                f.write(satir)
        print(f"{kaynak} {etiket}: mac verisi yok (yalnizca resim) -> veri_yok.txt", flush=True)
        return
    g = gruplar(t) or {"": ""}
    if gruplar(t) and ana_yukselme(t):
        g = {"": "Yükselme Grubu", **g}   # ana sayfanin haftalari da indirilsin
    print(f"{kaynak} {etiket}: {len(g)} grup", flush=True)
    for gid in (list(g)[:2] if deneme else g):
        ek = f"&grupID={gid}" if gid else ""
        gt = t if not gid else d.al(f"{TAB}?pageID={pid}{ek}", os.path.join(klasor, f"g{gid}.html"))
        if gt is None:
            continue
        hs = haftalar(gt) or [0]
        for h in (hs[:2] if deneme else hs):
            if h:
                d.al(f"{TAB}?pageID={pid}{ek}&hafta={h}", os.path.join(klasor, f"g{gid}_h{h}.html"))


def indir(deneme):
    d = Indirici()
    liste = sezonlar()
    print(f"{len(liste)} sezon bulundu")
    if deneme:
        secilen = {("superlig", "1959"), ("superlig", "1975-1976"), ("3lig", "1990-1991"), ("2lig", "1990-1991")}
        liste = [s for s in liste if (s[0], s[2]) in secilen]
    for kaynak, yil, etiket, pid in liste:
        sezon_indir(d, kaynak, etiket, pid, deneme)
    print(f"Bitti, yeni indirilen sayfa: {d.indirilen}")


def tarih(s):
    s = s.strip()
    m = re.fullmatch(r"(\d\d)\.(\d\d)\.(\d{4})", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = re.fullmatch(r"(\d{1,2}) (\w+) (\d{4})(?: \d\d:\d\d)?", s)
    if m and m.group(2) in AYLAR:
        return f"{m.group(3)}-{AYLAR[m.group(2)]:02d}-{int(m.group(1)):02d}"
    return s or None


def saat_bul(s):
    x = re.search(r"\d\d:\d\d", s)
    return x.group(0) if x else None


def maclar(t):
    """Sayfadaki mac satirlari: kupaMaclari denetimlerinden okunur."""
    sonuc = []
    modul_po = {}
    for m in re.finditer(r'id="((ctl00_MPane_m_\d+_\d+)_ctnr_[^"]*?kupaMaclari_ctl\d+)_lblTakim1"', t):
        on, modul = m.group(1), m.group(2)
        def al(ek):
            x = re.search(r'id="%s_%s"[^>]*>(.*?)</(?:span|a)>' % (re.escape(on), ek), t, re.S)
            return temiz(x.group(1)) if x else ""
        def kulup(ek):
            x = re.search(r'id="%s_%s"[^>]*href="[^"]*kulupI[Dd]=(\d+)' % (re.escape(on), ek), t, re.I)
            return x.group(1) if x else None
        sk = re.search(r'id="%s_lblSkor"[^>]*href="[^"]*macI[Dd]=(\d+)[^"]*"[^>]*>(.*?)</a>' % re.escape(on), t, re.S | re.I)
        if not sk:
            continue
        if modul not in modul_po:
            modul_po[modul] = bool(re.search(r"Play-?\s?Off", temiz(t[max(0, m.start() - 2500):m.start()]), re.I))
        po = modul_po[modul]
        once = temiz(t[max(0, m.start() - 1500):m.start()])
        tur = re.findall(r"((?:Yarı |Çeyrek )?[\w\.]+ Maçları)", once) if po else []
        sonuc.append(dict(mac=sk.group(1), skor=temiz(sk.group(2)), tarih=tarih(al("lblTarih")), saat=al("lbSaat") or saat_bul(al("lblTarih")),
                          ev=al("lblTakim1"), dep=al("lblTakim2"), ev_id=kulup("lblTakim1"), dep_id=kulup("lblTakim2"),
                          pen=al("lblSkor90Sonrasi"), po=po, tur=tur[-1].strip() if tur else None))
    # Super Lig sayfalari farkli duzen: "Haftanin Maclari" (dtlHaftaninMaclari) denetimleri
    for m in re.finditer(r'id="([^"]*dtlHaftaninMaclari_ctl\d+)_A3"', t):
        on = re.escape(m.group(1))
        def ht(ek):
            x = re.search(r'id="%s_%s"[^>]*>(.*?)</span>' % (on, ek), t, re.S)
            return temiz(x.group(1)) if x else ""
        def hk(ek):
            x = re.search(r'href="[^"]*kulupI[Dd]=(\d+)"[^>]*id="%s_%s"' % (on, ek), t, re.I)
            return x.group(1) if x else None
        mid = re.search(r'href="[^"]*macI[Dd]=(\d+)"[^>]*id="%s_A3"' % on, t, re.I)
        g1, g2 = ht("Label5"), ht("Label6")
        sonuc.append(dict(mac=mid.group(1) if mid else None, skor=f"{g1} - {g2}" if g1 != "" and g2 != "" else "",
                          tarih=tarih(ht("lblTarih")), saat=ht("lblSaat"), ev=ht("Label4"), dep=ht("Label1"),
                          ev_id=hk("A2"), dep_id=hk("A5"), pen="", po=False, tur=None))
    return sonuc


SEMA = """
CREATE TABLE kulup(id INTEGER PRIMARY KEY, tff_id TEXT UNIQUE, ad TEXT);
CREATE TABLE kulup_adi(kulup_id INTEGER, ad TEXT, ilk_sezon TEXT, son_sezon TEXT, mac_sayisi INTEGER, PRIMARY KEY(kulup_id, ad));
CREATE TABLE mac(id INTEGER PRIMARY KEY, kaynak TEXT, kaynak_id TEXT, kademe INTEGER, lig TEXT, sezon TEXT,
  grup TEXT, asama TEXT, hafta INTEGER, tarih TEXT, saat TEXT, ev_id INTEGER, dep_id INTEGER, ev_adi TEXT, dep_adi TEXT,
  ev_gol INTEGER, dep_gol INTEGER, ev_pen INTEGER, dep_pen INTEGER, ham_skor TEXT, UNIQUE(kaynak, kaynak_id));
CREATE TABLE kapsam(kademe INTEGER, sezon TEXT, grup TEXT, takim INTEGER, bulunan INTEGER, beklenen INTEGER);
CREATE TABLE puan(kademe INTEGER, lig TEXT, sezon TEXT, grup TEXT, sira INTEGER, tff_id TEXT, ad TEXT,
  O INTEGER, G INTEGER, B INTEGER, M INTEGER, A INTEGER, Y INTEGER, AV INTEGER, P INTEGER, sayfa TEXT);
CREATE INDEX i1 ON mac(ev_id); CREATE INDEX i2 ON mac(dep_id); CREATE INDEX i3 ON mac(sezon, kademe);
CREATE VIEW takim_maci AS
  SELECT m.id mac_id, m.kademe, m.lig, m.sezon, m.grup, m.asama, m.hafta, m.tarih, m.ev_id kulup_id, m.ev_adi takim, m.dep_id rakip_id, m.dep_adi rakip,
         'ev' saha, m.ev_gol attigi, m.dep_gol yedigi, m.ev_gol-m.dep_gol fark, m.ham_skor FROM mac m WHERE m.ev_gol IS NOT NULL
  UNION ALL
  SELECT m.id, m.kademe, m.lig, m.sezon, m.grup, m.asama, m.hafta, m.tarih, m.dep_id, m.dep_adi, m.ev_id, m.ev_adi,
         'deplasman', m.dep_gol, m.ev_gol, m.dep_gol-m.ev_gol, m.ham_skor FROM mac m WHERE m.ev_gol IS NOT NULL;
"""
LIG = {"superlig": "Süper Lig", "1lig": "1. Lig", "2lig": "2. Lig", "3lig": "3. Lig"}


def puan_tablosu(t):
    """Grup/sezon sayfasindaki resmi puan durumu (ilk tablo = genel; ardindan ic saha ve dis saha tablolari gelir)."""
    satirlar = []
    for blok in re.findall(r'grvACetvel_ctl\d+_lnkTakim"[^>]*?(?:kulupID=(\d+))?"?>(.*?)</a>(.*?)(?=grvACetvel_ctl\d+_lnkTakim|</table>)', t, re.S):
        kid, ad, geri = blok
        m = re.match(r"\s*(\d+)\.\s*(.*)", temiz(ad))
        if not m:
            continue
        sira = int(m.group(1))
        if satirlar and sira <= satirlar[-1]["sira"]:
            break   # ic saha tablosu basladi
        say = [int(x) if re.fullmatch(r"-?\d+", x) else None for x in
               re.findall(r'_(?:lblOyun|Label4|lblKazanma|lblPuan|Label1|Label2|Label5|Label3)">\s*(-?\d*)\s*<', geri)]
        if len(say) < 8:
            continue
        satirlar.append(dict(sira=sira, tff_id=kid or None, ad=m.group(2).strip(), O=say[0], G=say[1], B=say[2], M=say[3],
                             A=say[4], Y=say[5], AV=say[6], P=say[7]))
    return satirlar


def kur(db, ham, sadece=None):
    """Butun ham sayfalardan tff.db'yi kurar. sadece=[klasor adlari] verilirse mevcut veritabaninda yalniz o
    sezonlari siler ve yeniden yazar (guncel sezon icin; tam kurulum ~35 dk, bu birkac saniye)."""
    if sadece is None and os.path.exists(db):
        os.remove(db)
    c = sqlite3.connect(db)
    kulupler, adlar, yazilan, gor = {}, collections.defaultdict(list), 0, []
    if sadece is None:
        c.executescript(SEMA)
    else:
        kulupler = {t: i for i, t in c.execute("SELECT id, tff_id FROM kulup")}
        eski_kulup = set(kulupler)
        for k in sadece:
            kaynak, etiket, _ = k.rsplit("_", 2)
            c.execute("DELETE FROM mac WHERE kaynak='tff' AND sezon=? AND lig=?", (etiket, LIG[kaynak]))
            c.execute("DELETE FROM puan WHERE sezon=? AND lig=?", (etiket, LIG[kaynak]))
    klasorler = sorted(d for d in glob.glob(os.path.join(ham, "*_*_*")) if os.path.isdir(d))
    if sadece is not None:
        klasorler = [d for d in klasorler if os.path.basename(d) in sadece]
    for klasor in klasorler:
        kaynak, etiket, _pid = os.path.basename(klasor).rsplit("_", 2)
        yil = int(etiket[:4])
        giris = os.path.join(klasor, "giris.html")
        gt0 = oku(giris) if os.path.exists(giris) else ""
        gad = {k: grup_tam_ad(v) for k, v in gruplar(gt0).items()} if gt0 else {}
        if gad and ana_yukselme(gt0):
            gad[""] = "Yükselme Grubu"
        # resmi puan durumu: grup sayfasi (haftasiz); grupsuz sezonda giris sayfasi
        tablo_sayfalari = [(os.path.join(klasor, f"g{g}.html"), gad[g]) for g in gad if g] if gad else [(giris, None)]
        for yol, grup in tablo_sayfalari:
            if os.path.exists(yol):
                for r in puan_tablosu(oku(yol)):
                    c.execute("INSERT INTO puan VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (kademe(kaynak, yil), LIG[kaynak], etiket, grup, r["sira"], r["tff_id"], r["ad"], r["O"], r["G"],
                               r["B"], r["M"], r["A"], r["Y"], r["AV"], r["P"], os.path.basename(klasor) + "/" + os.path.basename(yol)))
        for yol in sorted(glob.glob(os.path.join(klasor, "*.html"))):
            ad = re.fullmatch(r"g(\d*)(?:_h(\d+))?\.html|giris\.html", os.path.basename(yol))
            if not ad:
                continue
            for m in maclar(oku(yol)):
                for k, n in ((m["ev_id"], m["ev"]), (m["dep_id"], m["dep"])):
                    if k not in kulupler:
                        kulupler[k] = len(kulupler) + 1
                    adlar[(kulupler[k], n)].append(etiket)
                s = re.fullmatch(r"(\d+)\s*-\s*(\d+)", m["skor"])
                pen = re.search(r"(\d+)\s*-\s*(\d+)", m["pen"] or "")
                hafta = int(ad.group(2)) if ad.group(2) and not m["po"] else None
                grup = None if m["po"] else (gad.get(ad.group(1) or "") or None)
                ana = int(not ad.group(1))
                # 2007-10 2. Lig: Yukselme Grubu'nun kendi sayfasi yok; maclari her sayfanin yan modulunde, "1 - 2"
                # bicimli skorla gorunur (haftasi = sayfanin haftasi)
                if gad.get("") == "Yükselme Grubu" and not m["po"] and re.fullmatch(r"\d+ - \d+", m["skor"]):
                    grup, ana = "Yükselme Grubu", 0
                elif gad.get("") == "Yükselme Grubu" and not ad.group(1):
                    grup = None   # ana sayfanin hafta listesi aslinda 01 grubunu gosteriyor
                # ana sayfa (grupID'siz) bazen varsayilan grubu (01) gosterir: o gorunum ayri bir grup sayilmaz
                gor.append((m["mac"], grup, ana))
                c.execute("""INSERT INTO mac(kaynak,kaynak_id,kademe,lig,sezon,grup,asama,hafta,tarih,saat,ev_id,dep_id,ev_adi,dep_adi,ev_gol,dep_gol,ev_pen,dep_pen,ham_skor)
                             VALUES('tff',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                             ON CONFLICT(kaynak,kaynak_id) DO UPDATE SET
                               hafta=COALESCE(hafta,excluded.hafta), grup=COALESCE(grup,excluded.grup)""",
                          (m["mac"], kademe(kaynak, yil), LIG[kaynak], etiket,
                           grup, m["tur"] or ("play-off" if m["po"] else "lig"),
                           hafta, m["tarih"], m["saat"], kulupler[m["ev_id"]], kulupler[m["dep_id"]], m["ev"], m["dep"],
                           int(s.group(1)) if s else None, int(s.group(2)) if s else None,
                           int(pen.group(1)) if pen else None, int(pen.group(2)) if pen else None, m["skor"]))
                yazilan += 1
    # Birden cok grubun sayfasinda gorunen mac (play-off/final modulu her grup sayfasinda tekrarlaniyor) hicbir gruba ait degil
    c.execute("CREATE TEMP TABLE gor(kaynak_id TEXT, grup TEXT, ana INTEGER)")
    c.executemany("INSERT INTO gor VALUES(?,?,?)", gor)
    # Grup sayfalarinda gorunen mac icin ana sayfa gorunumu yok sayilir; yalniz ana sayfada gorunende o kullanilir
    c.execute("""DELETE FROM gor WHERE ana=1 AND kaynak_id IN (SELECT kaynak_id FROM gor WHERE ana=0)""")
    c.execute("""UPDATE mac SET grup=(SELECT MAX(grup) FROM gor WHERE gor.kaynak_id=mac.kaynak_id)
                 WHERE kaynak='tff' AND asama='lig' AND kaynak_id IN (SELECT kaynak_id FROM gor GROUP BY kaynak_id HAVING COUNT(DISTINCT grup)=1)""")
    n = c.execute("""UPDATE mac SET grup=NULL, asama=CASE asama WHEN 'lig' THEN 'play-off' ELSE asama END
                     WHERE kaynak='tff' AND kaynak_id IN (SELECT kaynak_id FROM gor GROUP BY kaynak_id HAVING COUNT(DISTINCT grup)>1)""").rowcount
    print("birden cok grupta gorunen mac (gruba yazilmadi, play-off):", n)
    for tid, kid in kulupler.items():
        if sadece is not None and tid in eski_kulup:
            continue
        en = max((n for k, n in adlar if k == kid), key=lambda n: len(adlar[(kid, n)]))
        c.execute("INSERT INTO kulup VALUES(?,?,?)", (kid, tid, en))
    if sadece is None:
        for (kid, n), ss in adlar.items():
            c.execute("INSERT INTO kulup_adi VALUES(?,?,?,?,?)", (kid, n, min(ss), max(ss), len(ss)))
    else:
        c.execute("DELETE FROM kulup_adi")
        c.execute("""INSERT INTO kulup_adi SELECT k, ad, MIN(sezon), MAX(sezon), COUNT(DISTINCT sezon) FROM
                     (SELECT ev_id k, ev_adi ad, sezon FROM mac UNION ALL SELECT dep_id, dep_adi, sezon FROM mac) GROUP BY 1, 2""")
    c.execute("DELETE FROM kapsam")
    c.execute("""INSERT INTO kapsam
      WITH m AS (SELECT kademe, sezon, COALESCE(grup,'') grup, ev_id, dep_id FROM mac WHERE asama='lig'),
           t AS (SELECT kademe, sezon, grup, ev_id k FROM m UNION SELECT kademe, sezon, grup, dep_id FROM m),
           n AS (SELECT kademe, sezon, grup, COUNT(*) takim FROM t GROUP BY 1,2,3),
           b AS (SELECT kademe, sezon, grup, COUNT(*) bulunan FROM m GROUP BY 1,2,3)
      SELECT n.kademe, n.sezon, n.grup, n.takim, b.bulunan, n.takim*(n.takim-1) FROM n JOIN b USING(kademe, sezon, grup)""")
    c.commit()
    print("satir okundu:", yazilan, "| mac:", c.execute("select count(*) from mac").fetchone()[0],
          "| kulup:", c.execute("select count(*) from kulup").fetchone()[0])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("komut", choices=["indir", "kur"])
    p.add_argument("--deneme", action="store_true")
    p.add_argument("--db", default=os.path.join(KOK, "futbol.db"))
    p.add_argument("--ham", default=HAM)
    a = p.parse_args()
    indir(a.deneme) if a.komut == "indir" else kur(a.db, a.ham)

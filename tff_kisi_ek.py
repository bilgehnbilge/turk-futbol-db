#!/usr/bin/env python3
"""TFF kişi verisinin eksikleri: teknik direktör ve hakem sayfaları, oyuncu lisans hareketlerinin sonraki sayfaları.

  python3 tff_kisi_ek.py td [--db ...]       # teknik direktörler: kişi sayfası (doğum vb., raw/tff_kisi) + görev geçmişi (raw/tff_td)
  python3 tff_kisi_ek.py hakem [--db ...]    # hakemler: kişi sayfası (raw/tff_kisi) + hakem kartı: lisans, klasman, bölge (raw/tff_hakem)
  python3 tff_kisi_ek.py liste               # bütün teknik adamlar (antrenör, altyapı dahil) son görevleriyle (raw/tff_tdliste);
                                             #   sonra "td" maç kağıdında adı geçmeyen üst düzey görevlilerin görev geçmişini de indirir
  python3 tff_kisi_ek.py hareket             # 20'den çok lisans hareketi olan oyuncuların 2., 3. ... sayfaları (raw/tff_kisi_ek)
  python3 tff_kisi_ek.py say                 # ne kadarı indi
  python3 tff_kisi_ek.py ayikla [--hedef kisi.db]   # -> hareket, td_gorev, hakem_kart, td_liste tabloları

Teknik direktör, hakem ve oyuncu aynı TFF kişi numarasını kullanır (pageId=30&kisiId=, 219&antId=, 72&hakemId=).
Sayfalı tablolar ASP.NET geri gönderimiyle (__doPostBack) gelir: kayıtlı sayfanın gizli alanlarıyla "Sonraki" bağlantısı POST edilir,
her yanıt bir sonrakinin gizli alanlarını taşır. Kaldığı yerden devam eder; hata veren sayfa kaydedilmez, sonraki çalıştırmada denenir.
"""
import argparse, glob, gzip, html, os, re, sqlite3, sys, time, urllib.error, urllib.parse, urllib.request

import oyuncu

KOK = os.path.dirname(os.path.abspath(__file__))
UA = oyuncu.UA
TD_HAM = os.path.join(KOK, "raw", "tff_td")
HAKEM_HAM = os.path.join(KOK, "raw", "tff_hakem")
EK_HAM = os.path.join(KOK, "raw", "tff_kisi_ek")
TD_URL = "https://www.tff.org/Default.aspx?pageId=219&antId={}"
HAKEM_URL = "https://www.tff.org/Default.aspx?pageId=72&hakemId={}"
# hedef listesi: botun güncel kopyaları (raw/bot_kopya, Releases'teki paketten) varsa onlar, yoksa yereldekiler
VARSAYILAN_DB = [os.path.join(KOK, "raw", "bot_kopya", a) if os.path.exists(os.path.join(KOK, "raw", "bot_kopya", a)) else os.path.join(KOK, "raw", a)
                 for a in ("oyuncu.db", "bal_detay.db", "kadin_detay.db")]
BEKLE = 2.0


def yol(kok, k, sayfa=1):
    return os.path.join(kok, str(k)[-2:].zfill(2), f"{k}.html.gz" if sayfa == 1 else f"{k}_{sayfa}.html.gz")


def yaz(y, govde):
    os.makedirs(os.path.dirname(y), exist_ok=True)
    with gzip.open(y + ".tmp", "wb") as g:
        g.write(govde)
    os.replace(y + ".tmp", y)


def iste(url, veri=None):
    """(HTTP kodu, gövde bayt) — bağlantı hatasında (0, b"")."""
    r = urllib.request.Request(url, data=veri, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(r, timeout=60) as y:
            return y.status, y.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return 0, b""


def toplam_sayfa(t):
    """'1 / 3, Toplam 24 kayıt' -> 3 (sayfa çubuğu yoksa 1)"""
    m = re.search(r"(\d+)\s*/\s*(\d+),\s*Toplam", t)
    return int(m.group(2)) if m else 1


def sonraki(url, t, izgara):
    """t sayfasındaki <izgara> tablosunun "Sonraki »" bağlantısını POST eder: (kod, gövde) ya da bağlantı yoksa None."""
    hed = [html.unescape(x) for x in re.findall(r"__doPostBack\(&#39;([^&]*\$" + izgara + r"\$[^&]*)&#39;,&#39;&#39;\)\"[^>]*>\)?\s*Sonraki", t)]
    if not hed:
        return None
    alan = {a: html.unescape(v) for a, v in re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', t)}
    alan["__EVENTTARGET"], alan["__EVENTARGUMENT"] = hed[0], ""
    return iste(url, urllib.parse.urlencode(alan).encode())


class Sayac:
    def __init__(self):
        self.hata = self.kesinti = 0

    def basarili(self):
        self.hata = 0

    def basarisiz(self, ne, kod):
        self.hata += 1
        with open(os.path.join(KOK, "hatalar.log"), "a") as f:
            f.write(f"{time.strftime('%F %T')} {ne} {kod}\n")
        if self.hata >= 10:
            self.kesinti += 1
            if self.kesinti > 24:
                sys.exit("12 saattir art arda hata: durdum (aynı komut kaldığı yerden devam eder).")
            print(f"  art arda 10 hata (son kod {kod or 'bağlantı yok'}), 30 dk bekleniyor ({time.strftime('%H:%M')})", flush=True)
            time.sleep(1800)
            self.hata = 0
        time.sleep(30 * self.hata)


def sayfalar_indir(sy, kok, k, url, ilk, izgara, imza):
    """ilk sayfa (inmiş ya da yeni) + sayfa çubuğundaki sonraki sayfalar; imza: sayfanın geçerli olduğunu gösteren metin."""
    t = ilk.decode("cp1254", "replace")
    n = toplam_sayfa(t)
    for s in range(2, n + 1):
        y = yol(kok, k, s)
        if os.path.exists(y):
            t = gzip.open(y).read().decode("cp1254", "replace")
            continue
        time.sleep(BEKLE)
        r = sonraki(url, t, izgara)
        if r is None:
            break
        kod, govde = r
        if kod != 200 or imza not in govde or f"{s} / {n}".encode() not in govde:
            sy.basarisiz(f"{os.path.basename(kok)} {k} s{s}", kod)
            return False
        yaz(y, govde)
        sy.basarili()
        t = govde.decode("cp1254", "replace")
    return True


def kisi_sayfasi(sy, k):
    """Kişi sayfası (doğum tarihi vb.) yoksa indirir; True: var/indi ya da TFF'de yok; False: hata."""
    y = oyuncu.kisi_yol(k)
    if os.path.exists(y) or os.path.exists(y + ".yok"):
        return True
    kod, govde = iste(oyuncu.KISI_URL.format(k))
    time.sleep(BEKLE)
    if kod == 200 and b"oyuncuBilgileri_lblAdi" in govde:
        yaz(y, govde); sy.basarili(); return True
    if kod == 200 and len(govde) > 15000 and b"tff.org" in govde.lower():
        os.makedirs(os.path.dirname(y), exist_ok=True)
        open(y + ".yok", "w").close(); sy.basarili(); return True
    sy.basarisiz(f"kisi {k}", kod)
    return False


def hedefler(dbs, tablo):
    say = {}
    for db in dbs:
        if os.path.exists(db):
            for k, n in sqlite3.connect(db).execute(f"SELECT kisi, COUNT(*) FROM {tablo} WHERE kisi IS NOT NULL GROUP BY kisi"):
                say[k] = say.get(k, 0) + n
    return sorted(say, key=lambda k: -say[k])   # en çok maçı olandan


def gorev_indir(ne, dbs):
    """ne: 'td' ya da 'hakem'"""
    kok, url_k, tablo, izgara, imza = {
        "td": (TD_HAM, TD_URL, "teknik", "grdSonuc", "Yönettiği Takımlar".encode("cp1254")),
        "hakem": (HAKEM_HAM, HAKEM_URL, "hakem", None, "Hakem Bilgi Kartı".encode("cp1254")),
    }[ne]
    liste = hedefler(dbs, tablo)
    if ne == "td":   # teknik adam listesinden (indiyse) maç kağıdında adı geçmeyen üst düzey görevliler
        bilinen = set(liste)
        liste += [r[0] for r in liste_satirlari() if r[0] not in bilinen and UST_GOREV.search(r[4] or "")]
    eksik = [k for k in liste if not os.path.exists(yol(kok, k)) or not (os.path.exists(oyuncu.kisi_yol(k)) or os.path.exists(oyuncu.kisi_yol(k) + ".yok"))]
    print(f"{ne}: {len(liste)} kişi, {len(eksik)} eksik (~{len(eksik) * 2 * (BEKLE + 1) / 3600:.1f} saat)", flush=True)
    sy = Sayac()
    for i, k in enumerate(eksik, 1):
        if not kisi_sayfasi(sy, k):
            continue
        y = yol(kok, k)
        if os.path.exists(y):
            ilk = gzip.open(y).read()
        else:
            kod, ilk = iste(url_k.format(k))
            time.sleep(BEKLE)
            if kod == 200 and imza in ilk:
                yaz(y, ilk); sy.basarili()
            elif kod == 200 and len(ilk) > 15000 and b"tff.org" in ilk.lower():
                os.makedirs(os.path.dirname(y), exist_ok=True)
                open(y + ".yok", "w").close(); sy.basarili(); continue
            else:
                sy.basarisiz(f"{ne} {k}", kod); continue
        if izgara:
            sayfalar_indir(sy, kok, k, url_k.format(k), ilk, izgara, imza)
        if i % 200 == 0:
            print(f"  {i}/{len(eksik)} {time.strftime('%H:%M')}", flush=True)
    print("Bitti.", flush=True)


# ---------------------------------------------------------------- teknik adam listesi (pageID=163, "Takıma Göre", Tümü)
# TFF teknik adam araması her kişiyi SON görevinin kulübüyle bir kez listeler; takım adı en az 3 harfli ön ekle aranır.
# Bilinen bütün kulüp adlarının ilk 3 harfiyle arayınca son görevi bu kulüplerden birinde olan herkes (antrenör, altyapı dahil) çıkar.
LISTE_HAM = os.path.join(KOK, "raw", "tff_tdliste")
LISTE_URL = "https://www.tff.org/default.aspx?pageID=163"
LP = "ctl00$MPane$m_163_864_ctnr$m_163_864$"
BOS = "Uygun kayıt bulunamadı".encode("cp1254")


def _form(t):
    """sayfadaki bütün input alanları (gönderme düğmeleri hariç)"""
    f = {}
    for m in re.finditer(r"<input[^>]+>", t):
        s = m.group(0)
        n = re.search(r'name="([^"]+)"', s)
        ty = re.search(r'type="([^"]+)"', s)
        if not n or (ty and ty.group(1) in ("submit", "image", "checkbox", "button")):
            continue
        v = re.search(r'value="([^"]*)"', s)
        f[html.unescape(n.group(1))] = html.unescape(v.group(1)) if v else ""
    return f


def liste_yol(ek, s=1):
    a = urllib.parse.quote(ek, safe="")
    return os.path.join(LISTE_HAM, f"{a}.html.gz" if s == 1 else f"{a}_{s}.html.gz")


def on_ekler(dbs):
    """bilinen TFF kulüp adlarının (maç kağıtları, lisans hareketleri, görev listeleri) ilk 3 harfi"""
    adlar = set()
    for db in dbs + [oyuncu.KISI_DB]:
        if not os.path.exists(db):
            continue
        c = sqlite3.connect(db)
        tab = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "mac_bilgi" in tab:
            for a, b in c.execute("SELECT DISTINCT ev_adi, dep_adi FROM mac_bilgi"):
                adlar.update((a, b))
        for t in ("hareket", "td_gorev"):
            if t in tab:
                adlar.update(r[0] for r in c.execute(f"SELECT DISTINCT kulup_ad FROM {t}"))
    ekler = set()
    for a in adlar:
        a = " ".join((a or "").split())
        if len(a) >= 3:
            ekler.add(a[:3].replace("i", "İ").upper())
    return sorted(e for e in ekler if len(e.strip()) == 3)


def liste_indir(dbs):
    import http.cookiejar
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def git(veri=None):
        try:
            with op.open(urllib.request.Request(LISTE_URL, data=veri, headers={"User-Agent": UA}), timeout=90) as y:
                return y.status, y.read()
        except urllib.error.HTTPError as e:
            return e.code, b""
        except Exception:
            return 0, b""

    def gonder(f):
        time.sleep(BEKLE)
        return git(urllib.parse.urlencode(f, encoding="cp1254").encode())

    def sablon_al():
        kod, t = git()
        if kod != 200:
            return None
        f = _form(t.decode("cp1254", "replace"))
        f["__EVENTTARGET"], f["__EVENTARGUMENT"] = LP + "RadTabStrip1", LP + "RadTabStrip1$Tab2"
        kod, t = gonder(f)
        return t.decode("cp1254", "replace") if kod == 200 and LP.encode() + b"txtTakimAdi" in t else None

    ekler = on_ekler(dbs)
    bitti = lambda e: os.path.exists(liste_yol(e) + ".yok") or (os.path.exists(liste_yol(e)) and all(
        os.path.exists(liste_yol(e, s)) for s in range(2, toplam_sayfa(_oku(liste_yol(e))) + 1)))
    eksik = [e for e in ekler if not bitti(e)]
    print(f"liste: {len(ekler)} ön ek, {len(eksik)} eksik {time.strftime('%H:%M')}", flush=True)
    sy = Sayac()
    sablon = None
    for i, ek in enumerate(eksik, 1):
        if sablon is None:
            sablon = sablon_al()
            if sablon is None:
                sy.basarisiz("liste şablon", 0); continue
        y = liste_yol(ek)
        if os.path.exists(y):
            t = _oku(y)
        else:
            f = _form(sablon)
            f.update({LP + "txtTakimAdi": ek, LP + "Button1": "Ara", LP + "f2_text": "Tümü", LP + "f2_Input": "Tümü",
                      LP + "f2_value": "1", LP + "f2_index": "0"})
            kod, g = gonder(f)
            if kod == 200 and BOS in g:
                os.makedirs(LISTE_HAM, exist_ok=True)
                open(y + ".yok", "w").close(); sy.basarili(); continue
            if kod != 200 or b"antID=" not in g:
                sy.basarisiz(f"liste {ek}", kod); sablon = None; continue
            yaz(y, g); sy.basarili()
            t = g.decode("cp1254", "replace")
        n = toplam_sayfa(t)
        for s in range(2, n + 1):
            ys = liste_yol(ek, s)
            if os.path.exists(ys):
                t = _oku(ys); continue
            hed = [html.unescape(x) for x in re.findall(r"__doPostBack\(&#39;([^&]*\$rdgSonuclar\$[^&]*)&#39;,&#39;&#39;\)\"[^>]*>\)?\s*Sonraki", t)]
            if not hed:
                break
            f = _form(t)
            f["__EVENTTARGET"], f["__EVENTARGUMENT"] = hed[0], ""
            kod, g = gonder(f)
            if kod != 200 or f"{s} / {n}".encode() not in g:
                sy.basarisiz(f"liste {ek} s{s}", kod); sablon = None; break
            yaz(ys, g); sy.basarili()
            t = g.decode("cp1254", "replace")
        if i % 25 == 0:
            print(f"  {i}/{len(eksik)} {time.strftime('%H:%M')}", flush=True)
    print("Bitti.", flush=True)


def liste_oku(t):
    """[(kişi no, ad, TFF kulüp no, kulüp adı, görev, baş., bitiş, fesih)]"""
    i = t.find("rdgSonuclar")
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t[i:], re.S):
        m = re.search(r"antI[dD]=(\d+)", tr)
        if not m:
            continue
        h = [_hucre(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(h) < 6:
            continue
        kno = re.search(r"kulupI[dD]=(\d+)", tr)
        out.append((int(m.group(1)), h[0], int(kno.group(1)) if kno else None, h[1], h[2], _tarih(h[3]), _tarih(h[4]), _tarih(h[5])))
    return out


def liste_satirlari():
    sat = {}
    for f in glob.glob(os.path.join(LISTE_HAM, "*.html.gz")):
        for r in liste_oku(_oku(f)):
            sat[r[0]] = r
    return list(sat.values())


# TD görev sayfası indirilecekler: son görevi profesyonel/BAL/A takım düzeyinde olanlar
UST_GOREV = re.compile(r"PROFESYONEL|PGL|BAL|A TAKIM|KADIN")


def hareket_indir():
    liste = []
    for f in glob.glob(os.path.join(oyuncu.KISI_HAM, "*", "*.html.gz")):
        t = gzip.open(f).read()
        m = re.search(rb"(\d+)\s*/\s*(\d+),\s*Toplam", t)
        if m and int(m.group(2)) > 1:
            k = os.path.basename(f)[:-8]
            if not all(os.path.exists(yol(EK_HAM, k, s)) for s in range(2, int(m.group(2)) + 1)):
                liste.append((k, f))
    print(f"hareket: {len(liste)} oyuncunun sonraki sayfaları eksik", flush=True)
    sy = Sayac()
    for i, (k, f) in enumerate(liste, 1):
        sayfalar_indir(sy, EK_HAM, k, oyuncu.KISI_URL.format(k), gzip.open(f).read(), "grdTakimlar", b"oyuncuBilgileri_lblAdi")
        if i % 200 == 0:
            print(f"  {i}/{len(liste)} {time.strftime('%H:%M')}", flush=True)
    print("Bitti.", flush=True)


# ---------------------------------------------------------------- ayıklama
def _hucre(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split()) or None


def _tarih(s):
    m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", s or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def izgara_satirlari(t, izgara):
    """RadGrid tablosunun veri satırları: [(TFF kulüp no ya da None, [hücre metinleri])]"""
    i = t.find(f"_{izgara}_ctl01")
    if i < 0:
        return []
    j = t.find("<tbody>", i)
    k = t.find("</tbody>", j)
    if j < 0 or k < 0:
        return []
    out = []
    for tr in re.findall(r'<tr class="Grid(?:Alt)?Row_TFF_Contents">(.*?)</tr>', t[j:k], re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        m = re.search(r"kulupI[dD]=(\d+)", tr)
        out.append((int(m.group(1)) if m else None, [_hucre(x) for x in tds]))
    return out


def hareket_oku(t):
    """Kişi sayfasının bir sayfası -> [(TFF kulüp no, kulüp adı, sözleşme baş., bitiş, lisans türü, veriliş, yurt dışına çıkış)]"""
    return [(kno, h[0], _tarih(h[1]), _tarih(h[2]), h[3], _tarih(h[4]), _tarih(h[5]))
            for kno, h in izgara_satirlari(t, "grdTakimlar") if len(h) >= 6]


def td_oku(t):
    """[(TFF kulüp no, kulüp adı, görev, sözleşme baş., bitiş, fesih)]"""
    return [(kno, h[0], h[1], _tarih(h[2]), _tarih(h[3]), _tarih(h[4])) for kno, h in izgara_satirlari(t, "grdSonuc") if len(h) >= 5]


def hakem_oku(t):
    """(lisans no, klasman, bölge)"""
    al = lambda n: (lambda m: _hucre(m.group(1)) if m else None)(re.search(r'dtlHakemBilgi_' + n + r'"[^>]*>(.*?)</', t, re.S))
    return al("Label3"), al("Label4"), al("Label6")


TABLOLAR = {
    "hareket": "CREATE TABLE IF NOT EXISTS hareket(kisi INTEGER, sira INTEGER, kulup_tff INTEGER, kulup_ad TEXT, bas TEXT, bit TEXT, tur TEXT, verilis TEXT, yurtdisi TEXT)",
    "td_gorev": "CREATE TABLE IF NOT EXISTS td_gorev(kisi INTEGER, sira INTEGER, kulup_tff INTEGER, kulup_ad TEXT, gorev TEXT, bas TEXT, bit TEXT, fesih TEXT)",
    "hakem_kart": "CREATE TABLE IF NOT EXISTS hakem_kart(kisi INTEGER PRIMARY KEY, lisans TEXT, klasman TEXT, bolge TEXT)",
    "td_liste": "CREATE TABLE IF NOT EXISTS td_liste(kisi INTEGER PRIMARY KEY, ad TEXT, kulup_tff INTEGER, kulup_ad TEXT, gorev TEXT, bas TEXT, bit TEXT, fesih TEXT)",
}


def tablolar(c):
    for s in TABLOLAR.values():
        c.execute(s)
    c.execute("CREATE INDEX IF NOT EXISTS hareket_kisi ON hareket(kisi)")
    c.execute("CREATE INDEX IF NOT EXISTS td_gorev_kisi ON td_gorev(kisi)")


def hareket_yaz(c, k, sayfalar):
    """bir kişinin hareketlerini (bütün sayfalar) yazar; o kişinin eski satırları silinir. sayfalar: sayfa metinleri, sırayla."""
    sat = [r for t in sayfalar for r in hareket_oku(t)]
    c.execute("DELETE FROM hareket WHERE kisi=?", (k,))
    c.executemany("INSERT INTO hareket VALUES(?,?,?,?,?,?,?,?,?)", [(k, i, *r) for i, r in enumerate(sat)])
    return len(sat)


def _oku(y):
    return gzip.open(y).read().decode("cp1254", "replace")


def ayikla(db):
    """İnmiş sayfalar -> db (kisi.db): hareket, td_gorev, hakem_kart. Yalnız sayfası yerelde olan kişilerin satırları yenilenir
    (bot yeni oyuncuların hareketlerini aynı tablolara kendisi yazar, onlar korunur)."""
    c = sqlite3.connect(db)
    tablolar(c)
    n = eksik = 0
    for f in glob.glob(os.path.join(oyuncu.KISI_HAM, "*", "*.html.gz")):
        k = int(os.path.basename(f)[:-8])
        t = _oku(f)
        sayfalar = [t] + [_oku(yol(EK_HAM, k, s)) for s in range(2, toplam_sayfa(t) + 1) if os.path.exists(yol(EK_HAM, k, s))]
        eksik += len(sayfalar) < toplam_sayfa(t)
        n += hareket_yaz(c, k, sayfalar)
    print(f"hareket: {n} satır ({eksik} oyuncunun sonraki sayfaları eksik)", flush=True)
    n = 0
    for f in glob.glob(os.path.join(TD_HAM, "*", "*.html.gz")):
        b = os.path.basename(f)[:-8]
        if "_" in b:
            continue
        k = int(b)
        t = _oku(f)
        sat = [r for s in range(1, toplam_sayfa(t) + 1) if os.path.exists(yol(TD_HAM, k, s)) for r in td_oku(_oku(yol(TD_HAM, k, s)))]
        c.execute("DELETE FROM td_gorev WHERE kisi=?", (k,))
        c.executemany("INSERT INTO td_gorev VALUES(?,?,?,?,?,?,?,?)", [(k, i, *r) for i, r in enumerate(sat)])
        n += len(sat)
    print(f"td_gorev: {n} satır", flush=True)
    hk = [(int(os.path.basename(f)[:-8]), *hakem_oku(_oku(f))) for f in glob.glob(os.path.join(HAKEM_HAM, "*", "*.html.gz"))]
    c.executemany("INSERT OR REPLACE INTO hakem_kart VALUES(?,?,?,?)", hk)
    print(f"hakem_kart: {len(hk)} hakem", flush=True)
    tl = liste_satirlari()
    c.executemany("INSERT OR REPLACE INTO td_liste VALUES(?,?,?,?,?,?,?,?)", tl)
    print(f"td_liste: {len(tl)} teknik adam (son görevleriyle)", flush=True)
    c.commit()


def say(dbs):
    for ne, kok, tablo in (("td", TD_HAM, "teknik"), ("hakem", HAKEM_HAM, "hakem")):
        liste = hedefler(dbs, tablo)
        var = sum(1 for k in liste if os.path.exists(yol(kok, k)) or os.path.exists(yol(kok, k) + ".yok"))
        print(f"{ne}: {var}/{len(liste)} görev sayfası; ek sayfa {len(glob.glob(os.path.join(kok, '*', '*_*.html.gz')))}")
    print(f"hareket ek sayfa: {len(glob.glob(os.path.join(EK_HAM, '*', '*.html.gz')))}")
    ekler = on_ekler(dbs)
    var = sum(1 for e in ekler if os.path.exists(liste_yol(e)) or os.path.exists(liste_yol(e) + ".yok"))
    print(f"teknik adam listesi: {var}/{len(ekler)} ön ek, {len(liste_satirlari())} kişi")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("komut", choices=["td", "hakem", "hareket", "liste", "say", "ayikla"])
    p.add_argument("--hedef", default=oyuncu.KISI_DB, help="ayikla: yazılacak kisi.db")
    p.add_argument("--db", nargs="*", default=VARSAYILAN_DB, help="kadro/teknik/hakem tablolu ayrıntı veritabanları")
    a = p.parse_args()
    if a.komut == "hareket":
        hareket_indir()
    elif a.komut == "liste":
        liste_indir(a.db)
    elif a.komut == "ayikla":
        ayikla(a.hedef)
    elif a.komut == "say":
        say(a.db)
    else:
        gorev_indir(a.komut, a.db)

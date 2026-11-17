"""TFF maç detay sayfalarından kadro, gol, kart, oyuncu değişikliği, teknik direktör ve hakem verisi.

  python3 oyuncu.py indir [--kademe 1] [--sezon 2015-2016] [--bekle 2]   # raw/tff_mac/<..>/<macId>.html.gz (kaldığı yerden)
  python3 oyuncu.py kupa [--bekle 2]                                     # Türkiye Kupası maç sayfaları (TFF kupa arşivi, pageID=411)
  python3 oyuncu.py ayikla                                               # raw/oyuncu.db
  python3 oyuncu.py uyum                                                 # mac_bilgi.gol_uyum: gol listesi skorla tutuyor mu
  python3 oyuncu.py kisi [--bekle 2]                                     # raw/tff_kisi/<..>/<kisiId>.html.gz: oyuncu sayfaları
  python3 oyuncu.py kisi_ayikla                                          # raw/tff_kisi -> raw/kisi.db (doğum tarihi/yeri, uyruk)
  python3 oyuncu.py durum                                                # kaç sayfa indi / kaldı

Sayfa: https://www.tff.org/Default.aspx?pageID=29&macId=<macId>  (macId = tff.db'deki kaynak_id)
Kapsam: kadrolar 1990-91'den, gol/kart dakikaları yaklaşık 1995-96'dan itibaren dolu.
"""
import argparse, collections, glob, gzip, os, re, sqlite3, subprocess, sys, time

import topla

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "tff_mac")
TFF_DB = os.path.join(KOK, "raw", "tff.db")
OYUNCU_DB = os.path.join(KOK, "raw", "oyuncu.db")
URL = "https://www.tff.org/Default.aspx?pageID=29&macId={}"
UA = topla.UA


def yol(mac_id):
    return os.path.join(HAM, str(mac_id)[-2:].zfill(2), f"{mac_id}.html.gz")


def hedefler(kademe=None, sezon=None):
    """İndirilecek maçlar: skoru olan TFF lig maçları (en yeni sezondan geriye)."""
    c = sqlite3.connect(TFF_DB)
    q = "SELECT kaynak_id, sezon, kademe FROM mac WHERE kaynak='tff' AND kaynak_id<>'' AND ev_gol IS NOT NULL"
    p = []
    if kademe:
        q += " AND kademe=?"; p.append(kademe)
    if sezon:
        q += " AND sezon=?"; p.append(sezon)
    sirali = [(r[0], r[1]) for r in c.execute(q.replace("SELECT kaynak_id, sezon, kademe", "SELECT kaynak_id, kademe") + " ORDER BY kademe, sezon DESC, tarih", p)]
    # 1990-2007 TFF numara boşlukları (sezon sayfalarında listelenmeyen play-off/baraj, kupa, PAF... maçları): Süper Lig'den sonra
    yoklama = os.path.join(KOK, "raw", "tff_mac_yoklama.txt")
    if kademe or sezon or not os.path.exists(yoklama):
        return [m for m, _ in sirali]
    ek = open(yoklama).read().split()
    return [m for m, k in sirali if k == 1] + ek + [m for m, k in sirali if k != 1]


AYLAR = {a: i for i, a in enumerate(["ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık"], 1)}
KISI_DB = os.path.join(KOK, "raw", "kisi.db")


def kisi_ayikla():
    """İnmiş TFF oyuncu sayfaları (raw/tff_kisi) -> raw/kisi.db: ad, doğum tarihi, doğum yeri, uyruk."""
    import html as H
    c = sqlite3.connect(KISI_DB)
    c.execute("DROP TABLE IF EXISTS kisi")
    c.execute("CREATE TABLE kisi(kisi INTEGER PRIMARY KEY, ad TEXT, dogum TEXT, yer TEXT, uyruk TEXT)")
    al = lambda t, k: (lambda m: " ".join(H.unescape(re.sub(r"<[^>]+>", "", m.group(1))).split()) if m else "")(
        re.search(r'oyuncuBilgileri_' + k + r'"[^>]*>(.*?)</', t, re.S))
    satir = []
    for f in glob.glob(os.path.join(KISI_HAM, "*", "*.html.gz")):
        t = gzip.open(f).read().decode("cp1254", "replace")
        g = re.match(r"(\d{1,2})\s+(\S+)\s+(\d{4})", al(t, "Label2"))
        ay = AYLAR.get(g.group(2).replace("I", "ı").replace("İ", "i").lower()) if g else None
        dogum = f"{g.group(3)}-{ay:02d}-{int(g.group(1)):02d}" if g and ay else None
        satir.append((int(os.path.basename(f)[:-8]), topla.temiz(al(t, "lblAdi")), dogum, topla.temiz(al(t, "Label1")) or None, al(t, "Label3") or None))
    c.executemany("INSERT INTO kisi VALUES(?,?,?,?,?)", satir)
    c.commit()
    print(f"{len(satir)} oyuncu sayfası -> {KISI_DB}; doğum tarihi olan: {sum(1 for r in satir if r[2])}")


def kupa_hedefleri():
    """Türkiye Kupası maçları: TFF kupa arşivinin sezon sayfaları (raw/tff_kupa/kupa_<sezon>_<pageID>.html; arşiv pageID=411),
    skoru olan maçlar, en yeni sezondan geriye."""
    out, gor = [], set()
    # grup aşamaları ayrı grup/hafta sayfalarında (kupa_gruplari): raw/tff_kupa_grup/kupa_<sezon>_<pageID>/
    dosyalar = sorted(glob.glob(os.path.join(KOK, "raw", "tff_kupa", "kupa_*.html")) +
                      glob.glob(os.path.join(KOK, "raw", "tff_kupa_grup", "kupa_*", "*.html")), reverse=True)
    for f in dosyalar:
        for m in topla.maclar(topla.oku(f)):
            if m["mac"] and m["mac"] not in gor and re.fullmatch(r"\d+\s*-\s*\d+", m["skor"] or ""):
                gor.add(m["mac"]); out.append(m["mac"])
    return out


def kupa_gruplari():
    """Kupa sezonlarının grup aşaması: sezon sayfasındaki grupların grup ve hafta sayfaları -> raw/tff_kupa_grup/ (kaldığı yerden)."""
    topla.HAM = os.path.join(KOK, "raw", "tff_kupa_grup")
    d = topla.Indirici()
    for f in sorted(glob.glob(os.path.join(KOK, "raw", "tff_kupa", "kupa_*.html"))):
        m = re.search(r"kupa_(\d{4}-\d{4})_(\d+)\.html", f)
        if topla.gruplar(topla.oku(f)):
            topla.sezon_indir(d, "kupa", m.group(1), int(m.group(2)))
    print("Bitti, yeni indirilen sayfa:", d.indirilen, flush=True)


def indir(kademe, sezon, bekle, kupa=False):
    liste = [m for m in (kupa_hedefleri() if kupa else hedefler(kademe, sezon)) if not os.path.exists(yol(m)) and not os.path.exists(yol(m) + ".yok")]
    print(f"{len(liste)} sayfa indirilecek (~{len(liste) * (bekle + 0.6) / 3600:.1f} saat)", flush=True)
    hata = kesinti = 0
    for i, m in enumerate(liste, 1):
        hedef = yol(m)
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        r = subprocess.run(["curl", "-sL", "--compressed", "-m", "60", "-A", UA, "-w", "\n%{http_code}", URL.format(m)],
                           capture_output=True)
        govde, _, kod = r.stdout.rpartition(b"\n")
        kod = kod.decode().strip()
        if kod == "200" and len(govde) > 20000 and (b"rptKadrolar" in govde or b"lblOrganizasyonAdi" in govde):
            with gzip.open(hedef + ".tmp", "wb") as g:
                g.write(govde)
            os.replace(hedef + ".tmp", hedef)
            hata = 0
        elif kod == "200" and len(govde) > 15000 and b"tff.org" in govde.lower():
            # TFF normal sayfa döndü ama kadro yok (hükmen / oynanmamış maç / boş numara): işaretle, bir daha deneme
            open(hedef + ".yok", "w").close()
            hata = 0
        else:
            hata += 1
            with open(os.path.join(KOK, "hatalar.log"), "a") as f:
                f.write(f"{time.strftime('%F %T')} oyuncu {kod} {m}\n")
            if hata >= 10:
                # internet ya da TFF kesintisi: durmak yerine 30 dk bekleyip yeniden dene (gözetimsiz çalışma); 12 saat sürerse dur
                kesinti += 1
                if kesinti > 24:
                    sys.exit("12 saattir art arda hata: durdum (aynı komut kaldığı yerden devam eder).")
                print(f"  art arda 10 hata (son kod {kod or 'bağlantı yok'}), 30 dk bekleniyor ({time.strftime('%H:%M')})", flush=True)
                time.sleep(1800)
                hata = 0
            time.sleep(30 * hata)
        if i % 200 == 0:
            print(f"  {i}/{len(liste)} {time.strftime('%H:%M')}", flush=True)
        time.sleep(bekle)
    print("Bitti.", flush=True)


KISI_HAM = os.path.join(KOK, "raw", "tff_kisi")
KISI_URL = "https://www.tff.org/Default.aspx?pageId=30&kisiId={}"


def kisi_yol(k):
    return os.path.join(KISI_HAM, str(k)[-2:].zfill(2), f"{k}.html.gz")


def kisi_indir(bekle):
    """TFF oyuncu sayfaları (doğum tarihi/yeri, uyruk, lisans): kadrolarda geçen kişiler, en çok maça çıkandan başlayarak."""
    c = sqlite3.connect(OYUNCU_DB)
    hedef_l = [k for (k,) in c.execute("SELECT kisi FROM kadro WHERE kisi IS NOT NULL GROUP BY kisi ORDER BY COUNT(*) DESC")]
    liste = [k for k in hedef_l if not os.path.exists(kisi_yol(k)) and not os.path.exists(kisi_yol(k) + ".yok")]
    print(f"{len(liste)}/{len(hedef_l)} oyuncu sayfası indirilecek (~{len(liste) * (bekle + 0.8) / 3600:.1f} saat)", flush=True)
    hata = kesinti = 0
    for i, k in enumerate(liste, 1):
        yol_ = kisi_yol(k)
        os.makedirs(os.path.dirname(yol_), exist_ok=True)
        r = subprocess.run(["curl", "-sL", "--compressed", "-m", "60", "-A", UA, "-w", "\n%{http_code}", KISI_URL.format(k)], capture_output=True)
        govde, _, kod = r.stdout.rpartition(b"\n")
        kod = kod.decode().strip()
        if kod == "200" and b"oyuncuBilgileri_lblAdi" in govde:
            with gzip.open(yol_ + ".tmp", "wb") as g:
                g.write(govde)
            os.replace(yol_ + ".tmp", yol_)
            hata = 0
        elif kod == "200" and len(govde) > 15000 and b"tff.org" in govde.lower():
            open(yol_ + ".yok", "w").close()   # TFF sayfası var ama oyuncu bilgisi yok
            hata = 0
        else:
            hata += 1
            with open(os.path.join(KOK, "hatalar.log"), "a") as f:
                f.write(f"{time.strftime('%F %T')} kisi {kod} {k}\n")
            if hata >= 10:
                kesinti += 1
                if kesinti > 24:
                    sys.exit("12 saattir art arda hata: durdum (aynı komut kaldığı yerden devam eder).")
                print(f"  art arda 10 hata (son kod {kod or 'bağlantı yok'}), 30 dk bekleniyor ({time.strftime('%H:%M')})", flush=True)
                time.sleep(1800)
                hata = 0
            time.sleep(30 * hata)
        if i % 200 == 0:
            print(f"  {i}/{len(liste)} {time.strftime('%H:%M')}", flush=True)
        time.sleep(bekle)
    print("Bitti.", flush=True)


# ---------------------------------------------------------------- ayıklama
def _dk(s):
    """'45+12.dk' -> ('45+12', 45, 12); '0.dk' -> (None, None, None)"""
    m = re.match(r"\s*(\d+)(?:\+(\d+))?\.?\s*dk", s or "")
    if not m or m.group(1) == "0":
        return None, None, None
    return m.group(0).replace(".dk", "").replace("dk", "").strip(" ."), int(m.group(1)), int(m.group(2) or 0)


def sayfa_oku(t):
    """Bir maç sayfasından sözlük: kadro, gol, kart, degisiklik, teknik, hakem."""
    out = collections.defaultdict(list)
    kisi = r'href="Default\.aspx\?pageId=30&(?:amp;)?kisiId=(\d+)"[^>]*>([^<]*)<'
    for taraf in (1, 2):
        g = f"grdTakim{taraf}_"
        for bolum, ilk11 in (("rptKadrolar", 1), ("rptYedekler", 0)):
            for no, kid, ad in re.findall(g + bolum + r'_ctl\d+_formaNo">([^<]*)</span>\s*<a[^>]*' + kisi[4:], t):
                out["kadro"].append((taraf, int(kid), topla.temiz(ad), (no.strip(" .") or None), ilk11))
        for kid, metin in re.findall(g + r'rptGoller_ctl\d+_lblGol"\s*' + kisi[0:0] + r'href="Default\.aspx\?pageId=30&(?:amp;)?kisiId=(\d+)"[^>]*>([^<]*)<', t):
            m = re.match(r"(.*),\s*(\d+(?:\+\d+)?)\.dk\s*\((\w)\)", topla.temiz(metin))
            if m:
                dk, d1, d2 = _dk(m.group(2) + ".dk")
                out["gol"].append((taraf, int(kid), m.group(1).strip(), dk, d1, d2, m.group(3)))
        for renk, kid, ad, dk in re.findall(g + r'rptKartlar_ctl\d+_k"[^>]*alt="([^"]*)"[^>]*/?>.*?' + kisi + r'.*?_d">([^<]*)<', t, re.S):
            out["kart"].append((taraf, int(kid), topla.temiz(ad), topla.temiz(renk), *_dk(dk)))
        cik = re.findall(g + r'rptCikanlar_ctl\d+_lblCikan"\s*' + kisi[0:0] + r'href="Default\.aspx\?pageId=30&(?:amp;)?kisiId=(\d+)"[^>]*>([^<]*)<.*?_oc">([^<]*)<', t, re.S)
        gir = re.findall(g + r'rptGirenler_ctl\d+_lblGiren"\s*' + kisi[0:0] + r'href="Default\.aspx\?pageId=30&(?:amp;)?kisiId=(\d+)"[^>]*>([^<]*)<.*?_og">([^<]*)<', t, re.S)
        for i in range(max(len(cik), len(gir))):
            c_ = cik[i] if i < len(cik) else (None, None, "")
            g_ = gir[i] if i < len(gir) else (None, None, "")
            dk = _dk(g_[2] or c_[2])
            out["degisiklik"].append((taraf, int(g_[0]) if g_[0] else None, topla.temiz(g_[1] or ""),
                                      int(c_[0]) if c_[0] else None, topla.temiz(c_[1] or ""), *dk))
        for aid, ad in re.findall(g + r'rptTeknikKadro_ctl\d+_lnkTeknikSorumlu" href="Default\.aspx\?pageId=219&(?:amp;)?antId=(\d+)"[^>]*>([^<]*)<', t):
            out["teknik"].append((taraf, int(aid), topla.temiz(ad)))
    for hid, metin in re.findall(r'lnkHakem" href="Default\.aspx\?pageId=72&(?:amp;)?hakemId=(\d+)"[^>]*>([^<]*)<', t):
        m = re.match(r"(.*?)\s*\((.*)\)\s*$", topla.temiz(metin))
        out["hakem"].append((int(hid), (m.group(1) if m else topla.temiz(metin)).strip(), m.group(2) if m else None))
    # 1990'ların başı: yedekler ilk 11'le aynı listede (bazen yanında 254 numaralı tek bir yedek): bir takımda 11'den fazla
    # ilk 11 oyuncusu varsa oyuna sonradan girenler, hâlâ fazlaysa 11'den büyük forma numaralılar yedektir
    for taraf in (1, 2):
        ilk = [k for k in out["kadro"] if k[0] == taraf and k[4]]
        if len(ilk) > 11:
            girenler = {d[1] for d in out["degisiklik"] if d[0] == taraf and d[1]}
            yedek = {k[1] for k in ilk if k[1] in girenler}
            if len(ilk) - len(yedek) > 11:
                yedek |= {k[1] for k in ilk if k[1] not in yedek and (k[3] or "").isdigit() and int(k[3]) > 11}
            out["kadro"] = [(k[0], k[1], k[2], k[3], 0 if k[0] == taraf and k[1] in yedek else k[4]) for k in out["kadro"]]
    stad = re.search(r'lnkStad"[^>]*>([^<]*)<', t)
    out["stad"] = topla.temiz(stad.group(1)) if stad else None
    # maç bilgisi (sezon sayfalarında listelenmeyen maçlar için: play-off, baraj, kupa, PAF...)
    g = lambda k: (lambda m: topla.temiz(m.group(1)) if m else None)(re.search(r'dtMacBilgisi_' + k + r'"[^>]*>([^<]*)<', t))
    takim = lambda n: re.search(r'dtMacBilgisi_lnkTakim' + n + r'" href="Default\.aspx\?pageId=28&(?:amp;)?kulupId=(\d+)">([^<]*)<', t)
    t1, t2 = takim("1"), takim("2")
    tarih = re.match(r"(\d+)\.(\d+)\.(\d{4})(?:\s*-\s*(\d+:\d+))?", g("lblTarih") or "")
    sayi = lambda s: int(s) if s and s.strip().isdigit() else None
    out["bilgi"] = (g("lblOrganizasyonAdi"), f"{tarih.group(3)}-{int(tarih.group(2)):02d}-{int(tarih.group(1)):02d}" if tarih else None,
                    tarih.group(4) if tarih else None,
                    int(t1.group(1)) if t1 else None, topla.temiz(t1.group(2)) if t1 else None,
                    int(t2.group(1)) if t2 else None, topla.temiz(t2.group(2)) if t2 else None,
                    sayi(g("lblTakim1Skor")), sayi(g("Label12")), g("lblKod"))
    return out


SEMA = """
CREATE TABLE kadro(mac TEXT, taraf INTEGER, kisi INTEGER, ad TEXT, forma TEXT, ilk11 INTEGER);
CREATE TABLE gol(mac TEXT, taraf INTEGER, kisi INTEGER, ad TEXT, dakika TEXT, dk INTEGER, ek INTEGER, tip TEXT);
CREATE TABLE kart(mac TEXT, taraf INTEGER, kisi INTEGER, ad TEXT, renk TEXT, dakika TEXT, dk INTEGER, ek INTEGER);
CREATE TABLE degisiklik(mac TEXT, taraf INTEGER, giren INTEGER, giren_ad TEXT, cikan INTEGER, cikan_ad TEXT, dakika TEXT, dk INTEGER, ek INTEGER);
CREATE TABLE teknik(mac TEXT, taraf INTEGER, kisi INTEGER, ad TEXT);
CREATE TABLE hakem(mac TEXT, kisi INTEGER, ad TEXT, gorev TEXT);
CREATE TABLE mac_bilgi(mac TEXT PRIMARY KEY, stad TEXT, organizasyon TEXT, tarih TEXT, saat TEXT,
  ev_tff INTEGER, ev_adi TEXT, dep_tff INTEGER, dep_adi TEXT, ev_gol INTEGER, dep_gol INTEGER, kod TEXT);
CREATE INDEX k1 ON kadro(kisi); CREATE INDEX k2 ON kadro(mac); CREATE INDEX g1 ON gol(kisi); CREATE INDEX g2 ON gol(mac);
CREATE INDEX c1 ON kart(kisi); CREATE INDEX c2 ON kart(mac);
"""


def ayikla():
    if os.path.exists(OYUNCU_DB):
        os.remove(OYUNCU_DB)
    c = sqlite3.connect(OYUNCU_DB)
    c.executescript(SEMA)
    n = 0
    for f in glob.glob(os.path.join(HAM, "*", "*.html.gz")):
        mac = os.path.basename(f)[:-8]
        with gzip.open(f, "rb") as g:
            t = g.read().decode("cp1254", "replace")   # TFF sayfalari Windows-1254
        o = sayfa_oku(t)
        for tablo, n_al in (("kadro", 5), ("gol", 7), ("kart", 7), ("degisiklik", 8), ("teknik", 3), ("hakem", 3)):
            c.executemany(f"INSERT INTO {tablo} VALUES(?{',?' * n_al})", [(mac, *r) for r in o[tablo]])
        c.execute("INSERT INTO mac_bilgi VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (mac, o["stad"], *o["bilgi"]))
        n += 1
    c.commit()
    say = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("kadro", "gol", "kart", "degisiklik", "teknik", "hakem")}
    print(n, "mac sayfasi ->", OYUNCU_DB, say)
    gol_uyum(c)


def seri_mi(tip, dk, ek):
    """Seri penaltı golü: S, ya da dakikasız / 90+30 ve sonrası P (TFF seri penaltıları bazen P diye yazıyor)."""
    return tip == "S" or (tip == "P" and (dk is None or (dk == 90 and (ek or 0) >= 30)))


def gol_uyum(c=None):
    """mac_bilgi.gol_uyum: gol listesi skorla tutuyor mu?
    tutuyor | 0-0 | yok (gol listesi yok) | hukmen (3-0 masa başı; sahadaki goller listede) | seri (skora seri penaltılar katılmış) | uyumsuz"""
    c = c or sqlite3.connect(OYUNCU_DB)
    if "gol_uyum" not in [r[1] for r in c.execute("PRAGMA table_info(mac_bilgi)")]:
        c.execute("ALTER TABLE mac_bilgi ADD COLUMN gol_uyum TEXT")
    # TFF bazen normal golü "K" (kendi kalesine) diye işaretliyor: atan oyuncu golün listelendiği takımın kadrosunda ve
    # skor ancak gol o takıma sayılınca tutuyor (ör. kadın 2021-22 Mengü 0-45 Esentepe). Böyle maçlarda K işareti F yapılır.
    K = collections.defaultdict(list)
    for mac, taraf, tip, dk, ek in c.execute("SELECT mac, taraf, tip, dk, ek FROM gol"):
        if not seri_mi(tip, dk, ek):
            K[mac].append((taraf, tip))
    duz = []
    for mac, eg, dg in c.execute("SELECT mac, ev_gol, dep_gol FROM mac_bilgi WHERE ev_gol IS NOT NULL").fetchall():
        l = K.get(mac, [])
        if any(t == "K" for _, t in l):
            liste = [sum(1 for x, _ in l if x == s_) for s_ in (1, 2)]
            normal = [sum(1 for x, t in l if (2 - x if t == "K" else x - 1) == s_) for s_ in (0, 1)]
            if liste == [eg, dg] and normal != [eg, dg]:
                duz.append(mac)
    c.executemany("UPDATE gol SET tip='F' WHERE mac=? AND tip='K'", [(m,) for m in duz])
    if duz:
        print(f"kendi kalesine işareti hatalı (skorla tutmuyor, normal gol yapıldı): {len(duz)} maç")
    gol, seri = collections.defaultdict(lambda: [0, 0]), collections.Counter()
    for mac, taraf, tip, dk, ek in c.execute("SELECT mac, taraf, tip, dk, ek FROM gol"):
        if seri_mi(tip, dk, ek):
            seri[mac] += 1
            continue
        gol[mac][(2 - taraf) if tip == "K" else (taraf - 1)] += 1
    say, guncel = collections.Counter(), []
    for mac, eg, dg in c.execute("SELECT mac, ev_gol, dep_gol FROM mac_bilgi").fetchall():
        g = gol.get(mac)
        if eg is None:
            d = None
        elif eg + dg == 0 and not g:
            d = "0-0"
        elif not g:
            d = "yok"
        elif g == [eg, dg]:
            d = "tutuyor"
        elif (eg, dg) in ((3, 0), (0, 3)):
            d = "hukmen"
        elif seri[mac] or (eg > g[0] and dg > g[1] and eg + dg - sum(g) >= 5):
            d = "seri"
        else:
            d = "uyumsuz"
        say[d] += 1
        guncel.append((d, mac))
    c.executemany("UPDATE mac_bilgi SET gol_uyum=? WHERE mac=?", guncel)
    c.commit()
    print("gol listesi / skor:", dict(say))


# TFF sezon sayfalarinda listelenmeyen maclar (1990-2007 numara boslugu): lig play-off/baraj ve ozel kupalar
EK_CSV = os.path.join(KOK, "tff_ek_maclar.csv")
OZEL_KUPA = {"cumhurbaşkanlığı kupası": "Cumhurbaşkanlığı Kupası", "başbakanlık kupası": "Başbakanlık Kupası",
             "atatürk kupası": "Atatürk Kupası", "süper kupa": "TFF Süper Kupa"}
EK_LIG = ("Lig B", "Türk Telekom Lig A", "1. Lig", "2. Lig", "3. Lig")
# 1996 Cumhurbaşkanlığı ve Başbakanlık kupaları Mart 1997'de oynandı: 1995-96 sezonunun kupaları
EK_SEZON = {"43261": "1995-1996", "43348": "1995-1996"}
EK_HARIC = {"51641": "1993-94 3. Lig: Hopaspor-Rize ligde zaten iki kez oynamış (3.10.1993, 13.3.1994); bu maçın niteliği belirsiz"}


def ek_maclar():
    import csv
    t = sqlite3.connect(TFF_DB)
    # (tff kulup no, sezon) -> {kademe: mac sayisi}; kademe -> lig adi
    kd = collections.defaultdict(collections.Counter)
    for k, sezon, kademe, n in t.execute("""SELECT k.tff_id, m.sezon, m.kademe, COUNT(*) FROM mac m JOIN kulup k ON k.id IN (m.ev_id, m.dep_id)
                                             WHERE m.asama='lig' GROUP BY 1,2,3"""):
        kd[(str(k), sezon)][kademe] += n
    lig_adi = dict(t.execute("SELECT kademe, lig FROM mac GROUP BY kademe"))
    var = {r[0] for r in t.execute("SELECT kaynak_id FROM mac WHERE kaynak='tff'")}
    satir, sorun = [], []
    for m in (l.strip() for l in open(os.path.join(KOK, "raw", "tff_mac_yoklama.txt"))):
        if not m or not os.path.exists(yol(m)) or m in var or m in EK_HARIC:
            continue
        with gzip.open(yol(m), "rb") as g:
            o = sayfa_oku(g.read().decode("cp1254", "replace"))
        org, tarih, saat, et, ea, dt, da, eg, dg, kod = o["bilgi"]
        org = (org or "").split(" (")[0].strip()
        ozel = OZEL_KUPA.get(org.replace("CumhurBaşkanlığı", "Cumhurbaşkanlığı").lower())
        if not ozel and org not in EK_LIG:
            continue
        if not (tarih and et and dt and eg is not None and dg is not None):
            sorun.append((m, org, "eksik bilgi"))
            continue
        y, ay = int(tarih[:4]), int(tarih[5:7])
        sezon = EK_SEZON.get(m) or (f"{y}-{y + 1}" if ay >= 7 else f"{y - 1}-{y}")
        # seri penaltilar: TFF skoru penaltilarla birlikte yaziyor; 90+30 ve sonrasindaki penalti golleri atistir
        sayi = {1: [0, 0], 2: [0, 0]}   # taraf -> [mac golu, seri penalti]
        for taraf, _, _, _, d1, d2, tip in o["gol"]:
            seri = tip in ("S",) or (tip == "P" and (d1 is None or (d1 == 90 and d2 >= 30)))   # dakikasiz penalti: seri (orn. 1995 Basbakanlik)
            hedef = (3 - taraf) if tip == "K" else taraf
            sayi[hedef][1 if seri else 0] += 1
        ep = dp = None
        durum = "MS"
        if sayi[1][1] or sayi[2][1]:
            if sayi[1][0] == sayi[2][0] and sayi[1][0] + sayi[1][1] == eg and sayi[2][0] + sayi[2][1] == dg:
                eg, dg, ep, dp = sayi[1][0], sayi[2][0], sayi[1][1], sayi[2][1]
            else:
                sorun.append((m, org, f"penalti ayrilamadi {eg}-{dg} {sayi}"))
                continue
        elif o["gol"] and (sayi[1][0], sayi[2][0]) != (eg, dg):
            if sayi[1][0] == sayi[2][0] and min(eg, dg) - sayi[1][0] >= 3 and abs(eg - dg) <= 2:
                # seri penaltilar listede yok ama skor penaltilarla yazilmis (orn. 5-4, listede 1-1)
                eg, dg, ep, dp = sayi[1][0], sayi[2][0], eg - sayi[1][0], dg - sayi[2][0]
            elif {eg, dg} == {0, 3}:
                durum = "Hük."   # skor 3-0 hukmen, sahadaki goller farkli
            else:
                sorun.append((m, org, f"gol listesi skorla tutmuyor {eg}-{dg} {sayi}"))
        if ozel:
            yarisma, lig, kademe = "ozel_kupa", ozel, ""
        else:
            ortak = kd[(str(et), sezon)].keys() & kd[(str(dt), sezon)].keys()
            if len(ortak) != 1:   # iki takim ayni kademede degilse: ev sahibinin kademesi (baraj)
                ortak = kd[(str(et), sezon)].keys() or kd[(str(dt), sezon)].keys()
            if not ortak:
                sorun.append((m, org, "kademe bulunamadi"))
                continue
            kademe = min(ortak)
            yarisma, lig = "lig", lig_adi[kademe]
        satir.append(dict(kaynak_id=m, yarisma=yarisma, lig=lig, kademe=kademe, sezon=sezon, organizasyon=org, tarih=tarih,
                          saat=saat or "", ev_tff=et, ev_adi=topla.temiz(ea), dep_tff=dt, dep_adi=topla.temiz(da),
                          ev_gol=eg, dep_gol=dg, ev_pen="" if ep is None else ep, dep_pen="" if dp is None else dp, durum=durum))
    satir.sort(key=lambda r: (r["tarih"], int(r["kaynak_id"])))
    with open(EK_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(satir[0]))
        w.writeheader()
        w.writerows(satir)
    print(len(satir), "mac ->", EK_CSV, dict(collections.Counter((r["yarisma"], r["lig"]) for r in satir)))
    for s in sorun:
        print("  sorun:", *s)


def durum():
    c = sqlite3.connect(TFF_DB)
    for kd, n in c.execute("SELECT kademe, COUNT(*) FROM mac WHERE kaynak='tff' AND kaynak_id<>'' AND ev_gol IS NOT NULL GROUP BY 1"):
        var = sum(os.path.exists(yol(m)) for m in hedefler(kd))
        print(f"kademe {kd}: {var}/{n}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("komut", choices=["indir", "kupa", "kisi_ayikla", "ayikla", "durum", "ek", "uyum", "kisi"])
    p.add_argument("--kademe", type=int)
    p.add_argument("--sezon")
    p.add_argument("--bekle", type=float, default=2.0)
    a = p.parse_args()
    {"indir": lambda: indir(a.kademe, a.sezon, a.bekle), "kupa": lambda: (kupa_gruplari(), indir(None, None, a.bekle, kupa=True)), "kisi_ayikla": kisi_ayikla, "ayikla": ayikla, "durum": durum, "ek": ek_maclar, "uyum": gol_uyum, "kisi": lambda: kisi_indir(a.bekle)}[a.komut]()

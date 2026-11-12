"""TFF maç detay sayfalarından kadro, gol, kart, oyuncu değişikliği, teknik direktör ve hakem verisi.

  python3 oyuncu.py indir [--kademe 1] [--sezon 2015-2016] [--bekle 2]   # raw/tff_mac/<..>/<macId>.html.gz (kaldığı yerden)
  python3 oyuncu.py ayikla                                               # raw/oyuncu.db
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


def indir(kademe, sezon, bekle):
    liste = [m for m in hedefler(kademe, sezon) if not os.path.exists(yol(m)) and not os.path.exists(yol(m) + ".yok")]
    print(f"{len(liste)} sayfa indirilecek (~{len(liste) * (bekle + 0.6) / 3600:.1f} saat)", flush=True)
    hata = 0
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
                sys.exit("Art arda 10 hata: TFF erişimi kesmiş olabilir, durdum (kaldığı yerden devam eder).")
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
    # 1990'ların başı: yedekler ayrı listelenmemiş (hepsi "kadro"da); oyuna sonradan girenler ilk 11 değildir
    for taraf in (1, 2):
        if not any(k[0] == taraf and k[4] == 0 for k in out["kadro"]):
            girenler = {d[1] for d in out["degisiklik"] if d[0] == taraf and d[1]}
            out["kadro"] = [(k[0], k[1], k[2], k[3], 0 if k[0] == taraf and k[1] in girenler else k[4]) for k in out["kadro"]]
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


def durum():
    c = sqlite3.connect(TFF_DB)
    for kd, n in c.execute("SELECT kademe, COUNT(*) FROM mac WHERE kaynak='tff' AND kaynak_id<>'' AND ev_gol IS NOT NULL GROUP BY 1"):
        var = sum(os.path.exists(yol(m)) for m in hedefler(kd))
        print(f"kademe {kd}: {var}/{n}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("komut", choices=["indir", "ayikla", "durum"])
    p.add_argument("--kademe", type=int)
    p.add_argument("--sezon")
    p.add_argument("--bekle", type=float, default=2.0)
    a = p.parse_args()
    {"indir": lambda: indir(a.kademe, a.sezon, a.bekle), "ayikla": ayikla, "durum": durum}[a.komut]()

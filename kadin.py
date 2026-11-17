"""Kadın futbol ligleri (TFF arşivi pageID=848, 2006-07'den bugüne): sezon/hafta sayfaları ve maç sayfaları.

  python3 kadin.py liste     # sezon, grup ve hafta sayfaları -> raw/tff_kadin/<kaynak>_<sezon>_<pageID>/ (kaldığı yerden)
  python3 kadin.py kur       # raw/tff_kadin -> raw/kadin.db (topla.py'nin ayrıştırıcısıyla; erkek verisinden ayrı)
  python3 kadin.py mac       # maç sayfaları -> raw/tff_kadin_mac/<son iki hane>/<macId>.html.gz (kaldığı yerden)
  python3 kadin.py ayikla    # maç sayfaları -> raw/kadin_detay.db (kadro, gol, kart...)
  python3 kadin.py site      # raw/kadin.db + raw/kadin_detay.db -> docs/data/kadin/ (kadin_site.py)
  python3 kadin.py durum

Erkek ligleriyle karışmasın diye her şey ayrı klasör ve veritabanında. Kadın kulüpleri erkek kulüpleriyle aynı TFF
kulüp numarasını taşıyabilir.
"""
import gzip, os, re, sqlite3, subprocess, sys, time

import topla

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "tff_kadin")
MAC_HAM = os.path.join(KOK, "raw", "tff_kadin_mac")
DB = os.path.join(KOK, "raw", "kadin.db")

# (kaynak, sezon, pageID): kaynak = lig adı kısa kodu; kademe sezon içindeki sıraya göre (en üst lig 1)
SEZONLAR = [
    ("k1", "2006-2007", 627), ("k1", "2007-2008", 424), ("k2", "2007-2008", 683),
    ("k1", "2008-2009", 836), ("k1", "2009-2010", 933), ("k2", "2009-2010", 936),
    ("k1", "2010-2011", 1066), ("kb", "2010-2011", 1068), ("k1", "2011-2012", 1179), ("k2", "2011-2012", 1180),
    ("k1", "2012-2013", 1252), ("k2", "2012-2013", 1253), ("k1", "2013-2014", 1280), ("k2", "2013-2014", 1281),
    ("k1", "2014-2015", 1326), ("k2", "2014-2015", 1327), ("k3", "2014-2015", 1328),
    ("k1", "2015-2016", 1390), ("k2", "2015-2016", 1391), ("k3", "2015-2016", 1392),
    ("k1", "2016-2017", 1426), ("k2", "2016-2017", 1427), ("k3", "2016-2017", 1428),
    ("k1", "2017-2018", 1448), ("k2", "2017-2018", 1449), ("k3", "2017-2018", 1450),
    ("k1", "2018-2019", 1484), ("k2", "2018-2019", 1485), ("k3", "2018-2019", 1486),
    ("k1", "2019-2020", 1497), ("k2", "2019-2020", 1498), ("k3", "2019-2020", 1499),
    ("k1", "2020-2021", 1533),
    ("ks", "2021-2022", 1581), ("k2", "2021-2022", 1582), ("k3", "2021-2022", 1588),
    ("ks", "2022-2023", 1623), ("k1", "2022-2023", 1624), ("k2", "2022-2023", 1625), ("k3", "2022-2023", 1626),
    ("ks", "2023-2024", 1653), ("k1", "2023-2024", 1654), ("k2", "2023-2024", 1655), ("k3", "2023-2024", 1656),
    ("ks", "2024-2025", 1735), ("k1", "2024-2025", 1736), ("k2", "2024-2025", 1737), ("k3", "2024-2025", 1738),
    ("ks", "2025-2026", 1781), ("k1", "2025-2026", 1782), ("k2", "2025-2026", 1783), ("k3", "2025-2026", 1792),
]
LIG_AD = {"ks": "Kadın Futbol Süper Ligi", "k1": "Kadınlar 1. Ligi", "k2": "Kadınlar 2. Ligi", "k3": "Kadınlar 3. Ligi", "kb": "Kadınlar Bölgesel Ligi"}


def kademe(kaynak, sezon):
    """Süper Lig 2021-22'de kuruldu; 1. Lig o zamana kadar en üst lig, 2022-23'ten sonra ikinci lig."""
    yil = int(sezon[:4])
    if kaynak == "ks":
        return 1
    if kaynak == "kb":
        return 3
    n = int(kaynak[1])
    if yil >= 2022:
        return n + 1
    if yil == 2021:
        return n   # 2021-22: Süper Lig, 2. Lig, 3. Lig (1. Lig yok)
    return n


def liste():
    topla.HAM = HAM
    d = topla.Indirici()
    for kaynak, sezon, pid in SEZONLAR:
        topla.sezon_indir(d, kaynak, sezon, pid)
    print("Bitti, yeni indirilen sayfa:", d.indirilen)


def kur():
    topla.LIG.update(LIG_AD)
    topla.kademe = lambda kaynak, yil: kademe(kaynak, f"{yil}-{yil + 1}")
    topla.kur(DB, HAM)
    c = sqlite3.connect(DB)
    for r in c.execute("SELECT sezon, lig, COUNT(*), SUM(ev_gol IS NOT NULL) FROM mac GROUP BY 1, 2 ORDER BY 1, 2"):
        print(*r)
    print("toplam:", c.execute("SELECT COUNT(*) FROM mac").fetchone()[0])


def mac_yol(m):
    return os.path.join(MAC_HAM, str(m)[-2:].zfill(2), f"{m}.html.gz")


def mac():
    c = sqlite3.connect(DB)
    hedef = [m for (m,) in c.execute("SELECT kaynak_id FROM mac WHERE ev_gol IS NOT NULL ORDER BY sezon DESC, kademe")]
    liste_ = [m for m in hedef if not os.path.exists(mac_yol(m)) and not os.path.exists(mac_yol(m) + ".yok")]
    print(f"{len(liste_)}/{len(hedef)} maç sayfası indirilecek", flush=True)
    hata = 0
    for i, m in enumerate(liste_, 1):
        os.makedirs(os.path.dirname(mac_yol(m)), exist_ok=True)
        r = subprocess.run(["curl", "-sL", "--compressed", "-m", "60", "-A", topla.UA, "-w", "\n%{http_code}",
                            f"https://www.tff.org/Default.aspx?pageID=29&macId={m}"], capture_output=True)
        govde, _, kod = r.stdout.rpartition(b"\n")
        if kod.decode().strip() == "200" and len(govde) > 20000 and (b"rptKadrolar" in govde or b"lblOrganizasyonAdi" in govde):
            with gzip.open(mac_yol(m), "wb") as g:
                g.write(govde)
            hata = 0
        elif kod.decode().strip() == "200" and len(govde) > 15000:
            open(mac_yol(m) + ".yok", "w").close()
        else:
            hata += 1
            if hata >= 10:
                print("  art arda 10 hata, 30 dk bekleniyor", time.strftime("%H:%M"), flush=True)
                time.sleep(1800)
                hata = 0
            time.sleep(30 * hata)
        if i % 200 == 0:
            print(f"  {i}/{len(liste_)} {time.strftime('%H:%M')}", flush=True)
        time.sleep(2)
    print("Bitti.", flush=True)


DETAY_DB = os.path.join(KOK, "raw", "kadin_detay.db")


def ayikla():
    """Maç sayfaları -> raw/kadin_detay.db (oyuncu.py'nin ayrıştırıcısıyla: kadro, gol, kart, değişiklik, teknik, hakem)."""
    import oyuncu
    oyuncu.HAM, oyuncu.OYUNCU_DB = MAC_HAM, DETAY_DB
    oyuncu.ayikla()


def durum():
    if os.path.exists(DB):
        c = sqlite3.connect(DB)
        n = c.execute("SELECT COUNT(*) FROM mac WHERE ev_gol IS NOT NULL").fetchone()[0]
        var = sum(os.path.exists(mac_yol(m)) for (m,) in c.execute("SELECT kaynak_id FROM mac WHERE ev_gol IS NOT NULL"))
        print(f"maç sayfası: {var}/{n}")


if __name__ == "__main__":
    {"liste": liste, "kur": kur, "mac": mac, "ayikla": ayikla, "site": lambda: __import__("kadin_site").aktar(), "durum": durum}[sys.argv[1]]()

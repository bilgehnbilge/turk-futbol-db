"""Profesyonelliğe Geçiş Ligi (eski Bölgesel Amatör Lig; TFF arşivi pageID=1290, 2010-11'den bugüne): sezon/grup/hafta
sayfaları ve maç sayfaları. Erkek profesyonel liglerinin verisine (raw/tff, tff.db, futbol.db) karışmaz; siteye
eklenirken 5. seviye olarak bağlanacak.

  python3 bal.py liste     # sezon, grup ve hafta sayfaları -> raw/tff_bal/bal_<sezon>_<pageID>/ (kaldığı yerden)
  python3 bal.py kur       # raw/tff_bal -> raw/bal.db (topla.py'nin ayrıştırıcısıyla)
  python3 bal.py mac       # maç sayfaları -> raw/tff_bal_mac/<son iki hane>/<macId>.html.gz (kaldığı yerden)
  python3 bal.py ayikla    # maç sayfaları -> raw/bal_detay.db (kadro, gol, kart, değişiklik, teknik, hakem)
  python3 bal.py durum
  python3 bal.py hepsi     # liste + kur + mac + ayikla sırayla (gözetimsiz)
"""
import gzip, os, sqlite3, subprocess, sys, time

import topla

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "tff_bal")
MAC_HAM = os.path.join(KOK, "raw", "tff_bal_mac")
DB = os.path.join(KOK, "raw", "bal.db")
DETAY_DB = os.path.join(KOK, "raw", "bal_detay.db")

# arşiv sayfasındaki sezonlar (2026-11-17, pageID=1290)
SEZONLAR = [("2010-2011", 1107), ("2011-2012", 1178), ("2012-2013", 1241), ("2013-2014", 998), ("2014-2015", 1325),
            ("2015-2016", 1389), ("2016-2017", 1418), ("2017-2018", 1447), ("2018-2019", 1474), ("2019-2020", 1500),
            ("2020-2021", 1535), ("2021-2022", 1592), ("2022-2023", 1627), ("2023-2024", 1652), ("2024-2025", 1739),
            ("2025-2026", 1793)]
LIG_AD = {"bal": "Profesyonelliğe Geçiş Ligi"}


def liste():
    topla.HAM = HAM
    d = topla.Indirici()
    for sezon, pid in SEZONLAR:
        topla.sezon_indir(d, "bal", sezon, pid)
    print("Bitti, yeni indirilen sayfa:", d.indirilen, flush=True)


def kur():
    topla.LIG.update(LIG_AD)
    topla.kademe = lambda kaynak, yil: 5
    topla.kur(DB, HAM)
    c = sqlite3.connect(DB)
    for r in c.execute("SELECT sezon, COUNT(DISTINCT grup), COUNT(*), SUM(ev_gol IS NOT NULL) FROM mac GROUP BY 1 ORDER BY 1"):
        print(*r)
    print("toplam:", c.execute("SELECT COUNT(*) FROM mac").fetchone()[0], flush=True)


def mac_yol(m):
    return os.path.join(MAC_HAM, str(m)[-2:].zfill(2), f"{m}.html.gz")


def mac():
    c = sqlite3.connect(DB)
    hedef = [m for (m,) in c.execute("SELECT kaynak_id FROM mac WHERE ev_gol IS NOT NULL AND kaynak_id<>'' ORDER BY sezon DESC")]
    liste_ = [m for m in hedef if not os.path.exists(mac_yol(m)) and not os.path.exists(mac_yol(m) + ".yok")]
    print(f"{len(liste_)}/{len(hedef)} maç sayfası indirilecek (~{len(liste_) * 2.6 / 3600:.0f} saat)", flush=True)
    hata = 0
    for i, m in enumerate(liste_, 1):
        os.makedirs(os.path.dirname(mac_yol(m)), exist_ok=True)
        r = subprocess.run(["curl", "-sL", "--compressed", "-m", "60", "-A", topla.UA, "-w", "\n%{http_code}",
                            f"https://www.tff.org/Default.aspx?pageID=29&macId={m}"], capture_output=True)
        govde, _, kod = r.stdout.rpartition(b"\n")
        kod = kod.decode().strip()
        if kod == "200" and len(govde) > 20000 and (b"rptKadrolar" in govde or b"lblOrganizasyonAdi" in govde):
            with gzip.open(mac_yol(m) + ".tmp", "wb") as g:
                g.write(govde)
            os.replace(mac_yol(m) + ".tmp", mac_yol(m))
            hata = 0
        elif kod == "200" and len(govde) > 15000:
            open(mac_yol(m) + ".yok", "w").close()
            hata = 0
        else:
            hata += 1
            if hata >= 10:
                print("  art arda 10 hata, 30 dk bekleniyor", time.strftime("%H:%M"), flush=True)
                time.sleep(1800)
                hata = 0
            time.sleep(30 * hata)
        if i % 500 == 0:
            print(f"  {i}/{len(liste_)} {time.strftime('%H:%M')}", flush=True)
        time.sleep(2)
    print("Bitti.", flush=True)


def ayikla():
    import oyuncu
    oyuncu.HAM, oyuncu.OYUNCU_DB = MAC_HAM, DETAY_DB
    oyuncu.ayikla()


def durum():
    if os.path.exists(DB):
        c = sqlite3.connect(DB)
        n = c.execute("SELECT COUNT(*) FROM mac WHERE ev_gol IS NOT NULL").fetchone()[0]
        var = sum(os.path.exists(mac_yol(m)) for (m,) in c.execute("SELECT kaynak_id FROM mac WHERE ev_gol IS NOT NULL"))
        print(f"maç: {c.execute('SELECT COUNT(*) FROM mac').fetchone()[0]}, maç sayfası: {var}/{n}")
    else:
        print("raw/bal.db yok; sezon sayfaları:", sum(len(f) for _, _, f in os.walk(HAM)) if os.path.isdir(HAM) else 0)


def hepsi():
    liste(); kur(); mac(); ayikla()


if __name__ == "__main__":
    {"liste": liste, "kur": kur, "mac": mac, "ayikla": ayikla, "durum": durum, "hepsi": hepsi}[sys.argv[1]]()

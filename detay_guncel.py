"""Güncel sezonun maç ayrıntıları (kadro, gol, kart, değişiklik, teknik, hakem) ve yeni oyuncuların kişi sayfaları,
artımlı: yalnız veritabanında olmayan (ya da son 30 günde kadrosuz kalmış) maçların sayfası indirilir ve o maçın satırları
yeniden yazılır. Tam ayıklama (oyuncu.py ayikla) bütün ham sayfaları ister; bu betik ham sayfa olmadan da çalışır
(GitHub Actions: girdiler.py al ile Releases'ten gelen veritabanları üzerinde).

  python3 detay_guncel.py              # erkek (1-4. lig), Profesyonelliğe Geçiş Ligi, kadın ligleri, kişi sayfaları
  python3 detay_guncel.py --sezon 2026-2027

Kadın liglerinin güncel sezonu (skorlar) da burada yenilenir: kadin.py guncel + yalnız güncel sezonu kur.
"""
import argparse, datetime, gzip, os, sqlite3, subprocess, time

import topla

KOK = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(KOK, "raw")
MAC_URL = "https://www.tff.org/Default.aspx?pageID=29&macId={}"
HUKMEN = ("Hük.", "Çifte H")


def _curl(url):
    r = subprocess.run(["curl", "-sL", "--compressed", "-m", "60", "-A", topla.UA, "-w", "\n%{http_code}", url], capture_output=True)
    govde, _, kod = r.stdout.rpartition(b"\n")
    return govde, kod.decode().strip()


def mac_sayfasi(m, hedef):
    """'var' (kaydedildi), 'yok' (TFF sayfası var ama kadro yok) ya da 'hata'."""
    govde, kod = _curl(MAC_URL.format(m))
    if kod == "200" and len(govde) > 20000 and (b"rptKadrolar" in govde or b"lblOrganizasyonAdi" in govde):
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        with gzip.open(hedef + ".tmp", "wb") as g:
            g.write(govde)
        os.replace(hedef + ".tmp", hedef)
        return "var"
    if kod == "200" and len(govde) > 15000:
        return "yok"
    return "hata"


def detay(etiket, db, maclar, yol_, gun=30, en_cok=1500, bekle=2.0):
    """maclar: [(TFF maç no, tarih, durum)] (skoru olan). db: oyuncu.py SEMA'sındaki ayrıntı veritabanı."""
    import oyuncu
    if not os.path.exists(db):
        print(f"{etiket}: {db} yok, atlandı", flush=True)
        return 0
    c = sqlite3.connect(db)
    kadro = dict(c.execute("SELECT b.mac, COUNT(k.mac) FROM mac_bilgi b LEFT JOIN kadro k ON k.mac=b.mac GROUP BY b.mac"))
    sinir = (datetime.date.today() - datetime.timedelta(days=gun)).isoformat()
    hedef = []
    for m, tarih, durum in maclar:
        m = str(m)
        if not m:
            continue
        if m not in kadro:
            hedef.append(m)
        elif kadro[m] == 0 and tarih and tarih >= sinir and (durum or "") not in HUKMEN:
            hedef.append(m)   # TFF kadroyu sonradan giriyor
    hedef = hedef[:en_cok]
    print(f"{etiket}: {len(hedef)} maç sayfası indirilecek", flush=True)
    yazilan = hata = 0
    for i, m in enumerate(hedef, 1):
        y = yol_(m)
        if os.path.exists(y) and kadro.get(m, -1) != 0:
            durum = "var"   # yerelde zaten inmiş
        else:
            durum = mac_sayfasi(m, y)
            time.sleep(bekle)
        if durum == "hata":
            hata += 1
            if hata >= 10:
                print(f"  {etiket}: art arda 10 hata, durdum ({i}/{len(hedef)})", flush=True)
                break
            time.sleep(10 * hata)
            continue
        hata = 0
        if durum != "var":
            continue
        o = oyuncu.sayfa_oku(gzip.open(y).read().decode("cp1254", "replace"))
        for tablo in ("kadro", "gol", "kart", "degisiklik", "teknik", "hakem", "mac_bilgi"):
            c.execute(f"DELETE FROM {tablo} WHERE mac=?", (m,))
        for tablo, n_al in (("kadro", 5), ("gol", 7), ("kart", 7), ("degisiklik", 8), ("teknik", 3), ("hakem", 3)):
            c.executemany(f"INSERT INTO {tablo} VALUES(?{',?' * n_al})", [(m, *r) for r in o[tablo]])
        sutun = [r[1] for r in c.execute("PRAGMA table_info(mac_bilgi)")]
        c.execute(f"INSERT INTO mac_bilgi({','.join(sutun[:12])}) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (m, o["stad"], *o["bilgi"]))
        yazilan += 1
        if i % 200 == 0:
            c.commit()
            print(f"  {i}/{len(hedef)} {time.strftime('%H:%M')}", flush=True)
    c.commit()
    if yazilan:
        oyuncu.gol_uyum(c)
        c.commit()
    print(f"{etiket}: {yazilan} maç ayrıntısı yazıldı", flush=True)
    return yazilan


def kisi(dbs, en_cok=600, bekle=2.0):
    """Kadrolarda geçip raw/kisi.db'de olmayan oyuncuların TFF kişi sayfaları (doğum tarihi/yeri, uyruk). Her çalışmada en
    çok en_cok sayfa (~2,5 sn/sayfa): eksikler (ör. BAL oyuncuları) çalışmalara yayılır. Sıra: dbs sırası, en çok maça çıkan önce."""
    import oyuncu
    if not os.path.exists(oyuncu.KISI_DB):
        print("kişi: kisi.db yok, atlandı", flush=True)
        return 0
    k = sqlite3.connect(oyuncu.KISI_DB)
    k.execute("CREATE TABLE IF NOT EXISTS kisi_yok(kisi INTEGER PRIMARY KEY)")   # sayfası boş çıkanlar: bir daha denenmez
    var = {r for (r,) in k.execute("SELECT kisi FROM kisi UNION SELECT kisi FROM kisi_yok")}
    hedef = []
    for db in dbs:
        if os.path.exists(db):
            hedef += [x for (x,) in sqlite3.connect(db).execute(
                "SELECT kisi FROM kadro WHERE kisi IS NOT NULL GROUP BY kisi ORDER BY COUNT(*) DESC") if x not in var]
    hedef = list(dict.fromkeys(hedef))[:en_cok]
    print(f"kişi: {len(hedef)} oyuncu sayfası indirilecek", flush=True)
    n = hata = 0
    for x in hedef:
        y = oyuncu.kisi_yol(x)
        if os.path.exists(y):
            t = gzip.open(y).read()
        else:
            t, kod = _curl(oyuncu.KISI_URL.format(x))
            time.sleep(bekle)
            if kod != "200":
                hata += 1
                if hata >= 10:
                    print("  kişi: art arda 10 hata, durdum", flush=True)
                    break
                continue
            hata = 0
            if b"oyuncuBilgileri_lblAdi" in t:
                os.makedirs(os.path.dirname(y), exist_ok=True)
                with gzip.open(y, "wb") as g:
                    g.write(t)
        t = t.decode("cp1254", "replace")
        if "oyuncuBilgileri_lblAdi" not in t:
            k.execute("INSERT OR IGNORE INTO kisi_yok VALUES(?)", (x,))
            continue
        k.execute("INSERT OR REPLACE INTO kisi VALUES(?,?,?,?,?)", oyuncu.kisi_oku(x, t))
        n += 1
    k.commit()
    print(f"kişi: {n} oyuncu eklendi", flush=True)
    return n


def kadin_guncel():
    """Kadın liglerinin süren sezonu: lig sayfaları baştan, kadin.db'de yalnız o sezon yeniden kurulur."""
    import kadin
    if not os.path.exists(kadin.DB):
        print("kadın: kadin.db yok, atlandı", flush=True)
        return
    eski = topla.HAM, topla.kademe, dict(topla.LIG)
    try:
        klasorler = kadin.guncel()
        if klasorler:
            kadin.kur(sadece=klasorler)
    finally:   # kadin.py topla'nın genel ayarlarını değiştiriyor
        topla.HAM, topla.kademe = eski[0], eski[1]
        topla.LIG.clear(); topla.LIG.update(eski[2])


def main(sezon):
    import bal, kadin, oyuncu
    t = sqlite3.connect(os.path.join(RAW, "tff.db"))
    detay("erkek", oyuncu.OYUNCU_DB, t.execute(
        "SELECT kaynak_id, tarih, NULL FROM mac WHERE kaynak='tff' AND sezon=? AND ev_gol IS NOT NULL ORDER BY tarih", (sezon,)).fetchall(), oyuncu.yol)
    if os.path.exists(bal.DB):
        detay("BAL", bal.DETAY_DB, sqlite3.connect(bal.DB).execute(
            "SELECT kaynak_id, tarih, NULL FROM mac WHERE sezon=? AND ev_gol IS NOT NULL ORDER BY tarih", (sezon,)).fetchall(), bal.mac_yol)
    try:
        kadin_guncel()
    except (Exception, SystemExit) as e:
        print("Kadın ligleri güncellenemedi:", e, flush=True)
    if os.path.exists(kadin.DB):
        detay("kadın", kadin.DETAY_DB, sqlite3.connect(kadin.DB).execute(
            "SELECT kaynak_id, tarih, durum FROM mac WHERE sezon=? AND ev_gol IS NOT NULL ORDER BY tarih", (sezon,)).fetchall(), kadin.mac_yol)
    kisi([oyuncu.OYUNCU_DB, bal.DETAY_DB, kadin.DETAY_DB])


if __name__ == "__main__":
    import guncelle
    p = argparse.ArgumentParser()
    p.add_argument("--sezon", default=guncelle.simdiki_sezon())
    main(p.parse_args().sezon)

"""Site verisini üreten ama depoya girmeyen yerel girdiler (maç ayrıntıları, kadın ligleri, kişi bilgileri...) GitHub
Releases'te ("veritabani" sürümü, girdiler.tar.gz) tutulur. Bot (guncelle.py) her çalışmada indirir, güncel sezonu
artımlı günceller ve geri yükler; böylece güncelleme hiçbir bilgisayara bağlı kalmaz.

  python3 girdiler.py al      # Releases'ten indir, raw/ altına aç (yerelde DİKKAT: yereldeki dosyaların üzerine yazar)
  python3 girdiler.py yukle   # raw/ altındaki girdileri paketleyip Releases'e yükle (yerelde ayıklama/indirme sonrası)
  python3 girdiler.py liste

Yerelde tam ayıklama (oyuncu.py ayikla, kadin.py kur...) yaptıktan sonra `yukle` çalıştırılmalı; yoksa bot eski
girdilerle çalışır ve sitedeki yeni bilgiyi geri alır.
"""
import os, subprocess, sys, tarfile

KOK = os.path.dirname(os.path.abspath(__file__))
SURUM = "veritabani"
PAKET = "girdiler.tar.gz"
# raw/ altındaki yollar
GIRDILER = ["oyuncu.db", "bal_detay.db", "kisi.db", "kadin.db", "kadin_detay.db", "kadin_kupa_eslesme.json",
            "uefa_kadin", "mackolik_td/ek.json", "mackolik_td/takim_no.json",
            "mackolik_kadro", "rsssf_eski/eski.json"]   # son ikisi: 1959-91 Süper Lig kadroları ve 1959 öncesi bölümü


def yukle():
    yol = os.path.join(KOK, PAKET)
    with tarfile.open(yol, "w:gz", compresslevel=6) as t:
        for g in GIRDILER:
            p = os.path.join(KOK, "raw", g)
            if os.path.exists(p):
                t.add(p, arcname=g)
            else:
                print("yok, atlandı:", g)
    print(f"{PAKET}: {os.path.getsize(yol) / 1e6:.0f} MB", flush=True)
    subprocess.run(["gh", "release", "upload", SURUM, yol, "--clobber"], cwd=KOK, check=True)
    os.remove(yol)


def al():
    yol = os.path.join(KOK, PAKET)
    r = subprocess.run(["gh", "release", "download", SURUM, "-p", PAKET, "-O", yol, "--clobber"], cwd=KOK)
    if r.returncode != 0:
        print("girdiler.tar.gz indirilemedi; ayrıntılar güncellenmeyecek", flush=True)
        return False
    with tarfile.open(yol) as t:
        t.extractall(os.path.join(KOK, "raw"), filter="data")
    os.remove(yol)
    print("girdiler açıldı:", ", ".join(g for g in GIRDILER if os.path.exists(os.path.join(KOK, "raw", g))), flush=True)
    return True


if __name__ == "__main__":
    {"al": al, "yukle": yukle, "liste": lambda: print("\n".join(GIRDILER))}[sys.argv[1]]()

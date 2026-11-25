#!/usr/bin/env python3
"""Yerel ham veriyi (raw/ ve futbol.db) bir yedek klasörüne yazar; ör. Google Drive masaüstü uygulamasının klasörü.

  python3 yedekle.py "<hedef klasör>"          # ör. ~/Library/CloudStorage/GoogleDrive-.../My Drive/turk-futbol-db-yedek
  python3 yedekle.py "<hedef klasör>" --liste  # yalnız neyin değiştiğini göster, yazma

raw/ altındaki her klasör tek bir .tar dosyası olur (288 bin küçük dosyayı tek tek eşitlemek Drive'ı çok yavaşlatır);
dosyalar zaten gzip'li olduğundan yeniden sıkıştırılmaz. Veritabanları (.db) sqlite yedekleme komutuyla tutarlı kopyalanır.
Yalnız son yedekten sonra değişen klasör ve dosyalar yeniden yazılır, böylece Drive da yalnız onları yükler.
Geri dönüş: hedefteki raw/<ad>.tar dosyalarını `tar -xf <ad>.tar -C raw/` ile açın, .db dosyalarını yerine kopyalayın.
"""
import os, sqlite3, sys, tarfile, time

KOK = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(KOK, "raw")
ATLA = {".DS_Store"}


def en_yeni(yol):
    """Klasördeki en yeni değişiklik zamanı (dosya ve klasörler)."""
    t = os.path.getmtime(yol)
    for kok, dizinler, dosyalar in os.walk(yol):
        for a in dizinler + dosyalar:
            try:
                t = max(t, os.path.getmtime(os.path.join(kok, a)))
            except OSError:
                pass
    return t


def db_kopyala(kaynak, hedef):
    gecici = hedef + ".tmp"
    if os.path.exists(gecici):
        os.remove(gecici)
    with sqlite3.connect(kaynak) as k, sqlite3.connect(gecici) as h:
        k.backup(h)
    os.replace(gecici, hedef)


def klasor_tar(kaynak, hedef):
    gecici = hedef + ".tmp"
    with tarfile.open(gecici, "w") as t:
        t.add(kaynak, arcname=os.path.basename(kaynak), filter=lambda x: None if os.path.basename(x.name) in ATLA or x.name.endswith(".tmp") else x)
    os.replace(gecici, hedef)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    hedef = os.path.expanduser(sys.argv[1])
    liste = "--liste" in sys.argv
    os.makedirs(os.path.join(hedef, "raw"), exist_ok=True)
    isler = [(os.path.join(KOK, "futbol.db"), os.path.join(hedef, "futbol.db"))]
    for a in sorted(os.listdir(RAW)):
        if a in ATLA or a.endswith(".tmp"):
            continue
        k = os.path.join(RAW, a)
        isler.append((k, os.path.join(hedef, "raw", a + (".tar" if os.path.isdir(k) else ""))))
    yazilan = 0
    for k, h in isler:
        if not os.path.exists(k):
            continue
        degisti = not os.path.exists(h) or (en_yeni(k) if os.path.isdir(k) else os.path.getmtime(k)) > os.path.getmtime(h)
        if not degisti:
            continue
        ad = os.path.relpath(k, KOK)
        if liste:
            print("değişti:", ad); continue
        bas = time.time()
        if os.path.isdir(k):
            klasor_tar(k, h)
        elif k.endswith(".db"):
            db_kopyala(k, h)
        else:
            with open(k, "rb") as f, open(h + ".tmp", "wb") as g:
                while b := f.read(1 << 20):
                    g.write(b)
            os.replace(h + ".tmp", h)
        yazilan += 1
        print(f"{ad}: {os.path.getsize(h) / 1e6:,.0f} MB ({time.time() - bas:.0f} sn)", flush=True)
    print("Değişen yok." if not yazilan and not liste else f"Bitti: {yazilan} öğe yazıldı.")


if __name__ == "__main__":
    main()

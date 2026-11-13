"""Güncel sezonu TFF'den çekip veritabanını ve siteyi günceller.

  python3 guncelle.py             # indir + tff.db (yalnız güncel sezon) + futbol.db + site verisi
  python3 guncelle.py --yayinla   # ayrıca GitHub'a gönderir (site birkaç dakikada yenilenir)
  python3 guncelle.py --sezon 2026-2027

Lig: TFF (~250 sayfa x 2 sn). Avrupa kupaları: UEFA'nın maç verisi (avrupa.py uefa; takım eşlemesi uefa_kimlik.json).
Süre: ~10 dakika indirme + 3 dakika birleştirme. Tam kurulum (topla.py kur) gerekmez.
TFF'nin güncel sezon sayfaları (arşive geçmeden önce): Süper Lig 198, 1. Lig 142, 2. Lig 976, 3. Lig 971.
"""
import argparse, datetime, os, shutil, subprocess, sys

import topla

KOK = os.path.dirname(os.path.abspath(__file__))
GUNCEL = [("superlig", 198), ("1lig", 142), ("2lig", 976), ("3lig", 971)]


def simdiki_sezon():
    b = datetime.date.today()
    y = b.year if b.month >= 7 else b.year - 1
    return f"{y}-{y + 1}"


def calistir(*komut):
    print("$", " ".join(komut), flush=True)
    subprocess.run(komut, cwd=KOK, check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sezon", default=simdiki_sezon())
    p.add_argument("--yayinla", action="store_true", help="commit + git push")
    a = p.parse_args()

    d = topla.Indirici()
    klasorler = []
    for kaynak, pid in GUNCEL:
        ad = f"{kaynak}_{a.sezon}_{pid}"
        yol = os.path.join(topla.HAM, ad)
        if os.path.isdir(yol):
            shutil.rmtree(yol)   # sonuçlar değiştiği için güncel sezon her seferinde baştan indirilir
        topla.sezon_indir(d, kaynak, a.sezon, pid)
        if os.path.isdir(yol):
            klasorler.append(ad)
    print(f"İndirilen sayfa: {d.indirilen}", flush=True)
    if not klasorler:
        sys.exit("Hiçbir lig indirilemedi")

    topla.kur(os.path.join(KOK, "raw", "tff.db"), topla.HAM, sadece=klasorler)
    try:   # Avrupa kupaları: UEFA'nın maç verisi (Maçkolik GitHub sunucularına 403 veriyor); alınamazsa eski veri kalır
        import avrupa
        avrupa.uefa_guncel(a.sezon)
    except Exception as e:
        print("Avrupa güncellenemedi:", e, flush=True)
    calistir(sys.executable, "-B", "birlestir.py")
    if os.path.isdir(os.path.join(KOK, "raw", "uefa_mac")):   # UEFA maç detayları futbol.db maç numaralarına yeniden bağlanır
        calistir(sys.executable, "-B", "uefa_detay.py", "ayikla")
    calistir(sys.executable, "-B", "web_aktar.py")
    if a.yayinla:
        # Yalnız site verisi ve rapor commit'lenir; futbol.db (37 MB) her hafta commit'lenirse depo şişer,
        # o yüzden "veritabani" sürümüne (GitHub Releases) yüklenir ve üzerine yazılır.
        calistir("git", "add", "docs", "birlestirme_raporu.txt", "avrupa_maclar.csv", "uefa_kimlik.json", "kulup_no.json")
        degisti = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=KOK).returncode != 0
        if degisti:
            calistir("git", "commit", "-q", "-m", f"Güncel sezon {a.sezon}: {datetime.date.today():%d.%m.%Y} itibarıyla")
            calistir("git", "push", "-q")
        else:
            print("Site verisinde değişiklik yok.")
        if subprocess.run(["gh", "release", "view", "veritabani"], cwd=KOK, capture_output=True).returncode != 0:
            calistir("gh", "release", "create", "veritabani", "--title", "Güncel veritabanı",
                     "--notes", "futbol.db: her güncellemede üzerine yazılır.")
        calistir("gh", "release", "upload", "veritabani", "futbol.db", "--clobber")


if __name__ == "__main__":
    main()

"""Güncel sezonu TFF'den çekip veritabanını ve siteyi günceller.

  python3 guncelle.py             # indir + tff.db (yalnız güncel sezon) + futbol.db + site verisi
  python3 guncelle.py --yayinla   # ayrıca GitHub'a gönderir (site birkaç dakikada yenilenir)
  python3 guncelle.py --sezon 2026-2027

Lig: TFF (~250 sayfa x 2 sn). Maç ayrıntıları, kadın ligleri ve kişi sayfaları: detay_guncel.py (GitHub'da girdiler
Releases'ten gelir ve geri yüklenir: girdiler.py). Avrupa kupaları: UEFA'nın maç verisi (avrupa.py uefa; takım eşlemesi uefa_kimlik.json).
Süre: ~10 dakika indirme + 3 dakika birleştirme. Tam kurulum (topla.py kur) gerekmez.
TFF'nin güncel sezon sayfaları (arşive geçmeden önce): Süper Lig 198, 1. Lig 142, 2. Lig 976, 3. Lig 971,
Profesyonelliğe Geçiş Ligi 1596 (bal.py, raw/bal.db).
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

    if os.environ.get("GITHUB_ACTIONS"):   # yerelde duran girdiler (maç ayrıntıları, kadın ligleri...) Releases'ten
        import girdiler
        girdiler_var = girdiler.al()
    else:
        girdiler_var = True
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
    try:   # Profesyonelliğe Geçiş Ligi (5. seviye) ayrı veritabanında: raw/bal.db
        import bal
        print("BAL indirilen sayfa:", bal.guncel(a.sezon), flush=True)
    except (Exception, SystemExit) as e:   # indirici art arda hatada sys.exit yapıyor; bot durmasın
        print("BAL güncellenemedi:", e, flush=True)
    try:   # Avrupa kupaları: UEFA'nın maç verisi (Maçkolik GitHub sunucularına 403 veriyor); alınamazsa eski veri kalır
        import avrupa
        ue = avrupa.uefa_guncel(a.sezon)
    except Exception as e:
        ue = None
        print("Avrupa güncellenemedi:", e, flush=True)
    # yeni oynanan Avrupa maçlarının kadro/olay/istatistiği. raw/uefa_mac girdilerden gelmediyse çalışmaz: boş klasörle
    # uefa_detay ayikla yalnız yeni maçlardan veritabanı kurar ve web_aktar sitedeki bütün Avrupa maç ayrıntılarını siler.
    if girdiler_var and ue and os.path.isdir(os.path.join(KOK, "raw", "uefa_mac")):
        try:
            import uefa_detay
            uefa_detay.guncel(ue)
        except Exception as e:
            print("Avrupa maç ayrıntıları güncellenemedi:", e, flush=True)
    if girdiler_var:   # güncel sezonun maç ayrıntıları (erkek, BAL, kadın), kadın ligleri, yeni oyuncuların kişi sayfaları
        try:
            import detay_guncel
            detay_guncel.main(a.sezon)
        except (Exception, SystemExit) as e:
            print("Maç ayrıntıları güncellenemedi:", e, flush=True)
    calistir(sys.executable, "-B", "birlestir.py")
    if os.path.isdir(os.path.join(KOK, "raw", "uefa_mac")):   # UEFA maç detayları futbol.db maç numaralarına yeniden bağlanır
        calistir(sys.executable, "-B", "uefa_detay.py", "ayikla")
    calistir(sys.executable, "-B", "web_aktar.py")
    if a.yayinla:
        # Yalnız site verisi ve rapor commit'lenir; futbol.db (37 MB) her hafta commit'lenirse depo şişer,
        # o yüzden "veritabani" sürümüne (GitHub Releases) yüklenir ve üzerine yazılır.
        calistir("git", "add", "docs", "birlestirme_raporu.txt", "avrupa_maclar.csv", "uefa_kimlik.json", "kulup_no.json", "avrupa_no.json")
        degisti = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=KOK).returncode != 0
        if degisti:
            calistir("git", "commit", "-q", "-m", f"Güncel sezon {a.sezon}: {datetime.date.today():%d.%m.%Y} itibarıyla")
            for deneme in range(3):   # bu arada başka bir push geldiyse üstüne al (site verisinde botunki geçerli)
                if subprocess.run(["git", "push", "-q"], cwd=KOK).returncode == 0:
                    break
                calistir("git", "pull", "-q", "--rebase", "-X", "theirs")
            else:
                sys.exit("git push başarısız")
        else:
            print("Site verisinde değişiklik yok.")
        if subprocess.run(["gh", "release", "view", "veritabani"], cwd=KOK, capture_output=True).returncode != 0:
            calistir("gh", "release", "create", "veritabani", "--title", "Güncel veritabanı",
                     "--notes", "futbol.db: her güncellemede üzerine yazılır.")
        calistir("gh", "release", "upload", "veritabani", "futbol.db", "--clobber")
        if girdiler_var:
            import girdiler
            girdiler.yukle()


if __name__ == "__main__":
    main()

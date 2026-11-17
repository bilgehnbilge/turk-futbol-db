"""Kadın kulüplerinin logoları: TFF maç sayfalarındaki kulüp logosu (fys.tff.org/TFFUploadFolder/KulupLogolari).

  python3 kadin_logo.py liste    # ağa çıkmadan: maç sayfalarından kulüp -> logo adresi (raw/kadin_logo/liste.json)
  python3 kadin_logo.py indir    # logoları indirir (raw/kadin_logo/) ve docs/logo/tk<TFF kulüp no>.png (64 px) yazar

Erkek takımıyla aynı TFF kulübü olanlar (Galatasaray, Fenerbahçe...) sitede erkek takımının (FM paketi) logosunu
kullanır; TFF logosu yalnızca öbürleri için (kadin_site.py). Her kulüp için en son sezondaki logo alınır.
"""
import glob, gzip, json, os, re, sqlite3, subprocess, sys, time

import topla

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "kadin_logo")
LISTE = os.path.join(HAM, "liste.json")
CIKTI = os.path.join(KOK, "docs", "logo")
URL = "https://fys.tff.org/TFFUploadFolder/KulupLogolari/{}"


def liste():
    c = sqlite3.connect(os.path.join(KOK, "raw", "kadin.db"))
    bilgi = {r[0]: r[1:] for r in c.execute(
        "SELECT m.kaynak_id, e.tff_id, d.tff_id, m.tarih FROM mac m JOIN kulup e ON e.id = m.ev_id JOIN kulup d ON d.id = m.dep_id")}
    son = {}   # TFF kulüp no -> (tarih, dosya adı)
    for f in glob.glob(os.path.join(KOK, "raw", "tff_kadin_mac", "*", "*.html.gz")):
        m = os.path.basename(f)[:-8]
        if m not in bilgi:
            continue
        t = gzip.open(f).read().decode("cp1254", "replace")
        l = re.findall(r'KulupLogolari\\(\d+_120x120\.\w+)', t)
        if len(l) < 2:
            continue
        ev, dep, tarih = bilgi[m]
        for dosya, k in zip(l[:2], (ev, dep)):
            if k not in son or (tarih or "") > son[k][0]:
                son[k] = (tarih or "", dosya)
    os.makedirs(HAM, exist_ok=True)
    json.dump({k: v[1] for k, v in sorted(son.items())}, open(LISTE, "w"), indent=0)
    print(len(son), "kulübün logo adresi ->", LISTE)


def indir():
    if not os.path.exists(LISTE):
        liste()
    l = json.load(open(LISTE))
    yeni = 0
    for k, dosya in l.items():
        ham = os.path.join(HAM, dosya)
        if not os.path.exists(ham):
            r = subprocess.run(["curl", "-sfL", "-m", "60", "-A", topla.UA, "-o", ham + ".tmp", URL.format(dosya)])
            if r.returncode != 0 or os.path.getsize(ham + ".tmp") < 200:
                print("  indirilemedi:", k, dosya, flush=True)
                if os.path.exists(ham + ".tmp"):
                    os.remove(ham + ".tmp")
                continue
            os.replace(ham + ".tmp", ham)
            yeni += 1
            time.sleep(1)
        hedef = os.path.join(CIKTI, f"tk{k}.png")
        subprocess.run(["sips", "-s", "format", "png", "-Z", "64", ham, "--out", hedef], capture_output=True, check=True)
    print(f"{yeni} logo indirildi; {len(glob.glob(os.path.join(CIKTI, 'tk*.png')))} kadın kulübü logosu docs/logo'da")


if __name__ == "__main__":
    {"liste": liste, "indir": indir}[sys.argv[1]]()

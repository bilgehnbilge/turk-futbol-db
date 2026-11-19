#!/usr/bin/env python3
"""Erkek kulüplerinin (en çok Profesyonelliğe Geçiş Ligi) logoları: TFF maç sayfalarındaki kulüp logosu
(fys.tff.org/TFFUploadFolder/KulupLogolari). FM paketinde ve Vikipedi'de logosu olmayanlar için (web_aktar.py'de
öncelik: FM > Vikipedi > TFF > UEFA).

  python3 tff_logo.py liste   # ağa çıkmadan: maç sayfalarından TFF kulüp no -> en son sezondaki logo dosyası
  python3 tff_logo.py indir   # logoları indirir (raw/tff_logo/) -> docs/logo/tk<TFF kulüp no>.png (64 px) + logo_tff.json

Kadın kulüpleri de (kadin_logo.py) aynı adlandırmayı kullanır: aynı TFF kulübünün logosu aynı dosyadır.
"""
import glob, gzip, json, os, re, sqlite3, subprocess, sys, time

import topla

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "tff_logo")
LISTE = os.path.join(HAM, "liste.json")
CIKTI = os.path.join(KOK, "docs", "logo")
ESLESME = os.path.join(KOK, "logo_tff.json")
URL = "https://fys.tff.org/TFFUploadFolder/KulupLogolari/{}"
KAYNAK = [("tff.db", "tff_mac"), ("bal.db", "tff_bal_mac")]   # (maç listesi, maç sayfaları)


def liste():
    son = {}   # TFF kulüp no -> (tarih, dosya adı)
    for db, klasor in KAYNAK:
        yol = os.path.join(KOK, "raw", db)
        if not os.path.exists(yol):
            continue
        c = sqlite3.connect(yol)
        bilgi = {r[0]: r[1:] for r in c.execute(
            "SELECT m.kaynak_id, e.tff_id, d.tff_id, m.tarih FROM mac m JOIN kulup e ON e.id = m.ev_id JOIN kulup d ON d.id = m.dep_id")}
        for f in glob.glob(os.path.join(KOK, "raw", klasor, "*", "*.html.gz")):
            m = os.path.basename(f)[:-8]
            if m not in bilgi:
                continue
            ev, dep, tarih = bilgi[m]
            # her kulübün yalnız en yeni maçı okunur: eskiyse sayfayı açmaya gerek yok
            if all(k and k in son and (tarih or "") <= son[k][0] for k in (ev, dep)):
                continue
            t = gzip.open(f).read().decode("cp1254", "replace")
            l = re.findall(r'KulupLogolari\\(\d+_120x120\.\w+)', t)
            if len(l) < 2:
                continue
            for dosya, k in zip(l[:2], (ev, dep)):
                if k and (k not in son or (tarih or "") > son[k][0]):
                    son[k] = (tarih or "", dosya)
    os.makedirs(HAM, exist_ok=True)
    json.dump({k: v[1] for k, v in sorted(son.items())}, open(LISTE, "w"), indent=0)
    print(len(son), "kulübün logo adresi ->", LISTE, flush=True)


def indir(yalniz_eksik=True):
    if not os.path.exists(LISTE):
        liste()
    l = json.load(open(LISTE))
    var = set()
    if yalniz_eksik:   # FM paketinde ya da Vikipedi'de logosu olanlar indirilmez
        for f in ("logo_eslesme.json", "logo_wiki.json"):
            p = os.path.join(KOK, f)
            if os.path.exists(p):
                var |= {k[4:] for k, v in json.load(open(p, encoding="utf-8")).items()
                        if k.startswith("tff:") and v and os.path.exists(os.path.join(CIKTI, f"{v}.png"))}
    import collections, hashlib
    ozet = lambda f: hashlib.md5(open(f, "rb").read()).hexdigest()
    es, yeni = {}, 0
    for k, dosya in l.items():
        if k in var:
            continue
        ham = os.path.join(HAM, dosya)
        if not os.path.exists(ham):
            r = subprocess.run(["curl", "-sfL", "-m", "60", "-A", topla.UA, "-o", ham + ".tmp", URL.format(dosya)])
            if r.returncode != 0 or not os.path.exists(ham + ".tmp") or os.path.getsize(ham + ".tmp") < 200:
                print("  indirilemedi:", k, dosya, flush=True)
                if os.path.exists(ham + ".tmp"):
                    os.remove(ham + ".tmp")
                continue
            os.replace(ham + ".tmp", ham)
            yeni += 1
            time.sleep(1)
        hedef = os.path.join(CIKTI, f"tk{k}.png")
        r = subprocess.run(["sips", "-s", "format", "png", "-Z", "64", ham, "--out", hedef], capture_output=True)
        if r.returncode == 0:
            es[f"tff:{k}"] = f"tk{k}"
    # TFF'nin boş yer tutucusu (beyaz kare) birden çok kulüpte aynı dosya: üç ya da daha çok kulüpte tekrarlanan görsel atılır
    h = {k: ozet(os.path.join(HAM, l[k[4:]])) for k in es}
    say = collections.Counter(h.values())
    for k in [k for k in es if say[h[k]] >= 3]:
        os.remove(os.path.join(CIKTI, f"{es.pop(k)}.png"))
    json.dump(dict(sorted(es.items())), open(ESLESME, "w", encoding="utf-8"), indent=0)
    print(f"{yeni} logo indirildi; {len(es)} kulübün TFF logosu -> {ESLESME}", flush=True)


if __name__ == "__main__":
    {"liste": liste, "indir": indir}[sys.argv[1]]()

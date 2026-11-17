"""Kadın kulüplerinin logoları: TFF maç sayfalarındaki kulüp logosu (fys.tff.org/TFFUploadFolder/KulupLogolari).

  python3 kadin_logo.py liste    # ağa çıkmadan: maç sayfalarından kulüp -> logo adresi (raw/kadin_logo/liste.json)
  python3 kadin_logo.py indir    # logoları indirir (raw/kadin_logo/) ve docs/logo/tk<TFF kulüp no>.png (64 px) yazar
  python3 kadin_logo.py wiki_bul    # TFF'de logosu olmayanlar: İngilizce ve Türkçe Vikipedi'deki kulüp sayfasının logosu -> raw/kadin_logo/wiki_aday.json
  python3 kadin_logo.py wiki_indir  # adayları indirir -> docs/logo/wk<TFF kulüp no>.png

Vikipedi eşlemesi: sayfa futbol kulübü bilgi kutusu taşımalı ve sayfa başlığı ya da kulüp adı (kadın/women ekleri
atılarak) kulübün TFF'deki adlarından biriyle birebir tutmalı; kuruluş yılı kulübün ilk sezonundan sonra olmamalı.

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


WIKI = {"en": "https://en.wikipedia.org/w/api.php", "tr": "https://tr.wikipedia.org/w/api.php"}
WIKI_ADAY = os.path.join(HAM, "wiki_aday.json")
EK = r"\b(kadin|kadinlar|bayan|bayanlar|women|womens|ladies|futbol takimi|futbol kulubu|football club|team|takimi|kulubu|sk|fk|fc|s k)\b"


def wiki_api(dil, **p):
    import urllib.parse, urllib.request
    p.update(format="json", formatversion="2", maxlag="5")
    url = WIKI[dil] + "?" + urllib.parse.urlencode(p)
    for deneme in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": topla.UA}), timeout=60) as r:
                d = json.load(r)
            if "error" in d and d["error"].get("code") == "maxlag":
                time.sleep(10); continue
            return d
        except Exception as e:   # 429: Vikipedi istek sınırı; uzun ara ver
            print("hata", e, file=sys.stderr, flush=True); time.sleep((90 if "429" in str(e) else 5) * (deneme + 1))
        finally:
            time.sleep(2)   # Vikipedi'yi yormamak için istekler arası
    raise SystemExit("Vikipedi API cevap vermiyor")


def ad_kok(s):
    import logo
    n = logo.norm(re.sub(r"\(.*?\)", " ", s))
    n = re.sub(EK, " ", n)
    return logo.kok(n)


def wiki_bul():
    z = json.load(open(os.path.join(KOK, "docs", "data", "kadin", "ozet.json"), encoding="utf-8"))
    eksik = [k for k in z["kulupler"] if "logo" not in k]
    out = json.load(open(WIKI_ADAY, encoding="utf-8")) if os.path.exists(WIKI_ADAY) else {}
    bakildi = set(out.get("_bakildi", []))   # kaldığı yerden: daha önce bakılan kulüpler
    out["_bakildi"] = sorted(bakildi)
    for i, k in enumerate(eksik, 1):
        if k["tff"][0] in bakildi:
            continue
        adlar = {ad_kok(a[0]) for a in k["adlar"]} | {ad_kok(k["ad"])}
        adlar.discard("")
        bulundu = None
        for dil, ek in (("en", " women's football"), ("tr", " kadın futbol")):
            ara = wiki_api(dil, action="query", list="search", srsearch=k["adlar"][-1][0] + ek, srlimit=5, srnamespace=0)
            basliklar = [x["title"] for x in ara["query"]["search"]]
            if not basliklar:
                continue
            d = wiki_api(dil, action="query", prop="revisions", rvprop="content", rvslots="main", redirects=1, titles="|".join(basliklar))
            for p in d["query"]["pages"]:
                if "revisions" not in p:
                    continue
                t = p["revisions"][0]["slots"]["main"]["content"]
                if not re.search(r"\{\{\s*(infobox football club|futbol kulübü bilgi kutusu)", t, re.I):
                    continue
                al_ = lambda ad: (re.search(r"\|\s*" + ad + r"\s*=\s*([^\n|]*)", t) or [None, ""])[1].strip()
                resim = re.sub(r"^\[*(Dosya|File|Resim|Image):", "", al_("image") or al_("logo") or al_("arma") or al_("resim")).strip()
                if not re.search(r"\.(png|svg|jpe?g|gif)$", resim, re.I):
                    continue
                sayfa = {ad_kok(p["title"]), ad_kok(re.sub(r"\[\[|\]\]", "", al_("clubname") or al_("kulüpismi") or ""))} - {""}
                if not adlar & sayfa:
                    continue
                kur = re.search(r"(19\d\d|20\d\d)", al_("founded") or al_("kuruluş"))
                if kur and int(kur.group(1)) > int(k["ilk"][:4]) + 1:
                    continue
                bulundu = {"kulup": k["ad"], "tff": k["tff"][0], "dil": dil, "sayfa": p["title"], "resim": resim,
                           "kurulus": kur.group(1) if kur else None, "ilk": k["ilk"], "mac": k["mac"]}
                break
            time.sleep(0.4)
            if bulundu:
                break
        if bulundu:
            out[k["tff"][0]] = bulundu
        out["_bakildi"].append(k["tff"][0])
        json.dump(out, open(WIKI_ADAY, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if i % 25 == 0:
            print(f"  {i}/{len(eksik)}: {len(out)} bulundu", flush=True)
    json.dump(out, open(WIKI_ADAY, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(eksik)} logosuz kulüp, {len(out) - 1} Vikipedi logosu bulundu -> {WIKI_ADAY}")


def wiki_indir():
    aday = json.load(open(WIKI_ADAY, encoding="utf-8"))
    n = 0
    for tff, v in aday.items():
        if tff.startswith("_"):
            continue
        hedef = os.path.join(CIKTI, f"wk{tff}.png")
        if os.path.exists(hedef):
            n += 1; continue
        d = wiki_api(v["dil"], action="query", prop="imageinfo", iiprop="url", iiurlwidth="128", titles="File:" + v["resim"])
        ii = next((p.get("imageinfo") for p in d["query"]["pages"] if p.get("imageinfo")), None)
        if not ii:
            print("  url yok:", v["kulup"], v["resim"]); continue
        u = ii[0].get("thumburl") or ii[0]["url"]
        ham = os.path.join(HAM, "wiki", f"wk{tff}" + os.path.splitext(u.split("?")[0])[1])
        os.makedirs(os.path.dirname(ham), exist_ok=True)
        r = subprocess.run(["curl", "-sfL", "-m", "60", "-A", topla.UA, "-o", ham, u])
        if r.returncode != 0:
            print("  indirilemedi:", v["kulup"]); continue
        subprocess.run(["sips", "-s", "format", "png", "-Z", "64", ham, "--out", hedef], capture_output=True)
        n += os.path.exists(hedef)
        time.sleep(0.5)
    print(n, "Vikipedi logosu -> docs/logo/wk*.png")


if __name__ == "__main__":
    {"liste": liste, "indir": indir, "wiki_bul": wiki_bul, "wiki_indir": wiki_indir}[sys.argv[1]]()

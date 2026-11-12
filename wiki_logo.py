"""FM paketinde logosu olmayan kulüpler için tr.wikipedia'daki arma (bilgi kutusu "arma" alanı).

  python3 wiki_logo.py bul      -> raw/wiki_kulup/logo_aday.json (kulüp kimliği -> sayfa, arma dosyası, güven)
  python3 wiki_logo.py indir    -> docs/logo/w<sayfa no>.png (64 px) + logo_wiki.json (kulüp kimliği -> "w<no>")

Eşleme: önce TFF numarası (raw/wiki_kulup: Şablon:TFF kulüp), yoksa adla arama; sayfanın futbol kulübü bilgi
kutusu olmalı ve kulüp adı (ya da dönem adlarından biri) sayfa başlığı / kulüpismi ile birebir tutmalı.
"""
import json, os, re, sqlite3, subprocess, sys, time, urllib.parse, urllib.request

import logo

KOK = os.path.dirname(os.path.abspath(__file__))
DIZ = os.path.join(KOK, "raw", "wiki_kulup")
API = "https://tr.wikipedia.org/w/api.php"
UA = "turk-futbol-db/0.1 (kisisel arsiv)"
CIKTI = os.path.join(KOK, "docs", "logo")


def api(**p):
    p.update(format="json", formatversion="2", maxlag="5")
    url = API + "?" + urllib.parse.urlencode(p)
    for deneme in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                d = json.load(r)
            if "error" in d and d["error"].get("code") == "maxlag":
                time.sleep(10); continue
            return d
        except Exception as e:
            print("hata", e, file=sys.stderr); time.sleep(5 * (deneme + 1))
    raise SystemExit("API cevap vermiyor")


def wikitext(basliklar):
    out = {}
    for i in range(0, len(basliklar), 40):
        d = api(action="query", prop="revisions|info", rvprop="content", rvslots="main", redirects=1, titles="|".join(basliklar[i:i + 40]))
        yon = {r["from"]: r["to"] for r in d["query"].get("redirects", [])}
        sayfa = {p["title"]: p for p in d["query"]["pages"] if "revisions" in p}
        for b in basliklar[i:i + 40]:
            p = sayfa.get(yon.get(b, b))
            if p:
                out[b] = (p["title"], p["pageid"], p["revisions"][0]["slots"]["main"]["content"])
        time.sleep(0.5)
    return out


def alan(t, ad):
    m = re.search(r"\|\s*" + ad + r"\s*=\s*([^\n|]*)", t)
    return m.group(1).strip() if m else ""


def eksikler():
    K = json.load(open(os.path.join(KOK, "docs", "data", "kulupler.json"), encoding="utf-8"))
    c = sqlite3.connect(os.path.join(KOK, "futbol.db"))
    kim = {}
    for kid, k in c.execute("SELECT kulup_id, kaynak || ':' || kaynak_id FROM kulup_kimlik ORDER BY kaynak <> 'tff', son_sezon DESC"):
        kim.setdefault(kid, k)
    return [dict(k, kimlik=kim[k["id"]]) for k in K if k["yerli"] and "logo" not in k and k["id"] in kim
            and not re.search(r"\b(II|2P)\b|\(2P\)", k["ad"])]


def bul():
    W = json.load(open(os.path.join(DIZ, "kulupler.json"), encoding="utf-8"))
    tff_sayfa = {}
    for w in W:
        for t in w["tff"]:
            tff_sayfa.setdefault(t, w["baslik"])
    eksik = eksikler()
    aday = {}   # kimlik -> [başlık...]
    for k in eksik:
        b = [tff_sayfa[t] for t in k["tff"] if t in tff_sayfa]
        if b:
            aday[k["kimlik"]] = [("tff", b[0])]
            continue
        sonuc = api(action="query", list="search", srsearch=f'{k["ad"]} futbol kulübü', srlimit=5, srnamespace=0)
        aday[k["kimlik"]] = [("ara", s["title"]) for s in sonuc["query"]["search"]]
        time.sleep(0.4)
    basliklar = sorted({b for l in aday.values() for _, b in l})
    metin = wikitext(basliklar)
    out = {}
    for k in eksik:
        adlar = [k["ad"]] + [a[0] for a in k["adlar"]]
        for yol, b in aday.get(k["kimlik"], []):
            if b not in metin:
                continue
            baslik, pid, t = metin[b]
            if "kulübü bilgi kutusu" not in t.lower():
                continue
            arma = re.sub(r"^(Dosya|File|Resim|Image):", "", alan(t, "arma") or alan(t, "logo") or alan(t, "resim")).strip()
            if not arma or not re.search(r"\.(png|svg|jpe?g|gif)$", arma, re.I):
                continue
            sayfa_adlari = [re.sub(r"\s*\(.*\)$", "", baslik), alan(t, "kulüpismi")]
            tutan = any(logo.benzerlik(a, s) == 1.0 for a in adlar for s in sayfa_adlari if s)
            kur = re.search(r"(1[89]\d\d|20\d\d)", alan(t, "kuruluş"))
            # kuruluş yılı kulübün ilk sezonundan sonra olmamalı (aynı adlı yeni kulüp)
            yil_uygun = not kur or int(kur.group(1)) <= int(k["ilk"][:4]) + 1
            if (yol == "tff" or tutan) and yil_uygun:
                out[k["kimlik"]] = {"kulup": k["ad"], "sayfa": baslik, "pageid": pid, "arma": arma, "yol": yol,
                                    "kurulus": kur.group(1) if kur else None, "ilk": k["ilk"], "son": k["son"], "mac": k["mac"]}
                break
    json.dump(out, open(os.path.join(DIZ, "logo_aday.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(eksik)} logosuz kulüp, {len(out)} Vikipedi armasi bulundu "
          f"({sum(v['yol'] == 'tff' for v in out.values())} TFF no ile)")


def indir():
    aday = json.load(open(os.path.join(DIZ, "logo_aday.json"), encoding="utf-8"))
    dosyalar = sorted({v["arma"] for v in aday.values()})
    url = {}
    for i in range(0, len(dosyalar), 40):
        d = api(action="query", prop="imageinfo", iiprop="url", iiurlwidth="128", titles="|".join("Dosya:" + f for f in dosyalar[i:i + 40]))
        norm = {n["to"]: n["from"] for n in d["query"].get("normalized", [])}
        for p in d["query"]["pages"]:
            ii = p.get("imageinfo")
            if ii:
                ad = norm.get(p["title"], p["title"]).split(":", 1)[1]
                url[ad] = ii[0].get("thumburl") or ii[0]["url"]
        time.sleep(0.5)
    es = {}
    gecici = os.path.join(DIZ, "arma")
    os.makedirs(gecici, exist_ok=True)
    for kim, v in aday.items():
        u = url.get(v["arma"]) or url.get(v["arma"].replace("_", " "))
        if not u:
            print("url yok", v["kulup"], v["arma"]); continue
        ad = f"w{v['pageid']}"
        hedef = os.path.join(CIKTI, ad + ".png")
        if not os.path.exists(hedef):
            ham = os.path.join(gecici, ad + os.path.splitext(u)[1].split("?")[0])
            r = subprocess.run(["curl", "-sL", "-m", "60", "-A", UA, "-o", ham, "-w", "%{http_code}", u], capture_output=True, text=True)
            if r.stdout != "200":
                print("indirilemedi", v["kulup"], r.stdout); continue
            subprocess.run(["sips", "-s", "format", "png", "-Z", "64", ham, "--out", hedef], capture_output=True)
            time.sleep(0.5)
        if os.path.exists(hedef):
            es[kim] = ad
    json.dump(dict(sorted(es.items())), open(os.path.join(KOK, "logo_wiki.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(es), "Vikipedi arması -> docs/logo/w*.png, logo_wiki.json")


if __name__ == "__main__":
    {"bul": bul, "indir": indir}[sys.argv[1]]()

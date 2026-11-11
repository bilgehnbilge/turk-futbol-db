"""tr.wikipedia'dan TFF kulup numarali kulup sayfalarini ceker ve ayiklar.

  python3 wiki_kulup.py indir     -> raw/wiki_kulup/sayfalar.json (baslik -> wikitext)
  python3 wiki_kulup.py ayikla    -> raw/wiki_kulup/kulupler.json (TFF no, kurulus, eski adlar, kapanis...)
"""
import json, os, re, sys, time, urllib.parse, urllib.request

KOK = os.path.dirname(os.path.abspath(__file__))
DIZ = os.path.join(KOK, "raw", "wiki_kulup")
API = "https://tr.wikipedia.org/w/api.php"
UA = "turk-futbol-db/0.1 (kisisel arsiv)"


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
            print("hata", e, file=sys.stderr); time.sleep(10 * (deneme + 1))
    raise SystemExit("API cevap vermiyor")


def indir():
    os.makedirs(DIZ, exist_ok=True)
    basliklar, devam = [], {}
    while True:
        d = api(action="query", list="embeddedin", eititle="Şablon:TFF kulüp", einamespace=0, eilimit=500, **devam)
        basliklar += [x["title"] for x in d["query"]["embeddedin"]]
        if "continue" not in d:
            break
        devam = {"eicontinue": d["continue"]["eicontinue"]}
        time.sleep(1)
    print(len(basliklar), "sayfa")
    sayfa = {}
    for i in range(0, len(basliklar), 50):
        d = api(action="query", prop="revisions", rvprop="content", rvslots="main", titles="|".join(basliklar[i:i + 50]))
        for p in d["query"]["pages"]:
            if p.get("revisions"):
                sayfa[p["title"]] = p["revisions"][0]["slots"]["main"]["content"]
        print(i + 50, end=" ", flush=True)
        time.sleep(1)
    json.dump(sayfa, open(os.path.join(DIZ, "sayfalar.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("\nyazildi", len(sayfa))


def temizle(s):
    s = re.sub(r"<ref[^>]*/>|<ref.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"\{\{[Bb]ayrak[^}]*\}\}|\{\{[Rr]enk kutusu[^}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"'''?|<small>|</small>", "", s)
    return s.strip()


def alan(metin, ad):
    m = re.search(r"^\s*\|\s*" + ad + r"\s*=(.*?)(?=^\s*\||^\}\})", metin, flags=re.M | re.S)
    return temizle(m[1]) if m else ""


def ayikla():
    sayfa = json.load(open(os.path.join(DIZ, "sayfalar.json"), encoding="utf-8"))
    wd = {}   # Wikidata: {{TFF kulüp}} parametresizse numara P7450'den gelir
    wd_yol = os.path.join(DIZ, "wikidata_tff.json")
    for r in (json.load(open(wd_yol, encoding="utf-8")) if os.path.exists(wd_yol) else []):
        if "trTitle" in r:
            w = wd.setdefault(r["trTitle"], dict(tff=set(), kur="", fes=""))
            w["tff"].add(r["tff"]); w["kur"] = w["kur"] or r.get("inception", "")[:4]; w["fes"] = w["fes"] or r.get("dissolved", "")[:4]
    cikti = []
    for baslik, t in sayfa.items():
        nolar = re.findall(r"\{\{\s*TFF kulüp\s*\|\s*(?:id\s*=\s*)?(\d+)", t, flags=re.I) + sorted(wd.get(baslik, {}).get("tff", ()))
        if not nolar:
            continue
        eski = alan(t, "eskiadı") or alan(t, "eskiadi") or alan(t, "eski ad")
        eski_l = [x.strip(" ,;-") for x in re.split(r"<br\s*/?>|\n|,|;", eski) if x.strip(" ,;-")]
        kur = alan(t, "kuruluş") or alan(t, "kurulus")
        kategoriler = re.findall(r"\[\[Kategori:([^\]|]+)", t)
        fesih = [re.match(r"(\d{4})", k)[1] for k in kategoriler if "feshedilen" in k and re.match(r"\d{4}", k)]
        kur_kat = [re.match(r"(\d{4})", k)[1] for k in kategoriler if "kurulan" in k and re.match(r"\d{4}", k)]
        yil = re.search(r"(1[89]\d\d|20\d\d)", kur)
        karistirma = re.findall(r"\{\{\s*[Kk]arıştırma\s*\|([^}]*)\}\}", t)
        w = wd.get(baslik, {})
        cikti.append(dict(baslik=baslik, tff=sorted(set(nolar), key=int),
                          kurulus=(yil[1] if yil else (kur_kat[0] if kur_kat else w.get("kur", ""))),
                          fesih=fesih[0] if fesih else w.get("fes", ""), eski_adlar=eski_l, kulupismi=alan(t, "kulüpismi") or alan(t, "kulupismi"),
                          tamisim=alan(t, "tamisim"), karistirma=karistirma,
                          yonlendirme=bool(re.match(r"#(YÖNLENDİR|REDIRECT)", t, flags=re.I))))
    json.dump(cikti, open(os.path.join(DIZ, "kulupler.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(cikti), "kulup sayfasi; birden cok TFF no:", sum(len(x["tff"]) > 1 for x in cikti))


if __name__ == "__main__":
    {"indir": indir, "ayikla": ayikla}[sys.argv[1]]()

#!/usr/bin/env python3
"""Yabancı oyuncuların bilinen adları: Wikidata'da TFF oyuncu numarası (P2448) kayıtlı kişilerin Vikipedi madde başlıkları.

  python3 wikidata_ad.py indir    # Wikidata SPARQL (3 sorgu) -> raw/wikidata_tff.json
  python3 wikidata_ad.py dogum    # TFF numarası Wikidata'da olmayan yabancılar: aynı gün doğmuş futbolcular -> raw/wikidata_dogum.json
  python3 wikidata_ad.py ayikla   # ağa çıkmadan -> bilinen_ad_wiki.json (depoda; tff_detay.py okur)

Ad seçimi: İngilizce Vikipedi başlığı (özgün yazımı korur: "Ibrahim Šehić"), yoksa Türkçe Vikipedi başlığı, yoksa Wikidata
İngilizce etiketi; parantez içi ayırt ediciler atılır ("Danilo (footballer, born 1990)" -> "Danilo").
Doğum günüyle eşleme (dogum): TFF numarası Wikidata'ya girilmemiş yabancılar (ör. Rafael Leão) için o gün doğmuş futbolcular
(P106 = futbolcu) alınır; Vikipedi başlığının / etiketinin bütün sözcükleri TFF'deki tam adda geçiyorsa ya da doğum adı (P1477)
tam adla büyük ölçüde örtüşüyorsa ve tek aday kalıyorsa eşlenir.
Yabancı: TFF kişi sayfasındaki uyruk (raw/kisi.db) TC değil; kişi sayfası inmemişse Wikidata'daki vatandaşlıkları (P27)
arasında Türkiye yok.
"""
import csv, io, json, os, re, sqlite3, subprocess, sys

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "wikidata_tff.json")
CIKTI = os.path.join(KOK, "bilinen_ad_wiki.json")
UA = "football-archive-script/1.0"
SORGU = {
    "tr": 'SELECT ?tff ?t WHERE { ?i wdt:P2448 ?tff . ?s schema:about ?i ; schema:isPartOf <https://tr.wikipedia.org/> ; schema:name ?t }',
    "en": 'SELECT ?tff ?t WHERE { ?i wdt:P2448 ?tff . ?s schema:about ?i ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?t }',
    "etiket": 'SELECT ?tff ?t WHERE { ?i wdt:P2448 ?tff ; rdfs:label ?t FILTER(lang(?t)="en") }',
    "turk": 'SELECT DISTINCT ?tff WHERE { ?i wdt:P2448 ?tff ; wdt:P27 wd:Q43 }',
}


def sparql(q, bas="tff"):
    r = subprocess.run(["curl", "-s", "-G", "-m", "170", "-A", UA, "-H", "Accept: text/csv", "--data-urlencode", f"query={q}",
                        "https://query.wikidata.org/sparql"], capture_output=True, text=True)
    if not r.stdout.startswith(bas):
        sys.exit(f"Wikidata yanıtı okunamadı: {r.stdout[:200]}")
    return list(csv.DictReader(io.StringIO(r.stdout)))


def indir():
    out = {}
    for k, q in SORGU.items():
        rows = sparql(q)
        out[k] = {} if k != "turk" else []
        for r in rows:
            if k == "turk":
                out[k].append(r["tff"])
            else:
                out[k].setdefault(r["tff"], r["t"])
        print(k, len(rows), flush=True)
    json.dump(out, open(HAM, "w", encoding="utf-8"), ensure_ascii=False)


DOGUM = os.path.join(KOK, "raw", "wikidata_dogum.json")
DSORGU = """SELECT ?i ?dob ?l ?en ?tr ?bn (GROUP_CONCAT(DISTINCT ?al; separator="|") AS ?als) WHERE {
  VALUES ?dob { %s }
  ?i wdt:P569 ?dob ; wdt:P106 wd:Q937857 .
  OPTIONAL { ?i rdfs:label ?l FILTER(lang(?l) = "en") }
  OPTIONAL { ?s schema:about ?i ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?en }
  OPTIONAL { ?t schema:about ?i ; schema:isPartOf <https://tr.wikipedia.org/> ; schema:name ?tr }
  OPTIONAL { ?i wdt:P1477 ?bn }
  OPTIONAL { ?i skos:altLabel ?al FILTER(lang(?al) IN ("en", "pt", "es", "fr", "tr")) }
} GROUP BY ?i ?dob ?l ?en ?tr ?bn"""


def _bilinmeyen_yabancilar():
    """{kişi no: (TFF tam adı, doğum)}: uyruğu TC olmayan, bilinen adı olmayan, doğum tarihi bilinen oyuncular."""
    bilinen = set()
    for f in ("bilinen_ad.json", "bilinen_ad_wiki.json"):
        if os.path.exists(os.path.join(KOK, f)):
            bilinen |= set(json.load(open(os.path.join(KOK, f), encoding="utf-8")))
    w = json.load(open(HAM, encoding="utf-8"))
    bilinen |= set(w["tr"]) | set(w["en"]) | set(w["etiket"])
    db = sqlite3.connect(os.path.join(KOK, "raw", "kisi.db"))
    return {str(k): (a, d) for k, a, d, u in db.execute("SELECT kisi, ad, dogum, uyruk FROM kisi")
            if u and u != "TC" and d and str(k) not in bilinen}


def dogum():
    eski = json.load(open(DOGUM, encoding="utf-8")) if os.path.exists(DOGUM) else {}
    gunler = sorted({d for _, d in _bilinmeyen_yabancilar().values()} - set(eski))
    print(len(gunler), "doğum günü sorgulanacak", flush=True)
    for i in range(0, len(gunler), 8):
        parca = gunler[i:i + 8]
        import time
        for deneme in range(4):
            try:
                rows = sparql(DSORGU % " ".join(f'"{g}T00:00:00Z"^^xsd:dateTime' for g in parca), "i")
                break
            except SystemExit:
                if deneme == 3:
                    raise
                time.sleep(10 * (deneme + 1))
        time.sleep(1)
        for g in parca:
            eski.setdefault(g, [])
        for r in rows:
            eski[r["dob"][:10]].append({k: r[k] for k in ("i", "l", "en", "tr", "bn", "als") if r.get(k)})
        json.dump(eski, open(DOGUM, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  {min(i + 8, len(gunler))}/{len(gunler)}", flush=True)


def _sozcuk(s):
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFKD", (s or "").replace("İ", "I").replace("ı", "i")) if not unicodedata.combining(c))
    return [x for x in re.findall(r"[a-z0-9]+", s.lower()) if x not in ("da", "de", "do", "dos", "das", "del", "van", "von", "der", "e", "y", "jr", "junior")]


def dogum_esle():
    """{kişi no: bilinen ad} doğum günü + ad örtüşmesiyle (tek aday)."""
    if not os.path.exists(DOGUM):
        return {}
    gun = json.load(open(DOGUM, encoding="utf-8"))
    out = {}
    for k, (tam, d) in _bilinmeyen_yabancilar().items():
        ts = set(_sozcuk(tam))
        uyan = []
        for c in gun.get(d, []):
            adlar = [temiz(c.get(x)) for x in ("en", "tr", "l")] + (c.get("als") or "").split("|")
            ok = any(set(_sozcuk(a)) and set(_sozcuk(a)) <= ts for a in adlar if a)
            bn = set(_sozcuk(c.get("bn")))
            if not ok and bn and len(bn & ts) >= 2 and len(bn & ts) >= 0.7 * len(ts):
                ok = True
            if ok:
                uyan.append(c)
        if len({c["i"] for c in uyan}) == 1:
            ad = temiz(uyan[0].get("en")) or temiz(uyan[0].get("tr")) or temiz(uyan[0].get("l"))
            if ad and not re.fullmatch(r"Q\d+", ad):
                out[k] = ad
    return out


def temiz(t):
    return re.sub(r"\s*\([^)]*\)\s*$", "", t or "").strip()


def ayikla():
    w = json.load(open(HAM, encoding="utf-8"))
    turk = set(w["turk"])
    uyruk = {}
    kdb = os.path.join(KOK, "raw", "kisi.db")
    if os.path.exists(kdb):
        uyruk = {str(k): u for k, u in sqlite3.connect(kdb).execute("SELECT kisi, uyruk FROM kisi")}
    out = {}
    for tff in set(w["tr"]) | set(w["en"]) | set(w["etiket"]):
        yab = (uyruk[tff] not in (None, "", "TC")) if tff in uyruk else tff not in turk
        if not yab:
            continue
        ad = temiz(w["en"].get(tff)) or temiz(w["tr"].get(tff)) or temiz(w["etiket"].get(tff))
        if ad and not re.fullmatch(r"Q\d+", ad):
            out[tff] = ad
    eslesen = dogum_esle()
    for k, a in eslesen.items():
        out.setdefault(k, a)
    print(len(eslesen), "oyuncu doğum günüyle eşlendi")
    json.dump(dict(sorted(out.items(), key=lambda x: int(x[0]))), open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(out), "yabancı oyuncunun bilinen adı ->", CIKTI)


if __name__ == "__main__":
    {"indir": indir, "ayikla": ayikla, "dogum": dogum}[sys.argv[1]]()

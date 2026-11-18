#!/usr/bin/env python3
"""Yabancı oyuncuların bilinen adları: Wikidata'da TFF oyuncu numarası (P2448) kayıtlı kişilerin Vikipedi madde başlıkları.

  python3 wikidata_ad.py indir    # Wikidata SPARQL (3 sorgu) -> raw/wikidata_tff.json
  python3 wikidata_ad.py ayikla   # ağa çıkmadan -> bilinen_ad_wiki.json (depoda; tff_detay.py okur)

Ad seçimi: İngilizce Vikipedi başlığı (özgün yazımı korur: "Ibrahim Šehić"), yoksa Türkçe Vikipedi başlığı, yoksa Wikidata
İngilizce etiketi; parantez içi ayırt ediciler atılır ("Danilo (footballer, born 1990)" -> "Danilo").
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


def sparql(q):
    r = subprocess.run(["curl", "-s", "-G", "-m", "170", "-A", UA, "-H", "Accept: text/csv", "--data-urlencode", f"query={q}",
                        "https://query.wikidata.org/sparql"], capture_output=True, text=True)
    if not r.stdout.startswith("tff"):
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
    json.dump(dict(sorted(out.items(), key=lambda x: int(x[0]))), open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(out), "yabancı oyuncunun bilinen adı ->", CIKTI)


if __name__ == "__main__":
    {"indir": indir, "ayikla": ayikla}[sys.argv[1]]()

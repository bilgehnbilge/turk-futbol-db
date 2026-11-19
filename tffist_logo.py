#!/usr/bin/env python3
"""İstanbul kulüplerinin logoları: TFF İstanbul il temsilciliği sitesinin grup sayfaları (tffistanbul.org/gruplar,
robots.txt'de izinli; /mac/, /oyuncu/, /puantaj-ve-fikstur/ yasak ve kullanılmaz). FM paketinde, Vikipedi'de ve TFF
maç sayfalarında logosu olmayan kulüpler için (web_aktar.py'de en düşük öncelik, UEFA'dan önce).

  python3 tffist_logo.py indir    # 2010-11'den bugüne Süper Amatör ve 1. Amatör grup sayfaları -> raw/tffist/ (kaldığı yerden)
  python3 tffist_logo.py esle     # ağa çıkmadan: logosuz kulüpler <-> tffistanbul kulüpleri -> raw/tffist/eslesme.json
  python3 tffist_logo.py logo     # eşleşenlerin logoları -> docs/logo/ti<tffistanbul kulüp no>.png + logo_tffist.json

Eşleme: ad (logo.kok ile, ekler atılarak) iki tarafta da tek bir kulübe denk gelmeli ve kulübün İstanbul kulübü olduğu
görülmeli: lig maçlarında aynı grupta oynadığı rakiplerden en az üçü de tffistanbul listesinde (ad ile) bulunmalı
(farklı illerdeki aynı adlı kulüpler eşlenmesin).
"""
import collections, glob, html, json, os, re, sqlite3, subprocess, sys, time

import logo

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "tffist")
SITE = "https://tffistanbul.org"
UA = "turk-futbol-db/0.1 (kisisel arsiv)"
CIKTI = os.path.join(KOK, "docs", "logo")
ESLESME = os.path.join(HAM, "eslesme.json")
LOGO_ES = os.path.join(KOK, "logo_tffist.json")
SEZON = {y: 14 + (y - 2010) for y in range(2010, 2027)}   # 2010-2011 -> 14 ... 2026-2027 -> 30
LIG = {1: "super-amator-lig", 2: "1-amator-lig"}


def indir():
    os.makedirs(HAM, exist_ok=True)
    for y, sid in SEZON.items():
        for lid, slug in LIG.items():
            yol = os.path.join(HAM, f"{y}_{lid}.html")
            if os.path.exists(yol) and y < max(SEZON):   # güncel sezon her seferinde yenilenir
                continue
            r = subprocess.run(["curl", "-sfL", "-m", "60", "-A", UA, "-o", yol + ".tmp",
                                f"{SITE}/gruplar/{y}-{y + 1}/{slug}/{sid}/{lid}"])
            if r.returncode == 0:
                os.replace(yol + ".tmp", yol)
                print(y, slug, "tamam", flush=True)
            else:
                print(y, slug, "alınamadı", flush=True)
            time.sleep(2)


def kulupler():
    """tffistanbul kulüp no -> {ad, logo (en yeni sezondaki), sezonlar}"""
    out = {}
    for f in sorted(glob.glob(os.path.join(HAM, "*_*.html"))):
        y = int(os.path.basename(f)[:4])
        t = open(f, encoding="utf-8", errors="replace").read()
        # her kulüp: logo görseli ve /kulup/<ad>/<no> bağlantısı yan yana
        for blok in re.findall(r'<a href="/kulup/.*?</a>', t, re.S):
            no = re.search(r'/kulup/[^"/]+/(\d+)"', blok).group(1)
            img = (re.search(r'<img src="(/images/[^"]+)"', blok) or [None, None])[1]
            ad = html.unescape((re.search(r'team-meta__name">(.*?)</h6>', blok, re.S) or [None, ""])[1]).strip()
            k = out.setdefault(no, {"ad": ad, "logo": None, "son": 0, "sezon": []})
            k["sezon"].append(y)
            if y >= k["son"]:
                k.update(ad=ad, logo=html.unescape(img) if img else k["logo"], son=y)
    return out


def esle():
    K = kulupler()
    print(len(K), "tffistanbul kulübü,", sum(1 for k in K.values() if k["logo"]), "logolu", flush=True)
    ist_kok = collections.defaultdict(set)
    for no, k in K.items():
        ist_kok[logo.kok(k["ad"])].add(no)
    Z = json.load(open(os.path.join(KOK, "docs", "data", "kulupler.json"), encoding="utf-8"))
    var = set()
    for f in ("logo_eslesme.json", "logo_wiki.json", "logo_tff.json"):
        p = os.path.join(KOK, f)
        if os.path.exists(p):
            var |= {k for k, v in json.load(open(p, encoding="utf-8")).items() if v and os.path.exists(os.path.join(CIKTI, f"{v}.png"))}
    c = sqlite3.connect(os.path.join(KOK, "futbol.db"))
    kim = collections.defaultdict(list)
    for kid, k in c.execute("SELECT kulup_id, kaynak || ':' || kaynak_id FROM kulup_kimlik ORDER BY kaynak <> 'tff', son_sezon DESC"):
        kim[kid].append(k)
    adk = {z["id"]: {logo.kok(a[0]) for a in z["adlar"]} | {logo.kok(z["ad"])} for z in Z}
    biz_kok = collections.defaultdict(set)
    for kid, s in adk.items():
        for x in s:
            biz_kok[x].add(kid)
    # grup arkadaşları: aynı sezon, seviye ve grupta lig maçı yapılan kulüpler
    arkadas = collections.defaultdict(set)
    gr = collections.defaultdict(set)
    for kd, sz, g, e, d in c.execute("SELECT kademe, sezon, COALESCE(grup,''), ev_kulup, dep_kulup FROM mac WHERE yarisma='lig'"):
        gr[(kd, sz, g)].update((e, d))
    for uyeler in gr.values():
        for u in uyeler:
            arkadas[u] |= uyeler - {u}
    ist_tum = set(ist_kok)
    out = {}
    for z in Z:
        if not z["yerli"] or z.get("logo") or any(k in var for k in kim[z["id"]]):
            continue
        aday = {no for x in adk[z["id"]] for no in ist_kok.get(x, ())}
        if len(aday) != 1:
            continue
        no = next(iter(aday))
        if not K[no]["logo"] or any(len(biz_kok[x]) > 1 for x in adk[z["id"]] if x in ist_kok):
            continue
        ist_ark = sum(1 for a in arkadas[z["id"]] if adk.get(a, set()) & ist_tum)
        if ist_ark < 3:
            continue
        out[str(z["id"])] = {"kulup": z["ad"], "kimlik": kim[z["id"]][0], "tffist": no, "tffist_ad": K[no]["ad"],
                             "logo": K[no]["logo"], "ist_rakip": ist_ark}
    json.dump(out, open(ESLESME, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(out), "logosuz kulüp tffistanbul'la eşlendi ->", ESLESME, flush=True)


def logo_indir():
    es = json.load(open(ESLESME, encoding="utf-8"))
    gecici = os.path.join(HAM, "logo")
    os.makedirs(gecici, exist_ok=True)
    out = {}
    for v in es.values():
        ad = f"ti{v['tffist']}"
        hedef = os.path.join(CIKTI, ad + ".png")
        if not os.path.exists(hedef):
            ham = os.path.join(gecici, ad + (os.path.splitext(v["logo"])[1] or ".jpg"))
            url = SITE + subprocess.run(["python3", "-c", "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))", v["logo"]],
                                        capture_output=True, text=True).stdout.strip()
            r = subprocess.run(["curl", "-sfL", "-m", "60", "-A", UA, "-o", ham, url])
            if r.returncode != 0 or os.path.getsize(ham) < 200:
                print("indirilemedi", v["kulup"], url, flush=True); continue
            subprocess.run(["sips", "-s", "format", "png", "-Z", "64", ham, "--out", hedef], capture_output=True)
            time.sleep(1)
        if os.path.exists(hedef):
            out[v["kimlik"]] = ad
    json.dump(dict(sorted(out.items())), open(LOGO_ES, "w", encoding="utf-8"), indent=0)
    print(len(out), "logo ->", LOGO_ES, flush=True)


if __name__ == "__main__":
    {"indir": indir, "esle": esle, "logo": logo_indir}[sys.argv[1]]()

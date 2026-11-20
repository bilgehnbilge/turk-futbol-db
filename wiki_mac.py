#!/usr/bin/env python3
"""Türkçe Vikipedi'deki tek maç maddeleri (kupa finalleri, Cumhurbaşkanlığı / Başbakanlık kupaları, ünlü maçlar):
golcüler, dakikalar, stat, hakem. "Kategori:Türkiye futbol kulüplerinin maçları" altındaki kulüp kategorilerinden.

  python3 wiki_mac.py indir     # madde metinleri -> raw/wiki_mac/sayfalar.json (Vikipedi API; yeniden çalışırsa baştan)
  python3 wiki_mac.py ayikla    # ağa çıkmadan -> wiki_mac.json (depoda; web_aktar.py ve eski_site.py okur)

Maddede bir ya da birden çok {{Futbol maçı kutusu}} (iki ayaklı finallerde her maç için bir kutu) olur: date, team1, score,
team2, goals1, goals2 ({{gol|43||58}} dakikalar), stadium, referee. Kutusu olmayan maddelerde bilgi kutusundaki tarih,
takımlar ve skor alınır (golcü yok).
"""
import json, os, re, subprocess, sys, time, urllib.parse

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "wiki_mac")
CIKTI = os.path.join(KOK, "wiki_mac.json")
API = "https://tr.wikipedia.org/w/api.php"
UA = "turk-futbol-db/0.1 (kisisel arsiv)"
KOK_KATEGORI = "Kategori:Türkiye futbol kulüplerinin maçları"
AY = {a: i + 1 for i, a in enumerate(["ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık"])}


def api(**p):
    p.update(format="json", formatversion="2")
    for deneme in range(4):
        r = subprocess.run(["curl", "-s", "-m", "60", "-A", UA, API + "?" + urllib.parse.urlencode(p)], capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except ValueError:
            time.sleep(10 * (deneme + 1))
    raise SystemExit("Vikipedi API cevap vermiyor")


def uyeler(kat, tur):
    out, devam = [], {}
    while True:
        d = api(action="query", list="categorymembers", cmtitle=kat, cmtype=tur, cmlimit="500", **devam)
        out += [m["title"] for m in d["query"]["categorymembers"]]
        if "continue" not in d:
            return out
        devam = {"cmcontinue": d["continue"]["cmcontinue"]}
        time.sleep(0.5)


def indir():
    os.makedirs(HAM, exist_ok=True)
    kategoriler = uyeler(KOK_KATEGORI, "subcat")
    basliklar = set(uyeler(KOK_KATEGORI, "page"))
    for k in kategoriler:
        basliklar |= {b for b in uyeler(k, "page") if not b.startswith("Şablon:")}
        time.sleep(0.5)
    print(len(kategoriler), "kulüp kategorisi,", len(basliklar), "madde", flush=True)
    metin = {}
    l = sorted(basliklar)
    for i in range(0, len(l), 40):
        d = api(action="query", prop="revisions", rvprop="content", rvslots="main", titles="|".join(l[i:i + 40]))
        for p in d["query"]["pages"]:
            if "revisions" in p:
                metin[p["title"]] = p["revisions"][0]["slots"]["main"]["content"]
        time.sleep(1)
    json.dump(metin, open(os.path.join(HAM, "sayfalar.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(len(metin), "madde metni ->", HAM, flush=True)


def sablonlar(t, ad):
    """{{ad ...}} şablonlarının gövdeleri (iç içe şablonlar dahil)"""
    out = []
    for m in re.finditer(r"\{\{\s*" + ad + r"\s*\|", t, re.I):
        i, derinlik = m.start(), 0
        j = i
        while j < len(t):
            if t.startswith("{{", j):
                derinlik += 1; j += 2; continue
            if t.startswith("}}", j):
                derinlik -= 1; j += 2
                if derinlik == 0:
                    break
                continue
            j += 1
        out.append(t[m.end():j - 2])
    return out


def alanlar(govde):
    """şablon gövdesi -> {alan: değer}; | ayırıcısı yalnız en üst düzeyde"""
    parca, derin, kare, bas = [], 0, 0, 0
    for j, ch in enumerate(govde):
        if govde.startswith("{{", j): derin += 1
        elif govde.startswith("}}", j): derin -= 1
        elif govde.startswith("[[", j): kare += 1
        elif govde.startswith("]]", j): kare -= 1
        elif ch == "|" and derin == 0 and kare == 0:
            parca.append(govde[bas:j]); bas = j + 1
    parca.append(govde[bas:])
    out = {}
    for p in parca:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out


def temiz(s):
    s = re.sub(r"<ref[^>]*/>|<ref.*?</ref>", "", s or "", flags=re.S)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"<[^>]+>|'''?", " ", s)
    return re.sub(r"\s+", " ", s).strip(" ,;")


def tarih_coz(s):
    s = temiz(s).lower()
    m = re.search(r"(\d{1,2})\s+(" + "|".join(AY) + r")\s+(\d{4})", s)
    if m:
        return f"{m.group(3)}-{AY[m.group(2)]:02d}-{int(m.group(1)):02d}"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    return m.group(0) if m else None


def goller(s):
    """'[[Gündüz Kılıç]] {{gol|43||58}} <br /> [[Süleyman]] {{gol|49|pen}}' -> [[ad, dk, tip], ...]"""
    out = []
    s = re.sub(r"<ref[^>]*/>|<ref.*?</ref>", "", s or "", flags=re.S)
    for parca in re.split(r"<br\s*/?>|\n|\*", s):
        ad = temiz(re.sub(r"\{\{.*?\}\}", "", parca))
        dks = []
        for g in re.findall(r"\{\{\s*(?:gol|goal|pengol|penaltı|kk|ownGoal|og)\s*\|([^{}]*)\}\}", parca, re.I):
            tip = "P" if re.search(r"pen|p\b", g, re.I) else "K" if re.search(r"\bkk\b|\bog\b|kendi", g, re.I) else None
            for x in re.findall(r"(\d{1,3})(?:\s*\+\s*(\d+))?", g):
                dks.append((int(x[0]), tip))
        if not dks:
            dks = [(int(x), None) for x in re.findall(r"(\d{1,3})'", parca)]
            ad = temiz(re.sub(r"\(?\d{1,3}'\)?", "", ad))
        ad = re.sub(r"\s*\(?\d{1,3}\s*\+?\s*\d*\)?\s*$", "", ad).strip(" ,")
        for dk, tip in dks:
            if ad and dk <= 130:
                out.append([ad, dk, tip])
    return out


POZ = r"(?:KL|K|GK|DF|D|OS|MF|O|FV|FW|F|SB|SĞB|SLB|STP|DOS|OOS|KOS|SF|SĞK|SLK|LB|RB|CB|DM|CM|AM|LW|RW|CF|ST|LM|RM)"
KALIN = "'" * 3


def kadrolar(t):
    """Maç kutularının ardındaki kadro tabloları (kalın 'TAKIM:' başlıklı; satır: | KL || no || {{bayraksimge|X}} [[Ad]] (K) ||
    {{suboff|25}}) -> sırayla [{takim, oyuncu: [[forma, ad, ilk11, girdiği dk, çıktığı dk]], td: [ad]}]. 7'den az oyunculu tablo alınmaz."""
    out = []
    for blok in re.split(r"\n\{\|", t):
        bas = re.search(KALIN + r"([^'\n]{2,40}?):?" + KALIN + r"\s*:?", blok)
        if not bas or not re.search(r"\n\|\s*" + POZ + r"\s*\|\|", blok):
            continue
        oy, td, yedek = [], [], False
        for sat in blok.split("\n|-"):
            s = sat.strip()
            if re.search(r"Yedek|Substitut", s, re.I):
                yedek = True
            m = re.match(r"\|\s*" + POZ + r"\s*\|\|\s*([^|]*?)\s*\|\|(.*)", s, re.S)
            if not m:
                continue
            parca = m.group(2).split("||")
            ad = temiz(re.sub(r"\{\{bayraksimge\|[^}]*\}\}|\(\s*\[\[Kaptan[^\]]*\]\]\s*\)|\(K\)", "", parca[0], flags=re.S))
            ek = " ".join(parca[1:])
            gir = re.search(r"\{\{\s*sub\s*on\s*\|\s*(\d+)", ek, re.I)
            cik = re.search(r"\{\{\s*sub\s*off\s*\|\s*(\d+)", ek, re.I)
            if ad:
                oy.append([temiz(m.group(1)) or None, ad, 0 if (yedek or gir) else 1, int(gir.group(1)) if gir else None,
                           int(cik.group(1)) if cik else None])
        tm = re.search(r"(?:Teknik direktör|Antrenör):?'*\s*\n\|-\s*\n\|[^|\n]*\|(.*?)(?:\n\|\}|\n\|-)", blok, re.S)
        if tm:
            td = [x for x in [temiz(re.sub(r"\{\{bayraksimge\|[^}]*\}\}", "", tm.group(1), flags=re.S))] if x]
        if len(oy) >= 7:
            out.append({"takim": temiz(bas.group(1)), "oyuncu": oy, "td": td})
    return out


def kadro_ata(maclar, tablolar):
    """Maddenin maçlarına kadro tablolarını sırayla ikişer ikişer verir; takım adı tutmazsa (ters sıra) yer değiştirir."""
    import unicodedata
    def k(a):
        a = unicodedata.normalize("NFKD", (a or "").replace("İ", "I").replace("ı", "i")).encode("ascii", "ignore").decode().lower()
        return re.sub(r"\b(sk|jk|fk|spor|kulubu|futbol|takimi)\b|[^a-z]", "", a)
    tut = lambda p, q: bool(p) and bool(q) and (p in q or q in p)
    for i, x in enumerate(maclar):
        cift = tablolar[2 * i: 2 * i + 2]
        if len(cift) != 2:
            break
        a, b, ev, dep = k(cift[0]["takim"]), k(cift[1]["takim"]), k(x["ev"]), k(x["dep"])
        if tut(a, dep) and tut(b, ev):
            cift = cift[::-1]
        elif not (tut(a, ev) or tut(b, dep)):
            continue
        x["k1"], x["k2"] = cift[0]["oyuncu"], cift[1]["oyuncu"]
        x["t1"], x["t2"] = cift[0]["td"], cift[1]["td"]


def ayikla():
    sayfalar = json.load(open(os.path.join(HAM, "sayfalar.json"), encoding="utf-8"))
    out = []
    for baslik, t in sorted(sayfalar.items()):
        bas_ = len(out)
        kutular = sablonlar(t, r"(?:Futbol maçı kutusu|Footballbox(?: collapsible)?|Football box(?: collapsible)?)")
        if kutular:
            for k in kutular:
                a = alanlar(k)
                sk = re.search(r"(\d+)\s*[–\-:]\s*(\d+)", temiz(a.get("score", "")))
                out.append({"madde": baslik, "tarih": tarih_coz(a.get("date", "")), "ev": temiz(a.get("team1")), "dep": temiz(a.get("team2")),
                            "eg": int(sk.group(1)) if sk else None, "dg": int(sk.group(2)) if sk else None,
                            "g1": goller(a.get("goals1")), "g2": goller(a.get("goals2")),
                            "stad": temiz(a.get("stadium", "")).split(" Hakem")[0][:80] or None,
                            "hakem": temiz(a.get("referee", "")) or (re.search(r"Hakem:?\s*'*:?\s*\[?\[?([^\]<|\n]+)", k) or [None, None])[1]})
        else:
            b = next(iter(sablonlar(t, r"Futbol maçı bilgi kutusu")), None)
            if b:
                a = alanlar(b)
                n = lambda x: int(x) if re.fullmatch(r"\d+", temiz(x or "")) else None
                out.append({"madde": baslik, "tarih": tarih_coz(a.get("tarih", "")), "ev": temiz(a.get("takım1")), "dep": temiz(a.get("takım2")),
                            "eg": n(a.get("takım1skor")), "dg": n(a.get("takım2skor")), "g1": [], "g2": [],
                            "stad": temiz(a.get("stadyum", "")) or None, "hakem": temiz(a.get("hakem", "")) or None})
        kadro_ata(out[bas_:], kadrolar(t))
    for x in out:
        if x["hakem"]:
            x["hakem"] = temiz(x["hakem"]).strip(" '") or None
    json.dump(out, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    gol = sum(len(x["g1"]) + len(x["g2"]) for x in out)
    uyum = sum(1 for x in out if x["eg"] is not None and x["g1"] + x["g2"] and len(x["g1"]) == x["eg"] and len(x["g2"]) == x["dg"])
    print(f"{len(sayfalar)} madde -> {len(out)} maç, {gol} gol ({uyum} maçta gol sayısı skorla tutuyor), "
          f"{sum(1 for x in out if x.get('k1'))} maçta kadro -> {CIKTI}")


if __name__ == "__main__":
    {"indir": indir, "ayikla": ayikla}[sys.argv[1]]()


def uyumlu(x):
    """golcü sayısı skorla tutuyor mu (seri penaltıların karıştığı ya da eksik listeler atılır)"""
    return x["eg"] is not None and (x["g1"] or x["g2"]) and len(x["g1"]) == x["eg"] and len(x["g2"]) == x["dg"]


def aktar(maclar, cikti, yaz):
    """web_aktar: Vikipedi maçlarını futbol.db maçlarına bağlar (tarih ±1 gün + skor) -> data/wk.json
    {futbol maç no: {m: [...], o: [olaylar], q: madde}}. Yalnız golcüleri skorla tutan maçlar."""
    import datetime, collections
    if not os.path.exists(CIKTI):
        return []
    W = [x for x in json.load(open(CIKTI, encoding="utf-8")) if x["tarih"] and x["tarih"] >= "1959-01-01" and uyumlu(x)]
    gun = collections.defaultdict(list)
    for m in maclar:
        if m["tarih"] and m["ev_gol"] is not None and m["yarisma"] in ("kupa", "ozel_kupa", "lig"):
            gun[m["tarih"]].append(m)
    # takım adı da tutmalı: maddedeki iki takımdan en az biri (ek ve büyük/küçük harf farkı gözetmeden) kulübün adlarından biri
    import logo
    kad = collections.defaultdict(set)
    kp = os.path.join(cikti, "kulupler.json")
    for z in (json.load(open(kp, encoding="utf-8")) if os.path.exists(kp) else []):
        kad[z["id"]] = {logo.kok(z["ad"])} | {logo.kok(a[0]) for a in z["adlar"]}
    tutar = lambda kid, ad: logo.kok(ad) in kad.get(kid, ()) if ad else False
    out = {}
    for x in W:
        g = datetime.date.fromisoformat(x["tarih"])
        aday = []
        for d in (0, -1, 1):
            for m in gun.get((g + datetime.timedelta(d)).isoformat(), []):
                if (m["ev_gol"], m["dep_gol"]) == (x["eg"], x["dg"]):
                    aday.append((m, False))
                elif (m["ev_gol"], m["dep_gol"]) == (x["dg"], x["eg"]) and x["eg"] != x["dg"]:
                    aday.append((m, True))
            if aday:
                break
        aday = [(m, t) for m, t in aday if tutar(m["ev_kulup"], x["dep" if t else "ev"]) or tutar(m["dep_kulup"], x["ev" if t else "dep"])]
        if len(aday) != 1:
            continue
        m, ters = aday[0]
        g1, g2 = (x["g2"], x["g1"]) if ters else (x["g1"], x["g2"])
        olay = [[1, "GOAL", dk, None, ad, None, {"P": "PENALTY", "K": "OWN"}.get(t)] for ad, dk, t in g1] + \
               [[2, "GOAL", dk, None, ad, None, {"P": "PENALTY", "K": "OWN"}.get(t)] for ad, dk, t in g2]
        olay.sort(key=lambda o: o[2])
        out[m["id"]] = {"m": [m["tarih"], m["saat"], m["sezon"], m["lig"], m["grup"] or "", [m["ev_kulup"], m["ev_adi"]], [m["dep_kulup"], m["dep_adi"]],
                              [m["ev_gol"], m["dep_gol"], m["ev_pen"], m["dep_pen"], m["durum"]]],
                        "o": olay, "q": x["madde"], "s": x.get("stad"), "h": x.get("hakem")}
        if x.get("k1"):   # kadro: [forma, ad, ilk11] ve teknik direktör (sitedeki ev/konuk sırasıyla)
            k1, k2, t1, t2 = (x["k2"], x["k1"], x.get("t2"), x.get("t1")) if ters else (x["k1"], x["k2"], x.get("t1"), x.get("t2"))
            out[m["id"]]["k"] = [[[p[0], p[1], p[2]] for p in k1], [[p[0], p[1], p[2]] for p in k2]]
            out[m["id"]]["t"] = [t1 or [], t2 or []]
    yaz(os.path.join(cikti, "wk.json"), out)
    print(f"Vikipedi maç maddeleri: {len(W)} maçın {len(out)}'i sitedeki maçlara bağlandı -> wk.json", flush=True)
    return list(out)

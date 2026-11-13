"""Cumhurbaşkanlığı / Başbakanlık / Devlet Başkanlığı / Atatürk Kupası ve TFF Süper Kupa maçları: tr.wikipedia basım maddeleri.

  python3 wiki_kupa.py indir    # basım maddelerini raw/wiki_kupa/basimlar.json'a indirir
  python3 wiki_kupa.py ayikla   # wiki_kupa_maclar.csv (kulupler wiki_kupa_kulup.json ile eşlenir)
"""
import csv, json, os, re, sys, urllib.parse, urllib.request

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "wiki_kupa", "basimlar.json")
CSV = os.path.join(KOK, "wiki_kupa_maclar.csv")
UA = {"User-Agent": "turk-futbol-db/0.1 (kisisel arsiv)"}
LISTELER = ["Süper Kupa maçları listesi", "Başbakanlık Kupası maçları listesi"]
AY = {a: i + 1 for i, a in enumerate("ocak şubat mart nisan mayıs haziran temmuz ağustos eylül ekim kasım aralık".split())}


def api(**k):
    u = "https://tr.wikipedia.org/w/api.php?" + urllib.parse.urlencode(dict(format="json", **k))
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))


def icerik(basliklar):
    out = {}
    for i in range(0, len(basliklar), 40):
        d = api(action="query", prop="revisions", rvprop="content", rvslots="main", titles="|".join(basliklar[i:i + 40]), redirects=1)
        for p in d["query"]["pages"].values():
            if "revisions" in p:
                out[p["title"]] = p["revisions"][0]["slots"]["main"]["*"]
    return out


def indir():
    basliklar = []
    for s in icerik(LISTELER).values():
        basliklar += re.findall(r"\[\[(\d{4} [^\]|]*?(?:Kupası|Kupa))\|", s.split("== Kulübe göre")[0])
    basliklar += ["Atatürk Kupası (1998)", "Atatürk Kupası (2000)"]
    os.makedirs(os.path.dirname(HAM), exist_ok=True)
    w = icerik(list(dict.fromkeys(basliklar)))
    w.update({"liste:" + k: v for k, v in icerik(LISTELER).items()})
    json.dump(w, open(HAM, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(w), "madde ->", HAM)


def bloklar(s, ad):
    out = []
    for m in re.finditer(r"\{\{\s*(?:" + ad + r")\s*\n", s, re.I):
        i = j = m.start(); d = 0
        while j < len(s):
            if s.startswith("{{", j): d += 1; j += 2
            elif s.startswith("}}", j):
                d -= 1; j += 2
                if d == 0: break
            else: j += 1
        out.append(s[i:j])
    return out


def alan(b, k):
    m = re.search(r"\n\s*\|\s*" + k + r"\s*=([^\n]*)", b)
    return re.sub(r"<ref.*?(</ref>|/>)", "", m.group(1)).strip() if m else ""


def takim(v):
    m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", v)
    return (m.group(1).strip(), (m.group(2) or m.group(1)).strip()) if m else (v.strip(), v.strip())


def tarih(v):
    v = re.sub(r"\{\{[^}]*?(\d{4})\|(\d{1,2})\|(\d{1,2})[^}]*\}\}", lambda m: f"{m.group(3)} {list(AY)[int(m.group(2)) - 1]} {m.group(1)}", v)
    m = re.search(r"(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})", v)
    return f"{m.group(3)}-{AY[m.group(2).lower().replace('I', 'ı')]:02d}-{int(m.group(1)):02d}" if m and m.group(2).lower() in AY else None


def skor(v):
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)", re.sub(r"\[\[[^\]|]*\|", "", v))
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def listeler(w):
    """liste maddelerinden basım -> (şampiyonun madde adı, seri penaltı skoru notu)"""
    out = {}
    for k, s in w.items():
        if not k.startswith("liste:"):
            continue
        for sat in s.split("== Kulübe göre")[0].split("\n|-"):
            b = re.search(r"\[\[(\d{4} [^\]|]*?(?:Kupası|Kupa))\|", sat)
            hucre = [h.strip() for h in re.split(r"\n[|!]", sat)]
            if not b or len(hucre) < 3:
                continue
            p = re.search(r"penaltı vuruşlarını (\d+)\s*[-–]\s*(\d+)", sat)
            out[b.group(1)] = (takim(hucre[2])[0], (int(p.group(1)), int(p.group(2))) if p else None)
    return out


def ayikla():
    w = json.load(open(HAM, encoding="utf-8"))
    sampiyon = listeler(w)
    satir = []
    for baslik, s in sorted(w.items()):
        if baslik.startswith("liste:"):
            continue
        y = re.search(r"(\d{4})", baslik).group(1)
        ad = ("TFF Süper Kupa" if "Süper Kupa" in baslik else re.sub(r"^\d{4} | \(\d{4}\)$", "", baslik))
        sezon = (f"{int(y)}-{int(y) + 1}" if "Süper Kupa" in baslik else
                 f"{int(y) - 1}-{y}" if "Atatürk" not in baslik else None)
        kutu = bloklar(s, "Futbol maçı kutusu|Footballbox|Football box")
        maclar = []
        for b in kutu:
            e, d = skor(alan(b, "score"))
            ep, dp = skor(alan(b, "penaltyscore"))
            maclar.append(dict(tarih=tarih(alan(b, "date")), ev=takim(alan(b, "team1")), dep=takim(alan(b, "team2")), eg=e, dg=d,
                               ep=ep, dp=dp, tur=alan(b, "round") or "Final", uzatma="1" if alan(b, "aet") else ""))
        if not kutu:
            for b in bloklar(s, "Futbol maçı bilgi kutusu"):
                maclar.append(dict(tarih=tarih(alan(b, "tarih")), ev=takim(alan(b, "takım1")), dep=takim(alan(b, "takım2")),
                                   eg=int(alan(b, "takım1skor")) if alan(b, "takım1skor").isdigit() else None,
                                   dg=int(alan(b, "takım2skor")) if alan(b, "takım2skor").isdigit() else None, ep=None, dp=None,
                                   tur="Final", uzatma="", detay=alan(b, "detay")))
        for i, m in enumerate(maclar):
            if m["eg"] is None:   # oynanmadı (2011 Süper Kupa)
                continue
            if len(maclar) > 1 and i < len(maclar) - 1 and m["tur"] == "Final":
                m["tur"] = "Yarı final"
            kazanan = ""
            if m["tur"] == "Final" and baslik in sampiyon:
                sp, pen = sampiyon[baslik]
                kazanan = "ev" if sp == m["ev"][0] else "dep" if sp == m["dep"][0] else ""
                if m["eg"] == m["dg"] and m["ep"] is None and pen and kazanan:   # penaltı skoru yalnız listede
                    m["ep"], m["dp"] = (max(pen), min(pen)) if kazanan == "ev" else (min(pen), max(pen))
            if "hükmen" in s.lower():
                m["detay"] = "hükmen"
            sz = sezon or (lambda t: f"{t[:4]}-{int(t[:4]) + 1}" if int(t[5:7]) >= 7 else f"{int(t[:4]) - 1}-{t[:4]}")(m["tarih"])
            satir.append(dict(basim=baslik, kupa=ad, sezon=sz, tur=m["tur"], tarih=m["tarih"] or "", ev_wiki=m["ev"][0], ev_adi=m["ev"][1],
                              dep_wiki=m["dep"][0], dep_adi=m["dep"][1], ev_gol="" if m["eg"] is None else m["eg"],
                              dep_gol="" if m["dg"] is None else m["dg"], ev_pen="" if m["ep"] is None else m["ep"],
                              dep_pen="" if m["dp"] is None else m["dp"], kazanan=kazanan, durum="Hük." if "hükmen" in m.get("detay", "").lower() else "MS"))
    with open(CSV, "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(satir[0]), lineterminator="\n")
        wr.writeheader(); wr.writerows(satir)
    print(len(satir), "mac ->", CSV)


if __name__ == "__main__":
    {"indir": indir, "ayikla": ayikla}[sys.argv[1]]()

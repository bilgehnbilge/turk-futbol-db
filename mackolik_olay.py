#!/usr/bin/env python3
"""Maçkolik maç olayları (mackolik_detay.py) -> sitedeki lig maçlarının ayrıntısı: goller, kartlar, oyuncu değişiklikleri.

Kapsam: Süper Lig 1959-1991 ve 1. Lig 1990-91 (TFF'nin gol/kart vermediği maçlar). Türkiye Kupası TFF'den gelir.

  python3 mackolik_olay.py bag     # Maçkolik maç no -> futbol.db maçı eşlemesi -> mackolik_olay_bag.json (depoda)
  (web_aktar.py her çalışmada aktar()'ı çağırır -> docs/data/mk/)

Eşleme: 1984 öncesi maçlar futbol.db'de Maçkolik kaynaklı (aynı maç no). 1984-91 Süper Lig ve 1990-91 1. Lig maçları
TFF kaynaklı: Maçkolik sezon sayfasındaki tarih (±1 gün), iki kulüp ve skorla TFF maçına bağlanır; eşleme TFF maç
noyla mackolik_olay_bag.json'a yazılır (futbol.db maç numaraları her kurulumda değişebilir, TFF maç no değişmez).

Çıktı (maç numarası değil Maçkolik maç noyla anahtarlı; futbol.db no -> Maçkolik no eşlemesi her çalışmada yeniden yazılır):
  mk/dizin.json        futbol.db maç no -> Maçkolik maç no
  mk/m/<no[:2]>.json   maç olayları
raw/mackolik_detay.jsonl yoksa (GitHub Actions) mk/m dosyaları korunur, yalnız dizin yeniden yazılır.
"""
import collections, csv, datetime, json, os, sqlite3, sys

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "mackolik_detay.jsonl")
BAG = os.path.join(KOK, "mackolik_olay_bag.json")
YARISMA = {"superlig": 1, "1lig": 2}
TUR = {("goal", "goal"): ("GOAL", None), ("goal", "penalty-goal"): ("GOAL", "PENALTY"), ("goal", "own-goal"): ("GOAL", "OWN"),
       ("card", "yc"): ("YELLOW_CARD", None), ("card", "rc"): ("RED_CARD", None), ("card", "y2c"): ("YELLOW_CARD_SECOND", None),
       ("substitute", None): ("SUBSTITUTION", None), ("penalty-missed", "pm"): ("PENALTY", None)}


def kayitlar():
    out = {}
    if os.path.exists(HAM):
        for s in open(HAM, encoding="utf-8"):
            x = json.loads(s)
            if x["yarisma"] in YARISMA and x["olaylar"]:
                out[x["id"]] = x
    return out


def bag():
    import mackolik as M, mackolik_detay as D
    c = sqlite3.connect(os.path.join(KOK, "futbol.db"))
    kul = {k: v for k, v in c.execute("SELECT kaynak_id, kulup_id FROM kulup_kimlik WHERE kaynak='mackolik'")}
    meta = {}   # Maçkolik maç no -> (sezon, kademe, tarih, ev uuid, dep uuid, ev gol, dep gol)
    for r in csv.DictReader(open(os.path.join(KOK, "mackolik_maclar.csv"), encoding="utf-8")):
        if r["kaynak"] == "mackolik" and r["yarisma"] == "1lig" and r["sezon"] == "1990-1991":
            meta[r["kaynak_id"]] = (r["sezon"], 2, r["tarih"], r["ev_id"], r["dep_id"], r["ev_gol"], r["dep_gol"])
    for yar, etiket in D.EK_SEZONLAR:
        yol = os.path.join(D.SEZON_HAM, f"{yar}_{etiket}.html.gz")
        if yar in YARISMA and os.path.exists(yol):
            for m in M.maclar(M.oku(yol)):
                meta[m["kaynak_id"]] = (etiket, YARISMA[yar], m["tarih"], m["ev_id"], m["dep_id"], m["ev_gol"], m["dep_gol"])
    aday = collections.defaultdict(list)   # (sezon, kademe) -> TFF maçları
    for kid, sz, kd, tarih, e, d, eg, dg in c.execute("""SELECT kaynak_id, sezon, kademe, tarih, ev_kulup, dep_kulup, ev_gol, dep_gol FROM mac
                                                         WHERE kaynak='tff' AND yarisma='lig' AND sezon<'1991-1992' AND kademe IN (1, 2)"""):
        aday[(sz, kd)].append((kid, tarih, e, d, eg, dg))
    out, say = {}, collections.Counter()
    for mid, (sz, kd, tarih, eu, du, eg, dg) in meta.items():
        if not (str(eg).isdigit() and str(dg).isdigit()) or not tarih:
            continue
        t0 = datetime.date.fromisoformat(tarih)
        gunler = {(t0 + datetime.timedelta(g)).isoformat() for g in (-1, 0, 1)}
        l = [a for a in aday[(sz, kd)] if a[1] in gunler and (a[4], a[5]) == (int(eg), int(dg))]
        ek, dk = kul.get(eu), kul.get(du)
        tam = [a for a in l if ek and dk and (a[2], a[3]) == (ek, dk)]
        # kulübü dönemli kimlikli olan taraf (ör. Maçkolik 'Kale 50 FSK' = 1990-91 Nevşehirspor) eşleşmeyebilir: biri yeter
        tek = [a for a in l if (ek and a[2] == ek) or (dk and a[3] == dk)]
        sec, yol = (tam, "iki kulüp + tarih + skor") if len(tam) == 1 else (tek, "bir kulüp + tarih + skor") if len(tek) == 1 else ([], "")
        if len(sec) == 1:
            out[mid] = "tff:" + sec[0][0]; say[yol] += 1
        else:
            say["bağlanamadı"] += 1
    json.dump(dict(sorted(out.items())), open(BAG, "w", encoding="utf-8"), indent=0)
    print(f"{len(meta)} Maçkolik maçı (1984-91 Süper Lig, 1990-91 1. Lig):", dict(say), "->", BAG)


def dakika(o):
    t = str(o.get("timeMin") or "").replace(" ", "")
    if not t:
        return None, None
    a, _, b = t.partition("+")
    return (int(a), int(b or 0)) if a.isdigit() else (None, None)


def aktar(maclar, cikti, yaz, okunur=lambda s: s):
    """web_aktar: futbol.db maçları (dict) -> mk/ dosyaları; ayrıntısı olan futbol.db maç numaralarını döner."""
    mk = os.path.join(cikti, "mk")
    bag_ = json.load(open(BAG, encoding="utf-8")) if os.path.exists(BAG) else {}
    tff_mk = {v[4:]: k for k, v in bag_.items()}
    K = kayitlar()
    var = set(K) if K else set(json.load(open(os.path.join(mk, "var.json"), encoding="utf-8"))) if os.path.exists(os.path.join(mk, "var.json")) else set()
    dizin, m_ = {}, {}
    for m in maclar:
        if m["yarisma"] != "lig" or m["sezon"] >= "1991-1992":
            continue
        no = m["kaynak_id"] if m["kaynak"] == "mackolik" else tff_mk.get(m["kaynak_id"]) if m["kaynak"] == "tff" else None
        if no in var:
            dizin[m["id"]] = no; m_[no] = m
    if K:
        kova = collections.defaultdict(dict)
        for mid, x in K.items():
            m = m_.get(mid)
            if not m:
                continue
            olay = []
            for o in x["olaylar"]:
                tur = TUR.get((o["type"], o.get("subType")))
                if not tur:
                    continue   # seri penaltılar
                dk, ek = dakika(o)
                taraf = 1 if o.get("position") == "home" else 2
                if tur[0] == "SUBSTITUTION":   # macCiz: oyuncu1 = çıkan, oyuncu2 = giren
                    olay.append([taraf, tur[0], dk, ek or None, o.get("playerOutName"), o.get("playerName"), None])
                else:
                    olay.append([taraf, tur[0], dk, ek or None, o.get("playerName"), None, tur[1]])
            olay.sort(key=lambda x: (x[2] is None, x[2] or 0, x[3] or 0))
            kova[mid[:2]][mid] = {"m": [m["tarih"], m["saat"], m["sezon"], m["lig"], m["grup"] or "", [m["ev_kulup"], okunur(m["ev_adi"])],
                                        [m["dep_kulup"], okunur(m["dep_adi"])], [m["ev_gol"], m["dep_gol"], m["ev_pen"], m["dep_pen"], m["durum"]]],
                                  "o": olay}
        if os.path.isdir(os.path.join(mk, "m")):
            import shutil
            shutil.rmtree(os.path.join(mk, "m"))
        for b, d in kova.items():
            yaz(os.path.join(mk, "m", f"{b}.json"), d)
        yaz(os.path.join(mk, "var.json"), sorted(K))
    yaz(os.path.join(mk, "dizin.json"), dizin)
    print(f"Maçkolik olayları: {len(dizin)} lig maçına bağlandı -> {mk}")
    return sorted(dizin)


if __name__ == "__main__":
    {"bag": bag}[sys.argv[1]]()

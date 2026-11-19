#!/usr/bin/env python3
"""1959 öncesi bölümünün verisi: raw/rsssf_eski/eski.json (rsssf_eski.py ayikla) -> docs/data/eski.json.
web_aktar.py çağırır; ham veri yoksa (GitHub'daki bot) mevcut docs/data/eski.json olduğu gibi kalır.

Kulüpler sitedeki kulüplere adla bağlanır: ad (şehir ekleri atılarak) sitedeki tek bir kulübün adlarından biriyle
birebir tutmalı ve o kulüp 1963'ten önce de oynamış olmalı (aynı adlı sonraki kulüplere bağlanmasın). ELLE ile düzeltilir.
"""
import collections, json, os, re

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "rsssf_eski", "eski.json")
CIKTI = os.path.join(KOK, "docs", "data", "eski.json")
YARISMA = {"milli_kume": "Millî Küme", "sampiyona": "Türkiye Futbol Şampiyonası", "basbakanlik": "Başbakanlık Kupası",
           "federasyon": "Federasyon Kupası", "istanbul": "İstanbul Ligi"}
ACIKLAMA = {
    "milli_kume": "İstanbul, Ankara ve İzmir liglerinin en iyi takımlarıyla oynanan ilk ulusal lig (1937-1951).",
    "sampiyona": "Bölge şampiyonları arasında oynanan Türkiye şampiyonluğu turnuvası (1924-1951).",
    "basbakanlik": "Millî Küme ve Türkiye Şampiyonası kazananları arasında tek maç (1944-1950).",
    "federasyon": "Avrupa Kupası'na katılacak kulübü belirlemek için düzenlenen turnuva (1956-1958); Millî Lig'in öncüsü.",
    "istanbul": "İstanbul Futbol Ligi; RSSSF'de yalnız 1924'ün eleme turnuvası maç maç var.",
}
# ad -> sitedeki kulüp no (None: bağlama). Otomatik eşlemenin üstüne yazılır.
ELLE = {"Güneş": None,   # İstanbul Güneş SK (1930'lar); Ankara Güneşspor değil
        "Güneşspor": None, "Hacettepe": None}


def main():
    if not os.path.exists(HAM):
        return
    import logo
    d = json.load(open(HAM, encoding="utf-8"))
    Z = json.load(open(os.path.join(KOK, "docs", "data", "kulupler.json"), encoding="utf-8"))
    idx = collections.defaultdict(set)
    for z in Z:
        if z["yerli"] and z["ilk"][:4] <= "1963":
            for a in [z["ad"]] + [x[0] for x in z["adlar"]]:
                idx[logo.kok(a)].add(z["id"])
    adlar = collections.Counter()
    for m in d["maclar"]:
        adlar[m["ev"]] += 1; adlar[m["dep"]] += 1
    kulup = {}
    for a in adlar:
        sade = re.sub(r"\s+(Istanbul|İstanbul|Ankara|İzmir|Izmir)$", "", a)
        if a in ELLE or sade in ELLE:
            k = ELLE.get(a, ELLE.get(sade))
        else:
            c = idx.get(logo.kok(sade), set())
            k = next(iter(c)) if len(c) == 1 else None
        kulup[a] = k
    # kulüp listesi: aynı ada (şehir eki atılmış) tek kayıt
    no = {}
    liste = []
    for a, n in adlar.most_common():
        sade = re.sub(r"\s+(Istanbul|İstanbul|Ankara|İzmir|Izmir)$", "", a)
        if sade not in no:
            no[sade] = len(liste)
            liste.append({"ad": sade, "kulup": kulup[a], "mac": 0})
        no[a] = no[sade]
    sezonlar = collections.defaultdict(lambda: {"maclar": [], "tablo": None, "kral": []})
    # Millî Küme: sonuç tablosunda zaten olan eşleşme ayrıca listede yazılıysa (yarıda kalan maç) notu tablodaki maça taşınır
    matris = {(m["sezon"], m["ev"], m["dep"]): m for m in d["maclar"] if m.get("kaynak") == "matris"}
    tut = []
    for m in d["maclar"]:
        e = matris.get((m["sezon"], m["ev"], m["dep"])) if m["yarisma"] == "milli_kume" and m.get("kaynak") == "liste" else None
        if e:
            e["not"] = m.get("not") or m.get("durum")
        else:
            tut.append(m)
    for m in tut:
        s = sezonlar[(m["yarisma"], m["sezon"])]
        liste[no[m["ev"]]]["mac"] += 1; liste[no[m["dep"]]]["mac"] += 1
        g = [[x[0], x[1], x[2], x[3], x[4]] for x in m.get("goller", [])]
        s["maclar"].append([no[m["ev"]], no[m["dep"]], m["eg"], m["dg"], m.get("tur") or "", m.get("tarih"), m.get("durum"),
                            m.get("not"), m.get("sehir"), m.get("stad"), m.get("hakem"), g])
    for t in d["tablolar"]:
        s = sezonlar[(t["yarisma"], t["sezon"])]
        satir = [[r[0], no.get(r[1], no.get(r[1] + " Istanbul")), r[1], *r[2:]] for r in t["satir"]]
        if s["tablo"] is None:
            s["tablo"] = []
        s["tablo"].append({"tur": t.get("tur") or "", "satir": satir})
    for k in d["krallar"]:
        sezonlar[(k["yarisma"], k["sezon"])]["kral"].append([k["ad"], k["kulup"], k["gol"]])
    # şampiyon: lig tablosunun ya da final grubunun birincisi; yoksa finalin (son maçın) kazananı
    out = []
    for (y, sz), s in sorted(sezonlar.items(), key=lambda x: (x[0][1], list(YARISMA).index(x[0][0]))):
        if not s["maclar"] and not s["tablo"]:
            continue
        sam = None
        tl = [t for t in (s["tablo"] or []) if t["tur"] in ("", "Final grubu", "Lig")]
        if tl and tl[-1]["satir"] and tl[-1]["satir"][0][1] is not None:
            sam = tl[-1]["satir"][0][1]
        else:
            son = [m for m in s["maclar"] if m[4].startswith("Final") or m[4] in ("Şampiyonluk maçı", "Tekrar") or y == "basbakanlik"]
            if son and son[-1][2] is not None and son[-1][2] != son[-1][3]:
                sam = son[-1][0] if son[-1][2] > son[-1][3] else son[-1][1]
        out.append({"yarisma": y, "sezon": sz, "sampiyon": sam, **s})
    json.dump({"yarismalar": [[k, v, ACIKLAMA[k]] for k, v in YARISMA.items()], "kulupler": liste, "sezonlar": out,
               "alanlar": ["ev", "dep", "ev_gol", "dep_gol", "tur", "tarih", "durum", "not", "sehir", "stad", "hakem", "goller"]},
              open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    bagli = sum(1 for k in liste if k["kulup"])
    print(f"1959 öncesi: {len(out)} yarışma-sezon, {sum(len(s['maclar']) for s in out)} maç, {len(liste)} kulüp "
          f"({bagli} sitedeki kulübe bağlı) -> {CIKTI}")


if __name__ == "__main__":
    main()

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
           "federasyon": "Federasyon Kupası", "istanbul": "İstanbul Ligi", "diger": "Ünlü maçlar"}
ACIKLAMA = {
    "milli_kume": "İstanbul, Ankara ve İzmir liglerinin en iyi takımlarıyla oynanan ilk ulusal lig (1937-1951).",
    "sampiyona": "Bölge şampiyonları arasında oynanan Türkiye şampiyonluğu turnuvası (1924-1951).",
    "basbakanlik": "Millî Küme ve Türkiye Şampiyonası kazananları arasında tek maç (1944-1950).",
    "federasyon": "Avrupa Kupası'na katılacak kulübü belirlemek için düzenlenen turnuva (1956-1958); Millî Lig'in öncüsü.",
    "istanbul": "İstanbul Futbol Ligi; RSSSF'de yalnız 1924'ün eleme turnuvası maç maç var.",
    "diger": "Vikipedi'de ayrı maddesi olan, yukarıdaki yarışmaların dışındaki maçlar (İstanbul Ligi derbileri, Gazi Büstü).",
}
# ad -> sitedeki kulüp no (None: bağlama). Otomatik eşlemenin üstüne yazılır.
ELLE = {"Güneş": None,   # İstanbul Güneş SK (1930'lar); Ankara Güneşspor değil (logosu LOGO'da)
        "Güneşspor": "ad:Ankara Güneşspor",   # 1956-57 Federasyon Kupası: Ankara Güneşspor (kullanıcı)
        "Hacettepe": None,
        "Eskişehir Demirspor": "tff:3667"}
# sitede kulübü olmayan eski kulüplerin logoları (docs/logo/<ad>.png; kullanıcının verdiği)
LOGO = {"Güneş": "e_gunes", "Harp Okulu": "e_harp_okulu", "Harbiye": "e_harp_okulu"}
# aynı kulübün dönem adları (kulüp listesinde "ayni": öbür adın sırası). Harbiye 1936'da Ankara'ya taşınıp Harp Okulu
# adını aldı (tr.wikipedia Harp_Okulu_SK; kullanıcı). Bu kulüplerin başka kaynaklardan verisi gelince aynı kimliğe bağlanır.
AYNI = {"Harbiye": "Harp Okulu", "Harp Okulu": "Harbiye"}   # "tff:<no>": o TFF numaralı kulüp (1959 öncesi Demirspor = bugünkü kulüp, kullanıcı)


def main():
    if not os.path.exists(HAM):
        return
    import logo
    d = json.load(open(HAM, encoding="utf-8"))
    for m in d["maclar"]:
        m.pop("wiki", None)
    Z = json.load(open(os.path.join(KOK, "docs", "data", "kulupler.json"), encoding="utf-8"))
    idx = collections.defaultdict(set)
    for z in Z:
        if z["yerli"] and z["ilk"][:4] <= "1963":
            for a in [z["ad"]] + [x[0] for x in z["adlar"]]:
                idx[logo.kok(a)].add(z["id"])
    tff_no = {f"tff:{t}": z["id"] for z in Z for t in z.get("tff") or []}
    tff_no.update({f"ad:{z['ad']}": z["id"] for z in Z if z["yerli"]})   # ELLE'de "ad:<sitedeki ad>" da olur
    # Vikipedi'deki tek maç maddeleri (wiki_mac.py): RSSSF'deki maça golcü ve tarih; RSSSF'de olmayanlar "Ünlü maçlar"
    W = json.load(open(os.path.join(KOK, "wiki_mac.json"), encoding="utf-8")) if os.path.exists(os.path.join(KOK, "wiki_mac.json")) else []
    WIKI_ELLE = {("Fenerbahçe 0-7 Galatasaray", "1911-02-12"): ([], [["Celal İbrahim", None, None]] * 4 + [["Emin Bülent", None, None]] * 2 + [["İdris", None, None]])}
    # Vikipedi kadrosu: [ev oyuncuları, konuk oyuncuları, ev teknik direktörü, konuk]; oyuncu [ad, ilk11, girdiği dk, çıktığı dk]
    def kadro(w, ters):
        a, b = ("2", "1") if ters else ("1", "2")
        return [[[p[1], p[2], p[3], p[4]] for p in w["k" + a]], [[p[1], p[2], p[3], p[4]] for p in w["k" + b]],
                w.get("t" + a) or [], w.get("t" + b) or []]
    kk = lambda a: logo.kok(re.sub(r"\s+(Istanbul|İstanbul|Ankara|İzmir|Izmir)$", "", a or ""))
    for w in W:
        if not w["tarih"] or w["tarih"] >= "1959-08" or w["eg"] is None:
            continue
        g1, g2 = WIKI_ELLE.get((w["madde"], w["tarih"]), (w["g1"], w["g2"]))
        bul = None
        for m in d["maclar"]:
            if m["yarisma"] == "basbakanlik" and m.get("tarih") == w["tarih"]:
                bul = ("var", m); break
            if m["sezon"][:4] == w["tarih"][:4] and m["eg"] is not None:
                if (kk(m["ev"]), kk(m["dep"]), m["eg"], m["dg"]) == (kk(w["ev"]), kk(w["dep"]), w["eg"], w["dg"]):
                    bul = ("ayni", m); break
                if (kk(m["ev"]), kk(m["dep"]), m["eg"], m["dg"]) == (kk(w["dep"]), kk(w["ev"]), w["dg"], w["eg"]):
                    bul = ("ters", m); break
        if bul and bul[0] == "var":
            continue
        if bul:
            m = bul[1]
            a1, a2 = (g1, g2) if bul[0] == "ayni" else (g2, g1)
            m.setdefault("tarih", None)
            m["tarih"] = m["tarih"] or (w["tarih"] if bul[0] == "ayni" else None)
            m["goller"] = [[None, None, a, dk, None] for a, dk, _ in a1] + [[None, None, a, dk, "dep"] for a, dk, _ in a2]
            m["wiki"] = w["madde"]
            if w.get("k1"):
                m["kadro"] = kadro(w, bul[0] == "ters")
        else:
            d["maclar"].append({"yarisma": "diger", "sezon": w["tarih"][:4], "tur": w["madde"], "tarih": w["tarih"], "ev": w["ev"], "dep": w["dep"],
                                "eg": w["eg"], "dg": w["dg"], "stad": w.get("stad"), "hakem": w.get("hakem"), "kaynak": "wiki", "wiki": w["madde"],
                                "goller": [[None, None, a, dk, None] for a, dk, _ in g1] + [[None, None, a, dk, "dep"] for a, dk, _ in g2],
                                **({"kadro": kadro(w, False)} if w.get("k1") else {})})
    adlar = collections.Counter()
    for m in d["maclar"]:
        adlar[m["ev"]] += 1; adlar[m["dep"]] += 1
    kulup = {}
    for a in adlar:
        sade = re.sub(r"\s+(Istanbul|İstanbul|Ankara|İzmir|Izmir)$", "", re.split(r"\s{3,}", a)[0])   # RSSSF notu yapışmış adlar
        if a in ELLE or sade in ELLE:
            k = ELLE.get(a, ELLE.get(sade))
            k = tff_no.get(k) if isinstance(k, str) else k
        else:
            c = idx.get(logo.kok(sade), set())
            k = next(iter(c)) if len(c) == 1 else None
        kulup[a] = k
    # kulüp listesi: aynı ada (şehir eki atılmış) tek kayıt
    no = {}
    liste = []
    for a, n in adlar.most_common():
        sade = re.sub(r"\s+(Istanbul|İstanbul|Ankara|İzmir|Izmir)$", "", re.split(r"\s{3,}", a)[0])   # RSSSF notu yapışmış adlar
        if sade not in no:
            no[sade] = len(liste)
            liste.append({"ad": sade, "kulup": kulup[a], "mac": 0, **({"logo": LOGO[sade]} if sade in LOGO and kulup[a] is None else {})})
        no[a] = no[sade]
    for x in liste:
        if x["ad"] in AYNI and AYNI[x["ad"]] in no:
            x["ayni"] = no[AYNI[x["ad"]]]
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
        # gol: [ad, dakika, tip, taraf (1 ev / 2 konuk; RSSSF'de ara skordan)]
        g, onceki = [], (0, 0)
        for x in m.get("goller", []):
            if x[0] is not None:   # RSSSF: "2-1 Ad 52'" ara skor
                taraf = 1 if x[0] > onceki[0] else 2
                onceki = (x[0], x[1])
                g.append([x[2], x[3], x[4], taraf])
            else:
                g.append([x[2], x[3], None, 2 if x[4] == "dep" else 1])
        s["maclar"].append([no[m["ev"]], no[m["dep"]], m["eg"], m["dg"], m.get("tur") or "", m.get("tarih"), m.get("durum"),
                            m.get("not"), m.get("sehir"), m.get("stad"), m.get("hakem"), g, m.get("wiki"), m.get("kadro")])
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
        if y == "diger":
            out.append({"yarisma": y, "sezon": sz, "sampiyon": None, **s}); continue
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
               "alanlar": ["ev", "dep", "ev_gol", "dep_gol", "tur", "tarih", "durum", "not", "sehir", "stad", "hakem", "goller", "wiki", "kadro"]},
              open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    bagli = sum(1 for k in liste if k["kulup"])
    print(f"1959 öncesi: {len(out)} yarışma-sezon, {sum(len(s['maclar']) for s in out)} maç, {len(liste)} kulüp "
          f"({bagli} sitedeki kulübe bağlı) -> {CIKTI}")


if __name__ == "__main__":
    main()

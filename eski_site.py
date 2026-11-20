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
           "federasyon": "Federasyon Kupası", "istanbul": "İstanbul Ligi", "ankara": "Ankara Ligi", "izmir": "İzmir Ligi",
           "istanbul2": "İstanbul 2. Ligi", "ankara2": "Ankara 2. Ligi", "diger": "Ünlü maçlar"}
ACIKLAMA = {
    "milli_kume": "İstanbul, Ankara ve İzmir liglerinin en iyi takımlarıyla oynanan lig (1937-1951).",
    "sampiyona": "Bölge şampiyonları arasında oynanan Türkiye şampiyonluğu turnuvası (1924-1951).",
    "basbakanlik": "Millî Küme ve Türkiye Şampiyonası kazananları arasında tek maç (1944-1950).",
    "federasyon": "Avrupa Kupası'na katılacak kulübü belirlemek için düzenlenen turnuva (1956-1958); Millî Lig'in öncüsü.",
    "istanbul": "İstanbul Futbol Birliği Ligi (1904-), Cuma Ligi, İstanbul Ligi ve 1952'den Profesyonel Lig; Maçkolik arşivi (1924: RSSSF).",
    "ankara": "Ankara Ligi; 1955'ten Ankara Profesyonel Ligi (Maçkolik arşivi).",
    "izmir": "İzmir Ligi; 1955'ten İzmir Profesyonel Ligi (Maçkolik arşivi).",
    "istanbul2": "İstanbul Profesyonel 2. Ligi (Maçkolik arşivi).",
    "ankara2": "Ankara Profesyonel 2. Ligi (Maçkolik arşivi).",
    "diger": "Vikipedi'de ayrı maddesi olan, yukarıdaki yarışmaların dışındaki maçlar (İstanbul Ligi derbileri, Gazi Büstü).",
}
# ad -> sitedeki kulüp no (None: bağlama). Otomatik eşlemenin üstüne yazılır.
ELLE = {"Güneş": None,   # İstanbul Güneş SK (1930'lar); Ankara Güneşspor değil (logosu LOGO'da)
        "Güneşspor": "ad:Ankara Güneşspor",   # 1956-57 Federasyon Kupası: Ankara Güneşspor (kullanıcı)
        "Hacettepe": None,
        "Eskişehir Demirspor": "tff:3667"}
# sitede kulübü olmayan eski kulüplerin logoları (docs/logo/<ad>.png; kullanıcının verdiği)
LOGO = {"Güneş": "e_gunes", "Harp Okulu": "e_harp_okulu", "Harbiye": "e_harp_okulu", "Topkapı": "e_topkapi",
        "Hilal (İstanbul)": "e_goztepe_hilal", "Hilâl": "e_goztepe_hilal", "Göztepe Hilal": "e_goztepe_hilal"}
# aynı kulübün dönem adları (kulüp listesinde "ayni": öbür adın sırası). Harbiye 1936'da Ankara'ya taşınıp Harp Okulu
# adını aldı (tr.wikipedia Harp_Okulu_SK; kullanıcı). Bu kulüplerin başka kaynaklardan verisi gelince aynı kimliğe bağlanır.
# İstanbul Hilal (1912) bugün Göztepe Hilal; RSSSF 1924'te "Hilâl", Maçkolik'te "Hilal (İstanbul)" (kullanıcı).
AYNI = {"Harbiye": "Harp Okulu", "Harp Okulu": "Harbiye", "Hilâl": "Hilal (İstanbul)", "Hilal (İstanbul)": "Hilâl",
        "Göztepe Hilal": "Hilal (İstanbul)"}   # "tff:<no>": o TFF numaralı kulüp (1959 öncesi Demirspor = bugünkü kulüp, kullanıcı)


def mackolik_ekle(d, kk):
    """Maçkolik arşivinin 1959 öncesi lig maçları (mackolik_eski.site_maclar) -> d["maclar"], d["tablolar"], d["krallar"].
    Millî Küme maçları RSSSF'deki maça (yıl, takımlar, skor) tarih, gol ve kadro olarak eklenir; RSSSF'nin İstanbul Ligi sezonu
    Maçkolik'te varsa RSSSF'ninki atılır. Döner: {takım adı: sitedeki kulüp no} (Maçkolik arşiv takım numarasıyla)."""
    import sqlite3
    try:
        import mackolik_eski
        ms = mackolik_eski.site_maclar()
    except Exception as e:
        print("  Maçkolik 1959 öncesi verisi okunamadı:", e)
        return {}
    db = os.path.join(KOK, "futbol.db")
    kim = dict(sqlite3.connect(db).execute("SELECT kaynak_id, kulup_id FROM kulup_kimlik WHERE kaynak='mackolik_arsiv'")) if os.path.exists(db) else {}
    mk_kulup = {}
    for m in ms:
        for a, k in ((m["ev"], m["mk_ev"]), (m["dep"], m["mk_dep"])):
            if k in kim:
                mk_kulup.setdefault(a, kim[k])
    # RSSSF İstanbul Ligi sezonu Maçkolik'te de varsa çıkar
    mk_yil = {y for m in ms if m["yarisma"] == "istanbul" for y in re.findall(r"\d{4}", m["sezon"])}
    d["maclar"] = [m for m in d["maclar"] if not (m["yarisma"] == "istanbul" and m.get("kaynak") != "wiki" and m["sezon"][:4] in mk_yil)]
    d["tablolar"] = [t for t in d["tablolar"] if not (t["yarisma"] == "istanbul" and t["sezon"][:4] in mk_yil)]
    gruplar = collections.defaultdict(list)
    eklenen = birlesen = 0
    for m in ms:
        g_hazir = [[a, dk, tip, t] for a, dk, tip, t in m.get("goller") or []]
        if m["yarisma"] == "milli_kume":
            yil = set(re.findall(r"\d{4}", m["sezon"]))
            for r in d["maclar"]:
                if r["yarisma"] == "milli_kume" and r["sezon"][:4] in yil and (kk(r["ev"]), kk(r["dep"]), r["eg"], r["dg"]) == (kk(m["ev"]), kk(m["dep"]), m["eg"], m["dg"]):
                    r["tarih"] = r.get("tarih") or m["tarih"]
                    if g_hazir and not r.get("goller"):
                        r["g_hazir"] = g_hazir
                    if m.get("kadro") and not r.get("kadro"):
                        r["kadro"] = m["kadro"]
                    birlesen += 1
                    break
            continue
        r = {"yarisma": m["yarisma"], "sezon": m["sezon"], "tur": f"{m['hafta']}. hafta", "tarih": m["tarih"], "ev": m["ev"], "dep": m["dep"],
             "eg": m["eg"], "dg": m["dg"], "kaynak": "mackolik"}
        if g_hazir:
            r["g_hazir"] = g_hazir
        if m.get("kadro"):
            r["kadro"] = m["kadro"]
        d["maclar"].append(r); eklenen += 1
        gruplar[(m["yarisma"], m["sezon"])].append(r)
    # puan durumu (maç sonuçlarından; galibiyet 2, beraberlik 1) ve gol kralı (maçların çoğunun golcüsü biliniyorsa)
    for (y, sz), l in gruplar.items():
        t = collections.defaultdict(lambda: [0] * 7)
        for r in l:
            for a, b, x, z in ((r["ev"], r["dep"], r["eg"], r["dg"]), (r["dep"], r["ev"], r["dg"], r["eg"])):
                v = t[a]; v[0] += 1; v[1] += x > z; v[2] += x == z; v[3] += x < z; v[4] += x; v[5] += z; v[6] += 2 * (x > z) + (x == z)
        sira = sorted(t.items(), key=lambda kv: (-kv[1][6], -(kv[1][4] - kv[1][5]), -kv[1][4]))
        tam = {v[0] for _, v in sira} == {2 * (len(sira) - 1)}   # çift devreli lig tamam mı (arşivde eksik maç yoksa)
        d["tablolar"].append({"yarisma": y, "sezon": sz, "tur": "", "hesap": 1, **({} if tam else {"eksik": 1}),
                              "satir": [[i + 1, a, *v] for i, (a, v) in enumerate(sira)]})
        golcu = [r for r in l if r.get("g_hazir")]
        if len(golcu) >= 0.8 * len(l):
            say = collections.Counter()
            for r in golcu:
                for a, dk, tip, taraf in r["g_hazir"]:
                    if tip != "og":
                        say[(a, r["ev"] if taraf == 1 else r["dep"])] += 1
            if say:
                en = max(say.values())
                d["krallar"] += [{"yarisma": y, "sezon": sz, "ad": a, "kulup": k, "gol": n} for (a, k), n in say.items() if n == en]
    print(f"  Maçkolik 1959 öncesi: {eklenen} lig maçı eklendi, {birlesen} Millî Küme maçına tarih/gol/kadro; "
          f"{sum(1 for m in ms if m.get('kadro'))} maçta kadro")
    return mk_kulup


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
    mk_kulup = mackolik_ekle(d, kk)
    adlar = collections.Counter()
    for m in d["maclar"]:
        adlar[m["ev"]] += 1; adlar[m["dep"]] += 1
    kulup = {}
    for a in adlar:
        sade = re.sub(r"\s+(Istanbul|İstanbul|Ankara|İzmir|Izmir)$", "", re.split(r"\s{3,}", a)[0])   # RSSSF notu yapışmış adlar
        if a in ELLE or sade in ELLE:
            k = ELLE.get(a, ELLE.get(sade))
            k = tff_no.get(k) if isinstance(k, str) else k
        elif a in mk_kulup:   # Maçkolik arşiv takım numarası sitedeki kulübün kimliği
            k = mk_kulup[a]
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
        for x in ([] if "g_hazir" in m else m.get("goller", [])):
            if x[0] is not None:   # RSSSF: "2-1 Ad 52'" ara skor
                taraf = 1 if x[0] > onceki[0] else 2
                onceki = (x[0], x[1])
                g.append([x[2], x[3], x[4], taraf])
            else:
                g.append([x[2], x[3], None, 2 if x[4] == "dep" else 1])
        g = m.get("g_hazir", g)
        s["maclar"].append([no[m["ev"]], no[m["dep"]], m["eg"], m["dg"], m.get("tur") or "", m.get("tarih"), m.get("durum"),
                            m.get("not"), m.get("sehir"), m.get("stad"), m.get("hakem"), g, m.get("wiki"), m.get("kadro")])
    for t in d["tablolar"]:
        s = sezonlar[(t["yarisma"], t["sezon"])]
        satir = [[r[0], no.get(r[1], no.get(r[1] + " Istanbul")), r[1], *r[2:]] for r in t["satir"]]
        if s["tablo"] is None:
            s["tablo"] = []
        s["tablo"].append({"tur": t.get("tur") or "", "satir": satir, **{k: 1 for k in ("hesap", "eksik") if t.get(k)}})
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
        tl = [t for t in (s["tablo"] or []) if t["tur"] in ("", "Final grubu", "Lig") and not t.get("eksik")]   # eksik hesaplanmış tablo: şampiyon yok
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

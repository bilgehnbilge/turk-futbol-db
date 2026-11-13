"""'Sayılarla Türk futbolu' sayfası ve kulüplerin lig yolculuğu için özet veriler (web_aktar.py çağırır).

  data/sayilar.json   sezon istatistikleri (lig başına), skor dağılımı (on yıl başına), derbiler
  data/yolculuk.json  her kulübün sezon sezon kademesi ve sırası
"""
import collections

DERBI = {846: "Galatasaray", 463: "Fenerbahçe", 95: "Beşiktaş", 115: "Trabzonspor"}
SKOR_UST = 5   # 5 ve üstü tek hücre ("5+")


def baslangic(sezon):
    return int(sezon[:4])


def puan_sistemi(sezon):
    return 3 if baslangic(sezon) >= 1987 else 2


def gol(m):
    if m["durum"] == "Çifte H":
        return 0, 3
    return m["ev_gol"], m["dep_gol"]


def sezon_istat(maclar):
    """kademe -> [[sezon, maç, gol, ev galibiyeti, beraberlik, deplasman galibiyeti, 1-0, 1-1, 0-0]]"""
    t = collections.defaultdict(lambda: [0] * 8)
    for m in maclar:
        if m["yarisma"] != "lig" or m["asama"] != "lig" or m["durum"] != "MS" or m["ev_gol"] is None or not m["kademe"]:
            continue
        e, d = m["ev_gol"], m["dep_gol"]
        x = t[(m["kademe"], m["sezon"])]
        x[0] += 1; x[1] += e + d
        x[2 if e > d else 3 if e == d else 4] += 1
        if {e, d} == {1, 0}: x[5] += 1
        elif e == d == 1: x[6] += 1
        elif e == d == 0: x[7] += 1
    out = collections.defaultdict(list)
    for (k, s), x in sorted(t.items(), key=lambda kv: (kv[0][0], baslangic(kv[0][1]), kv[0][1])):
        out[k].append([s, *x])
    return out


def skor_dagilimi(maclar):
    """kademe -> on yıl -> {"e-d": maç}; 'tum' = bütün ligler"""
    out = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for m in maclar:
        if m["yarisma"] != "lig" or m["asama"] != "lig" or m["durum"] != "MS" or m["ev_gol"] is None or not m["kademe"]:
            continue
        k = f"{min(m['ev_gol'], SKOR_UST)}-{min(m['dep_gol'], SKOR_UST)}"
        on = f"{baslangic(m['sezon']) // 10 * 10}"
        for kd in (str(m["kademe"]), "tum"):
            out[kd][on][k] += 1
            out[kd]["tum"][k] += 1
    return {kd: {on: dict(c) for on, c in d.items()} for kd, d in out.items()}


def derbiler(maclar):
    out = []
    for m in maclar:
        if m["ev_kulup"] in DERBI and m["dep_kulup"] in DERBI and m["yarisma"] in ("lig", "kupa", "ozel_kupa") \
                and m["ev_gol"] is not None and m["durum"] in ("MS", None) and m["asama"] != "gecersiz":
            out.append([m["tarih"], m["sezon"], {"lig": "L", "kupa": "K", "ozel_kupa": "O"}[m["yarisma"]],
                        m["ev_kulup"], m["dep_kulup"], m["ev_gol"], m["dep_gol"], m["ev_pen"], m["dep_pen"]])
    return out


def yolculuk(maclar, resmi):
    """kulüp -> [[sezon, kademe, sıra, takım sayısı]]. Sıra: resmi puan tablosu varsa o, yoksa sonuçlardan hesap
    (galibiyet 1987-88 öncesi 2, sonra 3 puan; eşitlikte averaj, sonra atılan gol)."""
    grup = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0]))   # (sezon, kademe, grup) -> kulup -> [P, AG, YG]
    for m in maclar:
        if m["yarisma"] != "lig" or m["asama"] != "lig" or not m["kademe"] or m["ev_kulup"] is None or m["dep_kulup"] is None:
            continue
        g = grup[(m["sezon"], m["kademe"], m["grup"] or "")]
        g[m["ev_kulup"]]; g[m["dep_kulup"]]   # oynanmamış maçı olan takım da tabloda
        if m["ev_gol"] is None:
            continue
        e, d = gol(m)
        p = puan_sistemi(m["sezon"])
        for k, a, y in ((m["ev_kulup"], e, d), (m["dep_kulup"], d, e)):
            g[k][0] += p if a > y else 1 if a == y else 0
            g[k][1] += a; g[k][2] += y
    out = collections.defaultdict(list)
    for (sezon, kd, gr), tak in grup.items():
        sira = resmi.get((sezon, kd, gr))
        if not sira or set(sira) != set(tak):
            sirali = sorted(tak, key=lambda k: (-tak[k][0], -(tak[k][1] - tak[k][2]), -tak[k][1]))
            sira = {k: i + 1 for i, k in enumerate(sirali)}
        for k in tak:
            out[k].append([sezon, kd, sira[k], len(tak)])
    for k in out:
        # aynı sezonda iki grup (ör. ilk yarı / klasman grubu): en üst kademe, sonra en iyi sıra
        en = {}
        for x in out[k]:
            if x[0] not in en or (x[1], x[2] / x[3]) < (en[x[0]][1], en[x[0]][2] / en[x[0]][3]):
                en[x[0]] = x
        out[k] = sorted(en.values(), key=lambda x: (baslangic(x[0]), x[0]))
    return out


def resmi_siralar(c):
    out = collections.defaultdict(dict)
    for sezon, kd, gr, sira, kulup in c.execute(
            "SELECT sezon, kademe, COALESCE(grup,''), sira, kulup FROM puan_durumu WHERE yarisma='lig' AND kulup IS NOT NULL"):
        out[(sezon, kd, gr)][kulup] = sira
    return out


def hesapla(maclar, c):
    return ({"alanlar": ["sezon", "mac", "gol", "ev", "beraberlik", "deplasman", "s10", "s11", "s00"],
             "sezon": sezon_istat(maclar), "skor": skor_dagilimi(maclar), "skor_ust": SKOR_UST,
             "derbi_kulup": DERBI, "derbi": derbiler(maclar)},
            {"alanlar": ["sezon", "kademe", "sira", "takim"], "kulup": yolculuk(maclar, resmi_siralar(c))})

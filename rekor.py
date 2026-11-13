"""Tüm zamanlar rekorları: lig kademeleri, bütün profesyonel ligler, Türkiye Kupası ve lig + kupa birlikte (yalnız maç rekorları).

web_aktar.py çağırır -> docs/data/rekorlar.json

Kurallar
  - Geçersiz sayılan maçlar ('gecersiz') hiç girmez.
  - Hükmen sonuçlar (Hük., Çifte H) tablolara girer; maç rekorlarına, serilere ve gol sayımlarına girmez
    (seriyi bozmaz, atlanır).
  - Tarihsiz maçlar sıralanamadığı için serilere girmez.
  - Seriler kulübün o kapsamdaki maçlarının tarih sırasıyla hesaplanır, sezonlar arası sürer; kulüp o kapsamda
    bir sezon (ya da daha fazla) yoksa seri kesilir.
  - Lig kapsamlarında play-off maçları rekorlara ve serilere girer, tüm zamanlar tablosuna girmez.
  - Tüm zamanlar tablosu bugünkü kuralla hesaplanır: galibiyet 3 puan.
"""
import collections

ADET = 25
KAPSAMLAR = [
    ("tum", "Tüm maçlar (lig + kupa)", lambda m: m["yarisma"] in ("lig", "kupa", "ozel_kupa")),
    ("1", "Süper Lig", lambda m: m["yarisma"] == "lig" and m["kademe"] == 1),
    ("2", "1. Lig", lambda m: m["yarisma"] == "lig" and m["kademe"] == 2),
    ("3", "TFF 2. Lig", lambda m: m["yarisma"] == "lig" and m["kademe"] == 3),
    ("4", "TFF 3. Lig", lambda m: m["yarisma"] == "lig" and m["kademe"] == 4),
    ("pro", "Bütün profesyonel ligler", lambda m: m["yarisma"] == "lig"),
    ("kupa", "Türkiye Kupası", lambda m: m["yarisma"] == "kupa"),
]
HUKMEN = ("Hük.", "Çifte H")

SERILER = [   # anahtar, saha filtresi, koşul (attığı, yediği)
    ("yenilmez", None, lambda a, y: a >= y),
    ("ic_yenilmez", "E", lambda a, y: a >= y),
    ("dis_yenilmez", "D", lambda a, y: a >= y),
    ("galibiyet", None, lambda a, y: a > y),
    ("galibiyetsiz", None, lambda a, y: a <= y),
    ("golyemeden", None, lambda a, y: y == 0),
    ("golsuz", None, lambda a, y: a == 0),
]


def hesapla(maclar, sezon_sira, okunur):
    """maclar: futbol.db mac satırları (dict, tarih sırasıyla). sezon_sira: sezon -> sıra no."""
    son_sezon = max(sezon_sira, key=sezon_sira.get)
    out = {"kapsamlar": [[k, ad] for k, ad, _ in KAPSAMLAR], "veri": {}}
    for anahtar, ad, f in KAPSAMLAR:
        ms = [m for m in maclar if f(m) and m["asama"] != "gecersiz"]
        out["veri"][anahtar] = kapsam(ms, sezon_sira, son_sezon, okunur, lig=anahtar != "kupa", sadece_mac=anahtar == "tum")
    return out


def mac_satir(m, okunur):
    return [m["tarih"], m["sezon"], m["lig"], m["tur"] or m["grup"] or "", m["ev_kulup"], okunur(m["ev_adi"]),
            m["dep_kulup"], okunur(m["dep_adi"]), m["ev_gol"], m["dep_gol"], m["ev_pen"], m["dep_pen"], m["durum"]]


def kapsam(ms, sezon_sira, son_sezon, okunur, lig, sadece_mac=False):
    oynanan = [m for m in ms if m["ev_gol"] is not None and m["durum"] not in HUKMEN]

    # ---- maç rekorları
    fark = sorted(oynanan, key=lambda m: (-abs(m["ev_gol"] - m["dep_gol"]), -max(m["ev_gol"], m["dep_gol"]), m["tarih"] or "9"))
    gollu = sorted(oynanan, key=lambda m: (-(m["ev_gol"] + m["dep_gol"]), m["tarih"] or "9"))
    dep_fark = sorted((m for m in oynanan if m["dep_gol"] > m["ev_gol"]),
                      key=lambda m: (m["ev_gol"] - m["dep_gol"], -m["dep_gol"], m["tarih"] or "9"))

    ozet = {
        "mac": len(ms), "oynanan": len(oynanan),
        "sezon": [min((m["sezon"] for m in ms), key=sezon_sira.get, default=None), max((m["sezon"] for m in ms), key=sezon_sira.get, default=None)],
        "fark": [mac_satir(m, okunur) for m in fark[:ADET]],
        "dep_fark": [mac_satir(m, okunur) for m in dep_fark[:ADET]],
        "gollu": [mac_satir(m, okunur) for m in gollu[:ADET]],
    }
    if sadece_mac:   # lig + kupa birlikte: yalnız maç rekorları (seri ve tablo yarışma başına anlamlı)
        return ozet

    # ---- kulüp bakışıyla maçlar
    kulup = collections.defaultdict(list)
    for m in ms:
        for s, r, saha in (("ev", "dep", "E"), ("dep", "ev", "D")):
            if m[s + "_kulup"] is None:
                continue
            if m["durum"] == "Çifte H":
                a, y = 0, 3
            elif m["ev_gol"] is None:
                continue
            else:
                a, y = m[s + "_gol"], m[r + "_gol"]
            kulup[m[s + "_kulup"]].append(dict(t=m["tarih"], sz=m["sezon"], saha=saha, a=a, y=y,
                                              hk=m["durum"] in HUKMEN, po=m["asama"] == "play-off"))

    # ---- seriler
    seriler = {}
    for k, saha_f, kosul in SERILER:
        l = []
        for kid, km in kulup.items():
            dizi = [x for x in km if x["t"] and not x["hk"] and (saha_f is None or x["saha"] == saha_f)]
            cur, onceki = None, None
            for x in dizi:
                if onceki and sezon_sira[x["sz"]] - sezon_sira[onceki["sz"]] > 1:   # kapsamda sezon boşluğu
                    if cur:
                        l.append(cur)
                    cur = None
                if kosul(x["a"], x["y"]):
                    if cur:
                        cur["n"] += 1; cur["son"] = x
                    else:
                        cur = {"kulup": kid, "n": 1, "bas": x, "son": x}
                elif cur:
                    l.append(cur); cur = None
                onceki = x
            if cur:
                cur["devam"] = cur["son"] is dizi[-1] and cur["son"]["sz"] == son_sezon
                l.append(cur)
        l.sort(key=lambda s: (-s["n"], s["bas"]["t"]))
        seriler[k] = [[s["kulup"], s["n"], s["bas"]["t"], s["son"]["t"], s["bas"]["sz"], s["son"]["sz"], 1 if s.get("devam") else 0]
                      for s in l[:ADET]]

    # ---- kulüp sayımları ve tüm zamanlar tablosu
    tablo, gy, golsuz = [], [], []
    for kid, km in kulup.items():
        oy = [x for x in km if not x["hk"]]
        if oy:
            n_gy, n_gs = sum(x["y"] == 0 for x in oy), sum(x["a"] == 0 for x in oy)
            gy.append([kid, n_gy, len(oy)])
            golsuz.append([kid, n_gs, len(oy)])
        tm = [x for x in km if not (lig and x["po"])]
        if not tm:
            continue
        g = sum(x["a"] > x["y"] for x in tm); b = sum(x["a"] == x["y"] for x in tm); mg = len(tm) - g - b
        tablo.append([kid, len({x["sz"] for x in tm}), len(tm), g, b, mg, sum(x["a"] for x in tm), sum(x["y"] for x in tm), 3 * g + b])
    tablo.sort(key=lambda r: (-r[8], -(r[6] - r[7]), -r[6]))
    gy.sort(key=lambda r: (-r[1], r[2]))
    golsuz.sort(key=lambda r: (-r[1], r[2]))

    return {**ozet,
        "seriler": seriler,
        "golyemedi": gy[:ADET],
        "golatamadi": golsuz[:ADET],
        "tablo": tablo,
    }

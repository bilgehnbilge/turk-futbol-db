#!/usr/bin/env python3
"""Kırmızı kartın skora etkisi: Süper Lig 1991-92'den bugüne, TFF maç sayfalarındaki gol ve kart dakikalarından.

  python3 kirmizi.py          # kirmizi_kart.json (site: Sayılar sayfası) + kirmizi_kart_puan.csv (hakem hatası değerlendirmesi)

Yöntem
  1. Her maç, kırmızı kartlarla değişen oyuncu sayısı dönemlerine bölünür (11'e 11, 10'a 11, 9'a 11, 10'a 10 ...).
     Uzatmalar: ilk yarı 45+2, ikinci yarı 90+5 varsayılır; maçta daha geç bir olay varsa o yarı oraya kadar uzar.
  2. Gol modeli (Poisson): bir takımın dakika başına gol oranı = taban (ev/deplasman) × maçın bölümü (0-15 ... 90+)
     × kendi oyuncu sayısı katsayısı × rakibin oyuncu sayısı katsayısı. Katsayılar bütün maçlardan birlikte kestirilir.
  3. Gözlenen etki: tek kırmızılı maçlarda, kırmızıdan sonraki gol farkı ile aynı dakikada aynı skor durumunda
     ve aynı sahadaki kırmızısız maçların kalan gol farkı karşılaştırılır (modelden bağımsız denetim).
  4. Beklenen puan: verilen dakika, skor farkı, saha ve oyuncu sayılarıyla maçın geri kalanı modelden hesaplanır
     (iki takımın kalan golleri bağımsız Poisson). Bir kartın "maliyeti" = kart öncesi ve sonrası beklenen puan farkı.
"""
import collections, csv, gzip, json, math, os, sqlite3, sys

import oyuncu as O

KOK = os.path.dirname(os.path.abspath(__file__))
CIKTI_JSON = os.path.join(KOK, "kirmizi_kart.json")
CIKTI_CSV = os.path.join(KOK, "kirmizi_kart_puan.csv")
KIRMIZI = ("Kırmızı Kart", "Çift Sarı Kart")
UZ1, UZ2 = 2, 5                     # varsayılan uzatma (dk)
BOLUM = ["1-15", "16-30", "31-45", "45+", "46-60", "61-75", "76-90", "90+"]
KOVA = ["1-15", "16-30", "31-45+", "46-60", "61-75", "76-90", "90+"]   # kartın görüldüğü dakika dilimleri


def zaman(dk, ek):
    """(dakika, uzatma) -> maç saati: ilk yarı 0..45+uz1, ikinci yarı 45+uz1 .. 90+uz1+uz2 (uzatma ilk yarı için 45'e eklenir)."""
    if dk is None:
        return None
    ek = ek or 0
    if dk <= 45:
        return dk - 0.5 + (ek if dk == 45 else 0)
    return dk - 0.5 + UZ1 + (ek if dk == 90 else 0)


def bolum(t, y1):
    """maç saati -> bölüm indeksi (y1: o maçın ilk yarı sonu)"""
    if t < y1:
        return 0 if t < 15 else 1 if t < 30 else 2 if t < 45 else 3
    t2 = t - y1 + 45
    return 4 if t2 < 60 else 5 if t2 < 75 else 6 if t2 < 90 else 7


def kova(dk, ek):
    if dk <= 15: return 0
    if dk <= 30: return 1
    if dk <= 45: return 2
    if dk <= 60: return 3
    if dk <= 75: return 4
    if dk < 90 or (dk == 90 and not ek): return 5
    return 6


def maclar():
    t = sqlite3.connect(O.TFF_DB)
    out, sorun = [], collections.Counter()
    for mid, sezon, eg, dg, asama in t.execute("""SELECT kaynak_id, sezon, ev_gol, dep_gol, asama FROM mac WHERE kaynak='tff'
                                                  AND kademe=1 AND ev_gol IS NOT NULL AND kaynak_id<>'' AND sezon>='1991-1992'"""):
        if asama != "lig" or not os.path.exists(O.yol(mid)):
            continue
        with gzip.open(O.yol(mid), "rb") as f:
            o = O.sayfa_oku(f.read().decode("cp1254", "replace"))
        goller = [(2 - g[0] if g[6] == "K" else g[0] - 1, g[4], g[5]) for g in o["gol"] if g[6] != "S"]
        say = [sum(1 for g in goller if g[0] == s) for s in (0, 1)]
        if say != [eg, dg]:
            sorun["gol listesi skorla tutmuyor"] += 1; continue
        kart = [(k[0] - 1, k[5], k[6]) for k in o["kart"] if k[3] in KIRMIZI]
        if any(g[1] is None for g in goller) or any(k[1] is None for k in kart):
            sorun["dakikası olmayan gol/kart"] += 1; continue
        y1 = 45 + max([UZ1] + [ek + .5 for _, dk, ek in goller + kart if dk == 45 and ek])
        son = y1 + 45 + max([UZ2] + [ek + .5 for _, dk, ek in goller + kart if dk == 90 and ek])
        z = lambda dk, ek: (dk - .5 + (ek if dk == 45 else 0)) if dk <= 45 else (y1 + dk - 45.5 + (ek if dk == 90 else 0))
        out.append(dict(id=mid, sezon=sezon, eg=eg, dg=dg, y1=y1, son=son,
                        gol=sorted((z(dk, ek), s) for s, dk, ek in goller),
                        kart=sorted((z(dk, ek), s, kova(dk, ek)) for s, dk, ek in kart)))
    return out, sorun


def donemler(m):
    """[(başlangıç, bitiş, ev oyuncu, dep oyuncu, ev golü, dep golü, bölüm)] — bölüm sınırlarında da bölünür"""
    sinirlar = [0, 15, 30, 45, m["y1"], m["y1"] + 15, m["y1"] + 30, m["y1"] + 45, m["son"]]
    olay = sorted({x for x in sinirlar} | {k[0] for k in m["kart"]})
    oy = [11, 11]
    out = []
    for a, b in zip(olay, olay[1:]):
        for k in m["kart"]:
            if k[0] == a:
                oy[k[1]] -= 1
        if b <= a:
            continue
        g = [sum(1 for t, s in m["gol"] if a <= t < b and s == x) for x in (0, 1)]
        out.append((a, b, oy[0], oy[1], g[0], g[1], bolum(a, m["y1"])))
    # son dakikaya denk gelen (t == son) gol: son döneme
    for t, s in m["gol"]:
        if t >= m["son"]:
            d = list(out[-1]); d[4 + s] += 1; out[-1] = tuple(d)
    return out


# ---------------------------------------------------------------- Poisson modeli (saf Python Newton-Raphson)
def kat(n):   # oyuncu sayısı -> eksik oyuncu sınıfı: 0, 1, 2+ (3 ve üstü çok seyrek: 2 ile birlikte)
    return min(2, 11 - n)


def model_kur(ms, dogrusal=False):
    """dogrusal=False: eksik oyuncu 1 ve 2+ ayrı katsayı; True: her eksik oyuncu aynı çarpan (3-4 kart için dışdeğerleme)"""
    hucre = collections.defaultdict(lambda: [0.0, 0])   # (saha, bölüm, kendi eksik, rakip eksik) -> [dakika, gol]
    for m in ms:
        for a, b, oe, od, ge, gd, bo in donemler(m):
            for saha, ken, rak, g in ((0, oe, od, ge), (1, od, oe, gd)):
                h = hucre[(saha, bo, 11 - ken, 11 - rak)]; h[0] += b - a; h[1] += g
    # parametreler: [taban_ev, taban_dep, bölüm1..7 (bölüm0 = 0), kendi1..2, rakip1..2]  (doğrusal: kendi, rakip)
    P = 2 + 7 + (2 if dogrusal else 4)
    def x(k):
        v = [0.0] * P
        v[k[0]] = 1
        if k[1]: v[1 + k[1]] = 1
        if dogrusal:
            v[9] = k[2]; v[10] = k[3]
        else:
            if k[2]: v[8 + min(2, k[2])] = 1
            if k[3]: v[10 + min(2, k[3])] = 1
        return v
    satir = [(x(k), d, g) for k, (d, g) in hucre.items() if d > 0]
    b = [0.0] * P; b[0] = b[1] = math.log(1.4 / 94)
    for _ in range(50):
        G = [0.0] * P; H = [[0.0] * P for _ in range(P)]
        for xv, d, g in satir:
            mu = d * math.exp(sum(xi * bi for xi, bi in zip(xv, b)))
            for i in range(P):
                if xv[i]:
                    G[i] += xv[i] * (g - mu)
                    for j in range(P):
                        if xv[j]: H[i][j] += xv[i] * xv[j] * mu
        for i in range(P): H[i][i] += 1e-9
        adim = coz(H, G)
        b = [bi + ai for bi, ai in zip(b, adim)]
        if max(abs(a) for a in adim) < 1e-10:
            break
    ters = tersi(H)
    se = [math.sqrt(max(ters[i][i], 0)) for i in range(P)]
    dakika = {k: v[0] for k, v in hucre.items()}
    return b, se, hucre


def coz(A, y):
    n = len(y); M = [r[:] + [y[i]] for i, r in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c])); M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c and M[c][c]:
                f = M[r][c] / M[c][c]
                M[r] = [a - f * bb for a, bb in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] if M[i][i] else 0 for i in range(n)]


def tersi(A):
    n = len(A)
    return [list(col) for col in zip(*[coz(A, [1.0 if i == j else 0.0 for i in range(n)]) for j in range(n)])]


class Model:
    def __init__(self, b):
        self.b = b

    def oran(self, saha, bo, ken, rak):   # dakika başına gol
        b = self.b
        if len(b) == 11:   # doğrusal model
            return math.exp(b[saha] + (b[1 + bo] if bo else 0) + b[9] * (11 - ken) + b[10] * (11 - rak))
        return math.exp(b[saha] + (b[1 + bo] if bo else 0) + (b[8 + kat(ken)] if kat(ken) else 0) + (b[10 + kat(rak)] if kat(rak) else 0))

    def kalan_beklenen(self, t, saha, ken, rak, y1=45 + UZ1, son=90 + UZ1 + UZ2):
        """t anından maç sonuna kadar beklenen gol (bölüm bölüm)"""
        sin = [0, 15, 30, 45, y1, y1 + 15, y1 + 30, y1 + 45, son]
        top = 0.0
        for i in range(8):
            a, c = max(t, sin[i]), sin[i + 1]
            if c > a:
                top += (c - a) * self.oran(saha, i, ken, rak)
        return top

    def puan(self, t, fark, saha, ken, rak):
        """saha (0 ev, 1 dep) tarafındaki takımın t anından sonra beklenen puanı; fark = o takımın o anki gol farkı"""
        la = self.kalan_beklenen(t, saha, ken, rak)
        lb = self.kalan_beklenen(t, 1 - saha, rak, ken)
        pa = [math.exp(-la) * la ** k / math.factorial(k) for k in range(15)]
        pb = [math.exp(-lb) * lb ** k / math.factorial(k) for k in range(15)]
        p = 0.0
        for i, x in enumerate(pa):
            for j, y in enumerate(pb):
                f = fark + i - j
                p += x * y * (3 if f > 0 else 1 if f == 0 else 0)
        return p


def dk_saat(dk, ek=0):
    return zaman(dk, ek)


def gozlenen(ms):
    """tek kırmızılı maçlarda kova kova: kırmızıdan sonraki gol farkı - aynı dakika, aynı skor durumu, aynı sahadaki
    kırmızısız maçların kalan gol farkı ortalaması"""
    kirmizisiz = [m for m in ms if not m["kart"]]
    tek = [m for m in ms if len(m["kart"]) == 1]
    kes = lambda v: max(-2, min(2, v))
    onbellek = {}
    def taban(t, saha, fark):
        k = (round(t), saha, fark)
        if k not in onbellek:
            l = []
            for m in kirmizisiz:
                tt = t if t < 47 else t - 47 + m["y1"]
                once = [sum(1 for x, s in m["gol"] if x < tt and s == y) for y in (0, 1)]
                f = once[saha] - once[1 - saha]
                if kes(f) != fark: continue
                sonra = [sum(1 for x, s in m["gol"] if x >= tt and s == y) for y in (0, 1)]
                l.append((sonra[saha] - sonra[1 - saha], sonra[saha], sonra[1 - saha]))
            onbellek[k] = l
        return onbellek[k]
    out = []
    for i, ad in enumerate(KOVA):
        et, at, atb, ye, yeb, n_atla = [], 0, 0, 0, 0, 0
        for m in tek:
            t, s, kv = m["kart"][0]
            if kv != i: continue
            once = [sum(1 for x, ss in m["gol"] if x < t and ss == y) for y in (0, 1)]
            f = kes(once[s] - once[1 - s])
            tt = t if t < m["y1"] else 47 + (t - m["y1"])
            l = taban(tt, s, f)
            if len(l) < 30: n_atla += 1; continue
            sonra = [sum(1 for x, ss in m["gol"] if x >= t and ss == y) for y in (0, 1)]
            beklenen = sum(x[0] for x in l) / len(l)
            et.append((sonra[s] - sonra[1 - s]) - beklenen)
            at += sonra[s]; ye += sonra[1 - s]; atb += sum(x[1] for x in l) / len(l); yeb += sum(x[2] for x in l) / len(l)
        n = len(et)
        o = sum(et) / n; sd = (sum((e - o) ** 2 for e in et) / (n - 1)) ** .5 if n > 1 else 0
        out.append(dict(kova=ad, n=n, etki=round(o, 3), ga=round(1.96 * sd / math.sqrt(n), 3) if n else None,
                        atilan=round(at / n, 3), atilan_bek=round(atb / n, 3), yenen=round(ye / n, 3), yenen_bek=round(yeb / n, 3)))
    return out


def durum_tablosu(ms):
    """oyuncu sayısı durumlarında gözlenen dakika ve gol (takım bakışıyla: kendi - rakip)"""
    t = collections.defaultdict(lambda: [0.0, 0, 0, 0])
    for m in ms:
        for a, b, oe, od, ge, gd, bo in donemler(m):
            for ken, rak, at, ye in ((oe, od, ge, gd), (od, oe, gd, ge)):
                x = t[(ken, rak)]; x[0] += b - a; x[1] += at; x[2] += ye
    return t


def main():
    ms, sorun = maclar()
    b, se, hucre = model_kur(ms)
    bd, sed, _ = model_kur(ms, dogrusal=True)
    M = Model(b)
    MD = Model(bd)
    kat_ad = lambda i: math.exp(b[i])
    # model: eksik oyuncu katsayıları (gol oranı çarpanı) ve %95 aralık
    carpan = {
        "kendi": [dict(eksik=k, carpan=round(math.exp(b[8 + k]), 3), alt=round(math.exp(b[8 + k] - 1.96 * se[8 + k]), 3),
                       ust=round(math.exp(b[8 + k] + 1.96 * se[8 + k]), 3)) for k in (1, 2)],
        "rakip": [dict(eksik=k, carpan=round(math.exp(b[10 + k]), 3), alt=round(math.exp(b[10 + k] - 1.96 * se[10 + k]), 3),
                       ust=round(math.exp(b[10 + k] + 1.96 * se[10 + k]), 3)) for k in (1, 2)],
        "oyuncu_basina": dict(kendi=round(math.exp(bd[9]), 3), kendi_ga=[round(math.exp(bd[9] - 1.96 * sed[9]), 3), round(math.exp(bd[9] + 1.96 * sed[9]), 3)],
                              rakip=round(math.exp(bd[10]), 3), rakip_ga=[round(math.exp(bd[10] - 1.96 * sed[10]), 3), round(math.exp(bd[10] + 1.96 * sed[10]), 3)]),
        "bolum": [dict(bolum=BOLUM[i], carpan=round(math.exp(b[1 + i]) if i else 1.0, 3)) for i in range(8)],
        "taban90": [round(math.exp(b[0]) * 90, 3), round(math.exp(b[1]) * 90, 3)],
    }
    dt = durum_tablosu(ms)
    durumlar = []
    for (ken, rak), (dk, at, ye, _) in sorted(dt.items(), key=lambda kv: (-kv[0][0] + kv[0][1], -kv[0][0])):
        if dk < 1: continue
        durumlar.append(dict(durum=f"{ken}'e {rak}", kendi=ken, rakip=rak, dakika=round(dk), atilan90=round(at / dk * 90, 3),
                             yenen90=round(ye / dk * 90, 3), atilan=at, yenen=ye))
    # beklenen puan maliyeti: dakika (1..90, 90+3) × skor farkı (-2..2) × saha; 11'e 11'den 10'a 11'e ve 10'a 11'den 9'a 11'e
    DK = [(d, 0) for d in range(1, 91)] + [(90, 3)]
    gecis = [("11v11-10v11", (11, 11), (10, 11)), ("10v11-9v11", (10, 11), (9, 11)), ("11v10-10v10", (11, 10), (10, 10)),
             ("9v11-8v11", (9, 11), (8, 11))]
    tablo = []
    with open(CIKTI_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["gecis", "dakika", "uzatma", "saha", "gol_farki", "puan_once", "puan_sonra", "puan_kaybi", "gol_farki_kaybi"])
        for ad, once, sonra in gecis:
            for dk, ek in DK:
                t = zaman(dk, ek) + .5
                for saha in (0, 1):
                    for fark in (-2, -1, 0, 1, 2):
                        MM = MD if min(sonra) < 9 else M   # 8 oyuncu: her eksik oyuncu aynı çarpan varsayımı
                        p0 = MM.puan(t, fark, saha, *once); p1 = MM.puan(t, fark, saha, *sonra)
                        g0 = MM.kalan_beklenen(t, saha, *once) - MM.kalan_beklenen(t, 1 - saha, once[1], once[0])
                        g1 = MM.kalan_beklenen(t, saha, *sonra) - MM.kalan_beklenen(t, 1 - saha, sonra[1], sonra[0])
                        w.writerow([ad, dk, ek, "ev" if saha == 0 else "deplasman", fark, round(p0, 4), round(p1, 4), round(p0 - p1, 4), round(g0 - g1, 4)])
                        tablo.append([[g[0] for g in gecis].index(ad), dk, ek, saha, fark, round(p0, 3), round(p1, 3), round(g0 - g1, 3)])
    gz = gozlenen(ms)
    # modelin aynı kovalardaki tahmini (gözlenenle karşılaştırma): kova ortasında, ev+dep ortalaması
    orta = [(8, 0), (23, 0), (38, 0), (53, 0), (68, 0), (83, 0), (90, 3)]
    for g, (dk, ek) in zip(gz, orta):
        t = zaman(dk, ek) + .5
        g["model"] = round(sum(M.kalan_beklenen(t, s, 10, 11) - M.kalan_beklenen(t, 1 - s, 11, 10)
                               - (M.kalan_beklenen(t, s, 11, 11) - M.kalan_beklenen(t, 1 - s, 11, 11)) for s in (0, 1)) / 2, 3)
    kart_say = collections.Counter((sum(1 for k in m["kart"] if k[1] == 0), sum(1 for k in m["kart"] if k[1] == 1)) for m in ms)
    sonuc = dict(kapsam=dict(mac=len(ms), sezon_ilk=min(m["sezon"] for m in ms), sezon_son=max(m["sezon"] for m in ms),
                             kirmizili=sum(1 for m in ms if m["kart"]), kirmizi=sum(len(m["kart"]) for m in ms),
                             tek=sum(1 for m in ms if len(m["kart"]) == 1), cikarilan=dict(sorun),
                             kart_dagilimi=[[a, b_, n] for (a, b_), n in sorted(kart_say.items())]),
                 gozlenen=gz, model=carpan, durumlar=durumlar,
                 gecisler=[[g[0], list(g[1]), list(g[2])] for g in gecis],
                 puan_alanlar=["gecis", "dakika", "uzatma", "saha", "fark", "puan_once", "puan_sonra", "gol_farki_kaybi"], puan=tablo)
    json.dump(sonuc, open(CIKTI_JSON, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(json.dumps({k: v for k, v in sonuc.items() if k not in ("puan",)}, ensure_ascii=False, indent=1)[:6000])
    print("->", CIKTI_JSON, CIKTI_CSV)


if __name__ == "__main__":
    main()

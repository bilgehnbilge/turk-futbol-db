#!/usr/bin/env python3
"""UEFA oyuncuları (Avrupa maçları) ile TFF oyuncularını (lig ve kupa) aynı kişi olarak eşler -> docs/data/oyuncu_bag.json

web_aktar.py çağırır (tff_detay ve UEFA ayrıntıları yazıldıktan sonra). Tek başına: python3 oyuncu_bag.py

Eşleme kuralı (hepsi birlikte):
  1. Aynı sezonda aynı kulüpte oynamış olmak: UEFA oyuncusunun Avrupa maçı yaptığı (sezon, kulüp) TFF oyuncusunun
     kariyerinde de olmalı.
  2. Ad benzerliği: soyadı (UEFA adının son kelimesi) TFF adında geçmeli ve ad benzerlik puanı eşiği geçmeli;
     ad-soyad sırası ters yazılmış yabancı oyuncular da tutar ("Rotariu Josif" / "Iosif Rotariu" için soyadı yeter).
  3. Doğum: iki tarafta da varsa yıl aynı olmalı. 1 Ocak / 1 Temmuz yalnız yıl bilindiğini gösterir; ikisi de tam
     tarihse gün de tutmalı. TFF doğum bilgisi raw/kisi.db'den (oyuncu.py kisi_ayikla).
Adaylar arasında en iyi puanlı tek aday seçilir; eşit puanlı iki aday varsa eşlenmez.
"""
import collections, glob, json, os, sqlite3, unicodedata

KOK = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(KOK, "docs", "data")
KISI_DB = os.path.join(KOK, "raw", "kisi.db")
CIKTI = os.path.join(D, "oyuncu_bag.json")


def sade(s):
    s = (s or "").replace("İ", "i").replace("I", "ı").lower().replace("ı", "i")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return [w for w in "".join(c if c.isalnum() else " " for c in s).split() if w]


def yalniz_yil(t):
    return t is None or t[5:] in ("01-01", "07-01")


def dogum_tutar(a, b):
    if not a or not b:
        return None   # bilinmiyor
    if a[:4] != b[:4]:
        return False
    return True if yalniz_yil(a) or yalniz_yil(b) or a == b else False


def ad_puani(u, t):
    """0..1: UEFA adının kelimeleri TFF adında ne kadar var (soyadı şart)."""
    uw, tw = sade(u), sade(t)
    if not uw or not tw:
        return 0
    def var(w):
        return any(x == w or (len(w) >= 4 and (x.startswith(w) or w.startswith(x))) for x in tw)
    soyad = var(uw[-1]) or var(uw[0])   # ad-soyad ters yazılmış olabilir
    if not soyad:
        return 0
    return sum(var(w) for w in uw) / len(uw) * (0.9 if len(uw) == 1 else 1)


def bagla(yaz=None):
    u = json.load(open(os.path.join(D, "oyuncu_uefa.json"), encoding="utf-8"))
    av = {r[0]: r for r in json.load(open(os.path.join(D, "avrupa.json"), encoding="utf-8"))["maclar"]}
    # UEFA oyuncusu -> {(sezon, kulüp)}
    uks = collections.defaultdict(set)
    for k in u["katilim"]:
        m = av.get(k[1])
        if m:
            uks[str(k[0])].add((m[2], k[2]))
    # TFF: (sezon, kulüp) -> oyuncular
    tks, tad = collections.defaultdict(set), {}
    for f in glob.glob(os.path.join(D, "tff", "o", "*.json")):
        for kisi, v in json.load(open(f, encoding="utf-8"))["oyuncu"].items():
            tad[kisi] = v["ad"]
            for r in v["s"]:
                if r[4]:
                    tks[(r[0], r[1])].add(kisi)
    dog = {}
    if os.path.exists(KISI_DB):
        dog = {str(k): d for k, d in sqlite3.connect(KISI_DB).execute("SELECT kisi, dogum FROM kisi")}
    import tff_detay
    dog.update({str(k): d for k, d in tff_detay.DOGUM_DUZELT.items()})
    bag, say = {}, collections.Counter()
    for p, ks in uks.items():
        ad, udog = u["oyuncu"][p][0], u["oyuncu"][p][1]
        aday = collections.Counter()
        for x in ks:
            for kisi in tks.get(x, ()):
                aday[kisi] += 1
        if not aday:
            say["TFF'de ortak sezon-kulüp yok"] += 1; continue
        puan = []
        for kisi, ortak in aday.items():
            a = ad_puani(ad, tad[kisi])
            dt = dogum_tutar(udog, dog.get(kisi))
            if a < 0.5 or dt is False:
                continue
            puan.append((a + 0.3 * (dt is True) + 0.05 * min(ortak, 4), kisi, dt))
        puan.sort(reverse=True)
        if not puan:
            say["ad tutmadı"] += 1; continue
        if len(puan) > 1 and puan[0][0] - puan[1][0] < 0.05:
            say["iki aday eşit"] += 1; continue
        bag[p] = int(puan[0][1])
        say["eşlendi (doğum da tuttu)" if puan[0][2] else "eşlendi (doğum bilinmiyor)"] += 1
    yaz = yaz or (lambda y, v: json.dump(v, open(y, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":")))
    yaz(CIKTI, bag)
    avrupa_yas(bag, yaz)
    print("UEFA-TFF oyuncu eşlemesi:", dict(say), "->", CIKTI)
    return bag


def avrupa_yas(bag, yaz):
    """Kulüplerin yaş rekorlarına (tff/kulup/<id>.json: genc, yasli, genc_gol, yasli_gol) Avrupa maçlarını kat: UEFA doğum
    tarihleri; TFF oyuncusuyla eşlenen oyuncu TFF numarasıyla (aynı kişinin lig kaydıyla birleşir), eşlenmeyen 'u<UEFA no>'."""
    import datetime
    u = json.load(open(os.path.join(D, "oyuncu_uefa.json"), encoding="utf-8"))
    av = {r[0]: r for r in json.load(open(os.path.join(D, "avrupa.json"), encoding="utf-8"))["maclar"]}
    ek = collections.defaultdict(lambda: collections.defaultdict(lambda: [None, None, None, None]))   # kulüp -> kişi -> oyun [genç, yaşlı], gol [genç, yaşlı]
    adlar = {}
    for k in u["katilim"]:
        p, mid, kid, gol = str(k[0]), k[1], k[2], k[4]
        o, m = u["oyuncu"].get(p), av.get(mid)
        if not o or not m or not o[1] or o[1][5:] in ("01-01", "07-01"):
            continue
        g = (datetime.date.fromisoformat(m[1]) - datetime.date.fromisoformat(o[1])).days
        if g < 15 * 365 or g > 50 * 365:   # UEFA doğum tarihlerinde hata var (ör. 1985 Ömer Kılıç: 1971); TFF için alt sınır 12
            continue
        kisi = bag.get(p) or f"u{p}"
        adlar[kisi] = o[0]
        rakip = m[6] if m[5] == kid else m[5]
        x = [g, m[1], mid, rakip]
        r = ek[kid][kisi]
        for i, ok in ((0, True), (2, bool(gol))):
            if not ok:
                continue
            if r[i] is None or g < r[i][0]: r[i] = x
            if r[i + 1] is None or g > r[i + 1][0]: r[i + 1] = x
    n = 0
    for kid, d in ek.items():
        y = os.path.join(D, "tff", "kulup", f"{kid}.json")
        if not os.path.exists(y):
            continue
        v = json.load(open(y, encoding="utf-8"))
        for anahtar, i, ters in (("genc", 0, False), ("yasli", 1, True), ("genc_gol", 2, False), ("yasli_gol", 3, True)):
            l = {x[0]: x for x in v.get(anahtar, [])}
            for kisi, r in d.items():
                x = r[i]
                if x is None:
                    continue
                eski = l.get(kisi) or l.get(int(kisi) if str(kisi).isdigit() else kisi)
                if not eski or (x[0] > eski[2] if ters else x[0] < eski[2]):
                    ad = eski[1] if eski else adlar[kisi]
                    l[kisi if not eski else eski[0]] = [kisi if not eski else eski[0], ad, x[0], x[1], x[2], x[3]]
            v[anahtar] = sorted(l.values(), key=lambda x: -x[2] if ters else x[2])[:10]
        yaz(y, v); n += 1
    print(f"Avrupa yaş rekorları: {n} kulübe katıldı")


if __name__ == "__main__":
    bagla()

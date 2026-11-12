"""futbol.db -> docs/data/*.json (GitHub Pages arayuzu icin).

  python3 web_aktar.py

Uretilen dosyalar:
  docs/data/ozet.json          genel sayilar, sezon listesi, lig adlari
  docs/data/kulupler.json      kulup listesi (arama icin): id, ad, donem adlari, ilk/son sezon, mac sayisi, ardillik
  docs/data/kulup/<id>.json    kulubun tum maclari (takim bakis acisiyla)
  docs/data/sezon/<sezon>.json sezonun tum maclari (puan tablosu ve fikstur icin)
  docs/data/rekorlar.json      tum zamanlar rekorlari, seriler ve tablolar (rekor.py)

Satir bicimleri dosyalarin "alanlar" anahtarinda yazar.
"""
import collections, datetime, json, os, shutil, sqlite3

import rekor

KOK = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(KOK, "futbol.db")
CIKTI = os.path.join(KOK, "docs", "data")
YAR = {"lig": "L", "kupa": "K", "avrupa": "A", "terfi": "T"}


KISALTMA = {"MKE", "PTT", "DSİ", "YSE", "GSK", "TEK", "THY", "PTT", "TCDD", "SAİ", "TKİ", "DHMİ", "TSK", "İDSİ", "BŞB", "ASKİ", "İSKİ"}


TR_BUYUK = set("ÇĞİÖŞÜ")
KATLA = str.maketrans("ÇĞİÖŞÜ", "CGIOSU")
SOZLUK = collections.defaultdict(collections.Counter)   # ASCII hali -> Turkce harfli yazimlar


def sozluk_kur(adlar):
    """Turkce harfle yazilmis buyuk harfli adlardaki kelimeler: 'PENDİKSPOR' -> PENDIKSPOR anahtari."""
    for ad in adlar:
        if ad and not any(ch.islower() for ch in ad) and TR_BUYUK & set(ad):
            for w in ad.split():
                SOZLUK[w.translate(KATLA)][w] += 1


def turkcele(ad):
    """TFF'nin bazi eski kayitlari Turkce harfsiz ('PENDIKSPOR'): kelimeyi sozlukteki Turkce yazimiyla degistir."""
    if not ad or any(ch.islower() for ch in ad) or TR_BUYUK & set(ad):
        return ad
    return " ".join(SOZLUK[w].most_common(1)[0][0] if w in SOZLUK else w for w in ad.split(" "))


def okunur(ad):
    """TFF'nin tamamen buyuk harfli adlari: 'GÖZTEPE A.Ş.' -> 'Göztepe A.Ş.' (kisaltmalar korunur)."""
    if not ad or any(ch.islower() for ch in ad):
        return ad
    ad = turkcele(ad)
    def kelime(w):
        harf = "".join(ch for ch in w if ch.isalpha())
        if len(harf) <= 2 or harf in KISALTMA or w.replace(".", "") in KISALTMA:
            return w
        out, bas = [], True
        for ch in w:
            if ch.isalpha():
                out.append(ch if bas else ch.replace("I", "ı").replace("İ", "i").lower())
                bas = False
            else:
                out.append(ch)
                bas = ch in ".-/("
        return "".join(out)
    return " ".join(kelime(w) for w in ad.split(" "))


def gorunen(ad, adlar):
    """Kulup adi: TFF'nin buyuk harfli adi okunur hale getirilir."""
    return okunur(ad)


def yaz(yol, veri):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, separators=(",", ":"))


def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    if os.path.isdir(CIKTI):
        shutil.rmtree(CIKTI)
    maclar = [dict(r) for r in c.execute("SELECT * FROM mac ORDER BY tarih IS NULL, tarih, saat, id")]
    sozluk_kur([m["ev_adi"] for m in maclar] + [m["dep_adi"] for m in maclar])

    def tur(m):
        if m["yarisma"] == "lig" or m["yarisma"] == "terfi":
            return m["grup"] or ""
        return m["tur"] or m["grup"] or ""   # kupa: tur adi Mackolik'te grup alaninda

    def asama(m):
        return "p" if m["asama"] == "play-off" else "x" if m["asama"] == "gecersiz" else ""

    def gol(m, s, r):   # 'Çifte H': iki takım da 0-3 yenik
        if m["durum"] == "Çifte H":
            return 0, 3
        return m[s + "_gol"], m[r + "_gol"]

    # ---- kulupler
    adlar = collections.defaultdict(list)
    for r in c.execute("SELECT kulup_id, ad, ilk_sezon, son_sezon, mac_sayisi FROM kulup_adi ORDER BY kulup_id, ilk_sezon"):
        ad = okunur(r[1])
        onceki = next((a for a in adlar[r[0]] if a[0] == ad), None)   # buyuk/kucuk harf farkli ayni ad birlesir
        if onceki:
            onceki[1], onceki[2], onceki[3] = min(onceki[1], r[2]), max(onceki[2], r[3]), onceki[3] + r[4]
        else:
            adlar[r[0]].append([ad, r[2], r[3], r[4]])
    ardil = collections.defaultdict(list)
    for r in c.execute("SELECT onceki_kulup, sonraki_kulup, sezon, tur, aciklama FROM kulup_ardil"):
        ardil[r[0]].append({"yon": "sonraki", "kulup": r[1], "sezon": r[2], "tur": r[3], "aciklama": r[4]})
        ardil[r[1]].append({"yon": "onceki", "kulup": r[0], "sezon": r[2], "tur": r[3], "aciklama": r[4]})
    # logo: logo_eslesme.json {"tff:3661": <FM kimligi>, ...} -> docs/logo/<FM kimligi>.png
    logo_es = json.load(open(os.path.join(KOK, "logo_eslesme.json"), encoding="utf-8")) if os.path.exists(os.path.join(KOK, "logo_eslesme.json")) else {}
    wiki_yol = os.path.join(KOK, "logo_wiki.json")   # FM paketinde olmayanlar: Vikipedi arması (wiki_logo.py)
    logo_es = {**(json.load(open(wiki_yol, encoding="utf-8")) if os.path.exists(wiki_yol) else {}), **logo_es}
    logo = {}
    for r in c.execute("SELECT kulup_id, kaynak || ':' || kaynak_id FROM kulup_kimlik ORDER BY kaynak <> 'tff', son_sezon DESC"):
        fm = logo_es.get(r[1])
        if fm and r[0] not in logo and os.path.exists(os.path.join(KOK, "docs", "logo", f"{fm}.png")):
            logo[r[0]] = fm
    renk = {}
    for f in ("logo_renk.json", "logo_renk_elle.json"):   # elle olan üstüne yazar
        if os.path.exists(os.path.join(KOK, f)):
            renk.update({k: v for k, v in json.load(open(os.path.join(KOK, f), encoding="utf-8")).items() if not k.startswith("_")})
    tff = collections.defaultdict(list)
    for r in c.execute("SELECT kulup_id, kaynak_id FROM kulup_kimlik WHERE kaynak='tff' AND kaynak_id NOT LIKE '%-once'"):
        tff[r[0]].append(r[1])

    kulup_mac = collections.defaultdict(list)
    yerli = set()
    for m in maclar:
        for s, r in (("ev", "dep"), ("dep", "ev")):
            k = m[s + "_kulup"]
            if k is None:
                continue
            if m["yarisma"] != "avrupa":
                yerli.add(k)
            kulup_mac[k].append([m["id"], m["tarih"], m["sezon"], YAR[m["yarisma"]], m["lig"], m["kademe"], tur(m), asama(m),
                                 "E" if s == "ev" else "D", okunur(m[s + "_adi"]), m[r + "_kulup"], okunur(m[r + "_adi"]),
                                 *gol(m, s, r), m[s + "_pen"], m[r + "_pen"], m["durum"], m["notlar"]])
    liste = []
    for r in c.execute("SELECT id, ad FROM kulup ORDER BY id"):
        k, ad = r
        ms = kulup_mac.get(k, [])
        if not ms:
            continue
        sezonlar = sorted({x[2] for x in ms})
        en_ust = min((x[5] for x in ms if x[3] == "L" and x[5]), default=None)
        liste.append({"id": k, "ad": gorunen(ad, adlar.get(k, [])), "adlar": adlar.get(k, []), "ilk": sezonlar[0], "son": sezonlar[-1], "mac": len(ms),
                      "yerli": k in yerli, "enust": en_ust, "tff": tff.get(k, []), "ardil": ardil.get(k, []),
                      **({"logo": logo[k]} if k in logo else {}),
                      **({"renk": [x for x in renk[str(logo[k])] if x]} if k in logo and str(logo[k]) in renk else {})})
        yaz(os.path.join(CIKTI, "kulup", f"{k}.json"), {
            "alanlar": ["id", "tarih", "sezon", "yarisma", "lig", "kademe", "grup_tur", "playoff", "saha", "takim", "rakip_id",
                        "rakip", "attigi", "yedigi", "pen_a", "pen_y", "durum", "not"],
            "maclar": ms})
    yaz(os.path.join(CIKTI, "kulupler.json"), liste)

    # ---- sezonlar
    sez = collections.defaultdict(list)
    for m in maclar:
        sez[m["sezon"]].append([m["id"], m["tarih"], YAR[m["yarisma"]], m["lig"], m["kademe"], tur(m), asama(m),
                                m["ev_kulup"], okunur(m["ev_adi"]), m["dep_kulup"], okunur(m["dep_adi"]), m["ev_gol"], m["dep_gol"],
                                m["ev_pen"], m["dep_pen"], m["durum"], m["notlar"]])
    for s, ms in sez.items():
        yaz(os.path.join(CIKTI, "sezon", f"{s}.json"), {
            "alanlar": ["id", "tarih", "yarisma", "lig", "kademe", "grup_tur", "playoff", "ev_id", "ev", "dep_id", "dep",
                        "ev_gol", "dep_gol", "ev_pen", "dep_pen", "durum", "not"],
            "maclar": ms})

    # ---- tüm zamanlar rekorları
    sezon_sira = {s: i for i, s in enumerate(sorted(sez, key=lambda s: (s[:4], s)))}
    yaz(os.path.join(CIKTI, "rekorlar.json"), rekor.hesapla(maclar, sezon_sira, okunur))

    say = {r[0]: r[1] for r in c.execute("SELECT yarisma, COUNT(*) FROM mac GROUP BY 1")}
    kapsam = [list(r) for r in c.execute("SELECT kademe, sezon, grup, takim, bulunan, beklenen FROM kapsam")]
    yaz(os.path.join(CIKTI, "ozet.json"), {
        "mac": len(maclar), "kulup": len(liste), "yarisma": say,
        "surum": datetime.datetime.now().strftime("%Y%m%d%H%M"),   # veri dosyalari icin onbellek anahtari
        "sezonlar": sorted(sez, key=lambda s: (s[:4], s)),
        "ilk_tarih": next((m["tarih"] for m in maclar if m["tarih"]), None),
        "son_tarih": max(m["tarih"] for m in maclar if m["tarih"] and m["ev_gol"] is not None),
        "kapsam": kapsam})
    toplam = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(CIKTI) for f in fs)
    print(f"{len(liste)} kulup, {len(sez)} sezon, {len(maclar)} mac -> {CIKTI} ({toplam / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()

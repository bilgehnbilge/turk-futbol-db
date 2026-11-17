"""Kadın ligleri -> docs/data/kadin/ (sitenin ayrı "Kadın" bölümü; erkek verisine hiç karışmaz).

  python3 kadin.py site      (ya da: python3 kadin_site.py)

Girdi: raw/kadin.db (kadin.py kur: maçlar, skorlar) ve raw/kadin_detay.db (kadin.py ayikla: kadro, gol, kart...).
Çıktı:
  kadin/ozet.json        sezonlar, ligler, kulüpler, sezon gol kralları
  kadin/maclar.json      bütün maçlar (puan tabloları, kulüp sayfaları tarayıcıda hesaplanır)
  kadin/oyuncular.json   oyuncu dizini (arama, tüm zamanlar listeleri)
  kadin/m/<TFF maç no % 250>.json   maç ayrıntısı (kadro, olaylar, hakemler)
  kadin/o/<kişi no % 250>.json      oyuncu kariyeri (sezon x kulüp)
  kadin/k/<kulüp>.json              kulübün oyuncuları

Kulüp adları: erkek takımıyla aynı TFF kulübü olanlar (Galatasaray, Fenerbahçe, Beşiktaş...) erkek bölümündeki adıyla
ve "(Kadın)" ekiyle yazılır; adında zaten Kadın/Bayan geçmeyen ve bir erkek kulübüyle aynı adı taşıyanlar da "(Kadın)" alır.
"""
import collections, datetime, json, os, sqlite3

import web_aktar
import tff_detay

KOK = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(KOK, "raw", "kadin.db")
DETAY_DB = os.path.join(KOK, "raw", "kadin_detay.db")
CIKTI = os.path.join(KOK, "docs", "data", "kadin")
KOVA = 250
KART = {"Sarı Kart": "Y", "Kırmızı Kart": "R", "Çift Sarı Kart": "YR"}
ASAMA = {"lük Maçları": "3.lük maçları", "Off Maçları": "Play-off maçları", "Out Maçları": "Play-out maçları",
         "Grubu Maçları": "Final grubu maçları", "Turu Maçları": "Final turu maçları", "Kademe Maçları": "Kademe maçları"}
yaz = web_aktar.yaz


def kadin_mi(ad):
    a = ad.upper().replace("İ", "I")
    return "KADIN" in a or "BAYAN" in a


def aktar():
    c = sqlite3.connect(DB)
    o = sqlite3.connect(DETAY_DB) if os.path.exists(DETAY_DB) else None
    erkek = json.load(open(os.path.join(KOK, "docs", "data", "kulupler.json"), encoding="utf-8"))
    erkek_tff = {t: k for k in erkek for t in k.get("tff", [])}
    erkek_ad = {web_aktar.okunur(a[0]).casefold() for k in erkek for a in k.get("adlar", [])} | {k["ad"].casefold() for k in erkek}
    web_aktar.sozluk_kur([r[0] for r in c.execute("SELECT ad FROM kulup_adi")])

    # ---- kulüpler
    kulup = {}
    for kid, tff, ad in c.execute("SELECT id, tff_id, ad FROM kulup"):
        adlar = [[web_aktar.okunur(a), i, s, n] for a, i, s, n in c.execute(
            "SELECT ad, ilk_sezon, son_sezon, mac_sayisi FROM kulup_adi WHERE kulup_id=? ORDER BY son_sezon, ilk_sezon", (kid,))]
        son = adlar[-1][0] if adlar else web_aktar.okunur(ad)
        e = erkek_tff.get(tff)
        if e:
            gorunen = e["ad"] + " (Kadın)"
        elif not kadin_mi(son) and son.casefold() in erkek_ad:
            gorunen = son + " (Kadın)"
        else:
            gorunen = son
        # logo: erkek takımıyla aynı kulüpse onun logosu (FM paketi), yoksa TFF maç sayfasındaki logo (kadin_logo.py)
        logo = e["logo"] if e and e.get("logo") else f"tk{tff}" if os.path.exists(os.path.join(KOK, "docs", "logo", f"tk{tff}.png")) else None
        kulup[kid] = {"id": kid, "ad": gorunen, "adlar": adlar, "tff": tff, **({"logo": logo} if logo else {}),
                      **({"erkek": e["id"]} if e else {}), **({"renk": e["renk"]} if e and e.get("renk") else {})}

    # ---- maçlar
    detay = set()
    if o:
        detay = {int(m) for (m,) in o.execute("SELECT mac FROM mac_bilgi")}
    maclar, kul_mac = [], collections.Counter()
    sezon_kul = collections.defaultdict(set)
    for (mid, tff, sezon, kademe, lig, grup, asama, hafta, tarih, saat, ev, dep, eg, dg, ep, dp, ham) in c.execute(
            "SELECT id, kaynak_id, sezon, kademe, lig, grup, asama, hafta, tarih, saat, ev_id, dep_id, ev_gol, dep_gol, ev_pen, dep_pen, ham_skor "
            "FROM mac ORDER BY tarih IS NULL, tarih, saat, id"):
        tff = int(tff)
        asama = "" if asama == "lig" else ASAMA.get(asama, asama)
        maclar.append([tff, tarih, sezon, kademe, lig, grup or "", asama, hafta, ev, dep, eg, dg, ep, dp,
                       1 if tff in detay else 0, ham if eg is None and ham not in (None, "", "-") else None])
        for k in (ev, dep):
            kul_mac[k] += 1
            sezon_kul[k].add(sezon)
    for k, v in kulup.items():
        v["mac"] = kul_mac[k]
        ss = sorted(sezon_kul[k])
        v["ilk"], v["son"] = (ss[0], ss[-1]) if ss else (None, None)
    tff_kulup = {}   # TFF maç no -> (ev kulüp, dep kulüp, sezon, kademe, lig mi)
    for r in maclar:
        tff_kulup[r[0]] = (r[8], r[9], r[2], r[3], r[6] == "")
    sezonlar = sorted({r[2] for r in maclar})
    ligler = collections.defaultdict(set)
    for r in maclar:
        ligler[r[2]].add((r[3], r[4]))

    os.makedirs(CIKTI, exist_ok=True)
    yaz(os.path.join(CIKTI, "maclar.json"), {
        "alanlar": ["tff", "tarih", "sezon", "kademe", "lig", "grup", "asama", "hafta", "ev", "dep", "ev_gol", "dep_gol", "ev_pen", "dep_pen", "ayrinti", "durum"],
        "maclar": maclar})

    krallar, oyuncular = {}, []
    if o:
        krallar, oyuncular = detay_aktar(o, c, tff_kulup, kulup)

    yaz(os.path.join(CIKTI, "ozet.json"), {
        "surum": datetime.datetime.now().strftime("%Y%m%d%H%M"),
        "mac": len(maclar), "oynanan": sum(r[10] is not None for r in maclar), "ayrintili": len(detay),
        "sezonlar": sezonlar, "ligler": {s: sorted(l) for s, l in ligler.items()},
        "kulupler": sorted(kulup.values(), key=lambda k: -k["mac"]), "krallar": krallar, "oyuncu": len(oyuncular)})
    toplam = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(CIKTI) for f in fs)
    print(f"kadın: {len(maclar)} maç ({len(detay)} ayrıntılı), {len(kulup)} kulüp, {len(oyuncular)} oyuncu -> {CIKTI} ({toplam / 1e6:.1f} MB)")


def detay_aktar(o, c, tff_kulup, kulup):
    okunur = tff_detay.kisi_okunur_kur(o, web_aktar.okunur)
    ad = {}
    kadro = collections.defaultdict(lambda: [[], []])
    for mac, taraf, kisi, a, forma, ilk11 in o.execute("SELECT mac, taraf, kisi, ad, forma, ilk11 FROM kadro ORDER BY rowid"):
        kadro[int(mac)][taraf - 1].append([forma, kisi, ilk11])
        ad.setdefault(kisi, a)
    olay = collections.defaultdict(list)
    for mac, taraf, kisi, a, dk, d1, d2, tip in o.execute("SELECT mac, taraf, kisi, ad, dakika, dk, ek, tip FROM gol"):
        olay[int(mac)].append([taraf, "G", d1, d2 or 0, kisi, None, tip])
        ad.setdefault(kisi, a)
    for mac, taraf, kisi, a, renk, dk, d1, d2 in o.execute("SELECT mac, taraf, kisi, ad, renk, dakika, dk, ek FROM kart"):
        olay[int(mac)].append([taraf, KART.get(renk, "Y"), d1, d2 or 0, kisi, None, None])
        ad.setdefault(kisi, a)
    giris, cikis = collections.defaultdict(dict), collections.defaultdict(dict)
    for mac, taraf, gir, gad, cik, cad, dk, d1, d2 in o.execute("SELECT * FROM degisiklik"):
        if gir or cik:
            olay[int(mac)].append([taraf, "S", d1, d2 or 0, cik, gir, None])
            if gir:
                giris[int(mac)][gir] = d1
                ad.setdefault(gir, gad)
            if cik:
                cikis[int(mac)][cik] = d1
                ad.setdefault(cik, cad)
    teknik = collections.defaultdict(lambda: [[], []])
    for mac, taraf, kisi, a in o.execute("SELECT mac, taraf, kisi, ad FROM teknik"):
        teknik[int(mac)][taraf - 1].append(okunur(a))
    hakem = collections.defaultdict(list)
    for mac, kisi, a, gorev in o.execute("SELECT mac, kisi, ad, gorev FROM hakem"):
        hakem[int(mac)].append([okunur(a), gorev or "Hakem"])
    bilgi = {int(m): (s, u) for m, s, u in o.execute("SELECT mac, stad, gol_uyum FROM mac_bilgi")}

    # maç dosyaları
    kova = collections.defaultdict(dict)
    for m, (stad, uyum) in bilgi.items():
        kova[m % KOVA][m] = {"s": stad, "u": uyum, "k": kadro[m], "o": sorted(olay[m], key=lambda x: (x[2] is None, x[2] or 0, x[3])),
                             "t": teknik[m], "h": hakem[m]}
    for b, d in kova.items():
        kisiler = {p[1] for r in d.values() for t in r["k"] for p in t} | {x[4] for r in d.values() for x in r["o"]} | \
                  {x[5] for r in d.values() for x in r["o"]}
        yaz(os.path.join(CIKTI, "m", f"{b}.json"), {"ad": {k: okunur(ad.get(k, "")) for k in kisiler if k}, "mac": d})

    # oyuncu istatistikleri: (kisi, sezon, kulüp, kademe) -> [maç, ilk11, gol, pen, sarı, kırmızı]
    O = collections.defaultdict(lambda: collections.defaultdict(lambda: [0] * 6))
    kul_oy = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, None, None]))
    kral = collections.defaultdict(collections.Counter)   # (sezon, kademe) -> kisi -> lig golü
    kral_kul = {}
    for m in bilgi:
        if m not in tff_kulup:
            continue
        ev, dep, sezon, kademe, lig = tff_kulup[m]
        for taraf, kid in ((1, ev), (2, dep)):
            for forma, kisi, ilk11 in kadro[m][taraf - 1]:
                if not kisi or not (ilk11 or kisi in giris[m]):
                    continue
                r = O[kisi][(sezon, kid, kademe if lig else 0)]
                r[0] += 1
                r[1] += ilk11
                k = kul_oy[kid][kisi]
                k[0] += 1
                k[2] = min(k[2] or sezon, sezon)
                k[3] = max(k[3] or sezon, sezon)
        for taraf, tur, d1, d2, k1, k2, tip in olay[m]:
            kid = ev if taraf == 1 else dep
            if tur == "G" and k1 and tip != "K" and not tff_detay.seri_mi(tip, d1, d2):
                r = O[k1][(sezon, kid, kademe if lig else 0)]
                r[2] += 1
                r[3] += tip == "P"
                kul_oy[kid][k1][1] += 1
                if lig:
                    kral[(sezon, kademe)][k1] += 1
                    kral_kul[(sezon, kademe, k1)] = kid
            elif tur in ("Y", "R", "YR") and k1:
                r = O[k1][(sezon, kid, kademe if lig else 0)]
                if tur == "Y":
                    r[4] += 1
                else:
                    r[5] += 1
    okova = collections.defaultdict(dict)
    dizin = []
    for kisi, sat in O.items():
        satir = [[s, kid, kad, *v] for (s, kid, kad), v in sorted(sat.items())]
        okova[kisi % KOVA][kisi] = {"ad": okunur(ad.get(kisi, "")), "s": satir}
        mac, gol = sum(x[3] for x in satir), sum(x[5] for x in satir)
        son = max(satir, key=lambda x: x[0])
        dizin.append([kisi, okunur(ad.get(kisi, "")), mac, gol, min(x[0] for x in satir), son[0], son[1]])
    for b, d in okova.items():
        yaz(os.path.join(CIKTI, "o", f"{b}.json"), {"oyuncu": d})
    yaz(os.path.join(CIKTI, "oyuncular.json"), {"alanlar": ["kisi", "ad", "mac", "gol", "ilk", "son", "son_kulup"], "oyuncular": dizin})
    for kid, d in kul_oy.items():
        yaz(os.path.join(CIKTI, "k", f"{kid}.json"), {"alanlar": ["kisi", "ad", "mac", "gol", "ilk", "son"],
            "oyuncular": sorted(([k, okunur(ad.get(k, "")), *v] for k, v in d.items()), key=lambda x: -x[2])})
    krallar = {}
    for (sezon, kademe), cnt in kral.items():
        en = cnt.most_common(1)[0][1]
        krallar.setdefault(sezon, {})[kademe] = [[k, okunur(ad.get(k, "")), n, kral_kul[(sezon, kademe, k)]] for k, n in cnt.most_common() if n >= en][:5]
    return krallar, dizin


if __name__ == "__main__":
    aktar()

"""Kadın ligleri -> docs/data/kadin/ (sitenin ayrı "Kadın" bölümü; erkek verisine hiç karışmaz).

  python3 kadin.py site      (ya da: python3 kadin_site.py)

Girdi: raw/kadin.db (kadin.py kur: maçlar, skorlar) ve raw/kadin_detay.db (kadin.py ayikla: kadro, gol, kart...).
Çıktı (kulüp, maç ve oyuncu dosyaları erkek bölümüyle aynı biçimde; app.js aynı sayfaları kadın verisiyle çizer):
  kadin/ozet.json        sezonlar, ligler, kulüpler, sezon gol kralları, ayrıntılı maç aralıkları
  kadin/maclar.json      bütün maçlar (bölümün sezon sayfaları için)
  kadin/kulup/<id>.json  kulübün maçları (web_aktar'ın kulup/<id>.json biçimi; maç no = TFF maç no)
  kadin/tff/...          maç ayrıntıları, oyuncu kariyerleri, kulüp oyuncu listeleri (tff_detay.aktar)

Kulüp adları: erkek takımıyla aynı TFF kulübü olanlar (Galatasaray, Fenerbahçe, Beşiktaş...) erkek bölümündeki adıyla
ve "(Kadın)" ekiyle yazılır; adında zaten Kadın/Bayan geçmeyen ve bir erkek kulübüyle aynı adı taşıyanlar da "(Kadın)" alır.
"""
import collections, datetime, json, os, shutil, sqlite3

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

    # ---- erkek bölümüyle aynı biçimde: kulüp maç dosyaları ve TFF ayrıntıları (kulüp, maç, oyuncu sayfaları app.js'in kodunu kullanır)
    m_dict = []
    for r in maclar:
        tff, tarih, sezon, kademe, lig, grup, asama, hafta, ev, dep, eg, dg, ep, dp, ayr, durum = r
        m_dict.append({"id": tff, "kaynak": "tff", "kaynak_id": str(tff), "yarisma": "lig", "lig": lig, "kademe": kademe, "sezon": sezon,
                       "grup": grup or None, "asama": "play-off" if asama else "lig", "tur": asama or None, "tarih": tarih, "saat": None,
                       "ev_kulup": ev, "dep_kulup": dep, "ev_adi": kulup[ev]["ad"], "dep_adi": kulup[dep]["ad"], "ev_gol": eg, "dep_gol": dg,
                       "ev_pen": ep, "dep_pen": dp, "durum": "MS" if eg is not None else None, "notlar": None})
    kulup_mac = collections.defaultdict(list)
    for m in m_dict:
        tur = m["grup"] if not m["tur"] else m["tur"]
        tur = f"{int(tur)}. grup" if tur and tur.isdigit() else tur or ""
        for s, r_ in (("ev", "dep"), ("dep", "ev")):
            kulup_mac[m[s + "_kulup"]].append([m["id"], m["tarih"], m["sezon"], "L", m["lig"], m["kademe"], tur, "p" if m["tur"] else "",
                                               "E" if s == "ev" else "D", m[s + "_adi"], m[r_ + "_kulup"], m[r_ + "_adi"],
                                               m[s + "_gol"], m[r_ + "_gol"], m[s + "_pen"], m[r_ + "_pen"], m["durum"], None])
    for kid, ms in kulup_mac.items():
        yaz(os.path.join(CIKTI, "kulup", f"{kid}.json"), {
            "alanlar": ["id", "tarih", "sezon", "yarisma", "lig", "kademe", "grup_tur", "playoff", "saha", "takim", "rakip_id",
                        "rakip", "attigi", "yedigi", "pen_a", "pen_y", "durum", "not"], "maclar": ms})
    for k, v in kulup.items():
        v.update(tff=[v["tff"]], ardil=[], yerli=True, enust=min((m[5] for m in kulup_mac[k] if not m[7]), default=None))
    tff_ayr, krallar, oyuncu = [], {}, 0
    if o:
        bellek = sqlite3.connect(":memory:")
        bellek.executescript("CREATE TABLE kulup_kimlik(kulup_id, kaynak, kaynak_id, ilk_sezon, son_sezon);"
                             "CREATE TABLE mac(kaynak, kaynak_id, tarih, ev_kulup, dep_kulup, yarisma);")
        bellek.executemany("INSERT INTO kulup_kimlik VALUES(?, 'tff', ?, NULL, NULL)", [(k, v["tff"][0]) for k, v in kulup.items()])
        eski = tff_detay.OYUNCU_DB, tff_detay.KUPA_ES
        tff_detay.OYUNCU_DB, tff_detay.KUPA_ES = DETAY_DB, os.path.join(KOK, "raw", "kadin_kupa_eslesme.json")
        try:
            tff_ayr = tff_detay.aktar(bellek, m_dict, web_aktar.okunur, CIKTI)
        finally:
            tff_detay.OYUNCU_DB, tff_detay.KUPA_ES = eski
        krallar = gol_krallari(o, tff_kulup)
        oyuncu = len(json.load(open(os.path.join(CIKTI, "tff", "oyuncular.json"), encoding="utf-8"))["oyuncu"])
    rekor_sayilar(m_dict, sezonlar, kulup)
    for eski_ in ("m", "o", "k", "oyuncular.json"):   # 17.11 öncesi kadın bölümüne özel dosyalar
        y = os.path.join(CIKTI, eski_)
        if os.path.isdir(y):
            shutil.rmtree(y)
        elif os.path.exists(y):
            os.remove(y)

    yaz(os.path.join(CIKTI, "ozet.json"), {
        "surum": datetime.datetime.now().strftime("%Y%m%d%H%M"),
        "mac": len(maclar), "oynanan": sum(r[10] is not None for r in maclar), "ayrintili": len(detay),
        "sezonlar": sezonlar, "ligler": {s: sorted(l) for s, l in ligler.items()}, "detayli": [], "detayli_aralik": web_aktar.araliklar(tff_ayr),
        "kulupler": sorted(kulup.values(), key=lambda k: -k["mac"]), "krallar": krallar, "oyuncu": oyuncu,
        "sampiyonlar": sampiyonlar(kulup), "sampiyon_not": json.load(open(SAMPIYON, encoding="utf-8")).get("_notlar", {})})
    toplam = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(CIKTI) for f in fs)
    print(f"kadın: {len(maclar)} maç ({len(tff_ayr)} ayrıntılı), {len(kulup)} kulüp, {oyuncu} oyuncu -> {CIKTI} ({toplam / 1e6:.1f} MB)")


KADEME_AD = {1: "Kadın Süper Ligi", 2: "Kadınlar 1. Ligi", 3: "Kadınlar 2. Ligi", 4: "Kadınlar 3. Ligi"}   # bugünkü adlar, seviyeye göre


def rekor_sayilar(maclar, sezonlar, kulup):
    """Erkek bölümünün Rekorlar ve Sayılar sayfaları için aynı biçimde: rekorlar.json, sayilar.json, yolculuk.json."""
    import rekor, sayilar
    sezon_sira = {s: i for i, s in enumerate(sorted(sezonlar, key=lambda s: (s[:4], s)))}
    eski_k, eski_d = rekor.KAPSAMLAR, sayilar.DERBI
    rekor.KAPSAMLAR = [("pro", "Bütün ligler", lambda m: True)] + [
        (str(k), ad, (lambda k_: lambda m: m["kademe"] == k_)(k)) for k, ad in KADEME_AD.items()]
    tff_kid = {v["tff"][0]: k for k, v in kulup.items()}
    sayilar.DERBI = {tff_kid[t]: ad for t, ad in (("3604", "Galatasaray (Kadın)"), ("3592", "Fenerbahçe (Kadın)"), ("3590", "Beşiktaş (Kadın)"), ("3596", "Trabzonspor (Kadın)")) if t in tff_kid}
    try:
        yaz(os.path.join(CIKTI, "rekorlar.json"), rekor.hesapla(maclar, sezon_sira, web_aktar.okunur))
        bellek = sqlite3.connect(":memory:")
        bellek.execute("CREATE TABLE puan_durumu(sezon, kademe, grup, sira, kulup, yarisma)")
        sy, yol = sayilar.hesapla(maclar, bellek)
        yaz(os.path.join(CIKTI, "sayilar.json"), sy)
        yaz(os.path.join(CIKTI, "yolculuk.json"), yol)
    finally:
        rekor.KAPSAMLAR, sayilar.DERBI = eski_k, eski_d


SAMPIYON = os.path.join(KOK, "kadin_sampiyon.json")


def sampiyonlar(kulup):
    """kadin_sampiyon.json (sezon -> TFF kulüp no) -> sezon -> kulüp kimliği (null: şampiyon yok)."""
    tff = {v["tff"][0]: k for k, v in kulup.items()}
    d = json.load(open(SAMPIYON, encoding="utf-8"))
    out = {}
    for s, t in d.items():
        if s.startswith("_"):
            continue
        if t is not None and t not in tff:
            raise SystemExit(f"kadin_sampiyon.json: {s} şampiyonu (TFF {t}) kulüp listesinde yok")
        out[s] = tff.get(t)
    return out


def gol_krallari(o, tff_kulup):
    """(sezon, kademe) -> en çok lig golü atan(lar): [[kişi, ad, gol, kulüp], ...]"""
    okunur = tff_detay.kisi_okunur_kur(o, web_aktar.okunur)
    kral, kul, ad = collections.defaultdict(collections.Counter), {}, {}
    for mac, taraf, kisi, a, dk, ek, tip in o.execute("SELECT mac, taraf, kisi, ad, dk, ek, tip FROM gol"):
        t = tff_kulup.get(int(mac))
        if not t or not t[4] or not kisi or tip == "K" or tff_detay.seri_mi(tip, dk, ek):
            continue
        ev, dep, sezon, kademe, _ = t
        kral[(sezon, kademe)][kisi] += 1
        kul[(sezon, kademe, kisi)] = ev if taraf == 1 else dep
        ad[kisi] = a
    out = {}
    for (sezon, kademe), cnt in kral.items():
        en = cnt.most_common(1)[0][1]
        out.setdefault(sezon, {})[kademe] = [[k, okunur(ad[k]), n, kul[(sezon, kademe, k)]] for k, n in cnt.most_common() if n >= en][:5]
    return out


if __name__ == "__main__":
    aktar()

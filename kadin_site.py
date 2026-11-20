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
        # sonra Vikipedi'deki kulüp sayfasının logosu (kadin_logo.py wiki_bul / wiki_indir)
        logo = e["logo"] if e and e.get("logo") else next((f"{o}{tff}" for o in ("tk", "wk") if os.path.exists(os.path.join(KOK, "docs", "logo", f"{o}{tff}.png"))), None)
        kulup[kid] = {"id": kid, "ad": gorunen, "adlar": adlar, "tff": tff, **({"logo": logo} if logo else {}),
                      **({"erkek": e["id"]} if e else {}), **({"renk": e["renk"]} if e and e.get("renk") else {})}

    # ---- maçlar
    detay = set()
    if o:
        detay = {int(m) for (m,) in o.execute("SELECT mac FROM mac_bilgi")}
    maclar, kul_mac = [], collections.Counter()
    sezon_kul = collections.defaultdict(set)
    for (mid, tff, sezon, kademe, lig, grup, asama, hafta, tarih, saat, ev, dep, eg, dg, ep, dp, ham, durum) in c.execute(
            "SELECT id, kaynak_id, sezon, kademe, lig, grup, asama, hafta, tarih, saat, ev_id, dep_id, ev_gol, dep_gol, ev_pen, dep_pen, ham_skor, durum "
            "FROM mac ORDER BY tarih IS NULL, tarih, saat, id"):
        # TFF maç no; fikstürde olmayıp puan tablosundan eklenen maçlar (kadin.py duzelt) eksi numara alır
        tff = int(tff) if tff.isdigit() else -mid
        asama = "" if asama == "lig" else ASAMA.get(asama, asama)
        maclar.append([tff, tarih, sezon, kademe, lig, grup or "", asama, hafta, ev, dep, eg, dg, ep, dp,
                       1 if tff in detay else 0, durum or (ham if eg is None and ham not in (None, "", "-") else None), saat or None])
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
        "alanlar": ["tff", "tarih", "sezon", "kademe", "lig", "grup", "asama", "hafta", "ev", "dep", "ev_gol", "dep_gol", "ev_pen", "dep_pen", "ayrinti", "durum", "saat"],
        "maclar": maclar})

    # ---- erkek bölümüyle aynı biçimde: kulüp maç dosyaları ve TFF ayrıntıları (kulüp, maç, oyuncu sayfaları app.js'in kodunu kullanır)
    m_dict = []
    for r in maclar:
        tff, tarih, sezon, kademe, lig, grup, asama, hafta, ev, dep, eg, dg, ep, dp, ayr, durum = r[:16]
        m_dict.append({"id": tff, "kaynak": "tff" if tff > 0 else "puan", "kaynak_id": str(tff), "yarisma": "lig", "lig": lig, "kademe": kademe, "sezon": sezon,
                       "grup": grup or None, "asama": "play-off" if asama else "lig", "tur": asama or None, "tarih": tarih, "saat": None,
                       "ev_kulup": ev, "dep_kulup": dep, "ev_adi": kulup[ev]["ad"], "dep_adi": kulup[dep]["ad"], "ev_gol": eg, "dep_gol": dg,
                       "ev_pen": ep, "dep_pen": dp, "durum": ("Hük." if durum == "Hük." else "MS") if eg is not None else None,
                       "notlar": "TFF puan tablosundan (fikstürde yok)" if tff < 0 else None})
    detayli = avrupa(m_dict, kulup)   # Türk kadın kulüplerinin UEFA maçları (kadin_avrupa.py)
    kulup_mac = collections.defaultdict(list)
    for m in m_dict:
        tur = m["grup"] if not m["tur"] else m["tur"]
        tur = f"{int(tur)}. grup" if tur and tur.isdigit() else tur or ""
        for s, r_ in (("ev", "dep"), ("dep", "ev")):
            kulup_mac[m[s + "_kulup"]].append([m["id"], m["tarih"], m["sezon"], "A" if m["yarisma"] == "avrupa" else "L", m["lig"], m["kademe"], tur,
                                               "p" if m["tur"] and m["yarisma"] != "avrupa" else "",
                                               "E" if s == "ev" else "D", m[s + "_adi"], m[r_ + "_kulup"], m[r_ + "_adi"],
                                               m[s + "_gol"], m[r_ + "_gol"], m[s + "_pen"], m[r_ + "_pen"], m["durum"], m["notlar"]])
    for kid, ms in kulup_mac.items():
        yaz(os.path.join(CIKTI, "kulup", f"{kid}.json"), {
            "alanlar": ["id", "tarih", "sezon", "yarisma", "lig", "kademe", "grup_tur", "playoff", "saha", "takim", "rakip_id",
                        "rakip", "attigi", "yedigi", "pen_a", "pen_y", "durum", "not"], "maclar": ms})
    for k, v in kulup.items():
        if v.get("yerli") is False:   # Avrupa rakibi (UEFA)
            v.update(enust=None)
            continue
        v.update(tff=[v["tff"]], ardil=[], yerli=True, enust=min((m[5] for m in kulup_mac[k] if not m[7] and m[3] == "L"), default=None))
    tff_ayr, krallar, oyuncu = [], {}, 0
    if o:
        bellek = sqlite3.connect(":memory:")
        bellek.executescript("CREATE TABLE kulup_kimlik(kulup_id, kaynak, kaynak_id, ilk_sezon, son_sezon);"
                             "CREATE TABLE mac(kaynak, kaynak_id, tarih, ev_kulup, dep_kulup, yarisma);")
        bellek.executemany("INSERT INTO kulup_kimlik VALUES(?, 'tff', ?, NULL, NULL)", [(k, v["tff"][0]) for k, v in kulup.items() if v["tff"]])
        eski = tff_detay.OYUNCU_DB, tff_detay.KUPA_ES
        tff_detay.OYUNCU_DB, tff_detay.KUPA_ES = DETAY_DB, os.path.join(KOK, "raw", "kadin_kupa_eslesme.json")
        try:
            tff_ayr = tff_detay.aktar(bellek, m_dict, web_aktar.okunur, CIKTI)
        finally:
            tff_detay.OYUNCU_DB, tff_detay.KUPA_ES = eski
        krallar = gol_krallari(o, tff_kulup)
        oyuncu = len(json.load(open(os.path.join(CIKTI, "tff", "oyuncular.json"), encoding="utf-8"))["oyuncu"])
    rekor_sayilar(m_dict, sezonlar, kulup)
    avrupa_oyuncu(kulup)   # Avrupa maçlarındaki oyuncular -> TFF kadın oyuncu sayfaları
    import kadin_milli   # Kadın A Milli Takımı -> kadin/milli.json, milli_detay.json
    if os.path.exists(kadin_milli.CIKTI):
        kadin_milli.site(yaz, CIKTI)
    # kırmızı kart analizi: kirmizi.py kadin yerelde üretir (depodaki kirmizi_kadin.json siteye kopyalanır)
    if os.path.exists(os.path.join(KOK, "kirmizi_kadin.json")):
        shutil.copy(os.path.join(KOK, "kirmizi_kadin.json"), os.path.join(CIKTI, "kirmizi.json"))
    for eski_ in ("m", "o", "k", "oyuncular.json"):   # 17.11 öncesi kadın bölümüne özel dosyalar
        y = os.path.join(CIKTI, eski_)
        if os.path.isdir(y):
            shutil.rmtree(y)
        elif os.path.exists(y):
            os.remove(y)

    yaz(os.path.join(CIKTI, "ozet.json"), {
        "surum": datetime.datetime.now().strftime("%Y%m%d%H%M"),
        "mac": len(maclar), "oynanan": sum(r[10] is not None for r in maclar), "ayrintili": len(detay),
        "sezonlar": sezonlar, "ligler": {s: sorted(l) for s, l in ligler.items()}, "detayli": detayli, "detayli_aralik": web_aktar.araliklar(tff_ayr),
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
    rekor.KAPSAMLAR = [("pro", "Bütün ligler", lambda m: m["yarisma"] == "lig")] + [
        (str(k), ad, (lambda k_: lambda m: m["yarisma"] == "lig" and m["kademe"] == k_)(k)) for k, ad in KADEME_AD.items()]
    tff_kid = {v["tff"][0]: k for k, v in kulup.items() if v["tff"]}
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
    tff = {v["tff"][0]: k for k, v in kulup.items() if v["tff"]}
    d = json.load(open(SAMPIYON, encoding="utf-8"))
    out = {}
    for s, t in d.items():
        if s.startswith("_"):
            continue
        if t is not None and t not in tff:
            raise SystemExit(f"kadin_sampiyon.json: {s} şampiyonu (TFF {t}) kulüp listesinde yok")
        out[s] = tff.get(t)
    return out


UEFA_HAM = os.path.join(KOK, "raw", "uefa_kadin")
UEFA_TFF = {"ALG Spor": "8472", "Ataşehir": "3580", "Beşiktaş": "3590", "Fenerbahçe": "3592", "Fomget SK": "6834",
            "Galatasaray": "3604", "Gazi": "2895", "Konak": "4270", "Trabzonspor": "3596"}   # UEFA adı -> TFF kulüp no
UEFA_YAR = {"UEFA Women's Champions League": "Kadınlar Şampiyonlar Ligi", "UEFA Women's Cup": "UEFA Kadınlar Kupası",
            "UEFA Women's Europa Cup": "Kadınlar Avrupa Kupası"}


def avrupa(m_dict, kulup):
    """raw/uefa_kadin -> m_dict'e Avrupa maçları (yarisma 'avrupa', maç no = UEFA maç no) ve kadin/mac/<no>.json ayrıntıları;
    rakip kulüpler kulup'a (no 900000 + UEFA takım no, yerli değil). Ayrıntılı maç numaralarını döner."""
    import glob, gzip
    from avrupa import UEFA_TUR
    yol = os.path.join(UEFA_HAM, "maclar.json")
    if not os.path.exists(yol):
        return []
    tff_kid = {v["tff"]: k for k, v in kulup.items() if isinstance(v.get("tff"), str)}
    out = []
    for dosya in sorted(glob.glob(os.path.join(UEFA_HAM, "mac", "*.json.gz"))):
        d = json.load(gzip.open(dosya, "rt", encoding="utf-8"))
        m = d["mac"]
        kid = {}
        for s_ in ("homeTeam", "awayTeam"):
            t = m[s_]
            tff = UEFA_TFF.get(t.get("internationalName")) if t.get("countryCode") == "TUR" else None
            if tff and tff in tff_kid:
                kid[s_] = tff_kid[tff]
            else:
                k = 900000 + int(t["id"])
                kulup.setdefault(k, {"id": k, "ad": t.get("internationalName"), "adlar": [], "tff": [], "ardil": [], "yerli": False,
                                     "ulke": t.get("countryCode"), "mac": 0})
                kid[s_] = k
        yil = int(m.get("seasonYear") or m["kickOffTime"]["date"][:4])
        sezon = f"{yil - 1}-{yil}"
        sk = (m.get("score") or {})
        top, pen = sk.get("total") or {}, sk.get("penalty") or {}
        yar = m.get("competition", {}).get("metaData", {}).get("name")
        lig = UEFA_YAR.get(yar, yar)
        tur_ = (m.get("round") or {}).get("metaData", {}).get("name") or ""
        tur = UEFA_TUR.get(tur_.lower(), tur_)
        ev, dep = kid["homeTeam"], kid["awayTeam"]
        mid = int(m["id"])
        m_dict.append({"id": mid, "kaynak": "uefa", "kaynak_id": str(mid), "yarisma": "avrupa", "lig": lig, "kademe": None, "sezon": sezon,
                       "grup": None, "asama": "avrupa", "tur": tur, "tarih": m["kickOffTime"]["date"], "saat": None,
                       "ev_kulup": ev, "dep_kulup": dep, "ev_adi": kulup[ev]["ad"], "dep_adi": kulup[dep]["ad"],
                       "ev_gol": top.get("home"), "dep_gol": top.get("away"), "ev_pen": pen.get("home"), "dep_pen": pen.get("away"),
                       "durum": "MS", "notlar": None})
        for k in (ev, dep):
            if kulup[k].get("yerli") is False:
                kulup[k]["mac"] += 1
                kulup[k]["ilk"] = min(kulup[k].get("ilk") or sezon, sezon); kulup[k]["son"] = max(kulup[k].get("son") or sezon, sezon)
        # ayrıntı: erkek Avrupa maç dosyalarıyla aynı biçim (oyuncu numarası yok: kadın UEFA oyuncu sayfası henüz yok)
        kadro, teknik = [[], []], [[], []]
        k_ = d.get("kadro") or {}
        for i, s_ in enumerate(("homeTeam", "awayTeam")):
            x = k_.get(s_) or {}
            for ilk11, bolum in ((1, "field"), (0, "bench")):
                for p in x.get(bolum) or []:
                    pl = p.get("player") or {}
                    kadro[i].append([str(p.get("jerseyNumber") or ""), pl.get("internationalName"), ilk11, 1 if p.get("isCaptain") else 0, None])
            for co in x.get("coaches") or []:
                if co.get("role", "COACH") == "COACH":
                    teknik[i].append((co.get("person") or {}).get("internationalName"))
        olay = []
        for e in d.get("olay") or []:
            pa, sa = e.get("primaryActor") or {}, e.get("secondaryActor") or {}
            taraf = 1 if (pa.get("team") or {}).get("id") == m["homeTeam"]["id"] else 2
            tm = e.get("time") or {}
            olay.append([taraf, e.get("type"), tm.get("minute"), tm.get("injuryMinute"), (pa.get("person") or {}).get("internationalName"),
                         (sa.get("person") or {}).get("internationalName"), e.get("subType") or e.get("goalType"), None, None])
        olay.sort(key=lambda o: (o[2] is None, o[2] or 0, o[3] or 0))
        hakem = next((r for r in m.get("referees") or [] if r.get("role") == "REFEREE"), None)
        st = m.get("stadium") or {}
        yaz(os.path.join(CIKTI, "mac", f"{mid}.json"), {
            "id": mid, "tarih": m["kickOffTime"]["date"], "saat": None, "sezon": sezon, "lig": lig, "tur": tur,
            "ev": [ev, kulup[ev]["ad"]], "dep": [dep, kulup[dep]["ad"]], "skor": [top.get("home"), top.get("away"), pen.get("home"), pen.get("away"), "MS"],
            "stad": ((st.get("translations") or {}).get("officialName") or {}).get("EN"),
            "sehir": (((st.get("city") or {}).get("translations") or {}).get("name") or {}).get("EN"),
            "seyirci": m.get("matchAttendance"), "hakem": (((hakem or {}).get("person") or {}).get("translations") or {}).get("name", {}).get("EN")
            or ((hakem or {}).get("person") or {}).get("internationalName"), "hakem_ulke": ((hakem or {}).get("person") or {}).get("countryCode"),
            "kaynak": "UEFA", "kadro": kadro, "teknik": teknik,
            "olay_alanlar": ["taraf", "tur", "dk", "ek", "oyuncu", "oyuncu2", "ayrinti", "oyuncu_no", "oyuncu2_no"], "olay": olay})
        out.append(mid)
    print(f"kadın Avrupa maçları: {len(out)}")
    return sorted(out)


def avrupa_oyuncu(kulup):
    """Türk kadın kulüplerinin UEFA maçlarında oynayanları TFF kadın oyuncularıyla eşler (oyuncu_bag.py'nin kuralları: aynı
    kulüpte o sezon ya da bir önceki sezon oynamış olmak, ad benzerliği, doğum tarihi tutması) -> kadin/avrupa_oyuncu.json;
    maç dosyalarındaki kadrolara oyuncu sayfası bağlantısı (kadin/mac/<no>.json, oyuncuOnek "k")."""
    import glob, gzip
    from oyuncu_bag import ad_puani, dogum_tutar
    tff_kid = {(v["tff"] if isinstance(v["tff"], str) else v["tff"][0]): k for k, v in kulup.items() if v.get("tff")}
    # TFF kadın oyuncuları: (sezon, kulüp) -> kişiler; ad, doğum
    tks, tad, tdog = collections.defaultdict(set), {}, {}
    for f in glob.glob(os.path.join(CIKTI, "tff", "o", "*.json")):
        for k, v in json.load(open(f, encoding="utf-8"))["oyuncu"].items():
            if "s" not in v:
                continue
            tad[k], tdog[k] = v["ad"], (v.get("d") or [None])[0]
            for r in v["s"]:
                if r[4]:
                    tks[(r[0], r[1])].add(k)
    katilim, oyuncu, maclar = collections.defaultdict(list), {}, {}
    dosyalar = sorted(glob.glob(os.path.join(UEFA_HAM, "mac", "*.json.gz")))
    for dosya in dosyalar:
        d = json.load(gzip.open(dosya, "rt", encoding="utf-8"))
        m = d["mac"]
        mid = int(m["id"])
        yil = int(m.get("seasonYear") or m["kickOffTime"]["date"][:4])
        sezon = f"{yil - 1}-{yil}"
        ol = d.get("olay") or []
        for i, s_ in enumerate(("homeTeam", "awayTeam")):
            t_ = m[s_]
            tff = UEFA_TFF.get(t_.get("internationalName")) if t_.get("countryCode") == "TUR" else None
            kid = tff_kid.get(tff)
            if kid is None:
                continue
            x = (d.get("kadro") or {}).get(s_) or {}
            for ilk11, bolum in ((1, "field"), (0, "bench")):
                for p in x.get(bolum) or []:
                    pl = p.get("player") or {}
                    pid = pl.get("id")
                    if not pid:
                        continue
                    kim = lambda e, r: ((e.get(r) or {}).get("person") or {}).get("id")
                    giris = next(((e.get("time") or {}).get("minute") for e in ol if e.get("type") == "SUBSTITUTION" and kim(e, "secondaryActor") == pid), None)
                    cikis = next(((e.get("time") or {}).get("minute") for e in ol if e.get("type") == "SUBSTITUTION" and kim(e, "primaryActor") == pid), None)
                    if not ilk11 and giris is None:
                        continue
                    gol = sum(e.get("type") == "GOAL" and kim(e, "primaryActor") == pid and (e.get("goalType") or e.get("subType")) != "OWN" for e in ol)
                    sari = sum(e.get("type") == "YELLOW_CARD" and kim(e, "primaryActor") == pid for e in ol)
                    kirm = sum(e.get("type") in ("RED_CARD", "RED_YELLOW_CARD", "YELLOW_CARD_SECOND") and kim(e, "primaryActor") == pid for e in ol)
                    oyuncu[pid] = (pl.get("internationalName"), pl.get("birthDate"))
                    katilim[pid].append([mid, kid, ilk11, gol, sari, kirm, giris, cikis, sezon])
    # eşleme
    bag = {}
    for pid, l in katilim.items():
        ad, dg = oyuncu[pid]
        aday = collections.Counter()
        for r in l:
            y = int(r[8][:4])
            for s in (r[8], f"{y - 1}-{y}"):
                for k in tks.get((s, r[1]), ()):
                    aday[k] += 1
        puan = []
        for k, ortak in aday.items():
            a, dt = ad_puani(ad, tad[k]), dogum_tutar(dg, tdog.get(k))
            if a >= 0.5 and dt is not False:
                puan.append((a + 0.3 * (dt is True) + 0.05 * min(ortak, 4), k))
        puan.sort(reverse=True)
        if puan and (len(puan) == 1 or puan[0][0] - puan[1][0] >= 0.05):
            bag[pid] = puan[0][1]
    # maç dosyalarına bağlantı ve oyuncu katılımları
    out = collections.defaultdict(list)
    for pid, l in katilim.items():
        if pid in bag:
            out[bag[pid]] += [r[:8] for r in l]
    for y in glob.glob(os.path.join(CIKTI, "mac", "*.json")):
        v = json.load(open(y, encoding="utf-8"))
        ad_kisi = {}
        dz = os.path.join(UEFA_HAM, "mac", f"{v['id']}.json.gz")
        if os.path.exists(dz):
            dd = json.load(gzip.open(dz, "rt", encoding="utf-8"))
            for s_ in ("homeTeam", "awayTeam"):
                for b_ in ("field", "bench"):
                    for p in ((dd.get("kadro") or {}).get(s_) or {}).get(b_) or []:
                        pl = p.get("player") or {}
                        if pl.get("id") in bag:
                            ad_kisi[pl.get("internationalName")] = int(bag[pl["id"]])
        for taraf in v["kadro"]:
            for p in taraf:
                p[4] = ad_kisi.get(p[1], p[4])
        v["oyuncuOnek"] = "k"
        for o in v["olay"]:
            o[7], o[8] = ad_kisi.get(o[4]), ad_kisi.get(o[5])
        maclar[v["id"]] = [v["tarih"], v["sezon"], v["lig"], v["tur"], v["ev"][0], v["dep"][0], v["ev"][1], v["dep"][1], v["skor"][0], v["skor"][1]]
        yaz(y, v)
    yaz(os.path.join(CIKTI, "avrupa_oyuncu.json"), {
        "alanlar": ["mac", "kulup", "ilk11", "gol", "sari", "kirmizi", "giris", "cikis"], "oyuncu": out,
        "mac_alanlar": ["tarih", "sezon", "lig", "tur", "ev", "dep", "ev_ad", "dep_ad", "ev_gol", "dep_gol"], "mac": maclar})
    print(f"kadın Avrupa oyuncuları: {len(katilim)} oyuncu, {len(bag)} TFF oyuncusuyla eşlendi")


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

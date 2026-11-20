#!/usr/bin/env python3
"""Kadın A Milli Takımı: TFF'nin maç listesi (pageID=441, sayfalı) ve maç sayfaları (pageID=440) -> kadin_milli_maclar.json.
Ayrıştırma ve site verisi milli.py'nin (erkek A milli) koduyla; site verisi docs/data/kadin/milli.json, milli_detay.json.

  python3 kadin_milli.py indir    # raw/tff_kadin_milli/liste_<n>.html + <macID>.html.gz (kaldığı yerden)
  python3 kadin_milli.py ayikla   # -> kadin_milli_maclar.json (depoda)
  python3 kadin_milli.py uefa     # UEFA maç servisinden kadrolar ve olaylar -> raw/uefa_kadin_milli/ (rakip kadrosu eksik maçlar için)
(kadin_site.py site verisini üretirken milli.site()'i bu dosyayla çağırır.)

Liste sayfaları ASP.NET form gönderimiyle (__doPostBack) sayfalanıyor: her sayfa bir öncekinin gizli alanlarıyla istenir.
"""
import gzip, html, http.cookiejar, os, re, sys, time, urllib.parse, urllib.request

import milli, topla

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "tff_kadin_milli")
CIKTI = os.path.join(KOK, "kadin_milli_maclar.json")
URL = "https://www.tff.org/Default.aspx?pageID=441"


def kur():
    """milli.py'yi kadın verisine yönlendir."""
    milli.HAM, milli.CIKTI = HAM, CIKTI
    milli.wiki_birlestir = lambda out: None   # Vikipedi tamamlaması yalnız erkek A milli için


def liste_indir():
    os.makedirs(HAM, exist_ok=True)
    acici = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    acici.addheaders = [("User-Agent", topla.UA)]
    t = acici.open(URL, timeout=90).read().decode("cp1254", "replace")
    n = 1
    while True:
        open(os.path.join(HAM, f"liste_{n}.html"), "w", encoding="cp1254", errors="replace").write(t)
        m = re.search(r"\b(\d+) / (\d+), Toplam (\d+) kayıt", t)
        print(f"  liste sayfası {n}" + (f" / {m.group(2)} ({m.group(3)} maç)" if m else ""), flush=True)
        hedef = re.search(r"__doPostBack\(&#39;([^&]*)&#39;,&#39;&#39;\)\">%d</a>" % (n + 1), t)
        if not hedef:
            break
        alan = {k: html.unescape(v) for k, v in re.findall(r'name="(__[A-Z]+)"[^>]*value="([^"]*)"', t)}
        alan.update(__EVENTTARGET=hedef.group(1), __EVENTARGUMENT="")
        time.sleep(2)
        t = acici.open(urllib.request.Request(URL, data=urllib.parse.urlencode(alan, encoding="cp1254").encode())).read().decode("cp1254", "replace")
        n += 1
    # milli.liste_oku tek dosya okur: sayfaları birleştir
    with open(os.path.join(HAM, "liste.html"), "w", encoding="cp1254", errors="replace") as f:
        for i in range(1, n + 1):
            f.write(open(os.path.join(HAM, f"liste_{i}.html"), encoding="cp1254", errors="replace").read())


def indir():
    kur()
    liste_indir()
    ms = milli.liste_oku()
    bugun = time.strftime("%Y-%m-%d")
    hedef = [m for m in ms if m["tarih"] and m["tarih"] < bugun and re.match(r"\d+\s*-\s*\d+", m["skor"])]
    eksik = [m for m in hedef if not os.path.exists(os.path.join(HAM, f"{m['tff']}.html.gz"))]
    print(f"{len(ms)} maç listede, {len(hedef)} oynanmış, {len(eksik)} sayfa indirilecek", flush=True)
    for i, m in enumerate(eksik, 1):
        kod, govde = milli.al(milli.MAC_URL.format(m["tff"]))
        if kod == "200" and len(govde) > 15000:
            with gzip.open(os.path.join(HAM, f"{m['tff']}.html.gz"), "wb") as g:
                g.write(govde)
        else:
            print("  hata", kod, m["tff"], flush=True)
            time.sleep(20)
        time.sleep(2)
    print("Bitti.", flush=True)


def ayikla():
    kur()
    milli.ayikla()


UEFA_HAM = os.path.join(KOK, "raw", "uefa_kadin_milli")   # Türkiye kadın A milli takımının UEFA maçları (takım no 500135)
UEFA_TR = "500135"
UEFA_TUR = {"GOAL": "G", "YELLOW_CARD": "Y", "RED_CARD": "R", "RED_YELLOW_CARD": "YR", "SUBSTITUTION": "S"}


def uefa_indir():
    """UEFA maç servisi: Türkiye kadın milli takımının maçları, kadroları ve olayları -> raw/uefa_kadin_milli/
    (TFF sayfasında rakip kadrosu olmayan maçları tamamlamak için; kaldığı yerden)."""
    import gzip, json
    import uefa_detay as U
    os.makedirs(os.path.join(UEFA_HAM, "mac"), exist_ok=True)
    out, off = {}, 0
    while True:
        d = U.al(f"{U.API}?teamId={UEFA_TR}&limit=100&offset={off}&order=ASC") or []
        out.update({m["id"]: m for m in d if m.get("status") == "FINISHED"})
        if len(d) < 100:
            break
        off += 100; time.sleep(0.5)
    json.dump(out, open(os.path.join(UEFA_HAM, "maclar.json"), "w", encoding="utf-8"), ensure_ascii=False)
    yeni = 0
    for mid, m in sorted(out.items()):
        yol = os.path.join(UEFA_HAM, "mac", f"{mid}.json.gz")
        if os.path.exists(yol):
            continue
        kadro = U.al(f"{U.API}/{mid}/lineups")
        olay = U.al(f"{U.API}/{mid}/events?filter=LINEUP&offset=0&limit=200")
        if kadro is None or olay is None:
            continue
        json.dump({"mac": m, "kadro": kadro, "olay": olay}, gzip.open(yol, "wt", encoding="utf-8"), ensure_ascii=False)
        yeni += 1; time.sleep(0.5)
    print(len(out), "UEFA maçı, yeni ayrıntı:", yeni)


def _sade(a):
    import unicodedata
    a = unicodedata.normalize("NFKD", (a or "").replace("ı", "i").replace("İ", "I")).encode("ascii", "ignore").decode().lower()
    return a.split()


def uefa_tamamla(detay, maclar):
    """TFF maç ayrıntılarındaki eksikleri UEFA maç verisinden doldurur (aynı gün tek UEFA maçı olanlar): boş kadro,
    teknik direktör, bir tarafın hiç olayı yoksa kartlar ve değişiklikler, golleri skordan eksik taraf (UEFA'nınki skorla
    tutuyorsa), stat, seyirci, hakem. Türkiye oyuncuları TFF kadrosuna soyadıyla bağlanır. Eklenenler "uq" listesinde.
    maclar: [tff, tarih, saha (E/D), attığı, yediği]. Döner: (tamamlanan maç sayısı, {tff: Türkiye teknik direktörü})."""
    import gzip, json
    yol = os.path.join(UEFA_HAM, "maclar.json")
    if not os.path.exists(yol):
        return 0, {}
    tarih = {}
    for mid, m in json.load(open(yol, encoding="utf-8")).items():
        tarih.setdefault(m["kickOffTime"]["date"], []).append(mid)
    en = lambda t, k: ((t or {}).get(k) or {}).get("EN")
    n, tr_td = 0, {}
    for tff, gun, saha, a, y in maclar:
        r = detay.get(tff)
        if not r or len(tarih.get(gun, [])) != 1:
            continue
        f = os.path.join(UEFA_HAM, "mac", f"{tarih[gun][0]}.json.gz")
        if not os.path.exists(f):
            continue
        d = json.load(gzip.open(f, "rt", encoding="utf-8"))
        m, k_ = d["mac"], d.get("kadro") or {}
        ek = []
        tr_s = "homeTeam" if m["homeTeam"]["id"] == UEFA_TR else "awayTeam"
        rk_s = "awayTeam" if tr_s == "homeTeam" else "homeTeam"
        tr_i = 0 if saha != "D" else 1                   # sitedeki Türkiye tarafı (TFF'deki saha)
        TR, RK = tr_i + 1, 2 - tr_i
        def kadro_al(s_):
            x_ = k_.get(s_) or {}
            kad = [[str(p.get("jerseyNumber") or ""), (p.get("player") or {}).get("internationalName"), ilk11, None, None]
                   for ilk11, b in ((1, "field"), (0, "bench")) for p in x_.get(b) or []]
            td = [[en((c.get("person") or {}).get("translations"), "name") or (c.get("person") or {}).get("internationalName"), None]
                  for c in x_.get("coaches") or [] if c.get("role", "COACH") == "COACH"]
            return kad, [t for t in td if t[0]]
        for i, s_ in ((tr_i, tr_s), (1 - tr_i, rk_s)):
            kad, td = kadro_al(s_)
            if kad and not r["k"][i]:
                r["k"][i] = kad; ek.append("kadro")
            if td and not r["t"][i]:
                r["t"][i] = td; ek.append("teknik direktör")
        if r["t"][tr_i]:
            tr_td[tff] = r["t"][tr_i][0][0]
        # Türkiye oyuncusunu TFF kadrosuna bağla: soyadı (UEFA "Ad Soyad" ya da yalnız soyad yazabiliyor)
        soy = {}
        for p in r["k"][tr_i]:
            for s_ in _sade(p[1])[1:] or _sade(p[1]):
                soy.setdefault(s_, set()).add((p[1], p[3]))
        def tr_bul(ad):
            for s_ in reversed(_sade(ad)):
                if len(soy.get(s_, ())) == 1:
                    return next(iter(soy[s_]))
            return (ad, None)
        lehine = lambda taraf, tip: taraf if tip != "K" else 3 - taraf      # kendi kalesine gol karşı tarafın hanesine
        tr_olay = any(o[0] == TR and o[1] != "G" for o in r["o"])
        rk_olay = any(o[0] == RK and o[1] != "G" for o in r["o"])
        ugol, olay_ek = {TR: [], RK: []}, False
        for e in d.get("olay") or []:
            tur = UEFA_TUR.get(e.get("type"))
            pa, sa = e.get("primaryActor") or {}, e.get("secondaryActor") or {}
            a1 = (pa.get("person") or {}).get("internationalName")
            if not tur or not a1:
                continue
            bizim = (pa.get("team") or {}).get("id") == UEFA_TR
            a2 = (sa.get("person") or {}).get("internationalName") if tur == "S" else None   # golde ikinci kişi kaleci
            k1 = k2 = None
            if bizim:
                a1, k1 = tr_bul(a1)
                if a2:
                    a2, k2 = tr_bul(a2)
            tm = e.get("time") or {}
            tip = {"PENALTY": "P", "OWN": "K"}.get(e.get("subType") or e.get("goalType")) if tur == "G" else None
            o = [TR if bizim else RK, tur, tm.get("minute"), tm.get("injuryMinute"), a1, a2, tip, k1, k2]
            if tur == "G":
                ugol[lehine(o[0], tip)].append(o)
            elif not (tr_olay if bizim else rk_olay):
                r["o"].append(o); olay_ek = True
        # goller: TFF'de bir tarafın golleri skordan azsa ve UEFA'nınki skorla tutuyorsa o tarafın golleri UEFA'dan
        for taraf, hedef in ((TR, a), (RK, y)):
            tff_n = sum(1 for o in r["o"] if o[1] == "G" and lehine(o[0], o[6]) == taraf)
            if hedef and tff_n < hedef and len(ugol[taraf]) == hedef:
                dk = {o[2] for o in ugol[taraf]}          # aynı dakikadaki TFF 'kendi kalesine' kaydı başka hanede yazılmış olabilir
                r["o"] = [o for o in r["o"] if not (o[1] == "G" and (lehine(o[0], o[6]) == taraf or (o[6] == "K" and o[2] in dk)))] + ugol[taraf]
                olay_ek = True
        if olay_ek:
            r["o"].sort(key=lambda o: (o[2] is None, o[2] or 0, o[3] or 0)); ek.append("olaylar")
        st = m.get("stadium") or {}
        stad = en(st.get("translations"), "officialName") or en(st.get("translations"), "name")
        sehir = en((st.get("city") or {}).get("translations"), "name")
        if stad and not r.get("s"):
            r["s"] = f"{stad}, {sehir}" if sehir and sehir not in stad else stad; ek.append("stat")
        if m.get("matchAttendance") and not r.get("sy"):
            r["sy"] = m["matchAttendance"]; ek.append("seyirci")
        hk = next((x for x in m.get("referees") or [] if x.get("role") == "REFEREE"), None)
        if hk and not r.get("hk"):
            p_ = hk.get("person") or {}
            r["hk"] = en(p_.get("translations"), "name") or p_.get("internationalName"); r["hu"] = p_.get("countryCode"); ek.append("hakem")
        if ek:
            r["uq"] = list(dict.fromkeys(ek)); n += 1
    return n, tr_td


def site(yaz, cikti):
    """milli.site'in çıktısı yazılmadan önce UEFA'yla tamamlanır; teknik direktör listesi TFF'de boşsa UEFA'dan."""
    import json
    kur()
    tut = {}
    milli.site(lambda yol, veri: tut.__setitem__(yol, veri), cikti)
    ms = json.load(open(CIKTI, encoding="utf-8"))
    satir = [[m["tff"], m["tarih"], "E" if m["ev"] == "TÜRKİYE" else "D",
              *((m["ev_gol"], m["dep_gol"]) if m["ev"] == "TÜRKİYE" else (m["dep_gol"], m["ev_gol"]))] for m in ms if m["ev_gol"] is not None]
    for yol, veri in tut.items():
        if yol.endswith("milli_detay.json"):
            n, tr_td = uefa_tamamla(veri, satir)
            print("kadın milli: UEFA'dan tamamlanan maç:", n)
    for yol, veri in tut.items():
        if yol.endswith("milli.json"):
            tek = veri["teknik"]
            bilinen = {t for _, l in tek.values() for t in l}
            sira = {x[0]: x[1] for x in veri["maclar"]}
            ek = {}
            for tff, ad in tr_td.items():
                if tff not in bilinen:
                    ek.setdefault(ad, []).append(tff)
            for ad, l in ek.items():
                anahtar = next((k for k, (a_, _) in tek.items() if a_ == ad), f"u{len(tek)}")
                tek.setdefault(anahtar, [ad, []])[1].extend(l)
                tek[anahtar][1].sort(key=lambda t: sira.get(t, ""))
        yaz(yol, veri)


if __name__ == "__main__":
    {"indir": indir, "ayikla": ayikla, "uefa": uefa_indir}[sys.argv[1]]()

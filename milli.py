"""A Milli Takım: TFF'nin bütün maç listesi (pageID=425) ve maç sayfaları (pageID=440) -> site verisi.

  python3 milli.py indir     # raw/tff_milli/liste.html + raw/tff_milli/<macID>.html.gz (kaldığı yerden)
  python3 milli.py ayikla    # milli_maclar.json (depoda; site verisi bundan üretilir)

web_aktar.py milli_maclar.json'dan docs/data/milli.json yazar.
"""
import collections, gzip, html, json, os, re, subprocess, sys, time

import oyuncu, topla

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "tff_milli")
CIKTI = os.path.join(KOK, "milli_maclar.json")
LISTE_URL = "https://www.tff.org/Default.aspx?pageID=425"
MAC_URL = "https://www.tff.org/Default.aspx?pageID=440&macID={}"


def al(url):
    r = subprocess.run(["curl", "-sL", "--compressed", "-m", "90", "-A", topla.UA, "-w", "\n%{http_code}", url], capture_output=True)
    govde, _, kod = r.stdout.rpartition(b"\n")
    return kod.decode().strip(), govde


def liste_oku():
    t = open(os.path.join(HAM, "liste.html"), "rb").read().decode("cp1254", "replace")
    out = []
    for ev, mid, skor, dep, tarih, org, tip in re.findall(
            r'_lnkKulup">([^<]*)</a>\s*</td><td>\s*<a[^>]*macID=(\d+)">([^<]*)</a>\s*</td><td>\s*<a[^>]*>([^<]*)</a>\s*</td><td>([^<]*)</td><td>([^<]*)</td><td>([^<]*)</td>', t):
        tarih = html.unescape(tarih).strip()
        g = re.match(r"(\d+)\.(\d+)\.(\d{4})", tarih)
        out.append({"tff": int(mid), "ev": html.unescape(ev).strip(), "dep": html.unescape(dep).strip(), "skor": html.unescape(skor).strip(),
                    "tarih": f"{g.group(3)}-{g.group(2)}-{g.group(1)}" if g else None, "org": " ".join(html.unescape(org).split())})
    return out


def indir():
    os.makedirs(HAM, exist_ok=True)
    kod, govde = al(LISTE_URL)
    if kod != "200" or b"rdgSonuclar" not in govde:
        sys.exit(f"liste alınamadı: {kod}")
    open(os.path.join(HAM, "liste.html"), "wb").write(govde)
    ms = liste_oku()
    bugun = time.strftime("%Y-%m-%d")
    hedef = [m for m in ms if m["tarih"] and m["tarih"] < bugun and re.match(r"\d+\s*-\s*\d+", m["skor"])]
    eksik = [m for m in hedef if not os.path.exists(os.path.join(HAM, f"{m['tff']}.html.gz"))]
    print(f"{len(ms)} maç listede, {len(hedef)} oynanmış, {len(eksik)} sayfa indirilecek", flush=True)
    for i, m in enumerate(eksik, 1):
        kod, govde = al(MAC_URL.format(m["tff"]))
        if kod == "200" and len(govde) > 15000:
            with gzip.open(os.path.join(HAM, f"{m['tff']}.html.gz"), "wb") as g:
                g.write(govde)
        else:
            print("  hata", kod, m["tff"], flush=True)
            time.sleep(20)
        if i % 50 == 0:
            print(f"  {i}/{len(eksik)}", flush=True)
        time.sleep(2)
    print("Bitti.", flush=True)


def sayfa_oku(t):
    """Milli maç sayfası (pageID=440): iki takımın kadrosu, golleri, kartları, değişiklikleri. Rakip oyuncuların TFF numarası
    yok (bağlantısız ad); Türk oyuncuların kisiId'si ve o günkü kulübü (hdnOynadigiKulup) var."""
    temiz = lambda x: " ".join(html.unescape(x or "").split())
    kisi = lambda h: int(h) if h and h != "0" else 0
    out = {"kadro": [], "gol": [], "kart": [], "degisiklik": [], "teknik": [], "hakem": []}
    a_ = r'(?:\s*href="Default\.aspx\?pageId=30&(?:amp;)?kisiId=(\d+)")?>([^<]*)</a>'
    for taraf in (1, 2):
        g = f"grdTakim{taraf}_"
        for bolum, ilk11 in (("rptKadrolar", 1), ("rptYedekler", 0)):
            for no, kid, ad, kul in re.findall(g + bolum + r'_ctl\d+_formaNo">([^<]*)</span>\s*<a id="[^"]*_lnkOyuncu"' + a_ +
                                               r'\s*<input[^>]*hdnOynadigiKulup"(?:\s*value="([^"]*)")?', t):
                out["kadro"].append((taraf, kisi(kid), temiz(ad), (no.strip(" .") or None), ilk11, temiz(kul) or None))
        for kid, metin in re.findall(g + r'rptGoller_ctl\d+_lblGol"' + a_, t):
            m = re.match(r"(.*),\s*(\d+(?:\+\d+)?)\.dk\s*\((\w)\)", temiz(metin))
            if m:
                dk, d1, d2 = oyuncu._dk(m.group(2) + ".dk")
                out["gol"].append((taraf, kisi(kid), m.group(1).strip(), dk, d1, d2, m.group(3)))
        for renk, kid, ad, dk in re.findall(g + r'rptKartlar_ctl\d+_k"[^>]*alt="([^"]*)"[^>]*/?>.*?_lblKart"' + a_ + r'.*?_d">([^<]*)<', t, re.S):
            out["kart"].append((taraf, kisi(kid), temiz(ad), temiz(renk), *oyuncu._dk(dk)))
        cik = re.findall(g + r'rptCikanlar_ctl\d+_lblCikan"' + a_ + r'.*?_oc">([^<]*)<', t, re.S)
        gir = re.findall(g + r'rptGirenler_ctl\d+_lblGiren"' + a_ + r'.*?_og">([^<]*)<', t, re.S)
        for i in range(max(len(cik), len(gir))):
            c_ = cik[i] if i < len(cik) else (None, "", "")
            g_ = gir[i] if i < len(gir) else (None, "", "")
            out["degisiklik"].append((taraf, kisi(g_[0]), temiz(g_[1]), kisi(c_[0]), temiz(c_[1]), *oyuncu._dk(g_[2] or c_[2])))
    return out


AY = {a: i for i, a in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}


def wiki_oku():
    """İngilizce Vikipedi 'Turkey national football team results (...)' maddeleri (raw/wiki_milli/*.json, API wikitext):
    maç kutularından tarih, skor, gol atanlar (Vikipedi bağlantısındaki tam adla), stat, seyirci, hakem."""
    out = []
    bag = lambda x: re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", x)
    for f in sorted(os.listdir(os.path.join(KOK, "raw", "wiki_milli"))):
        w = json.load(open(os.path.join(KOK, "raw", "wiki_milli", f), encoding="utf-8"))["parse"]["wikitext"]
        for kutu in re.split(r"\{\{\s*[Ff]ootball box", w)[1:]:
            alan = {}
            for k, v in re.findall(r"\n\s*\|\s*(\w+)\s*=([^\n]*)", kutu):
                alan.setdefault(k.strip(), v.strip())
            t = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", re.sub(r"\{\{[^}]*\}\}", "", alan.get("date", "")).strip())
            if not t or t.group(2) not in AY:
                continue
            kod = lambda x: (re.search(r"\{\{\s*fb(?:-rt)?\s*\|\s*(\w+)", x or "", re.I) or [None, None])[1]
            sk = re.match(r"(\d+)\s*[–-]\s*(\d+)", bag(alan.get("score", "")))
            def goller(x):
                l = []
                for parca in re.split(r"<br\s*/?>|\n", x or ""):
                    if "goal" not in parca.lower():
                        continue
                    link = re.search(r"\[\[([^|\]]*)(?:\|[^\]]*)?\]\]", parca)
                    ad = link.group(1) if link else re.sub(r"\{\{[^}]*\}\}|\(.*?\)", "", parca).strip(" ,")
                    for g in re.findall(r"\{\{\s*goals?\s*\|([^}]*)\}\}", parca, re.I):
                        p = [x.strip() for x in g.split("|")]
                        i = 0
                        while i < len(p):
                            if re.match(r"^\d+(\+\d+)?'?$", p[i]):
                                tip = "P" if i + 1 < len(p) and "pen" in p[i + 1].lower() else "K" if i + 1 < len(p) and "o.g" in p[i + 1].lower() else "F"
                                l.append([re.sub(r"\s*\(.*\)$", "", ad).strip(), p[i].rstrip("'"), tip])
                            i += 1
                return l
            t1, t2 = kod(alan.get("team1")), kod(alan.get("team2"))
            if "TUR" not in (t1, t2) and (re.search(r"Turkey|TUR\b", alan.get("team1", "")) or not t1):   # {{fb}} dışında yazılmış Türkiye
                t1 = "TUR" if (re.search(r"Turkey|TUR\b", alan.get("team1", "")) or not t1) and t2 != "TUR" else t1
            if "TUR" not in (t1, t2) and not t2:
                t2 = "TUR"
            out.append({"tarih": f"{t.group(3)}-{AY[t.group(2)]:02d}-{int(t.group(1)):02d}", "t1": t1, "t2": t2,
                        "skor": [int(sk.group(1)), int(sk.group(2))] if sk else None, "g1": goller(alan.get("goals1")), "g2": goller(alan.get("goals2")),
                        "stad": re.sub(r"\{\{[^}]*\}\}", "", bag(alan.get("stadium", ""))).strip(" ,") or None,
                        "seyirci": int(re.sub(r"\D", "", alan.get("attendance", "")) or 0) or None,
                        "hakem": re.sub(r"\{\{[^}]*\}\}|\(.*?\)", "", bag(alan.get("referee", ""))).strip(" ,") or None})
    return out


def sade(x):
    import unicodedata
    x = (x or "").replace("ı", "i").replace("İ", "i").replace("I", "i").lower()
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", x) if not unicodedata.combining(c) and (c.isalnum() or c == " ")).split())


def oyuncu_bul(ad, kadro):
    """Vikipedi adı -> TFF kadrosundaki oyuncu (kisi, ad). Tam ad, ya da soyadı / ad parçaları tek kişiyi gösteriyorsa."""
    n = sade(ad)
    if not n:
        return None
    l = [(k, a, sade(a)) for k, a in kadro]
    for f in (lambda s_: s_ == n, lambda s_: set(n.split()) <= set(s_.split()), lambda s_: n.split()[-1] in s_.split(),
              lambda s_: n.split()[0] in s_.split() and len(n.split()) == 1):
        a_ = [(k, a) for k, a, s_ in l if f(s_)]
        if len({k for k, _ in a_}) == 1:
            return a_[0]
    return None


def wiki_birlestir(out):
    """TFF gol listesi eksik ya da skorla uyuşmuyorsa ve Vikipedi'ninki uyuyorsa o tarafın gollerini Vikipedi'den alır;
    stat, seyirci ve hakem Vikipedi'den. Eklenen gol kaydının kaynağı 'w'."""
    W = collections.defaultdict(list)
    for w in wiki_oku():
        W[w["tarih"]].append(w)
    say = collections.Counter()
    genel = collections.defaultdict(set)   # bütün milli kadrolarda geçen adlar: kadrosu eksik maçta golcüyü bulmak için
    for m in out:
        for k in m.get("kadro", []):
            if k[1] and (k[0] == 1) == (m["ev"] == "TÜRKİYE"):
                genel[k[1]].add(k[2])
    genel_l = [(k, sorted(v)[0]) for k, v in genel.items()]
    for m in out:
        if "kadro" not in m or m["ev_gol"] is None:
            continue
        aday = [w for w in W.get(m["tarih"], []) if "TUR" in (w["t1"], w["t2"]) and w["skor"]]
        if len(aday) != 1:
            say["vikipedide yok"] += 1
            continue
        w = aday[0]
        ev_tr = m["ev"] == "TÜRKİYE"
        # Vikipedi tarafları -> TFF tarafları (1 = ev sahibi)
        w_tr = 1 if w["t1"] == "TUR" else 2
        tff_tr = 1 if ev_tr else 2
        wg = {tff_tr: w["g1"] if w_tr == 1 else w["g2"], 3 - tff_tr: w["g2"] if w_tr == 1 else w["g1"]}
        ws = {tff_tr: w["skor"][w_tr - 1], 3 - tff_tr: w["skor"][2 - w_tr]}
        if [ws[1], ws[2]] != [m["ev_gol"], m["dep_gol"]]:
            say["skor farklı"] += 1
            continue
        m["seyirci"] = w["seyirci"]; m["hakem_ad"] = w["hakem"]; m["stad"] = m.get("stad") or w["stad"]
        hedef = {1: m["ev_gol"], 2: m["dep_gol"]}
        def tff_say(taraf):   # TFF listesinde bu tarafa yazılan goller (kendi kalesine goller karşı tarafa)
            return sum(1 for g in m["gol"] if not oyuncu.seri_mi(g[6], g[4], g[5]) and ((g[0] == taraf) != (g[6] == "K")))
        for taraf in (1, 2):
            if tff_say(taraf) == hedef[taraf] or len(wg[taraf]) != hedef[taraf]:
                if tff_say(taraf) != hedef[taraf]:
                    say["iki kaynak da eksik"] += 1
                continue
            # bu tarafın TFF golleri (kendi kalesine goller dahil) atılır, Vikipedi'nin golleri yazılır
            m["gol"] = [g for g in m["gol"] if (g[0] == taraf) == (g[6] == "K")]
            kadro = [(k[1], k[2]) for k in m["kadro"] if k[0] == taraf and k[1]]
            rakip_kadro = [(k[1], k[2]) for k in m["kadro"] if k[0] != taraf and k[1]]
            for ad, dk, tip in wg[taraf]:
                d = oyuncu._dk(dk + ".dk")
                if tip == "K":   # kendi kalesine: karşı takımın oyuncusu
                    b_ = oyuncu_bul(ad, rakip_kadro)
                    m["gol"].append([3 - taraf, b_[0] if b_ else 0, b_[1] if b_ else ad, *d, "K", "w"])
                else:
                    b_ = oyuncu_bul(ad, kadro) or (oyuncu_bul(ad, genel_l) if taraf == tff_tr else None)
                    m["gol"].append([taraf, b_[0] if b_ else 0, b_[1] if b_ else ad, *d, tip, "w"])
                    if not b_ and taraf == tff_tr:
                        say["bağlanamayan Türk golcü"] += 1
                        print("   bağlanamadı:", m["tarih"], ad, "|", ", ".join(a for _, a in kadro)[:150])
            say[f"vikipediden ({'Türkiye' if taraf == tff_tr else 'rakip'})"] += 1
    print("Vikipedi:", dict(say))


def kulup_ayir(ad):
    """'UĞURCAN ÇAKIR ( GALATASARAY A.Ş. )' -> ('UĞURCAN ÇAKIR', 'GALATASARAY A.Ş.')"""
    m = re.match(r"(.*?)\s*\(\s*(.*?)\s*\)\s*$", ad or "")
    return (m.group(1).strip(), m.group(2).strip()) if m else ((ad or "").strip(), None)


def ayikla():
    import sqlite3, tff_detay, web_aktar
    ad_ = tff_detay.kisi_okunur_kur(sqlite3.connect(oyuncu.OYUNCU_DB), web_aktar.okunur)   # yabancı adlarda I = i
    ms = liste_oku()
    out = []
    for m in ms:
        sk = re.match(r"(\d+)\s*-\s*(\d+)", m["skor"])
        kayit = {**m, "ev_gol": int(sk.group(1)) if sk else None, "dep_gol": int(sk.group(2)) if sk else None}
        yol = os.path.join(HAM, f"{m['tff']}.html.gz")
        if os.path.exists(yol):
            t = gzip.open(yol).read().decode("cp1254", "replace")
            o = sayfa_oku(t)
            kadro = []
            for taraf, kisi, ad, forma, ilk11, kul in o["kadro"]:
                a, kul2 = kulup_ayir(ad)
                kul = kul or kul2
                kadro.append([taraf, kisi, ad_(a), ad_(kul) if kul else None, forma, ilk11])
            kayit.update(kadro=kadro, gol=[[x[0], x[1], ad_(kulup_ayir(x[2])[0]), *x[3:]] for x in o["gol"]],
                         kart=[[x[0], x[1], ad_(kulup_ayir(x[2])[0]), *x[3:]] for x in o["kart"]],
                         degisiklik=[[x[0], x[1], ad_(kulup_ayir(x[2])[0]), x[3], ad_(kulup_ayir(x[4])[0]), *x[5:]] for x in o["degisiklik"]],
                         teknik=[[x[0], x[1], ad_(x[2])] for x in o["teknik"]], hakem=[[x[0], ad_(x[1]), x[2]] for x in o["hakem"]])
            st = re.search(r'lblStad"[^>]*>([^<]*)<', t) or re.search(r'Stad[^"]*"[^>]*>([^<]{3,80})<', t)
            kayit["stad"] = html.unescape(st.group(1)).strip() if st else None
        out.append(kayit)
    wiki_birlestir(out)
    json.dump(out, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    ayr = [m for m in out if "kadro" in m]
    print(f"{len(out)} maç, {len(ayr)} ayrıntılı -> {CIKTI}")
    # doğrulama: gol listesi skorla tutuyor mu (Türkiye tarafı = TÜRKİYE yazan taraf)
    say = collections.Counter()
    for m in ayr:
        g = [0, 0]
        for taraf, kisi, a, dk, d1, d2, tip, *_ in m["gol"]:
            if oyuncu.seri_mi(tip, d1, d2):
                continue
            g[(2 - taraf) if tip == "K" else (taraf - 1)] += 1
        say["gol yok" if not m["gol"] else "tutuyor" if g == [m["ev_gol"], m["dep_gol"]] else "tutmuyor"] += 1
    print("gol listesi / skor:", dict(say))


KISA = {"UEFA", "FIFA", "RCD", "EURO", "ABD"}


def org_ad(org):
    """'DÜNYA ŞAMPİYONASI 2002 FİNALLERİ' -> 'Dünya Şampiyonası 2002 Finalleri' (Türkçe büyük/küçük harf, kısaltmalar korunur)"""
    def kelime(w):
        if w in KISA or not w[:1].isalpha():
            return w
        k = w.replace("I", "ı").replace("İ", "i").lower()
        return k[:1].replace("i", "İ").replace("ı", "I").upper() + k[1:]
    return " ".join(kelime(w) for w in org.split())


def kategori(org):
    o = org.upper()
    if "ÖZEL MAÇ" in o:
        return "Özel maç"
    if "ULUSLAR" in o:
        return "Uluslar Ligi"
    if "DÜNYA" in o:
        return "Dünya Kupası" if "FİNAL" in o else "Dünya Kupası elemeleri"
    if "AVRUPA" in o:
        return "Avrupa Şampiyonası" if "FİNAL" in o else "Avrupa Şampiyonası elemeleri"
    return "Diğer turnuvalar"   # Olimpiyat, Akdeniz Oyunları, Balkan, RCD, Konfederasyon Kupası...


def site(yaz, cikti):
    """milli_maclar.json -> docs/data/milli.json (liste, oyuncular, teknik direktörler) + milli_detay.json (maç ayrıntıları)."""
    if not os.path.exists(CIKTI):
        return
    ms = json.load(open(CIKTI, encoding="utf-8"))
    ulke = json.load(open(os.path.join(KOK, "milli_ulke.json"), encoding="utf-8"))
    TR = "TÜRKİYE"
    satir, detay = [], {}
    oy = collections.defaultdict(lambda: {"ad": None, "mac": 0, "ilk": 0, "gol": 0, "pen": 0, "sari": 0, "kirmizi": 0, "bas": None, "son": None, "kulup": collections.Counter()})
    td = collections.defaultdict(lambda: {"ad": None, "maclar": []})
    mac_gol, kal = [], collections.defaultdict(lambda: {"ad": None, "mac": 0, "gy": 0, "yenen": 0})
    for m in sorted(ms, key=lambda m: m["tarih"] or "9999"):
        if m["ev_gol"] is None or not m["tarih"]:
            continue
        ev_tr = m["ev"] == TR
        rakip = m["dep"] if ev_tr else m["ev"]
        a, y = (m["ev_gol"], m["dep_gol"]) if ev_tr else (m["dep_gol"], m["ev_gol"])
        satir.append([m["tff"], m["tarih"], ulke.get(rakip, [rakip])[0], rakip, "E" if ev_tr else "D", a, y, kategori(m["org"]), org_ad(m["org"]), 1 if "kadro" in m else 0])
        if "kadro" not in m:
            continue
        trt = 1 if ev_tr else 2   # Türkiye'nin taraf numarası sayfada
        giren = {x[1] for x in m["degisiklik"] if x[0] == trt and x[1]}   # [taraf, giren, giren adı, çıkan, çıkan adı, ...]
        for taraf, kisi, ad, kul, forma, ilk11 in m["kadro"]:
            if taraf != trt or not kisi or not (ilk11 or kisi in giren):
                continue
            o = oy[kisi]
            o["ad"] = ad; o["mac"] += 1; o["ilk"] += ilk11
            o["bas"] = o["bas"] or m["tarih"]; o["son"] = m["tarih"]
            if kul:
                o["kulup"][re.sub(r"\s+A\.?\s*Ş\.?$", "", kul)] += 1   # 'Galatasaray A.Ş.' = 'Galatasaray'
        for taraf, kisi, ad, dk, d1, d2, tip, *_ in m["gol"]:
            if taraf == trt and kisi and tip != "K" and not oyuncu.seri_mi(tip, d1, d2):
                oy[kisi]["gol"] += 1; oy[kisi]["pen"] += tip == "P"
        for taraf, kisi, ad, renk, dk, d1, d2 in m["kart"]:
            if taraf == trt and kisi:
                if renk == "Sarı Kart":
                    oy[kisi]["sari"] += 1
                else:
                    oy[kisi]["kirmizi"] += 1
        for taraf, ant, ad in m["teknik"]:
            if taraf == trt:
                td[ant]["ad"] = ad; td[ant]["maclar"].append(m["tff"])
        # rekorlar: bir maçta 3+ gol; kaleci (TFF ilk 11'i kaleciyle başlatıyor) gol yemeden
        bu = collections.Counter(x[1] for x in m["gol"] if x[0] == trt and x[1] and x[6] != "K" and not oyuncu.seri_mi(x[6], x[4], x[5]))
        for kisi, n in bu.items():
            if n >= 3:
                mac_gol.append([kisi, oy[kisi]["ad"], n, m["tff"], m["tarih"], ulke.get(rakip, [rakip])[0], 1 if m["ev"] == TR else 0])
        gk = next((k[1] for k in m["kadro"] if k[0] == trt and k[5] and k[1]), None)
        if gk:
            kal[gk]["mac"] += 1; kal[gk]["ad"] = oy[gk]["ad"]
            kal[gk]["gy"] += y == 0; kal[gk]["yenen"] += y
        # maç ayrıntısı: taraf 1 = ev sahibi (sayfadaki gibi)
        olay = [[x[0], "G", x[4], x[5], x[2], None, x[6], x[1] or None, None] for x in m["gol"] if not oyuncu.seri_mi(x[6], x[4], x[5])]
        olay += [[x[0], {"Sarı Kart": "Y", "Kırmızı Kart": "R"}.get(x[3], "YR"), x[5], x[6], x[2], None, None, x[1] or None, None] for x in m["kart"]]
        olay += [[x[0], "S", x[6], x[7], x[4], x[2], None, x[3] or None, x[1] or None] for x in m["degisiklik"]]
        olay.sort(key=lambda x: (x[2] is None, x[2] or 0, x[3] or 0))
        kadro = [[], []]
        for taraf, kisi, ad, kul, forma, ilk11 in m["kadro"]:
            kadro[taraf - 1].append([forma, ad, ilk11, kisi or None, kul])
        for l in kadro:
            l.sort(key=lambda p: (-p[2], int(p[0]) if str(p[0] or "").isdigit() else 99))
        teknik = [[], []]
        for taraf, ant, ad in m["teknik"]:
            teknik[taraf - 1].append([ad, ant])
        detay[m["tff"]] = {"k": kadro, "o": olay, "t": teknik, "h": [[h[1], (h[2] or "").split("(")[-1]] for h in m["hakem"]], "s": m.get("stad"),
                         "sy": m.get("seyirci"), "hk": m.get("hakem_ad")}
    oyuncular = {k: [v["ad"], v["mac"], v["ilk"], v["gol"], v["pen"], v["sari"], v["kirmizi"], v["bas"], v["son"],
                     [c for c, _ in v["kulup"].most_common()]] for k, v in oy.items()}
    tek = {k: [v["ad"], v["maclar"]] for k, v in td.items()}
    yaz(os.path.join(cikti, "milli.json"), {
        "ulke": ulke, "mac_alanlar": ["tff", "tarih", "rakip", "rakip_kod", "saha", "attigi", "yedigi", "kategori", "organizasyon", "ayrinti"],
        "maclar": satir, "oyuncu_alanlar": ["ad", "mac", "ilk11", "gol", "penalti", "sari", "kirmizi", "ilk", "son", "kulupler"],
        "oyuncu": oyuncular, "teknik": tek,
        "mac_gol_alanlar": ["kisi", "ad", "gol", "tff", "tarih", "rakip", "ic_saha"], "mac_gol": sorted(mac_gol, key=lambda x: (-x[2], x[4])),
        "kaleci_alanlar": ["kisi", "ad", "mac", "gol_yemeden", "yenen"],
        "kaleci": sorted([[k, v["ad"], v["mac"], v["gy"], v["yenen"]] for k, v in kal.items() if v["mac"] >= 5], key=lambda x: (-x[3], x[2]))})
    yaz(os.path.join(cikti, "milli_detay.json"), detay)
    print(f"milli: {len(satir)} maç, {len(detay)} ayrıntılı, {len(oyuncular)} oyuncu")


if __name__ == "__main__":
    {"indir": indir, "ayikla": ayikla}[sys.argv[1]]()

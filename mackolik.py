#!/usr/bin/env python3
"""Mackolik'ten eksik sezonlarin maclarini toplar.

  python3 mackolik.py sezonlar              # Mackolik'te hangi sezonlar var, hangileri eksik listemizde
  python3 mackolik.py indir --deneme        # 3 sezonluk deneme (1973-74, 1978-79, 1990-91)
  python3 mackolik.py indir                 # eksik sezonlarin hepsi (yarim kalirsa kaldigi yerden surer)
  python3 mackolik.py ayikla                # raw/mackolik -> mackolik_maclar.csv + kapsam ozeti
  python3 mackolik.py kesfet URL            # baska bir Mackolik ligi icin kimlik ve sezon listesi
  python3 mackolik.py arsiv URL [--yarisma 2lig]  # yeni sitenin 504 verdigi sezon: arsiv.mackolik.com'dan
                                            # (URL = bir grubun Standings sayfasi; ayni sezonun tum gruplari iner)
  python3 mackolik.py ligler                # arsiv sitesinden her sezonun donemdeki lig adlari ve gruplari
  python3 mackolik.py terfi                 # arsivden amatorden 2./3. Lig'e yukselme ligleri ve maclari
  python3 mackolik.py kupa                  # arsivden Turkiye Kupasi (1962-63'ten bugune)
  python3 mackolik.py kontrol               # arsiv puan tablolarindaki takim sayilari = CSV'dekiler mi

Her sezonun "puan-durumu" sayfasi o sezonun TUM maclarini icerir, yani sezon basina tek istek yeterli.
Sayfalar raw/mackolik/ altina .html.gz olarak saklanir. /api/ yollarina (robots.txt'de yasak) istek atilmaz.
Yalnizca Python standart kutuphanesi ve curl kullanir.
"""
import argparse, collections, csv, datetime, gzip, html, json, os, re, subprocess, sys, time, urllib.parse
from zoneinfo import ZoneInfo

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "mackolik")
PILOT = os.path.join(KOK, "raw", "pilot")
UA = "turk-futbol-db/0.1 (kisisel arsiv)"
BEKLE = 4.0          # istekler arasi bekleme (sn); sayfalar ~3-10 MB, siteyi yormayalim
SITE = "https://www.mackolik.com/puan-durumu"
TR = ZoneInfo("Europe/Istanbul")

# Mackolik yarismalari. "kademe" sezon baslangic yilindan kademeyi verir; None = bilinmiyor, elle belirlenmeli.
# Mackolik "Nesine 2. Lig" = 3. kademe serisi (1967-68'de basliyor, 1980-84 yok). Dogrulama (2026-11-09):
#  - Super Lig'den dusen/cikan 23 takimin (1967-81, takim kimligiyle) hicbiri bu seride yok -> 2. kademe degil.
#  - 1989-90 takimlari TFF 1990-91 3. Lig ile ortusuyor, 2. Lig ile neredeyse hic.
YARISMALAR = {
    "2lig": dict(id="2nttcoriwf5co73vmz1vr8frm", slug="türkiye-nesine-2-lig", pilot="mackolik_2lig_1973.html",
                 kademe=lambda yil: 3),
    # Super Lig: yalnizca TFF arsivinde mac verisi olmayan sezonlar indirilir (topla.py -> raw/tff/veri_yok.txt).
    "superlig": dict(id="482ofyysbdbeoxauk19yg7tdt", slug="türkiye-süper-lig", pilot="mackolik_superlig_1961.html",
                     kademe=lambda yil: 1, tff="superlig"),
    # 2. kademe (1963-90) icin kimligi "kesfet" ile bulup buraya ekleyin, ornek:
    # Eski 2. Lig (2. kademe) Mackolik'te bugunku 1. Lig yarismasinin altinda duruyor; sezonlar 1963-64'ten basliyor
    "1lig": dict(id="2o9svokc5s7diish3ycrzk7jm", slug="türkiye-trendyol-1-lig", pilot=None, kademe=lambda yil: 2),
}
# (yarisma, sezon): kademe. Yarismanin genel kuralina uymayan sezonlar icin elle duzeltme.
KADEME_ELLE = {}
# Mackolik ayni kulubu bazen iki kimlikle kaydediyor: eski kimlik -> kullanilacak kimlik. Takim adi oldugu gibi kalir.
TAKIM_BIRLESTIR = {
    # Kastamonuspor / GMG Kastamonuspor: 1969-90 arasi donusumlu; 1975-76'da ayni sezonda ikisi birden (28+2 mac)
    "btdqlwpxonx7ima1b4evszfqi": "a5mgs0c97s3ercxhy47rcewnp",
}
EKSIK = {2: (1963, 1989), 3: (1967, 1989)}   # kademe: (ilk, son) sezon baslangic yili
ARALIK = (min(a for a, _ in EKSIK.values()), max(b for _, b in EKSIK.values()))  # indirilecek yil araligi
DENEME = {("2lig", "1973-1974"), ("2lig", "1978-1979"), ("2lig", "1990-1991"), ("1lig", "1975-1976"), ("1lig", "1990-1991")}  # 1990-91 TFF'de de var
VERI_YOK = os.path.join(KOK, "raw", "tff", "veri_yok.txt")


def temiz(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def oku(yol):
    ac = gzip.open if yol.endswith(".gz") else open
    with ac(yol, "rb") as f:
        return f.read().decode("utf-8", "replace")


def sezon_listesi(t):
    """Sayfadaki sezon menusu: [(etiket '1973-1974', baslangic yili, sezon kimligi)]."""
    out = []
    for sid, ad in re.findall(r'component-dropdown__custom-item[^"]*"\s*data-value="(\w+)"\s*>\s*([^<]+?)\s*<', t):
        m = re.fullmatch(r"(\d{4})(?:/(\d{4}))?", ad.strip())
        if m:
            out.append((m.group(1) + (f"-{m.group(2)}" if m.group(2) else ""), int(m.group(1)), sid))
    return out


# Yalnizca arsiv sitesinden gelen yarismalar: kademe yok (amatorden yukselme maclari / kupa), asama sabit.
ARSIV_OZEL = {"terfi": "terfi", "kupa": "kupa"}


def kademe_bul(yar, etiket):
    if yar in ARSIV_OZEL:
        return None
    return KADEME_ELLE.get((yar, etiket), YARISMALAR[yar]["kademe"](int(etiket[:4])))


def curl(url, hedef, deneme=4):
    """Buyuk sezonlari sunucu yavas uretiyor (~70 sn): ilk istek 504 donup sonrakiler onbellekten gelebiliyor.
    Bu yuzden 5xx/zaman asiminda artan araliklarla yeniden dener."""
    gecici = hedef + ".tmp"
    for i in range(deneme):
        r = subprocess.run(["curl", "-sL", "--compressed", "-m", "180", "-A", UA, "-o", gecici, "-w", "%{http_code}", url],
                           capture_output=True, text=True)
        kod = r.stdout.strip()
        if not (kod.startswith("5") or kod in ("000", "429")) or i == deneme - 1:
            break
        bekle = (300 if kod == "429" else 30) * (i + 1)   # 429 = cok fazla istek: uzun ara ver
        print(f"    HTTP {kod}, {bekle} sn sonra yeniden denenecek", flush=True)
        time.sleep(bekle)
    ok = kod == "200" and os.path.exists(gecici) and os.path.getsize(gecici) > 50000
    if ok:
        with open(gecici, "rb") as f, gzip.open(hedef, "wb") as g:
            g.write(f.read())
    if os.path.exists(gecici):
        os.remove(gecici)
    return ok, kod


def yarisma_sayfasi(ad):
    y = YARISMALAR[ad]
    if y.get("pilot") and os.path.exists(os.path.join(PILOT, y["pilot"])):
        return oku(os.path.join(PILOT, y["pilot"]))
    yol = os.path.join(HAM, f"{ad}_menu.html.gz")
    if not os.path.exists(yol):
        os.makedirs(HAM, exist_ok=True)
        ok, kod = curl(f"{SITE}/{urllib.parse.quote(y['slug'])}/{y['id']}", yol)
        time.sleep(BEKLE)
        if not ok:
            sys.exit(f"{ad} menu sayfasi alinamadi (HTTP {kod})")
    return oku(yol)


def tff_veri_yok():
    """topla.py'nin yalnizca resim buldugu sezonlar: {(tff kaynak, etiket)}."""
    if not os.path.exists(VERI_YOK):
        return set()
    with open(VERI_YOK, encoding="utf-8") as f:
        return {tuple(x.split("\t")[:2]) for x in f if x.strip()}


def gerekli_mi(ad, etiket, yil, k, veri_yok):
    y = YARISMALAR[ad]
    if os.path.isfile(os.path.join(ARSIV_HAM, f"{ad}_{etiket}", "gruplar.tsv")) and \
            not os.path.exists(os.path.join(HAM, f"{ad}_{etiket}.html.gz")):
        return False   # yeni sitenin uretemedigi sezon arsivden alindi (orn. 1986-87 3. Lig)
    if y.get("tff") and (y["tff"], etiket) in veri_yok:
        return True
    if k is None:  # kademesi bilinmiyorsa eksik yil araliginda olmasi yeter
        return ARALIK[0] <= yil <= ARALIK[1]
    a = EKSIK.get(k)
    return bool(a) and a[0] <= yil <= a[1]


def hedefler(deneme=False):
    """[(yarisma, etiket, yil, kademe)] indirilecek sezonlar."""
    out, veri_yok = [], tff_veri_yok()
    for ad, y in YARISMALAR.items():
        for etiket, yil, _sid in sezon_listesi(yarisma_sayfasi(ad)):
            k = kademe_bul(ad, etiket)
            if (ad, etiket) in DENEME if deneme else gerekli_mi(ad, etiket, yil, k, veri_yok):
                out.append((ad, etiket, yil, k))
    return sorted(out, key=lambda x: (x[0], x[2]))


def sezonlar_komutu():
    for ad, y in YARISMALAR.items():
        ls = sezon_listesi(yarisma_sayfasi(ad))
        print(f"{ad} ({y['id']}): Mackolik'te {len(ls)} sezon, {ls[-1][0]} .. {ls[0][0]}")
    liste = hedefler()
    print(f"\nIndirilecek sezonlar ({len(liste)}):")
    for ad, etiket, yil, k in liste:
        print(f"  {ad} {etiket}: kademe {k if k else '? (ayikla ciktisina bakip KADEME_ELLE tablosuna ekleyin)'}")
    for k, (a, b) in EKSIK.items():
        var = {yil for _, _, yil, kk in liste if kk == k}
        yok = [f"{yil}-{yil + 1}" for yil in range(a, b + 1) if yil not in var]
        print(f"\nkademe {k}: eksik {b - a + 1} sezonun {b - a + 1 - len(yok)} tanesi Mackolik'te mevcut")


def indir(deneme):
    liste = hedefler(deneme)
    print(f"{len(liste)} sezon indirilecek")
    hata = 0
    for ad, etiket, yil, k in liste:
        yol = os.path.join(HAM, f"{ad}_{etiket}.html.gz")
        if os.path.exists(yol):
            continue
        os.makedirs(HAM, exist_ok=True)
        url = f"{SITE}/{urllib.parse.quote(YARISMALAR[ad]['slug'])}/{etiket}/{YARISMALAR[ad]['id']}"
        ok, kod = curl(url, yol)
        time.sleep(BEKLE)
        if not ok:
            hata += 1
            with open(os.path.join(KOK, "hatalar.log"), "a") as f:
                f.write(f"{time.strftime('%F %T')} {kod} {url}\n")
            print(f"  {ad} {etiket}: HATA {kod}", flush=True)
            if hata >= 5:
                sys.exit("5 hata alindi, duruyorum. Ayrinti: hatalar.log")
            continue
        t = oku(yol)
        if not re.search(rf"<title>[^<]*{yil}", t):
            print(f"  {ad} {etiket}: UYARI sayfa basligi sezonla uyusmuyor, dosyayi kontrol edin: {yol}")
        n = len(set(re.findall(r'data-match-id="(\w+)"', t)))
        print(f"  {ad} {etiket} (kademe {k or '?'}): {n} mac", flush=True)
    print("Bitti.")


def gruplar(t):
    """Puan tablosu gruplarindan takim kimligi -> grup adi."""
    tak = {}
    parcalar = re.split(r'<div class="p0c-competition-tables__group"', t)[1:]
    for p in parcalar:
        ad = re.search(r'comp-group-name[^>]*>(.*?)<', p, re.S)
        ad = temiz(ad.group(1)) if ad else ""
        for tid in re.findall(r'class="p0c-competition-tables__team">\s*<a href="[^"]*/([a-z0-9]+)"', p):
            tak.setdefault(tid, ad)
    if len(set(tak.values())) <= 1:
        return {k: None for k in tak}
    return tak


def maclar(t):
    sonuc, gorulen = [], set()
    for gun, blok in re.findall(r'<li class="p0c-competition-match-list__day\s+" data-day="([\d-]+)"(.*?)</ol>\s*</li>', t, re.S):
        for satir in re.split(r'<li class="p0c-competition-match-list__row"', blok)[1:]:
            mid = re.search(r'data-match-id="(\w+)"', satir).group(1)
            if mid in gorulen:
                continue
            gorulen.add(mid)
            bas = re.search(r'data-starttime="(\d+)"', satir)
            takim = re.findall(r'team-name--(home|away)[^"]*"[^>]*href="[^"]*/([a-z0-9]+)"\s*>\s*<span class="p0c-competition-match-list__team-full">(.*?)</span>', satir, re.S)
            skor = dict(re.findall(r'data-slot="score-(home|away)">(.*?)</span>', satir, re.S))
            durum = re.search(r'data-slot="status-box"[^>]*>(.*?)</a>', satir, re.S)
            ev = next((x for x in takim if x[0] == "home"), None)
            dep = next((x for x in takim if x[0] == "away"), None)
            if not ev or not dep:
                continue
            saat = datetime.datetime.fromtimestamp(int(bas.group(1)), TR).strftime("%H:%M") if bas else ""
            sg = lambda k: temiz(skor.get(k, ""))
            sonuc.append(dict(kaynak_id=mid, tarih=gun, saat=saat, ev_id=ev[1], ev_adi=temiz(ev[2]),
                              dep_id=dep[1], dep_adi=temiz(dep[2]), ev_gol=sg("home"), dep_gol=sg("away"),
                              durum=temiz(durum.group(1)) if durum else ""))
    return sonuc


ALANLAR = ["kaynak", "kaynak_id", "yarisma", "lig", "kademe", "sezon", "grup", "asama", "tarih", "saat",
           "ev_id", "ev_adi", "dep_id", "dep_adi", "ev_gol", "dep_gol", "ev_90", "dep_90", "ev_pen", "dep_pen", "durum", "kazanan"]


def sezon_bloklari(ham):
    """(kaynak, yarisma, sezon, {takim: grup}, maclar) -- yeni site sayfalari + arsiv.mackolik.com klasorleri."""
    yeni = set()
    for ad_dosya in sorted(os.listdir(ham)):
        m = re.fullmatch(r"(\w+?)_(\d{4}(?:-\d{4})?)\.html(?:\.gz)?", ad_dosya)
        if m and m.group(1) == "kupa":
            yield ("mackolik", "kupa", m.group(2), {}, kupa_yeni(m.group(2))[0])
            continue
        if not m or m.group(1) not in YARISMALAR:
            continue
        t = oku(os.path.join(ham, ad_dosya))
        yeni.add(m.groups())
        ms = maclar(t)
        yield ("mackolik", *m.groups(), gruplar(t), ms + arsivle_tamamla(*m.groups(), None, ms))
    if os.path.isdir(ARSIV_HAM):
        for klasor in sorted(os.listdir(ARSIV_HAM)):
            m = re.fullmatch(r"(\w+?)_(\d{4}-\d{4})", klasor)
            if not m:
                continue
            if m.groups() in yeni:
                continue   # yeni sitede de var: asagida tamamlama icin kullanilir
            if m.group(1) == "kupa":
                continue   # kupa maclari yeni siteden; arsiv klasoru yalnizca tur adlari/final kazanani icin
            g, ms = arsiv_maclar(os.path.join(ARSIV_HAM, klasor))
            yield ("mackolik_arsiv", *m.groups(), g, ms)


def arsivle_tamamla(yar, etiket, g, ms):
    """Yeni sitede eksik maclari ayni sezonun arsiv klasorunden ekler (orn. 1970-71 3. Lig Kirmizi'nin ilk 2 haftasi).
    Arsiv takim kimlikleri, ortak maclar (ayni tarih + ayni skor) uzerinden yeni site kimliklerine baglanir."""
    klasor = os.path.join(ARSIV_HAM, f"{yar}_{etiket}")
    if not os.path.isdir(klasor):
        return []
    ag, ams = arsiv_maclar(klasor)
    anahtar = collections.defaultdict(list)
    for x in ms:
        anahtar[(x["tarih"], x["ev_gol"], x["dep_gol"])].append(x)
    oy = collections.defaultdict(collections.Counter)
    for a in ams:
        for x in anahtar.get((a["tarih"], a["ev_gol"], a["dep_gol"]), []):
            oy[a["ev_id"]][x["ev_id"]] += 1
            oy[a["dep_id"]][x["dep_id"]] += 1
    es = {a: c.most_common(1)[0][0] for a, c in oy.items() if c.most_common(1)[0][1] >= 3}
    adlar = {x["ev_id"]: x["ev_adi"] for x in ms} | {x["dep_id"]: x["dep_adi"] for x in ms}
    var = collections.Counter((x["ev_id"], x["dep_id"]) for x in ms)
    ek = []
    for a in ams:
        ev, dep = es.get(a["ev_id"]), es.get(a["dep_id"])
        if not ev or not dep:
            continue
        if var[(ev, dep)]:
            var[(ev, dep)] -= 1   # bu eslesme yeni sitede zaten var
            continue
        ek.append(dict(a, kaynak="mackolik_arsiv", ev_id=ev, ev_adi=adlar[ev], dep_id=dep, dep_adi=adlar[dep]))
    eslesmeyen = len({a["ev_id"] for a in ams} | {a["dep_id"] for a in ams}) - len(es)
    print(f"{yar} {etiket}: arsivden {len(ek)} eksik mac eklendi"
          + (f" ({eslesmeyen} arsiv takimi eslesmedi)" if eslesmeyen else ""))
    return ek


# ---- arsiv.mackolik.com (eski site) --------------------------------------------------------------------
# Yeni sitenin uretemedigi (504) sezonlar icin. Grup sayfasi: /Standings/Default.aspx?sId=<grup sezon kimligi>;
# maclar AJAX ile hafta hafta gelir: /AjaxHandlers/FixtureHandler.aspx?command=getWeeks|getMatches.
# Takim ve mac kimlikleri yeni siteden farklidir (sayisal), bu yuzden kaynak = "mackolik_arsiv".
ARSIV = "https://arsiv.mackolik.com"
ARSIV_HAM = os.path.join(KOK, "raw", "mackolik_arsiv")
ARSIV_BEKLE = 40.0  # 2, 6 ve 15 sn ile site saatlik kotaya takildi (429)


def curl_metin(url, deneme=4):
    for i in range(deneme):
        r = subprocess.run(["curl", "-sL", "--compressed", "-m", "60", "-A", UA, "-w", "\n%{http_code}", url],
                           capture_output=True, text=True)
        govde, _, kod = r.stdout.rpartition("\n")
        if kod == "200":
            return govde
        if kod == "429" and i >= 1:
            sys.exit("HTTP 429 (cok fazla istek) surup gidiyor: biraz sonra ayni komutu yeniden calistirin, "
                     "inen haftalar atlanir ve kaldigi yerden devam eder.")
        bekle = (300 if kod == "429" else 20) * (i + 1)
        print(f"    HTTP {kod}, {bekle} sn sonra yeniden denenecek", flush=True)
        time.sleep(bekle)
    return None


def js_dizi(t):
    """Sitenin dondugu JS dizisini (tek tirnakli metin, bos alanlar ',,') liste listesine cevirir."""
    satirlar, alan, satir, tirnak, kac, derin = [], "", None, False, False, 0
    for c in t.strip():
        if tirnak:
            if kac:
                alan += c; kac = False
            elif c == "\\":
                kac = True
            elif c == "'":
                tirnak = False
            else:
                alan += c
        elif c == "'":
            tirnak = True
        elif c == "[":
            derin += 1
            if derin == 2:
                satir, alan = [], ""
        elif c == "]":
            if derin == 2:
                satir.append(alan.strip()); satirlar.append(satir)
            derin -= 1
        elif c == "," and derin == 2:
            satir.append(alan.strip()); alan = ""
        elif derin == 2:
            alan += c
    return satirlar


def arsiv_indir(url, yar):
    sid = (re.search(r"sId=(\d+)", url) or sys.exit("URL'de sId=<sayi> olmali")).group(1)
    t = curl_metin(f"{ARSIV}/Standings/Default.aspx?sId={sid}") or sys.exit("Sayfa alinamadi")
    yil = re.search(r"<title>[^<]*?(\d{4})/(\d{4})", t) or sys.exit("Sezon basliktan okunamadi")
    etiket = f"{yil.group(1)}-{yil.group(2)}"
    secenek = re.findall(r'<option value="(\d+)"[^>]*>([^<]*)</option>',
                         re.search(r'id="cboSubGroups".*?</select>', t, re.S).group(0))
    adlar = dict(secenek)
    onek = re.sub(r"\d+\.\s*Grup.*", "", adlar[sid]).strip()
    gruplar_ = [(s, a) for s, a in secenek if re.sub(r"\d+\.\s*Grup.*", "", a).strip() == onek]
    klasor = os.path.join(ARSIV_HAM, f"{yar}_{etiket}")
    print(f"{yar} {etiket} (kademe {kademe_bul(yar, etiket)}): {len(gruplar_)} grup -> {klasor}")
    arsiv_gruplari_indir(klasor, gruplar_)


def arsiv_gruplari_indir(klasor, gruplar_):
    """Her grubun hafta listesini ve hafta hafta maclarini indirir (inmis dosyalar atlanir)."""
    os.makedirs(klasor, exist_ok=True)
    with open(os.path.join(klasor, "gruplar.tsv"), "w", encoding="utf-8") as f:
        f.writelines(f"{s}\t{a}\n" for s, a in gruplar_)
    for s, a in gruplar_:
        yol = os.path.join(klasor, f"g{s}_haftalar.txt")
        if not os.path.exists(yol):
            h = curl_metin(f"{ARSIV}/AjaxHandlers/FixtureHandler.aspx?command=getWeeks&id={s}")
            if h is None:
                print(f"  {a}: hafta listesi alinamadi"); continue
            open(yol, "w", encoding="utf-8").write(h)
            time.sleep(ARSIV_BEKLE)
        haftalar_ = js_dizi(open(yol, encoding="utf-8").read())
        n = 0
        for hf in haftalar_:
            yol = os.path.join(klasor, f"g{s}_h{hf[0]}.txt")
            if not os.path.exists(yol):
                m = curl_metin(f"{ARSIV}/AjaxHandlers/FixtureHandler.aspx?command=getMatches&id={s}&week={hf[0]}")
                if m is None:
                    print(f"  {a} hafta {hf[0]}: alinamadi"); continue
                open(yol, "w", encoding="utf-8").write(m)
                time.sleep(ARSIV_BEKLE)
            n += len(js_dizi(open(yol, encoding="utf-8").read()))
        print(f"  {a}: {len(haftalar_)} hafta, {n} mac", flush=True)


def terfi_komutu():
    """Amatorden 2. ve 3. Lig'e yukselme ligleri/maclari (arsivdeki 'x.Lige Terfi ...' gruplari), tum sezonlar."""
    for etiket in sezon_etiketleri():
        gr = [(sid, ad) for sid, ad in arsiv_lig_listesi(etiket) or [] if re.search(r"Terfi|Baraj", ad)]
        if gr:
            print(f"terfi {etiket}: {len(gr)} grup", flush=True)
            arsiv_gruplari_indir(os.path.join(ARSIV_HAM, f"terfi_{etiket}"), [(str(a), b) for a, b in gr])


def grup_adi(ad):
    """'3.Lig 1.Grup' -> 'Grup 1', '3.Lig Kirmizi Grup' -> 'Kirmizi', '2.Lige Terfi Ligi Anadolu Grubu' -> 'Anadolu',
    '2.Futbol Ligi Grup A' -> 'Grup A', '3.Lig' -> ''."""
    ek = ad[len(re.sub(GRUP_EKI, "", ad).rstrip()):].strip()
    no = re.fullmatch(r"(\d+)\.\s*Grup", ek)
    if no:
        return f"Grup {no.group(1)}"
    return re.sub(r"\s+(Grup|Grubu|Grupu)$", "", ek) if not ek.startswith("Grup") else ek


def arsiv_maclar(klasor):
    g, ms, gorulen = {}, [], set()
    ilk_yil = int(re.search(r"_(\d{4})-\d{4}$", klasor).group(1))
    for satir in open(os.path.join(klasor, "gruplar.tsv"), encoding="utf-8"):
        s, ad = satir.rstrip("\n").split("\t")
        grup, lig = grup_adi(ad), lig_adi_kademe(ad)[0]
        hyol = os.path.join(klasor, f"g{s}_haftalar.txt")
        if not os.path.exists(hyol):   # henuz inmemis grup
            continue
        for hf in js_dizi(open(hyol, encoding="utf-8").read()):
            yol = os.path.join(klasor, f"g{s}_h{hf[0]}.txt")
            if not os.path.exists(yol):
                continue
            for x in js_dizi(open(yol, encoding="utf-8").read()):
                if x[0] in gorulen:
                    continue
                gorulen.add(x[0])
                gun, ay = map(int, x[1].split("/"))
                # yil sezondan: Temmuz-Aralik ilk yil, Ocak-Haziran ikinci yil (sitenin hafta tarihlerinde
                # yanlis yil olabiliyor, orn. 1986-87 10. Grup 18. hafta "7.02.1986")
                tarih = datetime.date(ilk_yil + (ay < 7), ay, gun)
                bitti = x[8] in ("4", "6", "8", "10")
                g[x[3]] = g[x[5]] = grup
                ms.append(dict(kaynak_id=x[0], tarih=tarih.isoformat(), saat="", ev_id=x[3], ev_adi=temiz(x[4]),
                               dep_id=x[5], dep_adi=temiz(x[6]), ev_gol=x[9] if bitti else "",
                               dep_gol=x[10] if bitti else "", durum=x[2], lig=lig))
    return g, ms


KUPA = dict(id="7af85xa75vozt2l4hzi6ryts7", slug="türkiye-ziraat-türkiye-kupası")


def kupa_komutu():
    """Turkiye Kupasi: maclar yeni siteden (sezon basina 1 sayfa), donemin tur adlari ve finalde turu gecen
    arsivden (sezon basina 1 istek: tur listesi + final maclari)."""
    menu = os.path.join(HAM, "kupa_menu.html.gz")
    if not os.path.exists(menu):
        ok, kod = curl(f"{SITE}/{urllib.parse.quote(KUPA['slug'])}/{KUPA['id']}", menu)
        if not ok:
            sys.exit(f"kupa menu sayfasi alinamadi (HTTP {kod})")
        time.sleep(BEKLE)
    for etiket, _yil, _sid in reversed(sezon_listesi(oku(menu))):
        yol = os.path.join(HAM, f"kupa_{etiket}.html.gz")
        if not os.path.exists(yol):
            ok, kod = curl(f"{SITE}/{urllib.parse.quote(KUPA['slug'])}/{etiket}/{KUPA['id']}", yol)
            time.sleep(BEKLE)
            if not ok:
                print(f"kupa {etiket}: HATA {kod}", flush=True); continue
        klasor = os.path.join(ARSIV_HAM, f"kupa_{etiket}")
        ayol = os.path.join(klasor, "sezon.html")
        if not os.path.exists(ayol):
            h = curl_metin(f"{ARSIV}/AjaxHandlers/CupHandler.aspx?command=seasonMatches&id=1&season={etiket.replace('-', '/')}")
            if h is not None:
                os.makedirs(klasor, exist_ok=True)
                open(ayol, "w", encoding="utf-8").write(h)
            time.sleep(ARSIV_BEKLE)
        ms, not_ = kupa_yeni(etiket)
        print(f"kupa {etiket}: {len(ms)} mac, {len({x['grup'] for x in ms})} tur{not_}", flush=True)


def kupa_yeni(etiket):
    """Yeni sitenin kupa sayfasina gomulu JSON'daki maclar. Tur adlari arsivden (sira ile) eslestirilir."""
    yol = os.path.join(HAM, f"kupa_{etiket}.html.gz")
    if not os.path.exists(yol):
        return [], ""
    t = html.unescape(oku(yol))
    dec, ham = json.JSONDecoder(), {}
    for m in re.finditer(r'"raw":\{"match":\{', t):
        try:
            o, _ = dec.raw_decode(t, m.end() - 1)
            ham[o["id"]] = o
        except ValueError:
            pass
    # turlar ilk mac tarihine gore kronolojik
    ilk = collections.defaultdict(lambda: "9999")
    for o in ham.values():
        ilk[o["round"]["id"]] = min(ilk[o["round"]["id"]], o["date_time_utc"] or "9999")
    yeni_turlar = sorted(ilk, key=lambda r: ilk[r])
    adlar = {o["round"]["id"]: o["round"]["name"] for o in ham.values()}
    ayol = os.path.join(ARSIV_HAM, f"kupa_{etiket}", "sezon.html")
    at = open(ayol, encoding="utf-8").read() if os.path.exists(ayol) else ""
    arsiv_turlar = [ad for _, ad in sorted(kupa_turlari(at), key=lambda x: int(x[0]))]
    not_ = ""
    if arsiv_turlar and len(arsiv_turlar) == len(yeni_turlar):
        adlar.update(zip(yeni_turlar, arsiv_turlar))
    elif at:
        not_ = f"  UYARI tur sayisi tutmuyor (yeni {len(yeni_turlar)}, arsiv {len(arsiv_turlar)}): yeni sitenin tur adlari kullanildi"
    ms = []
    for o in ham.values():
        a, b = o["team_A"], o["team_B"]
        zaman = o["date_time_utc"]
        if zaman:
            dt = datetime.datetime.strptime(zaman, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc).astimezone(TR)
            tarih, saat = dt.date().isoformat(), dt.strftime("%H:%M")
        else:
            tarih = saat = ""
        oynandi = o.get("status") == "Played"
        kaz = {a["id"]: a["name"], b["id"]: b["name"]}.get(o.get("round_winner"), "")
        ms.append(dict(kaynak_id=o["uuid"], tarih=tarih, saat=saat, ev_id=a["uuid"], ev_adi=temiz(a["name"]),
                       dep_id=b["uuid"], dep_adi=temiz(b["name"]),
                       # fts = 90 dk; uzatmaya giden macta son skor ets, penaltilar ps
                       ev_gol=str(o["ets_A"] if o.get("ets_A") is not None else o["fts_A"]) if oynandi and o["fts_A"] is not None else "",
                       dep_gol=str(o["ets_B"] if o.get("ets_B") is not None else o["fts_B"]) if oynandi and o["fts_B"] is not None else "",
                       ev_90=str(o["fts_A"]) if oynandi and o.get("ets_A") is not None else "",
                       dep_90=str(o["fts_B"]) if oynandi and o.get("ets_B") is not None else "",
                       ev_pen=str(o["ps_A"]) if o.get("ps_A") is not None else "",
                       dep_pen=str(o["ps_B"]) if o.get("ps_B") is not None else "",
                       durum=("Pen" if o.get("ps_A") is not None else "UZ" if o.get("ets_A") is not None else "MS") if oynandi
                       else (o.get("status") or ""), kazanan=temiz(kaz),
                       grup=adlar[o["round"]["id"]], lig="Türkiye Kupası"))
    # arsivin tur listesi sayfasi finalin maclarini da icerir: penaltiyla biten finalde turu gecen oradan
    for x in kupa_satirlari(at):
        if x["kazanan"]:
            for y in ms:
                if not y["kazanan"] and y["tarih"] == x["tarih"] and (y["ev_gol"], y["dep_gol"]) == (x["ev_gol"], x["dep_gol"]):
                    y["durum"] = x["durum"]   # orn. "Pen"
                    y["kazanan"] = x["kazanan"] if x["kazanan"] in (y["ev_adi"], y["dep_adi"]) else \
                        (y["ev_adi"] if x["kazanan"] == x["ev_adi"] else y["dep_adi"])
    return ms, not_


def kupa_turlari(t):
    return re.findall(r'getLegMatches\((\d+)\);[^>]*>\s*([^<]*?)\s*</li>', t)


def kupa_satirlari(t):
    """Kupa tur sayfasindaki mac satirlari. Turu gecen takim kalin (<b>) yazilir."""
    out = []
    for mid, govde in re.findall(r'<tr class="row[^"]*" id="row_(\d+)"(.*?)</tr>', t, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", govde, re.S)
        takim = re.findall(r'/Takim/(\d+)/[^"]*"[^>]*>(.*?)</a>', govde, re.S)
        skor = re.search(r'class="td_score">.*?<b>\s*(\d+)\s*-\s*(\d+)\s*</b>', govde, re.S)
        if len(takim) < 2:
            continue
        g, a, y = map(int, temiz(tds[0]).split("/"))
        y += 1900 if y >= 50 else 2000
        kazanan = next((temiz(ad) for _, ad in takim if "<b>" in ad), "")
        out.append(dict(kaynak_id=mid, tarih=f"{y:04d}-{a:02d}-{g:02d}", saat="", ev_id=takim[0][0],
                        ev_adi=temiz(takim[0][1]), dep_id=takim[1][0], dep_adi=temiz(takim[1][1]),
                        ev_gol=skor.group(1) if skor else "", dep_gol=skor.group(2) if skor else "",
                        durum=temiz(tds[1]), kazanan=kazanan))
    return out


def kupa_maclar(klasor):
    yol = os.path.join(klasor, "sezon.html")
    if not os.path.exists(yol):
        return {}, []
    ms, gorulen = [], set()
    for tid, ad in kupa_turlari(open(yol, encoding="utf-8").read()):
        y = os.path.join(klasor, f"tur_{tid}.html")
        if not os.path.exists(y):
            continue
        for x in kupa_satirlari(open(y, encoding="utf-8").read()):
            if x["kaynak_id"] not in gorulen:
                gorulen.add(x["kaynak_id"])
                ms.append(dict(x, grup=ad, lig="Türkiye Kupası"))
    return {}, ms


def arsiv_lig_listesi(etiket, indir=False):
    """Arsiv sitesinin o sezon icin listeledigi ligler/gruplar: [(sId, ad), ...]. indir=False ise yalnizca diskten."""
    yol = os.path.join(ARSIV_HAM, "sezonlar", f"{etiket}.txt")
    if not os.path.exists(yol):
        if not indir:
            return None
        t = curl_metin(f"{ARSIV}/AjaxHandlers/CompetitionHandler.aspx?op=seasons&group=1&year={etiket.replace('-', '/')}")
        if t is None:
            return None
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        open(yol, "w", encoding="utf-8").write(t)
        time.sleep(ARSIV_BEKLE)
    return [tuple(x) for x in json.loads(open(yol, encoding="utf-8").read().strip()[1:-1])["l"]]


GRUP_EKI = r"\s*(?:\d+\.\s*Grup|Grup\s+\S+|\S+\s+Grup(?:u)?|\S+\s+Grubu)\s*$"


def lig_adi_kademe(ad):
    """'3.Lig Kirmizi Grup' -> ('3.Lig', 3). 2001 oncesi adlarda bastaki rakam kademeyi verir; rakamsiz = 1. kademe
    ('Milli Ligi', '1.Ligi')."""
    taban = re.sub(GRUP_EKI, "", ad).strip()
    if re.search(r"Terfi|Mahalli|Baraj", taban):   # yukselme ligleri/maclari, baraj maclari, mahalli ligler: kademe disi
        return taban, None
    m = re.match(r"(\d)\.", taban)
    return taban, int(m.group(1)) if m else 1


def sezon_etiketleri():
    et = set()
    for d in (HAM, ARSIV_HAM):
        if os.path.isdir(d):
            for f in os.listdir(d):
                m = re.fullmatch(r"\w+?_(\d{4}(?:-\d{4})?)(?:\.html\.gz)?", f)
                if m:
                    et.add(m.group(1))
    return sorted(et)


def ligler_komutu():
    for etiket in sezon_etiketleri():
        l = arsiv_lig_listesi(etiket, indir=True)
        if l is None:
            print(f"{etiket}: alinamadi"); continue
        kad = collections.defaultdict(list)
        for sid, ad in l:
            taban, k = lig_adi_kademe(ad)
            kad[k].append(ad)
        print(f"{etiket}: " + " | ".join(f"k{k or '-'} {len(v)} grup ({re.sub(GRUP_EKI, '', v[0]).strip()})" for k, v in sorted(kad.items(), key=lambda x: x[0] or 9)), flush=True)


def kontrol_komutu(cikti):
    """Her sezon ve kademe icin arsivdeki puan tablolarinin takim sayisini CSV'deki takim sayisiyla karsilastirir.
    (Bir takimin TUM maclari kaynakta yoksa ic tamlik kontrolu bunu goremez; bu kontrol gorur.)"""
    bizde = collections.defaultdict(set)
    for x in csv.DictReader(open(cikti, encoding="utf-8")):
        if x["asama"] == "lig":
            bizde[(x["sezon"], x["kademe"])].update((x["ev_adi"], x["dep_adi"]))
    os.makedirs(os.path.join(ARSIV_HAM, "puan"), exist_ok=True)
    for etiket in sezon_etiketleri():
        kad = collections.defaultdict(list)
        for sid, ad in arsiv_lig_listesi(etiket) or []:
            _, k = lig_adi_kademe(ad)
            if k and bizde.get((etiket, str(k))):
                kad[k].append((sid, ad))
        for k, liste in sorted(kad.items()):
            n = 0
            for sid, ad in liste:
                yol = os.path.join(ARSIV_HAM, "puan", f"{sid}.json")
                if not os.path.exists(yol):
                    t = curl_metin(f"{ARSIV}/AjaxHandlers/StandingHandler.ashx?op=standing&id={sid}")
                    if t is None:
                        break
                    open(yol, "w", encoding="utf-8").write(t)
                    time.sleep(ARSIV_BEKLE)
                n += len(json.load(open(yol, encoding="utf-8"))["s"])
            b = len(bizde[(etiket, str(k))])
            print(f"{etiket} k{k}: arsiv {n} takim, bizde {b}" + ("" if n == b else "  <-- FARK"), flush=True)


def cift_kayit_ayikla(yar, etiket, ms):
    """Ayni mac iki kez, rakip iki ayri kimlikle girilmisse (orn. 1974-75 Super Lig: 'Kayserispor' ve
    'K.Erciyesspor' ayni iki macta) sezonda az gorunen kimlikli kopyayi atar."""
    sayi = collections.Counter()
    for x in ms:
        sayi.update((x["ev_id"], x["dep_id"]))
    anahtar = collections.defaultdict(list)
    for x in ms:
        anahtar[(x["tarih"], "ev", x["ev_id"], x["ev_gol"], x["dep_gol"])].append(x)
        anahtar[(x["tarih"], "dep", x["dep_id"], x["ev_gol"], x["dep_gol"])].append(x)
    at = set()
    for k, v in anahtar.items():
        if len(v) < 2 or not k[0] or k[3] == "":
            continue
        diger = "dep_id" if k[1] == "ev" else "ev_id"
        v = sorted(v, key=lambda x: -sayi[x[diger]])
        for x in v[1:]:
            if x[diger] != v[0][diger] and sayi[x[diger]] <= 3:
                at.add(id(x))
    if at:
        adlar = sorted({(x["ev_adi"] if sayi[x["ev_id"]] <= 3 else x["dep_adi"]) for x in ms if id(x) in at})
        print(f"{yar} {etiket}: {len(at)} cift kayit atildi ({', '.join(adlar)})")
    return [x for x in ms if id(x) not in at]


def ayikla(ham, cikti):
    satirlar, kapsam = [], []
    for kaynak, yar, etiket, g, ms in sezon_bloklari(ham):
        g = {TAKIM_BIRLESTIR.get(tid, tid): ad for tid, ad in g.items()}
        ms = cift_kayit_ayikla(yar, etiket, ms)
        # birlestirilen kimlikler (TAKIM_BIRLESTIR) sezon icinde tek ad tasisin: en sik gecen ad
        sik = collections.defaultdict(collections.Counter)
        for x in ms:
            for t in ("ev", "dep"):
                sik[TAKIM_BIRLESTIR.get(x[t + "_id"], x[t + "_id"])][x[t + "_adi"]] += 1
        ad_of = {tid: c.most_common(1)[0][0] for tid, c in sik.items()}
        k = kademe_bul(yar, etiket)
        # donemin lig adi (arsiv sitesindeki): ayni kademedeki gruplarin ortak adi
        liste = arsiv_lig_listesi(etiket)
        adlar = sorted({lig_adi_kademe(a)[0] for _, a in liste or [] if lig_adi_kademe(a)[1] == k})
        lig = " / ".join(adlar)
        if liste is not None and yar not in ARSIV_OZEL:
            ag = sum(1 for _, a in liste if lig_adi_kademe(a)[1] == k)
            bg = len({v for v in g.values() if v}) or 1
            if ag != bg:
                print(f"UYARI {yar} {etiket}: arsivde {ag} grup ({lig or '-'}), bizde {bg}")
        for x in ms:
            x["ev_id"] = TAKIM_BIRLESTIR.get(x["ev_id"], x["ev_id"])
            x["dep_id"] = TAKIM_BIRLESTIR.get(x["dep_id"], x["dep_id"])
            x["ev_adi"], x["dep_adi"] = ad_of[x["ev_id"]], ad_of[x["dep_id"]]
            # Bazi takimlar (cekilen/ihrac edilen?) puan tablosunda yok: grubu rakipten al.
            ge, gd = g.get(x["ev_id"]), g.get(x["dep_id"])
            if yar == "kupa":
                x["asama"] = "kupa"   # grup = tur adi (kupa_maclar'dan)
            elif ge and gd and ge != gd:  # farkli gruplarin takimlari: final / play-off (orn. 1959 Kirmizi-Beyaz finali)
                x.update(grup="", asama="play-off")
            else:
                x.update(grup=ge or gd or "", asama=ARSIV_OZEL.get(yar, "lig"))
            x.update(kaynak=x.get("kaynak", kaynak), yarisma=yar, lig=x.get("lig") or lig, kademe=k or "", sezon=etiket)
            satirlar.append(x)
        # Ayni grup ici eslesme normalden fazla tekrarliyorsa fazlasi ikinci tur maci (orn. 1965-66 2. kademe:
        # 11'er takimli iki grup, sonra ilk dortlerin 8 takimli final grubu). Tarih sirasiyla ilk 'devre' mac lig sayilir.
        ciftler = collections.defaultdict(list)
        for x in ms:
            if x["asama"] == "lig":
                ciftler[(x["grup"], frozenset((x["ev_id"], x["dep_id"])))].append(x)  # ev/dep bakilmaz: saha degisen maclar
        for gr in {c[0] for c in ciftler}:
            devre = collections.Counter(len(v) for c, v in ciftler.items() if c[0] == gr).most_common(1)[0][0]
            for c, v in ciftler.items():
                if c[0] == gr:
                    for x in sorted(v, key=lambda x: (x["tarih"], x["saat"]))[devre:]:
                        x.update(grup="", asama="play-off")
        sayac = collections.defaultdict(lambda: [set(), 0, collections.Counter()])
        for x in ms:
            s = sayac[x["grup"]]
            s[0].update((x["ev_id"], x["dep_id"]))
            s[1] += 1
            s[2][(x["ev_id"], x["dep_id"])] += 1
        for gr, (tk, n, ciftler) in sorted(sayac.items()) if yar != "kupa" else []:   # kupa: eleme, sayim anlamsiz
            # devre: ayni ev-deplasman eslesmesinin en sik tekrar sayisi (1979-80 gibi 4 devreli ligler icin 2)
            devre = collections.Counter(ciftler.values()).most_common(1)[0][0]
            # play-off / final maclarinin bicimi sezona gore degisir: beklenen sayi hesaplanmaz
            kapsam.append((k or "?", etiket, gr or "-", len(tk), n, len(tk) * (len(tk) - 1) * devre if gr else n))
        if not k and yar not in ARSIV_OZEL:
            print(f"UYARI {yar} {etiket}: kademe bilinmiyor ({len(sayac)} grup, "
                  f"{len({t for s in sayac.values() for t in s[0]})} takim). KADEME_ELLE tablosuna ekleyin.")
    with open(cikti, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ALANLAR, restval="")
        w.writeheader()
        w.writerows(satirlar)
    print(f"{len(satirlar)} mac -> {cikti}\n")
    print(f"{'kademe':>6} {'sezon':<10} {'grup':<14} {'takim':>5} {'mac':>5} {'beklenen':>8}")
    for k, s, gr, tk, n, b in kapsam:
        isaret = "" if n == b else "  <-- eksik/fazla"
        print(f"{k:>6} {s:<10} {gr:<14} {tk:>5} {n:>5} {b:>8}{isaret}")


def kesfet(url):
    m = re.search(r"/puan-durumu/([^/]+)/(?:[^/]+/)*([a-z0-9]{20,30})/?$", urllib.parse.unquote(url))
    if not m:
        sys.exit("URL bir Mackolik puan-durumu adresi olmali, ornek: https://www.mackolik.com/puan-durumu/<lig>/<kimlik>")
    os.makedirs(HAM, exist_ok=True)
    yol = os.path.join(HAM, f"kesfet_{m.group(2)}.html.gz")
    if not os.path.exists(yol):
        ok, kod = curl(url, yol)
        if not ok:
            sys.exit(f"Sayfa alinamadi (HTTP {kod})")
    t = oku(yol)
    ls = sezon_listesi(t)
    print("baslik :", temiz((re.search(r"<title>(.*?)</title>", t, re.S) or [None, ""])[1]))
    print("kimlik :", m.group(2), "| slug:", m.group(1))
    print("sezonlar:", ", ".join(e for e, _, _ in reversed(ls)))
    print(f'\nYARISMALAR sozlugune eklemek icin:\n    "ad": dict(id="{m.group(2)}", slug="{m.group(1)}", pilot=None, kademe=lambda yil: None),')


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("komut", choices=["sezonlar", "indir", "ayikla", "kesfet", "arsiv", "ligler", "kontrol", "terfi", "kupa"])
    p.add_argument("url", nargs="?")
    p.add_argument("--deneme", action="store_true")
    p.add_argument("--yarisma", default="2lig", help="arsiv: sezonun hangi seriye ait oldugu (kademe buradan)")
    p.add_argument("--ham", default=HAM)
    p.add_argument("--cikti", default=os.path.join(KOK, "mackolik_maclar.csv"))
    a = p.parse_args()
    if a.komut == "sezonlar":
        sezonlar_komutu()
    elif a.komut == "indir":
        indir(a.deneme)
    elif a.komut == "ayikla":
        ayikla(a.ham, a.cikti)
    elif a.komut == "terfi":
        terfi_komutu()
    elif a.komut == "kupa":
        kupa_komutu()
    elif a.komut == "kontrol":
        kontrol_komutu(a.cikti)
    elif a.komut == "ligler":
        ligler_komutu()
    elif a.komut == "arsiv":
        arsiv_indir(a.url or sys.exit("arsiv icin grup sayfasi URL'si verin"), a.yarisma)
    else:
        kesfet(a.url or sys.exit("kesfet icin URL verin"))

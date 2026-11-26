"""TFF maç sayfalarından (raw/oyuncu.db, oyuncu.py ayikla) site verisi: maç ayrıntıları, oyuncu sayfaları, kulüplerin oyuncu listeleri.

web_aktar.py çağırır. Çıktı docs/data/tff/ altında; TFF maç numarasıyla (macId) anahtarlanır, futbol.db maç numaraları
değişse de dosyalar geçerli kalır:
  tff/var.json             ayrıntısı olan TFF maç numaraları (artışlarla) ve futbol.db'ye bağlanmayan kupa maçlarının eşlemesi
  tff/dizin.json           futbol.db maç no -> TFF maç no (web_aktar her çalışmada yeniden yazar)
  tff/m/<macId//250>.json maç ayrıntıları (kadro, gol, kart, değişiklik, teknik direktör, hakem)
  tff/o/<kisi%500>.json    oyuncu kariyeri: sezon x kulüp x yarışma satırları
  tff/oyuncular.json       oyuncu arama dizini
  tff/kulup/<id>.json      kulübün en çok gol atan ve en çok maça çıkan oyuncuları

raw/oyuncu.db yoksa (GitHub Actions) yalnız dizin.json yeniden yazılır; diğer dosyalar olduğu gibi kalır.
"""
import collections, datetime, json, os, shutil, sqlite3

KOK = os.path.dirname(os.path.abspath(__file__))
# elle düzeltilen TFF doğum tarihleri (TFF kişi no -> tarih)
DOGUM_DUZELT = {int(k): v[0] for k, v in json.load(open(os.path.join(KOK, "dogum_duzeltme.json"), encoding="utf-8")).items() if k.isdigit()}
OYUNCU_DB = os.path.join(KOK, "raw", "oyuncu.db")
KUPA_ES = os.path.join(KOK, "tff_kupa_eslesme.json")   # Maçkolik kupa maçı -> TFF maç no (1990-2007 kupa sayfaları)
YAR = {"lig": "L", "kupa": "K", "ozel_kupa": "O", "avrupa": "A", "terfi": "T"}
MK_KUPA = 70_500_000   # 1990 öncesi Türkiye Kupası / Süper Kupa maçlarının ayrıntı numarası (Maçkolik arşiv kadrosu)
MK_MAC = 70_000_000   # TFF'de olmayan (Maçkolik kaynaklı, 1984-85 öncesi Süper Lig) maçların ayrıntı numarası:
# MK_MAC + Maçkolik maç kimliklerinin sıralı listesindeki yeri (sıkışık numara: ayrıntı dosyaları no // 250 ile gruplanır;
# bu maçların listesi tarihî ve sabit olduğu için numaralar her kurulumda aynı kalır)


MK_ILK = None   # Maçkolik arşiv kadrolarının en eski sezonu (maclari_yaz doldurur; site notları için ozet.json'a)
KART = {"Sarı Kart": "Y", "Kırmızı Kart": "R", "Çift Sarı Kart": "YR"}


def seri_mi(tip, dk, ek):
    return tip == "S" or (tip == "P" and (dk is None or (dk == 90 and (ek or 0) >= 30)))


def yaz(yol, veri):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, separators=(",", ":"))


def artis(l):
    """[5, 6, 9] -> [5, 1, 3]"""
    return [b - a for a, b in zip([0] + l[:-1], l)]


def geri(l):
    out, t = [], 0
    for x in l:
        t += x
        out.append(t)
    return out


def kupa_eslestir(o, c):
    """TFF'nin 1990-2007 kupa sayfalarını ve Süper Kupa maçlarını futbol.db'deki (Maçkolik / Vikipedi kaynaklı) maçlara bağlar:
    tarih + iki kulüp."""
    tff_kulup = collections.defaultdict(list)   # TFF kulüp no -> [(kulüp, ilk sezon, son sezon)]; '2434-once' gibi dönemli kimlikler
    for kid, tid, ilk, son in c.execute("SELECT kulup_id, kaynak_id, ilk_sezon, son_sezon FROM kulup_kimlik WHERE kaynak='tff'"):
        tff_kulup[int(tid.split("-")[0])].append((kid, ilk or "0000", son or "9999"))
    def kulup(tid, tarih):
        y, ay = int(tarih[:4]), int(tarih[5:7])
        sezon = f"{y}-{y + 1}" if ay >= 7 else f"{y - 1}-{y}"
        l = tff_kulup.get(tid, [])
        return next((k for k, a, b in l if a <= sezon <= b), l[0][0] if len(l) == 1 else None)
    aday = collections.defaultdict(list)
    for kaynak, kid_, tarih, ev, dep in c.execute("SELECT kaynak, kaynak_id, tarih, ev_kulup, dep_kulup FROM mac WHERE yarisma IN ('kupa', 'ozel_kupa')"):
        aday[tarih].append((f"{kaynak}:{kid_}", ev, dep))
    es = {}
    for mac, org, tarih, et, dt in o.execute("SELECT mac, organizasyon, tarih, ev_tff, dep_tff FROM mac_bilgi WHERE organizasyon LIKE '%Kupa%'"):
        if "Türkiye Kupası" not in (org or "") and "Kupası (Profesyonel" not in (org or "") and "Süper Kupa" not in (org or ""):
            continue
        if not tarih:
            continue
        e, d = kulup(et, tarih), kulup(dt, tarih)
        for anahtar, ev, dep in aday.get(tarih, []):
            if (ev, dep) == (e, d):
                es[anahtar] = [int(mac), 0]
            elif (ev, dep) == (d, e):
                es[anahtar] = [int(mac), 1]   # taraflar ters
    return es


def aktar(c, maclar, okunur, cikti):
    tff = os.path.join(cikti, "tff")
    varyol = os.path.join(tff, "var.json")
    yerel = os.path.exists(OYUNCU_DB)
    if yerel:
        o = sqlite3.connect(OYUNCU_DB)
        bal = os.path.join(KOK, "raw", "bal_detay.db")   # Profesyonelliğe Geçiş Ligi maç ayrıntıları (bal.py ayikla)
        if os.path.basename(OYUNCU_DB) == "oyuncu.db" and os.path.exists(bal) and os.path.getsize(bal):
            # geçici görünümler aynı adlı ana tabloların önüne geçer: sorgular iki veritabanını birlikte okur
            o.execute("ATTACH ? AS bal", (bal,))
            for t in ("mac_bilgi", "gol", "kart", "degisiklik", "teknik", "hakem"):
                o.execute(f"CREATE TEMP VIEW {t} AS SELECT * FROM main.{t} UNION ALL SELECT * FROM bal.{t}")
            # kadro sırası önemli (rowid): görünümde rowid yok, sıra sütunu taşınır
            o.execute("CREATE TEMP VIEW kadro AS SELECT rowid AS sira_, * FROM main.kadro "
                      "UNION ALL SELECT rowid + 10000000000, * FROM bal.kadro")
        kupa = kupa_eslestir(o, c)
        yaz(KUPA_ES, kupa)
    else:
        if not os.path.exists(varyol):
            return []
        kupa = json.load(open(KUPA_ES, encoding="utf-8")) if os.path.exists(KUPA_ES) else {}
    # futbol.db maçı -> (TFF maç no, taraflar ters mi)
    bag = {}
    mk_sira = {k: MK_MAC + i for i, k in enumerate(sorted(
        m["kaynak_id"] for m in maclar if m["kaynak"] == "mackolik" and m["kaynak_id"] and m["yarisma"] == "lig" and m["kademe"] == 1))}
    for m in maclar:
        if m["yarisma"] == "avrupa" or m["ev_gol"] is None:
            continue
        if m["kaynak"] == "tff" and m["kaynak_id"]:
            bag[m["id"]] = (int(m["kaynak_id"]), 0)
        elif m["kaynak"] == "mackolik" and m["kaynak_id"] and m["yarisma"] == "lig" and m["kademe"] == 1:
            # 1984-85 öncesi Süper Lig: maç TFF'de yok, Maçkolik'ten; ayrıntısı (arşiv kadrosu) sabit bir numarayla yazılır
            bag[m["id"]] = (mk_sira[m["kaynak_id"]], 0)
        elif f"{m['kaynak']}:{m['kaynak_id']}" in kupa:
            bag[m["id"]] = tuple(kupa[f"{m['kaynak']}:{m['kaynak_id']}"])
    # 1990 öncesi Türkiye Kupası ve Süper Kupa (TFF'de yok): ayrıntısı Maçkolik arşiv kadrosu; sabit numara MK_KUPA + sıra
    eski_kupa = sorted((m["yarisma"], m["kaynak"], m["kaynak_id"], m["id"]) for m in maclar
                       if m["yarisma"] in ("kupa", "ozel_kupa") and m["id"] not in bag and m["kaynak_id"] and m["ev_gol"] is not None
                       and m["tarih"] and m["tarih"] < "1990-07-01")
    for i, (_, _, _, f) in enumerate(eski_kupa):
        bag[f] = (MK_KUPA + i, 0)
    if yerel:
        mevcut = maclari_yaz(o, c, maclar, bag, okunur, tff)
        yaz(varyol, {"maclar": artis(sorted(mevcut))})
    mevcut = set(geri(json.load(open(varyol, encoding="utf-8"))["maclar"]))
    bag = {f: t for f, t in bag.items() if t[0] in mevcut}
    fl = sorted(bag)
    yaz(os.path.join(tff, "dizin.json"), {"f": artis(fl), "t": artis([bag[f][0] for f in fl]), "ters": [f for f in fl if bag[f][1]]})
    return fl


TR_HARF = set("ÇĞİÖŞÜ")


def kisi_okunur_kur(o, okunur):
    """Kişi adları: TFF büyük harfle yazıyor; Türkçe adlarda I = ı, yabancı adlarda I = i ('MARIO JARDEL' -> Mario Jardel).
    Adında Türkçe harf olan kişilerin kelimeleri Türkçe sayılır ('UĞUR YILMAZ' -> YILMAZ Türkçe); başka adlardaki
    bu kelimeler de Türkçe kuralla, geri kalan kelimeler yabancı kuralla yazılır."""
    say_tr, say_ya = collections.Counter(), collections.Counter()   # kelime: Türkçe harfli adlarda / öbürlerinde kaç kez
    for (a,) in o.execute("SELECT DISTINCT ad FROM kadro UNION SELECT DISTINCT ad FROM teknik UNION SELECT DISTINCT ad FROM hakem"):
        if a:
            (say_tr if TR_HARF & set(a) else say_ya).update(w for w in a.split() if "I" in w)
    tr = {w for w in say_tr if say_tr[w] >= say_ya[w]}
    def f(a):
        a = on_temiz(a)
        if not a or any(ch.islower() for ch in a):
            return a
        if TR_HARF & set(a):
            s = okunur(a)
        else:
            s = " ".join(okunur(w) if w in tr else okunur(w.replace("I", "İ")) for w in a.split())
        # bağlaçlar (DE, DA, DOS…) ilk kelime değilse küçük: "Roberto Carlos da Silva Rocha"
        # okunur kısa kelimeleri büyük bırakıyor ("EL", "DE"): baştaki büyük harf kalır, gerisi küçülür
        w = [x[0] + x[1:].replace("I", "ı").replace("İ", "i").lower() if len(x) > 1 and x.isupper() and x.isalpha() else x for x in s.split()]
        return " ".join([w[0]] + [x.lower() if x.upper().replace("İ", "I") in BAGLAC else x for x in w[1:]]) if w else s
    return f


BAGLAC = {"DE", "DA", "DO", "DOS", "DAS", "DI", "DU", "DEL", "VAN", "VON", "DER"}   # ad içinde küçük yazılan bağlaçlar
EDAT = {"DE", "DA", "DO", "DOS", "DAS", "DI", "DU", "DEL", "VAN", "VON", "DER", "DEN", "LA", "LE", "EL"}


def on_temiz(a):
    """TFF'nin ad yazımındaki bozukluklar: virgülle ayrılmış adlar ("RAYAN,NY,ALNA"), noktadan sonra boşluksuz kısaltmalar
    ("M.ALİ"), büyük harfli adda tek tük küçük harf ("ARiF")."""
    import re
    if not a:
        return a
    a = re.sub(r"\s+", " ", re.sub(r"\.(?=[^\s.])", ". ", a.replace(",", " "))).strip()
    harf = [ch for ch in a if ch.isalpha()]
    kucuk = sum(ch.islower() for ch in harf)
    if harf and 0 < kucuk <= len(harf) * 0.2:
        a = a.replace("i", "İ").upper()
    return a


def yabanci_mi(a, tc_kelime):
    """Kişi sayfası olmayan oyuncu: adının kelimelerinin çoğu Türk oyuncuların adlarında hiç geçmiyorsa ve Ğ/Ş yoksa yabancı."""
    w = [x for x in on_temiz(a).upper().replace(".", " ").split() if len(x) > 1 and x not in BAGLAC]
    if not w or any(set(x) & set("ĞŞ") for x in w):
        return False
    def tc(x):   # Türk adlarında geçen kelime ya da bileşik soyadı (KIRIK+KAYA)
        x = x.replace("İ", "I")
        return x in tc_kelime or any((x[i:] in tc_kelime and len(x) - i >= 4) or (x[:i] in tc_kelime and i >= 4) for i in range(2, len(x) - 1))
    return sum(tc(x) for x in w) < len(w) / 2


def yabanci_okunur(a, okunur):
    """Yabancı oyuncunun TFF'deki büyük harfli adı: Türkçe harfli (Ğ Ş Ö Ü) kelimeler Türkçe kuralla, gerisinde I = i."""
    a = on_temiz(a)
    w = [okunur(x) if set(x) & set("ĞŞÖÜ") else okunur(x.replace("I", "İ")).replace("İ", "I") for x in a.split()]
    w = [x[0] + x[1:].replace("I", "ı").replace("İ", "i").lower() if len(x) > 1 and x.isupper() and x.isalpha() else x for x in w]
    return " ".join([w[0]] + [x.lower() if x.upper().replace("İ", "I") in BAGLAC else x for x in w[1:]]) if w else a


BIRLES = {}   # ikinci TFF numarası -> asıl numara (maclari_yaz doldurur)


def kisi_birlestir(kadro, tersi, m_, ad, okunur):
    """TFF bazen aynı oyuncuya iki kişi numarası veriyor (Erkan Sözeri: 21807 ve 547117). Aynı ad (aksansız), aynı sezon
    aynı kulüpte oynamış ve hiçbir maçta birlikte kadroda olmayan numaralar tek kişi sayılır; asıl numara çok maçlı olan.
    Dönen: {ikinci no: asıl no}."""
    from oyuncu_bag import sade
    S = lambda x: " ".join(sade(okunur(ad.get(x, ""))))
    grup = collections.defaultdict(set)   # (ad, sezon, kulüp) -> kişiler
    birlikte = set()
    mac_say = collections.Counter()
    for t_, k_ in kadro.items():
        f_ = tersi.get(t_)
        if not f_:
            continue
        m = m_[f_[0]]
        for i, taraf in enumerate(k_):
            kid = m["ev_kulup"] if (i == 0) != bool(f_[1]) else m["dep_kulup"]
            adlar = collections.defaultdict(list)
            for p in taraf:
                if p[1]:
                    mac_say[p[1]] += 1
                    adlar[S(p[1])].append(p[1])
            for a_, l in adlar.items():
                grup[(a_, m["sezon"], kid)].update(l)
                for x in l:
                    for y in l:
                        if x != y:
                            birlikte.add((x, y))
    ust = {}
    def bul(x):
        while ust.get(x, x) != x:
            x = ust[x]
        return x
    for (a_, _, _), l in grup.items():
        if not a_ or len(l) < 2:
            continue
        l = sorted(l, key=lambda x: -mac_say[x])
        for x in l[1:]:
            if (l[0], x) in birlikte:
                continue
            ra, rx = bul(l[0]), bul(x)
            if ra != rx:
                if mac_say[rx] > mac_say[ra]:
                    ra, rx = rx, ra
                ust[rx] = ra
    # aynı ad + aynı tam doğum tarihi (kişi sayfası; 1 Ocak / 1 Temmuz yalnız yıl demek) ve hiç birlikte kadroda olmayan:
    # kulüp ya da sezon tutmasa da aynı kişi (ör. bir numarası alt ligde, öbürü Süper Lig'de)
    kisi_db = os.path.join(KOK, "raw", "kisi.db")
    dg = collections.defaultdict(list)
    if os.path.exists(kisi_db):
        for x, d_ in sqlite3.connect(kisi_db).execute("SELECT kisi, dogum FROM kisi WHERE dogum IS NOT NULL"):
            if x in mac_say and d_[5:] not in ("01-01", "07-01") and S(x):
                dg[(S(x), d_)].append(x)
    n_dg = 0
    for l in dg.values():
        l = sorted(l, key=lambda x: -mac_say[x])
        for x in l[1:]:
            if (l[0], x) in birlikte:
                continue
            ra, rx = bul(l[0]), bul(x)
            if ra != rx:
                if mac_say[rx] > mac_say[ra]:
                    ra, rx = rx, ra
                ust[rx] = ra
                n_dg += 1
    print(f"aynı oyuncunun ikinci TFF numarası: {sum(1 for x in ust if bul(x) != x)} (doğum tarihiyle eklenen {n_dg})")
    return {x: bul(x) for x in ust if bul(x) != x}


def istatistik_yaz(O, ad, okunur, tff, n=100, eski=None, yas=None, yas_kapsam=0):
    """Oyuncu istatistikleri sayfası (#/oyuncular) -> tff/istatistik.json:
    liste[yarışma][gol|mac]: ilk n oyuncu [kisi, ad, mac, gol, ilk sezon, son sezon, son kulüp(, 1: oyuncu sayfası yok)];
      "tum" 1959 öncesi arşiv kadrolarını (eski: kisi -> [maç, gol, ilk, son, son kulüp]) da sayar, "tum59" saymaz;
    yas[kapsam]: genc, yasli, genc_gol, yasli_gol -> [kisi, ad, gün, tarih, maç, kulüp, rakip] (kapsam: tum, k1..k5, kupa);
    krallar[sezon][kademe]: lig golü en çok olan ilk 3 [kisi, ad, gol, mac, kulüp]; kart[sari|kirmizi]: ilk 50."""
    KAPSAM = {"tum59": lambda y, k: True, "sl": lambda y, k: y == "L" and k == 1, "lig": lambda y, k: y in ("L", "T"),
              "kupa": lambda y, k: y == "K"}
    liste = {}
    for kp, f in KAPSAM.items():
        sat = []
        for kisi, d in O.items():
            if not kisi:
                continue
            rs = [(a, v) for a, v in d.items() if v[0] and f(a[2], a[3])]
            if not rs:
                continue
            mac, gol = sum(v[0] for _, v in rs), sum(v[2] for _, v in rs)
            son = max(rs, key=lambda x: (x[0][0], x[1][0]))[0]
            sat.append([kisi, okunur(ad.get(kisi, "")), mac, gol, min(a[0] for a, _ in rs), son[0], son[1]])
        liste[kp] = {"gol": sorted([x for x in sat if x[3]], key=lambda x: (-x[3], x[2]))[:n], "mac": sorted(sat, key=lambda x: (-x[2], -x[3]))[:n]}
        if kp == "tum59":
            tum = {x[0]: list(x) for x in sat}
            for kisi, (mac, gol, ilk, son, kul) in (eski or {}).items():
                if kisi in tum:
                    x = tum[kisi]
                    x[2] += mac; x[3] += gol; x[4] = min(x[4], ilk)
                else:
                    tum[kisi] = [kisi, okunur(ad.get(kisi, "")), mac, gol, ilk, son, kul, 1]
            sat_ = list(tum.values())
            liste["tum"] = {"gol": sorted([x for x in sat_ if x[3]], key=lambda x: (-x[3], x[2]))[:n], "mac": sorted(sat_, key=lambda x: (-x[2], -x[3]))[:n]}
    kral = collections.defaultdict(lambda: collections.defaultdict(list))
    for kisi, d in O.items():
        if not kisi:
            continue
        top = collections.defaultdict(lambda: [0, 0, None, 0])   # (sezon, kademe) -> gol, mac, en çok oynadığı kulüp, o kulüpteki maç
        for (sz, kid, y, kd), v in d.items():
            if y == "L" and v[0]:
                r = top[(sz, kd)]
                r[0] += v[2]; r[1] += v[0]
                if v[0] > r[3]: r[2], r[3] = kid, v[0]
        for (sz, kd), r in top.items():
            if r[0]:
                kral[sz][kd].append([kisi, okunur(ad.get(kisi, "")), r[0], r[1], r[2]])
    krallar = {sz: {str(kd): sorted(l, key=lambda x: (-x[2], x[3]))[:3] for kd, l in v.items()} for sz, v in kral.items()}
    kart = {}
    for i, k in ((5, "sari"), (6, "kirmizi")):
        sat = [[kisi, okunur(ad.get(kisi, "")), sum(v[0] for v in d.values()), sum(v[i] for v in d.values())] for kisi, d in O.items() if kisi]
        kart[k] = sorted([x for x in sat if x[3]], key=lambda x: (-x[3], x[2]))[:50]
    yaz(os.path.join(tff, "istatistik.json"), {"alanlar": ["kisi", "ad", "mac", "gol", "ilk", "son", "son_kulup"], "liste": liste,
        "kral_alanlar": ["kisi", "ad", "gol", "mac", "kulup"], "krallar": krallar, "kart_alanlar": ["kisi", "ad", "mac", "sayi"], "kart": kart,
        "yas_alanlar": ["kisi", "ad", "gun", "tarih", "mac", "kulup", "rakip"], "yas": yas or {}, "yas_kapsam": yas_kapsam})


HAREKET_TUR = ["Amatör Transfer", "Filiz Lisans", "Yurt İçi Transfer", "Karşılıklı Sona Erdirme", "Profesyonelliğe Geçiş",
               "Sözleşme Yenileme", "Amatöre Dönüş", "Geçici Transfer", "Uzatma", "Yurt Dışı Transfer", "Tedbir Kaldırma", "Fesih"]
HAREKET_ATLA = {"Amatör Vize", "Vize"}   # her sezon yenilenen vizeler: kulüp değişmez, sayfayı şişirir


def hareketler(c, kisi_db, okunur_kulup):
    """TFF lisans hareketleri (kisi.db hareket; tff_kisi_ek.py ayikla) -> {kisi: [[veriliş, kulüp, tür, sözleşme baş., bitiş, yurt dışı]]}.
    kulüp: futbol.db kulüp no (TFF kulüp numarasından, o tarihteki sezona göre) ya da bağlanamayan kulübün adı (çoğu amatör kulüp);
    tür: HAREKET_TUR sırası ya da listede yoksa adı. Vizeler alınmaz. Sondaki boş alanlar kırpılır."""
    if not os.path.exists(kisi_db) or not sqlite3.connect(kisi_db).execute("SELECT 1 FROM sqlite_master WHERE name='hareket'").fetchone():
        return {}
    tk = collections.defaultdict(list)
    for kid, no, s1, s2 in c.execute("SELECT kulup_id, kaynak_id, ilk_sezon, son_sezon FROM kulup_kimlik WHERE kaynak='tff'"):
        tk[int(str(no).split("-")[0])].append((s1 or "", s2 or "9999", kid))   # "2434-once": aynı TFF no, önceki kulüp
    def kulup(no, tarih):
        l = tk.get(no)
        if not l:
            return None
        if len(l) > 1 and tarih:
            y, a = int(tarih[:4]), int(tarih[5:7])
            sz = f"{y}-{y + 1}" if a >= 7 else f"{y - 1}-{y}"
            for s1, s2, kid in l:
                if s1 <= sz <= s2:
                    return kid
        return max(l)[2]
    tur = {t: i for i, t in enumerate(HAREKET_TUR)}
    out = collections.defaultdict(list)
    for kisi, no, kad, bas, bit, t, ver, yd in sqlite3.connect(kisi_db).execute(
            "SELECT kisi, kulup_tff, kulup_ad, bas, bit, tur, verilis, yurtdisi FROM hareket ORDER BY kisi, COALESCE(verilis, bas), sira"):
        if t in HAREKET_ATLA:
            continue
        r = [ver or "", kulup(no, ver or bas) or okunur_kulup(kad or ""), tur.get(t, t), bas or "", bit or "", yd or ""]
        while r and r[-1] == "":
            r.pop()
        out[kisi].append(r)
    return out


def maclari_yaz(o, c, maclar, bag, okunur_kulup, tff):
    okunur = kisi_okunur_kur(o, okunur_kulup)
    m_ = {m["id"]: m for m in maclar}
    tersi = {t: (f, ters) for f, (t, ters) in bag.items()}   # TFF no -> futbol no
    kadro = collections.defaultdict(lambda: ([], []))
    ad = {}
    # kaleci: TFF ilk 11'i kaleciyle başlatıyor; bir oyuncunun ilk sırada yazıldığı maçların oranı kalecileri ayırır (~1 / ~0)
    ilk_sira, ilk_say, bas_say = {}, collections.Counter(), collections.Counter()
    for mac, taraf, kisi, a, forma, ilk11 in o.execute("SELECT mac, taraf, kisi, ad, forma, ilk11 FROM kadro ORDER BY "
                                                         + ("sira_" if "bal" in [r[1] for r in o.execute("PRAGMA database_list")] else "rowid")):
        mac = int(mac)
        if ilk11 and kisi:
            bas_say[kisi] += 1
            if (mac, taraf) not in ilk_sira:
                ilk_sira[(mac, taraf)] = kisi
                ilk_say[kisi] += 1
        if mac not in tersi:
            continue
        kadro[mac][taraf - 1].append([forma, kisi, ilk11])
        ad.setdefault(kisi, a)
    olay = collections.defaultdict(list)
    for mac, taraf, kisi, a, dk, d1, d2, tip in o.execute("SELECT mac, taraf, kisi, ad, dakika, dk, ek, tip FROM gol"):
        if int(mac) in tersi and not seri_mi(tip, d1, d2):
            olay[int(mac)].append([taraf, "G", d1, d2 or 0, kisi, None, tip])
            ad.setdefault(kisi, a)
    for mac, taraf, kisi, a, renk, dk, d1, d2 in o.execute("SELECT mac, taraf, kisi, ad, renk, dakika, dk, ek FROM kart"):
        if int(mac) in tersi:
            olay[int(mac)].append([taraf, KART.get(renk, "Y"), d1, d2 or 0, kisi, None, None])
            ad.setdefault(kisi, a)
    for mac, taraf, giren, gad, cikan, cad, dk, d1, d2 in o.execute("SELECT * FROM degisiklik"):
        if int(mac) in tersi:
            olay[int(mac)].append([taraf, "S", d1, d2 or 0, cikan, giren, None])
            ad.setdefault(giren, gad); ad.setdefault(cikan, cad)
    # bilinen adlar (Brezilyalı oyuncular, oyuncu_bag.py -> bilinen_ad.json): sitede bu ad, oyuncu sayfasında tam ad da
    # ve yabancı oyuncular (Vikipedi/Wikidata, wikidata_ad.py -> bilinen_ad_wiki.json; öncelikli)
    tam_ad = {}
    if os.path.basename(OYUNCU_DB) == "oyuncu.db":
        # yabancı oyuncuların TFF'deki büyük harfli adı: Türkçe kural yok (TFF "ROGERIO CONCEIÇAO" -> "Rogerıo" olmasın)
        kdb = os.path.join(KOK, "raw", "kisi.db")
        uy = dict(sqlite3.connect(kdb).execute("SELECT kisi, uyruk FROM kisi")) if os.path.exists(kdb) else {}
        yab = {k_ for k_, u_ in uy.items() if u_ and u_ != "TC"}
        # (yabanci_mi tahmini kullanılmıyor: kişi sayfası inince uyruk oradan gelir)
        for k_ in yab:
            if k_ in ad and ad[k_] and not any(ch.islower() for ch in ad[k_]):
                ad[k_] = yabanci_okunur(ad[k_], okunur)
        bilinen = {}
        for dosya in ("bilinen_ad.json", "bilinen_ad_wiki.json"):
            if os.path.exists(os.path.join(KOK, dosya)):
                bilinen.update(json.load(open(os.path.join(KOK, dosya), encoding="utf-8")))
        for k_, a_ in bilinen.items():
            if int(k_) in ad and ad[int(k_)]:
                tam_ad[int(k_)] = okunur(ad[int(k_)])
                ad[int(k_)] = a_
    # 1959-1991 Süper Lig: Maçkolik arşiv kadroları ve olayları (mackolik_oyuncu.py)
    import mackolik_oyuncu as MO
    erkek = os.path.basename(OYUNCU_DB) == "oyuncu.db"   # kadın verisi (kadin_site.py) aynı kodla geçer: arşiv yalnız erkek
    ar, ar_say = MO.yukle(maclar, bag, c) if erkek else ({}, {})
    dog_es = {}   # eşleştirmede yaş kontrolü için doğum tarihleri (yalnız yıl bilinenler dahil)
    if erkek and os.path.exists(os.path.join(KOK, "raw", "kisi.db")):
        for k_, d_ in sqlite3.connect(os.path.join(KOK, "raw", "kisi.db")).execute("SELECT kisi, dogum FROM kisi WHERE dogum IS NOT NULL"):
            try:
                dog_es[k_] = datetime.date.fromisoformat(DOGUM_DUZELT.get(k_, d_))
            except ValueError:
                pass
    es_mk = MO.kisi_esle(ar, kadro, ad, {t_: m_[f_]["sezon"] for t_, (f_, _) in tersi.items()},
                         lambda t_, i: m_[tersi[t_][0]]["ev_kulup" if (i == 0) != bool(tersi[t_][1]) else "dep_kulup"],
                         lambda t_: m_[tersi[t_][0]]["tarih"] if t_ in tersi else None, dog_es) if erkek else {}
    mk_kadro, mk_olay = MO.kat(ar, es_mk, kadro, olay, ad, ilk_sira, ilk_say, bas_say)
    # 1959 öncesi arşiv kadroları: yalnız oyuncular sayfasının "Bütün maçlar" listelerine (maç ve oyuncu sayfalarına girmez)
    eski, eski_ad = MO.eski_kariyer(es_mk, c) if erkek else ({}, {})
    for k_, a_ in eski_ad.items():
        ad.setdefault(k_, a_)
    global MK_ILK
    if erkek:
        MK_ILK = min((m["sezon"] for m in maclar if m["id"] in bag and bag[m["id"]][0] in mk_kadro), default=None)
    if erkek:
        print(f"Maçkolik arşiv kadroları ({MK_ILK}'den): {dict(ar_say)}; kadro {len(mk_kadro)} maç, yalnız olay {len(mk_olay)} maç")
    # TFF'nin aynı kişiye verdiği ikinci numaralar: aynı ad, aynı sezon aynı kulüpte oynamış, hiçbir maçta birlikte değil
    global BIRLES
    BIRLES = kisi_birlestir(kadro, tersi, m_, ad, okunur) if erkek else {}
    if BIRLES:
        b_ = lambda k_: BIRLES.get(k_, k_)
        for t_, k_ in list(kadro.items()):
            kadro[t_] = tuple([[p[0], b_(p[1]), p[2]] for p in taraf] for taraf in k_)
        for t_, l in olay.items():
            for x in l:
                x[4] = b_(x[4]); x[5] = b_(x[5]) if x[5] else x[5]
        for k_ in list(ilk_sira):
            ilk_sira[k_] = b_(ilk_sira[k_])
        for es, ana in BIRLES.items():
            ilk_say[ana] += ilk_say.pop(es, 0); bas_say[ana] += bas_say.pop(es, 0)
        print(f"TFF'de iki numaralı oyuncular birleşti: {len(BIRLES)}")
        for es, ana in BIRLES.items():
            if es in eski:
                r_ = eski.pop(es)
                if ana in eski:
                    e_ = eski[ana]
                    eski[ana] = [e_[0] + r_[0], e_[1] + r_[1], min(e_[2], r_[2]), *max((e_[3], e_[4]), (r_[3], r_[4]), key=lambda x: x[0])]
                else:
                    eski[ana] = r_
    teknik = collections.defaultdict(lambda: ([], []))
    import mackolik_td   # TFF'de boş kalan teknik direktörler: Maçkolik arşivi takım fikstürleri (raw/mackolik_td/ek.json)
    for mac, taraf, kisi, a in list(o.execute("SELECT mac, taraf, kisi, ad FROM teknik")) + (mackolik_td.ek_satirlar(o) if erkek else []):
        if int(mac) in tersi:
            teknik[int(mac)][taraf - 1].append([kisi, okunur(a)])
    hakem = collections.defaultdict(list)
    for mac, kisi, a, gorev in o.execute("SELECT mac, kisi, ad, gorev FROM hakem"):
        if int(mac) in tersi:
            hakem[int(mac)].append([okunur(a), (gorev or "").split("(")[-1]])
    bilgi = {int(m): (s, u) for m, s, u in o.execute("SELECT mac, stad, gol_uyum FROM mac_bilgi")}

    # ---- maç dosyaları
    kova = collections.defaultdict(dict)
    mevcut = []
    for t, (f, ters) in tersi.items():
        if t not in kadro and t not in olay:
            continue
        k, ol, tk = kadro[t], sorted(olay[t], key=lambda x: (x[2] is None, x[2] or 0, x[3])), teknik[t]
        if ters:
            k, tk = (k[1], k[0]), (tk[1], tk[0])
            ol = [[3 - x[0], *x[1:]] for x in ol]
        for taraf in k:
            taraf.sort(key=lambda p: (-p[2], int(p[0]) if (p[0] or "").isdigit() else 99))
        stad, uyum = bilgi.get(t, (None, None))
        m = m_[f]
        kayit = {"m": [m["tarih"], m["saat"], m["sezon"], m["lig"], m["tur"] or m["grup"] or "", [m["ev_kulup"], okunur_kulup(m["ev_adi"])],
                       [m["dep_kulup"], okunur_kulup(m["dep_adi"])], [m["ev_gol"], m["dep_gol"], m["ev_pen"], m["dep_pen"], m["durum"]]],
                 "k": [k[0], k[1]], "o": ol, "t": [tk[0], tk[1]], "h": hakem[t]}
        if stad:
            kayit["s"] = okunur_kulup(stad)
        if uyum in ("uyumsuz", "yok") and t not in mk_olay and t not in mk_kadro:
            kayit["u"] = uyum
        if t in mk_kadro:
            kayit["q"] = "Maçkolik"
        elif t in mk_olay:
            kayit["oq"] = "Maçkolik"
        kova[t // 250][t] = kayit
        mevcut.append(t)
    mdir = os.path.join(tff, "m")
    if os.path.isdir(mdir):
        shutil.rmtree(mdir)
    for b, d in kova.items():
        kisiler = {p[1] for r in d.values() for taraf in r["k"] for p in taraf} | {x[4] for r in d.values() for x in r["o"]} | \
                  {x[5] for r in d.values() for x in r["o"] if x[5]}
        yaz(os.path.join(mdir, f"{b}.json"), {"ad": {k_: okunur(ad.get(k_, "")) for k_ in kisiler if k_}, "mac": d})

    # ---- oyuncu kariyerleri: sezon x kulüp x yarışma
    O = collections.defaultdict(lambda: collections.defaultdict(lambda: [0] * 12))   # kisi -> anahtar -> [mac, ilk11, gol, pen, kk, sari, kirmizi, dakika, yedek, kaleci maç, gol yemeden, yenen gol]
    kul_oy = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, None, None]))   # kulüp -> kisi -> [mac, gol, ilk, son]
    kul_lig = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, None, None]))  # yalnız lig (play-off dahil)
    kul_sezon = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0]))   # kulüp -> (kisi, sezon) -> [gol, lig golü, gol yemeden (kaleci), maç, sarı, kırmızı]
    kul_kart = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, None, None]))   # kulüp -> kisi -> [sarı, kırmızı, maç, ilk, son]
    mac_gol = collections.defaultdict(list)   # kulüp -> [kisi, gol, futbol maç no, lig mi]
    genel_gol = []
    # geri dönüşler: gol dakikalarıyla maçın akışı. kulüp -> [futbol maç no, en büyük fark, o anki skor (biz, onlar), dakika]
    donus, kacan = collections.defaultdict(list), collections.defaultdict(list)
    kaleci = lambda k_: bas_say[k_] >= 3 and ilk_say[k_] / bas_say[k_] >= 0.6
    # yaş rekorları: yalnız tam doğum tarihi (1 Ocak / 1 Temmuz yalnız yıl bilindiğini gösterir; oyuncu.py kisi_ayikla)
    kisi_db = os.path.join(KOK, "raw", "kisi.db")
    dog = {}
    if os.path.exists(kisi_db):
        for k_, d_ in sqlite3.connect(kisi_db).execute("SELECT kisi, dogum FROM kisi WHERE dogum IS NOT NULL"):
            d_ = DOGUM_DUZELT.get(k_, d_)
            if d_[5:] not in ("01-01", "07-01"):
                dog[k_] = datetime.date.fromisoformat(d_)
    for es, ana in BIRLES.items():
        if ana not in dog and es in dog:
            dog[ana] = dog[es]
    yas_oy = collections.defaultdict(dict)    # kulüp -> kisi -> [en genç: gün, maç] + [en yaşlı: gün, maç]
    yas_gol = collections.defaultdict(dict)
    # genel yaş rekorları (oyuncular sayfası): kapsam (tum, k1..k5 lig kademesi, kupa) -> kisi -> [gün, maç, kulüp] x 2
    yas_g_oy = collections.defaultdict(dict)
    yas_g_gol = collections.defaultdict(dict)
    ilk_tarih = {}   # kişi -> TFF'deki ilk maçı
    def yas_ekle(tablo, kid, kisi, f_, tarih):
        if kisi not in dog or not tarih:
            return
        if kisi not in ilk_tarih or tarih < ilk_tarih[kisi]:
            ilk_tarih[kisi] = tarih
        g = (datetime.date.fromisoformat(tarih) - dog[kisi]).days
        if g < 12 * 365 or g > 50 * 365:   # doğum tarihi hatalı (12 yaşında ligde oynamış oyuncular var)
            return
        r_ = tablo[kid].get(kisi)
        if not r_:
            tablo[kid][kisi] = [g, f_, g, f_]
        else:
            if g < r_[0]: r_[0], r_[1] = g, f_
            if g > r_[2]: r_[2], r_[3] = g, f_
    def yas_genel(tablo, m, kid, kisi, f_):
        if kisi not in dog or not m["tarih"]:
            return
        g = (datetime.date.fromisoformat(m["tarih"]) - dog[kisi]).days
        if g < 12 * 365 or g > 50 * 365:
            return
        kap = ["tum"] + ([f"k{m['kademe']}"] if m["yarisma"] == "lig" and m["kademe"] else []) + (["kupa"] if m["yarisma"] == "kupa" else [])
        for kp in kap:
            r_ = tablo[kp].get(kisi)
            if not r_:
                tablo[kp][kisi] = [g, f_, kid, g, f_, kid]
            else:
                if g < r_[0]: r_[0:3] = [g, f_, kid]
                if g > r_[3]: r_[3:6] = [g, f_, kid]
    for t in mevcut:
        f, ters = tersi[t]
        m = m_[f]
        k = kadro[t]
        if ters:
            k = (k[1], k[0])
        ol = [[3 - x[0], *x[1:]] for x in olay[t]] if ters else olay[t]
        giris = {x[5]: x[2] for x in ol if x[1] == "S" and x[5]}
        cikis = {x[4]: x[2] for x in ol if x[1] == "S" and x[4]}
        for x in ol:
            if x[1] in ("R", "YR"):
                cikis.setdefault(x[4], x[2])
        lig = m["yarisma"] == "lig"
        hukmen = m["durum"] in ("Hük.", "Çifte H")
        # maçın akışı: yalnız bütün gollerin dakikası belli ve gol listesi skorla birebir tutuyorsa
        gl = [x for x in ol if x[1] == "G"]
        if gl and not hukmen and m["ev_gol"] is not None and all(x[2] is not None for x in gl):
            sk, en_ = [0, 0], [[0, None, None], [0, None, None]]   # taraf -> [en büyük geride kalış, skor, dakika]
            for x in sorted(gl, key=lambda x: (x[2], x[3] or 0)):
                sk[(2 - x[0]) if x[6] == "K" else (x[0] - 1)] += 1
                for i_ in (0, 1):
                    geri_ = sk[1 - i_] - sk[i_]
                    if geri_ > en_[i_][0]:
                        en_[i_] = [geri_, sk[i_], sk[1 - i_], f"{x[2]}+{x[3]}" if x[3] else str(x[2])]
            if sk == [m["ev_gol"], m["dep_gol"]]:
                for i_, kid_ in ((0, m["ev_kulup"]), (1, m["dep_kulup"])):
                    if en_[i_][0] and sk[i_] > sk[1 - i_]:
                        donus[kid_].append([f, *en_[i_]])
                    if en_[1 - i_][0] and sk[i_] < sk[1 - i_]:   # rakip geriden gelip kazandı: biz öndeydik
                        g_ = en_[1 - i_]
                        kacan[kid_].append([f, g_[0], g_[2], g_[1], g_[3]])
        for i, taraf in enumerate(k):
            kid = m["ev_kulup"] if i == 0 else m["dep_kulup"]
            anahtar_ = (m["sezon"], kid, YAR[m["yarisma"]], m["kademe"] or 0)
            yedigi = m["dep_gol"] if i == 0 else m["ev_gol"]
            # gol yemeden: ilk 11'deki kaleci (ilk sıradaki, kaleci değilse kadrodaki kaleci), hükmen maçlar hariç
            ilk_ = ilk_sira.get((t, (2 - i) if ters else (i + 1)))
            gk = ilk_ if ilk_ and kaleci(ilk_) else next((p[1] for p in taraf if p[2] and kaleci(p[1])), None)
            if gk and not hukmen and yedigi is not None:
                if yedigi == 0:
                    kul_sezon[kid][(gk, m["sezon"])][2] += 1
                rg = O[gk][anahtar_]
                rg[9] += 1; rg[10] += yedigi == 0; rg[11] += yedigi
            for forma, kisi, ilk11 in taraf:
                oyn = ilk11 or kisi in giris
                r = O[kisi][anahtar_]
                if not oyn:
                    r[8] += 1
                    continue
                kul_sezon[kid][(kisi, m["sezon"])][3] += 1
                yas_ekle(yas_oy, kid, kisi, f, m["tarih"])
                yas_genel(yas_g_oy, m, kid, kisi, f)
                kk_ = kul_kart[kid][kisi]
                kk_[2] += 1
                kk_[3] = min(kk_[3] or m["sezon"], m["sezon"]); kk_[4] = max(kk_[4] or m["sezon"], m["sezon"])
                if lig:
                    kl = kul_lig[kid][kisi]
                    kl[0] += 1
                    kl[2] = min(kl[2] or m["sezon"], m["sezon"]); kl[3] = max(kl[3] or m["sezon"], m["sezon"])
                bas = 0 if ilk11 else (giris.get(kisi) or 0)
                son = cikis.get(kisi) or 90
                r[0] += 1; r[1] += ilk11; r[7] += max(0, min(son, 90) - min(bas, 90)) if son is not None else 0
                kk = kul_oy[kid][kisi]
                kk[0] += 1
                kk[2] = min(kk[2] or m["sezon"], m["sezon"]); kk[3] = max(kk[3] or m["sezon"], m["sezon"])
        bu_mac = collections.Counter()
        for x in ol:
            taraf_ = x[0] - 1
            kid = m["ev_kulup"] if taraf_ == 0 else m["dep_kulup"]
            anahtar_ = (m["sezon"], kid, YAR[m["yarisma"]], m["kademe"] or 0)
            r = O[x[4]][anahtar_]
            if x[1] == "G":
                if x[6] == "K":
                    r[4] += 1
                else:
                    r[2] += 1; r[3] += x[6] == "P"
                    kul_oy[kid][x[4]][1] += 1
                    ks = kul_sezon[kid][(x[4], m["sezon"])]
                    ks[0] += 1
                    if lig:
                        ks[1] += 1
                        kul_lig[kid][x[4]][1] += 1
                    bu_mac[(kid, x[4])] += 1
                    yas_ekle(yas_gol, kid, x[4], f, m["tarih"])
                    yas_genel(yas_g_gol, m, kid, x[4], f)
            elif x[1] == "Y":
                r[5] += 1
                kul_sezon[kid][(x[4], m["sezon"])][4] += 1
                kul_kart[kid][x[4]][0] += 1
            elif x[1] in ("R", "YR"):
                r[6] += 1
                kul_sezon[kid][(x[4], m["sezon"])][5] += 1
                kul_kart[kid][x[4]][1] += 1
        for (kid, kisi), n in bu_mac.items():
            if n >= 2:
                mac_gol[kid].append([kisi, n, f, 1 if lig else 0])
                if n >= 3:   # genel rekorlar: bir maçta en çok gol (hat-trick ve üstü)
                    rakip = m["dep_kulup"] if m["ev_kulup"] == kid else m["ev_kulup"]
                    genel_gol.append([kisi, None, n, f, m["tarih"], m["sezon"], kid, rakip, YAR[m["yarisma"]], m["kademe"] or 0, m["asama"] == "play-off"])
    odir = os.path.join(tff, "o")
    if os.path.isdir(odir):
        shutil.rmtree(odir)
    okova = collections.defaultdict(dict)
    dizin = []
    kisi_db = os.path.join(KOK, "raw", "kisi.db")   # doğum tarihi/yeri, uyruk (oyuncu.py kisi_ayikla)
    kb = {k: [DOGUM_DUZELT.get(k, d), y, u] for k, d, y, u in sqlite3.connect(kisi_db).execute("SELECT kisi, dogum, yer, uyruk FROM kisi")} if os.path.exists(kisi_db) else {}
    es_l = collections.defaultdict(list)
    for es, ana in BIRLES.items():
        okova[es % 500][es] = {"bk": ana}   # eski bağlantılar asıl sayfaya
        es_l[ana].append(es)
        if ana not in kb and es in kb:
            kb[ana] = kb[es]
    hr = hareketler(c, kisi_db, okunur_kulup)
    for es, ana in BIRLES.items():
        if ana not in hr and es in hr:
            hr[ana] = hr[es]
    for kisi, sat in O.items():
        if not kisi:
            continue
        satir = sorted([[*a, *v] for a, v in sat.items() if v[0] or v[8]], key=lambda x: (x[0], x[2]))
        okova[kisi % 500][kisi] = {"ad": okunur(ad.get(kisi, "")), **({"tam": tam_ad[kisi]} if kisi in tam_ad and tam_ad[kisi] != ad[kisi] else {}), "s": satir, **({"d": kb[kisi]} if kisi in kb and any(kb[kisi]) else {}), **({"es": es_l[kisi]} if kisi in es_l else {}),
                               **({"h": hr[kisi]} if kisi in hr else {})}
        if not any(s[4] for s in satir):
            continue   # hiç oynamamış (yalnız yedek kulübesi): sayfası var (maç kadrolarından bağlantı), arama dizininde yok
        mac = sum(s[4] for s in satir)
        gol = sum(s[6] for s in satir)
        son = max(satir, key=lambda s: (s[0], s[4]))
        dizin.append([kisi, okunur(ad.get(kisi, "")), mac, gol, min(s[0] for s in satir if s[4]), max(s[0] for s in satir if s[4]), son[1]])
    for b, d in okova.items():
        yaz(os.path.join(odir, f"{b}.json"), {"alanlar": ["sezon", "kulup", "yarisma", "kademe", "mac", "ilk11", "gol", "penalti", "kendi_kalesine",
                                                         "sari", "kirmizi", "dakika", "yedek", "kaleci_mac", "gol_yemeden", "yenen_gol"], "oyuncu": d})
    yaz(os.path.join(tff, "oyuncular.json"), {"alanlar": ["kisi", "ad", "mac", "gol", "ilk", "son", "son_kulup"],
                                              "oyuncu": sorted(dizin, key=lambda x: -x[2])})
    kdir = os.path.join(tff, "kulup")
    if os.path.isdir(kdir):
        shutil.rmtree(kdir)
    def ilk_n(l, f, n=10):   # ilk n + sonuncuyla eşit olanlar
        l = sorted(l, key=f)
        if len(l) > n:
            son = f(l[n - 1])[0]
            l = [x for i, x in enumerate(l) if i < n or f(x)[0] == son]
        return l
    def supheli(k_):
        """TFF bilinmeyen doğum tarihlerini ilk maçtan 12 yıl geriye yazmış görünüyor (Metin Ülgen: doğum 16.12.1978, ilk maç
        16.12.1990). İlk maçı 12. doğum gününden önce ya da sonraki 10 gün içinde olanın doğum tarihine güvenilmez
        (Erkan Aygün: doğum 27.01.1980 yazılı, ama 1991'de oynamış)."""
        d_, t_ = dog.get(k_), ilk_tarih.get(k_)
        if not d_ or not t_:
            return False
        try:
            on_iki = d_.replace(year=d_.year + 12)
        except ValueError:   # 29 Şubat
            on_iki = d_.replace(year=d_.year + 12, day=28)
        return (datetime.date.fromisoformat(t_) - on_iki).days <= 10
    def yas_rekor(kid):
        A = lambda k_: okunur(ad.get(k_, ""))
        rakip = lambda f_: m_[f_]["dep_kulup"] if m_[f_]["ev_kulup"] == kid else m_[f_]["ev_kulup"]
        sat = lambda k_, g, f_: [k_, A(k_), g, m_[f_]["tarih"], f_, rakip(f_)]
        out = {"yas_alanlar": ["kisi", "ad", "gun", "tarih", "mac", "rakip"], "yas_kapsam": len(dog)}
        for ad_, t_ in (("", yas_oy), ("_gol", yas_gol)):
            v = {k_: r for k_, r in t_.get(kid, {}).items() if not supheli(k_)}
            out["genc" + ad_] = sorted((sat(k_, r[0], r[1]) for k_, r in v.items()), key=lambda x: x[2])[:10]
            out["yasli" + ad_] = sorted((sat(k_, r[2], r[3]) for k_, r in v.items()), key=lambda x: -x[2])[:10]
        return out
    # oyuncular sayfası: genel listeler ve yaş rekorları
    def yas_satir(k_, g, f_, kid):
        m = m_[f_]
        return [k_, okunur(ad.get(k_, "")), g, m["tarih"], f_, kid, m["dep_kulup"] if m["ev_kulup"] == kid else m["ev_kulup"]]
    yas = {}
    for kp in sorted(set(yas_g_oy) | set(yas_g_gol)):
        r = {}
        for ad_, t_ in (("", yas_g_oy), ("_gol", yas_g_gol)):
            v = {k_: x for k_, x in t_.get(kp, {}).items() if not supheli(k_)}
            r["genc" + ad_] = [yas_satir(k_, x[0], x[1], x[2]) for k_, x in sorted(v.items(), key=lambda y: y[1][0])[:25]]
            r["yasli" + ad_] = [yas_satir(k_, x[3], x[4], x[5]) for k_, x in sorted(v.items(), key=lambda y: -y[1][3])[:25]]
        yas[kp] = r
    istatistik_yaz(O, ad, okunur, tff, eski=eski, yas=yas, yas_kapsam=len(dog))
    for kid, d in kul_oy.items():
        A = lambda k_: okunur(ad.get(k_, ""))
        l = [[k_, A(k_), *v] for k_, v in d.items() if k_]
        ll = [[k_, A(k_), *v] for k_, v in kul_lig[kid].items() if k_ and v[0]]
        ss = [[k_, A(k_), sz, *v] for (k_, sz), v in kul_sezon[kid].items() if k_]
        mg = [[k_, A(k_), n, f, lg, m_[f]["tarih"], m_[f]["dep_kulup"] if m_[f]["ev_kulup"] == kid else m_[f]["ev_kulup"]] for k_, n, f, lg in mac_gol[kid] if k_]
        yaz(os.path.join(kdir, f"{kid}.json"), {
            "alanlar": ["kisi", "ad", "mac", "gol", "ilk", "son"],
            "gol": sorted([x for x in l if x[3]], key=lambda x: (-x[3], x[2]))[:25], "mac": sorted(l, key=lambda x: (-x[2], -x[3]))[:25],
            "lig_gol": ilk_n([x for x in ll if x[3]], lambda x: (-x[3], x[2])), "lig_mac": ilk_n(ll, lambda x: (-x[2], -x[3])),
            "sezon_alanlar": ["kisi", "ad", "sezon", "gol", "lig_gol", "gol_yemeden", "mac", "sari", "kirmizi"],
            "sezon_sari": ilk_n([x for x in ss if x[7]], lambda x: (-x[7], x[6], x[2])),
            "sezon_kirmizi": ilk_n([x for x in ss if x[8]], lambda x: (-x[8], x[6], x[2])),
            "kart_alanlar": ["kisi", "ad", "sari", "kirmizi", "mac", "ilk", "son"],
            "sari": ilk_n([[k_, A(k_), *v] for k_, v in kul_kart[kid].items() if k_ and v[0]], lambda x: (-x[2], x[4])),
            "kirmizi": ilk_n([[k_, A(k_), *v] for k_, v in kul_kart[kid].items() if k_ and v[1]], lambda x: (-x[3], x[4])),
            "sezon_gol": ilk_n([x for x in ss if x[3]], lambda x: (-x[3], x[2])),
            "sezon_lig_gol": ilk_n([x for x in ss if x[4]], lambda x: (-x[4], x[2])),
            "sezon_gy": ilk_n([x for x in ss if x[5]], lambda x: (-x[5], x[2])),
            "mac_gol_alanlar": ["kisi", "ad", "gol", "mac", "lig", "tarih", "rakip"],
            "mac_gol": ilk_n(mg, lambda x: (-x[2], x[5] or "")), "mac_lig_gol": ilk_n([x for x in mg if x[4]], lambda x: (-x[2], x[5] or "")),
            "donus_alanlar": ["mac", "fark", "biz", "onlar", "dakika"],   # en geride (kacan: en önde) olunan an
            "donus": sorted(donus.get(kid, []), key=lambda x: (-x[1], m_[x[0]]["tarih"] or "")),
            "kacan": sorted(kacan.get(kid, []), key=lambda x: (-x[1], m_[x[0]]["tarih"] or "")),
            **yas_rekor(kid)})
    for x in genel_gol:
        x[1] = okunur(ad.get(x[0], ""))
    yaz(os.path.join(tff, "rekor.json"), {"mac_gol_alanlar": ["kisi", "ad", "gol", "mac", "tarih", "sezon", "kulup", "rakip", "yarisma", "kademe", "playoff"],
                                          "mac_gol": sorted(genel_gol, key=lambda x: (-x[2], x[4] or ""))})
    print(f"TFF ayrıntı: {len(mevcut)} maç, {len(dizin)} oyuncu, {len(kul_oy)} kulüp")
    return mevcut

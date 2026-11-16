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
import collections, json, os, shutil, sqlite3

KOK = os.path.dirname(os.path.abspath(__file__))
OYUNCU_DB = os.path.join(KOK, "raw", "oyuncu.db")
KUPA_ES = os.path.join(KOK, "tff_kupa_eslesme.json")   # Maçkolik kupa maçı -> TFF maç no (1990-2007 kupa sayfaları)
YAR = {"lig": "L", "kupa": "K", "ozel_kupa": "O", "avrupa": "A", "terfi": "T"}
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
    """TFF'nin 1990-2007 kupa sayfalarını futbol.db'deki (Maçkolik kaynaklı) kupa maçlarına bağlar: tarih + iki kulüp."""
    tff_kulup = collections.defaultdict(list)   # TFF kulüp no -> [(kulüp, ilk sezon, son sezon)]; '2434-once' gibi dönemli kimlikler
    for kid, tid, ilk, son in c.execute("SELECT kulup_id, kaynak_id, ilk_sezon, son_sezon FROM kulup_kimlik WHERE kaynak='tff'"):
        tff_kulup[int(tid.split("-")[0])].append((kid, ilk or "0000", son or "9999"))
    def kulup(tid, tarih):
        y, ay = int(tarih[:4]), int(tarih[5:7])
        sezon = f"{y}-{y + 1}" if ay >= 7 else f"{y - 1}-{y}"
        l = tff_kulup.get(tid, [])
        return next((k for k, a, b in l if a <= sezon <= b), l[0][0] if len(l) == 1 else None)
    aday = collections.defaultdict(list)
    for kaynak, kid_, tarih, ev, dep in c.execute("SELECT kaynak, kaynak_id, tarih, ev_kulup, dep_kulup FROM mac WHERE yarisma='kupa'"):
        aday[tarih].append((f"{kaynak}:{kid_}", ev, dep))
    es = {}
    for mac, org, tarih, et, dt in o.execute("SELECT mac, organizasyon, tarih, ev_tff, dep_tff FROM mac_bilgi WHERE organizasyon LIKE '%Kupa%'"):
        if "Türkiye Kupası" not in (org or "") and "Kupası (Profesyonel" not in (org or ""):
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
        kupa = kupa_eslestir(o, c)
        yaz(KUPA_ES, kupa)
    else:
        if not os.path.exists(varyol):
            return []
        kupa = json.load(open(KUPA_ES, encoding="utf-8")) if os.path.exists(KUPA_ES) else {}
    # futbol.db maçı -> (TFF maç no, taraflar ters mi)
    bag = {}
    for m in maclar:
        if m["yarisma"] == "avrupa" or m["ev_gol"] is None:
            continue
        if m["kaynak"] == "tff" and m["kaynak_id"]:
            bag[m["id"]] = (int(m["kaynak_id"]), 0)
        elif f"{m['kaynak']}:{m['kaynak_id']}" in kupa:
            bag[m["id"]] = tuple(kupa[f"{m['kaynak']}:{m['kaynak_id']}"])
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
        if not a or any(ch.islower() for ch in a):
            return a
        if TR_HARF & set(a):
            return okunur(a)
        return " ".join(okunur(w) if w in tr else okunur(w.replace("I", "İ")) for w in a.split())
    return f


def maclari_yaz(o, c, maclar, bag, okunur_kulup, tff):
    okunur = kisi_okunur_kur(o, okunur_kulup)
    m_ = {m["id"]: m for m in maclar}
    tersi = {t: (f, ters) for f, (t, ters) in bag.items()}   # TFF no -> futbol no
    kadro = collections.defaultdict(lambda: ([], []))
    ad = {}
    # kaleci: TFF ilk 11'i kaleciyle başlatıyor; bir oyuncunun ilk sırada yazıldığı maçların oranı kalecileri ayırır (~1 / ~0)
    ilk_sira, ilk_say, bas_say = {}, collections.Counter(), collections.Counter()
    for mac, taraf, kisi, a, forma, ilk11 in o.execute("SELECT mac, taraf, kisi, ad, forma, ilk11 FROM kadro ORDER BY rowid"):
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
    teknik = collections.defaultdict(lambda: ([], []))
    for mac, taraf, kisi, a in o.execute("SELECT mac, taraf, kisi, ad FROM teknik"):
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
        if uyum in ("uyumsuz", "yok"):
            kayit["u"] = uyum
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
    O = collections.defaultdict(lambda: collections.defaultdict(lambda: [0] * 9))   # kisi -> anahtar -> [mac, ilk11, gol, pen, kk, sari, kirmizi, dakika, yedek]
    kul_oy = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, None, None]))   # kulüp -> kisi -> [mac, gol, ilk, son]
    kul_lig = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, None, None]))  # yalnız lig (play-off dahil)
    kul_sezon = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0]))   # kulüp -> (kisi, sezon) -> [gol, lig golü, gol yemeden (kaleci), maç]
    mac_gol = collections.defaultdict(list)   # kulüp -> [kisi, gol, futbol maç no, lig mi]
    kaleci = lambda k_: bas_say[k_] >= 3 and ilk_say[k_] / bas_say[k_] >= 0.6
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
        for i, taraf in enumerate(k):
            kid = m["ev_kulup"] if i == 0 else m["dep_kulup"]
            anahtar_ = (m["sezon"], kid, YAR[m["yarisma"]], m["kademe"] or 0)
            yedigi = m["dep_gol"] if i == 0 else m["ev_gol"]
            # gol yemeden: ilk 11'deki kaleci (ilk sıradaki, kaleci değilse kadrodaki kaleci), hükmen maçlar hariç
            ilk_ = ilk_sira.get((t, (2 - i) if ters else (i + 1)))
            gk = ilk_ if ilk_ and kaleci(ilk_) else next((p[1] for p in taraf if p[2] and kaleci(p[1])), None)
            if gk and yedigi == 0 and not hukmen:
                kul_sezon[kid][(gk, m["sezon"])][2] += 1
            for forma, kisi, ilk11 in taraf:
                oyn = ilk11 or kisi in giris
                r = O[kisi][anahtar_]
                if not oyn:
                    r[8] += 1
                    continue
                kul_sezon[kid][(kisi, m["sezon"])][3] += 1
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
            elif x[1] == "Y":
                r[5] += 1
            elif x[1] in ("R", "YR"):
                r[6] += 1
        for (kid, kisi), n in bu_mac.items():
            if n >= 2:
                mac_gol[kid].append([kisi, n, f, 1 if lig else 0])
    odir = os.path.join(tff, "o")
    if os.path.isdir(odir):
        shutil.rmtree(odir)
    okova = collections.defaultdict(dict)
    dizin = []
    for kisi, sat in O.items():
        if not kisi:
            continue
        satir = sorted([[*a, *v] for a, v in sat.items() if v[0] or v[8]], key=lambda x: (x[0], x[2]))
        if not any(s[4] for s in satir):
            continue   # hiç oynamamış (yalnız yedek kulübesi)
        okova[kisi % 500][kisi] = {"ad": okunur(ad.get(kisi, "")), "s": satir}
        mac = sum(s[4] for s in satir)
        gol = sum(s[6] for s in satir)
        son = max(satir, key=lambda s: (s[0], s[4]))
        dizin.append([kisi, okunur(ad.get(kisi, "")), mac, gol, min(s[0] for s in satir if s[4]), max(s[0] for s in satir if s[4]), son[1]])
    for b, d in okova.items():
        yaz(os.path.join(odir, f"{b}.json"), {"alanlar": ["sezon", "kulup", "yarisma", "kademe", "mac", "ilk11", "gol", "penalti", "kendi_kalesine",
                                                         "sari", "kirmizi", "dakika", "yedek"], "oyuncu": d})
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
            "sezon_alanlar": ["kisi", "ad", "sezon", "gol", "lig_gol", "gol_yemeden", "mac"],
            "sezon_gol": ilk_n([x for x in ss if x[3]], lambda x: (-x[3], x[2])),
            "sezon_lig_gol": ilk_n([x for x in ss if x[4]], lambda x: (-x[4], x[2])),
            "sezon_gy": ilk_n([x for x in ss if x[5]], lambda x: (-x[5], x[2])),
            "mac_gol_alanlar": ["kisi", "ad", "gol", "mac", "lig", "tarih", "rakip"],
            "mac_gol": ilk_n(mg, lambda x: (-x[2], x[5] or "")), "mac_lig_gol": ilk_n([x for x in mg if x[4]], lambda x: (-x[2], x[5] or ""))})
    print(f"TFF ayrıntı: {len(mevcut)} maç, {len(dizin)} oyuncu, {len(kul_oy)} kulüp")
    return mevcut

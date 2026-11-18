"""Kadın futbol ligleri (TFF arşivi pageID=848, 2006-07'den bugüne): sezon/hafta sayfaları ve maç sayfaları.

  python3 kadin.py liste     # sezon, grup ve hafta sayfaları -> raw/tff_kadin/<kaynak>_<sezon>_<pageID>/ (kaldığı yerden)
  python3 kadin.py guncel    # süren sezonun lig sayfaları (GUNCEL; her seferinde baştan)
  python3 kadin.py kur       # raw/tff_kadin -> raw/kadin.db (topla.py'nin ayrıştırıcısıyla; erkek verisinden ayrı)
  python3 kadin.py mac       # maç sayfaları -> raw/tff_kadin_mac/<son iki hane>/<macId>.html.gz (kaldığı yerden)
  python3 kadin.py ayikla    # maç sayfaları -> raw/kadin_detay.db (kadro, gol, kart...)
  python3 kadin.py site      # raw/kadin.db + raw/kadin_detay.db -> docs/data/kadin/ (kadin_site.py)
  python3 kadin.py duzelt    # kur sonunda kendiliğinden: TFF puan tablosuyla hükmen / eksik maçlar ve play-off sanılan aşamalar
  python3 kadin.py denetle   # resmi puan tablolarıyla tutmayan grupların listesi
  python3 kadin.py durum

Erkek ligleriyle karışmasın diye her şey ayrı klasör ve veritabanında. Kadın kulüpleri erkek kulüpleriyle aynı TFF
kulüp numarasını taşıyabilir.
"""
import collections, gzip, os, re, sqlite3, subprocess, sys, time

import topla

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "tff_kadin")
MAC_HAM = os.path.join(KOK, "raw", "tff_kadin_mac")
DB = os.path.join(KOK, "raw", "kadin.db")

# (kaynak, sezon, pageID): kaynak = lig adı kısa kodu; kademe sezon içindeki sıraya göre (en üst lig 1)
SEZONLAR = [
    ("k1", "2006-2007", 627), ("k1", "2007-2008", 424), ("k2", "2007-2008", 683),
    ("k1", "2008-2009", 836), ("k1", "2009-2010", 933), ("k2", "2009-2010", 936),
    ("k1", "2010-2011", 1066), ("kb", "2010-2011", 1068), ("k1", "2011-2012", 1179), ("k2", "2011-2012", 1180),
    ("k1", "2012-2013", 1252), ("k2", "2012-2013", 1253), ("k1", "2013-2014", 1280), ("k2", "2013-2014", 1281),
    ("k1", "2014-2015", 1326), ("k2", "2014-2015", 1327), ("k3", "2014-2015", 1328),
    ("k1", "2015-2016", 1390), ("k2", "2015-2016", 1391), ("k3", "2015-2016", 1392),
    ("k1", "2016-2017", 1426), ("k2", "2016-2017", 1427), ("k3", "2016-2017", 1428),
    ("k1", "2017-2018", 1448), ("k2", "2017-2018", 1449), ("k3", "2017-2018", 1450),
    ("k1", "2018-2019", 1484), ("k2", "2018-2019", 1485), ("k3", "2018-2019", 1486),
    ("k1", "2019-2020", 1497), ("k2", "2019-2020", 1498), ("k3", "2019-2020", 1499),
    ("k1", "2020-2021", 1533),
    ("ks", "2021-2022", 1581), ("k2", "2021-2022", 1582), ("k3", "2021-2022", 1588),
    ("ks", "2022-2023", 1623), ("k1", "2022-2023", 1624), ("k2", "2022-2023", 1625), ("k3", "2022-2023", 1626),
    ("ks", "2023-2024", 1653), ("k1", "2023-2024", 1654), ("k2", "2023-2024", 1655), ("k3", "2023-2024", 1656),
    ("ks", "2024-2025", 1735), ("k1", "2024-2025", 1736), ("k2", "2024-2025", 1737), ("k3", "2024-2025", 1738),
    ("ks", "2025-2026", 1781), ("k1", "2025-2026", 1782), ("k2", "2025-2026", 1783), ("k3", "2025-2026", 1792),
]
# Süren sezon: TFF'nin güncel lig sayfaları (arşive geçmemiş; her çalıştırmada baştan indirilir). 3. Lig yeni sezona
# geçmediyse sayfası eski sezonu gösterir; o zaman atlanır.
GUNCEL = [("ks", 1000), ("k1", 1602), ("k2", 1001), ("k3", 1298)]
LIG_AD = {"ks": "Kadın Futbol Süper Ligi", "k1": "Kadınlar 1. Ligi", "k2": "Kadınlar 2. Ligi", "k3": "Kadınlar 3. Ligi", "kb": "Kadınlar Bölgesel Ligi"}


def kademe(kaynak, sezon):
    """Süper Lig 2021-22'de kuruldu; 1. Lig o zamana kadar en üst lig, 2022-23'ten sonra ikinci lig."""
    yil = int(sezon[:4])
    if kaynak == "ks":
        return 1
    if kaynak == "kb":
        return 3
    n = int(kaynak[1])
    if yil >= 2022:
        return n + 1
    if yil == 2021:
        return n   # 2021-22: Süper Lig, 2. Lig, 3. Lig (1. Lig yok)
    return n


def liste():
    topla.HAM = HAM
    d = topla.Indirici()
    for kaynak, sezon, pid in SEZONLAR:
        topla.sezon_indir(d, kaynak, sezon, pid)
    print("Bitti, yeni indirilen sayfa:", d.indirilen)


def simdiki_sezon():
    import datetime
    b = datetime.date.today()
    y = b.year if b.month >= 7 else b.year - 1
    return f"{y}-{y + 1}"


def guncel():
    """Süren sezonun lig sayfaları -> raw/tff_kadin/<kaynak>_<sezon>_<pageID>/ (her seferinde baştan)."""
    import shutil
    topla.HAM = HAM
    d = topla.Indirici()
    sezon = simdiki_sezon()
    for kaynak, pid in GUNCEL:
        klasor = os.path.join(HAM, f"{kaynak}_{sezon}_{pid}")
        if os.path.isdir(klasor):
            shutil.rmtree(klasor)
        topla.sezon_indir(d, kaynak, sezon, pid)
        giris = os.path.join(klasor, "giris.html")
        t = open(giris, encoding="cp1254", errors="replace").read() if os.path.exists(giris) else ""
        if not any((m["tarih"] or "") >= f"{sezon[:4]}-08-01" for m in topla.maclar(t) or []):
            print(f"{kaynak} {sezon}: sayfa henüz yeni sezona geçmemiş, atlandı", flush=True)
            shutil.rmtree(klasor, ignore_errors=True)
    print("Bitti, indirilen sayfa:", d.indirilen)


def kur():
    topla.LIG.update(LIG_AD)
    topla.kademe = lambda kaynak, yil: kademe(kaynak, f"{yil}-{yil + 1}")
    topla.kur(DB, HAM)
    c = sqlite3.connect(DB)
    for r in c.execute("SELECT sezon, lig, COUNT(*), SUM(ev_gol IS NOT NULL) FROM mac GROUP BY 1, 2 ORDER BY 1, 2"):
        print(*r)
    print("toplam:", c.execute("SELECT COUNT(*) FROM mac").fetchone()[0])
    duzelt()


# ---------------------------------------------------------------- TFF puan tablolarıyla düzeltme
# Kadın liglerinin sezon sayfalarında üç sorun var (2026-11-17 taraması, raw/kadin.db puan tablosuyla karşılaştırma):
#  1. Ligden çekilen takımın maçları fikstürde hiç listelenmiyor ama puan tablosunda 0-3 hükmen sayılıyor.
#  2. Bazı maçların skoru "-" (oynanmadı) ama puan tablosunda sonucu var (hükmen).
#  3. Bazı sezonlarda normal sezon ya da grup aşaması play-off modülünde listeleniyor (2016-17, 2020-21 en üst lig).
# Düzeltme yalnız resmi puan tablosuyla birebir tutan sonuç bulunabiliyorsa yapılır; tutmayan gruplar raporlanır.

def _grup_kosul(c, sezon, kd, g):
    """resmi tablonun grubu bizde de lig grubu olarak varsa yalnız onun maçları"""
    var = g and c.execute("SELECT 1 FROM mac WHERE sezon=? AND kademe=? AND asama='lig' AND grup=? LIMIT 1", (sezon, kd, g)).fetchone()
    return (" AND grup=?", (g,)) if var else ("", ())


def _tablo(c, sezon, kd, T, g=""):
    t = {k: [0] * 6 for k in T}
    k_, p_ = _grup_kosul(c, sezon, kd, g)
    for e, d, a, b in c.execute("SELECT ev_id, dep_id, ev_gol, dep_gol FROM mac WHERE sezon=? AND kademe=? AND asama='lig' AND ev_gol IS NOT NULL" + k_,
                                (sezon, kd, *p_)):
        if e in T and d in T:
            for x, ga, gb in ((e, a, b), (d, b, a)):
                r = t[x]; r[0] += 1; r[1] += ga > gb; r[2] += ga == gb; r[3] += ga < gb; r[4] += ga; r[5] += gb
    return t


def duzelt():
    import itertools
    c = sqlite3.connect(DB)
    if "durum" not in [r[1] for r in c.execute("PRAGMA table_info(mac)")]:
        c.execute("ALTER TABLE mac ADD COLUMN durum TEXT")
    kid = {t: k for k, t in c.execute("SELECT id, tff_id FROM kulup")}
    gruplar = c.execute("SELECT DISTINCT sezon, kademe, COALESCE(grup, '') FROM puan ORDER BY 1, 2, 3").fetchall()
    rapor, tamam, n_ekle, n_skor, n_asama = [], [], 0, 0, 0
    # 3. play-off sanılan aşamalar: resmi grubun takımları arasında hiç lig maçı yoksa, o takımlar arasındaki
    #    play-off maçlarının en sonuncuları (resmi maç sayısı kadar) o grubun lig maçlarıdır; sezonda başka lig maçı
    #    yoksa bunlardan önceki maçlar normal sezondur
    sk = collections.defaultdict(list)
    for sezon, kd, g in gruplar:
        sk[(sezon, kd)].append(g)
    for (sezon, kd), gl in sk.items():
        ilk_lig = c.execute("SELECT COUNT(*) FROM mac WHERE sezon=? AND kademe=? AND asama='lig'", (sezon, kd)).fetchone()[0]
        secilen = []
        for g in gl:
            if (g and c.execute("SELECT 1 FROM mac WHERE sezon=? AND kademe=? AND asama='lig' AND grup=?", (sezon, kd, g)).fetchone()) or (not g and ilk_lig):
                continue
            R = {kid[t]: r for t, *r in c.execute("SELECT tff_id, O FROM puan WHERE sezon=? AND kademe=? AND COALESCE(grup,'')=?", (sezon, kd, g)) if t in kid}
            T, n = set(R), sum(r[0] for r in R.values()) // 2
            if ilk_lig and c.execute(f"SELECT COUNT(*) FROM mac WHERE sezon=? AND kademe=? AND asama='lig' AND ev_id IN ({','.join('?' * len(T))}) "
                                     f"AND dep_id IN ({','.join('?' * len(T))})", (sezon, kd, *T, *T)).fetchone()[0]:
                continue   # bu takımların lig maçları zaten var (grup adı farklı yazılmış)
            aday = [r for r in c.execute("SELECT id, tarih, ev_id, dep_id FROM mac WHERE sezon=? AND kademe=? AND asama<>'lig' AND tarih IS NOT NULL "
                                         "ORDER BY tarih, id", (sezon, kd)) if r[2] in T and r[3] in T]
            # tarih sırasıyla art arda n maç; her takımın maç sayısı resmi tabloyla tutan en geç pencere
            # (ikinci aşama grubu normal sezondan sonra; turnuva grubu eleme maçlarından önce)
            sec = None
            for i in range(len(aday) - n, -1, -1) if n else []:
                w = aday[i:i + n]
                say_ = collections.Counter(x for r in w for x in (r[2], r[3]))
                if all(say_[t] == R[t][0] for t in T):
                    sec = w; break
            if not sec:
                continue
            c.executemany("UPDATE mac SET asama='lig', grup=? WHERE id=?", [(g or None, r[0]) for r in sec])
            n_asama += len(sec); secilen += sec
            tamam.append(f"{sezon} {kd}. kademe {g}: {len(sec)} maç play-off'tan lig grubuna")
        if secilen and not ilk_lig:   # sezonda hiç lig maçı yoktu: ikinci aşamadan önceki maçlar normal sezon
            k = c.execute("UPDATE mac SET asama='lig', grup=NULL WHERE sezon=? AND kademe=? AND asama<>'lig' AND tarih < ?",
                          (sezon, kd, min(r[1] for r in secilen))).rowcount
            n_asama += k
            tamam.append(f"{sezon} {kd}. kademe: {k} maç normal sezon olarak lige")
    # 1-2. hükmen maçlar
    for sezon, kd, g in gruplar:
        R = {kid[t]: list(r) for t, *r in c.execute("SELECT tff_id, O, G, B, M, A, Y FROM puan WHERE sezon=? AND kademe=? AND COALESCE(grup,'')=?",
                                                    (sezon, kd, g)) if t in kid}
        T = set(R)
        if len(T) < 2:
            continue
        # bütün maçları 0-3 hükmen sayılan (ligden çekilen) takımlar: oynadığı maçlar da 0-3 yazılır
        for t, r in R.items():
            if r[0] and r[1] == r[2] == 0 and r[4] == 0 and r[5] == 3 * r[0]:
                for mid, e, d in c.execute("SELECT id, ev_id, dep_id FROM mac WHERE sezon=? AND kademe=? AND asama='lig' AND (ev_id=? OR dep_id=?)",
                                           (sezon, kd, t, t)).fetchall():
                    if (e in T and d in T):
                        c.execute("UPDATE mac SET ev_gol=?, dep_gol=?, durum='Hük.' WHERE id=?", (0 if e == t else 3, 3 if e == t else 0, mid))
        biz = _tablo(c, sezon, kd, T, g)
        k_, p_ = _grup_kosul(c, sezon, kd, g)
        D = {t: [a - b for a, b in zip(R[t], biz[t])] for t in T}
        if all(not any(v) for v in D.values()):
            continue
        ad = f"{sezon} {kd}. kademe {g or ''}".strip()
        n_tk = len(T)
        tur = {R[t][0] / (n_tk - 1) for t in T}
        if len(tur) != 1 or not float(next(iter(tur))).is_integer():
            rapor.append(f"{ad}: devre sayısı çıkarılamadı"); continue
        tur = int(next(iter(tur)))
        if any(v[0] < 0 for v in D.values()):
            # lig haftası gibi listelenmiş final / şampiyonluk maçı: iki takım devre sayısından fazla karşılaşmış,
            # en sonuncusu çıkınca iki takımın satırı resmi tabloyla tutuyorsa o maç play-off sayılır
            cift = collections.defaultdict(list)
            for mid, e, d, x, y, tr in c.execute("SELECT id, ev_id, dep_id, ev_gol, dep_gol, tarih FROM mac WHERE sezon=? AND kademe=? AND asama='lig' "
                                                 "AND ev_gol IS NOT NULL" + k_ + " ORDER BY tarih", (sezon, kd, *p_)):
                if e in T and d in T:
                    cift[frozenset((e, d))].append((mid, e, d, x, y))
            cikan = []
            for l in cift.values():
                if len(l) > tur:
                    mid, e, d, x, y = l[-1]
                    DD = {t: v[:] for t, v in D.items()}
                    for t, ga, gb in ((e, x, y), (d, y, x)):
                        v = DD[t]; v[0] += 1; v[1] += ga > gb; v[2] += ga == gb; v[3] += ga < gb; v[4] += ga; v[5] += gb
                    if not any(DD[e]) and not any(DD[d]):
                        D = DD; cikan.append(mid)
            if any(v[0] < 0 for v in D.values()):
                rapor.append(f"{ad}: bizde fazla maç var (ikinci aşama aynı grupta olabilir)"); continue
            c.executemany("UPDATE mac SET asama='play-off' WHERE id=?", [(m,) for m in cikan])
            tamam.append(f"{ad}: {len(cikan)} maç lig haftasından play-off'a (final/şampiyonluk maçı)")
            n_asama += len(cikan)
            if all(not any(v) for v in D.values()):
                continue
        say = collections.Counter()
        bos = []   # skoru olmayan lig maçları: (id, ev, dep)
        for mid, e, d, eg in c.execute("SELECT id, ev_id, dep_id, ev_gol FROM mac WHERE sezon=? AND kademe=? AND asama='lig'" + k_, (sezon, kd, *p_)):
            if e in T and d in T:
                say[frozenset((e, d))] += 1
                if eg is None:
                    bos.append((mid, e, d))
        yeni = []   # (ev, dep): fikstürde olmayan maçlar; ev sahibi, varsa öbür maçın deplasman takımı
        for a, b in itertools.combinations(sorted(T), 2):
            eksik = tur - say[frozenset((a, b))]
            for _ in range(max(0, eksik)):
                ev = c.execute("SELECT dep_id FROM mac WHERE sezon=? AND kademe=? AND asama='lig' AND ((ev_id=? AND dep_id=?) OR (ev_id=? AND dep_id=?))" + k_ + " LIMIT 1",
                               (sezon, kd, a, b, b, a, *p_)).fetchone()
                ev = ev[0] if ev else a
                yeni.append((ev, b if ev == a else a))
        yuva = [(e, d) for _, e, d in bos] + yeni
        if 2 * len(yuva) != sum(v[0] for v in D.values()):
            rapor.append(f"{ad}: eksik maç sayısı tutmuyor ({len(yuva)} boş yer, puan tablosuna göre {sum(v[0] for v in D.values()) // 2})"); continue
        # sonuç: tek boş yer varsa skor doğrudan çıkar; yoksa 3-0 / 0-3 / 0-0 hükmen kombinasyonu aranır
        def uygula(D, e, d, x, y, k=1):
            for t, ga, gb in ((e, x, y), (d, y, x)):
                v = D[t]; v[0] -= k; v[1] -= k * (ga > gb); v[2] -= k * (ga == gb); v[3] -= k * (ga < gb); v[4] -= k * ga; v[5] -= k * gb
        sonuc = None
        DD, cozum = {t: v[:] for t, v in D.items()}, {}
        degisti = True
        while degisti and len(cozum) < len(yuva):
            degisti = False
            for i, (e, d) in enumerate(yuva):
                if i in cozum:
                    continue
                for t, ters in ((e, False), (d, True)):
                    if sum(1 for j, (a, b) in enumerate(yuva) if j not in cozum and t in (a, b)) == 1:
                        x, y = DD[t][4], DD[t][5]
                        if ters:
                            x, y = y, x
                        if x < 0 or y < 0:
                            break
                        uygula(DD, e, d, x, y); cozum[i] = (x, y); degisti = True
                        break
        hukmen_ara = False
        if len(cozum) == len(yuva) and all(not any(v) for v in DD.values()):
            sonuc = [cozum[i] for i in range(len(yuva))]
        else:
            DD = {t: v[:] for t, v in D.items()}
            yol = []
            def ara(i):
                if i == len(yuva):
                    return all(not any(v) for v in DD.values())
                e, d = yuva[i]
                for x, y in ((3, 0), (0, 3), (0, 0)):
                    uygula(DD, e, d, x, y)
                    if all(v[0] >= 0 and v[1] >= 0 and v[2] >= 0 and v[3] >= 0 and v[4] >= 0 and v[5] >= 0 for v in DD.values()):
                        yol.append((x, y))
                        if ara(i + 1):
                            return True
                        yol.pop()
                    uygula(DD, e, d, x, y, -1)
                return False
            if len(yuva) <= 60 and ara(0):
                sonuc, hukmen_ara = yol, True
        if not sonuc:
            rapor.append(f"{ad}: {len(yuva)} eksik maçın sonucu puan tablosundan çıkarılamadı"); continue
        lig = c.execute("SELECT lig FROM mac WHERE sezon=? AND kademe=? LIMIT 1", (sezon, kd)).fetchone()[0]
        tamam.append(f"{ad}: {len(bos)} skorsuz maça sonuç, {len(yeni)} maç eklendi ({', '.join(f'{x}-{y}' for x, y in sonuc)})")
        for i, ((e, d), (x, y)) in enumerate(zip(yuva, sonuc)):
            hk = "Hük." if hukmen_ara and (x, y) in ((3, 0), (0, 3)) else None
            if i < len(bos):
                c.execute("UPDATE mac SET ev_gol=?, dep_gol=?, durum=? WHERE id=?", (x, y, hk, bos[i][0])); n_skor += 1
            else:
                ad_ = dict(c.execute("SELECT id, ad FROM kulup WHERE id IN (?, ?)", (e, d)))
                c.execute("INSERT INTO mac(kaynak, kaynak_id, kademe, lig, sezon, grup, asama, ev_id, dep_id, ev_adi, dep_adi, ev_gol, dep_gol, ham_skor, durum) "
                          "VALUES('puan', ?, ?, ?, ?, ?, 'lig', ?, ?, ?, ?, ?, ?, 'puan tablosundan', ?)",
                          (f"{sezon}-{kd}-{g}-{e}-{d}-{i}", kd, lig, sezon, g or None, e, d, ad_[e], ad_[d], x, y, hk)); n_ekle += 1
    c.commit()
    print(f"düzeltme: {n_asama} maç play-off'tan lige, {n_skor} skorsuz maça sonuç, {n_ekle} fikstürde olmayan maç eklendi (TFF puan tablosundan)")
    for r in tamam:
        print("  düzeltildi:", r)
    for r in rapor:
        print("  çözülemedi:", r)


def denetle():
    """Lig gruplarımızı TFF'nin resmi puan tablolarıyla karşılaştırır: oynanan maç sayısı tutmayan grupları yazar."""
    c = sqlite3.connect(DB)
    kid = {t: k for k, t in c.execute("SELECT id, tff_id FROM kulup")}
    n = 0
    for sezon, kd, g in c.execute("SELECT DISTINCT sezon, kademe, COALESCE(grup, '') FROM puan ORDER BY 1, 2, 3").fetchall():
        R = {kid[t]: (a, list(r)) for t, a, *r in c.execute("SELECT tff_id, ad, O, G, B, M, A, Y FROM puan WHERE sezon=? AND kademe=? AND COALESCE(grup,'')=?",
                                                          (sezon, kd, g)) if t in kid}
        b = _tablo(c, sezon, kd, set(R), g)
        fark = [a for t, (a, r) in R.items() if r != b[t]]
        if fark:
            n += 1
            print(f"{sezon} {kd}. kademe {g}: resmi {sum(r[0] for _, r in R.values()) // 2} maç, bizde {sum(v[0] for v in b.values()) // 2}; "
                  f"{len(fark)}/{len(R)} takımın satırı farklı")
    print(n, "grupta resmi tabloyla fark")


def mac_yol(m):
    return os.path.join(MAC_HAM, str(m)[-2:].zfill(2), f"{m}.html.gz")


def mac():
    c = sqlite3.connect(DB)
    import oyuncu   # son 30 günün kadrosuz sayfaları yeniden (TFF kadroları sonradan giriyor)
    oyuncu.kadrosuz_yenile(c.execute("SELECT kaynak_id, tarih, durum FROM mac WHERE ev_gol IS NOT NULL AND kaynak='tff'"), mac_yol)
    hedef = [m for (m,) in c.execute("SELECT kaynak_id FROM mac WHERE ev_gol IS NOT NULL ORDER BY sezon DESC, kademe")]
    liste_ = [m for m in hedef if not os.path.exists(mac_yol(m)) and not os.path.exists(mac_yol(m) + ".yok")]
    print(f"{len(liste_)}/{len(hedef)} maç sayfası indirilecek", flush=True)
    hata = 0
    for i, m in enumerate(liste_, 1):
        os.makedirs(os.path.dirname(mac_yol(m)), exist_ok=True)
        r = subprocess.run(["curl", "-sL", "--compressed", "-m", "60", "-A", topla.UA, "-w", "\n%{http_code}",
                            f"https://www.tff.org/Default.aspx?pageID=29&macId={m}"], capture_output=True)
        govde, _, kod = r.stdout.rpartition(b"\n")
        if kod.decode().strip() == "200" and len(govde) > 20000 and (b"rptKadrolar" in govde or b"lblOrganizasyonAdi" in govde):
            with gzip.open(mac_yol(m), "wb") as g:
                g.write(govde)
            hata = 0
        elif kod.decode().strip() == "200" and len(govde) > 15000:
            open(mac_yol(m) + ".yok", "w").close()
        else:
            hata += 1
            if hata >= 10:
                print("  art arda 10 hata, 30 dk bekleniyor", time.strftime("%H:%M"), flush=True)
                time.sleep(1800)
                hata = 0
            time.sleep(30 * hata)
        if i % 200 == 0:
            print(f"  {i}/{len(liste_)} {time.strftime('%H:%M')}", flush=True)
        time.sleep(2)
    print("Bitti.", flush=True)


DETAY_DB = os.path.join(KOK, "raw", "kadin_detay.db")


def ayikla():
    """Maç sayfaları -> raw/kadin_detay.db (oyuncu.py'nin ayrıştırıcısıyla: kadro, gol, kart, değişiklik, teknik, hakem)."""
    import oyuncu
    oyuncu.HAM, oyuncu.OYUNCU_DB = MAC_HAM, DETAY_DB
    oyuncu.ayikla()


def durum():
    if os.path.exists(DB):
        c = sqlite3.connect(DB)
        n = c.execute("SELECT COUNT(*) FROM mac WHERE ev_gol IS NOT NULL").fetchone()[0]
        var = sum(os.path.exists(mac_yol(m)) for (m,) in c.execute("SELECT kaynak_id FROM mac WHERE ev_gol IS NOT NULL"))
        print(f"maç sayfası: {var}/{n}")


if __name__ == "__main__":
    {"liste": liste, "guncel": guncel, "kur": kur, "duzelt": duzelt, "denetle": denetle, "mac": mac, "ayikla": ayikla, "site": lambda: __import__("kadin_site").aktar(), "durum": durum}[sys.argv[1]]()

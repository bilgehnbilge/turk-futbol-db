"""Kulüp logoları: Football Manager logo paketi (FM kulüp kimliğine göre adlandırılmış PNG'ler) -> docs/logo/.

  python3 logo.py esle   raw/fm_takimlar.tsv + paket -> logo_eslesme.json (+ logo_eslesme_kontrol.txt)
  python3 logo.py kopyala                           -> docs/logo/<FM kimliği>.png (64 px)

raw/fm_takimlar.tsv: FM kimliği <tab> takım adı <tab> lig (Sortitoutsi FM26 Türkiye lig sayfalarından; kapanmış
kulüpler bu listede yok, onlar elle ya da arama ile logo_eslesme_elle.json'a eklenir).
logo_eslesme.json: {"tff:3661": <FM kimliği>, ...}  — kulübün kalıcı kimliği (TFF / Maçkolik) -> FM kimliği.
Elle düzeltme: logo_eslesme_elle.json aynı biçimde; otomatik eşlemenin üstüne yazılır (değer null = logo yok).
"""
import difflib, json, os, re, sqlite3, subprocess, sys, unicodedata

KOK = os.path.dirname(os.path.abspath(__file__))
PAKET = os.path.expanduser("~/Library/Application Support/Sports Interactive/Football Manager 27/graphics/logos/"
                           "Logos TCM26/Men/Europe/Turkey/Clubs")
CIKTI = os.path.join(KOK, "docs", "logo")
ESLESME = os.path.join(KOK, "logo_eslesme.json")
ELLE = os.path.join(KOK, "logo_eslesme_elle.json")

GURULTU = r"\b(a ?s|as|sk|jk|spor kulubu|kulubu|sportif faaliyetler|sportif yatirimlar|yatirimlari|ve)\b"


def norm(s):
    s = s.replace("İ", "i").replace("I", "ı").lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s.replace("ı", "i")) if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\bfutbol kulubu\b|\bfutbol spor kulubu\b|\bfsk\b", "fk", s)   # FK adı şehir adından ayrı kalsın
    s = re.sub(r"\bfutbol a ?s\b|\bf a ?s\b|\bfas\b", "fas", s)
    s = re.sub(GURULTU, " ", s)
    s = re.sub(r"\bbld\b|\bbelediyesi\b", "belediye", s)
    return re.sub(r"\s+", " ", s).strip()


def kok(s):
    """'Ödemiş Spor' -> 'odemisspor' (boşluklar atılır, sondaki 'spor' tek biçime getirilir)"""
    k = norm(s).replace(" ", "")
    return k[:-4] if k.endswith("spor") else k


PRO = {"130286", "463479", "463485", "463486", "70043162", "70043163", "70043164", "70043165"}   # FM26: Süper Lig - 3. Lig


def kelimeler(s):
    return {w[:-4] if w.endswith("spor") and len(w) > 4 else w for w in norm(s).split()} - {"", "spor"}


def seviye(lig):
    return 3 if lig in PRO else 2 if lig.startswith("70086") else 1   # pro > BAL > amatör


def benzerlik(a, b, pro=False):
    """1.0 = aynı ad (spor eki/boşluk farkı); 0.97 = profesyonel ligde sponsorlu ad (bizim adın bütün kelimeleri FM adında);
    0.9 = kelime alt kümesi (kontrol listesine düşer); 0 = eşleşmez"""
    ka, kb = kok(a), kok(b)
    if not ka or not kb:
        return 0
    if ka == kb:
        return 1.0
    wa, wb = kelimeler(a), kelimeler(b)
    if wa and wa <= wb and len("".join(wa)) >= 5 and not any(w.isdigit() for w in wb - wa):
        return 0.97 if pro else 0.9
    return 0


def esle():
    paket = {int(f[5:-4]) for f in os.listdir(PAKET) if re.fullmatch(r"TCM1_\d+\.png", f)}
    fm = {}
    for satir in open(os.path.join(KOK, "raw", "fm_takimlar.tsv"), encoding="utf-8"):
        p = satir.rstrip("\n").split("\t")
        if len(p) >= 2 and int(p[0]) in paket:
            fm[int(p[0])] = {"ad": p[1], "lig": p[2] if len(p) > 2 else ""}
    kulupler = json.load(open(os.path.join(KOK, "docs", "data", "kulupler.json"), encoding="utf-8"))
    c = sqlite3.connect(os.path.join(KOK, "futbol.db"))
    kimlik = {}
    for kid, kim in c.execute("SELECT kulup_id, kaynak || ':' || kaynak_id FROM kulup_kimlik ORDER BY kaynak <> 'tff', son_sezon DESC"):
        kimlik.setdefault(kid, kim)

    adaylar = []   # (puan, kulüp, fm)
    for k in kulupler:
        if not k["yerli"] or k["id"] not in kimlik:
            continue
        # dönem adları: yalnız kulübün son yıllarına ait olanlar (eski bir ad bugün başka kulübün adı olabilir)
        adlar = [a[0] for a in k["adlar"] if a[3] >= 10 and int(a[2][:4]) >= int(k["son"][:4]) - 6]
        guncel = k["son"] >= "2024"
        for f, v in fm.items():
            pro = guncel and v["lig"] in PRO
            p = benzerlik(k["ad"], v["ad"], pro)
            if adlar and max(benzerlik(a, v["ad"]) for a in adlar) == 1.0:   # dönem adları yalnız birebir eşleşmede
                p = max(p, 0.99)
            if p:
                # aynı adlı birden çok FM takımı: güncel kulüpte profesyonel ligdeki öne, kapanmış kulüpte alt ligdeki
                p += 0.02 * pro + 0.001 * seviye(v["lig"]) * (1 if k["son"] >= "2015" else -1)
                adaylar.append((p, k["id"], f))
    adaylar.sort(reverse=True)
    kulup_fm, kullanilan = {}, set()
    for p, kid, f in adaylar:   # açgözlü eşleme: her FM takımı tek kulübe
        if kid in kulup_fm or f in kullanilan:
            continue
        kulup_fm[kid] = (f, p); kullanilan.add(f)

    sonuc = {kimlik[kid]: f for kid, (f, p) in kulup_fm.items() if p >= 0.97}
    if os.path.exists(ELLE):
        for k, v in json.load(open(ELLE, encoding="utf-8")).items():
            if not k.startswith("_"):
                if v is None:
                    sonuc.pop(k, None)
                else:
                    sonuc[k] = v
    json.dump(dict(sorted(sonuc.items())), open(ESLESME, "w", encoding="utf-8"), ensure_ascii=False, indent=0)

    K = {k["id"]: k for k in kulupler}
    with open(os.path.join(KOK, "logo_eslesme_kontrol.txt"), "w", encoding="utf-8") as out:
        out.write("Emin olunamayan eşlemeler (kelime alt kümesi; logo_eslesme.json'a ALINMADI): kulüp -> FM takımı\n")
        for kid, (f, p) in sorted(kulup_fm.items(), key=lambda x: x[1][1]):
            if p < 0.97:
                out.write(f"  {p:.2f}  {K[kid]['ad']} [{kimlik[kid]}] {K[kid]['ilk'][:4]}-{K[kid]['son'][:4]} -> {fm[f]['ad']} ({f}) {fm[f]['lig']}\n")
        eksik = [k for k in kulupler if k["yerli"] and k["id"] not in kulup_fm]
        out.write(f"\nLogosu bulunamayan {len(eksik)} kulüp (maç sayısına göre):\n")
        for k in sorted(eksik, key=lambda k: -k["mac"]):
            out.write(f"  {k['ad']} [{kimlik.get(k['id'])}] {k['ilk'][:4]}-{k['son'][:4]} {k['mac']} maç\n")
    yerli = sum(k["yerli"] for k in kulupler)
    print(f"{len(fm)} FM takımı (pakette), {yerli} yerli kulüp, {len(kulup_fm)} eşlendi; "
          f"{sum(p < 0.97 for f, p in kulup_fm.values())} emin değil -> logo_eslesme_kontrol.txt")


def kopyala():
    os.makedirs(CIKTI, exist_ok=True)
    gerekli = set(json.load(open(ESLESME, encoding="utf-8")).values())
    for f in os.listdir(CIKTI):
        if f.endswith(".png") and int(f[:-4]) not in gerekli:
            os.remove(os.path.join(CIKTI, f))
    yeni = 0
    for f in gerekli:
        hedef = os.path.join(CIKTI, f"{f}.png")
        if os.path.exists(hedef):
            continue
        subprocess.run(["sips", "-Z", "64", os.path.join(PAKET, f"TCM1_{f}.png"), "--out", hedef], capture_output=True, check=True)
        yeni += 1
    boyut = sum(os.path.getsize(os.path.join(CIKTI, f)) for f in os.listdir(CIKTI))
    print(f"{len(gerekli)} logo ({yeni} yeni) -> {CIKTI} ({boyut / 1e6:.1f} MB)")


# ---------------------------------------------------------------- renkler
def png_oku(yol):
    """8 bit RGB/RGBA, taramasız PNG -> [(r, g, b, a), ...] (yalnız standart kütüphane)."""
    import struct, zlib
    d = open(yol, "rb").read()
    i, idat, w = 8, b"", None
    while i < len(d):
        n, tur = struct.unpack(">I4s", d[i:i + 8])
        veri = d[i + 8:i + 8 + n]
        if tur == b"IHDR":
            w, h, derinlik, renk_turu = struct.unpack(">IIBB", veri[:10])
            if derinlik != 8 or renk_turu not in (2, 6):
                return []
            bpp = 4 if renk_turu == 6 else 3
        elif tur == b"IDAT":
            idat += veri
        i += 12 + n
    ham, satir, onceki, px = zlib.decompress(idat), w * bpp, bytearray(w * bpp), []
    for y in range(h):
        f, s = ham[y * (satir + 1)], bytearray(ham[y * (satir + 1) + 1:(y + 1) * (satir + 1)])
        for x in range(satir):
            a = s[x - bpp] if x >= bpp else 0
            b = onceki[x]
            c = onceki[x - bpp] if x >= bpp else 0
            if f == 1: s[x] = (s[x] + a) & 255
            elif f == 2: s[x] = (s[x] + b) & 255
            elif f == 3: s[x] = (s[x] + (a + b) // 2) & 255
            elif f == 4:
                p_ = a + b - c; pa, pb, pc = abs(p_ - a), abs(p_ - b), abs(p_ - c)
                s[x] = (s[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        px += [tuple(s[x:x + bpp]) + ((255,) if bpp == 3 else ()) for x in range(0, satir, bpp)]
        onceki = s
    return px


def renkler(yol):
    """Logonun ana rengi ve ikinci rengi (#rrggbb). Beyaz/gri/siyah zemin ve kenarlar elenir;
    renkli piksel yoksa (siyah-beyaz logo) koyu gri."""
    import colorsys
    kutu = {}
    for r_, g, b, a in png_oku(yol):
        if a < 200:
            continue
        h, l, s = colorsys.rgb_to_hls(r_ / 255, g / 255, b / 255)
        if s < 0.25 or l > 0.92 or l < 0.08:
            continue
        k = (round(h * 24) % 24, round(l * 4))
        x = kutu.setdefault(k, [0, 0, 0, 0]); x[0] += 1; x[1] += r_; x[2] += g; x[3] += b
    sec = sorted(kutu.items(), key=lambda kv: -kv[1][0])
    toplam = sum(v[0] for v in kutu.values())
    out = []
    for (hb, lb), (n, r_, g, b) in sec:
        if toplam and n / toplam < 0.06:
            break
        renk = (r_ // n, g // n, b // n)
        if all(abs(hb - h2) > 1 and abs(hb - h2) < 23 for h2, _ in [k for k, _ in out]):
            out.append(((hb, lb), renk))
        if len(out) == 2:
            break
    def hexle(c):   # kenar yumuşatmasının açtığı rengi toparla: çok açık ya da soluk olmasın
        h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in c))
        l, s = min(l, 0.52), max(s, 0.6)
        return "#%02x%02x%02x" % tuple(round(v * 255) for v in colorsys.hls_to_rgb(h, l, s))
    if not out:
        return ["#2b2f36", None]
    return [hexle(out[0][1]), hexle(out[1][1]) if len(out) > 1 else None]


def renk_hesapla():
    es = json.load(open(ESLESME, encoding="utf-8"))
    out = {}
    for f in sorted(set(es.values())):
        yol = os.path.join(CIKTI, f"{f}.png")
        if os.path.exists(yol):
            out[str(f)] = renkler(yol)
    json.dump(out, open(os.path.join(KOK, "logo_renk.json"), "w", encoding="utf-8"), indent=0)
    print(len(out), "logo rengi -> logo_renk.json")


if __name__ == "__main__":
    {"esle": esle, "kopyala": kopyala, "renk": renk_hesapla}[sys.argv[1]]()

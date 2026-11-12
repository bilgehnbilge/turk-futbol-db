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


if __name__ == "__main__":
    {"esle": esle, "kopyala": kopyala}[sys.argv[1]]()

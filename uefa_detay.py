"""Türk takımlarının Avrupa maçlarının ayrıntısı: UEFA maç servisi (kadro, goller, kartlar, değişiklikler, hakem, stat).

  python3 uefa_detay.py indir   -> raw/uefa_mac/<UEFA maç no>.json.gz  (maç özeti + kadro + olaylar; kaldığı yerden)
  python3 uefa_detay.py ayikla  -> raw/uefa_detay.db (mac, kadro, olay) + bizim maç numarasıyla eşleme

Maç listesi: Türk takımlarının UEFA takım numaralarıyla (raw/uefa_maclar.json'dan) teamId sorgusu.
"""
import collections, datetime, glob, gzip, json, os, re, sqlite3, subprocess, sys, time

KOK = os.path.dirname(os.path.abspath(__file__))
API = "https://match.uefa.com/v5/matches"
UA = "turk-futbol-db/0.1 (kisisel arsiv)"
HAM = os.path.join(KOK, "raw", "uefa_mac")
DB = os.path.join(KOK, "raw", "uefa_detay.db")
YARISMA = {"1", "2", "9", "14", "2019"}   # Şampiyonlar Ligi/Kupası, Kupa Galipleri, Süper Kupa, UEFA Kupası/Avrupa Ligi, Konferans Ligi


def al(url):
    for deneme in range(4):
        r = subprocess.run(["curl", "-sL", "--compressed", "-m", "60", "-A", UA, url], capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except ValueError:
            time.sleep(5 * (deneme + 1))
    return None


def maclar():
    """Türk takımlarının bütün resmi UEFA kulüp maçları (oynanmış)."""
    ue = json.load(open(os.path.join(KOK, "raw", "uefa_maclar.json")))
    takimlar = {m[s] for v in ue.values() for m in v for s, u in (("ev", "ev_ulke"), ("dep", "dep_ulke")) if m[u] == "TUR"}
    out = {}
    for t in sorted(takimlar):
        off = 0
        while True:
            d = al(f"{API}?teamId={t}&limit=100&offset={off}&order=ASC") or []
            for m in d:
                if str(m.get("competition", {}).get("id")) in YARISMA and m.get("status") == "FINISHED":
                    out[m["id"]] = m
            if len(d) < 100:
                break
            off += 100
            time.sleep(0.3)
        time.sleep(0.3)
    return out


def indir():
    os.makedirs(HAM, exist_ok=True)
    ms = maclar()
    print(len(ms), "maç", flush=True)
    yeni = 0
    for i, (mid, m) in enumerate(sorted(ms.items()), 1):
        yol = os.path.join(HAM, f"{mid}.json.gz")
        if os.path.exists(yol):
            continue
        kadro = al(f"{API}/{mid}/lineups")
        olay = al(f"{API}/{mid}/events?filter=LINEUP&offset=0&limit=200")
        if kadro is None or olay is None:
            print("alınamadı", mid, flush=True); continue
        with gzip.open(yol + ".tmp", "wt", encoding="utf-8") as f:
            json.dump({"mac": m, "kadro": kadro, "olay": olay}, f, ensure_ascii=False)
        os.replace(yol + ".tmp", yol)
        yeni += 1
        if i % 100 == 0:
            print(f"  {i}/{len(ms)} {time.strftime('%H:%M')}", flush=True)
        time.sleep(0.4)
    print("Bitti,", yeni, "yeni maç", flush=True)


SEMA = """
CREATE TABLE mac(uefa_id TEXT PRIMARY KEY, mac_id INTEGER, tarih TEXT, yarisma TEXT, tur TEXT, ev TEXT, dep TEXT, ev_uefa TEXT, dep_uefa TEXT,
  ev_gol INTEGER, dep_gol INTEGER, stad TEXT, sehir TEXT, seyirci INTEGER, hakem TEXT, hakem_ulke TEXT);
CREATE TABLE kadro(uefa_id TEXT, taraf INTEGER, oyuncu TEXT, ad TEXT, forma TEXT, ilk11 INTEGER, kaptan INTEGER, dogum TEXT, ulke TEXT, mevki TEXT);
CREATE TABLE teknik(uefa_id TEXT, taraf INTEGER, kisi TEXT, ad TEXT);
CREATE TABLE olay(uefa_id TEXT, taraf INTEGER, tur TEXT, oyuncu TEXT, ad TEXT, dk INTEGER, ek INTEGER, oyuncu2 TEXT, ad2 TEXT, ayrinti TEXT);
CREATE INDEX k1 ON kadro(oyuncu); CREATE INDEX o1 ON olay(oyuncu); CREATE INDEX m1 ON mac(mac_id);
"""


def ayikla():
    if os.path.exists(DB):
        os.remove(DB)
    c = sqlite3.connect(DB)
    c.executescript(SEMA)
    f = sqlite3.connect(os.path.join(KOK, "futbol.db"))
    # bizim kulüp -> UEFA takım no (logo_uefa.json: yabancı rakipler); aynı gün aynı skorlu iki maçı ayırmak için
    lu = json.load(open(os.path.join(KOK, "logo_uefa.json")))
    turk = {r[0] for r in f.execute("SELECT ev_kulup FROM mac WHERE yarisma='lig' UNION SELECT dep_kulup FROM mac WHERE yarisma='lig'")}
    k_uefa = {kid: lu[k][1:] for kid, k in f.execute("SELECT kulup_id, kaynak || ':' || kaynak_id FROM kulup_kimlik") if k in lu and kid not in turk}
    bizim = collections.defaultdict(list)
    import unicodedata
    kel = lambda s: {w[:5] for w in re.sub(r"[^a-z0-9 ]", " ", "".join(c for c in unicodedata.normalize("NFKD", (s or "").replace("ı", "i").lower())
                                                                     if not unicodedata.combining(c))).split() if len(w) >= 3}
    adlar_kel = collections.defaultdict(set)   # Türk kulübünün bütün dönem adlarının kelimeleri
    for kid, ad in f.execute("SELECT kulup_id, ad FROM kulup_adi UNION SELECT id, ad FROM kulup"):
        adlar_kel[kid] |= kel(ad)
    for mid, tarih, eg, dg, ev, dep, eva, depa in f.execute("SELECT id, tarih, ev_gol, dep_gol, ev_kulup, dep_kulup, ev_adi, dep_adi FROM mac WHERE yarisma='avrupa' AND tarih IS NOT NULL"):
        bizim[tarih].append((mid, eg, dg, None if ev in turk else k_uefa.get(ev), None if dep in turk else k_uefa.get(dep),
                             adlar_kel.get(ev) if ev in turk else None, adlar_kel.get(dep) if dep in turk else None))
    en = lambda x: ((x or {}).get("translations") or {}).get("name", {}).get("EN") or (x or {}).get("internationalName")
    say = collections.Counter()
    for yol in sorted(glob.glob(os.path.join(HAM, "*.json.gz"))):
        d = json.load(gzip.open(yol, "rt", encoding="utf-8"))
        m, uid = d["mac"], d["mac"]["id"]
        ev_id, dep_id = m["homeTeam"]["id"], m["awayTeam"]["id"]
        sk = (m.get("score") or {}).get("total") or {}
        t = m["kickOffTime"]["date"]
        gunler = [x for g in (0, -1, 1) for x in bizim.get(str(datetime.date.fromisoformat(t) + datetime.timedelta(days=g)), [])]
        # bizim maçta rakibin UEFA numarası biliniyorsa ve bu maçtaki takımlardan biri değilse: başka maç
        # Türk tarafının adı da tutmalı (aynı gün aynı skorlu iki Türk takımı maçı)
        u_ev, u_dep = kel(m["homeTeam"].get("internationalName")), kel(m["awayTeam"].get("internationalName"))
        uygun = lambda x: all(v is None or v in (ev_id, dep_id) for v in (x[3], x[4])) and ad_tutar(x)
        ad_tutar = lambda x: all(v is None or bool(v & (u_ev | u_dep)) for v in (x[5], x[6]))
        gunler = [x for x in gunler if uygun(x)]
        rakip_tutan = [x for x in gunler if x[3] == ev_id or x[4] == dep_id]
        aday = [x for x in (rakip_tutan or gunler) if (x[1], x[2]) == (sk.get("home"), sk.get("away"))]
        if len(aday) > 1:   # aynı gün aynı skorlu birden çok aday: Türk takımının adına bak
            aday = [x for x in aday if ad_tutar(x)]
        if not aday and len(rakip_tutan) == 1:   # skor farklı yazılmış (uzatma/penaltı) ama rakip ve gün tutuyor
            aday = rakip_tutan
        hakem = next((r for r in m.get("referees") or [] if r.get("role") == "REFEREE"), None)
        c.execute("INSERT INTO mac VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            uid, aday[0][0] if len(aday) == 1 else None, t, m["competition"].get("metaData", {}).get("name"),
            (m.get("round") or {}).get("metaData", {}).get("name"), m["homeTeam"].get("internationalName"), m["awayTeam"].get("internationalName"),
            ev_id, dep_id, sk.get("home"), sk.get("away"),
            ((m.get("stadium") or {}).get("translations") or {}).get("officialName", {}).get("EN"),
            (((m.get("stadium") or {}).get("city") or {}).get("translations") or {}).get("name", {}).get("EN"),
            m.get("matchAttendance"), en((hakem or {}).get("person")), ((hakem or {}).get("person") or {}).get("countryCode")))
        say["eslesen" if len(aday) == 1 else "eslesmeyen"] += 1
        k = d["kadro"] or {}
        for taraf, anahtar in ((1, "homeTeam"), (2, "awayTeam")):
            x = k.get(anahtar) or {}
            for ilk11, bolum in ((1, "field"), (0, "bench")):
                for p in x.get(bolum) or []:
                    pl = p.get("player") or {}
                    c.execute("INSERT INTO kadro VALUES(?,?,?,?,?,?,?,?,?,?)", (uid, taraf, pl.get("id"), pl.get("internationalName"),
                              str(p.get("jerseyNumber") or ""), ilk11, 1 if p.get("isCaptain") else 0, pl.get("birthDate"), pl.get("countryCode"),
                              pl.get("fieldPosition")))
            for co in x.get("coaches") or []:
                pe = co.get("person") or {}
                c.execute("INSERT INTO teknik VALUES(?,?,?,?)", (uid, taraf, pe.get("id"), en(pe)))
        for e in d["olay"] or []:
            pa = (e.get("primaryActor") or {})
            sa = (e.get("secondaryActor") or {})
            taraf = 1 if (pa.get("team") or {}).get("id") == ev_id else 2
            tm = e.get("time") or {}
            c.execute("INSERT INTO olay VALUES(?,?,?,?,?,?,?,?,?,?)", (uid, taraf, e.get("type"), (pa.get("person") or {}).get("id"),
                      (pa.get("person") or {}).get("internationalName"), tm.get("minute"), tm.get("injuryMinute"),
                      (sa.get("person") or {}).get("id"), (sa.get("person") or {}).get("internationalName"), e.get("subType") or e.get("goalType")))
    for (mid,) in c.execute("SELECT mac_id FROM mac WHERE mac_id IS NOT NULL GROUP BY mac_id HAVING COUNT(*) > 1").fetchall():
        c.execute("UPDATE mac SET mac_id=NULL WHERE mac_id=?", (mid,)); say["cakisan"] += 1
    c.commit()
    s = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("mac", "kadro", "teknik", "olay")}
    print(s, dict(say), "olay türleri:", dict(c.execute("SELECT tur, COUNT(*) FROM olay GROUP BY 1").fetchall()))


if __name__ == "__main__":
    {"indir": indir, "ayikla": ayikla}[sys.argv[1]]()

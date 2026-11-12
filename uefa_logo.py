"""Avrupa kupası rakiplerinin logoları: UEFA maç servisi (match.uefa.com) -> docs/logo/u<UEFA takım no>.png

  python3 uefa_logo.py topla    -> raw/uefa_maclar.json (1955'ten bugüne Türk takımlı UEFA maçları; sezon başına bir kez)
  python3 uefa_logo.py esle     -> logo_uefa.json (kulüp kimliği -> "u<no>"; maçları tarih ±1 gün ve skorla eşler)
  python3 uefa_logo.py indir    -> docs/logo/u<no>.png (64 px)

Kapsam: Şampiyon Kulüpler Kupası/Şampiyonlar Ligi (1), Kupa Galipleri Kupası (2), UEFA Kupası/Avrupa Ligi (14),
Konferans Ligi (2019), Süper Kupa (9). Fuar Şehirleri Kupası ve Intertoto UEFA servisinde yok; o rakipler başka
bir UEFA maçında karşılaşılmışsa yine logo alır.
"""
import collections, datetime, json, os, sqlite3, subprocess, sys, time

KOK = os.path.dirname(os.path.abspath(__file__))
API = "https://match.uefa.com/v5/matches"
UA = "turk-futbol-db/0.1 (kisisel arsiv)"
YARISMA = [1, 2, 14, 2019, 9]
HAM = os.path.join(KOK, "raw", "uefa_maclar.json")
CIKTI = os.path.join(KOK, "docs", "logo")


def al(url):
    for deneme in range(4):
        r = subprocess.run(["curl", "-sL", "--compressed", "-m", "60", "-A", UA, url], capture_output=True, text=True)
        try:
            return json.loads(r.stdout or "[]")
        except ValueError:
            time.sleep(5 * (deneme + 1))
    return []


def topla():
    out = json.load(open(HAM)) if os.path.exists(HAM) else {}
    for yil in range(1956, datetime.date.today().year + 2):
        for cid in YARISMA:
            anahtar = f"{yil}-{cid}"
            if anahtar in out and yil < datetime.date.today().year:
                continue
            ms, off = [], 0
            while True:
                d = al(f"{API}?competitionId={cid}&seasonYear={yil}&limit=100&offset={off}&order=ASC")
                if not isinstance(d, list):
                    break
                ms += [{"t": m["kickOffTime"]["date"], "ev": m["homeTeam"].get("id"), "dep": m["awayTeam"].get("id"),
                        "ev_ad": m["homeTeam"].get("internationalName"), "dep_ad": m["awayTeam"].get("internationalName"),
                        "ev_ulke": m["homeTeam"].get("countryCode"), "dep_ulke": m["awayTeam"].get("countryCode"),
                        "eg": ((m.get("score") or {}).get("total") or {}).get("home"), "dg": ((m.get("score") or {}).get("total") or {}).get("away")}
                       for m in d if "TUR" in (m["homeTeam"].get("countryCode"), m["awayTeam"].get("countryCode"))]
                if len(d) < 100:
                    break
                off += 100
                time.sleep(0.3)
            out[anahtar] = ms
            time.sleep(0.3)
        print(yil, sum(len(v) for k, v in out.items() if k.startswith(f"{yil}-")), flush=True)
        json.dump(out, open(HAM, "w"), ensure_ascii=False)


def esle():
    ue = [m for v in json.load(open(HAM)).values() for m in v]
    gun = collections.defaultdict(list)
    for m in ue:
        gun[m["t"]].append(m)
    c = sqlite3.connect(os.path.join(KOK, "futbol.db"))
    kim = {}
    for kid, k in c.execute("SELECT kulup_id, kaynak || ':' || kaynak_id FROM kulup_kimlik ORDER BY kaynak <> 'tff', son_sezon DESC"):
        kim.setdefault(kid, k)
    oy = collections.defaultdict(collections.Counter)   # bizim kulüp -> UEFA no oyları
    ulke = collections.defaultdict(collections.Counter)
    for tarih, ev, dep, eg, dg in c.execute("SELECT tarih, ev_kulup, dep_kulup, ev_gol, dep_gol FROM mac WHERE yarisma='avrupa' AND tarih IS NOT NULL"):
        t = datetime.date.fromisoformat(tarih)
        aday = [m for g in (-1, 0, 1) for m in gun.get(str(t + datetime.timedelta(days=g)), [])]
        tut = [m for m in aday if (m["eg"], m["dg"]) == (eg, dg)] or aday
        if len(tut) != 1:
            tut = [m for m in tut if (m["eg"], m["dg"]) == (eg, dg)]
        if len(tut) == 1:
            m = tut[0]
            if ev is not None and m["ev_ulke"] != "TUR":
                oy[ev][m["ev"]] += 1; ulke[ev][m["ev_ulke"]] += 1
            if dep is not None and m["dep_ulke"] != "TUR":
                oy[dep][m["dep"]] += 1; ulke[dep][m["dep_ulke"]] += 1
    es = {kim[k]: f"u{o.most_common(1)[0][0]}" for k, o in oy.items() if k in kim}
    json.dump(dict(sorted(es.items())), open(os.path.join(KOK, "logo_uefa.json"), "w"), indent=0)
    # rakibin ülkesi (UEFA ülke kodu); elle düzeltme/ekleme: ulke_elle.json
    ul = {kim[k]: u.most_common(1)[0][0] for k, u in ulke.items() if k in kim}
    json.dump(dict(sorted(ul.items())), open(os.path.join(KOK, "kulup_ulke.json"), "w"), indent=0)
    yabanci = c.execute("SELECT COUNT(DISTINCT k) FROM (SELECT ev_kulup k FROM mac WHERE yarisma='avrupa' UNION SELECT dep_kulup FROM mac WHERE yarisma='avrupa')").fetchone()[0]
    print(len(es), "Avrupa rakibi UEFA numarasıyla eşlendi ->", "logo_uefa.json", f"(Avrupa maçı olan {yabanci} kulüpten)")


def indir():
    es = json.load(open(os.path.join(KOK, "logo_uefa.json")))
    os.makedirs(os.path.join(KOK, "raw", "uefa_logo"), exist_ok=True)
    n = 0
    for ad in sorted(set(es.values())):
        hedef = os.path.join(CIKTI, ad + ".png")
        if os.path.exists(hedef):
            continue
        ham = os.path.join(KOK, "raw", "uefa_logo", ad + ".png")
        r = subprocess.run(["curl", "-sL", "-m", "60", "-A", UA, "-o", ham, "-w", "%{http_code}",
                            f"https://img.uefa.com/imgml/TP/teams/logos/100x100/{ad[1:]}.png"], capture_output=True, text=True)
        if r.stdout == "200" and os.path.getsize(ham) > 500:
            subprocess.run(["sips", "-s", "format", "png", "-Z", "64", ham, "--out", hedef], capture_output=True)
            n += 1
        else:
            print("logo yok", ad, r.stdout)
        time.sleep(0.3)
    print(n, "UEFA logosu indirildi")


if __name__ == "__main__":
    {"topla": topla, "esle": esle, "indir": indir}[sys.argv[1]]()

#!/usr/bin/env python3
"""UEFA kulüp kupalarının bütün maçları (Türk takımı olsun olmasın): Avrupa Elo'su ve lig gücü karşılaştırmaları için.

  python3 uefa_tum.py indir    -> raw/uefa_tum.json.gz  (yarışma-sezon başına maç listesi; biten geçmiş sezonlar bir kez)
  python3 uefa_tum.py ozet     -> sayılar

Kaynak: match.uefa.com/v5/matches (uefa_logo.py ile aynı servis). Yarışmalar: Şampiyon Kulüpler Kupası/Şampiyonlar Ligi (1),
Kupa Galipleri Kupası (2), UEFA Kupası/Avrupa Ligi (14), Konferans Ligi (2019), Süper Kupa (9).
Fuar Şehirleri Kupası ve Intertoto UEFA servisinde yok.
"""
import collections, datetime, gzip, json, os, sys, time

from uefa_logo import al, API, YARISMA

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "uefa_tum.json.gz")
BEKLE = 0.5


def sade(m):
    sk = m.get("score") or {}
    t = lambda k: [sk[k].get("home"), sk[k].get("away")] if sk.get(k) else None
    ko = m.get("kickOffTime") or {}
    takim = lambda x: {"id": x.get("id"), "ad": x.get("internationalName"), "ulke": x.get("countryCode"),
                       "ulke_ad": ((x.get("translations") or {}).get("countryName") or {}).get("EN")}
    return {"id": m.get("id"), "yarisma": (m.get("competition") or {}).get("id"), "sezon": m.get("seasonYear"),
            "tur": ((m.get("round") or {}).get("metaData") or {}).get("name"), "asama": (m.get("round") or {}).get("phase"),
            "tip": m.get("type"), "ayak": (m.get("leg") or {}).get("number"), "tarih": ko.get("date") or (ko.get("dateTime") or "")[:10] or None,
            "saat": ko.get("dateTime"), "durum": m.get("status"), "ev": takim(m.get("homeTeam") or {}), "dep": takim(m.get("awayTeam") or {}),
            "skor": t("total"), "skor90": t("regular"), "pen": t("penalty"), "kazanan": ((m.get("winner") or {}).get("match") or {}).get("team", {}).get("id")
            if isinstance((m.get("winner") or {}).get("match"), dict) else None,
            "tarafsiz": (m.get("stadium") or {}).get("countryCode") not in (None, (m.get("homeTeam") or {}).get("countryCode"))}


def indir():
    out = json.load(gzip.open(HAM, "rt", encoding="utf-8")) if os.path.exists(HAM) else {}
    bu_yil = datetime.date.today().year
    for yil in range(1955, bu_yil + 2):
        for cid in YARISMA:
            anahtar = f"{yil}-{cid}"
            if anahtar in out and yil < bu_yil - 1:
                continue
            ms, off = [], 0
            while True:
                d = al(f"{API}?competitionId={cid}&seasonYear={yil}&limit=100&offset={off}&order=ASC")
                if not isinstance(d, list):
                    break
                ms += [sade(m) for m in d]
                if len(d) < 100:
                    break
                off += 100
                time.sleep(BEKLE)
            out[anahtar] = ms
            time.sleep(BEKLE)
        print(yil, sum(len(v) for k, v in out.items() if k.startswith(f"{yil}-")), flush=True)
        with gzip.open(HAM + ".tmp", "wt", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
        os.replace(HAM + ".tmp", HAM)
    ozet()


def ozet():
    out = json.load(gzip.open(HAM, "rt", encoding="utf-8"))
    ms = [m for v in out.values() for m in v]
    tek = {m["id"]: m for m in ms}
    print(f"{len(tek)} maç ({len(ms)} kayıt), {len({m['ev']['id'] for m in tek.values()} | {m['dep']['id'] for m in tek.values()})} kulüp")
    print("durum:", collections.Counter(m["durum"] for m in tek.values()).most_common())
    print("yarışma:", collections.Counter(m["yarisma"] for m in tek.values()).most_common())
    print("tarihsiz:", sum(1 for m in tek.values() if not m["tarih"]), "skorsuz biten:", sum(1 for m in tek.values() if m["durum"] == "FINISHED" and not m["skor"]))
    on = collections.Counter((m["tarih"] or "????")[:3] + "0" for m in tek.values())
    print("on yıllara göre:", sorted(on.items()))
    ulke = collections.Counter(u for m in tek.values() for u in (m["ev"]["ulke"], m["dep"]["ulke"]))
    print("ülke sayısı:", len(ulke), ulke.most_common(8))


if __name__ == "__main__":
    {"indir": indir, "ozet": ozet}[sys.argv[1] if len(sys.argv) > 1 else "ozet"]()

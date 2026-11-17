#!/usr/bin/env python3
"""Türk kadın kulüplerinin UEFA maçları (Kadınlar Şampiyonlar Ligi / UEFA Kadınlar Kupası, Kadınlar Avrupa Kupası):
UEFA maç servisi (match.uefa.com, erkek Avrupa maçlarıyla aynı).

  python3 kadin_avrupa.py indir   # raw/uefa_kadin/maclar.json + raw/uefa_kadin/mac/<UEFA maç no>.json.gz (kadro + olaylar)

Türk takımları önce Kadınlar Şampiyonlar Ligi sezonlarından (competitionId=28, 2001-02'den) bulunur; sonra her takımın
bütün UEFA maçları takım numarasıyla alınır (böylece başka kadın kupaları da gelir).
"""
import gzip, json, os, sys, time

import uefa_detay as U

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "uefa_kadin")
UWCL = 28


def indir():
    os.makedirs(os.path.join(HAM, "mac"), exist_ok=True)
    takim = {}
    for yil in range(2002, 2028):
        off = 0
        while True:
            d = U.al(f"{U.API}?competitionId={UWCL}&seasonYear={yil}&limit=100&offset={off}&order=ASC") or []
            for m in d:
                for s in ("homeTeam", "awayTeam"):
                    if m[s].get("countryCode") == "TUR":
                        takim[m[s]["id"]] = m[s].get("internationalName")
            if len(d) < 100:
                break
            off += 100
            time.sleep(0.3)
        time.sleep(0.3)
    print(len(takim), "Türk kadın takımı:", sorted(takim.values()), flush=True)
    maclar = {}
    for t in sorted(takim):
        off = 0
        while True:
            d = U.al(f"{U.API}?teamId={t}&limit=100&offset={off}&order=ASC") or []
            for m in d:
                if m.get("status") == "FINISHED":
                    maclar[m["id"]] = m
            if len(d) < 100:
                break
            off += 100
            time.sleep(0.3)
        time.sleep(0.3)
    json.dump(maclar, open(os.path.join(HAM, "maclar.json"), "w", encoding="utf-8"), ensure_ascii=False)
    yar = {}
    for m in maclar.values():
        k = m.get("competition", {}).get("metaData", {}).get("name") or m.get("competition", {}).get("id")
        yar[k] = yar.get(k, 0) + 1
    print(len(maclar), "maç:", yar, flush=True)
    yeni = 0
    for mid in sorted(maclar):
        yol = os.path.join(HAM, "mac", f"{mid}.json.gz")
        if os.path.exists(yol):
            continue
        kadro = U.al(f"{U.API}/{mid}/lineups")
        olay = U.al(f"{U.API}/{mid}/events?filter=LINEUP&offset=0&limit=200")
        if kadro is None or olay is None:
            print("  alınamadı:", mid, flush=True); continue
        with gzip.open(yol, "wt", encoding="utf-8") as g:
            json.dump({"mac": maclar[mid], "kadro": kadro, "olay": olay}, g, ensure_ascii=False)
        yeni += 1
        time.sleep(0.5)
    print("Bitti, yeni maç ayrıntısı:", yeni, flush=True)


if __name__ == "__main__":
    {"indir": indir}[sys.argv[1]]()

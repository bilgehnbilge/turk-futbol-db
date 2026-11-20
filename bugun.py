#!/usr/bin/env python3
"""Ana sayfa "Bugün tarihte" bölümü: docs/data/bugun.json (web_aktar.py sezon dosyalarını yazdıktan sonra çağırır).
Yalnız lig (L) ve Türkiye Kupası (K) maçları; Avrupa ve Milli Takım maçlarını istemci avrupa.json / milli.json'dan kendisi alıyor.

Biçim:
{
  "alanlar": ["id","tarih","yarisma","kademe","tur","ev_id","dep_id","ev_gol","dep_gol","ev_pen","dep_pen","durum","neden"],
  "gun": { "11-18": [[...], ...], ... }      # her gün en çok 6 maç, önem sırasıyla
}
neden: "final" (kupa finali), "yari" (kupa yarı finali), "derbi" (en üst ligde büyük dört arasında),
       "fark" (farklı skor), "gol" (çok gollü maç)

Tek başına: python3 bugun.py <docs/data/sezon klasörü> <çıktı.json>
"""
import json, glob, os, sys, collections

BUYUK = {95, 115, 463, 846}   # Beşiktaş, Trabzonspor, Fenerbahçe, Galatasaray
GUNDE = 6


def neden_puan(r):
    _id, tarih, yar, lig, kademe, tur, po, ev, _e, dep, _d, eg, dg, ep, dp, durum, _not = r[:17]
    if eg is None or dg is None or not tarih:
        return None
    tur = tur or ""
    fark, top = abs(eg - dg), eg + dg
    if yar == "K":
        if "Final" in tur and "Yarı" not in tur and "Çeyrek" not in tur and "finaller" not in tur:
            return "final", 100 + top
        if "Yarı" in tur:
            return "yari", 40 + top
        if ev in BUYUK and dep in BUYUK:
            return "derbi", 45 + fark * 4 + top
        return None
    if yar != "L":
        return None
    if kademe == 1 and ev in BUYUK and dep in BUYUK:
        return "derbi", 60 + fark * 5 + top
    if kademe == 1 and fark >= 5:
        return "fark", 30 + fark * 4
    if kademe == 1 and top >= 8:
        return "gol", 28 + top
    if fark >= 9:   # alt liglerde rekor sayılabilecek skorlar
        return "fark", 15 + fark * 2
    return None


def main(klasor, cikti):
    gun = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(klasor, "*.json"))):
        for r in json.load(open(f, encoding="utf-8"))["maclar"]:
            if r[15] in ("Hük.", "Çifte H") or r[6] == "x":   # hükmen ve sayılmayan maçlar dışarıda
                continue
            np = neden_puan(r)
            if not np:
                continue
            neden, puan = np
            gun[r[1][5:10]].append((puan, [r[0], r[1], r[2], r[4], r[5], r[7], r[9], r[11], r[12], r[13], r[14], r[15], neden]))
    cik = {}
    for g, l in sorted(gun.items()):
        l.sort(key=lambda x: (-x[0], x[1][1]))
        secilen, derbi = [], 0
        for _p, row in l:   # çeşitlilik: günde en çok 3 derbi
            if row[-1] == "derbi":
                if derbi >= 3:
                    continue
                derbi += 1
            secilen.append(row)
            if len(secilen) >= GUNDE:
                break
        cik[g] = secilen
    json.dump({"alanlar": ["id", "tarih", "yarisma", "kademe", "tur", "ev_id", "dep_id", "ev_gol", "dep_gol", "ev_pen", "dep_pen", "durum", "neden"],
               "gun": cik}, open(cikti, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(len(cik), "gün,", sum(map(len, cik.values())), "maç,", os.path.getsize(cikti), "bayt")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

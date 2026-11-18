"""Sezon özetleri: docs/sezon_ozet.json (Sezonlar sayfasındaki sezon kartları ve sezon sayfasının özet şeridi için).

docs/data/sezon/*.json (web_aktar.py üretir) ve docs/sampiyonlar.json'dan hesaplanır; data/ klasörüne yazmaz.
web_aktar.py'den sonra çalıştırılmalı:  python3 sezon_ozet.py

Her sezon için:
  sampiyon  Süper Lig şampiyonu (sampiyonlar.json; yoksa — süren sezon — None)
  lider     süren sezonda Süper Lig'in o anki lideri (tek gruplu ise)
  kupa      Türkiye Kupası galibi (final maç(lar)ı: toplam skor, eşitse son maçın penaltıları)
  sl        Süper Lig: [takım, maç, gol]
  mac       sezondaki bütün maçlar
  k         kademe -> {"c": bir üst lige çıkanlar, "d": bir alt lige düşenler, "a": sonraki sezon profesyonel liglerde
            olmayanlar}; bir sonraki sezonun lig üyeliğinden çıkarılır (play-off, ihraç, çekilme ayırt edilmez)
"""
import json
import re
from pathlib import Path

KOK = Path(__file__).resolve().parent / "docs"
FINAL = re.compile(r"(^|\s)final", re.I)
ARA = re.compile(r"yar[ıi]|çeyrek|ceyrek|son 16", re.I)


def puan(sezon):
    return 3 if int(sezon[:4]) >= 1987 else 2


def kademeler(maclar):
    """Normal sezon lig maçlarından kulüp -> kademe (en üst)."""
    k = {}
    for m in maclar:
        if m[2] != "L" or m[6] in ("p", "x") or m[4] is None:
            continue
        for t in (m[7], m[9]):
            if t is not None:
                k[t] = min(k.get(t, 99), m[4])
    return k


def kupa_galibi(maclar):
    fin = [m for m in maclar if m[2] == "K" and FINAL.search(m[5] or "") and not ARA.search(m[5] or "") and m[11] is not None]
    if not fin:
        return None
    fin.sort(key=lambda m: m[1] or "")
    cift = {fin[-1][7], fin[-1][9]}
    fin = [m for m in fin if {m[7], m[9]} == cift]
    gol = {}
    for m in fin:
        gol[m[7]] = gol.get(m[7], 0) + m[11]
        gol[m[9]] = gol.get(m[9], 0) + m[12]
    (a, ga), (b, gb) = list(gol.items()) if len(gol) == 2 else (list(gol.items()) + [(None, -1)])[:2]
    if ga != gb:
        return a if ga > gb else b
    s = fin[-1]
    if s[13] is None:
        return None
    return s[7] if s[13] > s[14] else s[9]


def lider(maclar, sezon):
    t = {}
    for m in maclar:
        if m[2] != "L" or m[4] != 1 or m[6] in ("p", "x") or m[11] is None:
            continue
        if m[5]:
            return None   # gruplu: tek lider yok
        for a, b, ga, gb in ((m[7], m[9], m[11], m[12]), (m[9], m[7], m[12], m[11])):
            x = t.setdefault(a, [0, 0, 0])
            x[0] += puan(sezon) if ga > gb else 1 if ga == gb else 0
            x[1] += ga - gb
            x[2] += ga
    return max(t, key=lambda k: t[k]) if t else None


def main():
    ozet = json.loads((KOK / "data/ozet.json").read_text())
    sampiyon = json.loads((KOK / "sampiyonlar.json").read_text())["sampiyon"]
    sezonlar = ozet["sezonlar"]
    veri = {s: json.loads((KOK / f"data/sezon/{s}.json").read_text())["maclar"] for s in sezonlar}
    kd = {s: kademeler(veri[s]) for s in sezonlar}
    cikti = {}
    for i, s in enumerate(sezonlar):
        ms = veri[s]
        sl = [m for m in ms if m[2] == "L" and m[4] == 1 and m[6] not in ("p", "x")]
        oynanan = [m for m in sl if m[11] is not None]
        o = {
            "sampiyon": sampiyon.get(s),
            "kupa": kupa_galibi(ms),
            "sl": [len({t for m in sl for t in (m[7], m[9])}), len(oynanan), sum(m[11] + m[12] for m in oynanan)],
            "mac": len(ms),
        }
        if o["sampiyon"] is None and i == len(sezonlar) - 1:
            o["lider"] = lider(ms, s)
        sonraki = sezonlar[i + 1] if i + 1 < len(sezonlar) else None
        if sonraki and kd[s] and kd[sonraki]:
            k = {}
            for t, a in kd[s].items():
                b = kd[sonraki].get(t)
                yon = "a" if b is None else "c" if b < a else "d" if b > a else None
                if yon:
                    k.setdefault(str(a), {"c": [], "d": [], "a": []})[yon].append(t)
            o["k"] = k
        cikti[s] = o
    hedef = KOK / "sezon_ozet.json"
    hedef.write_text(json.dumps({"surum": ozet.get("surum"), "sezon": cikti}, ensure_ascii=False, separators=(",", ":")))
    print(hedef, hedef.stat().st_size, "bayt,", len(cikti), "sezon")


if __name__ == "__main__":
    main()

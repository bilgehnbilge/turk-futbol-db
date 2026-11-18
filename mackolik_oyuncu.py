#!/usr/bin/env python3
"""Maçkolik arşivinin 1959-1991 Süper Lig maç kadroları ve olayları (mackolik_kadro.py, raw/mackolik_kadro) -> TFF oyuncu
verisine (tff_detay.py) katılır: maç sayfalarında kadro, oyuncu sayfalarında maç/gol/kart, kulüp istatistikleri.

  python3 mackolik_oyuncu.py      # ağa çıkmadan: kaç maç ve oyuncu bağlandı (deneme)

Bağlama:
  * Arşiv maçı -> futbol.db maçı: sezonun maç listesindeki (fikstur) tarih ve iki arşiv takım no'su; takım no -> kulüp
    kulup_kimlik'ten (mackolik_arsiv) ve raw/mackolik_td/takim_no.json'dan. futbol.db'de bu maçların kaynağı TFF'nin
    skor sayfaları; ayrıntıları TFF maç no'suyla (tff_detay'deki gibi) yazılır.
  * Arşiv oyuncusu -> TFF kişisi: 1990-91'de iki kaynakta da olan maçlarda aynı takımda ad benzerliği (oyunculuk boyunca
    çoğunluk). TFF'de karşılığı olmayan (1990 öncesi bırakmış) oyuncu 'MK + arşiv oyuncu no' numarasını alır.
  * TFF'de kadrosu olan maçlarda (1990-91) TFF kadrosu kalır; golü yoksa arşivin golleri, kartları, değişiklikleri eklenir.
Olay kodları: 1 gol (d: 1 normal, 2 penaltı, 3 kendi kalesine — bu durumda olay yararlanan takımda yazılı),
2 sarı kart, 3 kırmızı (d: 1 doğrudan, 2 ikinci sarıdan), 4 değişiklik (oyuncu giren, d çıkan).
"""
import collections, datetime, glob, json, os, sqlite3

import mackolik as M
from oyuncu_bag import ad_puani

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "mackolik_kadro")
MK = 90_000_000   # TFF'de karşılığı olmayan arşiv oyuncusu: MK + arşiv oyuncu no (TFF kişi no'ları 3 milyonun altında)


def arsiv_maclari():
    """{arşiv maç no: (sezon, tarih, ev arşiv takım no, dep arşiv takım no)} (kadrosu inmiş maçlar)"""
    out = {}
    for klasor in glob.glob(os.path.join(HAM, "fikstur", "*")):
        sezon = os.path.basename(klasor)
        y1, y2 = int(sezon[:4]), int(sezon[5:9])
        for f in glob.glob(os.path.join(klasor, "g*_h*.txt")):
            if f.endswith("_haftalar.txt"):
                continue
            for x in M.js_dizi(open(f, encoding="utf-8").read()):
                try:
                    g, a = (int(v) for v in x[1].split("/"))
                except (ValueError, AttributeError):
                    continue
                out[str(x[0])] = (sezon, f"{y1 if a >= 7 else y2}-{a:02d}-{g:02d}", str(x[3]), str(x[5]))
    return out


def takim_kulup(c):
    """arşiv takım no -> {kulüp}"""
    out = collections.defaultdict(set)
    for k, a in c.execute("SELECT kulup_id, kaynak_id FROM kulup_kimlik WHERE kaynak='mackolik_arsiv'"):
        out[a.split("-")[0]].add(k)
    y = os.path.join(KOK, "raw", "mackolik_td", "takim_no.json")
    if os.path.exists(y):
        for k, a in json.load(open(y, encoding="utf-8")).items():
            out[str(a)].add(int(k))
    return out


def yukle(maclar, bag, c):
    """futbol.db maçlarına bağlanan arşiv maçları: {TFF maç no: (ters mi, arşiv JSON)}; ters: arşivin ev sahibi futbol.db'de
    deplasman."""
    tk = takim_kulup(c)
    aday = collections.defaultdict(list)
    for m in maclar:
        if m["kademe"] == 1 and m["yarisma"] == "lig" and m["id"] in bag and m["tarih"]:
            aday[(m["sezon"], m["tarih"])].append(m)
    out, say = {}, collections.Counter()
    for mid, (sezon, tarih, ev, dep) in arsiv_maclari().items():
        y = os.path.join(HAM, "mac", mid[-2:].zfill(2), f"{mid}.json")
        if not os.path.exists(y):
            continue
        g = datetime.date.fromisoformat(tarih)
        bul = []
        for d in (0, -1, 1):
            for m in aday.get((sezon, (g + datetime.timedelta(d)).isoformat()), []):
                if m["ev_kulup"] in tk[ev] and m["dep_kulup"] in tk[dep]:
                    bul.append((m, 0))
                elif m["ev_kulup"] in tk[dep] and m["dep_kulup"] in tk[ev]:
                    bul.append((m, 1))
            if bul:
                break
        if len(bul) != 1:
            say["bağlanamadı" if not bul else "birden çok aday"] += 1
            continue
        m, ters = bul[0]
        t, t_ters = bag[m["id"]]
        out[t] = (ters ^ t_ters, json.load(open(y, encoding="utf-8")))
        say["bağlandı"] += 1
    return out, say


def kisi_esle(ar, kadro, ad):
    """1990-91: aynı maç ve taraftaki ad benzerliğiyle arşiv oyuncu no -> TFF kişi no (çoğunluk oyu)."""
    oy = collections.defaultdict(collections.Counter)
    for t, (ters, d) in ar.items():
        if t not in kadro:
            continue
        for i, l in enumerate((d["h"], d["a"])):
            tl = kadro[t][i ^ ters]
            for pid, a, _ in l:
                p = sorted(((ad_puani(a, ad.get(k, "")), k) for _, k, _ in tl), reverse=True)
                if p and p[0][0] >= 0.5 and (len(p) == 1 or p[0][0] - p[1][0] >= 0.2):
                    oy[pid][p[0][1]] += 1
    return {pid: c.most_common(1)[0][0] for pid, c in oy.items()}


def kat(ar, es, kadro, olay, ad, ilk_sira, ilk_say, bas_say):
    """Arşiv maçlarını tff_detay.maclari_yaz'ın tablolarına ekle. Dönen: (kadrosu arşivden gelen, yalnız olayları arşivden
    gelen) TFF maç no kümeleri."""
    kisi = lambda pid: es.get(pid) or MK + pid
    kaynak, olay_kaynak = set(), set()
    for t, (ters, d) in ar.items():
        yan = lambda i: (i - 1) ^ ters   # arşiv tarafı (1/2) -> futbol.db tarafı (0/1)
        if t not in kadro or not any(kadro[t]):
            kaynak.add(t)
            k = ([], [])
            # oyuna sonradan girenler ilk 11 değil (bazı maçlarda arşiv kadrosu eksik: giren oyuncu ilk 11 sırasında yazılı)
            giren = {e[2] for e in d.get("e", []) if e[4] == 4}
            for i, l in ((1, d["h"]), (2, d["a"])):
                for j, (pid, a, _) in enumerate(l):
                    if not pid:
                        continue
                    ilk11 = 1 if j < 11 and pid not in giren else 0
                    k[yan(i)].append(["", kisi(pid), ilk11])
                    ad.setdefault(kisi(pid), a)
                    if ilk11:
                        bas_say[kisi(pid)] += 1
                        if (t, yan(i) + 1) not in ilk_sira:
                            ilk_sira[(t, yan(i) + 1)] = kisi(pid)
                            ilk_say[kisi(pid)] += 1
            kadro[t] = k
        elif any(x[1] == "G" for x in olay.get(t, [])):
            continue   # TFF'nin kendi golleri var
        else:
            olay[t] = []
            olay_kaynak.add(t)
        for e in d.get("e", []):
            taraf, dk, pid, a, tur, ek = e[0], e[1], e[2], e[3], e[4], e[5] or {}
            if not pid:
                continue
            ad.setdefault(kisi(pid), a)
            tr = yan(taraf) + 1
            if tur == 1:
                if ek.get("d") == 3:   # kendi kalesine: olay yararlanan takımda, oyuncu öbür takımda
                    olay[t].append([3 - tr, "G", dk, 0, kisi(pid), None, "K"])
                else:
                    olay[t].append([tr, "G", dk, 0, kisi(pid), None, "P" if ek.get("d") == 2 else None])
            elif tur == 2:
                olay[t].append([tr, "Y", dk, 0, kisi(pid), None, None])
            elif tur == 3:
                olay[t].append([tr, "YR" if ek.get("d") == 2 else "R", dk, 0, kisi(pid), None, None])
            elif tur == 4 and ek.get("d"):
                olay[t].append([tr, "S", dk, 0, kisi(ek["d"]), kisi(pid), None])
                ad.setdefault(kisi(ek["d"]), ek.get("sub"))
    return kaynak, olay_kaynak


if __name__ == "__main__":
    c = sqlite3.connect(os.path.join(KOK, "futbol.db")); c.row_factory = sqlite3.Row
    maclar = [dict(r) for r in c.execute("SELECT * FROM mac")]
    bag = {m["id"]: (int(m["kaynak_id"]), 0) for m in maclar if m["kaynak"] == "tff" and m["kaynak_id"] and m["ev_gol"] is not None}
    ar, say = yukle(maclar, bag, c)
    sz = {int(m["kaynak_id"]): m["sezon"] for m in maclar if m["kaynak"] == "tff" and m["kaynak_id"]}
    print(dict(say), dict(sorted(collections.Counter(sz[t] for t in ar).items())))

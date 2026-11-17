#!/usr/bin/env python3
"""Sitedeki maç bağlantıları doğru maça mı gidiyor? docs/data'daki her ayrıntı kaynağı, bağlandığı maçla karşılaştırılır.

  python3 baglanti_denetle.py

Bir maç sayfası (#/mac/<no>) üç kaynaktan çizilir: UEFA (data/mac/<no>.json), TFF (data/tff/dizin.json -> data/tff/m/),
Maçkolik (data/mk/dizin.json -> data/mk/m/); kadın bölümünde data/kadin/tff/. Her birinde ayrıntı dosyasındaki tarih ve
iki kulüp, kulüp/sezon dosyalarındaki maçla (aynı numara) tutmalı. Ayrıca app.js'teki #/mac yönlendirmeleri listelenir.
"""
import collections, datetime, glob, json, os, re

KOK = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(KOK, "docs", "data")


def yukle(y):
    return json.load(open(y, encoding="utf-8"))


def maclar(kok):
    """sezon dosyalarından (erkek) ya da kulüp dosyalarından (kadın): no -> (tarih, ev, dep)"""
    out = {}
    if os.path.isdir(os.path.join(kok, "sezon")):
        for f in glob.glob(os.path.join(kok, "sezon", "*.json")):
            for r in yukle(f)["maclar"]:
                out[r[0]] = (r[1], r[7], r[9])
    else:
        for f in glob.glob(os.path.join(kok, "kulup", "*.json")):
            kid = int(os.path.basename(f)[:-5])
            for r in yukle(f)["maclar"]:
                ev, dep = (kid, r[10]) if r[8] == "E" else (r[10], kid)
                out[r[0]] = (r[1], ev, dep)
    return out


def yakin(a, b):
    if not a or not b:
        return a == b
    return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days) <= 1


def geri(l):
    t, out = 0, []
    for x in l:
        t += x; out.append(t)
    return out


def denetle(ad, kok, M):
    sorun = collections.Counter(); ornek = []
    def kontrol(kaynak, no, tarih, ev, dep, ters=False):
        m = M.get(no)
        if m is None:
            sorun[f"{kaynak}: sitede böyle maç yok"] += 1; ornek.append((kaynak, no, tarih, ev, dep, None)); return
        e, d = (dep, ev) if ters else (ev, dep)
        if not yakin(m[0], tarih) or {e, d} != {m[1], m[2]}:
            sorun[f"{kaynak}: başka maç"] += 1; ornek.append((kaynak, no, tarih, e, d, m))
        else:
            sorun[f"{kaynak}: doğru"] += 1
    # UEFA
    if os.path.isdir(os.path.join(kok, "mac")):
        for f in glob.glob(os.path.join(kok, "mac", "*.json")):
            x = yukle(f)
            kontrol("UEFA", x["id"], x["tarih"], x["ev"][0], x["dep"][0])
    # TFF
    dz = os.path.join(kok, "tff", "dizin.json")
    if os.path.exists(dz):
        d = yukle(dz)
        fl, tl, ters = geri(d["f"]), geri(d["t"]), set(d.get("ters", []))
        kova = {}
        for f_, t_ in zip(fl, tl):
            b = t_ // 250
            if b not in kova:
                y = os.path.join(kok, "tff", "m", f"{b}.json")
                kova[b] = yukle(y)["mac"] if os.path.exists(y) else {}
            r = kova[b].get(str(t_))
            if not r:
                sorun["TFF: ayrıntı dosyası yok"] += 1; continue
            kontrol("TFF", f_, r["m"][0], r["m"][5][0], r["m"][6][0], f_ in ters)
    # Maçkolik
    dz = os.path.join(kok, "mk", "dizin.json")
    if os.path.exists(dz):
        kova = {}
        for f_, no in yukle(dz).items():
            b = no[:2]
            if b not in kova:
                kova[b] = yukle(os.path.join(kok, "mk", "m", f"{b}.json"))
            r = kova[b].get(no)
            if not r:
                sorun["Maçkolik: ayrıntı dosyası yok"] += 1; continue
            kontrol("Maçkolik", int(f_), r["m"][0], r["m"][5][0], r["m"][6][0])
    print(f"== {ad}")
    for k, v in sorted(sorun.items()):
        print(f"  {k}: {v}")
    for o in ornek[:8]:
        print("   ", o)
    return sum(v for k, v in sorun.items() if not k.endswith("doğru"))


def main():
    hata = denetle("Erkek", D, maclar(D))
    hata += denetle("Kadın", os.path.join(D, "kadin"), maclar(os.path.join(D, "kadin")))
    # app.js / kadin.js'teki #/mac yönlendirmeleri
    for f in ("app.js", "kadin.js", "milli.js", "grafik.js"):
        t = open(os.path.join(KOK, "docs", f), encoding="utf-8").read()
        for m in re.finditer(r"location\.replace\(`([^`]*)`\)", t):
            if "/mac/" in m.group(1):
                print(f"  UYARI: {f} maç bağlantısını yönlendiriyor: {m.group(1)}"); hata += 1
    print("Sorun:", hata)


if __name__ == "__main__":
    main()

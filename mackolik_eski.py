#!/usr/bin/env python3
"""1959 öncesi lig maçları: Maçkolik arşivinin (arsiv.mackolik.com) hafta hafta maç listeleri (skorlarıyla).

Arşivde 1904-05'ten itibaren İstanbul ligleri (Futbol Birliği Ligi, Cuma Ligi, İstanbul Ligi, Profesyonel Lig ve 2. Lig),
Millî Küme (Maarif Mükâfatı, Millî Eğitim Kupası adlarıyla) ve 1955-59 Ankara / İzmir profesyonel ligleri var
(sezon listeleri: raw/mackolik_arsiv/sezonlar/<sezon>.txt). Maç sayfalarının kadro adresi bu dönem için HTTP 500 veriyor;
golcüler başka kaynaklardan (Vikipedi) gelir.

  python3 mackolik_eski.py say      # ağa çıkmadan: hangi sezonların listesi indi
  python3 mackolik_eski.py indir    # yarıda kalırsa aynı komut kaldığı yerden sürer (istekler arası 40 sn)

Sonuç: raw/mackolik_kadro/fikstur/<sezon>/ (mackolik_kadro.py ile aynı yer ve biçim).
"""
import os, sys, time

import mackolik as M
import mackolik_kadro as K


def sezonlar():
    out = []
    for f in sorted(os.listdir(os.path.join(M.ARSIV_HAM, "sezonlar"))):
        e = f[:-4]
        if e[:4] < "1959" and e != "1959":
            gr = [(str(s), a) for s, a in M.arsiv_lig_listesi(e) or []]
            if gr:
                out.append((e, gr))
    return out


def indir():
    for e, gr in sezonlar():
        print(f"{e}: {', '.join(a for _, a in gr)} {time.strftime('%H:%M')}", flush=True)
        M.arsiv_gruplari_indir(os.path.join(K.FIKSTUR, e), gr)
        print(f"  {len(K.sezon_maclari(e, gr))} bitmiş maç", flush=True)
    print("Bitti.", flush=True)


def say():
    top = 0
    for e, gr in sezonlar():
        n = len(K.sezon_maclari(e, gr)); top += n
        print(f"{e}: {n} maç ({', '.join(a for _, a in gr)})")
    print("toplam:", top)


if __name__ == "__main__":
    {"indir": indir, "say": say}[sys.argv[1]]()

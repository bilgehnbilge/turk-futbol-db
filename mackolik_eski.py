#!/usr/bin/env python3
"""1959 öncesi lig maçları: Maçkolik arşivinin (arsiv.mackolik.com) hafta hafta maç listeleri (skorlarıyla).

Arşivde 1904-05'ten itibaren İstanbul ligleri (Futbol Birliği Ligi, Cuma Ligi, İstanbul Ligi, Profesyonel Lig ve 2. Lig),
Millî Küme (Maarif Mükâfatı, Millî Eğitim Kupası adlarıyla) ve 1955-59 Ankara / İzmir profesyonel ligleri var
(sezon listeleri: raw/mackolik_arsiv/sezonlar/<sezon>.txt). Maç sayfalarının kadro adresi bu dönem için HTTP 500 veriyor;
Millî Küme ve profesyonel liglerde ise kadro ve goller var (2026-11-19, 1938 Galatasaray 0-7 Güneş).

  python3 mackolik_eski.py say      # ağa çıkmadan: hangi sezonların listesi indi
  python3 mackolik_eski.py indir    # yarıda kalırsa aynı komut kaldığı yerden sürer (istekler arası 40 sn)
  python3 mackolik_eski.py kadro    # maç kadroları ve olayları (goller): her lig-sezonda önce ilk 3 maç denenir,
                                    # hiçbiri gelmezse (İstanbul Ligi'nin eski sezonlarında HTTP 500) o lig-sezon atlanır

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


def kadro():
    import json, random
    atlanan = os.path.join(K.HAM, "eski_kadrosuz.json")   # kadro sayfası olmayan lig-sezonlar (yeniden denenmez)
    yok = set(json.load(open(atlanan))) if os.path.exists(atlanan) else set()
    for e, gr in sorted(sezonlar(), reverse=True):   # yeniden eskiye: profesyonel ligler, sonra Millî Küme
        for s, ad in gr:
            if f"{e}|{s}" in yok:
                continue
            ms = K.sezon_maclari(e, [(s, ad)])
            eksik = [m for m in ms if not os.path.exists(K.mac_yol(m[0]))]
            if not eksik:
                continue
            var_ = sum(os.path.exists(K.mac_yol(m[0])) for m in ms)
            print(f"{e} {ad}: {len(ms)} maç, {len(eksik)} indirilecek {time.strftime('%H:%M')}", flush=True)
            ok = 0
            for i, (mid, mad) in enumerate(eksik, 1):
                ok += K.mac_indir(mid, mad)
                time.sleep(K.BEKLE + random.uniform(0, 5))
                if i == 3 and not ok and not var_:
                    print(f"  ilk 3 maçın kadrosu yok, {e} {ad} atlanıyor", flush=True)
                    yok.add(f"{e}|{s}")
                    json.dump(sorted(yok), open(atlanan, "w"))
                    break
                if i % 50 == 0:
                    print(f"  {i}/{len(eksik)} {time.strftime('%H:%M')}", flush=True)
    print("Bitti.", flush=True)


def say():
    top = 0
    for e, gr in sezonlar():
        n = len(K.sezon_maclari(e, gr)); top += n
        print(f"{e}: {n} maç ({', '.join(a for _, a in gr)})")
    print("toplam:", top)


if __name__ == "__main__":
    {"indir": indir, "say": say, "kadro": kadro}[sys.argv[1]]()

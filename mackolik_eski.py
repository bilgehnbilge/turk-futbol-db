#!/usr/bin/env python3
"""1959 öncesi lig maçları: Maçkolik arşivinin (arsiv.mackolik.com) hafta hafta maç listeleri (skorlarıyla).

Arşivde 1904-05'ten itibaren İstanbul ligleri (Futbol Birliği Ligi, Cuma Ligi, İstanbul Ligi, Profesyonel Lig ve 2. Lig),
Millî Küme (Maarif Mükâfatı, Millî Eğitim Kupası adlarıyla) ve 1955-59 Ankara / İzmir profesyonel ligleri var
(sezon listeleri: raw/mackolik_arsiv/sezonlar/<sezon>.txt). Maç sayfalarının kadro adresi bu dönem için HTTP 500 veriyor;
Millî Küme ve profesyonel liglerde ise kadro ve goller var (2026-11-19, 1938 Galatasaray 0-7 Güneş).

  python3 mackolik_eski.py say      # ağa çıkmadan: hangi sezonların listesi indi
  python3 mackolik_eski.py indir    # yarıda kalırsa aynı komut kaldığı yerden sürer (istekler arası 40 sn)
  python3 mackolik_eski.py hepsi    # tek iş, yeniden eskiye: her sezonun listesi ve hemen ardından kadroları (önerilen)
  python3 mackolik_eski.py kadro    # maç kadroları ve olayları (goller), örneklemeli
  python3 mackolik_eski.py tam      # kadro, ama atlanmış maçlar dahil her maç denenir (sonradan kontrol)

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


ATLANAN = os.path.join(K.HAM, "eski_kadrosuz.json")   # kadro sayfası olmayan lig-sezonlar (yeniden denenmez)


SONRADAN = 1_000_000   # arşive sonradan eklenen maçların numaraları (1957-59'da 664 maçın hiçbirinde kadro yoktu)
ORNEK = 5              # bu maçlardan her lig-sezonda denenen; birinde kadro çıkarsa hepsi denenir


def _kadrolu(mid):
    import json
    try:
        d = json.load(open(K.mac_yol(mid)))
        return bool(d.get("h") or d.get("a"))
    except (OSError, ValueError):
        return False


def kadro_sezon(e, gr, yok, tam=False):
    """Bir sezonun liglerinde maç kadroları ve olayları. Arşivin asıl maçları (numarası SONRADAN'dan küçük) hep denenir;
    sonradan eklenenlerden önce ORNEK tanesi, birinde kadro varsa hepsi (tam=True: hepsi). HTTP 500 verenler sonraki
    çalıştırmada yeniden denenir."""
    import random
    for s, ad in gr:
        if f"{e}|{s}" in yok:
            continue
        ms = K.sezon_maclari(e, [(s, ad)])
        eksik = [m for m in ms if not os.path.exists(K.mac_yol(m[0]))]
        if not eksik:
            continue
        kalan = []
        if not tam:
            asil = [m for m in eksik if int(m[0]) < SONRADAN]
            sonra = [m for m in eksik if int(m[0]) >= SONRADAN]
            sonra_inen = [m for m in ms if int(m[0]) >= SONRADAN and os.path.exists(K.mac_yol(m[0]))]
            if any(_kadrolu(m[0]) for m in sonra_inen):
                pass                                   # bu ligde sonradan eklenen kadrolu maç var: hepsi
            elif len(sonra_inen) >= ORNEK:
                eksik = asil                           # örnek denendi, kadro çıkmadı
            else:                                      # önce örnek; kadro çıkarsa aşağıdaki ikinci tur geri kalanı alır
                ornek = random.sample(sonra, min(ORNEK - len(sonra_inen), len(sonra)))
                eksik = asil + ornek
                kalan = [m for m in sonra if m not in ornek]
            if not eksik:
                continue
        print(f"{e} {ad}: {len(ms)} maç, {len(eksik)} kadro indirilecek {time.strftime('%H:%M')}", flush=True)
        ok = 0
        for i, (mid, mad) in enumerate(eksik, 1):
            ok += K.mac_indir(mid, mad)
            time.sleep(K.BEKLE + random.uniform(0, 5))
            if i % 50 == 0:
                print(f"  {i}/{len(eksik)} {time.strftime('%H:%M')} (inen: {ok})", flush=True)
            if kalan and i == len(eksik) and any(_kadrolu(m[0]) for m in ms if int(m[0]) >= SONRADAN):
                print(f"  örnekte kadro çıktı: {len(kalan)} maç daha", flush=True)
                eksik += kalan; kalan = []
        if kalan:
            print(f"  sonradan eklenen {len(kalan)} maç atlandı (örnekte kadro yok)", flush=True)


def _yok():
    import json
    return set(json.load(open(ATLANAN))) if os.path.exists(ATLANAN) else set()


def kadro(tam=False):
    yok = _yok()
    for e, gr in sorted(sezonlar(), reverse=True):   # yeniden eskiye
        kadro_sezon(e, gr, yok, tam)
    print("Bitti.", flush=True)


def hepsi():
    """Tek iş: yeniden eskiye her sezonun maç listesi, hemen ardından kadroları ve golleri (önce 1950'lerin profesyonel
    ligleri ve Millî Küme)."""
    yok = _yok()
    for e, gr in sorted(sezonlar(), key=lambda x: x[0][:4], reverse=True):
        print(f"{e}: {', '.join(a for _, a in gr)} {time.strftime('%H:%M')}", flush=True)
        M.arsiv_gruplari_indir(os.path.join(K.FIKSTUR, e), gr)
        kadro_sezon(e, gr, yok)
    print("Bitti.", flush=True)


def say():
    top = 0
    for e, gr in sezonlar():
        n = len(K.sezon_maclari(e, gr)); top += n
        print(f"{e}: {n} maç ({', '.join(a for _, a in gr)})")
    print("toplam:", top)


if __name__ == "__main__":
    {"indir": indir, "say": say, "kadro": kadro, "hepsi": hepsi, "tam": lambda: kadro(True)}[sys.argv[1]]()

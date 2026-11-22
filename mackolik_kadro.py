#!/usr/bin/env python3
"""Eski Maçkolik arşivinden (arsiv.mackolik.com) 1959-1991 Süper Lig maç kadroları ve olayları.

TFF'de 1991 öncesi kadro yok. Arşiv sitesinin maç sayfası kadroyu ayrı bir istekle yükler:
  /Match/MatchData.aspx?t=dtl&id=<arşiv maç no>   (Match.js'ten, 2026-11-16)
Dönen JSON: h / a = ev / deplasman kadrosu [[oyuncu no, ad, 0], ...] (ilk 11, sonra yedekler),
e = olaylar [[takım 1|2, dakika, oyuncu no, ad, tür, {...}], ...] (tür 1 gol, 2 sarı, 4 değişiklik ...),
d = skor ve durum.

  python3 mackolik_kadro.py say      # ağa çıkmadan: kaç sezon/maç listesi ve kadro indi
  python3 mackolik_kadro.py indir    # yarıda kalırsa aynı komut kaldığı yerden sürer

Sezon sezon (1990-91'den geriye): önce sezonun hafta hafta maç listesi, sonra her maçın kadro verisi.
Arşiv sitesi saatlik kotaya takıldığı için istekler arası 40 sn beklenir (~90 istek/saat).
Sonuç: raw/mackolik_kadro/fikstur/<sezon>/ (maç listeleri) ve raw/mackolik_kadro/mac/<son iki hane>/<maç no>.json
"""
import json, os, random, subprocess, sys, time

import mackolik as M

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "mackolik_kadro")
FIKSTUR = os.path.join(HAM, "fikstur")
MAC = os.path.join(HAM, "mac")
BEKLE = M.ARSIV_BEKLE
BITTI = ("4", "6", "8", "10")   # arşivin "maç bitti" durum kodları (mackolik.arsiv_maclar ile aynı)


def sezonlar():
    """[(sezon, [(grup no, ad), ...])] yeniden eskiye; yalnızca en üst lig grupları."""
    out = []
    for f in os.listdir(os.path.join(M.ARSIV_HAM, "sezonlar")):
        etiket = f[:-4]
        gr = [(str(s), a) for s, a in M.arsiv_lig_listesi(etiket) or [] if M.lig_adi_kademe(a)[1] == 1]
        if gr and etiket <= "1990-1991":
            out.append((etiket, gr))
    return sorted(out, key=lambda x: x[0][:4] + ("b" if len(x[0]) > 4 else "a"), reverse=True)


def sezon_maclari(etiket, gr):
    """Diskteki maç listelerinden bitmiş maçlar: [(maç no, 'Ev - Deplasman')]."""
    klasor, out, gorulen = os.path.join(FIKSTUR, etiket), [], set()
    for s, _ in gr:
        hyol = os.path.join(klasor, f"g{s}_haftalar.txt")
        if not os.path.exists(hyol):
            continue
        for hf in M.js_dizi(open(hyol, encoding="utf-8").read()):
            yol = os.path.join(klasor, f"g{s}_h{hf[0]}.txt")
            if os.path.exists(yol):
                for x in M.js_dizi(open(yol, encoding="utf-8").read()):
                    if x[0] not in gorulen and x[8] in BITTI:
                        gorulen.add(x[0]); out.append((x[0], f"{x[4]} - {x[6]}"))
    return out


def mac_yol(mid):
    return os.path.join(MAC, mid[-2:].zfill(2), f"{mid}.json")


def mac_indir(mid, ad):
    """True: kaydedildi, False: atlandı (sonraki çalıştırmada yeniden denenir)."""
    engel = 0
    while True:
        r = subprocess.run(["curl", "-sL", "--compressed", "-m", "60", "-A", M.UA, "-w", "\n%{http_code}",
                            "-e", f"{M.ARSIV}/Mac/{mid}/", f"{M.ARSIV}/Match/MatchData.aspx?t=dtl&id={mid}&s=0"],
                           capture_output=True, text=True)
        govde, _, kod = r.stdout.rpartition("\n")
        if kod in ("429", "403"):
            engel += 1
            if engel >= 3:
                sys.exit(f"Arşiv sitesi üst üste {engel} kez engelledi (HTTP {kod}). Birkaç saat sonra aynı komutla devam edin.")
            print(f"  HTTP {kod}: {15 * engel} dk ara veriliyor", flush=True)
            time.sleep(900 * engel)
            continue
        if kod != "200" or not govde.lstrip().startswith("{"):
            print(f"  {mid} ({ad}): HTTP {kod}, atlandı", flush=True)
            return False
        try:
            json.loads(govde)
        except ValueError:
            print(f"  {mid} ({ad}): okunamayan yanıt, atlandı", flush=True)
            return False
        os.makedirs(os.path.dirname(mac_yol(mid)), exist_ok=True)
        with open(mac_yol(mid) + ".tmp", "w", encoding="utf-8") as f:
            f.write(govde)
        os.replace(mac_yol(mid) + ".tmp", mac_yol(mid))
        return True


def indir():
    for etiket, gr in sezonlar():
        print(f"{etiket}: maç listesi", flush=True)
        M.arsiv_gruplari_indir(os.path.join(FIKSTUR, etiket), gr)
        maclar = sezon_maclari(etiket, gr)
        eksik = [m for m in maclar if not os.path.exists(mac_yol(m[0]))]
        print(f"{etiket}: {len(maclar)} maç, {len(eksik)} kadro indirilecek {time.strftime('%H:%M')}", flush=True)
        kadrolu = 0
        for i, (mid, ad) in enumerate(eksik, 1):
            if mac_indir(mid, ad):
                d = json.load(open(mac_yol(mid), encoding="utf-8"))
                kadrolu += bool(d.get("h") or d.get("a"))
            if i % 50 == 0:
                print(f"  {etiket} {i}/{len(eksik)} {time.strftime('%H:%M')} (kadrolu: {kadrolu})", flush=True)
            time.sleep(BEKLE + random.uniform(0, 5))
    print("Bitti.", flush=True)


def say():
    tm = tk = 0
    for etiket, gr in sezonlar():
        maclar = sezon_maclari(etiket, gr)
        var = [m for m, _ in maclar if os.path.exists(mac_yol(m))]
        kadro = sum(bool((d := json.load(open(mac_yol(m), encoding="utf-8"))).get("h") or d.get("a")) for m in var)
        liste = "liste var" if maclar else "liste yok"
        print(f"{etiket}: {liste}, {len(maclar)} maç, {len(var)} indi, {kadro} kadrolu")
        tm += len(var); tk += kadro
    print(f"toplam: {tm} maç indi, {tk} tanesinde kadro var")


if __name__ == "__main__":
    {"indir": indir, "say": say}[sys.argv[1] if len(sys.argv) > 1 else "say"]()

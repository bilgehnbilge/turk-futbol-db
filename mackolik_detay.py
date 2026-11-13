#!/usr/bin/env python3
"""Maçkolik maç sayfalarından gol (ve varsa kart) olayları: TFF'nin ayrıntı vermediği maçlar için.

Kapsam (örnek sayfalarla ölçüldü, 2026-11-13):
  - Süper Lig 1959-1991 (TFF'de 1984-90 sayfaları boş, 1990-91'de gol yok)
  - 1. Lig 1990-91 (TFF'de gol yok)
  - Türkiye Kupası 2007-08 ve sonrası (1990-2007 TFF sayfaları zaten indi)
  - 2. Lig 1990-91: denenir; ilk maçlarda olay yoksa o sezon atlanır
1990 öncesi alt liglerde Maçkolik'te gol bilgisi yok, onlar listeye alınmaz.

  python3 mackolik_detay.py say      # ağa çıkmadan: kaç maç var, kaçı indi
  python3 mackolik_detay.py indir    # yarıda kalırsa aynı komut kaldığı yerden sürer

Sonuç: raw/mackolik_detay.jsonl (her satır bir maç: {"id", "yarisma", "sezon", "olaylar"}).
Siteyi yormamak için istekler arası 6-9 sn beklenir; 429/403 gelirse 15 dk, sonra 30 dk ara verilir,
üst üste 3 engelde durur. Maç sayfası başına ~230 KB indirilir ama yalnızca olaylar saklanır.
"""
import csv, html, json, os, random, re, subprocess, sys, time, urllib.parse

import mackolik as M

KOK = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(KOK, "raw", "mackolik_detay.jsonl")
SEZON_HAM = os.path.join(KOK, "raw", "mackolik")
BEKLE = (6.0, 9.0)
# Maçkolik sayfası olmayan sezonların maç numaraları için indirilecek sezon sayfaları (TFF'den aldığımız sezonlar)
EK_SEZONLAR = [("superlig", f"{y}-{y + 1}") for y in range(1984, 1991)] + [("2lig", "1990-1991")]
BOS_ESIK = 25   # bir sezonun ilk 25 gollü maçında hiç olay yoksa o sezonun geri kalanı atlanır


def sezon_sayfasi(yar, etiket):
    yol = os.path.join(SEZON_HAM, f"{yar}_{etiket}.html.gz")
    if not os.path.exists(yol):
        y = M.YARISMALAR[yar]
        url = f"{M.SITE}/{urllib.parse.quote(y['slug'])}/{etiket}/{y['id']}"
        print(f"  sezon sayfası: {yar} {etiket}", flush=True)
        ok, kod = M.curl(url, yol)
        time.sleep(random.uniform(*BEKLE))
        if not ok:
            print(f"  UYARI: {yar} {etiket} sezon sayfası alınamadı (HTTP {kod}), atlanıyor", flush=True)
            return []
    return M.maclar(M.oku(yol))


def hedefler(ag=True):
    """[(mac kimliği, yarisma, sezon, gol sayısı)] öncelik sırasıyla."""
    satir = list(csv.DictReader(open(os.path.join(KOK, "mackolik_maclar.csv"), encoding="utf-8")))
    gol = lambda r: (int(r["ev_gol"]) + int(r["dep_gol"])) if str(r["ev_gol"]).isdigit() and str(r["dep_gol"]).isdigit() else None   # None: oynanmamış
    sec = lambda f: [(r["kaynak_id"], r["yarisma"], r["sezon"], gol(r)) for r in satir if r["kaynak"] == "mackolik" and f(r)]
    out = sec(lambda r: r["yarisma"] == "superlig")
    for yar, etiket in EK_SEZONLAR[:-1]:
        if ag or os.path.exists(os.path.join(SEZON_HAM, f"{yar}_{etiket}.html.gz")):
            out += [(m["kaynak_id"], yar, etiket, gol(m)) for m in sezon_sayfasi(yar, etiket)]
    out += sec(lambda r: r["yarisma"] == "1lig" and r["sezon"] == "1990-1991")
    out += sec(lambda r: r["yarisma"] == "kupa" and r["sezon"] >= "2007-2008")
    yar, etiket = EK_SEZONLAR[-1]
    if ag or os.path.exists(os.path.join(SEZON_HAM, f"{yar}_{etiket}.html.gz")):
        out += [(m["kaynak_id"], yar, etiket, gol(m)) for m in sezon_sayfasi(yar, etiket)]
    gorulen, tek = set(), []
    for x in out:
        if x[3] is not None and x[0] not in gorulen:
            gorulen.add(x[0]); tek.append(x)
    return tek


def olaylar(t):
    """Sayfadaki 'keyEvents' dizisi (gol, kart...). Dizi yoksa None."""
    u = html.unescape(t)
    i = u.find('"keyEvents":[')
    if i < 0:
        return None
    j, d = i + len('"keyEvents":'), 0
    for k in range(j, len(u)):   # köşeli parantezleri sayarak dizinin sonunu bul
        if u[k] == "[": d += 1
        elif u[k] == "]":
            d -= 1
            if d == 0:
                return json.loads(u[j:k + 1])
    return None


def indirilenler():
    if not os.path.exists(CIKTI):
        return {}
    out = {}
    with open(CIKTI, encoding="utf-8") as f:
        for s in f:
            x = json.loads(s)
            out[x["id"]] = x
    return out


def say():
    h, var = hedefler(ag=False), indirilenler()
    import collections
    c = collections.Counter((y, s[:3] + "0'lar") for _, y, s, _ in h)
    for k in sorted(c):
        print(f"  {k[0]:9} {k[1]}: {c[k]} maç")
    print(f"Toplam {len(h)} maç (henüz indirilmemiş sezon sayfalarındakiler hariç), {len(var)} tanesi indi.")
    eksik = [f"{y} {e}" for y, e in EK_SEZONLAR if not os.path.exists(os.path.join(SEZON_HAM, f"{y}_{e}.html.gz"))]
    if eksik:
        print("İndirme başlayınca önce şu sezon sayfaları alınacak:", ", ".join(eksik))


def indir():
    var = indirilenler()
    h = hedefler()
    # daha önce boş çıkmış sezonlar
    bos_say, dolu = {}, set()
    for x in var.values():
        k = (x["yarisma"], x["sezon"])
        if x.get("gol", 0) > 0:
            if x["olaylar"]:
                dolu.add(k)
            else:
                bos_say[k] = bos_say.get(k, 0) + 1
    liste = [x for x in h if x[0] not in var]
    print(f"{len(liste)} maç sayfası indirilecek (~{len(liste) * (sum(BEKLE) / 2 + 1) / 3600:.0f} saat)", flush=True)
    engel = 0
    with open(CIKTI, "a", encoding="utf-8") as f:
        for i, (mid, yar, sezon, gol) in enumerate(liste, 1):
            k = (yar, sezon)
            if k not in dolu and bos_say.get(k, 0) >= BOS_ESIK:
                continue   # bu sezonda Maçkolik'te olay yok
            url = f"https://www.mackolik.com/mac/x/{mid}"
            r = subprocess.run(["curl", "-sL", "--compressed", "-m", "90", "-A", M.UA, "-w", "\n%{http_code}", url], capture_output=True)
            govde, _, kod = r.stdout.rpartition(b"\n")
            kod = kod.decode().strip()
            if kod in ("429", "403"):
                engel += 1
                if engel >= 3:
                    sys.exit(f"Maçkolik üst üste {engel} kez engelledi (HTTP {kod}). Birkaç saat sonra aynı komutla devam edin.")
                bekle = 900 * engel
                print(f"  HTTP {kod}: {bekle // 60} dk ara veriliyor", flush=True)
                time.sleep(bekle)
                continue
            if kod != "200":
                print(f"  {mid}: HTTP {kod}, atlandı (sonraki çalıştırmada yeniden denenir)", flush=True)
                time.sleep(random.uniform(*BEKLE))
                continue
            engel = 0
            ol = olaylar(govde.decode("utf-8", "replace"))
            f.write(json.dumps({"id": mid, "yarisma": yar, "sezon": sezon, "gol": gol, "olaylar": ol or []}, ensure_ascii=False) + "\n")
            f.flush()
            if gol > 0:
                if ol:
                    dolu.add(k)
                else:
                    bos_say[k] = bos_say.get(k, 0) + 1
                    if k not in dolu and bos_say[k] == BOS_ESIK:
                        print(f"  {yar} {sezon}: ilk {BOS_ESIK} gollü maçta olay yok, sezon atlanıyor", flush=True)
            if i % 100 == 0:
                print(f"  {i}/{len(liste)} {time.strftime('%H:%M')} ({yar} {sezon})", flush=True)
            time.sleep(random.uniform(*BEKLE))
    print("Bitti.")


if __name__ == "__main__":
    {"say": say, "indir": indir}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()

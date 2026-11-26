#!/usr/bin/env python3
"""Eski Maçkolik arşivinden (arsiv.mackolik.com) 1959-1991 Süper Lig maç kadroları ve olayları.

TFF'de 1991 öncesi kadro yok. Arşiv sitesinin maç sayfası kadroyu ayrı bir istekle yükler:
  /Match/MatchData.aspx?t=dtl&id=<arşiv maç no>   (Match.js'ten, 2026-11-16)
Dönen JSON: h / a = ev / deplasman kadrosu [[oyuncu no, ad, 0], ...] (ilk 11, sonra yedekler),
e = olaylar [[takım 1|2, dakika, oyuncu no, ad, tür, {...}], ...] (tür 1 gol, 2 sarı, 4 değişiklik ...),
d = skor ve durum.

  python3 mackolik_kadro.py say      # ağa çıkmadan: kaç sezon/maç listesi ve kadro indi
  python3 mackolik_kadro.py indir    # yarıda kalırsa aynı komut kaldığı yerden sürer
  python3 mackolik_kadro.py kupa     # 1962-90 Türkiye Kupası (tur sayfaları + kadrolar); kaldığı yerden sürer
  python3 mackolik_kadro.py kupa_say # ağa çıkmadan kupa durumu

Sezon sezon (1990-91'den geriye): önce sezonun hafta hafta maç listesi, sonra her maçın kadro verisi.
Arşiv sitesi saatlik kotaya takıldığı için istekler arası 40 sn beklenir (~90 istek/saat).
Sonuç: raw/mackolik_kadro/fikstur/<sezon>/ (maç listeleri) ve raw/mackolik_kadro/mac/<son iki hane>/<maç no>.json
"""
import glob, json, os, random, subprocess, sys, time

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


KUPA_SEZON = [f"{y}-{y + 1}" for y in range(1962, 1990)]
YOKLA = 5   # bir turun ilk 5 maçında kadro yoksa turun geri kalanı istenmez
HEPSI = "--hepsi" in sys.argv   # kupa --hepsi: yoklama atlaması kapalı, kadrosuz turların bütün maçları da istenir


def kadrolu_mu(mid):
    d = json.load(open(mac_yol(mid), encoding="utf-8"))
    return bool(d.get("h") or d.get("a"))


def kupa_turlari_indir(etiket):
    """Sezonun tur sayfalarını (maç numaraları) indirir; [(tur adı, [(maç no, 'Ev - Dep'), ...])] döner (yalnız oynanmış)."""
    kl = os.path.join(M.ARSIV_HAM, f"kupa_{etiket}")
    sezon = open(os.path.join(kl, "sezon.html"), encoding="utf-8").read()
    turlar = M.kupa_turlari(sezon)
    if not turlar:   # 1967-75: arşiv bütün maçları sezon sayfasında veriyor
        satir = [(None, x) for x in M.kupa_satirlari(sezon)]
    else:
        satir = []
        for tid, ad in sorted(turlar, key=lambda x: int(x[0])):
            yol = os.path.join(kl, f"tur_{tid}.html")
            if not os.path.exists(yol):
                h = M.curl_metin(f"{M.ARSIV}/AjaxHandlers/CupHandler.aspx?command=legMatches&id={tid}")
                time.sleep(BEKLE + random.uniform(0, 5))
                if h is None:
                    print(f"  kupa {etiket} {ad}: tur sayfası alınamadı (sonra yeniden denenir)", flush=True)
                    continue
                open(yol + ".tmp", "w", encoding="utf-8").write(h)
                os.replace(yol + ".tmp", yol)
            satir += [(ad, x) for x in M.kupa_satirlari(open(yol, encoding="utf-8").read())]
    out, gorulen = {}, set()
    for ad, x in satir:
        if x["ev_gol"] and x["kaynak_id"] not in gorulen:
            gorulen.add(x["kaynak_id"])
            out.setdefault(ad or "", []).append((x["kaynak_id"], f"{x['ev_adi']} - {x['dep_adi']}", {x["ev_id"], x["dep_id"]}))
    return list(out.items())


def lig_takimlari(etiket):
    """Sezonun Süper Lig (en üst lig) takımlarının arşiv takım no'ları (diskteki lig fikstüründen)."""
    out = set()
    for et, gr in sezonlar():
        if et == etiket:
            for s, _ in gr:
                for yol in glob.glob(os.path.join(FIKSTUR, etiket, f"g{s}_h*.txt")):
                    if not yol.endswith("_haftalar.txt"):
                        out |= {x[i] for x in M.js_dizi(open(yol, encoding="utf-8").read()) for i in (3, 5)}
    return out


SUPER_SEZON = [f"{y}-{y + 1}" for y in range(1965, 1990)]


def super_sezon_maclari(etiket, indir_=True):
    """Süper Kupa (Cumhurbaşkanlığı / Devlet Başkanlığı Kupası; arşivde kupa id=2) sezon sayfasındaki maçlar."""
    kl = os.path.join(M.ARSIV_HAM, f"superkupa_{etiket}")
    yol = os.path.join(kl, "sezon.html")
    if not os.path.exists(yol):
        if not indir_:
            return []
        h = M.curl_metin(f"{M.ARSIV}/AjaxHandlers/CupHandler.aspx?command=seasonMatches&id=2&season={etiket.replace('-', '/')}")
        time.sleep(BEKLE + random.uniform(0, 5))
        if h is None:
            print(f"  süper kupa {etiket}: sezon sayfası alınamadı (sonra yeniden denenir)", flush=True)
            return []
        os.makedirs(kl, exist_ok=True)
        open(yol + ".tmp", "w", encoding="utf-8").write(h)
        os.replace(yol + ".tmp", yol)
    return [x for x in M.kupa_satirlari(open(yol, encoding="utf-8").read()) if x["ev_gol"]]


def superkupa():
    """1965-90 Süper Kupa maç kadroları (sezon başına bir maç; yoklama yok, hepsi denenir)."""
    say = dict(kadrolu=0, kadrosuz=0, hata=0)
    for etiket in reversed(SUPER_SEZON):
        for x in super_sezon_maclari(etiket):
            mid = x["kaynak_id"]
            if os.path.exists(mac_yol(mid)):
                continue
            if not mac_indir(mid, f"{x['ev_adi']} - {x['dep_adi']}"):
                say["hata"] += 1
                time.sleep(BEKLE + random.uniform(0, 5))
                continue
            if kadrolu_mu(mid):
                say["kadrolu"] += 1
                time.sleep(BEKLE + random.uniform(0, 5))
            else:
                say["kadrosuz"] += 1
        print(f"  süper kupa {etiket} {time.strftime('%H:%M')}", flush=True)
    print(f"Süper Kupa bitti: {say}", flush=True)


def kupa():
    """Önce 1965-90 Süper Kupa (küçük), sonra 1962-90 Türkiye Kupası kadroları. Site hatası (HTTP/okunamayan yanıt) ile kadrosu olmayan maç ayrılır: hata
    kaydedilmez (sonraki çalıştırmada yeniden denenir), kadrosuz maç boş olarak kaydedilir ve beklemeden sonrakine geçilir.
    Bir turun ilk 5 maçı kadrosuzsa turun kalanından yalnız Süper Lig takımının oynadığı maçlar istenir."""
    superkupa()
    top = dict(kadrolu=0, kadrosuz=0, hata=0, atlanan=0)
    for etiket in reversed(KUPA_SEZON):
        print(f"kupa {etiket}: tur listesi", flush=True)
        turlar = kupa_turlari_indir(etiket)
        lig = lig_takimlari(etiket)
        if not lig:
            print(f"  UYARI {etiket}: Süper Lig takım listesi bulunamadı, yoklama atlaması kapalı", flush=True)
        n = sum(len(m) for _, m in turlar)
        print(f"kupa {etiket}: {len(turlar)} tur, {n} oynanmış maç {time.strftime('%H:%M')}", flush=True)
        for ad, maclar in turlar:
            bakilan = kadrolu = 0
            for mid, mad, takim in maclar:
                if lig and not HEPSI and bakilan >= YOKLA and kadrolu == 0 and not (takim & lig):
                    top["atlanan"] += 1   # kadrosuz turda Süper Lig takımı oynamayan maç
                    continue
                if os.path.exists(mac_yol(mid)):
                    bakilan += 1; kadrolu += kadrolu_mu(mid)
                    continue
                if not mac_indir(mid, mad):
                    top["hata"] += 1
                    time.sleep(BEKLE + random.uniform(0, 5))
                    continue
                bakilan += 1
                if kadrolu_mu(mid):
                    kadrolu += 1; top["kadrolu"] += 1
                    time.sleep(BEKLE + random.uniform(0, 5))
                else:
                    top["kadrosuz"] += 1   # beklemeden sonraki maça
            print(f"  {etiket} {ad or 'tüm turlar'}: {len(maclar)} maç, {kadrolu} kadrolu {time.strftime('%H:%M')}", flush=True)
    print(f"Bitti. Bu çalıştırmada: {top}", flush=True)


def kupa_say():
    """Ağa çıkmadan: sezon başına diskte olan tur sayfası ve inen kadro."""
    sk = [x["kaynak_id"] for e in SUPER_SEZON for x in super_sezon_maclari(e, False)]
    var = [m for m in sk if os.path.exists(mac_yol(m))]
    print(f"süper kupa: {len(sk)} maç listede, {len(var)} indi, {sum(map(kadrolu_mu, var))} kadrolu")
    for etiket in KUPA_SEZON:
        kl = os.path.join(M.ARSIV_HAM, f"kupa_{etiket}")
        sezon = open(os.path.join(kl, "sezon.html"), encoding="utf-8").read()
        turlar = M.kupa_turlari(sezon)
        if turlar:
            inen = sum(os.path.exists(os.path.join(kl, f"tur_{tid}.html")) for tid, _ in turlar)
            ms = M.kupa_maclar(kl)[1]
        else:
            inen, ms = "-", M.kupa_satirlari(sezon)
        ms = [x for x in ms if x["ev_gol"]]
        var = [x["kaynak_id"] for x in ms if os.path.exists(mac_yol(x["kaynak_id"]))]
        print(f"kupa {etiket}: tur {inen}/{len(turlar)}, {len(ms)} maç, {len(var)} indi, {sum(map(kadrolu_mu, var))} kadrolu")


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
    {"indir": indir, "say": say, "kupa": kupa, "kupa_say": kupa_say}[sys.argv[1] if len(sys.argv) > 1 else "say"]()

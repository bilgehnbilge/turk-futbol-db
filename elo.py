#!/usr/bin/env python3
"""Türk kulüpleri için Elo puanı: 1959'dan bugüne bütün profesyonel lig, play-off, Türkiye Kupası ve özel kupa maçları.

  python3 elo.py ayarla   # ayarları geçmiş maçların tahmin isabetine göre seçer -> elo_ayar.json
  python3 elo.py          # ayarlarla hesaplar, özet yazar (web_aktar.py de hesapla() ile çağırır -> data/elo.json)

Hesap (her maçtan önce):
  beklenen = 1 / (1 + 10^(-(R_ev + H - R_dep) / 400))       H: ev sahibi avantajı (maçlardan kendini günceller)
  R += K × yarışma ağırlığı × gol farkı çarpanı × (sonuç - beklenen)
  sonuç: galibiyet 1, beraberlik 0,5 (penaltıyla biten kupa maçı beraberlik), yenilgi 0
  gol farkı çarpanı: 1 farka 1, 2 farka 1,5, 3+ farka (11 + fark) / 8  (Dünya Futbol Elo'su)
Ligler arası denge:
  - Yeni kulüp, ilk oynadığı ligin o anki ortalamasının biraz altından başlar (ilk lig yoksa en alt seviyenin altından).
  - Her sezon başında puanın bir kısmı kulübün o sezon oynayacağı ligin ortalamasına çekilir (yükselen/düşen takım
    yeni ligine yaklaşır; kadro değişimi). Kupa maçları ligler arasında köprü kurar.
Süper Lig'in ortalaması her sezon başında 1500'e kaydırılır: puanlar dönemler arasında karşılaştırılabilir.
Avrupa maçları dahil değil (yabancı rakiplerin gücü bilinmiyor); hükmen ve sayılmayan maçlar dahil değil.
"""
import collections, json, math, os, sqlite3, sys, time

KOK = os.path.dirname(os.path.abspath(__file__))
AYAR_YOL = os.path.join(KOK, "elo_ayar.json")
VARSAYILAN = dict(K=24.0, kupa=1.0, playoff=1.0, h0=70.0, h_hiz=0.06, cekim=0.25, kademe_aralik=150.0, yeni_eksi=50.0,
                  gol_carpani=1)
BASLANGIC = 1500.0


def sezon_bas(s):
    return int(s[:4])


def maclari_al(c):
    """Elo'ya giren maçlar: tarih sırasıyla [(tarih, sezon, yarisma, asama, kademe, ev, dep, ev_gol, dep_gol, pen, id)]"""
    out = []
    for r in c.execute("""SELECT id, tarih, sezon, yarisma, asama, kademe, ev_kulup, dep_kulup, ev_gol, dep_gol, ev_pen, dep_pen, durum
                          FROM mac WHERE yarisma IN ('lig','kupa','ozel_kupa') AND ev_gol IS NOT NULL AND tarih IS NOT NULL
                          AND ev_kulup IS NOT NULL AND dep_kulup IS NOT NULL AND ev_kulup <> dep_kulup
                          AND asama <> 'gecersiz' AND COALESCE(durum,'MS') NOT IN ('Hük.','Çifte H','Cancelled','Fixture')
                          ORDER BY tarih, id"""):
        mid, tarih, sezon, yar, asama, kd, ev, dep, eg, dg, ep, dp, durum = r
        pen = ep is not None and dp is not None and eg == dg
        out.append((tarih, sezon, yar, asama, kd, ev, dep, eg, dg, (ep, dp) if pen else None, mid))
    return out


def lig_kademesi(c):
    """(kulüp, sezon) -> o sezon oynadığı en üst lig kademesi"""
    out = {}
    for k, s, kd in c.execute("""SELECT ev_kulup, sezon, MIN(kademe) FROM mac WHERE yarisma='lig' AND kademe IS NOT NULL GROUP BY 1,2
                                 UNION ALL SELECT dep_kulup, sezon, MIN(kademe) FROM mac WHERE yarisma='lig' AND kademe IS NOT NULL GROUP BY 1,2"""):
        if k is not None:
            out[(k, s)] = min(kd, out.get((k, s), 9))
    return out


def gol_carpani(fark):
    fark = abs(fark)
    return 1.0 if fark <= 1 else 1.5 if fark == 2 else (11 + fark) / 8


def calistir(maclar, kademe, a, kayit=False, degerlendir_bas=1965):
    """Bütün maçları sırayla oynatır. Döner: (Brier skoru, sayı, R, H, kayıtlar)"""
    R = {}
    H = a["h0"]
    sezon_simdi = None
    kademe_toplam = collections.defaultdict(lambda: [0.0, 0])   # bu sezon kademe ortalaması (sezon başında hesaplanır)
    ort = {}
    brier, n = 0.0, 0
    gecmis = collections.defaultdict(list) if kayit else None   # kulüp -> [(tarih, puan)]
    mac_kaydi = [] if kayit else None
    son_sezon_kulup = {}

    def kademe_ort(kd):
        if kd in ort:
            return ort[kd]
        return BASLANGIC - a["kademe_aralik"] * ((kd or 5) - 1)

    for tarih, sezon, yar, asama, kd, ev, dep, eg, dg, pen, mid in maclar:
        if sezon != sezon_simdi:
            # yeni sezon: kademe ortalamaları (önceki sezonun puanlarıyla), sonra çekim
            sezon_simdi = sezon
            tum = collections.defaultdict(list)
            for k, r in R.items():
                kk = kademe.get((k, sezon))
                if kk:
                    tum[kk].append(r)
            ort = {kk: sum(v) / len(v) for kk, v in tum.items() if len(v) >= 4}
            if 1 in ort:   # Süper Lig ortalaması her sezon 1500: dönemler karşılaştırılabilir (enflasyon olmaz)
                kay = BASLANGIC - ort[1]
                for k in R:
                    R[k] += kay
                ort = {kk: v + kay for kk, v in ort.items()}
            for k in list(R):
                kk = kademe.get((k, sezon))
                hedef = kademe_ort(kk) if kk else None
                if hedef is not None:
                    R[k] += a["cekim"] * (hedef - R[k])
        for k in (ev, dep):
            if k not in R:
                kk = kademe.get((k, sezon), 5)
                R[k] = kademe_ort(kk) - a["yeni_eksi"]
        fark = R[ev] + H - R[dep]
        E = 1 / (1 + 10 ** (-fark / 400))
        if pen or eg == dg:
            S = .5
        else:
            S = 1.0 if eg > dg else 0.0
        if sezon_bas(sezon) >= degerlendir_bas:
            brier += (S - E) ** 2; n += 1
        agirlik = a["kupa"] if yar != "lig" else (a["playoff"] if asama == "play-off" else 1.0)
        G = gol_carpani(eg - dg) if (a["gol_carpani"] and not pen) else 1.0
        d = a["K"] * agirlik * G * (S - E)
        if kayit:
            mac_kaydi.append((mid, R[ev], R[dep], H, E))
        R[ev] += d; R[dep] -= d
        H += a["h_hiz"] * a["K"] * (S - E)   # ev sahibi avantajı da bir "puan" gibi öğrenilir
        if kayit:
            gecmis[ev].append((tarih, sezon, R[ev])); gecmis[dep].append((tarih, sezon, R[dep]))
    return (brier / max(n, 1), n, R, H, (gecmis, mac_kaydi))


def ayar_oku():
    a = dict(VARSAYILAN)
    if os.path.exists(AYAR_YOL):
        a.update(json.load(open(AYAR_YOL, encoding="utf-8")).get("ayar", {}))
    return a


def ayarla():
    c = sqlite3.connect(os.path.join(KOK, "futbol.db"))
    maclar, kademe = maclari_al(c), lig_kademesi(c)
    a = dict(VARSAYILAN)
    en = calistir(maclar, kademe, a)[0]
    print(f"başlangıç Brier {en:.5f}", flush=True)
    adimlar = {"K": [12, 16, 20, 24, 28, 32, 40], "kupa": [.5, .75, 1, 1.25, 1.5], "playoff": [.75, 1, 1.25, 1.5],
               "h0": [40, 60, 80, 100], "h_hiz": [0, .02, .04, .06, .1, .15], "cekim": [0, .1, .2, .3, .4, .5],
               "kademe_aralik": [50, 100, 150, 200, 250, 300], "yeni_eksi": [0, 25, 50, 100, 150], "gol_carpani": [0, 1]}
    for tur in range(3):
        degisti = False
        for p, degerler in adimlar.items():
            sonuc = {}
            for v in degerler:
                b = dict(a, **{p: v})
                sonuc[v] = calistir(maclar, kademe, b)[0]
            v = min(sonuc, key=sonuc.get)
            if sonuc[v] < en - 1e-7 and v != a[p]:
                a[p] = v; en = sonuc[v]; degisti = True
            print(f"  tur {tur + 1} {p}: {v}  Brier {en:.5f}", flush=True)
        if not degisti:
            break
    # taban: her maçta 0,5 / ev sahibi oranı ile tahmin
    taban = calistir(maclar, kademe, dict(a, K=0, h_hiz=0, yeni_eksi=0, kademe_aralik=0))[0]
    json.dump({"ayar": a, "brier": round(en, 5), "brier_esit_puan": round(taban, 5),
               "aciklama": "Brier: 1965'ten sonraki maçlarda (sonuç - beklenen)^2 ortalaması; düşük daha iyi. "
                           "brier_esit_puan: herkes aynı puanda, yalnız ev sahibi avantajıyla tahmin."},
              open(AYAR_YOL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("->", AYAR_YOL, a, en, "eşit puan tabanı", taban)


def hesapla(c, okunur=lambda s: s):
    """web_aktar için: data/elo.json içeriği"""
    a = ayar_oku()
    maclar, kademe = maclari_al(c), lig_kademesi(c)
    brier, n, R, H, (gecmis, mac_kaydi) = calistir(maclar, kademe, a, kayit=True)
    son_tarih = maclar[-1][0]
    son_sezon = maclar[-1][1]
    # sezon sonu puanı ve tüm zamanların zirvesi
    sezon_sonu = {}
    zirve = []
    for k, l in gecmis.items():
        ss = {}
        for tarih, sezon, r in l:
            ss[sezon] = r
        sezon_sonu[k] = [[s, round(r)] for s, r in sorted(ss.items(), key=lambda x: (sezon_bas(x[0]), x[0]))]
        t, s, r = max(l, key=lambda x: x[2])
        zirve.append([k, round(r), t, s])
    zirve.sort(key=lambda x: -x[1])
    # bu sezon ligde oynayan kulüplerin güncel puanı
    guncel = []
    for k, r in R.items():
        kd = kademe.get((k, son_sezon))
        if kd:
            son = gecmis[k]
            once = next((x[2] for x in reversed(son) if x[0] < son[-1][0] and (son[-1][0] > x[0])), None)
            # 10 maç önceki puan
            on_once = son[-11][2] if len(son) > 10 else son[0][2]
            guncel.append([k, round(r), kd, round(r - on_once)])
    guncel.sort(key=lambda x: -x[1])
    # en büyük sürprizler: beklenen skoru en düşük olan galibiyetler (1965 sonrası)
    beklenen = {mid: (re, rd, h, e) for mid, re, rd, h, e in mac_kaydi}
    surpriz = []
    mac_bilgi = {m[10]: m for m in maclar}
    for mid, (re, rd, h, e) in beklenen.items():
        m = mac_bilgi[mid]
        if sezon_bas(m[1]) < 1965 or m[9] or m[7] == m[8]:
            continue
        kazanan_e = e if m[7] > m[8] else 1 - e
        surpriz.append((kazanan_e, mid))
    surpriz.sort()
    sur = []
    for e, mid in surpriz[:50]:
        m = mac_bilgi[mid]; re, rd, h, _ = beklenen[mid]
        sur.append([mid, m[0], m[1], m[5], m[6], m[7], m[8], round(re), round(rd), round(e, 3)])
    return {"ayar": a, "brier": round(brier, 5), "mac": n, "ev_avantaji": round(H, 1), "son_tarih": son_tarih, "son_sezon": son_sezon,
            "guncel_alanlar": ["kulup", "elo", "kademe", "son10"], "guncel": guncel,
            "zirve_alanlar": ["kulup", "elo", "tarih", "sezon"], "zirve": zirve[:100],
            "surpriz_alanlar": ["id", "tarih", "sezon", "ev", "dep", "ev_gol", "dep_gol", "ev_elo", "dep_elo", "kazananin_beklentisi"], "surpriz": sur,
            "sezon_alanlar": ["sezon", "elo"], "kulup": sezon_sonu}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ayarla":
        ayarla()
    else:
        c = sqlite3.connect(os.path.join(KOK, "futbol.db"))
        t0 = time.time()
        d = hesapla(c)
        ad = dict(c.execute("SELECT id, ad FROM kulup"))
        print(f"{d['mac']} maç, Brier {d['brier']}, ev avantajı {d['ev_avantaji']} ({time.time() - t0:.1f} sn)")
        print("Güncel ilk 25:")
        for k, r, kd, s10 in d["guncel"][:25]:
            print(f"  {ad[k]:28} {r:5}  kademe {kd}  son 10 maç {s10:+}")
        print("Tüm zamanların zirveleri:")
        for k, r, t, s in d["zirve"][:15]:
            print(f"  {ad[k]:28} {r:5}  {t}")

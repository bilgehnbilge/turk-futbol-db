#!/usr/bin/env python3
"""Erkek ligleri doğrulaması: bütün resmi puan tabloları (TFF 1984-85'ten bugüne, Maçkolik arşivi 1959-1990) ile
futbol.db'deki maçlardan hesaplanan tablolar takım takım karşılaştırılır.

  python3 dogrula.py        # -> dogrulama_raporu.md (ve ekrana özet)

Karşılaştırma: her resmi tablo, aynı sezonda takımları en çok örtüşen lig grubumuza bağlanır (en az %70 ortak takım).
O, G, B, M, AG, YG karşılaştırılır; puan silmeleri karşılaştırmaya girmez. Hükmen sonuçlar skoruyla, "Çifte H" iki
takıma da 0-3 yenilgi, geçersiz sayılan maçlar hiç sayılmaz (sitedeki hesapla aynı).

Sınıflar
  tam           bütün satırlar aynı
  skor          her takımın maç sayısı aynı; sonuç ya da gol farklı (bir maçın skoru farklı yazılmış)
  eksik         bazı takımların bizde daha az maçı var
  fazla         bazı takımların bizde daha çok maçı var (play-off / tekrar maç lig sayılmış ya da çift kayıt)
  eksik+fazla   ikisi birden
  kulüp eşlemesi  maç sayısı tam ama bir takım bizde başka kulüp kimliğiyle (aynı kulübün iki kaydı)
  farklı aşama  takım sayısı grubumuzdan farklı: resmi tablo klasman / play-off / iki aşamanın toplamı (karşılaştırılamaz)
  bağlanamadı   resmi tablonun takımları hiçbir grubumuzla yeterince örtüşmüyor (çoğunlukla ikinci aşama / klasman tablosu)
"""
import collections, glob, json, os, sqlite3

KOK = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(KOK, "futbol.db")
TFF_DB = os.path.join(KOK, "raw", "tff.db")
ARSIV = os.path.join(KOK, "raw", "mackolik_arsiv")
RAPOR = os.path.join(KOK, "dogrulama_raporu.md")
KADEME_AD = {1: "Süper Lig", 2: "1. Lig", 3: "2. Lig", 4: "3. Lig"}
ALAN = ["O", "G", "B", "M", "AG", "YG"]
SINIF = ["tam", "skor", "eksik", "fazla", "eksik+fazla", "kulüp eşlemesi", "farklı aşama", "bağlanamadı"]


def kimlik_bulucu(c):
    """(kaynak, kaynak no, sezon) -> kulüp; '-once' gibi dönemli kimlikler sezona göre seçilir"""
    k = collections.defaultdict(list)
    for kid, kaynak, kno, ilk, son in c.execute("SELECT kulup_id, kaynak, kaynak_id, ilk_sezon, son_sezon FROM kulup_kimlik"):
        k[(kaynak, kno.split("-")[0])].append((kid, ilk or "0000", son or "9999"))
    def bul(kaynak, kno, sezon):
        l = k.get((kaynak, str(kno)), [])
        return next((x for x, a, b in l if a <= sezon <= b), l[0][0] if l else None)
    return bul


def resmi_tablolar(bul):
    out = []   # (kaynak, sezon, kademe, grup adı, [(kulüp, ad, [O,G,B,M,AG,YG])])
    t = sqlite3.connect(TFF_DB)
    grp = collections.defaultdict(list)
    for sezon, kd, g, tid, ad, *r in t.execute("SELECT sezon, kademe, COALESCE(grup,''), tff_id, ad, O, G, B, M, A, Y FROM puan ORDER BY rowid"):
        grp[(sezon, kd, g)].append((bul("tff", tid, sezon) if tid else None, ad, list(r)))
    for (sezon, kd, g), l in grp.items():
        out.append(("TFF", sezon, kd, g, l))
    import mackolik as M
    sid = {}
    for f in glob.glob(os.path.join(ARSIV, "sezonlar", "*.txt")):
        d = json.loads(open(f, encoding="utf-8").read().strip()[1:-1])
        for s, ad in d["l"]:
            sid[s] = (os.path.basename(f)[:-4], ad)
    for f in sorted(glob.glob(os.path.join(ARSIV, "puan", "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        if d["id"] not in sid:
            continue
        etiket, ligad = sid[d["id"]]
        _, kd = M.lig_adi_kademe(ligad)
        l = [(bul("mackolik_arsiv", r[0], etiket), r[1], [r[2] + r[3], r[4] + r[5], r[6] + r[7], r[8] + r[9], r[10] + r[11], r[12] + r[13]])
             for r in d["s"]]
        out.append(("Maçkolik", etiket, kd, ligad, l))
    return out


def bizim_gruplar(c):
    """(sezon, yarışma, kademe, grup) -> {kulüp: [O,G,B,M,AG,YG]}"""
    g = collections.defaultdict(lambda: collections.defaultdict(lambda: [0] * 6))
    for sz, y, kd, gr, e, d, a, b, durum in c.execute("""SELECT sezon, yarisma, kademe, COALESCE(grup,''), ev_kulup, dep_kulup, ev_gol, dep_gol, durum
                                                          FROM mac WHERE yarisma IN ('lig','terfi') AND asama='lig'"""):
        t = g[(sz, y, kd, gr)]
        if durum == "Çifte H":
            sonuc = ((e, 0, 3), (d, 0, 3))
        elif a is None:
            t[e]; t[d]   # takım grupta var, maç oynanmadı
            continue
        else:
            sonuc = ((e, a, b), (d, b, a))
        for k, x, y_ in sonuc:
            r = t[k]; r[0] += 1; r[1] += x > y_; r[2] += x == y_; r[3] += x < y_; r[4] += x; r[5] += y_
    return g


def main():
    c = sqlite3.connect(DB)
    bul = kimlik_bulucu(c)
    ad = dict(c.execute("SELECT id, ad FROM kulup"))
    tablolar = resmi_tablolar(bul)
    biz = bizim_gruplar(c)
    sezon_gr = collections.defaultdict(list)
    for k in biz:
        sezon_gr[k[0]].append(k)
    sonuclar, bagli = [], set()
    for kaynak, sezon, kd, g, satir in tablolar:
        ks = {s[0] for s in satir if s[0]}
        # en çok ortak takım; eşitlikte takım sayısı tutan, sonra adı tutan grup (ilk aşama 01 ile 1. Klasman Grubu aynı takımları paylaşır)
        ad_tut = lambda x: (x[3] or "") == g or (g[:1].isdigit() and (x[3] or "").startswith(g.lstrip("0")[:1] + ".") and "lasman" in g.lower() == ("lasman" in (x[3] or "").lower()))
        aday = max(sezon_gr.get(sezon, []), key=lambda x: (len(ks & set(biz[x])), len([k for k, v in biz[x].items() if v[0]]) == len(satir),
                                                          ad_tut(x), x[2] == kd), default=None)
        ort = len(ks & set(biz[aday])) / len(satir) if aday and satir else 0
        kayit = dict(kaynak=kaynak, sezon=sezon, kademe=kd, grup=g, takim=len(satir), resmi_mac=sum(s[2][0] for s in satir) // 2)
        if ort < 0.7:
            sonuclar.append(dict(kayit, sinif="bağlanamadı", ortak=f"%{round(100 * ort)}")); continue
        bagli.add(aday)
        b = biz[aday]
        kayit.update(bizim=aday, bizim_mac=sum(v[0] for v in b.values()) // 2)
        farklar = []
        for k, a, r in satir:
            br = b.get(k, [0] * 6) if k else None
            if br is None or r != br:
                farklar.append((ad.get(k, a) if k else a, r, br))
        eksik = any(br is not None and br[0] < r[0] for _, r, br in farklar) or any(br is None for _, r, br in farklar)
        fazla = any(br is not None and br[0] > r[0] for _, r, br in farklar)
        bizim_takim = {k for k, v in b.items() if v[0]}
        if farklar and eksik and not fazla:   # TFF bazı sezonlarda klasman tablosunu iki aşamanın toplamıyla veriyor
            top = collections.defaultdict(lambda: [0] * 6)
            for x in sezon_gr[sezon]:
                if x[1] == aday[1] and x[2] == aday[2]:
                    for k, v in biz[x].items():
                        top[k] = [p + q for p, q in zip(top[k], v)]
            if all(k and top.get(k) == r for k, _, r in satir):
                sonuclar.append(dict(kayit, sinif="tam", not_="iki aşamanın toplamı")); continue
        if len(satir) != len(bizim_takim) and farklar:
            sinif = "farklı aşama"   # resmi tablo başka aşamanın (klasman, play-off, iki aşamanın toplamı) tablosu
        elif farklar and ks - bizim_takim and bizim_takim - ks and kayit["resmi_mac"] == kayit["bizim_mac"]:
            sinif = "kulüp eşlemesi"   # maçlar tam; bir takım bizde başka kulüp kimliğiyle kayıtlı
        else:
            sinif = "tam" if not farklar else "eksik+fazla" if eksik and fazla else "eksik" if eksik else "fazla" if fazla else "skor"
        mac_ = None
        if sinif == "skor" and len(farklar) == 2:   # iki takımın aralarındaki maçlardan hangisi resmi tabloyla tutmuyor
            (a1, r1, b1), (a2, r2, b2) = farklar
            k1 = next(k for k, a, r in satir if r == r1 and (ad.get(k, a) if k else a) == a1)
            k2 = next(k for k, a, r in satir if r == r2 and (ad.get(k, a) if k else a) == a2)
            d1 = (r1[4] - b1[4], r1[5] - b1[5])
            for tarih, e, x, y in c.execute("SELECT tarih, ev_kulup, ev_gol, dep_gol FROM mac WHERE sezon=? AND yarisma=? AND kademe IS ? AND COALESCE(grup,'')=? "
                                            "AND asama='lig' AND ((ev_kulup=? AND dep_kulup=?) OR (ev_kulup=? AND dep_kulup=?))",
                                            (sezon, aday[1], aday[2], aday[3], k1, k2, k2, k1)):
                xx, yy = (x + d1[0], y + d1[1]) if e == k1 else (x + d1[1], y + d1[0])
                # düzeltilmiş skorla iki takımın satırı da resmi tabloyla birebir tutmalı
                def satir_(b, k, eski, yeni):
                    v = b[:]
                    for (gx, gy), isaret in ((eski, -1), (yeni, 1)):
                        mx, my = (gx, gy) if k == e else (gy, gx)
                        v[1] += isaret * (mx > my); v[2] += isaret * (mx == my); v[3] += isaret * (mx < my); v[4] += isaret * mx; v[5] += isaret * my
                    return v
                if xx >= 0 and yy >= 0 and satir_(b1, k1, (x, y), (xx, yy)) == r1 and satir_(b2, k2, (x, y), (xx, yy)) == r2:
                    ev, dep = (a1, a2) if e == k1 else (a2, a1)
                    mac_ = f"{tarih or 'tarihsiz'} {ev} – {dep}: bizde {x}-{y}, resmi tabloya göre {xx}-{yy}"
                    break
        sonuclar.append(dict(kayit, sinif=sinif, farklar=farklar, mac=mac_))
    # resmi tablosu olmayan gruplarımız (yalnız lig; terfi grupları ayrı)
    tablosuz = sorted(k for k in biz if k not in bagli and k[1] == "lig")

    # ---- rapor
    say = collections.Counter(s["sinif"] for s in sonuclar)
    satir_say = sum(s["takim"] for s in sonuclar if s["sinif"] != "bağlanamadı")
    tutan_satir = sum(s["takim"] - len(s.get("farklar", [])) for s in sonuclar if s["sinif"] != "bağlanamadı")
    L = ["# Erkek ligleri doğrulama raporu", "",
         f"`python3 dogrula.py` ile üretildi. {len(tablolar)} resmi puan tablosu (TFF: {sum(t[0] == 'TFF' for t in tablolar)}, "
         f"Maçkolik arşivi: {sum(t[0] == 'Maçkolik' for t in tablolar)}) futbol.db'deki maçlardan hesaplanan tablolarla karşılaştırıldı.", "",
         "| Sonuç | Tablo |", "|---|---|"] + [f"| {k} | {say[k]} |" for k in SINIF] + [
         "", f"Bağlanan tablolardaki {satir_say:,} takım satırının {tutan_satir:,} tanesi birebir tutuyor.".replace(",", "."), "",
         f"Resmi tablosu bulunmayan lig grubumuz: {len(tablosuz)}.", ""]
    lig_say = collections.defaultdict(collections.Counter)
    for s in sonuclar:
        lig_say[KADEME_AD.get(s["kademe"], f"{s['kademe']}. kademe")][s["sinif"]] += 1
    L += ["## Lig seviyesine göre", "", "| Lig | " + " | ".join(SINIF) + " |", "|---" * (len(SINIF) + 1) + "|"]
    for lig, cc in sorted(lig_say.items()):
        L.append(f"| {lig} | " + " | ".join(str(cc[k]) for k in SINIF) + " |")
    for sinif, baslik in (("eksik", "Eksik maç"), ("eksik+fazla", "Eksik ve fazla birlikte"), ("fazla", "Fazla maç"), ("skor", "Skor farkı"),
                          ("kulüp eşlemesi", "Kulüp eşlemesi (maçlar tam, bir takım başka kimlikle)"),
                          ("farklı aşama", "Farklı aşamanın tablosu (karşılaştırılamadı)")):
        l = [s for s in sonuclar if s["sinif"] == sinif]
        if not l:
            continue
        L += ["", f"## {baslik} ({len(l)} tablo)", "", "| Sezon | Lig | Grup | Kaynak | Resmi maç | Bizde | Farklı takım | Örnek (resmi O/G/B/M/AG/YG → bizde) ya da tutmayan maç |",
              "|---|---|---|---|---|---|---|---|"]
        for s in sorted(l, key=lambda s: (s["sezon"], s["kademe"] or 9, s["grup"])):
            tutarsiz = [x for x, r, _ in s["farklar"] if r[1] + r[2] + r[3] != r[0]]
            ornek = (f"Resmi tabloda {', '.join(tutarsiz)} için G+B+M ≠ O (kaynak hatası). " if tutarsiz else "") + (s.get("mac") or "")
            ornek = ornek or "; ".join(f"{a}: {'/'.join(map(str, r))} → {'/'.join(map(str, br)) if br else 'yok'}" for a, r, br in s["farklar"][:2])
            L.append(f"| {s['sezon']} | {KADEME_AD.get(s['kademe'], s['kademe'])} | {s['bizim'][3] or s['grup'] or '-'} | {s['kaynak']} | {s['resmi_mac']} | "
                     f"{s['bizim_mac']} | {len(s['farklar'])}/{s['takim']} | {ornek} |")
    l = [s for s in sonuclar if s["sinif"] == "bağlanamadı"]
    if l:
        L += ["", f"## Bağlanamayan resmi tablolar ({len(l)})", "",
              "Takımları hiçbir lig grubumuzla %70 örtüşmüyor. Çoğu ikinci aşama (klasman, play-off, yükselme) tablosu ya da kulüp eşlemesi yapılamamış eski kayıt.", "",
              "| Sezon | Lig | Grup | Kaynak | Takım | Ortak takım |", "|---|---|---|---|---|---|"]
        for s in sorted(l, key=lambda s: (s["sezon"], s["kademe"] or 9, s["grup"])):
            L.append(f"| {s['sezon']} | {KADEME_AD.get(s['kademe'], s['kademe'])} | {s['grup'] or '-'} | {s['kaynak']} | {s['takim']} | {s['ortak']} |")
    if tablosuz:
        by = collections.defaultdict(list)
        for sz, _, kd, g in tablosuz:
            by[(KADEME_AD.get(kd, kd))].append(f"{sz}{' ' + g if g else ''}")
        L += ["", f"## Resmi tablosu olmayan lig gruplarımız ({len(tablosuz)})", ""]
        for lig, l in sorted(by.items(), key=lambda x: str(x[0])):
            L.append(f"- **{lig}** ({len(l)}): {', '.join(l)}")
    open(RAPOR, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"{len(tablolar)} resmi tablo:", dict(say), f"| {tutan_satir}/{satir_say} satır tutuyor | tablosuz grup: {len(tablosuz)} -> {RAPOR}")


if __name__ == "__main__":
    main()

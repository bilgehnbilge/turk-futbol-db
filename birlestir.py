#!/usr/bin/env python3
"""futbol.db: Mackolik (1959-91 ligler, terfi, Turkiye Kupasi), TFF (1984/1990- ligler) ve Avrupa kupalarini birlestirir.

Kulup kimligi (kaynaklar arasi eslestirme):
  1. Mackolik (yeni site uuid) <-> TFF kulupID: TFF'nin Turkiye Kupasi sayfalari (1994-) ile Mackolik kupa maclari ve
     1990-91 2. Lig ortak maclari tarih+skor ile eslenir; belirsiz maclar bilinen eslesmelerle tekrar tekrar cozulur.
  2. Arsiv kimligi <-> Mackolik uuid: arsivin puan tablolarindaki (sezon, kademe) takim satirlari ile Mackolik maclarindan
     hesaplanan O-G-B-M-AG-YG imzalari birebir eslenir. Arsivdeki ad o sezonun DONEM ADI olarak da kullanilir.
  3. 1990 sinirinda kupaya girmeden kaybolan kulupler: 1988-90 Mackolik <-> 1990-93 TFF arasinda ad benzerligi
     (yalnizca tek ve guclu aday varsa; digerleri raporda).
  4. RSSSF (kimliksiz) Intertoto satirlari: o sezon Mackolik'te ayni adi tasiyan Turk kulubu.
Ayni kuluba baglanan birden cok TFF numarasi / Mackolik kimligi 'kulup_kimlik' tablosunda durur ve raporda listelenir
(ardillik adayi: kullanici onaylayinca kulup_ardil'a girer).

Cikti: futbol.db  +  birlestirme_raporu.txt
"""
import collections
import csv
import datetime
import glob
import json
import os
import re
import sqlite3
import sys

import topla

KOK = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(KOK, "futbol.db")
RAPOR = os.path.join(KOK, "birlestirme_raporu.txt")
DUZELTME = os.path.join(KOK, "kulup_duzeltme.json")
TFF_DB = os.path.join(KOK, "raw", "tff.db")
ARSIV = os.path.join(KOK, "raw", "mackolik_arsiv")
TRM = str.maketrans("İIıŞşĞğÜüÖöÇçÂâÎî", "iiissgguuooccaaii")
rapor = []


def yaz(*a):
    s = " ".join(str(x) for x in a)
    rapor.append(s)
    print(s, flush=True)


def norm(ad):
    s = re.sub(r"([a-z])\.(?=[a-z])", r"\1 ", ad.translate(TRM).lower())
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    kis = {"bld": "belediye", "bel": "belediye", "belediyesi": "belediye", "belediyespor": "belediye", "iy": "idmanyurdu",
           "bsb": "buyuksehir", "bb": "buyuksehir", "b": "buyuksehir", "dsi": "dsi",
           "esk": "eskisehir", "ant": "antalya", "adn": "adana", "ank": "ankara", "ist": "istanbul", "izm": "izmir",
           "gb": "genclerbirligi"}
    dur = {"as", "a", "s", "spor", "kulubu", "sk", "fk", "futbol", "ve", "jk", "fsk", "sporkulubu", "sportif", "faaliyetleri"}
    out = []
    for w in s.split():
        w = kis.get(w, w)
        if w.endswith("spor") and len(w) > 6:
            w = w[:-4]
        if w not in dur and len(w) > 1:
            out.append(w)
    return out


def benzer(a, b):
    """a'nin kelimelerinin ne kadari b'de (onek eslesmesi dahil)"""
    A, B = norm(a), norm(b)
    if not A or not B:
        return 0.0
    tut = sum(1 for x in A if x in B or (len(x) >= 4 and any(len(y) >= 4 and (y.startswith(x) or x.startswith(y)) for y in B))
              or (len(x) >= 6 and any(len(y) >= 6 and (y.endswith(x) or x.endswith(y)) for y in B)))
    return tut / len(A)


# ---------------------------------------------------------------- kaynaklari oku
def mackolik_oku():
    with open(os.path.join(KOK, "mackolik_maclar.csv"), encoding="utf-8") as f:
        ms = list(csv.DictReader(f))
    # "kk": kulup kimliginin kaynagi. Arsivden eklenen eksik maclar (kaynak=mackolik_arsiv) yeni sitenin uuid'lerini tasir.
    for x in ms:
        x["kk"] = "mackolik" if x["kaynak"] == "mackolik_arsiv" and not x["ev_id"].isdigit() else x["kaynak"]
    return ms


def avrupa_oku():
    with open(os.path.join(KOK, "avrupa_maclar.csv"), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def tff_oku():
    c = sqlite3.connect(TFF_DB)
    c.row_factory = sqlite3.Row
    ms = [dict(r) for r in c.execute("""SELECT m.*, ke.tff_id ev_tff, kd.tff_id dep_tff FROM mac m
                                        JOIN kulup ke ON ke.id=m.ev_id JOIN kulup kd ON kd.id=m.dep_id""")]
    # 1. Lig 2008-09 sayfalarinda kulupID baglantisi yok: ayni adin baska sezonlardaki numarasi
    ad_no = collections.defaultdict(collections.Counter)
    for m in ms:
        for s in ("ev", "dep"):
            if m[s + "_tff"]:
                ad_no[m[s + "_adi"]][m[s + "_tff"]] += 1
    cozulemeyen = collections.Counter()
    for m in ms:
        for s in ("ev", "dep"):
            if not m[s + "_tff"]:
                aday = ad_no.get(m[s + "_adi"])
                if aday:
                    m[s + "_tff"] = aday.most_common(1)[0][0]
                else:
                    m[s + "_tff"] = "ad:" + m[s + "_adi"]
                    cozulemeyen[m[s + "_adi"]] += 1
    if cozulemeyen:
        yaz("  TFF: kulupID'si olmayan ve adi baska sezonda gecmeyen:", dict(cozulemeyen))
    return ms


# ---------------------------------------------------------------- 1. uuid <-> TFF (kupa + 1990-91)
def uuid_tff(mk, tff):
    gun = collections.defaultdict(list)
    for f in glob.glob(os.path.join(KOK, "raw", "tff_kupa", "kupa_*.html")):
        for m in topla.maclar(topla.oku(f)):
            s = re.fullmatch(r"(\d+)\s*-\s*(\d+)", m["skor"])
            if s and m["tarih"] and m["ev_id"] and m["dep_id"]:
                gun[m["tarih"]].append((m["ev_id"], m["dep_id"], int(s[1]), int(s[2])))
    for m in tff:
        if m["sezon"] == "1990-1991" and m["ev_gol"] is not None:
            gun[m["tarih"]].append((m["ev_tff"], m["dep_tff"], m["ev_gol"], m["dep_gol"]))
    adaylar = []
    for x in mk:
        if x["kaynak"] != "mackolik" or not x["ev_gol"] or not x["tarih"]:
            continue
        if not ((x["yarisma"] == "kupa" and x["sezon"] >= "1994") or x["sezon"] == "1990-1991"):
            continue
        gol = {(int(x["ev_gol"]), int(x["dep_gol"]))}
        if x.get("ev_90"):
            gol.add((int(x["ev_90"]), int(x["dep_90"])))
        ad = []
        for g in (0, -1, 1):
            t = (datetime.date.fromisoformat(x["tarih"]) + datetime.timedelta(g)).isoformat()
            ad = [m for m in gun.get(t, []) if (m[2], m[3]) in gol]
            if ad:
                break
        if ad:
            adaylar.append((x["ev_id"], x["dep_id"], ad, x["sezon"], x["kaynak_id"]))
    esl, oy = {}, {}
    for _ in range(10):
        oy = collections.defaultdict(collections.Counter)
        mac_tff, sez_oy = {}, collections.defaultdict(collections.Counter)   # mac/sezon bazinda hangi TFF numarasi
        for e, d, ad, sezon, kid in adaylar:
            uy = [m for m in ad if (e not in esl or m[0] in esl[e]) and (d not in esl or m[1] in esl[d])]
            if len(uy) == 1:
                oy[e][uy[0][0]] += 1
                oy[d][uy[0][1]] += 1
                mac_tff[(kid, "ev")], mac_tff[(kid, "dep")] = uy[0][0], uy[0][1]
                sez_oy[(e, sezon)][uy[0][0]] += 1
                sez_oy[(d, sezon)][uy[0][1]] += 1
        yeni = {}
        for u, cn in oy.items():
            (t, n), = cn.most_common(1)
            # ikinci bir TFF numarasi da gucluyse (orn. Goztepe'nin iki kaydi) ikisini de tut; main() bu uuid'i
            # tek kulupte birlestirmez, her maci/sezonu kendi TFF numarasina dagitir
            yeni[u] = {a for a, b in cn.items() if b >= max(3, n / 4)} or {t}
        if yeni == esl:
            break
        esl = yeni
    yaz(f"1) Mackolik<->TFF: {len(adaylar)} ortak mac adayi, {len(esl)} Mackolik kulubu TFF numarasina baglandi")
    return esl, oy, mac_tff, sez_oy


# ---------------------------------------------------------------- 2. arsiv id <-> uuid (puan tablosu imzasi)
def arsiv_uuid(mk):
    sid_bilgi = {}
    for f in glob.glob(os.path.join(ARSIV, "sezonlar", "*.txt")):
        etiket = os.path.basename(f)[:-4]
        d = json.loads(open(f, encoding="utf-8").read().strip()[1:-1])
        for sid, ad in d["l"]:
            sid_bilgi[sid] = (etiket, ad)
    imza_mk = collections.defaultdict(lambda: collections.defaultdict(lambda: [0] * 6))
    adlar_mk = {}
    for x in mk:
        if x["asama"] not in ("lig", "play-off") or not x["ev_gol"] or not x["kademe"]:
            continue
        eg, dg = int(x["ev_gol"]), int(x["dep_gol"])
        for kim, ad, a, b in ((x["ev_id"], x["ev_adi"], eg, dg), (x["dep_id"], x["dep_adi"], dg, eg)):
            s = imza_mk[(x["sezon"], x["kademe"], x["kk"])][kim]
            s[0] += 1; s[1] += a > b; s[2] += a == b; s[3] += a < b; s[4] += a; s[5] += b
            adlar_mk[kim] = ad
    esl = collections.defaultdict(collections.Counter)   # arsiv id -> {(kaynak, id): oy}
    donem_adi = {}                                         # (kaynak, id, sezon) -> arsiv adi
    sez_ar = {}                                            # (kaynak, id, sezon) -> arsiv id
    eslesen = toplam = 0
    for f in sorted(glob.glob(os.path.join(ARSIV, "puan", "*.json"))):
        sid = int(os.path.basename(f)[:-5])
        if sid not in sid_bilgi:
            continue
        etiket, ligad = sid_bilgi[sid]
        import mackolik as M
        _, kademe = M.lig_adi_kademe(ligad)
        if not kademe:
            continue
        for r in json.load(open(f, encoding="utf-8"))["s"]:
            toplam += 1
            imza = [r[2] + r[3], r[4] + r[5], r[6] + r[7], r[8] + r[9], r[10] + r[11], r[12] + r[13]]
            aday = []
            for kaynak in ("mackolik", "mackolik_arsiv"):
                for kim, s in imza_mk.get((etiket, str(kademe), kaynak), {}).items():
                    if s == imza:
                        aday.append((benzer(r[1], adlar_mk[kim]) + benzer(adlar_mk[kim], r[1]), kaynak, kim))
            # ayni imzali birden cok takim (nadir): ad benzerligi en yuksek olan
            aday.sort(reverse=True)
            if aday and (len(aday) == 1 or aday[0][0] > aday[1][0]):
                _, kaynak, kim = aday[0]
                esl[str(r[0])][(kaynak, kim)] += 1
                donem_adi[(kaynak, kim, f"{etiket}#{kademe}")] = r[1]
                sez_ar[(kaynak, kim, f"{etiket}#{kademe}")] = str(r[0])
                eslesen += 1
    yaz(f"2) Arsiv<->Mackolik: puan tablosundaki {toplam} takim satirinin {eslesen}'i imzayla eslendi, "
        f"{len(esl)} arsiv kimligi")
    return esl, donem_adi, sez_ar


# ---------------------------------------------------------------- kulup varliklari (birlesim-bul)
class BB:
    def __init__(self):
        self.p = {}

    def bul(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def bir(self, a, b):
        a, b = self.bul(a), self.bul(b)
        if a != b:
            self.p[max(a, b)] = min(a, b)


def main():
    if os.path.exists(DB):
        os.remove(DB)
    mk, av, tff = mackolik_oku(), avrupa_oku(), tff_oku()
    yaz(f"Kaynaklar: Mackolik {len(mk)} mac, Avrupa {len(av)}, TFF {len(tff)}")
    u2t, u2t_oy, mac_tff, sez_oy = uuid_tff(mk, tff)
    a2u, donem_adi, sez_ar = arsiv_uuid(mk)
    dz = json.load(open(DUZELTME, encoding="utf-8")) if os.path.exists(DUZELTME) else {}

    def kim_coz(s):
        k, _, v = s.partition(":")
        return (k, v)
    # Birden cok TFF numarasina giden uuid'ler (Mackolik'in tek kimlikte birlestirdigi ayri kulupler):
    # uuid kulup olarak kullanilmaz; her mac kendi TFF numarasina, mac eslesmediyse sezonun/en yakin sezonun numarasina.
    bol_el = {}
    for b in dz.get("uuid_bol", []):
        for u in {x[s + "_id"] for x in mk for s in ("ev", "dep") if x[s + "_id"].startswith(b["uuid"])}:
            bol_el[u] = b
    # TFF numarasini sezonda kes (orn. 3688: 2007'ye kadar Aliağa, sonra Göztepe): eski kisim '<no>-once' dugumu olur
    kes = {k["tff"]: k for k in dz.get("tff_kes", [])}

    def kes_no(t, sezon):
        return t + "-once" if t in kes and sezon < kes[t]["sinir"] else t
    def kes_adi(t, ad):   # kesilen numaranin eski kismi: TFF'nin sonradan yazdigi ad yerine donem adi
        k = kes.get(t[:-5]) if t.endswith("-once") else None
        return k.get("once_donem_adi", ad) if k else ad
    for m in tff:
        for s in ("ev", "dep"):
            m[s + "_tff"] = kes_no(m[s + "_tff"], m["sezon"])
    cok = {u for u, ts in u2t.items() if len(ts) > 1 or ts & set(kes)} | set(bol_el)
    cok_sez = collections.defaultdict(dict)
    for (u, sezon), cn in sez_oy.items():
        if u in cok:
            cok_sez[u][sezon] = cn.most_common(1)[0][0]

    def cok_dugum(u, sezon, mac):
        if u in bol_el:
            b = bol_el[u]
            return kim_coz(b["once"] if sezon < b["sinir"] else b["sonra"])
        if mac in mac_tff:
            return ("tff", kes_no(mac_tff[mac], sezon))
        ss = cok_sez[u]
        if sezon in ss:
            return ("tff", kes_no(ss[sezon], sezon))
        yakin = min(ss, key=lambda z: abs(int(z[:4]) - int(sezon[:4])))
        return ("tff", kes_no(ss[yakin], sezon))
    # Yeni Mackolik bazi alt lig kuluplerini tek kimlikte birlestirmis (orn. 'K.Erciyesspor' kimligi altinda 1988-89
    # Kayseri Emniyet, 1989-90 Erciyesspor). 1990 oncesi sezonlarda kulup kimligi = arsivin o sezonki kimligi.
    uuid_ar = collections.defaultdict(dict)   # uuid -> {sezon: arsiv id}
    for (kaynak, kim, sezon), a in sez_ar.items():
        if kaynak == "mackolik":
            uuid_ar[kim][sezon] = a

    # arsiv kimligini sezonda kes (orn. 13184: 1967-74 Afyonspor ile 1981'de kurulan Yeni Afyonspor ayni kimlikte)
    akes = {k["arsiv"]: k for k in dz.get("arsiv_kes", [])}

    def dugum(kaynak, kim, sezon, kademe="", mac=None):
        r = dugum_(kaynak, kim, sezon, kademe, mac)
        if r[0] == "mackolik_arsiv" and r[1] in akes and sezon < akes[r[1]]["sinir"]:
            return (r[0], r[1] + "-once")
        return r

    def dugum_(kaynak, kim, sezon, kademe="", mac=None):
        """sezon+kademe: ayni uuid ayni sezonda iki ligde gorunebiliyor (Mackolik'in birlestirdigi farkli kulupler)"""
        if kaynak == "mackolik" and kim in uuid_ar and sezon[:4] < "1990":
            ss = uuid_ar[kim]
            if f"{sezon}#{kademe}" in ss:
                return ("mackolik_arsiv", ss[f"{sezon}#{kademe}"])
            ayni = sorted(k for k in ss if k.split("#")[0] == sezon)
            if ayni:   # kupa: o sezonun (ilk) lig kimligi
                return ("mackolik_arsiv", ss[ayni[0]])
            yakin = min(ss, key=lambda x: abs(int(x[:4]) - int(sezon[:4])))   # arsiv tablosu olmayan sezon (kupa)
            return ("mackolik_arsiv", ss[yakin])
        if kaynak == "mackolik" and kim in cok:
            return cok_dugum(kim, sezon, mac)
        return (kaynak, kim)

    # Mackolik liglerinde 1990-91 TFF'de de var: TFF tercih
    tff_sez = {(m["sezon"], str(m["kademe"])) for m in tff}
    once = len(mk)
    mk = [x for x in mk if not (x["yarisma"] != "kupa" and (x["sezon"], x["kademe"]) in tff_sez)]
    yaz(f"   Mackolik'ten TFF'de de bulunan lig sezonlari cikarildi: {once - len(mk)} mac")

    bb = BB()
    kimlik_ad = collections.defaultdict(collections.Counter)
    kimlik_sezon = collections.defaultdict(set)

    sezon_ad = {}
    lig_sezon = collections.defaultdict(set)   # cakisma kontrolu yalniz lig maclariyla (kupa degil)
    lig_sayi = collections.Counter()

    def gor(k, ad, sezon):
        bb.bul(k)
        kimlik_ad[k][ad] += 1
        kimlik_sezon[k].add(sezon)
        sezon_ad.setdefault((k, sezon), ad)

    yerli = set()
    for kume, yerli_mi in ((mk, True), (av, False)):
        for x in kume:
            for s in ("ev", "dep"):
                if x[s + "_id"]:
                    d_ = dugum(x.get("kk", x["kaynak"]), x[s + "_id"], x["sezon"], x.get("kademe", ""), (x["kaynak_id"], s))
                    ad_ = donem_adi.get((x.get("kk", x["kaynak"]), x[s + "_id"], f'{x["sezon"]}#{x.get("kademe", "")}'), x[s + "_adi"])
                    if x.get("yarisma") == "kupa":   # kupada donem adi bilinmiyor; once lig satirlarinin adi yerlessin
                        kimlik_ad[d_][ad_] += 0
                        kimlik_sezon[d_].add(x["sezon"])
                        bb.bul(d_)
                    else:
                        gor(d_, ad_, x["sezon"])
                        lig_sezon[d_].add(x["sezon"])
                        lig_sayi[(d_, x["sezon"])] += 1
                    if yerli_mi:
                        yerli.add(d_)
    for m in tff:
        for s in ("ev", "dep"):
            gor(("tff", m[s + "_tff"]), m[s + "_adi"], m["sezon"])
            lig_sezon[("tff", m[s + "_tff"])].add(m["sezon"])
            lig_sayi[(("tff", m[s + "_tff"]), m["sezon"])] += 1
    for u, ts in u2t.items():
        if u in cok:
            continue
        for t in ts:
            bb.bir(("mackolik", u), ("tff", t))
    for t, k in kes.items():   # kesilen numaranin parcalari hedef kuluplere
        if k.get("sonra"):
            bb.bir(("tff", t), kim_coz(k["sonra"]))
        if k.get("once_hedef"):
            bb.bir(("tff", t + "-once"), kim_coz(k["once_hedef"]))
    for a, b, *_ in dz.get("ayni", []):   # farkli numarali ama ayni kulup (kullanici/Vikipedi)
        bb.bir(kim_coz(a), kim_coz(b))
    # 3. Sinir: 1990 oncesi arsiv kimlikleri <-> TFF kimlikleri (Super Lig icin sinir 1984, alt ligler icin 1990).
    #    Ayni sezonda ikisinde de mac varsa farkli kulup; aksi halde donem adlari benzerligi + uuid kaniti; bire bir, guclu once.
    def yil(s):
        return int(s[:4])
    ar_d = {k: ss for k, ss in lig_sezon.items() if k[0] == "mackolik_arsiv" and k in yerli}
    tff_g = collections.defaultdict(lambda: dict(ss=set(), ad=collections.Counter(), ids=set()))
    for k, ss in lig_sezon.items():
        if k[0] == "tff":
            g = tff_g[bb.bul(k)]
            g["ss"] |= ss; g["ids"].add(k[1])
            g.setdefault("buyuk", set()).update(z for z in ss if lig_sayi[(k, z)] >= 10)
            for s_ in ss:
                g.setdefault("sad", {})[s_] = sezon_ad.get((k, s_), "")
    uuid_kanit = collections.defaultdict(set)    # arsiv dugumu -> {tff kok}
    for u, ss in uuid_ar.items():
        for t in ([kim_coz(bol_el[u]["once"])[1]] if u in bol_el else u2t.get(u, ())):
            for a in ss.values():
                uuid_kanit[("mackolik_arsiv", a)].add(bb.bul(("tff", t)))
    adaylar = []
    for a, ass in ar_d.items():
        a_ad = {sezon_ad.get((a, s_), "") for s_ in sorted(ass)[-3:]} - {""}
        ay = [yil(s_) for s_ in ass]
        for t, g in tff_g.items():
            # ayni sezonda ikisinde de tam bir lig sezonu (>=10 mac) varsa ayni kulup olamaz (baraj/play-off maci sayilmaz)
            a_buyuk = {z for z in ass if lig_sayi[(a, z)] >= 10}
            if not g["ss"] or min(g["ss"]) > "1993-1994" or (a_buyuk & g["buyuk"]):
                continue
            ty = [yil(s_) for s_ in g["ss"]]
            if min(abs(x - y) for x in ay for y in ty) > 2:
                continue
            # TFF'nin A'ya en yakin sezonlardaki adlari (TFF eski sezonlara bazen sonraki adi yaziyor)
            son_a = max(ay)
            yakin = [z for z in g["ss"] if abs(yil(z) - son_a) <= 4] or sorted(g["ss"], key=lambda z: min(abs(yil(z) - x) for x in ay))[:3]
            t_adlar = {g["sad"][z] for z in yakin} - {""}
            ad_p = max((min(benzer(x, y), 1) + min(benzer(y, x), 1) for x in a_ad for y in t_adlar), default=0)
            kanit = t in uuid_kanit.get(a, ())
            puan = ad_p + (0.5 if kanit else 0)
            if puan >= 1.0:
                adaylar.append((puan, ad_p, kanit, a, t))
    adaylar.sort(key=lambda x: (x[0], x[1]), reverse=True)
    kullanildi_a, kullanildi_t = set(), set()
    sinir_esl, sinir_supheli, sinir_rapor = [], [], []
    # elle duzeltmeler (kulup_duzeltme.json): zorunlu baglar once, yasak baglar aday listesinden cikar
    yasak = {(kim_coz(a), bb.bul(kim_coz(t))) for a, t, *_ in dz.get("baglama", [])}
    adaylar = [x for x in adaylar if (x[3], x[4]) not in yasak]
    for a, t, *_ in dz.get("bagla", []):
        a, t = kim_coz(a), bb.bul(kim_coz(t))
        sinir_esl.append((a, t)); kullanildi_a.add(a); kullanildi_t.add(t)
    for puan, ad_p, kanit, a, t in adaylar:
        if a in kullanildi_a or t in kullanildi_t:
            continue
        a_ad = sorted({sezon_ad.get((a, s_), "") for s_ in sorted(ar_d[a])[-2:]})
        t_ad = sorted({v for v in tff_g[t]["sad"].values() if v})[:3]
        if puan >= 1.5:
            sinir_esl.append((a, t)); kullanildi_a.add(a); kullanildi_t.add(t)
            if ad_p < 2:
                sinir_rapor.append((a_ad, max(ar_d[a]), "->", t_ad, min(tff_g[t]["ss"]), round(puan, 2), "uuid kaniti" if kanit else ""))
        else:
            sinir_supheli.append((a_ad, max(ar_d[a]), "->", t_ad, min(tff_g[t]["ss"]), round(puan, 2)))
    for a, t in sinir_esl:
        bb.bir(a, t)
    # TFF'ye baglanamamis uuid (yalniz 1990-94 kupasi): ayni uuid'nin son arsiv kimligi
    for u, ss in uuid_ar.items():
        k = ("mackolik", u)
        if k in kimlik_sezon and bb.bul(k) not in tff_g and u not in bol_el:
            son_a = ss[max(ss)]
            if bb.bul(("mackolik_arsiv", son_a)) not in tff_g:
                bb.bir(k, ("mackolik_arsiv", son_a))
    yaz(f"3) Sinir (arsiv<->TFF): {len(adaylar)} aday, {len(sinir_esl)} eslesme (tam ad disindakiler raporda: "
        f"{len(sinir_rapor)}), {len(sinir_supheli)} supheli")

    # 4. RSSSF satirlari (kimliksiz): ayni sezon Mackolik kupasinda ayni adli kulup
    ad_sezon = collections.defaultdict(collections.Counter)
    for x in mk:
        if x["kaynak"] == "mackolik":
            for s in ("ev", "dep"):
                ad_sezon[x[s + "_adi"]][x[s + "_id"]] += 1
    for x in av:
        if x["kaynak"] == "rsssf":
            for s in ("ev", "dep"):
                aday = ad_sezon.get(x[s + "_adi"])
                x[s + "_id"] = aday.most_common(1)[0][0] if aday else ""
                if aday:
                    x["kaynak_kimlik_" + s] = "mackolik"

    # ------------------------------------------------ veritabani
    c = sqlite3.connect(DB)
    c.executescript(SEMA)
    kokler = sorted({bb.bul(k) for k in kimlik_sezon}, key=str)
    kok_no = {r: i + 1 for i, r in enumerate(kokler)}

    def kulup_no(kaynak, kim, sezon="", kademe="", mac=None):
        return kok_no[bb.bul(dugum(kaynak, kim, sezon, kademe, mac) if sezon else (kaynak, kim))] if kim else None

    # kulup adi: en son sezonda kullanilan ad (Mackolik yazimi tercih, yoksa TFF)
    son_ad = {}
    for k, ss in kimlik_sezon.items():
        r = bb.bul(k)
        ad = kimlik_ad[k].most_common(1)[0][0]
        anahtar = (max(ss), k[0] in ("mackolik", "rsssf"))
        if r not in son_ad or anahtar > son_ad[r][0]:
            son_ad[r] = (anahtar, ad)
    for t, k in kes.items():
        r = bb.bul(("tff", t + "-once"))
        if r in son_ad and k.get("once_ad"):
            son_ad[r] = (son_ad[r][0], k["once_ad"])
    for r, no in kok_no.items():
        c.execute("INSERT INTO kulup VALUES(?,?)", (no, son_ad[r][1]))
    for k in kimlik_sezon:
        if k[0] == "rsssf":
            continue
        c.execute("INSERT INTO kulup_kimlik VALUES(?,?,?,?,?)",
                  (kok_no[bb.bul(k)], k[0], k[1], min(kimlik_sezon[k]), max(kimlik_sezon[k])))
    # bolunen uuid'ler: kimlik tablosunda en son sezonundaki kulube yazilir (PK tek satir)
    for u in sorted(cok):
        if ("mackolik", u) in kimlik_sezon:
            continue
        ss = sorted({x["sezon"] for x in mk + av if u in (x["ev_id"], x["dep_id"])})
        if ss:
            c.execute("INSERT OR IGNORE INTO kulup_kimlik VALUES(?,?,?,?,?)",
                      (kulup_no("mackolik", u, ss[-1]), "mackolik", u, ss[0], ss[-1]))
    for a in dz.get("ardil", []):
        c.execute("INSERT INTO kulup_ardil VALUES(?,?,?,?,?,?)",
                  (kok_no[bb.bul(kim_coz(a["onceki"]))], kok_no[bb.bul(kim_coz(a["sonraki"]))],
                   a.get("sezon"), a.get("tur"), a.get("aciklama"), "elle"))

    def donem(kaynak, kim, sezon, ad, kademe=""):
        """Mackolik yeni site eski sezonlara bugunku adi yaziyor: arsivin o sezonki adi (varsa)."""
        if kaynak == "mackolik_arsiv":
            return ad
        return donem_adi.get((kaynak, kim, f"{sezon}#{kademe}"), ad)

    # kupa maclari icin donem adi: ayni sezon, ayni kulubun lig adi (arsiv/TFF)
    lig_adi = {}
    for x in mk:
        if x["yarisma"] != "kupa":
            for s in ("ev", "dep"):
                lig_adi[(kulup_no(x["kk"], x[s + "_id"], x["sezon"], x["kademe"], (x["kaynak_id"], s)), x["sezon"])] = \
                    donem(x["kk"], x[s + "_id"], x["sezon"], x[s + "_adi"], x["kademe"])
    for m in tff:   # 1990 sonrasi: TFF'nin o sezonki adi (Mackolik bugunku adi yaziyor)
        for s in ("ev", "dep"):
            lig_adi.setdefault((kulup_no("tff", m[s + "_tff"]), m["sezon"]), kes_adi(m[s + "_tff"], m[s + "_adi"]))

    kulup_lig_sez = collections.defaultdict(list)
    for (no, sezon) in lig_adi:
        kulup_lig_sez[no].append(sezon)

    def kupa_adi(no, sezon, ad):
        """o sezon ligde yoksa (amator, kupa) en yakin sezondaki lig adi (5 yil icinde); yoksa kaynak adi"""
        if (no, sezon) in lig_adi:
            return lig_adi[(no, sezon)]
        ss = [z for z in kulup_lig_sez.get(no, ()) if abs(int(z[:4]) - int(sezon[:4])) <= 5]
        if ss:
            return lig_adi[(no, min(ss, key=lambda z: (abs(int(z[:4]) - int(sezon[:4])), z)))]
        return ad

    satir = []
    for x in mk:
        ek = kulup_no(x["kk"], x["ev_id"], x["sezon"], x["kademe"], (x["kaynak_id"], "ev"))
        dk = kulup_no(x["kk"], x["dep_id"], x["sezon"], x["kademe"], (x["kaynak_id"], "dep"))
        if x["yarisma"] == "kupa":
            ea, da = kupa_adi(ek, x["sezon"], x["ev_adi"]), kupa_adi(dk, x["sezon"], x["dep_adi"])
        else:
            ea = donem(x["kk"], x["ev_id"], x["sezon"], x["ev_adi"], x["kademe"])
            da = donem(x["kk"], x["dep_id"], x["sezon"], x["dep_adi"], x["kademe"])
        yarisma = "kupa" if x["yarisma"] == "kupa" else "terfi" if x["yarisma"] == "terfi" else "lig"
        satir.append((x["kaynak"], x["kaynak_id"], yarisma, x["lig"], int(x["kademe"]) if x["kademe"] else None, x["sezon"],
                      x["grup"] or None, x["asama"], None, x["tarih"] or None, x["saat"] or None, ek, dk, ea, da,
                      x["ev_adi"], x["dep_adi"], *gol(x), x["durum"] or None, x["kazanan"] or None, None))
    for m in tff:
        hafta_tur = m["asama"] if m["asama"] not in ("lig", "play-off") else None
        satir.append(("tff", m["kaynak_id"], "lig", m["lig"], m["kademe"], m["sezon"], m["grup"],
                      "lig" if m["asama"] == "lig" else "play-off", hafta_tur, m["tarih"], m["saat"],
                      kulup_no("tff", m["ev_tff"]), kulup_no("tff", m["dep_tff"]),
                      kes_adi(m["ev_tff"], m["ev_adi"]), kes_adi(m["dep_tff"], m["dep_adi"]), m["ev_adi"], m["dep_adi"],
                      m["ev_gol"], m["dep_gol"], None, None, m["ev_pen"], m["dep_pen"],
                      "MS" if m["ev_gol"] is not None else None, None, m["ham_skor"] if m["ev_gol"] is None and m["ham_skor"] else None))
    for x in av:
        kk = x.get("kaynak_kimlik_ev", x["kaynak"]), x.get("kaynak_kimlik_dep", x["kaynak"])
        ek = kulup_no(kk[0], x["ev_id"], x["sezon"], "", (x["kaynak_id"], "ev")) if x["ev_id"] else None
        dk = kulup_no(kk[1], x["dep_id"], x["sezon"], "", (x["kaynak_id"], "dep")) if x["dep_id"] else None
        satir.append((x["kaynak"], x["kaynak_id"], "avrupa", x["lig"], None, x["sezon"], None, "avrupa", x["tur"] or None,
                      x["tarih"] or None, x["saat"] or None, ek, dk, x["ev_adi"], x["dep_adi"], x["ev_adi"], x["dep_adi"],
                      *gol(x), x["durum"] or None, x["kazanan"] or None, x.get("not") or None))
    c.executemany(f"INSERT INTO mac VALUES(NULL,{','.join('?' * 26)})", satir)
    # TFF grup sayfalarinda tek tuk gorunen dis takim maclari (gruplar arasi final/baraj): grupta en fazla 2 maci olan
    # takimin maclari, grubun geri kalani tam bir lig ise (>=6 takim, takim basina >=10 mac) play-off sayilir.
    once_deg = c.total_changes
    c.execute("""
      WITH m AS (SELECT id, kademe, sezon, COALESCE(grup,'') g, ev_kulup, dep_kulup FROM mac WHERE kaynak='tff' AND asama='lig'),
           t AS (SELECT kademe, sezon, g, ev_kulup k, id FROM m UNION ALL SELECT kademe, sezon, g, dep_kulup, id FROM m),
           n AS (SELECT kademe, sezon, g, k, COUNT(*) n FROM t GROUP BY 1,2,3,4),
           buyuk AS (SELECT kademe, sezon, g FROM n WHERE n >= 10 GROUP BY 1,2,3 HAVING COUNT(*) >= 6)
      UPDATE mac SET asama='play-off' WHERE id IN (
        SELECT t.id FROM t JOIN n USING(kademe, sezon, g, k) JOIN buyuk USING(kademe, sezon, g) WHERE n.n <= 2)""")
    po = c.total_changes - once_deg
    yaz(f"   TFF grup sayfalarindaki tekil dis takim maclari play-off sayildi: {po}")
    resmi_tablolar(c, lambda node: kok_no.get(bb.bul(node)) if node in bb.p else None, kes_no, dugum)
    for d in dz.get("donem_adi", []):   # elle donem adi (orn. Vikipedi'den eski adlar)
        no = kok_no[bb.bul(kim_coz(d["kim"]))]
        for s in ("ev", "dep"):   # "eski" verilmisse yalniz o adla yazilmis maclar
            c.execute(f"UPDATE mac SET {s}_adi=? WHERE {s}_kulup=? AND sezon BETWEEN ? AND ? AND (? IS NULL OR {s}_adi=?)",
                      (d["ad"], no, d["ilk"], d["son"], d.get("eski"), d.get("eski")))
    c.execute("""INSERT INTO kulup_adi
                 SELECT kulup, ad, MIN(sezon), MAX(sezon), COUNT(*) FROM
                   (SELECT ev_kulup kulup, ev_adi ad, sezon FROM mac UNION ALL SELECT dep_kulup, dep_adi, sezon FROM mac)
                 WHERE kulup IS NOT NULL GROUP BY 1, 2""")
    c.commit()

    # ------------------------------------------------ rapor
    yaz("\nfutbol.db:", c.execute("SELECT COUNT(*) FROM mac").fetchone()[0], "mac,",
        c.execute("SELECT COUNT(*) FROM kulup").fetchone()[0], "kulup")
    for r in c.execute("SELECT yarisma, COUNT(*), MIN(sezon), MAX(sezon) FROM mac GROUP BY 1"):
        yaz("  ", *r)
    yaz("\nBirden cok TFF numarasi ya da birden cok Mackolik kimligi tek kulupte birlesen kulupler (ARDILLIK ADAYI):")
    for no, ad in c.execute("""SELECT k.id, k.ad FROM kulup k JOIN kulup_kimlik i ON i.kulup_id=k.id
                               GROUP BY k.id HAVING SUM(i.kaynak='tff')>1 OR SUM(i.kaynak='mackolik')>1 ORDER BY k.ad"""):
        ids = c.execute("SELECT kaynak, kaynak_id, ilk_sezon, son_sezon FROM kulup_kimlik WHERE kulup_id=? AND kaynak IN ('tff','mackolik') ORDER BY ilk_sezon", (no,)).fetchall()
        adlar = [a for a, in c.execute("SELECT ad FROM kulup_adi WHERE kulup_id=? ORDER BY ilk_sezon", (no,))]
        yaz(f"  [{no}] {ad}: " + "; ".join(f"{k}:{i[:10]} {a}..{b}" for k, i, a, b in ids) + " | adlar: " + ", ".join(adlar[:6]))
    yaz("\n1990 sinirinda ADLA eslenen kulupler (arsiv adi, son sezon -> TFF adi, ilk sezon, puan) -- kontrol edilmeli:")
    for s_ in sinir_rapor:
        yaz("  ", s_)
    yaz("\n1990 sinirinda emin olunamayan eslesmeler (BAGLANMADI):")
    for s in sinir_supheli:
        yaz("  ", s)
    # sezon tamligi: her lig grubunda bulunan mac / cift devreli beklenen (n*(n-1))
    c.execute("""CREATE TABLE kapsam AS
      WITH m AS (SELECT kademe, sezon, COALESCE(grup,'') grup, ev_kulup, dep_kulup FROM mac WHERE yarisma='lig' AND asama='lig'),
           t AS (SELECT kademe, sezon, grup, ev_kulup k FROM m UNION SELECT kademe, sezon, grup, dep_kulup FROM m),
           n AS (SELECT kademe, sezon, grup, COUNT(*) takim FROM t GROUP BY 1,2,3),
           b AS (SELECT kademe, sezon, grup, COUNT(*) bulunan FROM m GROUP BY 1,2,3)
      SELECT n.kademe, n.sezon, n.grup, n.takim, b.bulunan, n.takim*(n.takim-1) beklenen FROM n JOIN b USING(kademe, sezon, grup)""")
    c.commit()
    tam, top = c.execute("SELECT SUM(bulunan=beklenen), COUNT(*) FROM kapsam").fetchone()
    yaz(f"\nSezon tamligi: {top} lig grubunun {tam}'inde mac sayisi tam (n*(n-1)). Tutmayanlar (kademe, sezon, grup, takim, bulunan, beklenen):")
    for r in c.execute("SELECT * FROM kapsam WHERE bulunan<>beklenen ORDER BY sezon, kademe, grup"):
        yaz("  ", r)
    yaz("\nKulubu bulunamayan mac tarafi:",
        c.execute("SELECT COUNT(*) FROM mac WHERE ev_kulup IS NULL OR dep_kulup IS NULL").fetchone()[0])
    open(RAPOR, "w", encoding="utf-8").write("\n".join(rapor) + "\n")


# ---------------------------------------------------------------- resmi puan durumlari ve hukmen maclar
def resmi_tablolar(c, no_bul, kes_no, dugum):
    """TFF grup sayfalarindaki ve Mackolik arsivindeki resmi puan durumlarini puan_durumu tablosuna yazar
    (puan silmeleriyle), sonra resmi tablo ile mac listesi arasindaki farki hukmen maclarla kapatir."""
    import mackolik as M
    tablolar = []   # (kaynak, sezon, kademe, [satir dict(kulup, ad, sira, O,G,B,M,A,Y,P,silme)])
    t = sqlite3.connect(TFF_DB)
    grp = collections.defaultdict(list)
    for r in t.execute("SELECT sezon, kademe, COALESCE(grup,''), sira, tff_id, ad, O, G, B, M, A, Y, P FROM puan ORDER BY rowid"):
        grp[(r[0], r[1], r[2])].append(r)
    for (sezon, kademe, _), rs in grp.items():
        w = 3 if sezon[:4] >= "1987" else 2
        tablolar.append(("tff", sezon, kademe, [dict(kulup=no_bul(("tff", kes_no(r[4], sezon))) if r[4] else None, ad=r[5], sira=r[3],
                                                     O=r[6], G=r[7], B=r[8], M=r[9], A=r[10], Y=r[11], P=r[12], silme=r[12] - (r[7] * w + r[8]))
                                                for r in rs]))
    sid_bilgi = {}
    for f in glob.glob(os.path.join(ARSIV, "sezonlar", "*.txt")):
        d = json.loads(open(f, encoding="utf-8").read().strip()[1:-1])
        for sid, ad in d["l"]:
            sid_bilgi[sid] = (os.path.basename(f)[:-4], ad)
    for f in sorted(glob.glob(os.path.join(ARSIV, "puan", "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        if d["id"] not in sid_bilgi:
            continue
        etiket, ligad = sid_bilgi[d["id"]]
        _, kademe = M.lig_adi_kademe(ligad)
        satir = []
        for i, r in enumerate(d["s"]):
            silme = r[17] if isinstance(r[17], int) else 0
            satir.append(dict(kulup=no_bul(dugum("mackolik_arsiv", str(r[0]), etiket, str(kademe or ""))), ad=r[1], sira=i + 1,
                              O=r[2] + r[3], G=r[4] + r[5], B=r[6] + r[7], M=r[8] + r[9], A=r[10] + r[11], Y=r[12] + r[13],
                              P=r[14] + r[15] + silme, silme=silme))
        tablolar.append(("mackolik_arsiv", etiket, kademe, satir))

    # tabloyu mac grubuna bagla: ayni sezonda takimlari en cok ortusen lig/terfi grubu (TFF'nin hatali tekrar
    # tablolari -- 2007-10 2. Lig'de her grup sayfasi 01'in tablosunu gosterir -- elenir)
    gruplar = collections.defaultdict(set)
    for y, kd, sz, g, e, dp in c.execute("""SELECT yarisma, kademe, sezon, COALESCE(grup,''), ev_kulup, dep_kulup FROM mac
                                            WHERE yarisma IN ('lig','terfi') AND asama='lig'"""):
        gruplar[(sz, y, kd, g)] |= {e, dp}
    sezon_gruplari = collections.defaultdict(list)
    for k in gruplar:
        sezon_gruplari[k[0]].append(k)
    secilen = {}
    for kaynak, sezon, kademe, satir in tablolar:
        ks = {s["kulup"] for s in satir if s["kulup"]}
        if not ks:
            continue
        aday = max(sezon_gruplari.get(sezon, []), key=lambda g: (len(ks & gruplar[g]), g[2] == kademe), default=None)
        if not aday:
            continue
        ort = len(ks & gruplar[aday]) / len(satir)
        if ort < 0.7 or len(gruplar[aday] - {None}) > len(satir) + 2:
            continue
        onc = (kaynak == "tff", ort)
        if aday not in secilen or onc > secilen[aday][0]:
            secilen[aday] = (onc, kaynak, satir)
    c.execute("""CREATE TABLE puan_durumu(kaynak TEXT, yarisma TEXT, kademe INTEGER, sezon TEXT, grup TEXT, sira INTEGER,
                 kulup INTEGER, ad TEXT, O INTEGER, G INTEGER, B INTEGER, M INTEGER, AG INTEGER, YG INTEGER, P INTEGER, puan_silme INTEGER)""")
    for (sezon, y, kd, g), (_, kaynak, satir) in secilen.items():
        for s in satir:
            c.execute("INSERT INTO puan_durumu VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (kaynak, y, kd, sezon, g or None, s["sira"], s["kulup"], s["ad"], s["O"], s["G"], s["B"], s["M"],
                       s["A"], s["Y"], s["P"], s["silme"]))
    silme = c.execute("SELECT COUNT(*) FROM puan_durumu WHERE puan_silme<>0").fetchone()[0]
    yaz(f"   Resmi puan durumu: {len(tablolar)} tablo okundu, {len(secilen)} lig grubuna baglandi; puan silme/ek puan satiri: {silme}")

    # hukmen: resmi tabloda sayilip bizde skoru olmayan ya da hic olmayan maclar
    eklenen = guncel = 0
    for (sezon, y, kd, g), (_, kaynak, satir) in secilen.items():
        resmi = {s["kulup"]: s for s in satir if s["kulup"]}
        ms = c.execute(f"""SELECT id, ev_kulup, dep_kulup, ev_gol, dep_gol FROM mac WHERE sezon=? AND yarisma=? AND asama='lig'
                           AND COALESCE(grup,'')=? AND kademe IS ?""", (sezon, y, g, kd)).fetchall()
        lig = c.execute("SELECT lig FROM mac WHERE id=?", (ms[0][0],)).fetchone()[0] if ms else None
        biz = collections.defaultdict(lambda: dict(O=0, G=0, B=0, M=0, A=0, Y=0))
        cift = collections.Counter()
        for _, e, d, eg, dg in ms:
            cift[(e, d)] += 1
            if eg is None:
                continue
            for k, a, b in ((e, eg, dg), (d, dg, eg)):
                x = biz[k]; x["O"] += 1; x["A"] += a; x["Y"] += b
                x["G" if a > b else "M" if a < b else "B"] += 1
        acik = {k: {f: resmi[k][f] - biz[k][f] for f in ("O", "G", "B", "M", "A", "Y")} for k in resmi}
        if not any(v["O"] > 0 for v in acik.values()):
            continue
        tur = max(cift.values(), default=1)   # devre sayisi
        adaylar = [(mid, e, d) for mid, e, d, eg, dg in ms if eg is None] + \
                  [(None, e, d) for e in resmi for d in resmi if e != d for _ in range(max(0, tur - cift[(e, d)]))]
        for mid, e, d in adaylar:
            ae, ad_ = acik.get(e), acik.get(d)
            if not ae or not ad_ or ae["O"] <= 0 or ad_["O"] <= 0:
                continue
            if ad_["M"] > 0 and ae["G"] > 0 and ad_["Y"] >= 3 and ae["A"] >= 3:
                eg, dg = 3, 0
            elif ae["M"] > 0 and ad_["G"] > 0 and ae["Y"] >= 3 and ad_["A"] >= 3:
                eg, dg = 0, 3
            else:
                continue
            for x, a, b in ((ae, eg, dg), (ad_, dg, eg)):
                x["O"] -= 1; x["A"] -= a; x["Y"] -= b; x["G" if a > b else "M"] -= 1
            if mid:
                c.execute("UPDATE mac SET ev_gol=?, dep_gol=?, durum='Hük.', notlar=? WHERE id=?",
                          (eg, dg, "Resmi puan tablosuna göre hükmen sonuç", mid)); guncel += 1
            else:
                ea = next((s["ad"] for s in satir if s["kulup"] == e), None)
                da = next((s["ad"] for s in satir if s["kulup"] == d), None)
                c.execute(f"INSERT INTO mac VALUES(NULL,{','.join('?' * 26)})",
                          ("hukmen", f"{sezon}/{g}/{e}-{d}", y, lig,
                           kd, sezon, g or None, "lig", None, None, None, e, d, ea, da, ea, da, eg, dg, None, None, None, None,
                           "Hük.", None, "Maç oynanmadı; resmi puan tablosuna göre hükmen sonuç"))
                eklenen += 1
        # butun maclari hukmen kaybeden takim (orn. Ankaraspor 2009-10): oynanmis gorunen maclari da hukmen
        for k, s in resmi.items():
            if s["O"] and s["G"] == s["B"] == 0 and s["A"] == 0 and s["Y"] == 3 * s["O"]:
                c.execute(f"""UPDATE mac SET durum='Hük.' WHERE sezon=? AND yarisma=? AND COALESCE(grup,'')=? AND kademe IS ?
                              AND (ev_kulup=? AND ev_gol=0 AND dep_gol=3 OR dep_kulup=? AND ev_gol=3 AND dep_gol=0)""",
                          (sezon, y, g, kd, k, k))
    yaz(f"   Hukmen: {guncel} skorsuz maca resmi tablodan sonuc yazildi, {eklenen} oynanmamis mac eklendi")


def gol(x):
    def i(v):
        return int(v) if v not in ("", None) else None
    return i(x["ev_gol"]), i(x["dep_gol"]), i(x.get("ev_90")), i(x.get("dep_90")), i(x.get("ev_pen")), i(x.get("dep_pen"))


SEMA = """
CREATE TABLE kulup(id INTEGER PRIMARY KEY, ad TEXT);
CREATE TABLE kulup_kimlik(kulup_id INTEGER, kaynak TEXT, kaynak_id TEXT, ilk_sezon TEXT, son_sezon TEXT,
  PRIMARY KEY(kaynak, kaynak_id));
CREATE TABLE kulup_adi(kulup_id INTEGER, ad TEXT, ilk_sezon TEXT, son_sezon TEXT, mac_sayisi INTEGER, PRIMARY KEY(kulup_id, ad));
CREATE TABLE kulup_ardil(onceki_kulup INTEGER, sonraki_kulup INTEGER, sezon TEXT, tur TEXT, aciklama TEXT, kaynak TEXT);
CREATE TABLE mac(id INTEGER PRIMARY KEY, kaynak TEXT, kaynak_id TEXT, yarisma TEXT, lig TEXT, kademe INTEGER, sezon TEXT,
  grup TEXT, asama TEXT, tur TEXT, tarih TEXT, saat TEXT, ev_kulup INTEGER, dep_kulup INTEGER,
  ev_adi TEXT, dep_adi TEXT, ev_kaynak_adi TEXT, dep_kaynak_adi TEXT,
  ev_gol INTEGER, dep_gol INTEGER, ev_90 INTEGER, dep_90 INTEGER, ev_pen INTEGER, dep_pen INTEGER,
  durum TEXT, kazanan TEXT, notlar TEXT);
CREATE INDEX mac_ev ON mac(ev_kulup); CREATE INDEX mac_dep ON mac(dep_kulup); CREATE INDEX mac_sezon ON mac(sezon, kademe);
CREATE UNIQUE INDEX mac_kaynak ON mac(kaynak, kaynak_id);
-- her mac iki satir: takimin gozunden. Istatistiklerde durum IN ('MS','UZ','Pen','Hük.') ve gol dolu olanlar kullanilir.
CREATE VIEW takim_maci AS
  SELECT id mac_id, yarisma, lig, kademe, sezon, grup, asama, tur, tarih, ev_kulup kulup, ev_adi takim, dep_kulup rakip_kulup,
         dep_adi rakip, 'ev' saha, ev_gol attigi, dep_gol yedigi, ev_gol-dep_gol fark, durum FROM mac WHERE ev_gol IS NOT NULL
  UNION ALL
  SELECT id, yarisma, lig, kademe, sezon, grup, asama, tur, tarih, dep_kulup, dep_adi, ev_kulup, ev_adi, 'deplasman',
         dep_gol, ev_gol, dep_gol-ev_gol, durum FROM mac WHERE ev_gol IS NOT NULL;
"""

if __name__ == "__main__":
    main()

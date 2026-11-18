#!/usr/bin/env python3
"""TFF'de teknik direktörü boş kalan maçlar için Maçkolik arşivinin takım fikstürlerindeki teknik direktör değişikliği
işaretleri (arsiv.mackolik.com, takım sayfası > fikstür: "Teknik direktör değişikliği — Eski: X, Yeni: Y").

  python3 mackolik_td.py say      # ağa çıkmadan: kaç takım-sezon boş, kaçının arşiv numarası biliniyor, kaçı indi
  python3 mackolik_td.py indir    # yarıda kalırsa aynı komut kaldığı yerden sürer (istekler arası 40 sn, arşiv kotası)
  python3 mackolik_td.py cikar    # ağa çıkmadan: indirilen fikstürlerden boş maçların teknik direktörü -> raw/mackolik_td/ek.json

İstek: /AjaxHandlers/TeamHandler.aspx?command=teamtabs&id=<arşiv takım no>&seasonName=<2026/2027>&type=1&viewType=0
(Team.js'ten, 2026-11-17). Her takım-sezon için tek istek. Değişiklik işareti yeni teknik direktörün ilk maçında durur.
Arşiv takım numaraları: futbol.db'deki Maçkolik arşivi kimlikleri; bilinmeyenler indirilen fikstürlerdeki rakiplerden
(aynı gün oynanan maçla) bulunur -> raw/mackolik_td/takim_no.json.
Maçkolik isteklerini kullanıcı çalıştırır (robots.txt, anthropic-ai).
"""
import collections, datetime, json, os, random, re, sqlite3, subprocess, sys, time

import mackolik as M

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "mackolik_td")
NO = os.path.join(HAM, "takim_no.json")
BEKLE = M.ARSIV_BEKLE


def bos_takim_sezonlar():
    """{(kulüp, sezon): [(tarih, TFF maç no, taraf)]}: TFF sayfasında teknik direktörü boş (2007-08 ve sonrası)."""
    o = sqlite3.connect(os.path.join(KOK, "raw", "oyuncu.db"))
    f = sqlite3.connect(os.path.join(KOK, "futbol.db"))
    tk = collections.defaultdict(set)
    for m, t in o.execute("SELECT mac, taraf FROM teknik"):
        tk[m].add(t)
    out = collections.defaultdict(list)
    for kid, sz, tarih, ev, dep in f.execute("""SELECT kaynak_id, sezon, tarih, ev_kulup, dep_kulup FROM mac
                                                WHERE kaynak='tff' AND sezon>='2007-2008' AND ev_gol IS NOT NULL AND tarih IS NOT NULL"""):
        for t, c in ((1, ev), (2, dep)):
            if t not in tk.get(kid, ()) and c is not None:
                out[(c, sz)].append((tarih, kid, t))
    return out


def numaralar():
    f = sqlite3.connect(os.path.join(KOK, "futbol.db"))
    no = {}
    for k, a in f.execute("SELECT kulup_id, kaynak_id FROM kulup_kimlik WHERE kaynak='mackolik_arsiv' ORDER BY son_sezon"):
        no[str(k)] = a.split("-")[0]
    if os.path.exists(NO):
        no.update(json.load(open(NO, encoding="utf-8")))
    return no


def yol(aid, sezon):
    return os.path.join(HAM, f"{aid}_{sezon}.html")


def satirlar(t):
    """[(tarih, ev arşiv no, dep arşiv no, eski, yeni)]"""
    out = []
    for tr in re.split(r"<tr\b", t)[1:]:
        tarih = re.search(r'itemprop="startDate" content="(\d{4}-\d\d-\d\d)', tr)
        ids = re.findall(r"Takim/(\d+)/", tr)
        if not tarih or len(ids) < 1:
            continue
        d = re.search(r"Eski:\s*(.*?)\s*Yeni:\s*(.*?)'", tr, re.S)
        out.append((tarih.group(1), ids, (d.group(1).strip(), d.group(2).strip()) if d else None))
    return out


def ogren(no, kulup, sezon, aid, f):
    """İndirilen fikstürdeki rakiplerin arşiv numaralarını, aynı gün oynanan maçtan bizim kulüplere bağla."""
    t = open(yol(aid, sezon), encoding="utf-8").read()
    bizim = collections.defaultdict(list)
    for tarih, ev, dep in f.execute("SELECT tarih, ev_kulup, dep_kulup FROM mac WHERE sezon=? AND (ev_kulup=? OR dep_kulup=?) AND tarih IS NOT NULL",
                                    (sezon, kulup, kulup)):
        bizim[tarih].append(dep if ev == kulup else ev)
    yeni = 0
    for tarih, ids, _ in satirlar(t):
        rakip = [i for i in ids if i != aid]
        if len(rakip) != 1:
            continue
        g = datetime.date.fromisoformat(tarih)
        aday = [k for d in (0, -1, 1) for k in bizim.get((g + datetime.timedelta(d)).isoformat(), [])]
        if len(set(aday)) == 1 and str(aday[0]) not in no:
            no[str(aday[0])] = rakip[0]; yeni += 1
    return yeni


def indir():
    os.makedirs(HAM, exist_ok=True)
    hedef = bos_takim_sezonlar()
    no = numaralar()
    f = sqlite3.connect(os.path.join(KOK, "futbol.db"))
    sira = sorted(hedef, key=lambda x: (-len(hedef[x]), x[1]))
    yapilan, engel = set(), 0
    while True:
        bekleyen = [x for x in sira if x not in yapilan and str(x[0]) in no and not os.path.exists(yol(no[str(x[0])], x[1]))]
        # zaten inmiş fikstürlerden de rakip numarası öğren
        for x in sira:
            if x not in yapilan and str(x[0]) in no and os.path.exists(yol(no[str(x[0])], x[1])):
                ogren(no, x[0], x[1], no[str(x[0])], f); yapilan.add(x)
        json.dump(no, open(NO, "w", encoding="utf-8"), indent=0)
        bekleyen = [x for x in sira if x not in yapilan and str(x[0]) in no and not os.path.exists(yol(no[str(x[0])], x[1]))]
        if not bekleyen:
            break
        kulup, sezon = bekleyen[0]
        aid = no[str(kulup)]
        sn = sezon.replace("-", "/")
        r = subprocess.run(["curl", "-sL", "--compressed", "-m", "60", "-A", M.UA, "-w", "\n%{http_code}", "-e", f"{M.ARSIV}/Takim/{aid}/",
                            f"{M.ARSIV}/AjaxHandlers/TeamHandler.aspx?command=teamtabs&id={aid}&seasonName={sn}&type=1&viewType=0"],
                           capture_output=True, text=True)
        govde, _, kod = r.stdout.rpartition("\n")
        if kod in ("429", "403"):
            engel += 1
            if engel >= 3:
                sys.exit(f"Arşiv sitesi üst üste {engel} kez engelledi (HTTP {kod}). Birkaç saat sonra aynı komutla devam edin.")
            print(f"  HTTP {kod}: {15 * engel} dk ara veriliyor", flush=True)
            time.sleep(900 * engel)
            continue
        engel = 0
        if kod == "200" and "tblFixture" in govde:
            with open(yol(aid, sezon) + ".tmp", "w", encoding="utf-8") as g:
                g.write(govde)
            os.replace(yol(aid, sezon) + ".tmp", yol(aid, sezon))
            n = ogren(no, kulup, sezon, aid, f)
        else:
            print(f"  {aid} {sezon}: HTTP {kod}, fikstür yok", flush=True)
            open(yol(aid, sezon), "w").close()   # boş: bir daha deneme
            n = 0
        yapilan.add((kulup, sezon))
        print(f"  {len(yapilan)}/{len(sira)} {sezon} takım {aid}: {len(hedef[(kulup, sezon)])} boş maç, {n} yeni takım no "
              f"{time.strftime('%H:%M')}", flush=True)
        json.dump(no, open(NO, "w", encoding="utf-8"), indent=0)
        time.sleep(BEKLE + random.uniform(0, 5))
    print(f"Bitti. Numarası bulunamayan takım-sezon: {sum(1 for x in sira if str(x[0]) not in no)}", flush=True)


def cikar():
    """Boş maçların teknik direktörü: takım-sezon fikstüründeki değişiklik işaretleri + TFF'de bilinen maçlar."""
    hedef = bos_takim_sezonlar()
    no = numaralar()
    o = sqlite3.connect(os.path.join(KOK, "raw", "oyuncu.db"))
    f = sqlite3.connect(os.path.join(KOK, "futbol.db"))
    tff_td = collections.defaultdict(list)   # (kulüp, sezon) -> [(tarih, ad)]
    taraf_kulup = {}
    for kid, sz, tarih, ev, dep in f.execute("SELECT kaynak_id, sezon, tarih, ev_kulup, dep_kulup FROM mac WHERE kaynak='tff' AND sezon>='2007-2008'"):
        taraf_kulup[kid] = (sz, tarih, ev, dep)
    for mac, taraf, ad in o.execute("SELECT mac, taraf, ad FROM teknik"):
        x = taraf_kulup.get(mac)
        if x:
            tff_td[(x[2] if taraf == 1 else x[3], x[0])].append((x[1], ad))
    ek, say = [], collections.Counter()
    for (kulup, sezon), l in hedef.items():
        aid = no.get(str(kulup))
        p = yol(aid, sezon) if aid else None
        if not p or not os.path.exists(p):
            say["fikstür yok"] += len(l); continue
        degisim = sorted((d, e, y) for d, _, ey in satirlar(open(p, encoding="utf-8").read()) for e, y in ([ey] if ey else []))
        bilinen = sorted(tff_td.get((kulup, sezon), []))
        for tarih, mac, taraf in l:
            onceki = [x for x in degisim if x[0] <= tarih]
            sonraki = [x for x in degisim if x[0] > tarih]
            ad = onceki[-1][2] if onceki else sonraki[0][1] if sonraki else None
            if ad is None:   # sezonda değişiklik yok: TFF'de o takım-sezonda yazan tek teknik direktör
                adlar = {a for _, a in bilinen}
                ad = next(iter(adlar)) if len(adlar) == 1 else None
            if ad:
                ek.append([mac, taraf, ad]); say["dolduruldu"] += 1
            else:
                say["bulunamadı"] += 1
    json.dump(ek, open(os.path.join(HAM, "ek.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(dict(say), "->", os.path.join(HAM, "ek.json"))


def say():
    hedef = bos_takim_sezonlar()
    no = numaralar()
    bilinen = [x for x in hedef if str(x[0]) in no]
    indi = [x for x in bilinen if os.path.exists(yol(no[str(x[0])], x[1]))]
    print(f"boş takım-sezon: {len(hedef)} ({sum(len(v) for v in hedef.values())} maç), arşiv numarası bilinen: {len(bilinen)}, indi: {len(indi)}")



def sade(s):
    import unicodedata
    s = (s or "").replace("İ", "i").replace("I", "ı").lower().replace("ı", "i")
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).split())


def ek_satirlar(o):
    """raw/mackolik_td/ek.json -> teknik tablosuna eklenecek satırlar [(TFF maç no, taraf, TFF antrenör no, ad)]: Maçkolik'teki ad
    TFF'de teknik direktör olarak yazılı tek bir kişiyle tutanlar (tff_detay ve web_aktar teknik tablosuyla birlikte okur)."""
    y = os.path.join(HAM, "ek.json")
    if not os.path.exists(y):
        return []
    adlar = collections.defaultdict(collections.Counter)
    for kisi, ad in o.execute("SELECT kisi, ad FROM teknik"):
        adlar[sade(ad)][(kisi, ad)] += 1
    import zlib
    out = []
    for mac, taraf, ad in json.load(open(y, encoding="utf-8")):
        if not mac or not ad:
            continue
        k = adlar.get(sade(ad))
        if k and len({x[0] for x in k}) == 1:
            kisi, tad = k.most_common(1)[0][0]
        elif k:
            continue   # aynı adda birden çok TFF antrenörü
        else:   # TFF'de teknik direktör kaydı yok: ada bağlı kalıcı no (80 milyon + adın sağlama toplamı)
            kisi, tad = 80_000_000 + zlib.crc32(sade(ad).encode()) % 10_000_000, ad
        out.append((str(mac), taraf, kisi, tad))
    return out

if __name__ == "__main__":
    {"indir": indir, "say": say, "cikar": cikar}[sys.argv[1] if len(sys.argv) > 1 else "say"]()

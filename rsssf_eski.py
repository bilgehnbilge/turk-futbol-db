#!/usr/bin/env python3
"""1959 öncesi Türk futbolu: RSSSF'nin Türkiye sayfaları (Baki Demirkiran; rsssf.org/tablest/tur<yıl>.html).

  python3 rsssf_eski.py indir     # raw/rsssf_eski/ (sayfa başına bir istek, var olanı atlar)
  python3 rsssf_eski.py ayikla    # ağa çıkmadan -> raw/rsssf_eski/eski.json (maçlar, puan tabloları, gol kralları)

Yarışmalar: Türkiye Futbol Şampiyonası (1924-1951), Millî Küme (1937-1951), Başbakanlık Kupası (1944-1950),
Federasyon Kupası (1956-57, 1957-58). Millî Küme'nin maçları sonuç tablosundan (ev sahibi satırda, tarih yok);
öbürleri tur tur maç listelerinden (tarih çoğunlukla var). Başbakanlık Kupası maçlarında goller ve dakikaları yazılı.
"""
import html, json, os, re, subprocess, sys, time

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "rsssf_eski")
CIKTI = os.path.join(HAM, "eski.json")
UA = "turk-futbol-db/0.1 (kisisel arsiv)"
SAYFALAR = ["tur24", "tur27", "tur32", "tur33", "tur34", "tur35", "tur37", "tur38", "tur39", "tur40", "tur41", "tur42",
            "tur43", "tur44", "tur45", "tur46", "tur47", "tur49", "tur50", "tur51", "tur57", "tur58", "turktops", "turkhist"]
AY = {a: i + 1 for i, a in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
YARISMA = [(r"^Millî Küme", "milli_kume", "Millî Küme"),
           (r"^Türkiye Futbol Şampiyonası", "sampiyona", "Türkiye Futbol Şampiyonası"),
           (r"^Prime Minister's Cup", "basbakanlik", "Başbakanlık Kupası"),
           (r"^Federation Cup|^Federasyon Kupası", "federasyon", "Federasyon Kupası"),
           (r"^Istanbul Football League$", "istanbul", "İstanbul Ligi")]
TUR = [(r"^Preliminary Round", "Ön eleme"), (r"^First Round\s*-\s*resumed", "1. tur (devam)"), (r"^First Round", "1. tur"),
       (r"^Second Round", "2. tur"), (r"^Semifinals?\s*-\s*resumed", "Yarı final (devam)"), (r"^Third place", "Üçüncülük maçı"),
       (r"^Round (\d+)", "{}. tur"), (r"^Quarterfinals?\s*-\s*replay", "Çeyrek final (tekrar)"),
       (r"^Quarterfinals?", "Çeyrek final"), (r"^Semifinals?\s*-\s*replay", "Yarı final (tekrar)"), (r"^Semifinals?", "Yarı final"),
       (r"^Final Group|^Group Final", "Final grubu"), (r"^Final\s*-\s*replay", "Final (tekrar)"), (r"^Final\b(?! Table)", "Final"),
       (r"^Replay", "Tekrar"), (r"^Championship play-off", "Şampiyonluk maçı"), (r"^(Red|White) Group", "{} Grup"),
       (r"^Stage (\d)", "{}. aşama")]
SONUC = r"(\d{1,2}-\d{1,2}|abd|o/w|w/o|awd|n/p)"


def oku(ad):
    b = open(os.path.join(HAM, ad + ".html"), "rb").read()
    t = b.decode("utf-16") if b[:2] in (b"\xff\xfe", b"\xfe\xff") else b.decode("utf-8", "replace")
    if "�" in t:
        t = b.decode("latin1")
    return html.unescape(re.sub(r"<[^>]+>", "", t)).replace("\t", "    ")


def indir():
    os.makedirs(HAM, exist_ok=True)
    for p in SAYFALAR:
        yol = os.path.join(HAM, p + ".html")
        if os.path.exists(yol) and os.path.getsize(yol):
            continue
        subprocess.run(["curl", "-sf", "-m", "30", "-A", UA, "-o", yol, f"https://www.rsssf.org/tablest/{p}.html"])
        print(p, flush=True)
        time.sleep(1.5)


def tarih_yap(sezon, metin):
    m = re.match(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? (\d{1,2})", metin or "")
    if not m:
        return None
    ay, gun = AY[m.group(1)], int(m.group(2))
    y1 = int(sezon[:4])
    yil = y1 if len(sezon) == 4 or ay >= 7 else y1 + 1
    return f"{yil}-{ay:02d}-{gun:02d}"


def ayikla_sayfa(ad):
    sat = [s.rstrip() for s in oku(ad).splitlines()]
    baslik = next(s for s in sat if s.startswith("Turkey "))
    m = re.search(r"(\d{4})(?:/(\d{2}))?", baslik)
    sezon = m.group(1) if not m.group(2) else f"{m.group(1)}-{m.group(1)[:2]}{m.group(2)}"
    maclar, tablolar = [], []
    yar = tur = sehir = tarih = None
    tablo = None
    i = 0
    while i < len(sat):
        s = sat[i].strip()
        if not s:
            i += 1; continue
        if re.match(r"^\d{4}\.$|^list of|^About this", s):
            break
        for d, k, _ in YARISMA:
            if re.match(d, s):
                yar, tur, sehir, tarih = k, None, None, None
                break
        else:
            yeni = None
            for d, ad_ in TUR:
                mm = re.match(d, s)
                if mm:
                    yeni = ad_.format(*mm.groups()) if mm.groups() else ad_
                    break
            if yeni:
                tur = {"Red Grup": "Kırmızı Grup", "White Grup": "Beyaz Grup"}.get(yeni, yeni)
                tarih = tarih_yap(sezon, (re.search(r"\[([^\]]+)\]", s) or [None, None])[1])
                i += 1; continue
            if s in ("Ankara", "İstanbul", "İzmir", "Istanbul", "Izmir"):
                sehir = s.replace("Istanbul", "İstanbul").replace("Izmir", "İzmir"); i += 1; continue
            if re.fullmatch(r"\[[^\]]+\]", s):
                tarih = tarih_yap(sezon, s[1:-1]); i += 1; continue
            if s.startswith("Pos ") and yar:
                tablo = {"yarisma": yar, "sezon": sezon, "tur": tur, "satir": []}
                tablolar.append(tablo)
                i += 1
                while i < len(sat) and re.match(r"^\s*\d+\s+\S", sat[i]):
                    r = re.match(r"^\s*(\d+)\s+(.+?)\s+(\d+)\s+([\d-]+)\s+([\d-]+)\s+([\d-]+)\s+(\d+)\s*:\s*(\d+)\s+(\d+)", sat[i])
                    if r:
                        n = lambda x: 0 if x == "-" else int(x)
                        tablo["satir"].append([int(r.group(1)), r.group(2).strip(), *[n(r.group(k)) for k in range(3, 10)]])
                    i += 1
                continue
            # sonuç tablosu: kısaltma başlığı, ardından '---' içeren satırlar
            if yar and re.fullmatch(r"(\s*[A-ZÇĞİÖŞÜ]{1,4}){4,}", s) and i + 1 < len(sat) and "---" in sat[i + 1]:
                satirlar = []
                i += 1
                while i < len(sat) and "---" in sat[i]:
                    r = re.match(r"^(.+?)\s+((?:(?:\d{1,2}-\d{1,2}\*?|---|[a-z/]{1,4}|\*)\s*){4,})$", sat[i].strip())
                    satirlar.append((r.group(1).strip(), r.group(2).split()))
                    i += 1
                adlar = [a for a, _ in satirlar]
                for a, hucre in satirlar:
                    for j, h in enumerate(hucre[:len(adlar)]):
                        if j < len(adlar) and adlar[j] != a and re.fullmatch(r"\d{1,2}-\d{1,2}\*?", h):
                            eg, dg = map(int, h.rstrip("*").split("-"))
                            maclar.append({"yarisma": yar, "sezon": sezon, "tur": tur or "Lig", "tarih": None, "ev": a, "dep": adlar[j],
                                           "eg": eg, "dg": dg, "kaynak": "matris"})
                continue
            r = re.match(r"^(\S.*?)\s{2,}" + SONUC + r"\s+(\S.*?)\s*(?:\[(.*)\])?$", s) or \
                re.match(r"^(\S.*?)\s+-\s+(\S.*?)\s+(\d{1,2}-\d{1,2})\s*(?:\[(.*)\])?$", s)
            if yar and r:
                if " - " in s and re.search(r"\d-\d\s*(\[.*\])?$", s) and r.re.pattern.startswith("^(\\S.*?)\\s+-"):
                    ev, dep, sk, nt = r.group(1), r.group(2), r.group(3), r.group(4)
                else:
                    ev, sk, dep, nt = r.group(1), r.group(2), r.group(3), r.group(4)
                mac = {"yarisma": yar, "sezon": sezon, "tur": tur or "", "tarih": tarih, "ev": ev.strip(), "dep": dep.strip(),
                       "eg": None, "dg": None, "durum": None, "not": nt, "sehir": sehir, "kaynak": "liste"}
                if re.fullmatch(r"\d{1,2}-\d{1,2}", sk):
                    mac["eg"], mac["dg"] = map(int, sk.split("-"))
                else:
                    mac["durum"] = sk
                # Başbakanlık Kupası: stat, hakem ve goller alt satırlarda
                j = i + 1
                goller = []
                while j < len(sat) and sat[j].startswith("     ") and sat[j].strip():
                    g = sat[j].strip()
                    if g.startswith("Stadium:"):
                        mac["stad"] = g.split(":", 1)[1].strip()
                    elif g.startswith("Referee:"):
                        mac["hakem"] = g.split(":", 1)[1].strip()
                    else:
                        gm = re.match(r"(\d+)-(\d+)\s+(.+?)\s+(\d+)'(?:\s*\((pen|og)\))?", g)
                        if gm:
                            goller.append([int(gm.group(1)), int(gm.group(2)), gm.group(3), int(gm.group(4)), gm.group(5)])
                    j += 1
                if goller:
                    mac["goller"] = goller
                maclar.append(mac)
                i = j
                continue
        i += 1
    return maclar, tablolar


def krallar():
    out = []
    yar = None
    for s in oku("turktops").splitlines():
        if s.strip() in ("Millî Küme", "Federasyon Kupası"):
            yar = {"Millî Küme": "milli_kume", "Federasyon Kupası": "federasyon"}[s.strip()]
            continue
        if s.strip() == "Süper Lig":
            break
        m = re.match(r"^(\d{4}(?:-\d{2})?)?\s+(\S.*?)\s{2,}(\S.*?)\s{2,}(\d+)\s*$", s)
        if yar and m:
            yil = m.group(1) or out[-1]["sezon"]
            if "-" in yil:
                yil = f"{yil[:4]}-{yil[:2]}{yil[5:]}"
            out.append({"yarisma": yar, "sezon": yil, "ad": m.group(2), "kulup": m.group(3), "gol": int(m.group(4))})
    return out


def ayikla():
    tum_m, tum_t = [], []
    for p in SAYFALAR:
        if p.startswith("tur") and p[3:].isdigit():
            m, t = ayikla_sayfa(p)
            tum_m += m; tum_t += t
    k = krallar()
    json.dump({"maclar": tum_m, "tablolar": tum_t, "krallar": k}, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    import collections
    say = collections.Counter((x["yarisma"], x["sezon"]) for x in tum_m)
    for (y, s), n in sorted(say.items(), key=lambda x: (x[0][1], x[0][0])):
        print(f"  {s:8} {y:12} {n}")
    print(len(tum_m), "maç,", len(tum_t), "puan tablosu,", len(k), "gol kralı,",
          sum(len(x.get("goller", [])) for x in tum_m), "gol ayrıntısı ->", CIKTI)


if __name__ == "__main__":
    {"indir": indir, "ayikla": ayikla}[sys.argv[1]]()

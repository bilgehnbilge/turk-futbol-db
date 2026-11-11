#!/usr/bin/env python3
"""RSSSF Intertoto sayfalarindan (raw/rsssf/uicYY.html) Turk takimlarinin maclari -> raw/rsssf/intertoto_tr.csv

Iki sayfa duzeni var:
  1995-97: grup turlari "Rd 1 (24-25/6) A 0-1 B; C 0-4 D", eleme turlari "A  2-1 B  [aet, ...]" basliklarin altinda
  1998-2003: eslesme satiri "Ev  Ulk  Dep  Ulk  1.mac 2.mac toplam [aet|Np]", tarih tur basligindan ve x/y/z dipnotlarindan
RSSSF iki macli eslesmede skorlari hep 1. takim acisindan yazar (2.macta 1. takim deplasmandadir).
Grup turlarinda RSSSF yalnizca tarih araligi verir (24-25/6): ilk gun yazilir, 'not' sutununda aralik durur.
Sayfalarin sonundaki "UEFA Cup" bolumu (Intertoto'dan cikanlarin UEFA Kupasi maclari) alinmaz.
"""
import csv
import html
import os
import re

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "rsssf")
CIKTI = os.path.join(HAM, "intertoto_tr.csv")
AY = {a: i + 1 for i, a in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
# RSSSF yazimi -> Mackolik'teki ad
TR = {"Bursaspor": "Bursaspor", "Genclerbirligi": "Gençlerbirliği", "Antalyaspor": "Antalyaspor", "Gaziantepspor": "Gaziantepspor",
      "Kocaelispor": "Kocaelispor", "Samsunspor": "Samsunspor", "Istanbulspor": "İstanbulspor", "Altay Izmir": "Altay",
      "Trabzonspor": "Trabzonspor", "Denizlispor": "Denizlispor", "Çaykur Rizespor": "Ç. Rizespor"}
ALANLAR = ["kaynak", "kaynak_id", "yarisma", "lig", "sezon", "tur", "tarih", "saat", "ev_id", "ev_adi", "dep_id", "dep_adi",
           "ev_gol", "dep_gol", "ev_90", "dep_90", "ev_pen", "dep_pen", "durum", "kazanan", "not"]


def satirlar(yy):
    t = open(os.path.join(HAM, f"uic{yy}.html"), "rb").read().decode("latin-1")
    return [x.rstrip().replace("\t", " ") for x in html.unescape(re.sub(r"<[^>]+>", "", t)).splitlines()]


def tr_mi(ad):
    return ad.strip() in TR


def mac(yil, tur, tarih, ev, dep, eg, dg, durum="MS", kazanan="", not_="", pen=None):
    ev, dep = ev.strip(), dep.strip()
    return dict(kaynak="rsssf", kaynak_id=f"uic{yil}_{tarih}_{ev}_{dep}".replace(" ", "_"), yarisma="ita", lig="InterToto Kupası",
                sezon=f"{yil}-{yil + 1}", tur=tur, tarih=tarih, saat="", ev_id="", ev_adi=TR.get(ev, ev), dep_id="", dep_adi=TR.get(dep, dep),
                ev_gol=str(eg), dep_gol=str(dg), ev_pen=str(pen[0]) if pen else "", dep_pen=str(pen[1]) if pen else "",
                durum=durum, kazanan=TR.get(kazanan, kazanan), not_=not_)


def eski_duzen(yy, yil):
    """1995-97"""
    out, tur, tarihler, ayak = [], "", [], 0
    for l in satirlar(yy):
        g = re.match(r"Group (\d+)", l)
        if g:
            tur = f"Grup {g.group(1)}"
            continue
        r = re.match(r"Rd (\d) \((\d+)(?:-(\d+))?/(\d+)\)\s+(.*)", l)
        if r:
            gun, ay = int(r.group(2)), int(r.group(4))
            for parca in r.group(5).split(";"):
                m = re.match(r"\s*(.+?) (\d+)-(\d+) (.+?)\s*$", parca)
                if m and (tr_mi(m.group(1)) or tr_mi(m.group(4))):
                    out.append(mac(yil, f"{tur}, {r.group(1)}. maç", f"{yil}-{ay:02d}-{gun:02d}", m.group(1), m.group(4),
                                   m.group(2), m.group(3), not_=f"RSSSF tarih araligi {r.group(2)}{'-' + r.group(3) if r.group(3) else ''}/{ay}"))
            continue
        b = re.match(r"(1/8 FINALS|QUARTERFINALS|SEMIFINALS|FINALS)\s*\(([^)]*)\)", l)
        if b:
            tur = {"1/8 FINALS": "Son 16", "QUARTERFINALS": "Çeyrek Final", "SEMIFINALS": "Yarı Final", "FINALS": "Final"}[b.group(1)]
            # "29-30/7" | "02/8" | "26-27/7 and 30/7" | "08-22/8" | "6/8 and 20/8"
            tarihler = []
            for kisim in re.split(r" and |-(?=\d+/)", b.group(2)) if " and " in b.group(2) else [b.group(2)]:
                m = re.match(r"(\d+)(?:-(\d+))?/(\d+)", kisim.strip())
                if m:
                    tarihler.append((int(m.group(1)), int(m.group(3)), kisim.strip()))
            if len(tarihler) == 1 and re.match(r"(\d+)-(\d+)/(\d+)", b.group(2)) and tur in ("Yarı Final", "Final"):
                g1, g2, ay = map(int, re.match(r"(\d+)-(\d+)/(\d+)", b.group(2)).groups())
                tarihler = [(g1, ay, f"{g1}/{ay}"), (g2, ay, f"{g2}/{ay}")]
            ayak = 0
            continue
        if l.startswith("First legs"):
            ayak = 0
            continue
        if l.startswith("Second legs"):
            ayak = 1
            continue
        if re.match(r"(UEFA CUP|Part of)", l) and not tarihler:
            continue
        m = re.match(r"(\S.*?)\s{2,}(\d+)-(\d+) (\S.*?)\s*(\[.*\])?$", l)
        if m and tarihler and (tr_mi(m.group(1)) or tr_mi(m.group(4))):
            gun, ay, ham = tarihler[min(ayak, len(tarihler) - 1)]
            notlar = m.group(5) or ""
            pen = re.search(r"(\d+)-(\d+) on pen", notlar)
            uz = "aet" in notlar
            kaz = ""
            if pen:
                k = re.search(r"\[aet, (\S+)", notlar).group(1)
                kaz = m.group(1).strip() if m.group(1).startswith(k) or k in m.group(1) else m.group(4).strip()
                pen = (pen.group(1), pen.group(2)) if kaz == m.group(1).strip() else (pen.group(2), pen.group(1))
            out.append(mac(yil, tur, f"{yil}-{ay:02d}-{gun:02d}", m.group(1), m.group(4), m.group(2), m.group(3),
                           durum="Pen" if pen else "UZ" if uz else "MS", kazanan=kaz, pen=pen,
                           not_=f"RSSSF tarih {ham}" + (f"; {notlar}" if notlar else "")))
    return out


def tarih_coz(s, yil):
    m = re.match(r"(\w{3}) (\d+)", s.strip())
    return f"{yil}-{AY[m.group(1)]:02d}-{int(m.group(2)):02d}" if m else ""


def yeni_duzen(yy, yil):
    """1998-2003"""
    out, bolum, tur, d1, d2, bekleyen, dip, aralik = [], 0, "", "", "", [], {}, ""
    L = satirlar(yy)
    for i, l in enumerate(L):
        h = re.match(r"Round (\d) \((\w{3}) ([\d,\-]+) and (?:(\w{3}) )?([\d,\-]+)\)", l)
        if h:
            aralik = l[l.index("(") + 1:-1] if re.search(r"[,\-]", h.group(3) + h.group(5)) else ""
            if h.group(1) == "1":
                bolum += 1
            if bolum > 1:      # ikinci "Round 1" = UEFA Kupasi bolumu
                break
            for x in bekleyen:
                out.append(x)
            bekleyen = []
            tur = f"{h.group(1)}. Tur"
            d1 = tarih_coz(f"{h.group(2)} {re.match(r'\d+', h.group(3)).group()}", yil)
            d2 = tarih_coz(f"{h.group(4) or h.group(2)} {re.match(r'\d+', h.group(5)).group()}", yil)
            # bu turun dipnotlari: turun bitisine kadar olan "x 1st leg Jun 19; 2nd leg ..." satirlari
            dip = {}
            for k in L[i + 1:]:
                if re.match(r"Round \d", k):
                    break
                n = re.match(r"([xyz]) (.*)", k)
                if n:
                    son_dip = n.group(1)
                    dip[son_dip] = n.group(2)
                elif k.startswith("  ") and dip:
                    dip[son_dip] += " " + k.strip()
            continue
        m = re.match(r"(\S.*?)\s{2,}(\w{3})\s+(\S.*?)\s{2,}(\w{3})\s+(\d+)-(\d+)([xyz]?)\s+(\d+)-(\d+)([xyz]?)\s*(\*?)(\d+)-(\d+)([xyz*]?)\s*(.*)$", l)
        if not m or not (tr_mi(m.group(1)) or tr_mi(m.group(3))):
            continue
        a, b = m.group(1), m.group(3)
        t1, t2 = d1, d2
        for isaret in {m.group(7), m.group(10), m.group(14)} - {"", "*"}:
            notu = dip.get(isaret, "")
            k1 = re.search(r"1st leg (\w{3} \d+)", notu)
            k2 = re.search(r"2nd leg (\w{3} \d+)", notu)
            if k1 and isaret in (m.group(7), m.group(14)):
                t1 = tarih_coz(k1.group(1), yil)
            if k2 and isaret in (m.group(10), m.group(14)):
                t2 = tarih_coz(k2.group(1), yil)
        son = m.group(15)
        pen = re.match(r"(\d+)-(\d+)p", son)
        uz = "aet" in son or bool(pen)
        agg_a, agg_b = int(m.group(12)), int(m.group(13))
        kaz = a if agg_a > agg_b else b if agg_b > agg_a else ""
        if pen:
            kaz = a if int(pen.group(1)) > int(pen.group(2)) else b
        notlar = "; ".join(f"{x}: {dip[x]}" for x in {m.group(7), m.group(10), m.group(14)} - {"", "*"} if x in dip)
        if aralik:
            notlar = (f"tarih araligi {aralik}; " + notlar).rstrip("; ")
        def hukmen(isaret, ayak):
            n = dip.get(isaret, "")
            ilgili = any(w in n for w in (a.split()[0], b.split()[0]))
            return "awarded" in n and ilgili and (ayak in n or ("1st leg" not in n and "2nd leg" not in n))
        hk1, hk2 = hukmen(m.group(7), "1st leg"), hukmen(m.group(10), "2nd leg")
        bekleyen.append(mac(yil, tur, t1, a, b, m.group(5), m.group(6), durum="Hük." if hk1 else "MS",
                            not_=("RSSSF " + notlar) if notlar else ""))
        # 2. mac: ev sahibi b; RSSSF skoru a acisindan yazar
        bekleyen.append(mac(yil, tur, t2, b, a, m.group(9), m.group(8), durum="Hük." if hk2 else "Pen" if pen else "UZ" if uz else "MS",
                            kazanan=kaz, pen=(pen.group(2), pen.group(1)) if pen else None,
                            not_=("RSSSF " + notlar) if notlar else ""))
        if not kaz and m.group(11) == "*" or m.group(14) == "*":
            bekleyen[-1]["not"] = (bekleyen[-1]["not"] + "; deplasman golu").lstrip("; ")
    out.extend(bekleyen)
    return out


def main():
    ms = []
    for yy in ["95", "96", "97", "98", "99", "00", "01", "02", "03"]:
        yil = 1900 + int(yy) if int(yy) > 50 else 2000 + int(yy)
        bu = eski_duzen(yy, yil) if yil <= 1997 else yeni_duzen(yy, yil)
        print(yil, len(bu), "mac")
        ms += bu
    wiki_ile_duzelt(ms)
    with open(CIKTI, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ALANLAR, restval="")
        w.writeheader()
        for x in ms:
            x["not"] = x.pop("not_")
            w.writerow(x)
    for x in ms:
        print(" ", x["tarih"], x["tur"], "|", x["ev_adi"], x["ev_gol"], "-", x["dep_gol"], x["dep_adi"], x["durum"], x["ev_pen"] + "-" + x["dep_pen"] if x["ev_pen"] else "", x["kazanan"])



# ---- Wikipedia ile kesin tarih (RSSSF yalnizca tarih araligi verdiginde) ----
AYLAR_EN = {a: i + 1 for i, a in enumerate("January February March April May June July August September October November December".split())}


def sade(s):
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    s = s.translate(str.maketrans("İıŞşĞğÜüÖöÇçáéíóúëäøåšžčćđ", "IiSsGgUuOoCcaeiouaaoaszccd")).lower()
    return re.sub(r"[^a-z0-9 ]", " ", s)


def wiki_maclar(yil):
    yol = os.path.join(HAM, f"wiki_{yil}.txt")
    if not os.path.exists(yol):
        return []
    t = open(yol, encoding="utf-8").read()
    out = []
    for blk in re.split(r"\{\{\s*football ?box", t, flags=re.I)[1:]:
        p = {}
        for k in ("date", "team1", "score", "team2"):
            m = re.search(r"\|\s*" + k + r"\s*=\s*(.*)", blk)
            p[k] = m.group(1) if m else ""
        d = re.search(r"Start date\|(\d{4})\|(\d+)\|(\d+)", p["date"]) or re.search(r"(\d+) (\w+) (\d{4})", p["date"])
        if not d:
            continue
        if "Start date" in d.group(0):
            tarih = f"{d.group(1)}-{int(d.group(2)):02d}-{int(d.group(3)):02d}"
        elif d.group(2) in AYLAR_EN:
            tarih = f"{d.group(3)}-{AYLAR_EN[d.group(2)]:02d}-{int(d.group(1)):02d}"
        else:
            continue
        s = re.search(r"(\d+)\s*[–-]\s*(\d+)", re.sub(r"\[\[[^|\]]*\|", "", p["score"]))
        if s:
            out.append((tarih, sade(p["team1"]), int(s.group(1)), int(s.group(2)), sade(p["team2"])))
    return out


def ayni_takim(rsssf_ad, wiki_ad):
    a = [w for w in sade(rsssf_ad).split() if len(w) > 2]
    return any(w in wiki_ad for w in a)


def wiki_ile_duzelt(ms):
    say = 0
    for yil in sorted({int(x["sezon"][:4]) for x in ms}):
        wk = wiki_maclar(yil)
        for x in ms:
            if int(x["sezon"][:4]) != yil:
                continue
            import datetime
            gun = datetime.date.fromisoformat(x["tarih"])
            # ayni skor, 3 gun icinde, iki takimdan biri ad olarak tutuyor (rakip adlari kaynaklar arasinda cok farkli yaziliyor)
            aday = [w for w in wk if (w[2], w[3]) == (int(x["ev_gol"]), int(x["dep_gol"]))
                    and abs((datetime.date.fromisoformat(w[0]) - gun).days) <= 3
                    and (ayni_takim(x["ev_adi"], w[1]) or ayni_takim(x["dep_adi"], w[4]))]
            if len(aday) == 1:
                if aday[0][0] != x["tarih"]:
                    x["not_"] = re.sub(r"(RSSSF )?tarih araligi [^;]*;? ?|RSSSF tarih [^;]*;? ?", "", x["not_"]).strip("; ")
                    x["not_"] = (f"tarih Wikipedia (RSSSF {x['tarih']}); " + x["not_"]).strip("; ")
                    x["tarih"] = aday[0][0]
                else:
                    x["not_"] = re.sub(r"(RSSSF )?tarih araligi [^;]*;? ?", "", x["not_"]).strip("; ")
                x["not_"] = (x["not_"] + "; Wikipedia ile dogrulandi").strip("; ")
                say += 1
            else:
                ayni_gun = [w for w in wk if w[0] == x["tarih"] and (ayni_takim(x["ev_adi"], w[1]) or ayni_takim(x["dep_adi"], w[4]))]
                if x["durum"] == "Hük." and len(ayni_gun) == 1:
                    w = ayni_gun[0]
                    x["not_"] = f"hukmen; Wikipedia'da sahadaki skor {w[2]}-{w[3]}, tarih dogrulandi; " + \
                        re.sub(r"(RSSSF )?tarih araligi [^;]*;? ?", "", x["not_"]).strip("; ")
                else:
                    x["not_"] = (x["not_"] + f"; Wikipedia'da {'bulunamadi' if not aday else 'birden cok aday'}").strip("; ")
    print("Wikipedia ile eslesen:", say, "/", len(ms))


if __name__ == "__main__":
    main()

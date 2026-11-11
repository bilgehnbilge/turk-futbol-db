#!/usr/bin/env python3
"""Turk takimlarinin Avrupa kupasi maclari.

Yeni Mackolik: Sampiyonlar Ligi, UEFA Kupasi/Avrupa Ligi, Konferans Ligi, UEFA Super Kupa, Intertoto 2004-09.
Arsiv sitesi : Fuar Sehirleri Kupasi, Kupa Galipleri Kupasi, Intertoto 1997-2000 (saatlik kota: istekler arasi 40 sn).

Komutlar: yeni | arsiv [--sezon 1969-1970 --kod kgk] | ayikla
Inmis dosyalar atlanir; yarida kalirsa ayni komutla kaldigi yerden devam eder.
"""
import argparse
import collections
import csv
import datetime
import glob
import html
import json
import os
import re
import sys
import time
import urllib.parse

import mackolik as M

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "mackolik_avrupa")
CIKTI = os.path.join(KOK, "avrupa_maclar.csv")
ALANLAR = ["kaynak", "kaynak_id", "yarisma", "lig", "sezon", "tur", "tarih", "saat", "ev_id", "ev_adi", "dep_id", "dep_adi",
           "ev_gol", "dep_gol", "ev_90", "dep_90", "ev_pen", "dep_pen", "durum", "kazanan", "not"]

YENI = {
    "sl": dict(id="4oogyu6o156iphvdvphwpck10", slug="avrupa-şampiyonlar-ligi"),
    "el": dict(id="4c1nfi2j1m731hcay25fcgndq", slug="avrupa-avrupa-ligi"),
    "kl": dict(id="c7b8o53flg36wbuevfzy3lb10", slug="avrupa-konferans-ligi"),
    "sk": dict(id="a0f4gtru0oyxmpvty4thc5qkc", slug="avrupa-uefa-süper-kupa"),
    "it": dict(id="41ztcvq25kqznajeqco9n31ed", slug="avrupa-intertoto-kupası"),
}
ARSIV_KUPA = {"fuar": 374, "kgk": 375, "ita": 95}
RSSSF = os.path.join(KOK, "raw", "rsssf", "intertoto_tr.csv")   # Intertoto 1995-2003: rsssf_intertoto.py
ITA_SEZON = {"1997/1998", "1998/1999", "1999/2000"}  # 2004-09 yeni siteden geliyor

TR_AD = re.compile(r"Galatasaray|Fenerbah|Be[sş]ikta|Trabzon|G[oö]ztepe|Ankarag|Bursaspor|\bAltay\b|Eski[sş]ehir|Kayseri|Ba[sş]ak[sş]ehir"
                   r"|Sivasspor|Konyaspor|Antalyaspor|Alanyaspor|Gaziantep|Kocaelispor|Gen[cç]lerbir|[İI]stanbulspor|Adanaspor|Adana Demir"
                   r"|Denizlispor|Samsunspor|Sakaryaspor|Ankara Demir|Boluspor|Mersin|Orduspor|Bucaspor|Hacettepe|Karab[uü]k|Malatyaspor"
                   r"|Rizespor|Vanspor|Antep|Sar[iı]yer|Zeytinburnu|Erzurumspor|Kas[iı]mpa[sş]a|Aydinspor|Ayd[iı]nspor|Diyarbak[iı]r")


def lig_adi(kod, yil):
    if kod == "sl":
        return "Şampiyon Kulüpler Kupası" if yil < 1992 else "Şampiyonlar Ligi"
    if kod == "el":
        return "UEFA Kupası" if yil < 2009 else "Avrupa Ligi"
    return {"kl": "Konferans Ligi", "sk": "UEFA Süper Kupa", "it": "InterToto Kupası", "ita": "InterToto Kupası",
            "fuar": "Fuar Şehirleri Kupası", "kgk": "Kupa Galipleri Kupası"}[kod]


def yeni_url(y, etiket=None):
    orta = f"{etiket}/" if etiket else ""
    return f"https://www.mackolik.com/kupa/{urllib.parse.quote(y['slug'])}/{orta}fikstur/{y['id']}"


def yeni_indir():
    os.makedirs(HAM, exist_ok=True)
    for kod, y in YENI.items():
        menu = os.path.join(HAM, f"{kod}_menu.html.gz")
        if not os.path.exists(menu):
            ok, durum = M.curl(yeni_url(y), menu)
            if not ok:
                sys.exit(f"{kod}: menu alinamadi (HTTP {durum})")
            time.sleep(M.BEKLE)
        sezonlar = [e for e, _, _ in reversed(M.sezon_listesi(M.oku(menu)))]
        print(kod, len(sezonlar), "sezon", flush=True)
        for etiket in sezonlar:
            yol = os.path.join(HAM, f"{kod}_{etiket}.html.gz")
            if os.path.exists(yol):
                continue
            ok, durum = M.curl(yeni_url(y, etiket), yol)
            time.sleep(M.BEKLE)
            print(f"  {kod} {etiket}: {'tamam' if ok else 'HATA ' + str(durum)}", flush=True)


def yeni_maclar(yol):
    t = html.unescape(M.oku(yol))
    dec, ham = json.JSONDecoder(), {}
    for m in re.finditer(r'"raw":\{"match":\{', t):
        try:
            o, _ = dec.raw_decode(t, m.end() - 1)
            ham[o["id"]] = o
        except ValueError:
            pass
    ms = []
    for o in ham.values():
        a, b = o["team_A"], o["team_B"]
        tarih = saat = ""
        if o.get("date_time_utc"):
            dt = datetime.datetime.strptime(o["date_time_utc"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc).astimezone(M.TR)
            tarih, saat = dt.date().isoformat(), dt.strftime("%H:%M")
        oynandi = o.get("status") == "Played" and o.get("fts_A") is not None
        uz = o.get("ets_A") is not None
        pen = o.get("ps_A") is not None
        kazanan = {a["id"]: a["name"], b["id"]: b["name"]}.get(o.get("round_winner") or o.get("final_winner"), "")
        ms.append(dict(kaynak="mackolik", kaynak_id=o["uuid"], tur=o["round"]["name"], tarih=tarih, saat=saat,
                       ev_id=a["uuid"], ev_adi=M.temiz(a["name"]), dep_id=b["uuid"], dep_adi=M.temiz(b["name"]),
                       ev_gol=str(o["ets_A"] if uz else o["fts_A"]) if oynandi else "",
                       dep_gol=str(o["ets_B"] if uz else o["fts_B"]) if oynandi else "",
                       ev_90=str(o["fts_A"]) if oynandi and uz else "", dep_90=str(o["fts_B"]) if oynandi and uz else "",
                       ev_pen=str(o["ps_A"]) if pen else "", dep_pen=str(o["ps_B"]) if pen else "",
                       durum=("Pen" if pen else "UZ" if uz else "MS") if oynandi else (o.get("status") or ""), kazanan=M.temiz(kazanan)))
    return ms


def turk_kimlikleri():
    """Yerel veriden: yeni site kimlikleri (uuid), arsiv kimlikleri ve kulup adlari."""
    uuid, adlar, arsiv = set(), set(), set()
    with open(os.path.join(KOK, "mackolik_maclar.csv"), encoding="utf-8") as f:
        for x in csv.DictReader(f):
            for s in ("ev", "dep"):
                adlar.add(x[s + "_adi"])
                (uuid if x["kaynak"] == "mackolik" else arsiv).add(x[s + "_id"])
    for yol in glob.glob(os.path.join(M.ARSIV_HAM, "kupa_*", "tur_*.html")):
        arsiv.update(re.findall(r"/Takim/(\d+)/", open(yol, encoding="utf-8").read()))
    return uuid, arsiv, adlar


def arsiv_turk_mu(m, arsiv, adlar):
    return any(m[s + "_id"] in arsiv or m[s + "_adi"] in adlar or TR_AD.search(m[s + "_adi"]) for s in ("ev", "dep"))


def arsiv_indir(sadece_kod=None, sadece_sezon=None):
    _, arsiv, adlar = turk_kimlikleri()
    for kod, kid in ARSIV_KUPA.items():
        if sadece_kod and kod != sadece_kod:
            continue
        menu = os.path.join(HAM, f"arsiv_{kod}_menu.html")
        if not os.path.exists(menu):
            os.makedirs(HAM, exist_ok=True)
            t = M.curl_metin(f"{M.ARSIV}/Kupa/{kid}/x")
            if t is None:
                sys.exit(f"{kod}: menu alinamadi")
            open(menu, "w", encoding="utf-8").write(t)
            time.sleep(M.ARSIV_BEKLE)
        sezonlar = list(reversed(re.findall(r"<option[^>]*>\s*(\d{4}/\d{4})\s*</option>", open(menu, encoding="utf-8").read())))
        if kod == "ita":
            sezonlar = [s for s in sezonlar if s in ITA_SEZON]
        for sezon in sezonlar:
            etiket = sezon.replace("/", "-")
            if sadece_sezon and etiket != sadece_sezon:
                continue
            kl = os.path.join(HAM, f"arsiv_{kod}_{etiket}")
            os.makedirs(kl, exist_ok=True)
            yol = os.path.join(kl, "sezon.html")
            if not os.path.exists(yol):
                t = M.curl_metin(f"{M.ARSIV}/AjaxHandlers/CupHandler.aspx?command=seasonMatches&id={kid}&season={sezon}")
                if t is None:
                    print(f"  {kod} {etiket}: sezon alinamadi", flush=True)
                    continue
                open(yol, "w", encoding="utf-8").write(t)
                time.sleep(M.ARSIV_BEKLE)
            turlar = sorted(M.kupa_turlari(open(yol, encoding="utf-8").read()), key=lambda x: int(x[0]))
            goruldu, bos = False, 0
            for tid, ad in turlar:
                tyol = os.path.join(kl, f"tur_{tid}.html")
                if os.path.exists(tyol):
                    t = open(tyol, encoding="utf-8").read()
                else:
                    t = M.curl_metin(f"{M.ARSIV}/AjaxHandlers/CupHandler.aspx?command=legMatches&id={tid}")
                    if t is None:
                        print(f"  {kod} {etiket} {ad}: alinamadi", flush=True)
                        break
                    open(tyol, "w", encoding="utf-8").write(t)
                    time.sleep(M.ARSIV_BEKLE)
                var = any(arsiv_turk_mu(m, arsiv, adlar) for m in M.kupa_satirlari(t))
                if var:
                    goruldu, bos = True, 0
                else:
                    bos += 1
                    if goruldu or bos >= 4:   # Turk takimi elendi ya da bu sezon yok
                        break
            print(f"  {kod} {etiket}: {'Turk takimi var' if goruldu else 'Turk takimi yok'}", flush=True)


def ayikla():
    uuid, arsiv, adlar = turk_kimlikleri()
    satirlar, takimlar, durumlar, gorulen = [], collections.Counter(), collections.Counter(), set()
    for kod in YENI:
        for yol in sorted(glob.glob(os.path.join(HAM, f"{kod}_[0-9]*.html.gz"))):
            etiket = os.path.basename(yol)[len(kod) + 1:-8]
            for m in yeni_maclar(yol):
                if m["ev_id"] not in uuid and m["dep_id"] not in uuid:
                    continue
                satirlar.append({**m, "yarisma": kod, "lig": lig_adi(kod, int(etiket[:4])), "sezon": etiket})
    for kod in ARSIV_KUPA:
        for kl in sorted(glob.glob(os.path.join(HAM, f"arsiv_{kod}_[0-9]*"))):
            etiket = os.path.basename(kl)[len(f"arsiv_{kod}_"):]
            yolu = os.path.join(kl, "sezon.html")
            adi = dict(M.kupa_turlari(open(yolu, encoding="utf-8").read())) if os.path.exists(yolu) else {}
            # sezon sayfasi da mac satiri icerir (final; Intertoto'da tur listesi yok, maclar dogrudan burada)
            for yol in sorted(glob.glob(os.path.join(kl, "tur_*.html"))) + [yolu]:
                if not os.path.exists(yol):
                    continue
                t_ = open(yol, encoding="utf-8").read()
                tid = (re.search(r"tur_(\d+)", yol) or [None, None])[1]
                parcalar = [(adi.get(tid, ""), t_)]
                if tid is None:   # sezon sayfasi: her tur kendi "competition" basligi altinda
                    parcalar = [(M.temiz((re.match(r'[^>]*>\s*(?:<a[^>]*>)?(.*?)<', p_, re.S) or [None, ""])[1]), p_)
                                for p_ in t_.split('<div class="competition"')[1:]]
                for tur_adi, parca in parcalar:
                  for m in M.kupa_satirlari(parca):
                    if arsiv_turk_mu(m, arsiv, adlar) and m["kaynak_id"] not in gorulen:
                        gorulen.add(m["kaynak_id"])
                        satirlar.append({**m, "kaynak": "mackolik_arsiv", "tur": re.sub(r"^(Fuar Şehirleri|Kupa Galipleri) Kupası\s*", "", tur_adi), "yarisma": kod,
                                         "lig": lig_adi(kod, int(etiket[:4])), "sezon": etiket})
    # Intertoto 1995-2003 RSSSF'ten (tam); arsivin 1997-2000 sayfalari yalnizca 3. turu gosteriyor
    if os.path.exists(RSSSF):
        satirlar = [x for x in satirlar if not (x["kaynak"] == "mackolik_arsiv" and x["yarisma"] == "ita")]
        with open(RSSSF, encoding="utf-8") as f:
            satirlar += list(csv.DictReader(f))
    satirlar.sort(key=lambda x: (x["tarih"], x["kaynak_id"]))
    with open(CIKTI, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ALANLAR, extrasaction="ignore", restval="")
        w.writeheader()
        w.writerows(satirlar)
    for x in satirlar:
        durumlar[x["durum"]] += 1
        for s in ("ev", "dep"):
            kim = x[s + "_id"]
            if kim in uuid or kim in arsiv or x[s + "_adi"] in adlar or TR_AD.search(x[s + "_adi"]):
                takimlar[x[s + "_adi"]] += 1
    say = collections.Counter(x["lig"] for x in satirlar)
    print(len(satirlar), "mac ->", CIKTI)
    print("kupalar:", dict(say))
    print("durum:", dict(durumlar))
    print("Turk takimlari:", takimlar.most_common())


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("komut", choices=["yeni", "arsiv", "ayikla"])
    p.add_argument("--kod")
    p.add_argument("--sezon")
    p.add_argument("--bekle", type=float, help="yeni site: istekler arasi bekleme (sn)")
    a = p.parse_args()
    if a.bekle:
        M.BEKLE = a.bekle
    if a.komut == "yeni":
        yeni_indir()
    elif a.komut == "arsiv":
        arsiv_indir(a.kod, a.sezon)
    else:
        ayikla()

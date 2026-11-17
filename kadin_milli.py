#!/usr/bin/env python3
"""Kadın A Milli Takımı: TFF'nin maç listesi (pageID=441, sayfalı) ve maç sayfaları (pageID=440) -> kadin_milli_maclar.json.
Ayrıştırma ve site verisi milli.py'nin (erkek A milli) koduyla; site verisi docs/data/kadin/milli.json, milli_detay.json.

  python3 kadin_milli.py indir    # raw/tff_kadin_milli/liste_<n>.html + <macID>.html.gz (kaldığı yerden)
  python3 kadin_milli.py ayikla   # -> kadin_milli_maclar.json (depoda)
(kadin_site.py site verisini üretirken milli.site()'i bu dosyayla çağırır.)

Liste sayfaları ASP.NET form gönderimiyle (__doPostBack) sayfalanıyor: her sayfa bir öncekinin gizli alanlarıyla istenir.
"""
import gzip, html, http.cookiejar, os, re, sys, time, urllib.parse, urllib.request

import milli, topla

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "raw", "tff_kadin_milli")
CIKTI = os.path.join(KOK, "kadin_milli_maclar.json")
URL = "https://www.tff.org/Default.aspx?pageID=441"


def kur():
    """milli.py'yi kadın verisine yönlendir."""
    milli.HAM, milli.CIKTI = HAM, CIKTI
    milli.wiki_birlestir = lambda out: None   # Vikipedi tamamlaması yalnız erkek A milli için


def liste_indir():
    os.makedirs(HAM, exist_ok=True)
    acici = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    acici.addheaders = [("User-Agent", topla.UA)]
    t = acici.open(URL, timeout=90).read().decode("cp1254", "replace")
    n = 1
    while True:
        open(os.path.join(HAM, f"liste_{n}.html"), "w", encoding="cp1254", errors="replace").write(t)
        m = re.search(r"\b(\d+) / (\d+), Toplam (\d+) kayıt", t)
        print(f"  liste sayfası {n}" + (f" / {m.group(2)} ({m.group(3)} maç)" if m else ""), flush=True)
        hedef = re.search(r"__doPostBack\(&#39;([^&]*)&#39;,&#39;&#39;\)\">%d</a>" % (n + 1), t)
        if not hedef:
            break
        alan = {k: html.unescape(v) for k, v in re.findall(r'name="(__[A-Z]+)"[^>]*value="([^"]*)"', t)}
        alan.update(__EVENTTARGET=hedef.group(1), __EVENTARGUMENT="")
        time.sleep(2)
        t = acici.open(urllib.request.Request(URL, data=urllib.parse.urlencode(alan, encoding="cp1254").encode())).read().decode("cp1254", "replace")
        n += 1
    # milli.liste_oku tek dosya okur: sayfaları birleştir
    with open(os.path.join(HAM, "liste.html"), "w", encoding="cp1254", errors="replace") as f:
        for i in range(1, n + 1):
            f.write(open(os.path.join(HAM, f"liste_{i}.html"), encoding="cp1254", errors="replace").read())


def indir():
    kur()
    liste_indir()
    ms = milli.liste_oku()
    bugun = time.strftime("%Y-%m-%d")
    hedef = [m for m in ms if m["tarih"] and m["tarih"] < bugun and re.match(r"\d+\s*-\s*\d+", m["skor"])]
    eksik = [m for m in hedef if not os.path.exists(os.path.join(HAM, f"{m['tff']}.html.gz"))]
    print(f"{len(ms)} maç listede, {len(hedef)} oynanmış, {len(eksik)} sayfa indirilecek", flush=True)
    for i, m in enumerate(eksik, 1):
        kod, govde = milli.al(milli.MAC_URL.format(m["tff"]))
        if kod == "200" and len(govde) > 15000:
            with gzip.open(os.path.join(HAM, f"{m['tff']}.html.gz"), "wb") as g:
                g.write(govde)
        else:
            print("  hata", kod, m["tff"], flush=True)
            time.sleep(20)
        time.sleep(2)
    print("Bitti.", flush=True)


def ayikla():
    kur()
    milli.ayikla()


def site(yaz, cikti):
    kur()
    milli.site(yaz, cikti)


if __name__ == "__main__":
    {"indir": indir, "ayikla": ayikla}[sys.argv[1]]()

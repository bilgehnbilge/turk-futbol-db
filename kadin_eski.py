"""Kadın ligi, TFF kadın arşivinden (2007-08'den) önceki sezon: 2001-02 Türkiye Bayanlar Futbol Ligi.

TFF'nin kadın ligleri arşivinde 2007-08 öncesi yok; 2001-02'nin maç sayfaları ise TFF'de duruyor (oyuncu.py'nin maç
taramasına "Bayanlar Ligi (Profesyonel Takım)" organizasyonuyla karışmışlardı). Bu sezon maçlarıyla, kadrolarıyla
kadin_eski.json'da (depoda) tutulur ve her site üretiminde raw/kadin.db + raw/kadin_detay.db'ye eklenir; böylece
kadin.py kur (TFF arşivinden baştan kurulum) bu sezonu silmez ve bot (GitHub Actions) da aynı veriyi kullanır.

  python3 kadin_eski.py kur     # raw/oyuncu.db + elle eklenenler -> kadin_eski.json (yerelde, bir kez)
  python3 kadin_eski.py ekle    # kadin_eski.json -> raw/kadin.db, raw/kadin_detay.db (kadin_site.aktar çağırır)

1999-2000 ve 2002-03 sayfaları da TFF'de var ama skorları girilmemiş (0-0 / boş); onlar eklenmez. 1993-2007
sezonlarının şampiyonları kadin_sampiyon.json "_eski" altında (Vikipedi, RSSSF).
"""
import gzip, json, os, sqlite3, sys

KOK = os.path.dirname(os.path.abspath(__file__))
DOSYA = os.path.join(KOK, "kadin_eski.json")
SEZON = "2001-2002"
LIG = "Türkiye Bayanlar Futbol Ligi"
TABLOLAR = ("kadro", "gol", "kart", "degisiklik", "teknik", "hakem", "mac_bilgi")


def _hafta_grup(kod):
    """TFF maç kodu: A grubu (7 takım) 6001-6056, haftada 4 kod (biri bay); B grubu (6 takım) 6057-6086, haftada 3."""
    kod = int(kod)
    if 6001 <= kod <= 6056:
        return "A", (kod - 6001) // 4 + 1
    if 6057 <= kod <= 6086:
        return "B", (kod - 6057) // 3 + 1
    return None, None


def kur(ek_sayfalar=None):
    """ek_sayfalar: oyuncu.db'de olmayan, sonradan taranan TFF maç sayfaları (klasör; <macId>.html.gz)."""
    import oyuncu
    o = sqlite3.connect(os.path.join(KOK, "raw", "oyuncu.db"))
    satir = o.execute("SELECT mac, kod, tarih, ev_tff, ev_adi, dep_tff, dep_adi, ev_gol, dep_gol FROM mac_bilgi "
                      "WHERE organizasyon LIKE 'Bayanlar%' AND tarih BETWEEN '2001-08-01' AND '2002-07-31'").fetchall()
    detay = {t: [] for t in TABLOLAR}
    ids = [r[0] for r in satir]
    for t in TABLOLAR:
        for m in ids:
            detay[t] += [list(r) for r in o.execute(f"SELECT * FROM {t} WHERE mac=?", (m,))]
    # sonradan taranan sayfalar (ör. A grubunun son haftası): oyuncu.py'nin ayrıştırıcısıyla
    if ek_sayfalar:
        sutun = [r[1] for r in o.execute("PRAGMA table_info(mac_bilgi)")]
        for f in sorted(os.listdir(ek_sayfalar)):
            m = f.split(".")[0]
            if m in ids:
                continue
            s = oyuncu.sayfa_oku(gzip.open(os.path.join(ek_sayfalar, f)).read().decode("cp1254", "replace"))
            b = dict(zip(sutun[2:12], s["bilgi"]))
            if "Bayan" not in (b.get("organizasyon") or "") or not (b.get("tarih") or "").startswith(("2001", "2002")) or b.get("ev_gol") is None:
                continue
            satir.append((m, b["kod"], b["tarih"], b["ev_tff"], b["ev_adi"], b["dep_tff"], b["dep_adi"], b["ev_gol"], b["dep_gol"]))
            ids.append(m)
            for t, n in (("kadro", 5), ("gol", 7), ("kart", 7), ("degisiklik", 8), ("teknik", 3), ("hakem", 3)):
                detay[t] += [[m, *r] for r in s[t]]
            detay["mac_bilgi"].append([m, s["stad"], *s["bilgi"]] + [None] * (len(sutun) - 12))
    maclar = []
    for m, kod, tarih, et, ea, dt, da, eg, dg in sorted(satir, key=lambda r: (r[2], int(r[1]))):
        g, h = _hafta_grup(kod)
        maclar.append({"tff": m, "grup": g, "asama": "lig", "hafta": h, "tarih": tarih, "ev_tff": str(et), "ev_adi": ea,
                       "dep_tff": str(dt), "dep_adi": da, "ev_gol": eg, "dep_gol": dg})
    elle = json.load(open(DOSYA, encoding="utf-8")).get("elle", []) if os.path.exists(DOSYA) else []
    json.dump({"_aciklama": "2001-02 Türkiye Bayanlar Futbol Ligi (kadin_eski.py). maclar/detay: TFF maç sayfaları; "
                            "elle: TFF'de sayfası olmayan maçlar (kaynaklı).",
               "sezon": SEZON, "lig": LIG, "maclar": maclar, "elle": elle, "detay": detay},
              open(DOSYA, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"kadin_eski.json: {len(maclar)} maç (TFF), {len(elle)} elle, kadro satırı {len(detay['kadro'])}")


def ekle(db=None, detay_db=None):
    """kadin_eski.json -> kadin.db (mac, kulup) ve kadin_detay.db; önceki eklemeyi silip yeniden yazar."""
    if not os.path.exists(DOSYA):
        return
    import kadin
    db, detay_db = db or kadin.DB, detay_db or kadin.DETAY_DB
    if not os.path.exists(db):
        return
    d = json.load(open(DOSYA, encoding="utf-8"))
    c = sqlite3.connect(db)
    c.execute("DELETE FROM mac WHERE sezon=? AND kaynak IN ('tff_eski', 'elle')", (d["sezon"],))

    def kulup(tff, ad):
        r = c.execute("SELECT id FROM kulup WHERE tff_id=?", (tff,)).fetchone()
        if r:
            kid = r[0]
        else:
            kid = c.execute("INSERT INTO kulup(tff_id, ad) VALUES(?, ?)", (tff, ad)).lastrowid
        if not c.execute("SELECT 1 FROM kulup_adi WHERE kulup_id=? AND ad=?", (kid, ad)).fetchone():
            c.execute("INSERT INTO kulup_adi VALUES(?, ?, ?, ?, 0)", (kid, ad, d["sezon"], d["sezon"]))
        return kid

    n = 0
    for kaynak, l in (("tff_eski", d["maclar"]), ("elle", d.get("elle", []))):
        for m in l:
            c.execute("INSERT INTO mac(kaynak, kaynak_id, kademe, lig, sezon, grup, asama, hafta, tarih, ev_id, dep_id, ev_adi, dep_adi, "
                      "ev_gol, dep_gol, ev_pen, dep_pen, ham_skor, durum) VALUES(?,?,1,?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,?,?)",
                      (kaynak, str(m["tff"]), d["lig"], d["sezon"], m.get("grup"), m.get("asama") or "lig", m.get("hafta"), m["tarih"],
                       kulup(m["ev_tff"], m["ev_adi"]), kulup(m["dep_tff"], m["dep_adi"]), m["ev_adi"], m["dep_adi"],
                       m["ev_gol"], m["dep_gol"], f"{m['ev_gol']}-{m['dep_gol']}", None))
            n += 1
    # kulup_adi maç sayıları
    for kid, ad in c.execute("SELECT kulup_id, ad FROM kulup_adi WHERE ilk_sezon=? AND son_sezon=?", (d["sezon"], d["sezon"])).fetchall():
        say = c.execute("SELECT COUNT(*) FROM mac WHERE sezon=? AND ((ev_id=? AND ev_adi=?) OR (dep_id=? AND dep_adi=?))",
                        (d["sezon"], kid, ad, kid, ad)).fetchone()[0]
        c.execute("UPDATE kulup_adi SET mac_sayisi=? WHERE kulup_id=? AND ad=?", (say, kid, ad))
    c.commit()
    if os.path.exists(detay_db):
        o = sqlite3.connect(detay_db)
        ids = [str(m["tff"]) for m in d["maclar"]]
        for t in TABLOLAR:
            o.executemany(f"DELETE FROM {t} WHERE mac=?", [(m,) for m in ids])
            for r in d["detay"][t]:
                o.execute(f"INSERT INTO {t} VALUES({','.join('?' * len(r))})", r)
        o.commit()
    print(f"kadın {d['sezon']}: {n} maç eklendi (kadin_eski.json)")


if __name__ == "__main__":
    {"kur": lambda: kur(sys.argv[2] if len(sys.argv) > 2 else None), "ekle": ekle}[sys.argv[1]]()

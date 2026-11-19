/* Kadın ligleri: bölüm ana sayfası (sezonlar, kulüpler, oyuncular) ve sezon sayfaları. Erkek verisinden tamamen ayrı.
   Kulüp, maç ve oyuncu sayfaları (#/kadin/kulup|mac|oyuncu/...) app.js'teki erkek sayfalarının kodunu kadın verisiyle çizer.
   Veri: data/kadin/ (kadin_site.py; TFF arşivi pageID=848 ve maç sayfaları pageID=29).
   app.js'ten sonra yüklenir; $, esc, al, tarihYaz, sayiYaz, yuzde, sonuc, skorYaz, macCiz, temaUygula, takimTema, yollar app.js'ten gelir. */
(() => {
let KZ = null, KM = null, KOY = null;
const KK = new Map();
// bölüm verisi: app.js bolumSec("kadin") bunu çağırır; kulüp, maç ve oyuncu sayfaları erkek bölümünün kodunu kullanır
BOLUM_YUKLE.kadin = async () => {
  KZ = await al("data/kadin/ozet.json", { cache: "no-cache" });
  for (const k of KZ.kulupler) KK.set(k.id, adSadele(k));
  return { OZET: KZ, KULUP: KK, KADEME_AD: { 1: "Kadın Süper Ligi", 2: "Kadınlar 1. Ligi", 3: "Kadınlar 2. Ligi", 4: "Kadınlar 3. Ligi" } };
};
const kOzet = async () => KZ;
const s_ = () => KZ.surum || "";
const kMaclar = async () => KM ||= (await al(`data/kadin/maclar.json?s=${s_()}`)).maclar.map(r => ({
  tff: r[0], tarih: r[1], sezon: r[2], kademe: r[3], lig: r[4], grup: r[5], asama: r[6], hafta: r[7], ev: r[8], dep: r[9],
  eg: r[10], dg: r[11], ep: r[12], dp: r[13], ayr: r[14], durum: r[15] }));
const kOyuncular = async () => KOY ||= (await al(`data/kadin/tff/oyuncular.json?s=${s_()}`)).oyuncu.map(r => ({ kisi: r[0], ad: r[1], mac: r[2], gol: r[3], ilk: r[4], son: r[5], kulup: r[6] }));
const kAd = id => KK.get(id)?.ad ?? "?";
const kLogo = (id, cls = "logo-k") => { const l = KK.get(id)?.logo; return l ? `<img class="${cls}" src="logo/${l}.png" alt="" loading="lazy" onerror="this.remove()">` : ""; };
const kBag = (id, ayni) => id == null ? "?" : id === ayni ? `<span>${kLogo(id)}${esc(kAd(id))}</span>` : `<a class="bag" href="#/kadin/kulup/${id}">${kLogo(id)}${esc(kAd(id))}</a>`;
const kSkor = m => { const h = m.eg == null ? `<span class="soluk">${m.durum === "H" ? "hükmen" : "oynanmadı"}</span>` : skorYaz(m.eg, m.dg, m.ep, m.dp, m.durum);
  return detayVar(m.tff) ? `<a class="skor bagli" href="#/kadin/mac/${m.tff}" title="Maç ayrıntısı">${h}</a>` : h; };
const oyBag = (kisi, ad) => `<a class="oyuncu-bag" href="#/kadin/oyuncu/k${kisi}">${esc(ad)}</a>`;
const PUAN = 3;   // 2007-08'den beri bütün kadın liglerinde galibiyet 3 puan
const kademeAd = (sezon, k) => (KZ.ligler[sezon] || []).find(x => x[0] === k)?.[1] || `${k}. kademe`;
const NOT = `Veri: TFF (kadın ligleri arşivi ve maç sayfaları). 2006-07 sezonunun TFF'de yalnızca resmi var; 2007-08'in maç sayfalarında kadro ve gol yok.`;

function puanTablosu(ms) {
  const t = new Map(), sat = id => t.get(id) || t.set(id, { id, O: 0, G: 0, B: 0, M: 0, AG: 0, YG: 0 }).get(id);
  for (const m of ms) {
    if (m.eg == null) continue;
    const e = sat(m.ev), d = sat(m.dep);
    e.O++; d.O++; e.AG += m.eg; e.YG += m.dg; d.AG += m.dg; d.YG += m.eg;
    if (m.eg > m.dg) { e.G++; d.M++; } else if (m.eg < m.dg) { d.G++; e.M++; } else { e.B++; d.B++; }
  }
  return [...t.values()].map(x => ({ ...x, P: x.G * PUAN + x.B, Av: x.AG - x.YG })).sort((a, b) => b.P - a.P || b.Av - a.Av || b.AG - a.AG);
}
function macListe(ms, ayni) {
  if (!ms.length) return `<div class="bos">Maç yok.</div>`;
  return `<div style="overflow-x:auto"><table class="tablo mac-liste"><tbody>${ms.map(m => `<tr><td class="soluk">${tarihYaz(m.tarih)}</td>
    <td class="ad" style="text-align:right">${kBag(m.ev, ayni)}</td><td class="o skor">${kSkor(m)}</td><td class="ad">${kBag(m.dep, ayni)}</td></tr>`).join("")}</tbody></table></div>`;
}
const basOn = (baslik, alt) => `<div class="sayfa-bas"><div><h1>${baslik}</h1>${alt ? `<p class="soluk">${alt}</p>` : ""}</div></div>`;
const sekmeler = (l, aktif) => `<nav class="sekmeler">${l.map(([k, h, a]) => `<a href="${h}" class="${k === aktif ? "aktif" : ""}">${a}</a>`).join("")}</nav>`;

// ---------------------------------------------------------------- ana sayfa: sezonlar, kulüpler, oyuncular
const anaDurum = { kulupAra: "", oyuncuAra: "" };
// bölümün başlığı ve sekmeleri; Rekorlar ve Sayılar sekmeleri app.js / grafik.js'teki erkek sayfalarının kodunu kullanır (BOLUM_UST)
function kadinUst(sekme) {
  const z = KZ;
  const SEK = [["sezonlar", "#/kadin", "Sezonlar"], ["krallar", "#/kadin/krallar", "Gol kralları"], ["kulupler", "#/kadin/kulupler", "Kulüpler"],
    ["oyuncular", "#/kadin/oyuncular", "Oyuncular"], ["rekorlar", "#/kadin/rekorlar", "Rekorlar"], ["sayilar", "#/kadin/sayilar", "Sayılar"]];
  return `${basOn("Kadın Futbolu", `TFF kadın ligleri, ${z.sezonlar[0]}'den bugüne. Erkek liglerinden ayrı tutulur; erkek takımıyla aynı kulüp olanlar "(Kadın)" ekiyle yazılır.`)}
    <div class="kart bolum"><div class="ozet-sat">
      <div><b>${sayiYaz(z.oynanan)}</b><span>Maç</span></div><div><b>${sayiYaz(z.kulupler.filter(k => k.yerli !== false).length)}</b><span>Kulüp</span></div>
      <div><b>${sayiYaz(z.oyuncu)}</b><span>Oyuncu</span></div><div><b>${z.sezonlar.length}</b><span>Sezon</span></div>
      <div><b>${sayiYaz(z.ayrintili)}</b><span>Kadrolu maç</span></div></div></div>
    ${sekmeler(SEK, sekme)}`;
}
BOLUM_UST.kadin = kadinUst;
async function kadinSayfa(sekme = "sezonlar") {
  document.title = "Kadın Futbolu · Türk Futbol Arşivi";
  icerik.innerHTML = `<div class="yukleniyor">Kadın ligleri yükleniyor…</div>`;
  const z = await kOzet();
  icerik.innerHTML = `${kadinUst(sekme)}<div id="kadinIc"></div><p class="soluk not bolum">${NOT}</p>`;
  const ic = $("#kadinIc");
  if (sekme === "sezonlar") {
    // şampiyonlar: kadin_sampiyon.json (RSSSF / Vikipedi); sezon kartları (erkek Sezonlar sayfasıyla aynı görünüm)
    const sampiyonSay = new Map();
    for (const s of z.sezonlar) { const k = z.sampiyonlar?.[s]; if (k != null) sampiyonSay.set(k, (sampiyonSay.get(k) || 0) + 1); }
    const ms = await kMaclar(), sz = new Map();
    for (const m of ms) { const t = sz.get(m.sezon) || { mac: 0, gol: 0, oyn: 0, takim: new Set() }; t.mac++; if (m.kademe === 1 && !m.asama) { t.takim.add(m.ev); t.takim.add(m.dep); if (m.eg != null) { t.oyn++; t.gol += m.eg + m.dg; } } sz.set(m.sezon, t); }
    const kart = s => { const k = z.sampiyonlar?.[s], var_ = s in (z.sampiyonlar || {}), t = sz.get(s) || { mac: 0, takim: new Set() };
      return `<a class="sezon-kart${k != null ? " renkli" : ""}" href="#/kadin/sezon/${s}" style="${k != null ? formaSerit(k) : ""}">
        <span class="sk-yil">${s.slice(0, 4)}<small>–${s.slice(7)}</small></span>
        ${k != null ? `<span class="sk-sp">${kLogo(k)}<span><b>${esc(kAd(k))}</b><small>şampiyon</small></span></span>`
          : `<span class="sk-sp bos"><small>${var_ ? esc(z.sampiyon_not?.[s] || "şampiyon ilan edilmedi") : "sezon sürüyor"}</small></span>`}
        <span class="sk-alt"><span>${esc(kademeAd(s, 1))}</span><span>${t.takim.size} takım${t.oyn ? ` · ${(t.gol / t.oyn).toLocaleString("tr-TR", { maximumFractionDigits: 2, minimumFractionDigits: 2 })} gol/maç` : ""}</span></span></a>`; };
    ic.innerHTML = `<h2>Sezonlar ve şampiyonlar</h2>
      <div class="sezon-kartlar kadin-kartlar">${[...z.sezonlar].reverse().map(kart).join("")}</div>
      <h2 class="bolum">En çok şampiyonluk</h2>
      <div class="tablo-kap"><table class="tablo"><thead><tr><th class="ad">Kulüp</th><th class="s">Şampiyonluk</th><th class="ad">Sezonlar</th></tr></thead><tbody>
      ${[...sampiyonSay].sort((a, b) => b[1] - a[1]).map(([k, n]) => `<tr><td class="ad">${kBag(k)}</td><td class="s"><b>${n}</b></td>
        <td class="ad soluk">${z.sezonlar.filter(s => z.sampiyonlar[s] === k).join(", ")}</td></tr>`).join("")}</tbody></table></div>
      <p class="soluk not">Şampiyonlar en üst ligin (2021-22'ye kadar Kadınlar 1. Ligi, sonra Kadın Futbol Süper Ligi) sezon sonu sonucudur;
        play-off ve final turları dahil. Kaynak: RSSSF ve Vikipedi. 2006-07 (Gazi Üniversitesispor) ve öncesi sitede yok, TFF'de maç verisi bulunmuyor. Gol ortalaması en üst ligin normal sezon maçlarından.</p>`;
  } else if (sekme === "krallar") {
    ic.innerHTML = `<div class="tablo-kap"><table class="tablo"><thead><tr><th>Sezon</th><th class="ad">Lig</th><th class="ad">Oyuncu</th><th class="ad">Kulüp</th><th class="s">Gol</th></tr></thead><tbody>
      ${[...z.sezonlar].reverse().flatMap(s => Object.keys(z.krallar[s] || {}).sort().map(kd => { const k = z.krallar[s][kd]; return `<tr><td><a class="bag" href="#/kadin/sezon/${s}/${kd}">${s}</a></td><td class="ad soluk">${esc(kademeAd(s, +kd))}</td>
        <td class="ad">${k.map(x => oyBag(x[0], x[1])).join(", ")}</td><td class="ad">${k.map(x => kBag(x[3])).join(", ")}</td><td class="s"><b>${k[0][2]}</b></td></tr>`; })).join("")}</tbody></table></div>
      <p class="soluk not">Lig maçlarındaki goller (play-off ve final maçları hariç), TFF maç sayfalarından; kendi kalesine goller ve seri penaltılar sayılmaz. Gruplu liglerde bütün grupların en golcüsü. 2007-08 maç sayfalarında gol yok.</p>`;
  } else if (sekme === "kulupler") {
    const ciz = () => {
      const q = norm(anaDurum.kulupAra);
      const l = z.kulupler.filter(k => k.yerli !== false).filter(k => !q || norm(k.ad).includes(q) || k.adlar.some(a => norm(a[0]).includes(q)));
      $("#kKulupListe").innerHTML = `<div class="tablo-kap"><table class="tablo"><thead><tr><th class="ad">Kulüp</th><th>Sezonlar</th><th class="s">Maç</th></tr></thead><tbody>
        ${l.map(k => `<tr><td class="ad">${kBag(k.id)}</td><td class="soluk">${k.ilk?.slice(0, 4)}–${k.son?.slice(5)}</td><td class="s">${k.mac}</td></tr>`).join("")}</tbody></table></div>`;
    };
    ic.innerHTML = `<div class="filtre"><input id="kKulupAra" type="search" placeholder="Kulüp ara…" value="${esc(anaDurum.kulupAra)}"></div><div id="kKulupListe"></div>`;
    $("#kKulupAra").addEventListener("input", e => { anaDurum.kulupAra = e.target.value; ciz(); });
    ciz();
  } else {
    ic.innerHTML = `<div class="yukleniyor">Oyuncular yükleniyor…</div>`;
    const oy = await kOyuncular();
    const satir = (l, alan) => l.map((p, i) => `<tr><td class="s soluk">${i + 1}</td><td class="ad">${oyBag(p.kisi, p.ad)}</td><td class="ad">${kBag(p.kulup)}</td>
      <td class="soluk">${p.ilk.slice(0, 4)}–${p.son.slice(5)}</td><td class="s">${alan === "mac" ? `<b>${p.mac}</b>` : p.mac}</td><td class="s">${alan === "gol" ? `<b>${p.gol}</b>` : p.gol}</td></tr>`).join("");
    const bas = `<thead><tr><th class="s">#</th><th class="ad">Oyuncu</th><th class="ad">Son kulübü</th><th>Yıllar</th><th class="s">Maç</th><th class="s">Gol</th></tr></thead>`;
    const ciz = () => {
      const q = norm(anaDurum.oyuncuAra);
      $("#kOyListe").innerHTML = q.length >= 2
        ? `<div class="tablo-kap"><table class="tablo">${bas}<tbody>${satir(oy.filter(p => norm(p.ad).includes(q)).sort((a, b) => b.mac - a.mac).slice(0, 100), "mac")}</tbody></table></div>`
        : `<div class="izgara iki ust-hiza">
          <div><h2>En golcüler</h2><div class="tablo-kap"><table class="tablo">${bas}<tbody>${satir([...oy].sort((a, b) => b.gol - a.gol || a.mac - b.mac).slice(0, 50), "gol")}</tbody></table></div></div>
          <div><h2>En çok maça çıkanlar</h2><div class="tablo-kap"><table class="tablo">${bas}<tbody>${satir([...oy].sort((a, b) => b.mac - a.mac || b.gol - a.gol).slice(0, 50), "mac")}</tbody></table></div></div></div>`;
    };
    ic.innerHTML = `<div class="filtre"><input id="kOyAra" type="search" placeholder="Oyuncu ara…" value="${esc(anaDurum.oyuncuAra)}"></div><div id="kOyListe"></div>
      <p class="soluk not">Lig, play-off ve baraj maçları; 2008-09'dan bugüne TFF maç sayfalarındaki kadrolardan. Kendi kalesine goller ve seri penaltılar sayılmaz.</p>`;
    $("#kOyAra").addEventListener("input", e => { anaDurum.oyuncuAra = e.target.value; ciz(); });
    ciz();
  }
}

// ---------------------------------------------------------------- sezon
async function kadinSezon(sezon, kademeSec) {
  document.title = `Kadın ligleri ${sezon} · Türk Futbol Arşivi`;
  icerik.innerHTML = `<div class="yukleniyor">${esc(sezon)} yükleniyor…</div>`;
  const z = await kOzet(), ms = (await kMaclar()).filter(m => m.sezon === sezon);
  const i = z.sezonlar.indexOf(sezon), onceki = z.sezonlar[i - 1], sonraki = z.sezonlar[i + 1];
  const kademeler = [...new Set(ms.map(m => m.kademe))].sort();
  const kad = +kademeSec || kademeler[0];
  const km = ms.filter(m => m.kademe === kad);
  // lig bölümü sezon.js'teki ligBolumu ile (lig seçici, hafta kaydırıcı, sıralama yarışı, maçlar): kadın maçları o biçime çevrilir
  const cevir = m => ({ id: m.tff, tarih: m.tarih, yar: "L", lig: kademeAd(sezon, m.kademe), kademe: m.kademe, tur: m.grup || "", ev: m.ev, evAd: kAd(m.ev), dep: m.dep, depAd: kAd(m.dep),
    eg: m.eg, dg: m.dg, ep: m.ep, dp: m.dp, durum: m.durum === "H" ? "Hük." : m.durum });
  const gruplar = new Map();
  for (const m of ms.filter(m => !m.asama)) { const k = `${m.kademe}|${m.grup || ""}`; (gruplar.get(k) || gruplar.set(k, { yar: "L", kademe: m.kademe, lig: kademeAd(sezon, m.kademe), grup: m.grup ? (/^\d+$/.test(m.grup) ? `${+m.grup}. grup` : m.grup) : "", ms: [] }).get(k)).ms.push(cevir(m)); }
  const sirali = [...gruplar.values()].sort((a, b) => a.kademe - b.kademe || String(a.grup).localeCompare(String(b.grup), "tr", { numeric: true }));
  // çıkan / düşen: ertesi sezonun normal sezon maçlarından kademe karşılaştırması
  const kdm = s => { const t = new Map(); for (const m of KM.filter(x => x.sezon === s && !x.asama)) for (const id of [m.ev, m.dep]) t.set(id, Math.min(t.get(id) || 9, m.kademe)); return t; };
  const bu = kdm(sezon), ert = sonraki ? kdm(sonraki) : null, kk = {};
  if (ert?.size) for (const [id, a] of bu) { const b2 = ert.get(id), yon = b2 == null ? "a" : b2 < a ? "c" : b2 > a ? "d" : null; if (yon) ((kk[a] ||= { c: [], d: [], a: [] })[yon]).push(id); }
  const Zk = { [sezon]: { sampiyon: z.sampiyonlar?.[sezon] ?? null, k: kk } };
  const po = new Map();
  for (const m of ms.filter(m => m.asama)) { const k = `${kademeAd(sezon, m.kademe)} · ${m.asama === "play-off" ? "play-off maçları" : m.asama}`; (po.get(k) || po.set(k, []).get(k)).push(m); }
  const kral = z.krallar[sezon]?.[kad];
  icerik.innerHTML = `
  <div class="sayfa-bas"><h1>Kadın ligleri ${esc(sezon)}</h1>
    <div class="yan-yana">${onceki ? `<a class="cip" href="#/kadin/sezon/${onceki}">← ${onceki}</a>` : ""}${sonraki ? `<a class="cip" href="#/kadin/sezon/${sonraki}">${sonraki} →</a>` : ""}</div></div>
  <p class="soluk"><a class="bag" href="#/kadin">Kadın Futbolu</a> · ${ms.length} maç · Puan tabloları sonuçlardan hesaplandı (galibiyet 3 puan; puan silme cezaları dahil değil).</p>
  <section class="sezon-ozet" id="kOzet" aria-label="Sezon özeti (seçili lig)" aria-live="polite">
  </section>
  <div id="kLig"></div>
  ${po.size ? `<h2 class="bolum">Play-off ve final maçları</h2>${[...po].map(([k, l]) => `<div class="kart" style="margin-bottom:12px"><h3>${esc(k)}${l[0].grup ? ` · ${esc(l[0].grup)}` : ""}</h3>${macListe(l)}</div>`).join("")}` : ""}
  <p class="soluk not bolum">${NOT}</p>`;
  if (sirali.length) ligBolumu($("#kLig"), sezon, sirali, Zk, { ozet: $("#kOzet"),
    kral: async kd => { const l = z.krallar[sezon]?.[kd]; return l?.length ? l.map(x => ({ kisi: x[0], ad: x[1], gol: x[2], kulup: x[3] })) : null; } });
}

yollar.splice(yollar.length - 1, 0,
  [/^#\/kadin$/, () => kadinSayfa("sezonlar")],
  [/^#\/kadin\/(krallar|kulupler|oyuncular)$/, s => kadinSayfa(s)],
  [/^#\/kadin\/sezon\/([\d-]+)(?:\/(\d))?$/, (s, k) => kadinSezon(s, k)],
  [/^#\/oyuncu\/w(\d+)$/, id => location.replace(`#/kadin/oyuncu/k${id}`)]);   // 17.11'deki ilk sürümün oyuncu bağlantıları
})();

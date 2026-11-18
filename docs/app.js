"use strict";
/* Türk Futbol Arşivi — statik arayüz. Veri: data/*.json (web_aktar.py üretir). */

const $ = (s, k = document) => k.querySelector(s);
const icerik = $("#icerik");
const onbellek = new Map();
let KULUPLER = [], KULUP = new Map(), OZET = null;

// ---------------------------------------------------------------- yardımcılar
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const TRMAP = { "ç": "c", "ğ": "g", "ı": "i", "i̇": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u" };
const norm = s => String(s || "").toLocaleLowerCase("tr").replace(/[çğıöşüâîû]|i̇/g, c => TRMAP[c] || c)
  .replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
const tarihYaz = t => { if (!t) return "—"; const [y, a, g] = t.split("-"); return `${g}.${a}.${y}`; };
const YAR_AD = { L: "Lig", K: "Türkiye Kupası", O: "Diğer kupalar", A: "Avrupa", T: "Terfi" };
let KADEME_AD = { 1: "Süper Lig", 2: "1. Lig", 3: "TFF 2. Lig", 4: "TFF 3. Lig" };   // bugünkü adlar, seviyeye göre

// Bölüm: erkek (varsayılan) ya da kadın. Kulüp, maç ve oyuncu sayfaları iki bölümde aynı kodla çizilir; bölüm değişince
// OZET/KULUP/KADEME_AD ve önbellekler o bölümünkiyle değişir, bağlantılar K ("" | "kadin/"), veri yolları V ön ekini alır.
let K = "", V = "data/", BOLUM = "erkek";
const BOLUMLER = {}, BOLUM_YUKLE = {}, BOLUM_UST = {};   // BOLUM_UST.kadin(sekme): bölüm sayfalarının başlığı ve sekmeleri   // kadin.js BOLUM_YUKLE.kadin'i tanımlar: {OZET, KULUP, KADEME_AD}
async function bolumSec(ad) {
  if (ad === BOLUM) return;
  BOLUMLER[BOLUM] = { OZET, KULUP, KADEME_AD, DETAYLI, TFF_DIZIN };
  if (!BOLUMLER[ad]) BOLUMLER[ad] = { DETAYLI: null, TFF_DIZIN: null, ...(await BOLUM_YUKLE[ad]()) };
  ({ OZET, KULUP, KADEME_AD, DETAYLI, TFF_DIZIN } = BOLUMLER[ad]);
  BOLUM = ad; K = ad === "erkek" ? "" : ad + "/"; V = ad === "erkek" ? "data/" : `data/${ad}/`;
}
async function al(yol, secenek) {
  if (onbellek.has(yol)) return onbellek.get(yol);
  const p = fetch(yol, secenek).then(r => { if (!r.ok) throw new Error(yol + " " + r.status); return r.json(); });
  onbellek.set(yol, p);
  try { return await p; } catch (e) { onbellek.delete(yol); throw e; }
}
const kulupAd = id => KULUP.get(id)?.ad ?? "?";
// puan durumunda kısa ad: o sezonun resmi adı kulübün bugünkü adını içeriyorsa onu ("Rams Başakşehir Futbol Kulübü" ->
// "Başakşehir", "Galatasaray A.Ş." -> "Galatasaray"); içermiyorsa (eski adla oynadığı dönem) resmi addan şirket ekleri atılır
const KISA_EK = /\s+(A\.?\s?Ş\.?|Futbol\s+A\.?\s?Ş\.?|Kulübü|(Spor|Sportif)\s+Faaliyetler(i)?(\s+A\.?\s?Ş\.?)?)$/i;
// kulübün sitede görünen adı: şirket ekleri ve web adresi önekli sponsor atılır ("Göztepe A.Ş." -> "Göztepe",
// "Mısırlı.Com.Tr Fatih Karagümrük" -> "Fatih Karagümrük"); tam ad k.tamAd'da (aramada eski adlarla birlikte)
// "Futbol Kulübü" FK olur (Çorum FK, Bodrum FK gibi adın parçası; atılırsa şehir adı kalır), "A.Ş." ve "Kulübü" atılır
function adTemiz(s) {
  let a = String(s || "").replace(/^\S+\.(com|net|org)(\.tr)?\s+/i, "").replace(/\s+Futbol\s+Kulübü(\s+A\.?\s?Ş\.?|\s+SK)?$/i, " FK").replace(/\s+(Futbol\s+Spor|Gençlik\s+ve\s+Spor|Spor)\s+Kulübü$/i, " SK").trim(), once;
  do { once = a; a = a.replace(KISA_EK, "").trim(); } while (a !== once && a);
  return a || s;
}
function adSadele(k) {
  if (k.tamAd) return k;
  k.tamAd = k.ad;
  k.ad = adTemiz(k.ad);
  return k;
}
function kisaAd(id, resmi) {
  const k = KULUP.get(id);
  if (!resmi) return k?.ad ?? "?";
  const r = adTemiz(resmi);
  return k && norm(r).includes(norm(k.ad)) ? k.ad : r;
}
const logoImg = (id, cls = "logo-k") => { const l = KULUP.get(id)?.logo; return l ? `<img class="${cls}" src="logo/${l}.png" alt="" loading="lazy" onerror="this.remove()">` : ""; };
const kulupBag = (id, ad) => id != null && KULUP.has(id) ? `<a class="bag" href="#/${K}kulup/${id}">${logoImg(id)}${esc(ad ?? kulupAd(id))}</a>` : esc(ad ?? "?");
function sonuc(a, y) { if (a == null || y == null) return "N"; return a > y ? "G" : a < y ? "M" : "B"; }
function skorYaz(a, y, pa, py, durum) {
  if (a == null && durum === "Çifte H") return `0-3 / 3-0 <small class="soluk" title="İki takım da hükmen yenik">(çifte H)</small>`;
  if (a == null) return `<span class="soluk">${esc(durum === "Cancelled" ? "iptal" : "oynanmadı")}</span>`;
  let s = `${a}-${y}`;
  if (pa != null && py != null) s += ` <small class="soluk">(pen ${pa}-${py})</small>`;
  if (durum === "UZ") s += ` <small class="soluk">uz.</small>`;
  if (durum === "Hük.") s += ` <small class="soluk" title="Hükmen">(H)</small>`;
  if (durum === "Çifte H") s = `0-3 / 3-0 <small class="soluk" title="İki takım da hükmen yenik">(çifte H)</small>`;
  return s;
}
const yuzde = (a, b) => b ? Math.round(100 * a / b) : 0;

// ---------------------------------------------------------------- takım renkleri (logodan, web_aktar: renk)
const hexRgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const rgbHex = c => "#" + c.map(v => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0")).join("");
const parlaklik = h => { const [r, g, b] = hexRgb(h).map(v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }); return .2126 * r + .7152 * g + .0722 * b; };
const kontrast = (a, b) => { const x = parlaklik(a), y = parlaklik(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); };
const karistir = (h, hedef, t) => rgbHex(hexRgb(h).map((v, i) => v + (hexRgb(hedef)[i] - v) * t));
function yeterliKontrast(h, zemin, hedef, oran = 4.5) {   // h'yi hedefe (siyah/beyaz) doğru kaydırarak zeminle okunur yap
  for (let t = 0; t <= 1; t += .05) { const c = karistir(h, hedef, t); if (kontrast(c, zemin) >= oran) return c; }
  return hedef;
}
function takimTema(k) {
  if (!k?.renk?.length) return null;
  let [a, b] = k.renk;
  if (b && parlaklik(a) > .35 && parlaklik(b) < parlaklik(a)) [a, b] = [b, a];   // açık renk (sarı) zemin olmasın
  return {
    "--t1k": yeterliKontrast(a, "#ffffff", "#000000", 4.8),
    "--t2": b || karistir(a, "#ffffff", .35),
    "--tv-acik": yeterliKontrast(a, "#ffffff", "#000000"),
    "--tv-koyu": yeterliKontrast(a, "#14171c", "#ffffff"),
  };
}
function temaUygula(k) {
  const tema = takimTema(k);
  icerik.classList.toggle("tema-kulup", !!tema);
  icerik.removeAttribute("style");
  if (tema) for (const [ad, v] of Object.entries(tema)) icerik.style.setProperty(ad, v);
}
const sayiYaz = n => n.toLocaleString("tr-TR");

// ---------------------------------------------------------------- tema
(function tema() {
  const kayit = (() => { try { return localStorage.getItem("tema"); } catch { return null; } })();
  if (kayit) document.documentElement.dataset.theme = kayit;
  $("#tema").addEventListener("click", () => {
    const koyu = matchMedia("(prefers-color-scheme: dark)").matches;
    const simdi = document.documentElement.dataset.theme || (koyu ? "dark" : "light");
    const yeni = simdi === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = yeni;
    try { localStorage.setItem("tema", yeni); } catch { }
  });
})();

// ---------------------------------------------------------------- telefonda menü (≤720 px): düğme paneli açar/kapar
(function menuKur() {
  const ust = document.querySelector(".ust"), d = $("#menuDugme");
  if (!ust || !d) return;
  const ayarla = acik => { ust.classList.toggle("acik", acik); d.setAttribute("aria-expanded", acik); d.setAttribute("aria-label", acik ? "Menüyü kapat" : "Menüyü aç"); };
  d.addEventListener("click", () => ayarla(!ust.classList.contains("acik")));
  $("#ustMenu").addEventListener("click", e => { if (e.target.closest("a")) ayarla(false); });
  window.addEventListener("hashchange", () => ayarla(false));
  document.addEventListener("click", e => { if (!ust.contains(e.target)) ayarla(false); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && ust.classList.contains("acik")) { ayarla(false); d.focus(); } });
})();

// ---------------------------------------------------------------- kulüp arama
function aramaIndeksi() {
  for (const k of KULUPLER) {
    const adlar = new Set([k.ad, ...k.adlar.map(a => a[0])]);
    k._n = [...adlar].map(norm);
    k._nn = k._n.map(s => s.replace(/spor\b/g, "").replace(/\s+/g, " ").trim());
  }
}
function kulupAra(q, adet = 12) {
  const n = norm(q); if (!n) return [];
  const nn = n.replace(/spor\b/g, "").trim() || n;
  const sonuc = [];
  for (const k of KULUPLER) {
    let p = 0;
    for (let i = 0; i < k._n.length; i++) {
      const a = k._n[i], b = k._nn[i];
      let x = 0;
      if (a === n || b === nn) x = 100;
      else if (a.startsWith(n) || b.startsWith(nn)) x = 80;
      else if ((" " + a).includes(" " + n) || (" " + b).includes(" " + nn)) x = 60;
      else if (a.includes(n)) x = 40;
      if (x && i === 0) x += 5;
      p = Math.max(p, x);
    }
    if (p) sonuc.push([p + (k.yerli ? 10 : 0) + Math.min(k.mac / 400, 9), k]);
  }
  return sonuc.sort((a, b) => b[0] - a[0]).slice(0, adet).map(x => x[1]);
}
// kadın kulüpleri de aramada (ana sayfa arama kutusu): data/kadin/ozet.json'daki yerli kulüpler, gerektiğinde bir kez yüklenir
let KADIN_ARA = null;
async function kadinAraAl() {
  if (KADIN_ARA) return KADIN_ARA;
  const z = await al("data/kadin/ozet.json", { cache: "no-cache" }).catch(() => ({ kulupler: [] }));
  KADIN_ARA = z.kulupler.filter(k => k.yerli !== false).map(adSadele);
  for (const k of KADIN_ARA) k._n = [...new Set([k.ad, ...k.adlar.map(a => a[0])])].map(norm);
  return KADIN_ARA;
}
function kadinKulupAra(q, adet = 4) {
  const n = norm(q); if (!n || !KADIN_ARA) return [];
  return KADIN_ARA.map(k => [Math.max(...k._n.map(a => a === n ? 100 : a.startsWith(n) ? 80 : (" " + a).includes(" " + n) ? 60 : a.includes(n) ? 40 : 0)), k])
    .filter(x => x[0]).sort((a, b) => b[0] - a[0] || b[1].mac - a[1].mac).slice(0, adet).map(x => x[1]);
}
function kulupAltYazi(k) {
  const yil = `${k.ilk.slice(0, 4)}–${k.son.slice(0, 4)}`;
  if (!k.yerli) return `Avrupa rakibi · ${k.mac} maç`;
  return `${yil} · ${sayiYaz(k.mac)} maç${k.enust === 1 ? " · Süper Lig" : ""}`;
}
function oneriKutusu(input, kutu, secince) {
  let secili = -1, liste = [];
  const oyuncuVar = !input.dataset.yalnizKulup;
  const ciz = () => {
    liste = kulupAra(input.value, 10);
    const oy = oyuncuVar ? oyuncuAra(input.value) : [];
    const kd = oyuncuVar && BOLUM === "erkek" ? kadinKulupAra(input.value) : [];
    if (!liste.length && !oy.length && !kd.length) { kutu.hidden = true; return; }
    kutu.innerHTML = liste.map((k, i) => `<a href="#/${K}kulup/${k.id}" data-i="${i}" class="${i === secili ? "sec" : ""}">
      <span>${logoImg(k.id)}${esc(k.ad)}${eskiAdIpucu(k, input.value)}</span><small>${esc(kulupAltYazi(k))}</small></a>`).join("") +
      (oy.length ? `<div class="oneri-baslik">Oyuncular</div>` + oy.map(o => `<a href="#/${K}oyuncu/k${o.kisi}" class="oyuncu-oneri">
        <span>${esc(o.ad)}</span><small>${o.ilk.slice(0, 4)}–${o.son.slice(5)} · ${o.mac} maç${o.gol ? ` · ${o.gol} gol` : ""}${KULUP.get(o.kulup) ? ` · ${esc(KULUP.get(o.kulup).ad)}` : ""}</small></a>`).join("") : "") +
      (kd.length ? `<div class="oneri-baslik">Kadın takımları</div>` + kd.map(k => `<a href="#/kadin/kulup/${k.id}">
        <span>${k.logo ? `<img class="logo-k" src="logo/${k.logo}.png" alt="" loading="lazy" onerror="this.remove()">` : ""}${esc(k.ad)}</span><small>${k.ilk.slice(0, 4)}–${k.son.slice(0, 4)} · ${sayiYaz(k.mac)} maç${k.enust === 1 ? " · Kadın Süper Ligi" : ""}</small></a>`).join("") : "");
    kutu.hidden = false;
  };
  input.addEventListener("input", () => { secili = -1; if (oyuncuVar && norm(input.value).length >= 3 && !OYUNCULAR) oyuncuDiziniAl().then(ciz);
    if (oyuncuVar && BOLUM === "erkek" && !KADIN_ARA) kadinAraAl().then(ciz); ciz(); });
  input.addEventListener("focus", () => input.value && ciz());
  input.addEventListener("keydown", e => {
    if (kutu.hidden) return;
    if (e.key === "ArrowDown") { secili = Math.min(secili + 1, liste.length - 1); ciz(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { secili = Math.max(secili - 1, 0); ciz(); e.preventDefault(); }
    else if (e.key === "Enter") { const k = liste[Math.max(secili, 0)]; if (k) { secince(k); kutu.hidden = true; } e.preventDefault(); }
    else if (e.key === "Escape") kutu.hidden = true;
  });
  kutu.addEventListener("mousedown", e => {
    const a = e.target.closest("a[data-i]"); if (!a) return;
    e.preventDefault(); secince(liste[+a.dataset.i]); kutu.hidden = true;
  });
  document.addEventListener("click", e => { if (!kutu.contains(e.target) && e.target !== input) kutu.hidden = true; });
}
function eskiAdIpucu(k, q) {
  const n = norm(q); if (!n || k._n[0].includes(n)) return "";
  const a = k.adlar.find(a => norm(a[0]).includes(n));
  return a ? ` <small class="soluk">(${esc(a[0])})</small>` : "";
}

// ---------------------------------------------------------------- yönlendirme
const yollar = [
  [/^#?\/?$/, anaSayfa],
  [/^#\/kulup\/(\d+)(?:\/(\w+))?$/, (id, s) => kulupSayfa(+id, s || "ozet")],
  [/^#\/h2h\/(\d+)\/(\d+)$/, (a, b) => ikiliSayfa(+a, +b)],
  [/^#\/sezonlar$/, sezonlarSayfa],
  [/^#\/sezon\/([\d-]+)$/, s => sezonSayfa(s)],
  [/^#\/rekorlar(?:\/(\w+))?$/, k => rekorlarSayfa(k || "tum")],
  // (13.11.2026'daki eski Avrupa numaralarına yönlendirme 17.11'de kaldırıldı: lig maçlarının numaraları o aralığa ulaştı)
  [/^#\/mac\/(\d+)$/, id => macSayfa(+id)],
  [/^#\/oyuncu\/u(\d+)$/, id => oyuncuSayfa(id)],
  [/^#\/oyuncu\/k(\d+)$/, id => tffOyuncuSayfa(+id)],
  [/^#\/oyuncu\/t(\d+)$/, id => oyuncuSayfa(null, id)],
  [/^#\/oyuncu\/(a\d+)$/, id => oyuncuSayfa(null, id)],
  [/^#\/karsilastir$/, karsilastirSayfa],
  [/^#\/hakkinda$/, hakkindaSayfa],
];
async function yonlendir() {
  const h = location.hash || "#/";
  const hn = h.startsWith("#/kadin/milli") ? "#/milli" : h;   // kadın milli takımı Milli Takım bölümünde (erkek / kadın sekmesi)
  document.querySelectorAll(".ust nav a").forEach(a => a.classList.toggle("aktif", hn.startsWith(a.getAttribute("href"))));
  temaUygula(null);
  const bolum = h.startsWith("#/kadin") ? "kadin" : "erkek";
  try { await bolumSec(bolum); } catch (e) { icerik.innerHTML = `<div class="bos">Veri yüklenemedi (${esc(e.message)}).</div>`; return; }
  const h0 = bolum === "erkek" ? h : h.replace(/^#\/kadin\/(?=(kulup|mac|oyuncu|h2h)\/|(rekorlar|sayilar|milli)(\/|$))/, "#/");
  for (const [re, f] of yollar) {
    const m = h.match(re) || (h0 !== h && /^\^#\\\/(kulup|mac|oyuncu|h2h|rekorlar|sayilar|milli)/.test(re.source) ? h0.match(re) : null);
    if (m) {
      try { await f(...m.slice(1).map(x => x && decodeURIComponent(x))); }
      catch (e) { console.error(e); icerik.innerHTML = `<div class="bos">Bir hata oluştu: ${esc(e.message)}</div>`; }
      return;
    }
  }
  icerik.innerHTML = `<div class="bos">Sayfa bulunamadı. <a class="bag" href="#/">Ana sayfa</a></div>`;
}
window.addEventListener("hashchange", () => { yonlendir(); window.scrollTo(0, 0); });

// ---------------------------------------------------------------- ana sayfa
function anaSayfa() {
  document.title = "Türk Futbol Arşivi";
  const y = OZET.yarisma;
  const ornek = ["Göztepe", "Sarıyer", "Kayserispor", "Zonguldakspor", "Bursaspor", "Pendikspor", "Altay", "Sivasspor"];
  icerik.innerHTML = `
  <section class="kahraman">
    <h1>Türk futbolunun maç arşivi</h1>
    <p>1959'dan bugüne profesyonel lig maçları, Türkiye Kupası ve Türk takımlarının Avrupa kupası maçları. Bir kulüp ara, rekorlarına, serilerine ve rakiplerine bak.</p>
    <div class="buyuk-ara"><input id="anaAra" type="search" placeholder="Kulüp ya da oyuncu adı yaz…" autocomplete="off" autofocus><div id="anaOneri" class="oneri" hidden></div></div>
    <div class="cipler" style="justify-content:center;margin-top:16px">${ornek.map(a => { const k = kulupAra(a, 1)[0]; return k ? `<a class="cip" href="#/${K}kulup/${k.id}">${esc(a)}</a>` : ""; }).join("")}</div>
    <div class="sayilar">
      <div class="sayi"><b>${sayiYaz(OZET.mac)}</b><span>maç</span></div>
      <div class="sayi"><b>${sayiYaz(OZET.kulup)}</b><span>kulüp</span></div>
      <div class="sayi"><b>${sayiYaz(y.lig || 0)}</b><span>lig maçı</span></div>
      <div class="sayi"><b>${sayiYaz(y.kupa || 0)}</b><span>kupa maçı</span></div>
      <div class="sayi"><b>${sayiYaz(y.avrupa || 0)}</b><span>Avrupa maçı</span></div>
      <div class="sayi"><b>${OZET.sezonlar.length}</b><span>sezon</span></div>
    </div>
  </section>
  <section class="bolum izgara k3">
    <a class="kart" href="#/sezonlar"><h3>Sezonlar →</h3><p class="soluk">Her sezonun puan tabloları, kupa turları ve Avrupa maçları.</p></a>
    <a class="kart" href="#/elo"><h3>Elo puan durumu →</h3><p class="soluk">1959'dan bugüne bütün maçlardan hesaplanan güç puanı: bugünkü sıralama, tüm zamanların zirveleri ve en büyük sürprizler.</p></a>
    <a class="kart" href="#/sayilar"><h3>Sayılarla Türk futbolu →</h3><p class="soluk">Dönemlere göre gol ortalaması, skorlar, derbiler ve Süper Lig'de oynamış bütün kulüpler.</p></a>
    <a class="kart" href="#/rekorlar"><h3>Tüm zamanlar rekorları →</h3><p class="soluk">En farklı skorlar, en uzun seriler ve tüm zamanlar puan tabloları.</p></a>
    <a class="kart" href="#/karsilastir"><h3>İki kulübü karşılaştır →</h3><p class="soluk">Aralarındaki bütün maçlar ve genel denge.</p></a>
    <a class="kart" href="#/hakkinda"><h3>Veri hakkında →</h3><p class="soluk">Kaynaklar, kapsam ve bilinen sınırlar.</p></a>
  </section>`;
  oneriKutusu($("#anaAra"), $("#anaOneri"), k => location.hash = `#/kulup/${k.id}`);
}

// ---------------------------------------------------------------- kulüp verisi
async function kulupMaclari(id) {
  const d = await al(`${V}kulup/${id}.json?s=${OZET.surum || ""}`);
  return d.maclar.map(r => ({
    id: r[0], tarih: r[1], sezon: r[2], yar: r[3], lig: r[4], kademe: r[5], tur: r[6], po: r[7] === "p", saha: r[8],
    takim: r[9], rakipId: r[10], rakip: r[11], a: r[12], y: r[13], pa: r[14], py: r[15], durum: r[16], not: r[17], kulup: id,
    iptal: r[7] === "x", s: r[7] === "x" ? "N" : sonuc(r[12], r[13]),   // geçersiz maç istatistiğe girmez
  }))   // tarihsiz maçlar (sonradan eklenen hükmenler) kendi sezonlarının sonuna
    .map((m, i) => ({ m, i, k: m.tarih || `${m.sezon.slice(-4)}-07-01` }))
    .sort((a, b) => a.k.localeCompare(b.k) || a.i - b.i).map(x => x.m);
}
function oncul(id, gor = new Set()) {   // öncül kulüpler (kulup_ardil), özyinelemeli
  if (gor.has(id)) return []; gor.add(id);
  const k = KULUP.get(id); if (!k) return [];
  return k.ardil.filter(a => a.yon === "onceki").flatMap(a => [a.kulup, ...oncul(a.kulup, gor)]);
}
function toplam(ms) {
  const t = { O: 0, G: 0, B: 0, M: 0, AG: 0, YG: 0, GY: 0 };
  for (const m of ms) { if (m.s === "N") continue; t.O++; t[m.s]++; t.AG += m.a; t.YG += m.y; if (m.y === 0) t.GY++; }
  return t;
}
const HUKMEN_DURUM = new Set(["Hük.", "Çifte H"]);
function seriler(ms) {
  const tanim = [
    ["galibiyet", "Galibiyet serisi", m => m.s === "G"],
    ["yenilmezlik", "Yenilmezlik serisi", m => m.s !== "M"],
    ["golyemeden", "Gol yemeden", m => m.y === 0],
    ["golatarak", "Gol atarak", m => m.a > 0],
    ["maglubiyet", "Mağlubiyet serisi", m => m.s === "M"],
    ["galibiyetsiz", "Galibiyetsiz seri", m => m.s !== "G"],
    ["golsuz", "Gol atamadan", m => m.a === 0],
  ];
  // hükmen sonuçlar seriye girmez (atlanır, seriyi bozmaz); tarihsiz maçlar sıralanamaz
  const oynanan = ms.filter(m => m.s !== "N" && m.tarih && !HUKMEN_DURUM.has(m.durum));
  const sira = new Map((OZET.sezonlar || []).map((s, i) => [s, i]));
  return tanim.map(([k, ad, f]) => {
    let en = { n: 0 }, cur = { n: 0 };
    for (let i = 0; i < oynanan.length; i++) {
      // seçili maçlarda kulübün bulunmadığı sezon(lar) varsa seri kesilir (ör. ligden düşüp yıllar sonra dönmek)
      if (i && sira.get(oynanan[i].sezon) - sira.get(oynanan[i - 1].sezon) > 1) cur = { n: 0 };
      if (f(oynanan[i])) { if (!cur.n) cur.bas = i; cur.n++; if (cur.n > en.n) en = { n: cur.n, bas: cur.bas, son: i }; }
      else cur = { n: 0 };
    }
    const devam = cur.n ? { n: cur.n, bas: cur.bas, son: oynanan.length - 1 } : null;
    return { k, ad, en, devam, liste: oynanan };
  });
}

const FILTRE_VARSAYILAN = { yar: "L", saha: "", sezon: "", sonuc: "", rakip: "", sira: "yeni", oncul: false };
const kulupDurum = new Map();   // kulüp başına filtre durumu (sayfa içinde)

async function kulupSayfa(id, sekme) {
  const k = KULUP.get(id);
  if (!k) { icerik.innerHTML = `<div class="bos">Kulüp bulunamadı.</div>`; return; }
  document.title = `${k.ad} · Türk Futbol Arşivi`;
  icerik.innerHTML = `<div class="yukleniyor">${esc(k.ad)} yükleniyor…</div>`;
  const durum = kulupDurum.get(id) || { ...FILTRE_VARSAYILAN, yar: k.yerli ? "L" : "" };
  kulupDurum.set(id, durum);
  const kendi = await kulupMaclari(id);
  const onculler = oncul(id);
  let tum = kendi;
  if (durum.oncul && onculler.length) {
    const ek = (await Promise.all(onculler.map(kulupMaclari))).flat();
    const gor = new Set(kendi.map(m => m.id));
    tum = [...kendi, ...ek.filter(m => !gor.has(m.id) && !onculler.includes(m.rakipId) && m.rakipId !== id)]
      .sort((a, b) => (a.tarih || "").localeCompare(b.tarih || "") || a.id - b.id);
  }
  const ardilHtml = k.ardil.map(a => `<div class="uyari">${a.yon === "onceki" ? "Öncülü" : "Ardılı"}: ${kulupBag(a.kulup)} · ${esc(a.sezon || "")} ${esc(a.tur || "")}${a.aciklama ? ` — <span class="soluk">${esc(a.aciklama)}</span>` : ""}</div>`).join("");
  const adlar = k.adlar.filter(a => a[3] >= 3);
  temaUygula(k);
  const harf = k.ad.replace(/[^A-Za-zÇĞİÖŞÜçğıöşü0-9 ]/g, "").split(" ").filter(Boolean).slice(0, 2).map(w => w[0]).join("").toLocaleUpperCase("tr");
  icerik.innerHTML = `
  <section class="kulup-hero">
    ${k.logo ? `<img class="hero-filigran" src="logo/${k.logo}.png" alt="">` : ""}
    <div class="hero-ic">
      <div class="hero-logo ${k.logo ? "" : "harf"}">${k.logo ? `<img src="logo/${k.logo}.png" alt="">` : esc(harf)}</div>
      <div class="hero-metin">
        <h1>${esc(k.ad)}</h1>
        <div class="hero-meta"><span><b>${esc(k.ilk.slice(0, 4))}–${esc(k.son.slice(-4))}</b></span><span><b>${sayiYaz(k.mac)}</b> resmi maç</span>
          ${k.tff.length ? `<span>TFF ${k.tff.map(esc).join(", ")}</span>` : ""}${!k.yerli ? `<span>Avrupa rakibi</span>` : ""}</div>
        ${adlar.length > 1 ? `<div class="adlar">${adlar.slice(-4).reverse().map(a => `<span>${esc(a[0])}<em>${a[1].slice(0, 4)}–${a[2].slice(-4)}</em></span>`).join("")}
          ${adlar.length > 4 ? `<span title="${esc(adlar.slice(0, -4).map(a => `${a[0]} (${a[1].slice(0, 4)}–${a[2].slice(-4)})`).join("\n"))}">+${adlar.length - 4} eski ad</span>` : ""}</div>` : ""}
      </div>
      ${BOLUM === "erkek" ? `<a class="dugme" href="#/karsilastir" data-a="${id}" id="karsBtn">Karşılaştır</a>` : k.erkek != null ? `<a class="dugme" href="#/kulup/${k.erkek}">Erkek takımı</a>` : ""}
    </div>
  </section>
  ${ardilHtml}
  <div class="kulup-sekme"><nav class="sekmeler">
    ${[["ozet", "Özet"], ["rekorlar", "Rekorlar ve seriler"], ["maclar", "Maçlar"], ["rakipler", "Rakipler"], ["sezonlar", "Sezon sezon"]]
      .map(([s, ad]) => `<a href="#/${K}kulup/${id}/${s}" class="${s === sekme ? "aktif" : ""}">${ad}</a>`).join("")}
  </nav></div>
  <div id="filtreAlan"></div>
  <div id="sekmeIcerik"></div>`;
  $("#karsBtn")?.addEventListener("click", () => { karsilastirSecim.a = id; });

  const ciz = () => {
    $("#filtreAlan").innerHTML = filtreHtml(durum, tum, sekme, onculler);
    filtreBagla(durum, () => { kulupSayfa(id, sekme); }, ciz);
    const ms = filtrele(tum, durum, sekme);
    const hedef = $("#sekmeIcerik");
    if (sekme === "ozet") {
      hedef.innerHTML = ozetHtml(tum, durum);
      if (BOLUM === "erkek") { if (typeof yolculukCiz === "function") yolculukCiz(hedef, id); if (typeof eloCiz === "function") eloCiz(hedef, id); }
      tffOyunculari(hedef, id); if (tum.some(m => m.yar === "A")) avrupaOyunculari(hedef, id);
    }
    else if (sekme === "rekorlar") { hedef.innerHTML = rekorHtml(ms); tffOyuncuRekorlari($("#oyuncuRekor"), id); }
    else if (sekme === "maclar") macTablosu(hedef, ms, durum);
    else if (sekme === "rakipler") rakipTablosu(hedef, ms, id);
    else if (sekme === "sezonlar") hedef.innerHTML = sezonSezonHtml(tum);
  };
  ciz();
}

function filtrele(ms, d, sekme) {
  return ms.filter(m => (!d.yar || m.yar === d.yar) && (!d.saha || m.saha === d.saha)
    && (sekme === "rekorlar" || sekme === "rakipler" ? true : (!d.sezon || m.sezon === d.sezon))
    && (sekme !== "maclar" || ((!d.sonuc || (d.sonuc === "GY" ? m.y === 0 && m.s !== "N" : m.s === d.sonuc)) && (!d.rakip || norm(m.rakip).includes(norm(d.rakip))))));
}
function filtreHtml(d, ms, sekme, onculler) {
  if (sekme === "ozet" || sekme === "sezonlar") {
    return onculler.length ? `<div class="filtre"><label><input type="checkbox" id="fOncul" ${d.oncul ? "checked" : ""}> Öncül kulüplerin maçlarını da kat (${onculler.map(kulupAd).map(esc).join(", ")})</label></div>` : "";
  }
  const yarlar = [...new Set(ms.map(m => m.yar))];
  const cip = (ad, deger, alan) => `<button class="cip ${d[alan] === deger ? "aktif" : ""}" data-alan="${alan}" data-deger="${deger}">${ad}</button>`;
  const sezonlar = [...new Set(ms.map(m => m.sezon))].sort().reverse();
  return `<div class="filtre">
    <div class="cipler">${cip("Tümü", "", "yar")}${["L", "K", "O", "A", "T"].filter(y => yarlar.includes(y)).map(y => cip(YAR_AD[y], y, "yar")).join("")}</div>
    <div class="cipler">${cip("İç + dış", "", "saha")}${cip("İç saha", "E", "saha")}${cip("Deplasman", "D", "saha")}</div>
    ${sekme === "maclar" ? `
      <div class="cipler">${cip("Her sonuç", "", "sonuc")}${cip("G", "G", "sonuc")}${cip("B", "B", "sonuc")}${cip("M", "M", "sonuc")}${cip("Gol yemedi", "GY", "sonuc")}</div>
      <select id="fSezon"><option value="">Bütün sezonlar</option>${sezonlar.map(s => `<option ${s === d.sezon ? "selected" : ""}>${s}</option>`).join("")}</select>
      <input type="search" id="fRakip" placeholder="Rakip ara…" value="${esc(d.rakip)}">
      <select id="fSira">${[["yeni", "En yeni"], ["eski", "En eski"], ["fark", "En farklı galibiyet"], ["farkm", "En farklı mağlubiyet"], ["gol", "En gollü"]]
        .map(([v, a]) => `<option value="${v}" ${d.sira === v ? "selected" : ""}>${a}</option>`).join("")}</select>` : ""}
    ${onculler.length ? `<label><input type="checkbox" id="fOncul" ${d.oncul ? "checked" : ""}> Öncülleri kat</label>` : ""}
  </div>`;
}
function filtreBagla(d, yenidenYukle, ciz) {
  document.querySelectorAll("#filtreAlan .cip").forEach(b => b.addEventListener("click", () => { d[b.dataset.alan] = b.dataset.deger; ciz(); }));
  $("#fSezon")?.addEventListener("change", e => { d.sezon = e.target.value; ciz(); });
  $("#fSira")?.addEventListener("change", e => { d.sira = e.target.value; ciz(); });
  const r = $("#fRakip");
  if (r) { r.addEventListener("input", e => { d.rakip = e.target.value; clearTimeout(r._t); r._t = setTimeout(() => { ciz(); const n = $("#fRakip"); n.focus(); n.setSelectionRange(n.value.length, n.value.length); }, 250); }); }
  $("#fOncul")?.addEventListener("change", e => { d.oncul = e.target.checked; yenidenYukle(); });
}

function ozetSatir(t) {
  return `<div class="ozet-sat">
    <div><b>${sayiYaz(t.O)}</b><span>Maç</span></div><div><b>${sayiYaz(t.G)}</b><span>Galibiyet</span></div>
    <div><b>${sayiYaz(t.B)}</b><span>Beraberlik</span></div><div><b>${sayiYaz(t.M)}</b><span>Mağlubiyet</span></div>
    <div><b>${sayiYaz(t.AG)}</b><span>Attığı</span></div><div><b>${sayiYaz(t.YG)}</b><span>Yediği</span></div>
    <div><b>${sayiYaz(t.GY)}</b><span>Gol yemediği</span></div>
  </div>
  <div class="cubuk"><i class="g" style="width:${yuzde(t.G, t.O)}%"></i><i class="b" style="width:${yuzde(t.B, t.O)}%"></i><i class="m" style="width:${yuzde(t.M, t.O)}%"></i></div>
  <p class="soluk" style="margin:8px 0 0;font-size:13px">Galibiyet oranı %${yuzde(t.G, t.O)} · Kalesini gole kapattığı maç %${yuzde(t.GY, t.O)} · Maç başı ${(t.AG / Math.max(t.O, 1)).toFixed(2)} – ${(t.YG / Math.max(t.O, 1)).toFixed(2)} gol</p>`;
}
function ozetHtml(ms) {
  const bolumler = [["", "Bütün resmi maçlar"], ["L", "Lig"], ["K", "Türkiye Kupası"], ["O", "Diğer kupalar (Cumhurbaşkanlığı, Başbakanlık, Atatürk Kupası, TFF Süper Kupa)"], ["A", "Avrupa kupaları"], ["T", "Terfi maçları"]];
  const kartlar = bolumler.map(([y, ad]) => {
    const alt = ms.filter(m => !y || m.yar === y); if (!alt.length) return "";
    return `<div class="kart"><h3>${ad}</h3>${ozetSatir(toplam(alt))}</div>`;
  }).join("");
  const son = ms.filter(m => m.s !== "N" && m.tarih).slice(-10).reverse();
  const ligBas = {}, eskiAd = {};
  for (const m of ms) if (m.yar === "L" && m.kademe) {
    (ligBas[m.kademe] ||= new Set()).add(m.sezon);
    if (m.lig) (eskiAd[m.kademe] ||= new Set()).add(m.lig.replace(/\.(?=\S)/g, ". ").replace(/\s+/g, " ").trim());
  }
  const ligSatiri = kd => {
    const ss = [...ligBas[kd]].sort();
    const eski = [...(eskiAd[kd] || [])].filter(a => norm(a) !== norm(KADEME_AD[kd]) && norm("TFF " + a) !== norm(KADEME_AD[kd]));
    return `<p style="margin:6px 0"><b>${KADEME_AD[kd]}</b>: ${ss.length} sezon <span class="soluk">(${ss[0].slice(0, 4)}–${ss.at(-1).slice(-4)})</span>
      ${eski.length ? `<br><small class="soluk">Dönemin adıyla: ${eski.map(esc).join(", ")}</small>` : ""}</p>`;
  };
  return `<div class="izgara k2">${kartlar}</div>
  <div class="kart viz" id="yolculuk" hidden></div>
  <div class="kart viz" id="elo" hidden></div>
  <div class="bolum izgara k2">
    <div class="kart"><h3>Liglerde geçirdiği sezonlar</h3>
      ${Object.keys(ligBas).sort().map(ligSatiri).join("") || `<p class="soluk">Lig maçı yok.</p>`}
      <p class="soluk" style="font-size:12px;margin-top:10px">Ligler bugünkü adlarıyla, seviyeye göre gösterilir (Süper Lig = en üst lig).</p>
    </div>
    <div class="kart"><h3>Son maçlar</h3>
      ${son.map(m => `<div class="son-satir"><span class="son ${m.s}">${m.s}</span>
        <span class="tarih">${tarihYaz(m.tarih)}</span><span class="rakip">${kulupBag(m.rakipId, m.rakip)}${m.saha === "E" ? "" : ` <small class="soluk" title="Deplasman">(D)</small>`}</span>
        <b class="skor">${skorBag(m.id, skorYaz(m.a, m.y, m.pa, m.py, m.durum))}</b></div>`).join("")}
    </div>
  </div>`;
}

function macSatir(m, gosterTakim) {
  return `<tr><td class="o"><span class="son ${m.s}">${m.s === "N" ? "–" : m.s}</span></td>
    <td>${tarihYaz(m.tarih)}</td><td><a class="bag" href="#/${K}sezon/${m.sezon}">${esc(m.sezon)}</a></td>
    <td class="gizle-mobil">${esc(m.lig || YAR_AD[m.yar])}${m.tur ? ` <span class="soluk">· ${esc(m.tur)}</span>` : ""}${m.po ? ` <span class="rozet">play-off</span>` : ""}${m.iptal ? ` <span class="rozet" title="${esc(m.not || "")}">sayılmadı</span>` : ""}</td>
    ${gosterTakim ? `<td class="ad">${logoImg(m.kulup)}${esc(m.takim)}</td>` : ""}
    <td class="o">${m.saha === "E" ? "İç" : "Dış"}</td>
    <td class="ad">${kulupBag(m.rakipId, m.rakip)}</td>
    <td class="s skor">${detayVar(m.id) ? `<a class="skor bagli" href="#/${K}mac/${m.id}">${skorYaz(m.a, m.y, m.pa, m.py, m.durum)}</a>` : skorYaz(m.a, m.y, m.pa, m.py, m.durum)}</td></tr>`;
}
function macTablosu(hedef, ms, d) {
  const siralar = {
    yeni: (a, b) => (b.tarih || "").localeCompare(a.tarih || "") || b.id - a.id,
    eski: (a, b) => (a.tarih || "").localeCompare(b.tarih || "") || a.id - b.id,
    fark: (a, b) => ((b.a ?? -99) - (b.y ?? 0)) - ((a.a ?? -99) - (a.y ?? 0)) || (b.a - a.a),
    farkm: (a, b) => ((b.y ?? -99) - (b.a ?? 0)) - ((a.y ?? -99) - (a.a ?? 0)) || (b.y - a.y),
    gol: (a, b) => ((b.a ?? -1) + (b.y ?? 0)) - ((a.a ?? -1) + (a.y ?? 0)),
  };
  const liste = [...ms].sort(siralar[d.sira] || siralar.yeni);
  const t = toplam(liste);
  let n = 200;
  const ciz = () => {
    hedef.innerHTML = `<p class="soluk">${sayiYaz(liste.length)} maç · ${t.G}G ${t.B}B ${t.M}M · ${t.AG}-${t.YG} · ${t.GY} maçta gol yemedi</p>
      ${liste.length ? `<div class="tablo-kap"><table class="tablo"><thead><tr><th class="o">S</th><th>Tarih</th><th>Sezon</th><th class="gizle-mobil">Yarışma</th><th class="o">Saha</th><th>Rakip</th><th class="s">Skor</th></tr></thead>
      <tbody>${liste.slice(0, n).map(m => macSatir(m)).join("")}</tbody></table></div>` : `<div class="bos">Bu filtreye uyan maç yok.</div>`}
      ${liste.length > n ? `<button class="dugme daha" id="daha">${sayiYaz(liste.length - n)} maç daha göster</button>` : ""}`;
    $("#daha")?.addEventListener("click", () => { n += 500; ciz(); });
  };
  ciz();
}

// skor tabelası satırı: [G/B/M] · tarih · ev logosu + adı · skor · deplasman adı + logosu (sayfadaki kulübün adı bağlantısız)
function tabelaSatir(m, sonucGoster = false) {
  const ad = (id, ad) => id !== m.kulup && id != null && KULUP.has(id) ? `<a class="bag" href="#/${K}kulup/${id}">${esc(ad)}</a>` : `<span>${esc(ad)}</span>`;
  const [evId, evAd, depId, depAd, eg, dg, ep, dp] = m.saha === "E" ? [m.kulup, m.takim, m.rakipId, m.rakip, m.a, m.y, m.pa, m.py] : [m.rakipId, m.rakip, m.kulup, m.takim, m.y, m.a, m.py, m.pa];
  const skor = m.durum === "Çifte H" ? "0-3 / 3-0" : eg == null ? "–" : `${eg} - ${dg}`;
  const ek = ep != null && dp != null ? ` <small class="soluk">(pen ${ep}-${dp})</small>` : m.durum === "Hük." ? ` <small class="soluk">(H)</small>` : "";
  return `<div class="tabela${sonucGoster ? " sonuclu" : ""}" title="${esc(m.lig || YAR_AD[m.yar])}${m.tur ? " · " + esc(m.tur) : ""}">
    ${sonucGoster ? `<span class="son ${m.s}">${m.s === "N" ? "–" : m.s}</span>` : ""}
    <span class="tarih">${tarihYaz(m.tarih)}</span>
    <span class="ev">${logoImg(evId)}${ad(evId, evAd)}</span>
    ${m.id != null && detayVar(m.id) ? `<a class="skor bagli" href="#/${K}mac/${m.id}" title="Maç ayrıntısı">${skor}${ek}</a>` : `<b class="skor">${skor}${ek}</b>`}
    <span class="dep">${ad(depId, depAd)}${logoImg(depId)}</span></div>`;
}
function rekorKart(baslik, l) {
  const m = l?.[0];
  if (!m) return `<div class="kart rekor"><span class="baslik">${baslik}</span><span class="soluk">—</span></div>`;
  return `<div class="kart rekor"><span class="baslik">${baslik}</span>
    <span class="deger">${Math.abs(m.a - m.y) ? `${Math.max(m.a, m.y)}-${Math.min(m.a, m.y)}` : `${m.a}-${m.y}`}</span>
    <div class="tabelalar">${l.slice(0, 4).map(m => tabelaSatir(m)).join("")}</div>
    ${l.length > 4 ? `<span class="detay">ve aynı skorla ${l.length - 4} maç daha</span>` : ""}</div>`;
}
function enIyi(ms, f, esit) {   // rekor + aynı değerdeki bütün maçlar (en eskiden yeniye)
  let en = null, l = [];
  for (const m of ms) {
    if (m.s === "N") continue;
    const k = !en ? 1 : f(m) - f(en) || (esit ? esit(m) - esit(en) : 0);
    if (k > 0) { en = m; l = [m]; } else if (k === 0) l.push(m);
  }
  return l;
}
function rekorHtml(ms0) {
  if (!ms0.filter(m => m.s !== "N").length) return `<div class="bos">Bu filtreye uyan maç yok.</div>`;
  const hukmenSay = ms0.filter(m => m.s !== "N" && HUKMEN_DURUM.has(m.durum)).length;
  const ms = ms0.filter(m => !HUKMEN_DURUM.has(m.durum));   // hükmen sonuçlar maç rekorlarına ve gol sayımlarına girmez
  const gal = enIyi(ms, m => m.a - m.y, m => m.a), mag = enIyi(ms, m => m.y - m.a, m => m.y), gol = enIyi(ms, m => m.a + m.y, m => m.a - m.y);
  const evG = enIyi(ms.filter(m => m.saha === "E"), m => m.a - m.y, m => m.a), depG = enIyi(ms.filter(m => m.saha === "D"), m => m.a - m.y, m => m.a);
  const sr = seriler(ms);
  const seriKart = s => {
    const r = s.en.n ? `<span class="deger">${s.en.n} maç</span><span class="detay">${tarihYaz(s.liste[s.en.bas].tarih)} – ${tarihYaz(s.liste[s.en.son].tarih)}</span>
      <span class="detay">${esc(s.liste[s.en.bas].sezon)}${s.liste[s.en.son].sezon !== s.liste[s.en.bas].sezon ? " → " + esc(s.liste[s.en.son].sezon) : ""}</span>` : `<span class="soluk">—</span>`;
    const dv = s.devam && s.devam.n > 1 ? `<span class="detay"><b>Süren seri:</b> ${s.devam.n} maç</span>` : "";
    return `<details class="kart rekor"><summary><span class="baslik">${s.ad}</span>${r}${dv}</summary>
      ${s.en.n ? `<div class="seri-maclar tabelalar">${s.liste.slice(s.en.bas, s.en.son + 1).map(m => tabelaSatir(m, true)).join("")}</div>` : ""}</details>`;
  };
  // kalesini gole kapattığı maçlar: toplam, iç/dış, en iyi sezonlar
  const oy = ms.filter(m => m.s !== "N"), gy = oy.filter(m => m.y === 0);
  const sz = new Map();
  for (const m of oy) { const x = sz.get(m.sezon) || { sezon: m.sezon, O: 0, GY: 0 }; x.O++; if (m.y === 0) x.GY++; sz.set(m.sezon, x); }
  const enSezon = [...sz.values()].filter(x => x.O >= 5).sort((a, b) => b.GY - a.GY || b.GY / b.O - a.GY / a.O).slice(0, 5);
  const gyKart = `<div class="kart rekor"><span class="baslik">Kalesini gole kapattığı maç</span>
      <span class="deger">${sayiYaz(gy.length)} <small class="soluk" style="font-size:1rem">/ ${sayiYaz(oy.length)} (%${yuzde(gy.length, oy.length)})</small></span>
      <span class="detay">İç sahada ${gy.filter(m => m.saha === "E").length}, deplasmanda ${gy.filter(m => m.saha === "D").length}</span></div>
    <div class="kart rekor"><span class="baslik">En çok gol yemediği sezonlar</span>
      ${enSezon.map(x => `<span class="detay"><a class="bag" href="#/${K}sezon/${x.sezon}">${x.sezon}</a>: <b>${x.GY}</b> / ${x.O} maç</span>`).join("") || `<span class="soluk">—</span>`}</div>`;
  return `
  <h2>Kalesini gole kapattığı maçlar</h2>
  <div class="izgara iki ust-hiza">${gyKart}${seriKart(sr.find(s => s.k === "golyemeden"))}</div>
  <h2 class="bolum">En farklı sonuçlar</h2>
  <div class="izgara iki ust-hiza">${rekorKart("En farklı galibiyet", gal)}${rekorKart("En farklı mağlubiyet", mag)}${rekorKart("En gollü maç", gol)}
  ${rekorKart("İç sahada en farklı galibiyet", evG)}${rekorKart("Deplasmanda en farklı galibiyet", depG)}</div>
  <h2 class="bolum">Seriler <small class="soluk" style="font-weight:400;font-size:14px">— seçili maçlar art arda, sezonlar arası; ayrıntı için karta tıkla</small></h2>
  <div class="izgara iki ust-hiza">${sr.map(seriKart).join("")}</div>
  <p class="soluk" style="font-size:13px;margin-top:16px">Seriler seçili filtredeki maçların tarih sırasıyla hesaplanır; kulüp seçili yarışmada bir sezon ya da daha uzun süre yoksa seri kesilir. Penaltıyla biten kupa maçları beraberlik sayılır. Hükmen sonuçlar${hukmenSay ? ` (${hukmenSay} maç)` : ""} rekorlara, serilere ve gol sayımlarına girmez. "İç saha" seçilirse ev sahibi yenilmezlik serisi gibi kayıtlar çıkar.</p>
  <div id="oyuncuRekor"></div>`;
}

function rakipTablosu(hedef, ms, id) {
  const r = new Map();
  for (const m of ms) {
    if (m.s === "N") continue;
    const k = m.rakipId ?? "ad:" + m.rakip;
    const x = r.get(k) || { id: m.rakipId, ad: m.rakipId != null ? kulupAd(m.rakipId) : m.rakip, O: 0, G: 0, B: 0, M: 0, AG: 0, YG: 0, son: "" };
    x.O++; x[m.s]++; x.AG += m.a; x.YG += m.y; x.son = m.tarih > x.son ? m.tarih : x.son; r.set(k, x);
  }
  let liste = [...r.values()], sira = "O", ters = true, ara = "";
  const ciz = () => {
    const g = liste.filter(x => !ara || norm(x.ad).includes(norm(ara)))
      .sort((a, b) => { const va = sira === "Av" ? a.AG - a.YG : sira === "ad" ? a.ad : a[sira], vb = sira === "Av" ? b.AG - b.YG : sira === "ad" ? b.ad : b[sira]; return (typeof va === "string" ? va.localeCompare(vb, "tr") : va - vb) * (ters ? -1 : 1); });
    hedef.innerHTML = `<div class="filtre"><input type="search" id="rAra" placeholder="Rakip ara…" value="${esc(ara)}"><span class="soluk">${liste.length} farklı rakip</span></div>
    <div class="tablo-kap"><table class="tablo"><thead><tr>
      ${[["ad", "Rakip"], ["O", "O"], ["G", "G"], ["B", "B"], ["M", "M"], ["AG", "AG"], ["YG", "YG"], ["Av", "Av"]].map(([k, a]) => `<th class="sirala ${k === "ad" ? "" : "s"}" data-k="${k}">${a}${sira === k ? (ters ? " ↓" : " ↑") : ""}</th>`).join("")}<th class="gizle-mobil">Son maç</th><th></th></tr></thead>
    <tbody>${g.slice(0, 400).map(x => `<tr><td class="ad">${x.id != null ? kulupBag(x.id) : esc(x.ad)}</td><td class="s">${x.O}</td><td class="s">${x.G}</td><td class="s">${x.B}</td><td class="s">${x.M}</td>
      <td class="s">${x.AG}</td><td class="s">${x.YG}</td><td class="s">${x.AG - x.YG > 0 ? "+" : ""}${x.AG - x.YG}</td><td class="gizle-mobil">${tarihYaz(x.son)}</td>
      <td>${x.id != null ? `<a class="bag" href="#/${K}h2h/${id}/${x.id}">maçlar →</a>` : ""}</td></tr>`).join("")}</tbody></table></div>`;
    hedef.querySelectorAll("th.sirala").forEach(th => th.addEventListener("click", () => { if (sira === th.dataset.k) ters = !ters; else { sira = th.dataset.k; ters = sira !== "ad"; } ciz(); }));
    const i = $("#rAra"); i.addEventListener("input", e => { ara = e.target.value; clearTimeout(i._t); i._t = setTimeout(() => { ciz(); const n = $("#rAra"); n.focus(); n.setSelectionRange(n.value.length, n.value.length); }, 200); });
  };
  ciz();
}

function sezonSezonHtml(ms) {
  const s = new Map();
  for (const m of ms) {
    const x = s.get(m.sezon) || { sezon: m.sezon, ligler: new Map(), kupa: [], ozel: [], avrupa: [] };
    if (m.yar === "L" || m.yar === "T") {
      const key = `${m.lig}|${m.tur}|${m.yar}`;
      const l = x.ligler.get(key) || { lig: m.lig, grup: m.yar === "T" ? m.tur || "Terfi" : m.tur, kademe: m.kademe, yar: m.yar, ms: [] };
      if (!m.po) l.ms.push(m); x.ligler.set(key, l);
    } else if (m.yar === "K") x.kupa.push(m); else if (m.yar === "O") x.ozel.push(m); else if (m.yar === "A") x.avrupa.push(m);
    s.set(m.sezon, x);
  }
  const satirlar = [...s.values()].sort((a, b) => b.sezon.localeCompare(a.sezon)).map(x => {
    const ligler = [...x.ligler.values()].filter(l => l.ms.length).map(l => {
      const t = toplam(l.ms), p = puan(x.sezon);
      return `<div>${esc(l.lig)}${l.grup ? ` <span class="soluk">· ${esc(l.grup)}</span>` : ""}: <b>${t.O}</b> maç ${t.G}-${t.B}-${t.M}, ${t.AG}:${t.YG}${l.yar === "L" ? `, <b>${t.G * p + t.B}</b> puan` : ""}</div>`;
    }).join("");
    const kupaSon = x.kupa.filter(m => m.s !== "N").at(-1);
    return `<tr><td><a class="bag" href="#/${K}sezon/${x.sezon}">${x.sezon}</a></td><td class="ad">${ligler || `<span class="soluk">—</span>`}</td>
      <td class="ad gizle-mobil">${kupaSon ? `${esc(kupaSon.tur || "")} <span class="soluk">(${x.kupa.length} maç)</span>` : ""}${x.ozel.map(m => `<div>${esc(m.lig)} <span class="soluk">${m.a}-${m.y}${m.s === "G" ? ", kazandı" : m.s === "M" ? ", kaybetti" : ""}</span></div>`).join("")}</td>
      <td class="ad gizle-mobil">${x.avrupa.length ? `${esc(x.avrupa[0].lig)} <span class="soluk">(${x.avrupa.length} maç)</span>` : ""}</td></tr>`;
  }).join("");
  return `<p class="soluk" style="font-size:13px">Puanlar maç sonuçlarından hesaplanmıştır (1987-88 öncesi galibiyet 2 puan). Puan silme cezaları dahil değildir. Sezona tıklayınca o sezonun puan tablosu açılır.</p>
  <div class="tablo-kap"><table class="tablo"><thead><tr><th>Sezon</th><th>Lig</th><th class="gizle-mobil">Kupalar</th><th class="gizle-mobil">Avrupa</th></tr></thead><tbody>${satirlar}</tbody></table></div>`;
}
const puan = sezon => +sezon.slice(0, 4) >= 1987 ? 3 : 2;

// ---------------------------------------------------------------- iki kulüp
async function ikiliSayfa(a, b) {
  const ka = KULUP.get(a), kb = KULUP.get(b);
  if (!ka || !kb) { icerik.innerHTML = `<div class="bos">Kulüp bulunamadı.</div>`; return; }
  document.title = `${ka.ad} – ${kb.ad} · Türk Futbol Arşivi`;
  icerik.innerHTML = `<div class="yukleniyor">Yükleniyor…</div>`;
  const ms = (await kulupMaclari(a)).filter(m => m.rakipId === b);
  const d = { yar: "", saha: "", sezon: "", sonuc: "", rakip: "", sira: "yeni" };
  const ciz = () => {
    const f = ms.filter(m => (!d.yar || m.yar === d.yar) && (!d.saha || m.saha === d.saha));
    const t = toplam(f);
    icerik.innerHTML = `
    <div class="karsilasma">
      ${[a, b].map((id, i) => { const k = KULUP.get(id), tema = takimTema(k);
        return `${i ? `<span class="vs">vs</span>` : ""}<a class="taraf ${i ? "sag" : ""}" href="#/${K}kulup/${id}" style="--tr:${tema ? tema["--tv-acik"] : "var(--yazi)"}">
          <span class="buyuk-logo">${k.logo ? `<img src="logo/${k.logo}.png" alt="">` : esc(k.ad.slice(0, 2).toLocaleUpperCase("tr"))}</span>
          <span class="ad">${esc(k.ad)}</span></a>`; }).join("")}
    </div>
    <p class="soluk">${ms.length ? `${tarihYaz(ms[0].tarih)} ile ${tarihYaz(ms.at(-1).tarih)} arasında ${ms.length} resmi maç` : "Aralarında kayıtlı maç yok."}</p>
    <div class="filtre"><div class="cipler">${[["", "Tümü"], ["L", "Lig"], ["K", "Kupa"], ["O", "Diğer kupalar"], ["A", "Avrupa"]].filter(([v]) => !v || ms.some(m => m.yar === v)).map(([v, ad]) => `<button class="cip ${d.yar === v ? "aktif" : ""}" data-y="${v}">${ad}</button>`).join("")}</div>
    <div class="cipler">${[["", "İç + dış"], ["E", `${esc(ka.ad)} evinde`], ["D", `${esc(kb.ad)} evinde`]].map(([v, ad]) => `<button class="cip ${d.saha === v ? "aktif" : ""}" data-s="${v}">${ad}</button>`).join("")}</div></div>
    <div class="kart"><div class="ozet-sat">
      <div><b>${t.O}</b><span>Maç</span></div><div><b style="color:var(--g)">${t.G}</b><span>${esc(ka.ad)} kazandı</span></div>
      <div><b>${t.B}</b><span>Berabere</span></div><div><b style="color:var(--m)">${t.M}</b><span>${esc(kb.ad)} kazandı</span></div>
      <div><b>${t.AG}–${t.YG}</b><span>Gol</span></div></div>
      <div class="cubuk"><i class="g" style="width:${yuzde(t.G, t.O)}%"></i><i class="b" style="width:${yuzde(t.B, t.O)}%"></i><i class="m" style="width:${yuzde(t.M, t.O)}%"></i></div></div>
    <div class="bolum tablo-kap"><table class="tablo"><thead><tr><th class="o">S</th><th>Tarih</th><th>Sezon</th><th class="gizle-mobil">Yarışma</th><th>Ev sahibi</th><th class="s">Skor</th><th>Deplasman</th></tr></thead>
    <tbody>${[...f].reverse().map(m => {
      const ev = m.saha === "E" ? logoImg(m.kulup) + esc(m.takim) : logoImg(m.rakipId) + esc(m.rakip), dep = m.saha === "E" ? logoImg(m.rakipId) + esc(m.rakip) : logoImg(m.kulup) + esc(m.takim);
      const sk = m.saha === "E" ? skorYaz(m.a, m.y, m.pa, m.py, m.durum) : skorYaz(m.y, m.a, m.py, m.pa, m.durum);
      return `<tr><td class="o"><span class="son ${m.s}">${m.s === "N" ? "–" : m.s}</span></td><td>${tarihYaz(m.tarih)}</td><td><a class="bag" href="#/${K}sezon/${m.sezon}">${m.sezon}</a></td>
        <td class="gizle-mobil">${esc(m.lig || "")}${m.tur ? ` <span class="soluk">· ${esc(m.tur)}</span>` : ""}</td><td class="ad">${ev}</td><td class="s skor">${skorBag(m.id, sk)}</td><td class="ad">${dep}</td></tr>`;
    }).join("")}</tbody></table></div>`;
    icerik.querySelectorAll("[data-y]").forEach(x => x.addEventListener("click", () => { d.yar = x.dataset.y; ciz(); }));
    icerik.querySelectorAll("[data-s]").forEach(x => x.addEventListener("click", () => { d.saha = x.dataset.s; ciz(); }));
  };
  ciz();
}

const karsilastirSecim = { a: null, b: null };
function karsilastirSayfa() {
  document.title = "Karşılaştır · Türk Futbol Arşivi";
  icerik.innerHTML = `<h1>İki kulübü karşılaştır</h1><p class="soluk">İki kulüp seç; aralarındaki bütün resmi maçları gör.</p>
  <div class="izgara k2" style="max-width:820px">
    <div class="kart"><h3>1. kulüp</h3><div style="position:relative"><input id="kA" data-yalniz-kulup="1" type="search" placeholder="Kulüp ara…" autocomplete="off"><div id="oA" class="oneri" hidden></div></div><p id="sA" class="soluk"></p></div>
    <div class="kart"><h3>2. kulüp</h3><div style="position:relative"><input id="kB" data-yalniz-kulup="1" type="search" placeholder="Kulüp ara…" autocomplete="off"><div id="oB" class="oneri" hidden></div></div><p id="sB" class="soluk"></p></div>
  </div>`;
  const yaz = () => {
    $("#sA").innerHTML = karsilastirSecim.a ? `Seçildi: <b>${esc(kulupAd(karsilastirSecim.a))}</b>` : "";
    $("#sB").innerHTML = karsilastirSecim.b ? `Seçildi: <b>${esc(kulupAd(karsilastirSecim.b))}</b>` : "";
    if (karsilastirSecim.a && karsilastirSecim.b) location.hash = `#/h2h/${karsilastirSecim.a}/${karsilastirSecim.b}`;
  };
  oneriKutusu($("#kA"), $("#oA"), k => { karsilastirSecim.a = k.id; $("#kA").value = k.ad; yaz(); if (!karsilastirSecim.b) $("#kB").focus(); });
  oneriKutusu($("#kB"), $("#oB"), k => { karsilastirSecim.b = k.id; $("#kB").value = k.ad; yaz(); });
  if (karsilastirSecim.a) { $("#kA").value = kulupAd(karsilastirSecim.a); karsilastirSecim.b = null; $("#kB").focus(); } else $("#kA").focus();
  yaz();
  avrupaUlkeler();
}

// ---------------------------------------------------------------- maç sayfası
let DETAYLI = null;
// UEFA ayrıntıları: OZET.detayli (maç no listesi); TFF ayrıntıları: OZET.detayli_aralik ([başlangıç, uzunluk] aralıkları)
const detayVar = id => {
  if ((DETAYLI ||= new Set(OZET.detayli || [])).has(id)) return true;
  const a = OZET.detayli_aralik || []; let lo = 0, hi = a.length - 1;
  while (lo <= hi) { const o = (lo + hi) >> 1; if (id < a[o][0]) hi = o - 1; else if (id >= a[o][0] + a[o][1]) lo = o + 1; else return true; }
  return false;
};
// TFF maç ayrıntısı: futbol.db maç no -> TFF maç no (data/tff/dizin.json), sonra data/tff/m/<no/250>.json
let TFF_DIZIN = null;
async function tffMacAl(id) {
  if (!TFF_DIZIN) {
    const d = await al(`${V}tff/dizin.json?s=${OZET.surum || ""}`), m = new Map();
    let f = 0, t = 0;
    d.f.forEach((x, i) => { f += x; t += d.t[i]; m.set(f, t); });
    TFF_DIZIN = m;
  }
  const t = TFF_DIZIN.get(id);
  if (t == null) return null;
  const b = await al(`${V}tff/m/${Math.floor(t / 250)}.json?s=${OZET.surum || ""}`), r = b.mac[t];
  if (!r) return null;
  const ad = k => b.ad[k] || "";
  const TUR = { Y: "YELLOW_CARD", R: "RED_CARD", YR: "YELLOW_CARD_SECOND", S: "SUBSTITUTION", G: "GOAL" };
  const [tarih, saat, sezon, lig, tur, ev, dep, skor] = r.m;
  const ilkGorev = r.h.find(h => h[1] === "Hakem");
  return {
    id, tarih, saat, sezon, lig, tur, ev, dep, skor, stad: r.s, kaynak: r.q || "TFF", olayKaynak: r.oq, tff: t, uyum: r.u, oyuncuOnek: "k",
    hakem: ilkGorev ? ilkGorev[0] : null, hakemler: r.h,
    kadro: r.k.map(l => l.map(([forma, k, ilk11]) => [forma, ad(k), ilk11, 0, k])),
    teknik: r.t.map(l => l.map(([k, a]) => BOLUM === "erkek" ? [a, "a" + k] : a)),   // kadın bölümünde teknik direktör sayfası yok
    olay: r.o.map(([taraf, tur, dk, ek, k1, k2, tip]) => [taraf, TUR[tur], dk, ek || null, ad(k1), k2 ? ad(k2) : null,
      tip === "P" ? "PENALTY" : tip === "K" ? "OWN" : tip === "H" ? "HEADER" : null, k1, k2]),
  };
}
// ayrıntısı olan maçın skoru maç sayfasına bağlanır (ayrıntılı maçlar arttıkça kendiliğinden yayılır)
const skorBag = (id, html) => id != null && detayVar(id) ? `<a class="skor bagli" href="#/${K}mac/${id}" title="Maç ayrıntısı">${html}</a>` : html;
const OLAY = {
  GOAL: ["⚽", "Gol"], PENALTY: ["✖", "Kaçan penaltı"], YELLOW_CARD: ["🟨", "Sarı kart"], YELLOW_CARD_SECOND: ["🟨🟥", "İkinci sarı"],
  RED_YELLOW_CARD: ["🟨🟥", "İkinci sarıdan kırmızı"], RED_CARD: ["🟥", "Kırmızı kart"], SUBSTITUTION: ["⇄", "Oyuncu değişikliği"],
};
// Maçkolik maç olayları (Süper Lig 1959-1991, 1. Lig 1990-91): data/mk/dizin.json (futbol.db no -> Maçkolik no), data/mk/m/<no[:2]>.json
let MK_DIZIN = null;
// Maçkolik arşiv kadrolarıyla eklenen Süper Lig dönemi (ozet.json mk_kadro: en eski sezon)
const MK_NOT = () => BOLUM === "erkek" && OZET?.mk_kadro ? `; Süper Lig ${OZET.mk_kadro.slice(0, 4)}-${OZET.mk_kadro.slice(7, 9)} ile 1989-90 arası Maçkolik arşivinin kadrolarından` : "";
async function mkMacAl(id) {
  if (BOLUM !== "erkek") return null;
  MK_DIZIN ||= await al(`data/mk/dizin.json?s=${OZET.surum || ""}`).catch(() => ({}));
  const no = MK_DIZIN[id];
  if (!no) return null;
  const r = (await al(`data/mk/m/${no.slice(0, 2)}.json?s=${OZET.surum || ""}`).catch(() => ({})))[no];
  if (!r) return null;
  const [tarih, saat, sezon, lig, tur, ev, dep, skor] = r.m;
  return { id, tarih, saat, sezon, lig, tur, ev, dep, skor, kaynak: "Maçkolik", kadro: [[], []], teknik: [[], []],
    olay: r.o.map(([taraf, tur, dk, ek, a1, a2, ay]) => [taraf, tur, dk, ek, a1, a2, ay, null, null]) };
}
async function macSayfa(id) {
  icerik.innerHTML = `<div class="yukleniyor">Maç yükleniyor…</div>`;
  let d = (DETAYLI ||= new Set(OZET.detayli || [])).has(id) ? await al(`${V}mac/${id}.json?s=${OZET.surum || ""}`) : await tffMacAl(id);
  if (!d || (d.kaynak === "TFF" && !d.olay.some(o => o[1] === "GOAL") && (d.skor[0] || d.skor[1]))) {
    const mk = await mkMacAl(id);   // 1990-91: TFF'nin kadrosu + Maçkolik'in golleri, kartları, değişiklikleri
    if (mk && d) { d.olay = mk.olay; d.uyum = null; d.olayKaynak = "Maçkolik"; }
    else if (mk) d = mk;
  }
  if (!d) { icerik.innerHTML = `<div class="bos">Bu maçın ayrıntısı yok.</div>`; return; }
  macCiz(d);
}
function macCiz(d) {
  const onek = d.oyuncuOnek || "u";
  const [eg, dg, ep, dp, durum] = d.skor;
  document.title = `${d.ev[1]} ${eg}-${dg} ${d.dep[1]} · Türk Futbol Arşivi`;
  const href = d.kulupHref || (kid => kid != null && KULUP.has(kid) ? `#/${K}kulup/${kid}` : null);   // kadın bölümü kendi kulüp bağlantısını verir
  const ad = ([kid, a]) => href(kid) ? `<a href="${href(kid)}">${esc(a)}</a>` : esc(a);
  const buyuk = ([kid, a], i) => { const k = d.kulupBilgi ? d.kulupBilgi(kid) : KULUP.get(kid), tema = takimTema(k);
    return `<a class="taraf ${i ? "sag" : ""}" ${href(kid) ? `href="${href(kid)}"` : ""} style="--tr:${tema ? tema["--tv-acik"] : "var(--yazi)"}">
      <span class="buyuk-logo">${k?.logo ? `<img src="logo/${k.logo}.png" alt="">` : d.bayrak?.[i] ? d.bayrak[i] : esc(a.slice(0, 2).toLocaleUpperCase("tr"))}</span><span class="ad">${esc(a)}</span></a>`; };
  const dakika = o => o[2] == null ? "" : `${o[2]}${o[3] ? "+" + o[3] : ""}'`;
  // oyuncuya göre olay simgeleri (kadroda göstermek için)
  const simge = new Map(), ekle = (no, s) => no && simge.set(no, (simge.get(no) || "") + s);
  for (const o of d.olay) {
    const [taraf, tur, , , a1, a2, ay, n1, n2] = o, no = n1 || (a1 ? "ad:" + a1 : null), no2 = n2 || (a2 ? "ad:" + a2 : null);   // numarasız oyuncu: ada göre
    if (tur === "GOAL") ekle(no, `<span title="${ay === "OWN" ? "Kendi kalesine" : "Gol"} ${dakika(o)}">${ay === "OWN" ? "⚽<small>(k.k.)</small>" : "⚽"}</span>`);
    else if (tur === "SUBSTITUTION") { ekle(no, `<span class="cik" title="Çıktı ${dakika(o)}">↓${dakika(o)}</span>`); ekle(no2, `<span class="gir" title="Girdi ${dakika(o)}">↑${dakika(o)}</span>`); }
    else if (OLAY[tur] && tur !== "PENALTY") ekle(no, `<span title="${OLAY[tur][1]} ${dakika(o)}">${OLAY[tur][0]}</span>`);
  }
  const oy = (no, ad) => no ? `<a class="oyuncu-bag" href="#/${K}oyuncu/${onek}${no}">${esc(ad || "")}</a>` : esc(ad || "");
  const kadroHtml = (l, teknik) => `
    <div class="kadro-bolum">İlk 11</div>${l.filter(p => p[2]).map(p => `<div class="oyuncu"><span class="forma">${esc(p[0])}</span><span class="oad">${oy(p[4], p[1])}${p[3] ? ` <small class="soluk">(K)</small>` : ""}</span><span class="osimge">${simge.get(p[4] || "ad:" + p[1]) || ""}</span></div>`).join("") || `<div class="soluk">—</div>`}
    ${l.some(p => !p[2]) ? `<div class="kadro-bolum">Yedekler</div>${l.filter(p => !p[2]).map(p => `<div class="oyuncu yedek"><span class="forma">${esc(p[0])}</span><span class="oad">${oy(p[4], p[1])}</span><span class="osimge">${simge.get(p[4] || "ad:" + p[1]) || ""}</span></div>`).join("")}` : ""}
    ${teknik.length ? `<div class="kadro-bolum">Teknik direktör</div><div class="oyuncu"><span class="forma"></span><span class="oad">${teknik.map(t => Array.isArray(t) ? `<a class="oyuncu-bag" href="#/${K}oyuncu/${String(t[1]).startsWith("a") ? t[1] : "t" + t[1]}">${esc(t[0])}</a>` : esc(t)).join(", ")}</span></div>` : ""}`;
  const akis = d.olay.filter(o => o[1] !== "SUBSTITUTION" || true).map(o => {
    const [taraf, tur, , , a1, a2, ay, n1, n2] = o, [s, adi] = OLAY[tur] || ["•", tur];
    const metin = tur === "SUBSTITUTION" ? `<span class="gir">↑ ${oy(n2, a2)}</span> <span class="cik">↓ ${oy(n1, a1)}</span>`
      : `<b>${oy(n1, a1)}</b>${tur === "GOAL" && ay === "PENALTY" ? ` <small class="soluk">(penaltı)</small>` : ""}${tur === "GOAL" && ay === "HEADER" ? ` <small class="soluk">(kafa)</small>` : ""}${ay === "OWN" ? ` <small class="soluk">(kendi kalesine)</small>` : ""}${tur === "PENALTY" ? ` <small class="soluk">penaltı kaçırdı</small>` : ""}`;
    return `<div class="akis-satir ${taraf === 1 ? "ev" : "dep"} ${tur === "GOAL" ? "gol" : ""}"><span class="akis-ic">${taraf === 1 ? `${metin} <span class="s" title="${adi}">${s}</span>` : `<span class="s" title="${adi}">${s}</span> ${metin}`}</span><span class="akis-dk">${dakika(o)}</span></div>`;
  }).join("");
  icerik.innerHTML = `
  <div class="mac-bas">
    <div class="mac-ust soluk">${d.ustHtml || `<a class="bag" href="#/${K}sezon/${d.sezon}">${esc(d.sezon)}</a> · ${esc(d.lig)}${d.tur ? ` · ${esc(d.tur)}` : ""}`}</div>
    <div class="karsilasma mac">${buyuk(d.ev, 0)}<div class="mac-skor"><b>${eg ?? "–"} - ${dg ?? "–"}</b>${ep != null ? `<small>pen ${ep}-${dp}</small>` : durum === "UZ" ? `<small>uzatmada</small>` : ""}</div>${buyuk(d.dep, 1)}</div>
    <div class="mac-bilgi">
      <span>📅 ${tarihYaz(d.tarih)}${d.saat ? ` · ${esc(d.saat)}` : ""}</span>
      ${d.stad ? `<span>🏟 ${esc(d.stad)}${d.sehir ? `, ${esc(d.sehir)}` : ""}</span>` : ""}
      ${d.seyirci ? `<span>👥 ${sayiYaz(d.seyirci)} seyirci</span>` : ""}
      ${d.hakem ? `<span>🧑‍⚖️ ${esc(d.hakem)}${d.hakem_ulke && ULKE[d.hakem_ulke] ? ` <small class="soluk">(${ULKE[d.hakem_ulke][0]})</small>` : ""}</span>` : ""}
    </div>
    ${d.hakemler && d.hakemler.length > 1 ? `<div class="mac-hakemler soluk">${d.hakemler.filter(h => h[1] !== "Hakem").map(h => `${esc(h[1])}: ${esc(h[0])}`).join(" · ")}</div>` : ""}
  </div>
  ${d.uyum === "uyumsuz" ? `<p class="uyari bolum">TFF'nin bu maç için verdiği gol listesi skorla uyuşmuyor; kaynakta bir yazım hatası var. Goller TFF'de yazıldığı gibi gösteriliyor.</p>` : ""}
  ${d.uyum === "yok" ? `<p class="soluk not bolum">TFF bu maçın gollerini kaydetmemiş.</p>` : ""}
  ${istatHtml(d)}
  ${d.olay.length ? `<div class="kart bolum"><h3>Maçın akışı</h3><div class="akis">${akis}</div></div>` : ""}
  ${d.kadro[0].length || d.kadro[1].length ? `<div class="izgara iki bolum ust-hiza">
    <div class="kart"><h3>${ad(d.ev)}</h3>${kadroHtml(d.kadro[0], d.teknik[0])}</div>
    <div class="kart"><h3>${ad(d.dep)}</h3>${kadroHtml(d.kadro[1], d.teknik[1])}</div>
  </div>` : ""}
  <p class="soluk not bolum">${d.olayKaynak ? `Kadro: <a class="bag" href="https://www.tff.org/Default.aspx?pageID=29&macId=${d.tff}" target="_blank" rel="noopener">TFF maç sayfası</a>; goller, kartlar ve değişiklikler: ${esc(d.olayKaynak)}`
    : d.kaynak === "Maçkolik" ? (d.kadro[0].length ? "Kadro, goller, kartlar ve oyuncu değişiklikleri: Maçkolik arşivi" : "Goller, kartlar ve oyuncu değişiklikleri: Maçkolik. Bu dönemin kadroları henüz yok")
    : `Kadro ve olaylar: ${d.tff ? `<a class="bag" href="${d.kaynakUrl || `https://www.tff.org/Default.aspx?pageID=29&macId=${d.tff}`}" target="_blank" rel="noopener">TFF maç sayfası</a>` : esc(d.kaynak)}`}. Oyuncu adları kaynakta yazıldığı gibidir.</p>`;
}

const ISTAT = [   // [anahtar, ad, yüzde mi]
  ["ball_possession", "Topla oynama", true], ["attempts", "Şut"], ["attempts_on_target", "İsabetli şut"], ["attempts_off_target", "İsabetsiz şut"],
  ["attempts_blocked", "Engellenen şut"], ["big_chance", "Net gol fırsatı"], ["woodwork", "Direk"], ["attempts_on_post", "Direk"], ["corners", "Korner"],
  ["offsides", "Ofsayt"], ["saves", "Kurtarış"], ["passes_attempted", "Pas"], ["passes_completed", "İsabetli pas"], ["passes_accuracy", "Pas isabeti", true],
  ["cross_completed", "İsabetli orta"], ["tackles", "Top kapma"], ["recovered_ball", "Top kazanma"], ["fouls_committed", "Faul"],
  ["yellow_cards", "Sarı kart"], ["red_cards", "Kırmızı kart"], ["distance_covered", "Koşu mesafesi (km)"],
];
function istatHtml(d) {
  if (!d.istat) return "";
  const [a, b] = d.istat, gor = new Set();
  const satir = ISTAT.filter(([k, ad]) => (a[k] != null || b[k] != null) && !gor.has(ad) && gor.add(ad)).map(([k, ad, yuzdeMi]) => {
    const x = parseFloat(a[k] ?? 0) || 0, y = parseFloat(b[k] ?? 0) || 0, t = x + y || 1;
    const fmt = v => yuzdeMi ? `%${Math.round(v)}` : Number.isInteger(v) ? v : v.toFixed(1);
    if (!x && !y) return "";
    return `<div class="istat"><span class="isd ${x > y ? "fazla" : ""}">${fmt(x)}</span><span class="isad">${ad}</span><span class="isd ${y > x ? "fazla" : ""}">${fmt(y)}</span>
      <div class="iscubuklar"><div class="iscubuk"><i style="width:${100 * x / t}%"></i></div><div class="iscubuk sag"><i style="width:${100 * y / t}%"></i></div></div></div>`;
  });
  if (satir.filter(Boolean).length < 2) return "";
  const [ta, tb] = [takimTema(KULUP.get(d.ev[0])), takimTema(KULUP.get(d.dep[0]))];
  return `<div class="kart bolum istatlar" style="--ia:${ta ? ta["--tv-acik"] : "var(--yazi2)"};--ib:${tb ? tb["--tv-acik"] : "var(--soluk)"}"><h3>İstatistikler</h3>${satir.join("")}</div>`;
}

// kulüp özeti: Avrupa'da en çok gol atan ve en çok maça çıkan oyuncular (UEFA)
async function avrupaOyunculari(hedef, kid) {
  const kap = document.createElement("section");
  kap.className = "bolum";
  hedef.appendChild(kap);
  const d = await al(`data/oyuncu_uefa.json?s=${OZET.surum || ""}`);
  const t = new Map();
  for (const k of d.katilim) if (k[2] === kid) {
    const x = t.get(k[0]) || { no: k[0], mac: 0, ilk: 0, gol: 0, asist: 0, dk: 0 };
    x.mac++; x.ilk += k[3]; x.gol += k[4]; x.asist += k[10] || 0; x.dk += k[9] || 0; t.set(k[0], x);
  }
  if (!t.size) { kap.remove(); return; }
  const l = [...t.values()];
  const satir = (x, deger) => `<li><span class="kim"><a class="bag" href="#/${K}oyuncu/u${x.no}">${esc(d.oyuncu[x.no][0])}</a>
    <small class="soluk">${x.mac} maç${x.gol ? ` · ${x.gol} gol` : ""}${x.asist ? ` · ${x.asist} asist` : ""}</small></span><b class="n">${deger}</b></li>`;
  const sira = (l, f) => { let r = 0, onc; return l.map((x, i) => { const v = f(x); if (v !== onc) { r = i + 1; onc = v; } return [r, x]; }); };
  const liste = (l, f, g) => `<ol class="sirali">${sira(l, f).map(([r, x]) => satir(x, g(x)).replace("<li>", `<li><span class="sira">${r}</span>`)).join("")}</ol>`;
  const gol = l.filter(x => x.gol).sort((a, b) => b.gol - a.gol || b.asist - a.asist || a.mac - b.mac).slice(0, 15);
  const asist = l.filter(x => x.asist).sort((a, b) => b.asist - a.asist || b.gol - a.gol).slice(0, 10);
  const mac = [...l].sort((a, b) => b.mac - a.mac || b.gol - a.gol).slice(0, 15);
  kap.innerHTML = `<h2>Avrupa'da oyuncular</h2>
    <div class="izgara k3 ust-hiza">
      <div class="kart rekor-kart"><h3>En çok gol atanlar</h3><p class="soluk aciklama">Kendi kalesine goller hariç</p>${liste(gol, x => x.gol, x => x.gol) || `<p class="soluk">—</p>`}</div>
      ${asist.length ? `<div class="kart rekor-kart"><h3>En çok asist yapanlar</h3><p class="soluk aciklama">Yalnız UEFA'nın asist kaydettiği maçlar; eski maçlarda asist bilgisi yok</p>${liste(asist, x => x.asist, x => x.asist)}</div>` : ""}
      <div class="kart rekor-kart"><h3>En çok maça çıkanlar</h3><p class="soluk aciklama">İlk 11 ya da oyuna sonradan girerek</p>${liste(mac, x => x.mac, x => x.mac)}</div>
    </div>
    <p class="soluk not">Kaynak: UEFA. Fuar Şehirleri Kupası ve Intertoto maçları dahil değil.</p>`;
}

// ---------------------------------------------------------------- TFF oyuncu sayfası (lig ve kupa: TFF maç sayfalarından)
const KADIN_KAYNAK = "TFF maç sayfaları (kadın ligleri; kadro ve goller 2008-09'dan bugüne)";
// doğum yeri: "GARÇA-SAO PAULO-BREZİLYA" -> "Garça-Sao Paulo-Brezilya" (tire ve boşluktan sonra büyük harf)
// yabancı (uyruğu TC değil): Türkçe ı kuralı yok ("CAIRU/BA" -> "Cairu/Ba")
const okunurYer = (s, yabanci) => String(s || "").split(/([ \-\/])/).map(w => w.length > 1 && /\p{L}/u.test(w[0]) ? (yabanci ? w[0].replace("İ", "I") : w[0]) + (yabanci ? w.slice(1).replace(/[Iİ]/g, "i").toLowerCase() : w.slice(1).replace(/I/g, "ı").replace(/İ/g, "i").toLocaleLowerCase("tr")) : w).join("");
const tffYarAd = (yar, kademe) => yar === "L" ? (KADEME_AD[kademe] || "Lig") : YAR_AD[yar] || yar;
// kadın oyuncunun Avrupa maçları: özet, sezon-kulüp-kupa tablosu ve maç listesi
function kadinAvrupaHtml(l, M) {
  const ms = l.map(([mac, kulup, ilk11, gol, sari, kirmizi, giris, cikis]) => {
    const [tarih, sezon, lig, tur, ev, dep, evAd, depAd, eg, dg] = M[mac] || [];
    const evde = ev === kulup;
    return { mac, kulup, ilk11, gol, sari, kirmizi, giris, cikis, tarih, sezon, lig, tur, ev, dep, evAd, depAd, eg, dg,
      s: sonuc(evde ? eg : dg, evde ? dg : eg) };
  }).sort((a, b) => (b.tarih || "").localeCompare(a.tarih || ""));
  const top = ms.reduce((t, m) => (t.mac++, t.ilk += m.ilk11, t.gol += m.gol, t.sari += m.sari, t.kirmizi += m.kirmizi, t), { mac: 0, ilk: 0, gol: 0, sari: 0, kirmizi: 0 });
  const gr = [...ms.reduce((g, m) => { const k = `${m.sezon}|${m.kulup}|${m.lig}`; return g.set(k, [...(g.get(k) || []), m]); }, new Map())];
  return `<div class="kart bolum"><div class="ozet-sat">
    <div><b>${top.mac}</b><span>Avrupa maçı</span></div><div><b>${top.ilk}</b><span>İlk 11</span></div><div><b>${top.gol}</b><span>Gol</span></div>
    <div><b>${top.sari}</b><span>Sarı kart</span></div><div><b>${top.kirmizi}</b><span>Kırmızı kart</span></div></div></div>
  <div class="kart bolum tablo-kap"><table class="tablo"><thead><tr><th>Sezon</th><th class="ad">Kulüp</th><th class="ad">Kupa</th><th class="s">Maç</th><th class="s">İlk 11</th><th class="s">Gol</th><th class="s">Sarı</th><th class="s">Kırm.</th></tr></thead><tbody>
    ${gr.map(([k, l]) => `<tr><td>${esc(l[0].sezon)}</td><td class="ad">${kulupBag(l[0].kulup)}</td><td class="ad soluk">${esc(l[0].lig || "")}</td><td class="s">${l.length}</td>
      <td class="s">${l.reduce((s, m) => s + m.ilk11, 0)}</td><td class="s">${l.reduce((s, m) => s + m.gol, 0) || ""}</td><td class="s">${l.reduce((s, m) => s + m.sari, 0) || ""}</td><td class="s">${l.reduce((s, m) => s + m.kirmizi, 0) || ""}</td></tr>`).join("")}
  </tbody></table></div>
  <div class="kart bolum"><h3>Maçlar</h3>${ms.map(m => `<div class="akis-satir"><span class="akis-ic"><span class="son ${m.s}">${m.s === "N" ? "–" : m.s}</span> ${tarihYaz(m.tarih)} · ${esc(m.evAd)} ${skorBag(m.mac, `${m.eg ?? "–"} - ${m.dg ?? "–"}`)} ${esc(m.depAd)}
    <small class="soluk">${esc(m.tur || "")} · ${m.ilk11 ? "İlk 11" : m.giris != null ? `${m.giris}'de girdi` : ""}${m.cikis != null ? ` · ${m.cikis}'de çıktı` : ""}${m.gol ? " · " + "⚽".repeat(m.gol) : ""}${m.sari ? " · 🟨" : ""}${m.kirmizi ? " · 🟥" : ""}</small></span></div>`).join("")}</div>
  <p class="soluk not">Kaynak: UEFA maç kadroları; oyuncu, aynı kulüpte oynadığı sezon, ad ve doğum tarihiyle TFF kaydına eşlendi.</p>`;
}
async function tffOyuncuSayfa(kisi) {
  icerik.innerHTML = `<div class="yukleniyor">Yükleniyor…</div>`;
  const d = await al(`${V}tff/o/${kisi % 500}.json?s=${OZET.surum || ""}`), p = d.oyuncu[kisi];
  if (p?.bk) { location.replace(`#/${K}oyuncu/k${p.bk}`); return; }   // TFF'nin aynı kişiye verdiği ikinci numara
  if (!p) {   // kulüp kaydı yok (ör. yalnız yurt dışında oynamış milli futbolcu): yalnız milli takım bölümü
    icerik.innerHTML = `<div id="milliOyuncu"></div>`;
    if (typeof milliOyuncu === "function" && await milliOyuncu($("#milliOyuncu"), kisi, true)) return;
    icerik.innerHTML = `<div class="bos">Oyuncu bulunamadı.</div>`; return;
  }
  document.title = `${p.ad} · Türk Futbol Arşivi`;
  const S = p.s.map(r => ({ sezon: r[0], kulup: r[1], yar: r[2], kademe: r[3], mac: r[4], ilk: r[5], gol: r[6], pen: r[7], kk: r[8], sari: r[9], kirmizi: r[10], dk: r[11], kmac: r[13] || 0, gy: r[14] || 0, yenen: r[15] || 0 }))
    .filter(r => r.mac);
  if (!S.length) {   // hiç oyuna girmemiş: yalnız yedek kulübesinde oturduğu maçlar
    const Y = [...p.s.reduce((m, r) => { const k = `${r[0]}|${r[1]}`; return m.set(k, (m.get(k) || 0) + (r[12] || 0)); }, new Map())].filter(x => x[1]).sort((a, b) => b[0].localeCompare(a[0]));
    icerik.innerHTML = `<div class="sayfa-bas"><div><h1>${esc(p.ad)}</h1></div></div>
      <p class="bolum">Kayıtlı maçlarda hiç oyuna girmedi; ${sayiYaz(Y.reduce((t, x) => t + x[1], 0))} maçta yedek kulübesindeydi.</p>
      <div class="tablo-kap bolum"><table class="tablo"><thead><tr><th>Sezon</th><th class="ad">Kulüp</th><th class="s">Yedek kulübesi</th></tr></thead><tbody>
      ${Y.map(([k, n]) => { const [sz, kid] = k.split("|"); return `<tr><td><a class="bag" href="#/${K}sezon/${sz}">${sz}</a></td><td class="ad">${kulupBag(+kid)}</td><td class="s">${n}</td></tr>`; }).join("")}</tbody></table></div>
      <p class="soluk not">Kaynak: <a class="bag" href="https://www.tff.org/Default.aspx?pageId=30&kisiId=${kisi}" target="_blank" rel="noopener">TFF</a> maç sayfaları.</p>`;
    return;
  }
  const topla = l => l.reduce((t, r) => { for (const k of ["mac", "ilk", "gol", "pen", "kk", "sari", "kirmizi", "dk", "kmac", "gy", "yenen"]) t[k] += r[k]; return t; },
    { mac: 0, ilk: 0, gol: 0, pen: 0, kk: 0, sari: 0, kirmizi: 0, dk: 0, kmac: 0, gy: 0, yenen: 0 });
  const T = topla(S);
  const kaleci = T.kmac > 0 && T.kmac >= T.ilk / 2;   // ilk 11'de çoğunlukla kaleci olarak başlamış
  const grupla = (l, f) => [...l.reduce((m, r) => { const k = f(r); return m.set(k, [...(m.get(k) || []), r]); }, new Map())];
  const ilk = S.reduce((a, r) => a < r.sezon ? a : r.sezon, "9999"), son = S.reduce((a, r) => a > r.sezon ? a : r.sezon, "");
  const hucre = t => `<td class="s">${t.mac}</td><td class="s">${t.ilk}</td><td class="s"><b>${t.gol || ""}</b></td><td class="s">${t.pen || ""}</td>
    <td class="s">${t.sari || ""}</td><td class="s">${t.kirmizi || ""}</td><td class="s">${t.dk ? sayiYaz(t.dk) : ""}</td>
    ${kaleci ? `<td class="s"><b>${t.gy || ""}</b></td><td class="s">${t.kmac ? `%${yuzde(t.gy, t.kmac)}` : ""}</td><td class="s">${t.kmac ? t.yenen : ""}</td><td class="s">${t.kmac ? (t.yenen / t.kmac).toFixed(2) : ""}</td>` : ""}`;
  const bas = ek => `<thead><tr>${ek.map((x, i) => `<th${i ? ' class="ad"' : ""}>${x}</th>`).join("")}<th class="s">Maç</th><th class="s" title="İlk 11'de başladığı maç">İlk 11</th>
    <th class="s">Gol</th><th class="s" title="Penaltıdan gol">Pen.</th><th class="s" title="Sarı kart">Sarı</th><th class="s" title="Kırmızı kart (ikinci sarıdan dahil)">Kırm.</th><th class="s" title="Yaklaşık oynanan dakika">Dakika</th>
    ${kaleci ? `<th class="s" title="Kaleci olarak ilk 11'de başladığı ve takımının gol yemediği maçlar">Gol yemeden</th><th class="s" title="Kaleci olarak başladığı maçların yüzde kaçında gol yemedi">%</th>
    <th class="s" title="Kaleci olarak başladığı maçlarda takımının yediği gol">Yenen gol</th><th class="s" title="Kaleci olarak başladığı maçlarda maç başına yenen gol">Maç başı</th>` : ""}</tr></thead>`;
  const yarlar = grupla(S, r => r.yar === "L" ? "L" + r.kademe : r.yar).sort((a, b) => a[0].localeCompare(b[0]));
  const kulupler = grupla(S, r => r.kulup).sort((a, b) => topla(b[1]).mac - topla(a[1]).mac);
  const sezonlar = grupla(S, r => `${r.sezon}|${r.kulup}`).sort((a, b) => b[0].localeCompare(a[0]));
  const B = BOLUM === "erkek" ? await oyuncuBagAl() : {};
  const uNo = Object.keys(B).find(u => B[u] === kisi) || null;
  // aynı kişinin teknik direktörlük kaydı (teknik.json oyuncu: anahtar -> TFF oyuncu no)
  const TJ = BOLUM === "erkek" ? await al(`data/teknik.json?s=${OZET.surum || ""}`).catch(() => ({})) : {};
  const tdKs = Object.keys(TJ.oyuncu || {}).filter(k => TJ.oyuncu[k] === kisi), tdK = tdKs[0] || null;   // aynı kişinin birden çok kaydı olabilir (UEFA + TFF)
  const tdArg = tdK ? (tdK.startsWith("a") ? tdK : tdK.slice(1)) : null;
  // kadın bölümü: Avrupa maçları (kadin/avrupa_oyuncu.json; UEFA kadrolarından TFF oyuncusuyla eşlenen)
  const AV = BOLUM === "kadin" ? await al(`${V}avrupa_oyuncu.json?s=${OZET.surum || ""}`).catch(() => null) : null;
  const kAv = AV?.oyuncu?.[kisi] || null;
  const [dg, dyer, uyruk] = p.d || [];
  const dogumYaz = dg ? (["01-01", "07-01"].includes(dg.slice(5)) ? dg.slice(0, 4) : tarihYaz(dg)) : null;
  icerik.innerHTML = `
  <div class="sayfa-bas"><div><h1>${esc(p.ad)}</h1>${p.tam ? `<p class="soluk">Tam adı: ${esc(p.tam)}</p>` : ""}
    <p class="soluk">${ilk.slice(0, 4)}–${son.slice(5) || son.slice(0, 4)} · ${kulupler.map(([k]) => kulupBag(k)).join(", ")}</p>
    ${dogumYaz || dyer || uyruk ? `<p class="soluk">${[dogumYaz ? `Doğum: ${dogumYaz}${dyer ? `, ${esc(okunurYer(dyer, uyruk && uyruk !== "TC"))}` : ""}` : dyer ? `Doğum yeri: ${esc(okunurYer(dyer, uyruk && uyruk !== "TC"))}` : "", uyruk && uyruk !== "TC" ? `Uyruk: ${esc(uyruk)}` : ""].filter(Boolean).join(" · ")}</p>` : ""}</div></div>
  ${uNo || tdK || kAv ? `<nav class="sekmeler bolum" id="oySekme"><a href="#" data-k="lk" class="aktif">Lig ve kupa <small class="soluk">${sayiYaz(T.mac)} maç</small></a>
    <a href="#" data-k="av">Avrupa <small class="soluk" id="avSay"></small></a><a href="#" data-k="td" hidden>Teknik direktör <small class="soluk" id="tdSay"></small></a></nav>` : ""}
  <div id="sk-lk">
  <div class="kart bolum"><div class="ozet-sat">
    <div><b>${sayiYaz(T.mac)}</b><span>Maç</span></div><div><b>${sayiYaz(T.ilk)}</b><span>İlk 11</span></div><div><b>${T.gol}</b><span>Gol</span></div>
    <div><b>${T.pen}</b><span>Penaltı golü</span></div><div><b>${T.sari}</b><span>Sarı kart</span></div><div><b>${T.kirmizi}</b><span>Kırmızı kart</span></div>
    ${kaleci ? `<div><b>${T.gy}</b><span>Gol yemeden</span></div><div><b>%${yuzde(T.gy, T.kmac)}</b><span>Gol yemeden oranı</span></div>
      <div><b>${(T.yenen / T.kmac).toFixed(2)}</b><span>Maç başı yenen gol</span></div>`
      : `<div><b>${T.mac ? (T.gol / T.mac).toFixed(2) : "–"}</b><span>Maç başı gol</span></div>`}</div></div>
  <div class="tablo-kap bolum"><table class="tablo">${bas(["Yarışma"])}<tbody>${yarlar.map(([k, l]) => `<tr><td class="ad">${esc(tffYarAd(l[0].yar, l[0].kademe))}</td>${hucre(topla(l))}</tr>`).join("")}
      ${yarlar.length > 1 ? `<tr class="toplam"><td class="ad"><b>Toplam</b></td>${hucre(T)}</tr>` : ""}</tbody></table></div>
  <div class="tablo-kap bolum"><table class="tablo">${bas(["Kulüp"])}<tbody>${kulupler.map(([k, l]) => `<tr><td class="ad">${kulupBag(k)}</td>${hucre(topla(l))}</tr>`).join("")}</tbody></table></div>
  <h2 class="bolum">Sezon sezon</h2>
  <div class="tablo-kap"><table class="tablo">${bas(["Sezon", "Kulüp", "Yarışma"])}<tbody>${sezonlar.map(([k, l]) => {
    const [sz, kid] = k.split("|");
    return `<tr><td><a class="bag" href="#/${K}sezon/${sz}">${sz}</a></td><td class="ad">${kulupBag(+kid)}</td><td class="ad soluk">${[...new Set(l.map(r => tffYarAd(r.yar, r.kademe)))].join(", ")}</td>${hucre(topla(l))}</tr>`;
  }).join("")}</tbody></table></div>
  <p class="soluk not">Kaynak: <a class="bag" href="https://www.tff.org/Default.aspx?pageId=30&kisiId=${kisi}" target="_blank" rel="noopener">TFF</a> ${BOLUM === "kadin" ? "maç sayfaları (kadın ligleri, 2008-09'dan bugüne)." : `maç sayfaları (lig 1990-91'den, gol dakikaları 1991-92'den; Türkiye Kupası 1990-2007)${MK_NOT()}.`}
    Ligler bugünkü adlarıyla gösteriliyor (1. kademe: ${esc(KADEME_AD[1])}, 2. kademe: ${esc(KADEME_AD[2])}…). Dakika, oyuna giriş-çıkış ve kırmızı kart dakikalarından hesaplanan yaklaşık süredir; uzatmalar sayılmaz.
    ${kaleci ? "Kaleci istatistikleri ilk 11'de kaleci olarak başladığı maçlardan (TFF kadroyu kaleciyle başlatıyor); oyundan çıktığı maçlarda da bütün maçın skoru sayılır, hükmen maçlar hariç." : ""}
    ${BOLUM === "erkek" ? `${uNo ? "Avrupa maçları UEFA'dan (Avrupa sekmesi)." : "Avrupa maçı kaydı bu oyuncuyla eşlenmedi."} ${OZET?.mk_kadro ? `Süper Lig'de ${OZET.mk_kadro.slice(0, 4)} öncesi` : "1990 öncesi"} maçlar henüz bu sayfada yok.` : ""}</p>
  </div>
  <div id="sk-av" hidden></div><div id="sk-td" hidden></div>
  <div id="milliOyuncu"></div>`;
  if (kAv) {
    $("#sk-av").innerHTML = kadinAvrupaHtml(kAv, AV.mac);
    $("#avSay").textContent = `${kAv.length} maç`;
  }
  if (uNo || tdK || kAv) {
    const n = uNo || tdK ? await oyuncuSayfa(uNo, tdArg, { oy: $("#sk-av"), td: $("#sk-td"), tdK: tdKs }) : null;
    if (n) {
      $("#avSay").textContent = `${n.oy} maç`;
      if (n.td) { const a = $('#oySekme a[data-k="td"]'); a.hidden = false; $("#tdSay").textContent = `${n.td} maç`; }
      if (!n.oy) $('#oySekme a[data-k="av"]').hidden = true;
    }
    icerik.querySelectorAll("#oySekme a").forEach(a => a.addEventListener("click", e => {
      e.preventDefault();
      icerik.querySelectorAll("#oySekme a").forEach(x => x.classList.toggle("aktif", x === a));
      for (const k of ["lk", "av", "td"]) $("#sk-" + k).hidden = a.dataset.k !== k;
    }));
  }
  if (typeof milliOyuncu === "function") {   // milli takım kaydı birleşmiş ikinci numarada olabilir
    for (const k of [kisi, ...(p.es || [])]) if (await milliOyuncu($("#milliOyuncu"), k, false)) break;
  }
}

// kulüp rekorları sekmesi: oyuncu rekorları (TFF maç sayfaları; filtreden bağımsız)
async function tffOyuncuRekorlari(kap, kid) {
  if (!kap) return;
  let d;
  try { d = await al(`${V}tff/kulup/${kid}.json?s=${OZET.surum || ""}`); } catch { return; }
  if (!d.lig_mac) return;
  const oy = (k, a) => `<a class="bag" href="#/${K}oyuncu/${String(k).startsWith("u") ? k : "k" + k}">${esc(a)}</a>`;   // u…: UEFA oyuncusu (TFF ile eşlenmemiş)
  const sira = (l, f) => { let r = 0, onc; return l.map((x, i) => { const v = f(x); if (v !== onc) { r = i + 1; onc = v; } return [r, x]; }); };
  const kart = (baslik, aciklama, l, deger, alt) => `<div class="kart rekor-kart"><h3>${baslik}</h3>${aciklama ? `<p class="soluk aciklama">${aciklama}</p>` : ""}
    ${l.length ? `<ol class="sirali">${sira(l, deger).slice(0, l.length > 12 ? 10 : 12).map(([r, x]) => `<li><span class="sira">${r}</span><span class="kim">${oy(x[0], x[1])}<small class="soluk">${alt(x)}</small></span><b class="n">${deger(x)}</b></li>`).join("")}</ol>
      ${l.length > 12 ? `<p class="soluk aciklama">ve aynı sayıyla ${l.length - 10} kayıt daha</p>` : ""}` : `<p class="soluk">—</p>`}</div>`;
  const yil = x => `${x[4].slice(0, 4)}–${x[5].slice(5)}`;
  const sz = x => `<a class="bag" href="#/${K}sezon/${x[2]}">${x[2]}</a>`;
  const mac = x => `${tarihYaz(x[5])} · ${x[6] != null ? kulupBag(x[6]) : ""} · ${skorBag(x[3], "maç")}`;
  kap.innerHTML = `<h2 class="bolum">Oyuncu rekorları</h2>
  <div class="izgara iki ust-hiza">
    ${kart("Ligde en çok maça çıkanlar", "İlk 11 ya da oyuna sonradan girerek", d.lig_mac, x => x[2], x => `${yil(x)} · ${x[3]} gol`)}
    ${kart("Ligde en çok gol atanlar", "Kendi kalesine goller hariç", d.lig_gol, x => x[3], x => `${yil(x)} · ${x[2]} maç`)}
    ${kart("Bir sezonda en çok gol", BOLUM === "kadin" ? "Lig, play-off ve final maçları" : "Lig ve kupa birlikte (Avrupa hariç)", d.sezon_gol, x => x[3], x => `${sz(x)} · ${x[6]} maç`)}
    ${kart("Bir sezonda ligde en çok gol", "", d.sezon_lig_gol, x => x[4], x => `${sz(x)}`)}
    ${kart("Bir sezonda en çok gol yemeden maç", `Kaleci: ilk 11'de başladığı ve takımının gol yemediği maçlar${BOLUM === "kadin" ? "" : ", lig ve kupa"}`, d.sezon_gy, x => x[5], x => `${sz(x)} · ${x[6]} maç`)}
    ${kart("Bir maçta en çok gol", BOLUM === "kadin" ? "Lig, play-off ve final maçları" : "Lig ve kupa", d.mac_gol, x => x[2], mac)}
    ${kart("Ligde bir maçta en çok gol", "", d.mac_lig_gol, x => x[2], mac)}
  </div>
  ${d.sari ? `<h2 class="bolum">Kartlar</h2>
  <div class="izgara iki ust-hiza">
    ${kart("En çok sarı kart görenler", BOLUM === "kadin" ? "Kulüpteki bütün maçlar" : "Kulüpteki bütün lig ve kupa maçları", d.sari, x => x[2], x => `${x[5].slice(0, 4)}–${x[6].slice(5)} · ${x[4]} maç`)}
    ${kart("En çok kırmızı kart görenler", "İkinci sarıdan kırmızı dahil", d.kirmizi, x => x[3], x => `${x[5].slice(0, 4)}–${x[6].slice(5)} · ${x[4]} maç`)}
    ${kart("Bir sezonda en çok sarı kart", BOLUM === "kadin" ? "" : "Lig ve kupa birlikte", d.sezon_sari, x => x[7], x => `${sz(x)} · ${x[6]} maç`)}
    ${kart("Bir sezonda en çok kırmızı kart", "İkinci sarıdan kırmızı dahil", d.sezon_kirmizi, x => x[8], x => `${sz(x)} · ${x[6]} maç`)}
  </div>` : ""}
  ${d.genc?.length ? (() => {   // yaş rekorları: maç günündeki yaş (tam doğum tarihi bilinen oyuncular)
    const yasYaz = x => {   // maç günü ve gün farkından doğum tarihi -> "15 yaş 3 ay 18 gün"
      const m = new Date(x[3] + "T12:00:00Z"), d = new Date(m - x[2] * 864e5);
      const ay = (dd, n) => { const s = Date.UTC(dd.getUTCFullYear(), dd.getUTCMonth() + n, 1);   // n ay sonrası (ay sonuna kırpılır)
        const son = new Date(Date.UTC(dd.getUTCFullYear(), dd.getUTCMonth() + n + 1, 0)).getUTCDate();
        return new Date(s + (Math.min(dd.getUTCDate(), son) - 1) * 864e5 + 432e5); };
      let n = (m.getUTCFullYear() - d.getUTCFullYear()) * 12 + m.getUTCMonth() - d.getUTCMonth();
      if (ay(d, n) > m) n--;
      const y = Math.floor(n / 12), a = n % 12, g = Math.round((m - ay(d, n)) / 864e5);
      return `${y} yaş${a ? ` ${a} ay` : ""}${g ? ` ${g} gün` : ""}`;
    };
    const yasMac = x => `${tarihYaz(x[3])} · ${x[5] != null ? kulupBag(x[5]) : ""} · ${skorBag(x[4], "maç")}`;
    const yk = (baslik, aciklama, l) => `<div class="kart rekor-kart"><h3>${baslik}</h3><p class="soluk aciklama">${aciklama}</p>
      ${l.length ? `<ol class="sirali">${l.map((x, i) => `<li><span class="sira">${i + 1}</span><span class="kim">${oy(x[0], x[1])}<small class="soluk">${yasMac(x)}</small></span><b class="n" style="font-size:13px;white-space:nowrap">${yasYaz(x)}</b></li>`).join("")}</ol>` : `<p class="soluk">—</p>`}</div>`;
    return `<h2 class="bolum">Yaş rekorları</h2>
  <div class="izgara iki ust-hiza">
    ${yk("En genç oyuncular", "Kulüpte oynadığı en erken maçtaki yaşı", d.genc)}
    ${yk("En yaşlı oyuncular", "Kulüpte oynadığı en geç maçtaki yaşı", d.yasli)}
    ${yk("En genç golcüler", "Kulüp için ilk golündeki yaşı (kendi kalesine hariç)", d.genc_gol)}
    ${yk("En yaşlı golcüler", "Kulüp için son golündeki yaşı", d.yasli_gol)}
  </div>
  <p class="soluk not">Yaş, maç günündeki yaştır; yalnız doğum tarihi tam bilinen oyuncular sayılır (TFF oyuncu sayfalarından, şimdilik ${sayiYaz(d.yas_kapsam || 0)} oyuncu).
    Az maça çıkmış oyuncuların sayfaları henüz inmediği için özellikle en genç oyuncu listeleri eksik olabilir; indirme tamamlandıkça güncellenecek.</p>`;
  })() : ""}
  <p class="soluk not">Kaynak: ${BOLUM === "kadin" ? `${KADIN_KAYNAK}.` : `TFF maç sayfaları — lig 1990-91'den (goller 1991-92'den), Türkiye Kupası 1990-2007${MK_NOT()}. Daha eski dönem ve Avrupa maçları bu listelere henüz girmiyor; seyirci kaydı TFF sayfalarında yok.`} Yukarıdaki filtreler bu bölümü etkilemez.</p>`;
}

// kulüp özeti: lig ve kupada en çok gol atan ve en çok maça çıkan oyuncular (TFF)
async function tffOyunculari(hedef, kid) {
  const kap = document.createElement("section");
  kap.className = "bolum";
  hedef.appendChild(kap);
  let d;
  try { d = await al(`${V}tff/kulup/${kid}.json?s=${OZET.surum || ""}`); } catch { kap.remove(); return; }
  const satir = (x, deger) => `<li><span class="kim"><a class="bag" href="#/${K}oyuncu/k${x[0]}">${esc(x[1])}</a>
    <small class="soluk">${x[4].slice(0, 4)}–${x[5].slice(5)} · ${x[2]} maç${x[3] ? ` · ${x[3]} gol` : ""}</small></span><b class="n">${deger}</b></li>`;
  const sira = (l, f) => { let r = 0, onc; return l.map((x, i) => { const v = f(x); if (v !== onc) { r = i + 1; onc = v; } return [r, x]; }); };
  const liste = (l, f) => `<ol class="sirali">${sira(l, f).map(([r, x]) => satir(x, f(x)).replace("<li>", `<li><span class="sira">${r}</span>`)).join("")}</ol>`;
  kap.innerHTML = `<h2>${BOLUM === "kadin" ? "Oyuncular" : "Lig ve kupada oyuncular"}</h2>
    <div class="izgara iki ust-hiza">
      <div class="kart rekor-kart"><h3>En çok gol atanlar</h3><p class="soluk aciklama">Penaltı golleri dahil, kendi kalesine goller hariç</p>${d.gol.length ? liste(d.gol.slice(0, 15), x => x[3]) : `<p class="soluk">—</p>`}</div>
      <div class="kart rekor-kart"><h3>En çok maça çıkanlar</h3><p class="soluk aciklama">İlk 11 ya da oyuna sonradan girerek</p>${liste(d.mac.slice(0, 15), x => x[2])}</div>
    </div>
    <p class="soluk not">Kaynak: ${BOLUM === "kadin" ? `${KADIN_KAYNAK}.` : `TFF maç sayfaları. Lig 1990-91'den, gol kayıtları 1991-92'den bugüne; Türkiye Kupası 1990-2007${MK_NOT()}. Daha eski dönem henüz yok.`}</p>`;
}

// oyuncu arama dizini (kulüp arama kutusunda: en az 3 harf yazılınca yüklenir)
let OYUNCULAR = null, OYUNCU_YUKLENIYOR = null;
function oyuncuDiziniAl() {
  return OYUNCU_YUKLENIYOR ||= al(`data/tff/oyuncular.json?s=${OZET.surum || ""}`).then(d => {
    OYUNCULAR = d.oyuncu.map(r => ({ kisi: r[0], ad: r[1], mac: r[2], gol: r[3], ilk: r[4], son: r[5], kulup: r[6], n: norm(r[1]) }));
    return OYUNCULAR;
  });
}
function oyuncuAra(q, adet = 5) {
  const n = norm(q); if (!OYUNCULAR || n.length < 3) return [];
  const out = [];
  for (const o of OYUNCULAR) {   // dizin maç sayısına göre sıralı: ilk eşleşenler en çok oynayanlar
    if (o.n.startsWith(n) || o.n.includes(" " + n) || (n.includes(" ") && o.n.includes(n))) { out.push(o); if (out.length >= adet) break; }
  }
  return out;
}

// ---------------------------------------------------------------- oyuncu sayfası (şimdilik UEFA: Avrupa maçları)
// UEFA oyuncusu -> TFF oyuncusu (oyuncu_bag.py): eşlenen oyuncunun tek sayfası TFF sayfasıdır, Avrupa maçları orada sekmede
let OYUNCU_BAG = null;
const oyuncuBagAl = async () => OYUNCU_BAG ||= await al(`data/oyuncu_bag.json?s=${OZET.surum || ""}`).catch(() => ({}));
async function oyuncuSayfa(no, tdNo, hedef) {
  if (!hedef) icerik.innerHTML = `<div class="yukleniyor">Yükleniyor…</div>`;
  const [d, av] = await Promise.all([al(`data/oyuncu_uefa.json?s=${OZET.surum || ""}`), al(`data/avrupa.json?s=${OZET.surum || ""}`)]);
  // teknik direktör sayfası oyuncu kaydına bağlıysa oyuncu sayfasına yönlen; oyuncunun teknik direktörlük kaydını bul
  if (tdNo && !hedef) {   // teknik direktör: TFF oyuncusuyla aynı kişiyse tek oyuncu sayfasına; TFF antrenör no UEFA kaydıyla birleşmişse oraya
    const T1 = await al(`data/teknik.json?s=${OZET.surum || ""}`), anahtar = tdNo.startsWith("a") ? tdNo : "t" + tdNo;
    const k = tdNo.startsWith("a") ? T1.tff?.[tdNo.slice(1)] : null, kk = k && k !== tdNo ? k : anahtar;
    if (T1.oyuncu?.[kk]) { location.replace(`#/oyuncu/k${T1.oyuncu[kk]}`); return; }
    if (k && k !== tdNo) { location.replace(`#/oyuncu/${k.startsWith("t") ? "t" + k.slice(1) : k}`); return; }
  }
  if (tdNo && !hedef && d.td_oyuncu[tdNo]) { location.replace(`#/oyuncu/u${d.td_oyuncu[tdNo]}`); return; }
  if (!hedef && no) { const B = await oyuncuBagAl(); if (B[no]) { location.replace(`#/oyuncu/k${B[no]}`); return; } }
  if (!tdNo) tdNo = Object.keys(d.td_oyuncu).find(k => d.td_oyuncu[k] === no) || null;
  const T0 = tdNo?.startsWith("a") ? await al(`data/teknik.json?s=${OZET.surum || ""}`) : null;
  const o = no ? d.oyuncu[no] : d.td[tdNo] ? [d.td[tdNo], null, null] : T0?.kisi[tdNo] ? [T0.kisi[tdNo][0], null, null] : null;
  if (!o) { icerik.innerHTML = `<div class="bos">Kişi bulunamadı.</div>`; return; }
  const [ad, dogum, ulke] = o;
  if (!hedef) document.title = `${ad} · Türk Futbol Arşivi`;
  const mac = new Map(av.maclar.map(r => [r[0], r]));
  const ks = d.katilim.filter(k => k[0] === no).map(k => {
    const r = mac.get(k[1]); const ev = r[5] === k[2];
    return { id: k[1], kulup: k[2], ilk11: k[3], gol: k[4], sari: k[5], kirmizi: k[6], giris: k[7], cikis: k[8], dakika: k[9], tarih: r[1], sezon: r[2], lig: r[3], tur: r[4],
      saha: ev ? "E" : "D", rakipId: ev ? r[6] : r[5], rakip: kulupAd(ev ? r[6] : r[5]) || (ev ? r[13] : r[12]), takim: kulupAd(k[2]),
      a: ev ? r[7] : r[8], y: ev ? r[8] : r[7], pa: ev ? r[9] : r[10], py: ev ? r[10] : r[9], durum: r[11] };
  }).map(m => ({ ...m, s: sonuc(m.a, m.y) })).sort((a, b) => b.tarih.localeCompare(a.tarih));
  const top = ks.reduce((t, k) => (t.mac++, t.ilk += k.ilk11, t.gol += k.gol, t.sari += k.sari, t.kirmizi += k.kirmizi, t.dk += k.dakika || 0, t), { mac: 0, ilk: 0, gol: 0, sari: 0, kirmizi: 0, dk: 0 });
  const kulupler = [...ks.reduce((m, k) => m.set(k.kulup, [...(m.get(k.kulup) || []), k]), new Map())];
  const yas = dogum && dogum.slice(5) !== "01-01" ? tarihYaz(dogum) : dogum ? dogum.slice(0, 4) : null;
  // teknik direktörlük (data/teknik.json: TFF lig/kupa + UEFA Avrupa)
  const T = await al(`data/teknik.json?s=${OZET.surum || ""}`);
  const tKey = tdNo ? (tdNo.startsWith("a") ? tdNo : "t" + tdNo) : null;
  const tKeys = new Set(hedef?.tdK?.length ? hedef.tdK : tKey ? [tKey] : []);
  const td = tKeys.size ? T.maclar.filter(x => tKeys.has(x[0])).map(x => ({ id: x[1], kulup: x[2], sezon: x[3], yar: x[4], a: x[5], y: x[6], tarih: x[7], s: sonuc(x[5], x[6]) })) : [];
  const ozetle = l => l.reduce((t, m) => (t.O++, t[m.s]++, t), { O: 0, G: 0, B: 0, M: 0 });
  const pm = t => t.O ? ((3 * t.G + t.B) / t.O).toFixed(2) : "–";
  const satirT = (bas, t, ek = "") => `<tr><td class="ad">${bas}</td>${ek}<td class="s">${t.O}</td><td class="s">${t.G}</td><td class="s">${t.B}</td><td class="s">${t.M}</td>
    <td class="s">%${yuzde(t.G, t.O)}</td><td class="s"><b>${pm(t)}</b></td></tr>`;
  const bas = ek => `<thead><tr><th>${ek[0]}</th>${ek.slice(1).map(x => `<th>${x}</th>`).join("")}<th class="s">O</th><th class="s">G</th><th class="s">B</th><th class="s">M</th><th class="s">G%</th><th class="s" title="Maç başı puan (galibiyet 3 puan)">P/M</th></tr></thead>`;
  const YAR_TD = { L: "Lig", K: "Türkiye Kupası", O: "Diğer kupalar", A: "Avrupa", T: "Terfi" };
  const tdHtml = !td.length ? "" : (() => {
    const t = ozetle(td);
    const yarlar = ["L", "K", "O", "A", "T"].filter(y => td.some(m => m.yar === y));
    const sezon = [...td.reduce((m, x) => { const k = `${x.sezon}|${x.kulup}`; return m.set(k, [...(m.get(k) || []), x]); }, new Map())]
      .sort((a, b) => b[0].localeCompare(a[0]));
    const kul = [...td.reduce((m, x) => m.set(x.kulup, [...(m.get(x.kulup) || []), x]), new Map())].sort((a, b) => b[1].length - a[1].length);
    return `<div class="kart"><div class="ozet-sat">
      <div><b>${t.O}</b><span>Maç</span></div><div><b>${t.G}</b><span>Galibiyet</span></div><div><b>${t.B}</b><span>Beraberlik</span></div>
      <div><b>${t.M}</b><span>Mağlubiyet</span></div><div><b>%${yuzde(t.G, t.O)}</b><span>Kazanma</span></div><div><b>${pm(t)}</b><span>Maç başı puan</span></div></div>
      <div class="cubuk"><i class="g" style="width:${yuzde(t.G, t.O)}%"></i><i class="b" style="width:${yuzde(t.B, t.O)}%"></i><i class="m" style="width:${yuzde(t.M, t.O)}%"></i></div></div>
    <div class="izgara iki bolum ust-hiza">
      <div class="tablo-kap"><table class="tablo">${bas(["Yarışma"])}<tbody>${yarlar.map(y => satirT(YAR_TD[y], ozetle(td.filter(m => m.yar === y)))).join("")}${yarlar.length > 1 ? satirT("<b>Toplam</b>", t).replace("<tr>", '<tr class="toplam">') : ""}</tbody></table></div>
      <div class="tablo-kap"><table class="tablo">${bas(["Kulüp"])}<tbody>${kul.map(([kid, l]) => satirT(kulupBag(kid), ozetle(l))).join("")}</tbody></table></div>
    </div>
    <div class="tablo-kap bolum"><table class="tablo">${bas(["Sezon", "Kulüp", "Yarışma"])}<tbody>${sezon.map(([k, l]) => {
      const [sz, kid] = k.split("|");
      return satirT(`<a class="bag" href="#/${K}sezon/${sz}">${sz}</a>`, ozetle(l), `<td class="ad">${kulupBag(+kid)}</td><td class="soluk">${[...new Set(l.map(m => YAR_TD[m.yar]))].join(", ")}</td>`);
    }).join("")}</tbody></table></div>
    <p class="soluk not">Lig ve kupa maçları TFF maç sayfalarından (dört profesyonel lig 1990-91'den, Türkiye Kupası 1990-2007 ve 2007 sonrası özel kupalar${MK_NOT()}), Avrupa maçları UEFA'dan. Maç başı puan bütün sezonlarda galibiyet 3 puanla hesaplandı; hükmen maçlar dahil değil.</p>`;
  })();
  const html = `
  <div class="sayfa-bas"><div><h1>${esc(ad)}</h1>
    <p class="soluk">${ulke ? (ULKE[ulke] ? ulkeHtml(ulke) : ulke === "TUR" ? `${bayrak("TUR")} Türkiye` : esc(ulke)) : ""}${yas ? ` · Doğum: ${yas}` : ""}</p></div></div>
  ${ks.length && td.length ? `<nav class="sekmeler bolum">
    <a href="#" data-k="oy" class="${ks.length >= td.length ? "aktif" : ""}">Oyuncu olarak <small class="soluk">${ks.length} maç</small></a>
    <a href="#" data-k="td" class="${ks.length < td.length ? "aktif" : ""}">Teknik direktör olarak <small class="soluk">${td.length} maç</small></a></nav>`
    : ks.length ? `<h2 class="bolum">Oyuncu olarak</h2>` : td.length ? `<h2 class="bolum">Teknik direktör olarak</h2>` : ""}
  <div id="sk-oy" ${ks.length && td.length && ks.length < td.length ? "hidden" : ""}>
  ${ks.length ? `<div class="kart"><div class="ozet-sat">
    <div><b>${top.mac}</b><span>Avrupa maçı</span></div><div><b>${top.ilk}</b><span>İlk 11</span></div><div><b>${top.gol}</b><span>Gol</span></div>
    <div><b>${top.sari}</b><span>Sarı kart</span></div><div><b>${top.kirmizi}</b><span>Kırmızı kart</span></div>
    ${top.dk ? `<div><b>${sayiYaz(top.dk)}</b><span>Dakika*</span></div>` : ""}</div>
    ${top.dk ? `<p class="soluk not" style="margin:8px 0 0">* Dakika bilgisi UEFA'nın istatistik tuttuğu maçlardan.</p>` : ""}</div>` : ""}
  ${ks.length ? (() => {   // kulüp ve sezon tabloları: oyuncunun katkısı ve oynadığı maçlarda takımın sonuçları
    const say = l => l.reduce((t, k) => (t.mac++, t.ilk += k.ilk11, t.gol += k.gol, t.sari += k.sari, t.kirmizi += k.kirmizi, t.dk += k.dakika || 0, t[k.s] = (t[k.s] || 0) + 1, t),
      { mac: 0, ilk: 0, gol: 0, sari: 0, kirmizi: 0, dk: 0, G: 0, B: 0, M: 0 });
    const hucre = t => `<td class="s"><b>${t.mac}</b></td><td class="s">${t.ilk}</td><td class="s"><b>${t.gol || ""}</b></td><td class="s">${t.sari || ""}</td><td class="s">${t.kirmizi || ""}</td>
      <td class="s">${t.dk ? sayiYaz(t.dk) : ""}</td><td class="s">${t.G}</td><td class="s">${t.B}</td><td class="s">${t.M}</td><td class="s">%${yuzde(t.G, t.mac)}</td>`;
    const bas_ = ek => `<thead><tr>${ek.map((x, i) => `<th${i ? ' class="ad"' : ""}>${x}</th>`).join("")}<th class="s">Maç</th><th class="s" title="İlk 11'de başladığı maç">İlk 11</th>
      <th class="s">Gol</th><th class="s" title="Sarı kart">Sarı</th><th class="s" title="Kırmızı kart">Kırm.</th><th class="s" title="UEFA'nın istatistik tuttuğu maçlarda">Dakika</th>
      <th class="s" title="Oynadığı maçlarda takımının galibiyeti">G</th><th class="s">B</th><th class="s">M</th><th class="s" title="Galibiyet yüzdesi">G%</th></tr></thead>`;
    const sezonlar = [...ks.reduce((m, k) => { const x = `${k.sezon}|${k.kulup}`; return m.set(x, [...(m.get(x) || []), k]); }, new Map())];
    return `<div class="tablo-kap bolum"><table class="tablo">${bas_(["Kulüp"])}<tbody>
      ${kulupler.map(([kid, l]) => `<tr><td class="ad">${kid != null && KULUP.has(kid) ? kulupBag(kid) : esc(kulupAd(kid))}</td>${hucre(say(l))}</tr>`).join("")}
      ${kulupler.length > 1 ? `<tr class="toplam"><td class="ad"><b>Toplam</b></td>${hucre(say(ks))}</tr>` : ""}</tbody></table></div>
    <h3 class="bolum">Sezon sezon</h3>
    <div class="tablo-kap"><table class="tablo">${bas_(["Sezon", "Kulüp", "Kupa"])}<tbody>${sezonlar.map(([x, l]) => {
      const [sz, kid] = x.split("|");
      return `<tr><td><a class="bag" href="#/${K}sezon/${sz}">${sz}</a></td><td class="ad">${kulupBag(+kid)}</td><td class="ad soluk">${[...new Set(l.map(m => m.lig))].map(esc).join(", ")}</td>${hucre(say(l))}</tr>`;
    }).join("")}</tbody></table></div>
    <h3 class="bolum">Maçlar</h3>`;
  })() : ""}
  <div class="izgara iki ust-hiza">${kulupler.map(([kid, l]) => `<div class="kart"><h3>${kid != null && KULUP.has(kid) ? kulupBag(kid) : esc(kulupAd(kid))}</h3>
    <p class="soluk" style="margin:0 0 6px;font-size:13px">${l.length} maç · ${l.reduce((s, k) => s + k.gol, 0)} gol · ${l.at(-1).sezon} – ${l[0].sezon}</p>
    <div class="tabelalar">${l.map(m => `${tabelaSatir(m, true)}<div class="katki">${m.ilk11 ? "İlk 11" : `${m.giris}'de girdi`}${m.cikis != null ? ` · ${m.cikis}'de çıktı` : ""}${m.gol ? ` · ${"⚽".repeat(m.gol)}` : ""}${m.sari ? " · 🟨" : ""}${m.kirmizi ? " · 🟥" : ""}</div>`).join("")}</div></div>`).join("")}</div>
  </div>
  <div id="sk-td" ${ks.length && td.length && ks.length >= td.length ? "hidden" : ""}>${tdHtml}</div>
  <p class="soluk not bolum">Kaynak: UEFA (Türk takımlarının Avrupa kupası maçları)${tdHtml ? "; teknik direktörlükte lig ve kupa maçları TFF maç sayfalarından" : ""}.</p>`;
  if (hedef) {   // TFF oyuncu sayfasının Avrupa ve teknik direktör sekmeleri
    const g = document.createElement("div"); g.innerHTML = html;
    hedef.oy.replaceChildren(...g.querySelector("#sk-oy").childNodes);
    hedef.td.replaceChildren(...g.querySelector("#sk-td").childNodes);
    return { oy: ks.length, td: td.length };
  }
  icerik.innerHTML = html;

  icerik.querySelectorAll(".sekmeler a[data-k]").forEach(a => a.addEventListener("click", e => {
    e.preventDefault();
    icerik.querySelectorAll(".sekmeler a[data-k]").forEach(x => x.classList.toggle("aktif", x === a));
    $("#sk-oy").hidden = a.dataset.k !== "oy"; $("#sk-td").hidden = a.dataset.k !== "td";
  }));
}

// ---------------------------------------------------------------- Avrupa: ülkelere göre
const ULKE = {   // UEFA ülke kodu -> [Türkçe ad, bayrak]
  ALB: ["Arnavutluk", "🇦🇱"], AND: ["Andorra", "🇦🇩"], ARM: ["Ermenistan", "🇦🇲"], AUT: ["Avusturya", "🇦🇹"], AZE: ["Azerbaycan", "🇦🇿"],
  BEL: ["Belçika", "🇧🇪"], BIH: ["Bosna-Hersek", "🇧🇦"], BLR: ["Belarus", "🇧🇾"], BUL: ["Bulgaristan", "🇧🇬"], CRO: ["Hırvatistan", "🇭🇷"],
  CYP: ["Kıbrıs", "🇨🇾"], CZE: ["Çekya", "🇨🇿"], TCH: ["Çekoslovakya", "🇨🇿"], DEN: ["Danimarka", "🇩🇰"], ENG: ["İngiltere", "🏴󠁧󠁢󠁥󠁮󠁧󠁿"],
  ESP: ["İspanya", "🇪🇸"], EST: ["Estonya", "🇪🇪"], FIN: ["Finlandiya", "🇫🇮"], FRA: ["Fransa", "🇫🇷"], FRO: ["Faroe Adaları", "🇫🇴"],
  GEO: ["Gürcistan", "🇬🇪"], GER: ["Almanya", "🇩🇪"], FRG: ["Batı Almanya", "🇩🇪"], GDR: ["Doğu Almanya", "🇩🇪"], GIB: ["Cebelitarık", "🇬🇮"],
  GRE: ["Yunanistan", "🇬🇷"], HUN: ["Macaristan", "🇭🇺"], IRL: ["İrlanda", "🇮🇪"], ISL: ["İzlanda", "🇮🇸"], ISR: ["İsrail", "🇮🇱"],
  ITA: ["İtalya", "🇮🇹"], KAZ: ["Kazakistan", "🇰🇿"], KOS: ["Kosova", "🇽🇰"], LIE: ["Lihtenştayn", "🇱🇮"], LTU: ["Litvanya", "🇱🇹"],
  LUX: ["Lüksemburg", "🇱🇺"], LVA: ["Letonya", "🇱🇻"], MDA: ["Moldova", "🇲🇩"], MKD: ["Kuzey Makedonya", "🇲🇰"], MLT: ["Malta", "🇲🇹"],
  MNE: ["Karadağ", "🇲🇪"], NED: ["Hollanda", "🇳🇱"], NIR: ["Kuzey İrlanda", "🇬🇧"], NOR: ["Norveç", "🇳🇴"], POL: ["Polonya", "🇵🇱"],
  POR: ["Portekiz", "🇵🇹"], ROU: ["Romanya", "🇷🇴"], RUS: ["Rusya", "🇷🇺"], URS: ["Sovyetler Birliği", "🇷🇺"], SCO: ["İskoçya", "🏴󠁧󠁢󠁳󠁣󠁴󠁿"],
  SMR: ["San Marino", "🇸🇲"], SRB: ["Sırbistan", "🇷🇸"], YUG: ["Yugoslavya", "🇷🇸"], SCG: ["Sırbistan-Karadağ", "🇷🇸"], SUI: ["İsviçre", "🇨🇭"],
  SVK: ["Slovakya", "🇸🇰"], SVN: ["Slovenya", "🇸🇮"], SWE: ["İsveç", "🇸🇪"], UKR: ["Ukrayna", "🇺🇦"], WAL: ["Galler", "🏴󠁧󠁢󠁷󠁬󠁳󠁿"],
};
const ulkeAd = u => u ? (ULKE[u] ? ULKE[u][0] : u) : "Bilinmiyor";
// bayrak resmi (docs/bayrak/<iso>.svg; Windows bayrak emojisi göstermiyor). Tarihi ülkeler kendi bayraklarıyla.
const ULKE_BAYRAK = { TCH: "cs", GDR: "dd", URS: "su", YUG: "yu" };
function bayrakKod(u) {
  if (ULKE_BAYRAK[u]) return ULKE_BAYRAK[u];
  const e = ULKE[u]?.[1]; if (!e) return u === "TUR" ? "tr" : null;
  const cp = [...e].map(c => c.codePointAt(0));
  if (cp.length === 2 && cp.every(c => c >= 0x1F1E6 && c <= 0x1F1FF)) return cp.map(c => String.fromCharCode(c - 0x1F1E6 + 97)).join("");
  const etiket = cp.filter(c => c >= 0xE0061 && c <= 0xE007A).map(c => String.fromCharCode(c - 0xE0000)).join("");
  return { gbeng: "gb-eng", gbsct: "gb-sct", gbwls: "gb-wls", gbnir: "gb-nir" }[etiket] || null;
}
const bayrak = u => { const k = bayrakKod(u); return k ? `<img class="bayrak" src="bayrak/${k}.svg" alt="" loading="lazy">` : ""; };
const ulkeHtml = u => `${bayrak(u)} ${esc(ulkeAd(u))}`;
const avrupaDurum = { kulup: "", yar: "", sira: "O", ters: true, ulke: null };

async function avrupaUlkeler() {
  const kap = document.createElement("section");
  kap.className = "bolum";
  kap.innerHTML = `<h2>Avrupa'da ülkelere göre</h2><div class="yukleniyor" style="padding:20px">Yükleniyor…</div>`;
  icerik.appendChild(kap);
  const d = await al(`data/avrupa.json?s=${OZET.surum || ""}`);
  // kulübe bağlanmamış rakip (RSSSF Intertoto): adından yabancı kulüp kaydı bulunursa ona bağla
  const adIndeks = new Map();
  for (const k of KULUPLER) if (!k.yerli) for (const a of [k.ad, ...k.adlar.map(x => x[0])]) adIndeks.set(norm(a), k.id);
  const bagla = (id, ad) => id ?? adIndeks.get(norm(ad)) ?? null;
  const adUlke = new Map(Object.entries(d.ad_ulke || {}).map(([a, u]) => [norm(a), u]));   // büyük/küçük harf farkı tutsun
  const tum = d.maclar.map(r => ({ id: r[0], tarih: r[1], sezon: r[2], lig: r[3], tur: r[4], ev: bagla(r[5], r[12]), dep: bagla(r[6], r[13]), eg: r[7], dg: r[8], ep: r[9], dp: r[10], durum: r[11], evAd: r[12], depAd: r[13] }));
  const turk = id => KULUP.get(id)?.yerli;
  const kulupler = [...tum.reduce((m, x) => { for (const k of [x.ev, x.dep]) if (turk(k)) m.set(k, (m.get(k) || 0) + 1); return m; }, new Map())].sort((a, b) => b[1] - a[1]);
  const ligler = [...new Set(tum.map(m => m.lig))];
  const ciz = () => {
    const D = avrupaDurum;
    // her maç, Türk tarafının bakışıyla (iki Türk takımı karşılaştıysa — Süper Kupa vb. — dışarıda kalır)
    const satir = [];
    for (const m of tum) {
      if (m.eg == null || (D.yar && m.lig !== D.yar)) continue;
      const evT = !!turk(m.ev), depT = !!turk(m.dep);
      if (evT === depT) continue;
      const biz = evT ? m.ev : m.dep, rakip = evT ? m.dep : m.ev;
      if (D.kulup && biz !== +D.kulup) continue;
      const a = evT ? m.eg : m.dg, y = evT ? m.dg : m.eg;
      satir.push({ ...m, biz, rakip, rakipAd: evT ? m.depAd : m.evAd, a, y, saha: evT ? "E" : "D", s: sonuc(a, y), ulke: KULUP.get(rakip)?.ulke || adUlke.get(norm(evT ? m.depAd : m.evAd)) || "" });
    }
    const tablo = new Map();
    for (const m of satir) {
      const x = tablo.get(m.ulke) || { ulke: m.ulke, O: 0, G: 0, B: 0, M: 0, AG: 0, YG: 0, rakip: new Set() };
      x.O++; x[m.s]++; x.AG += m.a; x.YG += m.y; x.rakip.add(m.rakip ?? m.rakipAd); tablo.set(m.ulke, x);
    }
    const anahtar = { O: x => x.O, G: x => x.G, B: x => x.B, M: x => x.M, AG: x => x.AG, YG: x => x.YG, Av: x => x.AG - x.YG, Y: x => x.G / x.O, ad: x => ulkeAd(x.ulke) };
    const l = [...tablo.values()].sort((p, q) => { const f = anahtar[D.sira], a = f(p), b = f(q); return (typeof a === "string" ? a.localeCompare(b, "tr") : a - b) * (D.ters ? -1 : 1) || q.O - p.O; });
    const top = satir.reduce((t, m) => (t.O++, t[m.s]++, t.AG += m.a, t.YG += m.y, t), { O: 0, G: 0, B: 0, M: 0, AG: 0, YG: 0 });
    const ayrinti = D.ulke !== null ? satir.filter(m => m.ulke === D.ulke).sort((p, q) => q.tarih.localeCompare(p.tarih)) : [];
    kap.innerHTML = `<h2>Avrupa'da ülkelere göre</h2>
      <p class="soluk not">Türk kulüplerinin Avrupa kupası maçları, rakibin ülkesine göre. Bir ülkeye tıklayınca o ülke takımlarıyla oynanan maçlar açılır.</p>
      <div class="filtre">
        <select id="avKulup"><option value="">Bütün Türk kulüpleri</option>${kulupler.map(([id, n]) => `<option value="${id}" ${+D.kulup === id ? "selected" : ""}>${esc(kulupAd(id))} (${n})</option>`).join("")}</select>
        <select id="avYar"><option value="">Bütün kupalar</option>${ligler.map(y => `<option ${D.yar === y ? "selected" : ""}>${esc(y)}</option>`).join("")}</select>
        <span class="soluk">${top.O} maç · ${top.G}G ${top.B}B ${top.M}M · ${top.AG}-${top.YG}</span>
      </div>
      <div class="tablo-kap"><table class="tablo"><thead><tr>
        ${[["ad", "Ülke"], ["O", "O"], ["G", "G"], ["B", "B"], ["M", "M"], ["AG", "AG"], ["YG", "YG"], ["Av", "Av"], ["Y", "G%"]].map(([k, a]) => `<th class="sirala ${k === "ad" ? "" : "s"}" data-k="${k}">${a}${D.sira === k ? (D.ters ? " ↓" : " ↑") : ""}</th>`).join("")}
        <th class="s gizle-mobil">Rakip</th></tr></thead>
        <tbody>${l.map(x => `<tr class="${D.ulke === x.ulke ? "vurgu-sat" : ""}" data-u="${x.ulke}" style="cursor:pointer"><td class="ad">${ulkeHtml(x.ulke)}</td><td class="s">${x.O}</td><td class="s">${x.G}</td><td class="s">${x.B}</td><td class="s">${x.M}</td>
          <td class="s">${x.AG}</td><td class="s">${x.YG}</td><td class="s">${x.AG - x.YG > 0 ? "+" : ""}${x.AG - x.YG}</td><td class="s">%${yuzde(x.G, x.O)}</td><td class="s gizle-mobil">${x.rakip.size}</td></tr>`).join("")}</tbody></table></div>
      ${D.ulke !== null ? `<div class="kart bolum"><h3>${ulkeHtml(D.ulke)} — ${ayrinti.length} maç</h3><div class="tabelalar">${ayrinti.map(m => tabelaSatir({
        id: m.id, tarih: m.tarih, lig: m.lig, tur: m.tur, saha: m.saha, kulup: m.biz, takim: kulupAd(m.biz), rakipId: m.rakip, rakip: m.rakip != null ? kulupAd(m.rakip) : m.rakipAd,
        a: m.a, y: m.y, pa: m.saha === "E" ? m.ep : m.dp, py: m.saha === "E" ? m.dp : m.ep, durum: m.durum, s: m.s }, true)).join("")}</div></div>` : ""}`;
    kap.querySelector("#avKulup").addEventListener("change", e => { D.kulup = e.target.value; D.ulke = null; ciz(); });
    kap.querySelector("#avYar").addEventListener("change", e => { D.yar = e.target.value; D.ulke = null; ciz(); });
    kap.querySelectorAll("th.sirala").forEach(th => th.addEventListener("click", () => { if (D.sira === th.dataset.k) D.ters = !D.ters; else { D.sira = th.dataset.k; D.ters = th.dataset.k !== "ad"; } ciz(); }));
    kap.querySelectorAll("tr[data-u]").forEach(tr => tr.addEventListener("click", () => { D.ulke = D.ulke === tr.dataset.u ? null : tr.dataset.u; ciz(); }));
  };
  ciz();
}

// ---------------------------------------------------------------- sezonlar
function sezonlarSayfa() {
  document.title = "Sezonlar · Türk Futbol Arşivi";
  const on = new Map();
  for (const s of [...OZET.sezonlar].reverse()) { const d = s.slice(0, 3) + "0"; (on.get(d) || on.set(d, []).get(d)).push(s); }
  icerik.innerHTML = `<h1>Sezonlar</h1><p class="soluk">Puan tabloları maç sonuçlarından hesaplanır.</p>
    ${[...on].map(([d, ss]) => `<div class="on-dekad">${d}'lar</div><div class="sezon-izgara">${ss.map(s => `<a href="#/${K}sezon/${s}">${s}</a>`).join("")}</div>`).join("")}`;
}
async function sezonSayfa(sezon) {
  document.title = `${sezon} · Türk Futbol Arşivi`;
  icerik.innerHTML = `<div class="yukleniyor">${esc(sezon)} yükleniyor…</div>`;
  const d = await al(`data/sezon/${sezon}.json?s=${OZET.surum || ""}`);
  const ms = d.maclar.map(r => ({ id: r[0], tarih: r[1], yar: r[2], lig: r[3], kademe: r[4], tur: r[5], po: r[6] === "p" || r[6] === "x", iptal: r[6] === "x", ev: r[7], evAd: r[8], dep: r[9], depAd: r[10], eg: r[11], dg: r[12], ep: r[13], dp: r[14], durum: r[15] }));
  const i = OZET.sezonlar.indexOf(sezon);
  const onceki = OZET.sezonlar[i - 1], sonraki = OZET.sezonlar[i + 1];
  const gruplar = new Map();
  for (const m of ms) if ((m.yar === "L" || m.yar === "T") && !m.po) {
    const k = `${m.yar}|${m.kademe ?? 9}|${m.lig}|${m.tur}`;
    (gruplar.get(k) || gruplar.set(k, { yar: m.yar, kademe: m.kademe, lig: m.lig, grup: m.tur, ms: [] }).get(k)).ms.push(m);
  }
  const sirali = [...gruplar.values()].sort((a, b) => (a.yar === "T") - (b.yar === "T") || (a.kademe ?? 9) - (b.kademe ?? 9) || a.lig.localeCompare(b.lig, "tr") || String(a.grup).localeCompare(String(b.grup), "tr", { numeric: true }));
  const p = puan(sezon);
  const tabloHtml = g => {
    const t = new Map();
    const sat = (id, ad) => t.get(id) || t.set(id, { id, ad, O: 0, G: 0, B: 0, M: 0, AG: 0, YG: 0 }).get(id);
    for (const m of g.ms) {
      if (m.durum === "Çifte H") { for (const [id, ad] of [[m.ev ?? "a" + m.evAd, m.evAd], [m.dep ?? "a" + m.depAd, m.depAd]]) { const x = sat(id, ad); x.O++; x.M++; x.YG += 3; } continue; }
      if (m.eg == null) continue;
      const e = sat(m.ev ?? "a" + m.evAd, m.evAd), dd = sat(m.dep ?? "a" + m.depAd, m.depAd);
      e.ad = m.evAd; dd.ad = m.depAd;
      e.O++; dd.O++; e.AG += m.eg; e.YG += m.dg; dd.AG += m.dg; dd.YG += m.eg;
      if (m.eg > m.dg) { e.G++; dd.M++; } else if (m.eg < m.dg) { dd.G++; e.M++; } else { e.B++; dd.B++; }
    }
    const l = [...t.values()].map(x => ({ ...x, P: x.G * p + x.B, Av: x.AG - x.YG })).sort((a, b) => b.P - a.P || b.Av - a.Av || b.AG - a.AG);
    const oynanmamis = g.ms.filter(m => m.eg == null && m.durum !== "Çifte H").length;
    return `<div class="kart puan-kart">
      <div class="bas"><h3>${esc(g.lig)}${g.grup ? ` · ${esc(g.grup)}` : ""}</h3>
      <span>${g.ms.length} maç${oynanmamis ? `, ${oynanmamis} oynanmadı` : ""}</span></div>
      <table class="tablo"><thead><tr><th class="s">#</th><th>Takım</th><th class="s">O</th><th class="s ek2">G</th><th class="s ek2">B</th><th class="s ek2">M</th><th class="s ek">AG</th><th class="s ek">YG</th><th class="s">Av</th><th class="s">P</th></tr></thead>
      <tbody>${l.map((x, i) => `<tr><td class="s soluk">${i + 1}</td><td class="takim" title="${esc(x.ad)}">${typeof x.id === "number" ? kulupBag(x.id, kisaAd(x.id, x.ad)) : esc(kisaAd(null, x.ad))}</td><td class="s">${x.O}</td><td class="s ek2">${x.G}</td><td class="s ek2">${x.B}</td><td class="s ek2">${x.M}</td><td class="s ek">${x.AG}</td><td class="s ek">${x.YG}</td><td class="s">${x.Av > 0 ? "+" : ""}${x.Av}</td><td class="s p">${x.P}</td></tr>`).join("")}</tbody></table>
      <details><summary>Maçlar</summary>${macListesi(g.ms)}</details></div>`;
  };
  const kupa = ms.filter(m => m.yar === "K"), ozel = [...new Set(ms.filter(m => m.yar === "O").map(m => m.lig))].map((lig, i) => ({ k: "oz" + i, lig, ms: ms.filter(m => m.yar === "O" && m.lig === lig) })), avrupa = ms.filter(m => m.yar === "A"), po = ms.filter(m => (m.yar === "L" || m.yar === "T") && m.po);
  const turlara = l => { const t = new Map(); for (const m of l) (t.get(m.tur || m.lig) || t.set(m.tur || m.lig, []).get(m.tur || m.lig)).push(m); return [...t]; };
  icerik.innerHTML = `
  <div class="sayfa-bas"><h1>${esc(sezon)} sezonu</h1>
    <div class="yan-yana">${onceki ? `<a class="cip" href="#/${K}sezon/${onceki}">← ${onceki}</a>` : ""}${sonraki ? `<a class="cip" href="#/${K}sezon/${sonraki}">${sonraki} →</a>` : ""}</div></div>
  <p class="soluk">${ms.length} maç · Puan tabloları sonuçlardan hesaplandı (galibiyet ${p} puan; puan silme ve averaj kuralı farkları dahil değil).</p>
  <nav class="sekmeler">${sirali.length ? `<a href="#lig" data-k="lig" class="aktif">Lig</a>` : ""}${po.length ? `<a href="#po" data-k="po">Play-off / baraj</a>` : ""}${kupa.length ? `<a href="#kupa" data-k="kupa">Türkiye Kupası</a>` : ""}${ozel.map(o => `<a href="#${o.k}" data-k="${o.k}">${esc(o.lig)}</a>`).join("")}${avrupa.length ? `<a href="#avrupa" data-k="avrupa">Avrupa</a>` : ""}</nav>
  <div id="sz-lig" class="izgara puan">${sirali.map(tabloHtml).join("") || ""}</div>
  <div id="sz-po" hidden><p class="soluk not">Normal sezondan sonra oynanan yükselme play-off'ları, düşme barajları ve gruplar arası final maçları. Puan tablolarına girmez. Turlar (yarı final, final...) TFF'nin yazdığı yerde ondan, yazmadığı yerde eşleşmelerden çıkarıldı.</p>
    ${playoffHtml(po, ms)}</div>
  <div id="sz-kupa" hidden>${turlara(kupa).map(([t, l]) => `<div class="kart" style="margin-bottom:12px"><h3>${esc(t)}</h3>${macListesi(l)}</div>`).join("")}</div>
  ${ozel.map(o => `<div id="sz-${o.k}" hidden>${macListesi(o.ms)}</div>`).join("")}
  <div id="sz-avrupa" hidden>${turlara(avrupa.map(m => ({ ...m, tur: `${m.lig}${m.tur ? " · " + m.tur : ""}` }))).map(([t, l]) => `<div class="kart" style="margin-bottom:12px"><h3>${esc(t)}</h3>${macListesi(l)}</div>`).join("")}</div>`;
  const ilk = sirali.length ? "lig" : po.length ? "po" : kupa.length ? "kupa" : ozel.length ? ozel[0].k : "avrupa";
  const goster = k => { ["lig", "po", "kupa", ...ozel.map(o => o.k), "avrupa"].forEach(x => { const e = $("#sz-" + x); if (e) e.hidden = x !== k; }); icerik.querySelectorAll(".sekmeler a").forEach(a => a.classList.toggle("aktif", a.dataset.k === k)); };
  icerik.querySelectorAll(".sekmeler a").forEach(a => a.addEventListener("click", e => { e.preventDefault(); goster(a.dataset.k); }));
  goster(ilk);
}
// ---------------------------------------------------------------- play-off turları
// Aynı ligin play-off maçları, birbiriyle oynamış takım kümelerine (eşleşme ağaçlarına) ayrılır. Her ağaçta iki takımın
// maçları bir eşleşmedir (tek maç ya da iki ayak); tur = takımların bir önceki eşleşmesinin turu + 1. En son tur final,
// bir önceki yarı final... Son turda iki eşleşme varsa önceki turu kazananlarınki final, diğeri 3.lük maçı.
// Takım sayısından çok eşleşme varsa (herkes herkesle) ağaç değil, play-off grubudur.
const TFF_TUR = [[/^final/i, "Final"], [/^yar[ıi] ?final/i, "Yarı final"], [/^çeyrek ?final/i, "Çeyrek final"], [/^(\d)\. ?tur/i, m => `${m[1]}. tur`]];
function tffTur(t) { for (const [re, ad] of TFF_TUR) { const m = String(t || "").match(re); if (m) return typeof ad === "function" ? ad(m) : ad; } return null; }
function playoffHtml(po, ms) {
  const takim = (m, s) => s === "ev" ? (m.ev ?? "a" + m.evAd) : (m.dep ?? "a" + m.depAd);
  const grupOf = new Map();   // takımın normal sezondaki grubu
  for (const m of ms) if (m.yar === "L" && !m.po && m.tur) for (const s of ["ev", "dep"]) grupOf.set(takim(m, s), m.tur);
  const ligler = new Map();
  for (const m of po) (ligler.get(m.lig) || ligler.set(m.lig, []).get(m.lig)).push(m);
  const sirali = [...ligler].sort((a, b) => (a[1][0].kademe ?? 9) - (b[1][0].kademe ?? 9) || a[0].localeCompare(b[0], "tr"));
  return sirali.map(([lig, l]) => {
    l = [...l].sort((a, b) => (a.tarih || "").localeCompare(b.tarih || ""));
    // eşleşme ağaçları: birlikte oynamış takımlar (birleşim-bul)
    const ata = new Map(), bul = x => { while (ata.get(x) !== x) x = ata.get(x); return x; };
    for (const m of l) for (const s of ["ev", "dep"]) if (!ata.has(takim(m, s))) ata.set(takim(m, s), takim(m, s));
    for (const m of l) { const a = bul(takim(m, "ev")), b = bul(takim(m, "dep")); if (a !== b) ata.set(a, b); }
    const agaclar = new Map();
    for (const m of l) (agaclar.get(bul(takim(m, "ev"))) || agaclar.set(bul(takim(m, "ev")), []).get(bul(takim(m, "ev")))).push(m);
    const bolumler = [...agaclar.values()].map(ml => {
      const esl = new Map();   // eşleşme: takım çifti
      for (const m of ml) { const k = [takim(m, "ev"), takim(m, "dep")].map(String).sort().join("|"); (esl.get(k) || esl.set(k, { ms: [] }).get(k)).ms.push(m); }
      const es = [...esl.values()].sort((a, b) => a.ms[0].tarih.localeCompare(b.ms[0].tarih));
      const takimlar = new Set(ml.flatMap(m => [takim(m, "ev"), takim(m, "dep")]));
      const grupMu = es.length > takimlar.size;
      const kazanan = e => {   // toplam skor, eşitse son maçın penaltıları
        const t = new Map();
        for (const m of e.ms) { if (m.eg == null) return null; t.set(takim(m, "ev"), (t.get(takim(m, "ev")) || 0) + m.eg); t.set(takim(m, "dep"), (t.get(takim(m, "dep")) || 0) + m.dg); }
        const [[a, ga], [b, gb]] = [...t];
        if (ga !== gb) return ga > gb ? a : b;
        const s = e.ms.at(-1); if (s.ep == null) return null;
        return s.ep > s.dp ? takim(s, "ev") : takim(s, "dep");
      };
      const son = new Map(), kazandi = new Map();
      for (const e of es) {
        const [a, b] = [takim(e.ms[0], "ev"), takim(e.ms[0], "dep")];
        e.tur = 1 + Math.max(son.get(a) || 0, son.get(b) || 0);
        e.onceKazandi = [a, b].every(x => kazandi.get(x) !== false && son.has(x));
        son.set(a, e.tur); son.set(b, e.tur);
        const w = kazanan(e); kazandi.set(a, w == null ? undefined : w === a); kazandi.set(b, w == null ? undefined : w === b);
      }
      const enUst = Math.max(...es.map(e => e.tur));
      const sonTur = es.filter(e => e.tur === enUst);
      for (const e of es) {
        const tff = tffTur(e.ms.at(-1).tur);
        if (grupMu) e.ad = "Play-off grubu";
        else if (tff) e.ad = tff;
        else if (es.length === 1) {
          const g = [...takimlar].map(t => grupOf.get(t));
          e.ad = g[0] && g[1] && g[0] !== g[1] ? "Final" : "Eşleşme";
        } else if (e.tur === enUst) e.ad = sonTur.length === 2 && !e.onceKazandi && sonTur.some(x => x.onceKazandi) ? "3.lük maçı" : "Final";
        else e.ad = enUst - e.tur === 1 ? "Yarı final" : enUst - e.tur === 2 ? "Çeyrek final" : `${e.tur}. tur`;
      }
      // grup adı: ağaçtaki takımların normal sezon grubu tekse
      const gruplar = new Set([...takimlar].map(t => grupOf.get(t)).filter(Boolean));
      const tarih = ml.at(-1).tarih;
      return { es, baslik: gruplar.size === 1 ? `${[...gruplar][0]} play-off'u` : null, tarih };
    }).sort((a, b) => (a.baslik || "").localeCompare(b.baslik || "", "tr", { numeric: true }) || a.tarih.localeCompare(b.tarih));
    const SIRA = ["1. tur", "2. tur", "3. tur", "Çeyrek final", "Yarı final", "3.lük maçı", "Final", "Eşleşme", "Play-off grubu"];
    const bolumHtml = b => {
      const turlar = new Map();
      for (const e of b.es) (turlar.get(e.ad) || turlar.set(e.ad, []).get(e.ad)).push(...e.ms);
      return [...turlar].sort((x, y) => SIRA.indexOf(x[0]) - SIRA.indexOf(y[0]) || x[1][0].tarih.localeCompare(y[1][0].tarih))
        .map(([ad, l2]) => `<div class="po-tur"><span class="rozet${ad === "Final" ? " final" : ""}">${esc(ad)}</span>${macListesi(l2.sort((a, c) => a.tarih.localeCompare(c.tarih)))}</div>`).join("");
    };
    return `<div class="kart" style="margin-bottom:12px"><h3>${esc(lig)}</h3>${bolumler.map((b, i) =>
      `${bolumler.length > 1 ? `<h4 class="po-agac">${esc(b.baslik || `${i + 1}. eşleşme ağacı`)}</h4>` : ""}${bolumHtml(b)}`).join("")}</div>`;
  }).join("");
}

function macListesi(ms) {
  if (!ms.length) return `<div class="bos">Maç yok.</div>`;
  return `<div style="overflow-x:auto"><table class="tablo mac-liste"><tbody>${ms.map(m => `<tr><td class="soluk">${tarihYaz(m.tarih)}</td>
    <td class="ad" style="text-align:right">${kulupBag(m.ev, m.evAd)}</td><td class="o skor">${skorBag(m.id, skorYaz(m.eg, m.dg, m.ep, m.dp, m.durum))}</td><td class="ad">${kulupBag(m.dep, m.depAd)}</td></tr>`).join("")}</tbody></table></div>`;
}

// ---------------------------------------------------------------- tüm zamanlar rekorları
const SERI_AD = {
  yenilmez: ["Yenilmezlik serisi", "Art arda yenilmediği maç"],
  ic_yenilmez: ["İç sahada yenilmezlik", "İç sahada art arda yenilmediği maç"],
  dis_yenilmez: ["Deplasmanda yenilmezlik", "Deplasmanda art arda yenilmediği maç"],
  galibiyet: ["Galibiyet serisi", "Art arda kazandığı maç"],
  galibiyetsiz: ["Galibiyetsiz seri", "Art arda kazanamadığı maç"],
  golyemeden: ["Gol yemeden seri", "Kalesini art arda gole kapattığı maç"],
  golsuz: ["Gol atamama serisi", "Art arda gol atamadığı maç"],
};
const rekorDurum = { tablo: 20, acik: new Set() };

async function rekorlarSayfa(kap) {
  document.title = `${BOLUM === "kadin" ? "Kadın futbolu rekorları" : "Tüm zamanlar rekorları"} · Türk Futbol Arşivi`;
  icerik.innerHTML = `<div class="yukleniyor">Rekorlar yükleniyor…</div>`;
  const [R, TR] = await Promise.all([al(`${V}rekorlar.json?s=${OZET.surum || ""}`), al(`${V}tff/rekor.json?s=${OZET.surum || ""}`).catch(() => null)]);
  if (!R.veri[kap]) kap = R.kapsamlar[0][0];   // eski önbellekteki dosyada olmayan sekme
  const v = R.veri[kap];
  const kapAd = Object.fromEntries(R.kapsamlar)[kap];
  if (!v.tablo) v.tablo = null;
  const lig = kap !== "kupa";
  const sira = (l, f) => { let r = 0, onceki; return l.map((x, i) => { const d = f(x); if (d !== onceki) { r = i + 1; onceki = d; } return r; }); };

  const macTablo = (l, id) => {
    const r = sira(l, m => id === "gollu" ? m[8] + m[9] : `${Math.abs(m[8] - m[9])}|${Math.max(m[8], m[9])}`);
    const acik = rekorDurum.acik.has(id), n = acik ? l.length : 10;
    return `<div class="tablo-kap rekor-tablo-kap"><table class="tablo rekor-tablo"><tbody>${l.slice(0, n).map((m, i) => `<tr>
      <td class="s sira">${r[i]}</td><td class="tarih">${tarihYaz(m[0])}<br><a class="bag" href="#/${K}sezon/${m[1]}">${esc(m[1])}</a></td>
      <td class="ad" style="text-align:right" title="${esc(m[5])}">${kulupBag(m[4], m[5])}</td><td class="o skor">${skorBag(m[13], skorYaz(m[8], m[9], m[10], m[11], m[12]))}</td><td class="ad" title="${esc(m[7])}">${kulupBag(m[6], m[7])}</td>
      <td class="ek soluk" style="font-size:13px">${esc(m[2] || "")}${m[3] ? ` · ${esc(m[3])}` : ""}</td></tr>`).join("")}</tbody></table></div>
      ${l.length > 10 ? `<button class="dugme daha" data-ac="${id}">${acik ? "Daha az göster" : `İlk ${l.length}'i göster`}</button>` : ""}`;
  };
  const seriKart = k => {
    const l = v.seriler[k] || [], r = sira(l, s => s[1]);
    const acik = rekorDurum.acik.has(k), n = acik ? l.length : 10;
    return `<div class="kart rekor-kart"><h3>${SERI_AD[k][0]}</h3><p class="soluk aciklama">${SERI_AD[k][1]}</p>
      <ol class="sirali">${l.slice(0, n).map((s, i) => `<li><span class="sira">${r[i]}</span><span class="kim">${kulupBag(s[0])}
        <small class="soluk">${tarihYaz(s[2])} – ${s[6] ? "<b>sürüyor</b>" : tarihYaz(s[3])}</small></span>
        <b class="n">${s[1]}</b></li>`).join("") || `<li class="soluk">—</li>`}</ol>
      ${l.length > 10 ? `<button class="dugme daha" data-ac="${k}">${acik ? "Daha az" : `İlk ${l.length}`}</button>` : ""}</div>`;
  };
  const sayimKart = (id, baslik, aciklama, l) => {
    const r = sira(l, x => x[1]);
    const acik = rekorDurum.acik.has(id), n = acik ? l.length : 10;
    return `<div class="kart rekor-kart"><h3>${baslik}</h3><p class="soluk aciklama">${aciklama}</p>
      <ol class="sirali">${l.slice(0, n).map((x, i) => `<li><span class="sira">${r[i]}</span><span class="kim">${kulupBag(x[0])}
        <small class="soluk">${sayiYaz(x[2])} maçta · %${yuzde(x[1], x[2])}</small></span><b class="n">${sayiYaz(x[1])}</b></li>`).join("")}</ol>
      ${l.length > 10 ? `<button class="dugme daha" data-ac="${id}">${acik ? "Daha az" : `İlk ${l.length}`}</button>` : ""}</div>`;
  };
  // bir maçta en çok gol atan futbolcular (TFF maç sayfaları, 1991-92'den)
  const golKap = { tum: x => true, kupa: x => x[8] === "K", pro: x => x[8] === "L", 1: x => x[8] === "L" && x[9] === 1, 2: x => x[8] === "L" && x[9] === 2, 3: x => x[8] === "L" && x[9] === 3, 4: x => x[8] === "L" && x[9] === 4 };
  const oyuncuGol = () => {
    if (!TR) return "";
    const l = TR.mac_gol.filter(golKap[kap] || (() => false));
    if (!l.length) return "";
    const r = sira(l, x => x[2]), acik = rekorDurum.acik.has("oygol");
    let n = acik ? l.length : 10;
    if (!acik) while (n < l.length && n < 25 && l[n][2] === l[n - 1][2] && r[n] === r[n - 1]) n++;   // 10. sıradaki eşitlikler
    return `<h2 class="bolum">Bir maçta en çok gol atan futbolcular</h2>
    <div class="tablo-kap rekor-tablo-kap"><table class="tablo rekor-tablo"><tbody>${l.slice(0, n).map((x, i) => `<tr>
      <td class="s sira">${r[i]}</td><td class="tarih">${tarihYaz(x[4])}<br><a class="bag" href="#/${K}sezon/${x[5]}">${esc(x[5])}</a></td>
      <td class="ad"><a class="bag" href="#/${K}oyuncu/k${x[0]}">${esc(x[1])}</a><br><small class="soluk">${kulupBag(x[6])}</small></td>
      <td class="o"><b>${x[2]}</b> gol</td><td class="ad"><small class="soluk">Rakip</small> ${kulupBag(x[7])} <small>${skorBag(x[3], "· maç")}</small></td>
      <td class="ek soluk" style="font-size:13px">${esc(x[8] === "L" ? KADEME_AD[x[9]] || "Lig" : YAR_AD[x[8]] || "")}${x[10] ? " · play-off" : ""}</td></tr>`).join("")}</tbody></table></div>
    ${l.length > n ? `<button class="dugme daha" data-ac="oygol">${acik ? "Daha az göster" : `${sayiYaz(l.length)} maçın hepsini göster (3+ gol)`}</button>` : acik ? `<button class="dugme daha" data-ac="oygol">Daha az göster</button>` : ""}
    <p class="soluk not">Kaynak: ${BOLUM === "kadin" ? `${KADIN_KAYNAK}. Kendi kalesine goller hariç, penaltı golleri dahil.` : `TFF maç sayfaları — lig 1991-92'den, Türkiye Kupası 1991-2007${MK_NOT()}. Kendi kalesine goller hariç, penaltı golleri dahil.`}</p>`;
  };
  const tablo = () => {
    const l = v.tablo, n = Math.min(rekorDurum.tablo, l.length);
    return `<div class="tablo-kap"><table class="tablo"><thead><tr><th class="s">#</th><th>Kulüp</th><th class="s" title="Sezon">Sz</th><th class="s">O</th><th class="s">G</th><th class="s">B</th><th class="s">M</th>
      <th class="s">AG</th><th class="s">YG</th><th class="s">Av</th><th class="s">P</th></tr></thead>
      <tbody>${l.slice(0, n).map((x, i) => `<tr><td class="s">${i + 1}</td><td class="ad">${kulupBag(x[0])}</td><td class="s">${x[1]}</td><td class="s">${sayiYaz(x[2])}</td>
        <td class="s">${sayiYaz(x[3])}</td><td class="s">${sayiYaz(x[4])}</td><td class="s">${sayiYaz(x[5])}</td><td class="s">${sayiYaz(x[6])}</td><td class="s">${sayiYaz(x[7])}</td>
        <td class="s">${x[6] - x[7] > 0 ? "+" : ""}${sayiYaz(x[6] - x[7])}</td><td class="s"><b>${sayiYaz(x[8])}</b></td></tr>`).join("")}</tbody></table></div>
      ${l.length > n ? `<button class="dugme daha" data-tablo="1">${sayiYaz(l.length - n)} kulüp daha göster</button>` : ""}`;
  };

  const ciz = () => {
    icerik.innerHTML = `
    ${BOLUM_UST[BOLUM] ? `${BOLUM_UST[BOLUM]("rekorlar")}<h2>Tüm zamanlar rekorları</h2>` : "<h1>Tüm zamanlar rekorları</h1>"}
    <nav class="sekmeler">${R.kapsamlar.map(([k, ad]) => `<a href="#/${K}rekorlar/${k}" class="${k === kap ? "aktif" : ""}">${esc(ad)}</a>`).join("")}</nav>
    <p class="soluk">${esc(kapAd)} · ${esc(v.sezon[0])} – ${esc(v.sezon[1])} · ${sayiYaz(v.mac)} maç.
      ${kap === "pro" ? `Bütün lig seviyeleri bir arada: bir kulübün ${esc(KADEME_AD[1])}'nden alt lige geçişi seriyi bozmaz.` : ""}</p>

    ${v.tablo ? `<h2 class="bolum">Tüm zamanlar tablosu</h2>
    <p class="soluk not">Galibiyet bütün sezonlar için 3 puan sayıldı. ${lig ? "Play-off maçları ve puan silme cezaları dahil değil; hükmen sonuçlar dahil." : "Uzatmada biten maçlar skora göre, penaltıyla biten maçlar beraberlik sayıldı."}</p>
    ${tablo()}` : `<p class="soluk not">Bütün lig seviyeleri ve Türkiye Kupası birlikte. Seriler ve tablolar her yarışma için ayrı sekmelerde.</p>`}

    <h2 class="bolum">Maç rekorları</h2>
    <div class="izgara genis">
      <div><h3>En farklı galibiyetler</h3>${macTablo(v.fark, "fark")}</div>
      <div><h3>En gollü maçlar</h3>${macTablo(v.gollu, "gollu")}</div>
      <div><h3>Deplasmanda en farklı galibiyetler</h3>${macTablo(v.dep_fark, "dep_fark")}</div>
    </div>
    ${oyuncuGol()}

    ${v.seriler ? `<h2 class="bolum">Seriler</h2>
    <div class="izgara k3">${["yenilmez", "ic_yenilmez", "dis_yenilmez", "galibiyetsiz", "galibiyet", "golyemeden", "golsuz"].map(seriKart).join("")}</div>

    <h2 class="bolum">Toplam maç sayıları</h2>
    <div class="izgara k2">
      ${sayimKart("gy", "Kalesini en çok gole kapatanlar", "Gol yemediği maç sayısı", v.golyemedi)}
      ${sayimKart("gs", "En çok maçta gol atamayanlar", "Gol atamadığı maç sayısı", v.golatamadi)}
    </div>` : ""}
    <p class="soluk not bolum">Seriler kulübün bu kapsamdaki maçlarının tarih sırasıyla sayılır ve sezonlar arası sürer; kulüp bir sezon bu kapsamda yer almazsa seri kesilir.
      Hükmen sonuçlar ile tarihi bilinmeyen maçlar serilere, maç rekorlarına ve gol sayımlarına girmez. Kulüpler bugünkü adlarıyla, maçlar dönemin adlarıyla gösterilir.
      Eski sezonlardaki çok farklı skorlar kaynaklarda yazdığı gibidir.</p>`;
    icerik.querySelectorAll("[data-ac]").forEach(b => b.addEventListener("click", () => {
      const k = b.dataset.ac; rekorDurum.acik.has(k) ? rekorDurum.acik.delete(k) : rekorDurum.acik.add(k);
      const y = scrollY; ciz(); scrollTo(0, y);
    }));
    const nav = icerik.querySelector(".sekmeler"), ak = nav.querySelector(".aktif");
    nav.scrollLeft = ak.offsetLeft - (nav.clientWidth - ak.offsetWidth) / 2;
    icerik.querySelector("[data-tablo]")?.addEventListener("click", () => { rekorDurum.tablo += 100; const y = scrollY; ciz(); scrollTo(0, y); });
  };
  rekorDurum.tablo = 20;
  ciz();
}

// ---------------------------------------------------------------- hakkında
function hakkindaSayfa() {
  document.title = "Hakkında · Türk Futbol Arşivi";
  const eksik = OZET.kapsam.filter(k => k[4] !== k[5]).length;
  icerik.innerHTML = `<div style="max-width:760px">
  <h1>Veri hakkında</h1>
  <p>Bu arşiv, Türkiye'de 1959'dan bu yana oynanan profesyonel lig maçlarını, terfi maçlarını, Türkiye Kupası'nı ve Türk kulüplerinin resmi Avrupa kupası maçlarını bir araya getirir. Toplam <b>${sayiYaz(OZET.mac)}</b> maç ve <b>${sayiYaz(OZET.kulup)}</b> kulüp var. En son maç tarihi ${tarihYaz(OZET.son_tarih)}.</p>
  <h2 class="bolum">Kaynaklar</h2>
  <ul>
    <li><b>TFF</b>: 1984-85'ten bugüne Süper Lig, 1990-91'den bugüne alt ligler ve 1994-95'ten sonraki kupa eşleşmeleri.</li>
    <li><b>Maçkolik</b> (yeni site ve arşiv): 1959-1990 arası ligler, Türkiye Kupası ve Avrupa kupaları.</li>
    <li><b>RSSSF ve Vikipedi</b>: 1995-2003 Intertoto maçları; kulüp ardıllıkları ve eski adlar; 1966'dan bugüne Cumhurbaşkanlığı (1981-82'de Devlet Başkanlığı) Kupası, TFF Süper Kupa ve Başbakanlık Kupası maçları (1991-2006 arası TFF maç sayfalarından).</li>
    <li><b>Kulüp logoları</b>: Football Manager topluluk logo paketi (TCM), kulüplerin bugünkü logoları; FM kimlikleri Sortitoutsi'den eşlendi; pakette olmayan kulüplerde Türkçe Vikipedi'deki arma. Kadın kulüplerinde erkek takımıyla aynı kulüpse onun logosu, değilse TFF maç sayfalarındaki kulüp logosu. Logolar kulüplerin tescilli markasıdır.</li>
  </ul>
  <h2 class="bolum">Kulüpler nasıl eşlendi</h2>
  <p>Her kulüp TFF kulüp numarasına göre tanımlanır. 1990 öncesi kayıtlar, puan tablosu imzası ve ad benzerliğiyle TFF numarasına bağlandı. Aynı adı taşıyan ama farklı olan kulüpler (ör. 1984 Muşspor ile 2015 Muşspor) ayrı tutulur; bir kulübün yerine kurulan ya da hakkını devralan kulüp "ardıl" olarak gösterilir. Maçlarda takımın o dönemki adı yazar.</p>
  <h2 class="bolum">Bilinen sınırlar</h2>
  <ul>
    <li>Puan tabloları maç sonuçlarından hesaplanır; puan silme cezaları ve averaj kuralları dahil değildir.</li>
    <li>Ankara, İstanbul ve İzmir mahalli ligleri kapsam dışıdır.</li>
    <li>Lig gruplarının ${OZET.kapsam.length - eksik} / ${OZET.kapsam.length} tanesinde maç sayısı tam; kalanlar ligden çekilen takımlar, dört devreli gruplar ya da lig içinde oynanan play-off maçlarıdır.</li>
    <li>Oyuncu, gol ve kart bilgisi henüz yok.</li>
  </ul></div>`;
}

// ---------------------------------------------------------------- başlat
(async function basla() {
  try {
    OZET = await al("data/ozet.json", { cache: "no-cache" });   // sürüm anahtarı: veri dosyaları eski önbellekten gelmesin
    KULUPLER = await al(`data/kulupler.json?s=${OZET.surum || ""}`);
  } catch (e) {
    icerik.innerHTML = `<div class="bos">Veri yüklenemedi (${esc(e.message)}). Sayfayı bir web sunucusu üzerinden açın.</div>`;
    return;
  }
  for (const k of KULUPLER) { adSadele(k); KULUP.set(k.id, k); }
  aramaIndeksi();
  oneriKutusu($("#ustAra"), $("#ustOneri"), k => { location.hash = `#/kulup/${k.id}`; $("#ustAra").value = ""; });
  yonlendir();
})();

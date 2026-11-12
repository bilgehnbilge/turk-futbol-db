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
const YAR_AD = { L: "Lig", K: "Türkiye Kupası", A: "Avrupa", T: "Terfi" };
const KADEME_AD = { 1: "Süper Lig", 2: "1. Lig", 3: "TFF 2. Lig", 4: "TFF 3. Lig" };   // bugünkü adlar, seviyeye göre

async function al(yol, secenek) {
  if (onbellek.has(yol)) return onbellek.get(yol);
  const p = fetch(yol, secenek).then(r => { if (!r.ok) throw new Error(yol + " " + r.status); return r.json(); });
  onbellek.set(yol, p);
  try { return await p; } catch (e) { onbellek.delete(yol); throw e; }
}
const kulupAd = id => KULUP.get(id)?.ad ?? "?";
const logoImg = (id, cls = "logo-k") => { const l = KULUP.get(id)?.logo; return l ? `<img class="${cls}" src="logo/${l}.png" alt="" loading="lazy" onerror="this.remove()">` : ""; };
const kulupBag = (id, ad) => id != null && KULUP.has(id) ? `<a class="bag" href="#/kulup/${id}">${logoImg(id)}${esc(ad ?? kulupAd(id))}</a>` : esc(ad ?? "?");
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
function kulupAltYazi(k) {
  const yil = `${k.ilk.slice(0, 4)}–${k.son.slice(0, 4)}`;
  if (!k.yerli) return `Avrupa rakibi · ${k.mac} maç`;
  return `${yil} · ${sayiYaz(k.mac)} maç${k.enust === 1 ? " · Süper Lig" : ""}`;
}
function oneriKutusu(input, kutu, secince) {
  let secili = -1, liste = [];
  const ciz = () => {
    liste = kulupAra(input.value, 10);
    if (!liste.length) { kutu.hidden = true; return; }
    kutu.innerHTML = liste.map((k, i) => `<a href="#/kulup/${k.id}" data-i="${i}" class="${i === secili ? "sec" : ""}">
      <span>${logoImg(k.id)}${esc(k.ad)}${eskiAdIpucu(k, input.value)}</span><small>${esc(kulupAltYazi(k))}</small></a>`).join("");
    kutu.hidden = false;
  };
  input.addEventListener("input", () => { secili = -1; ciz(); });
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
  [/^#\/karsilastir$/, karsilastirSayfa],
  [/^#\/hakkinda$/, hakkindaSayfa],
];
async function yonlendir() {
  const h = location.hash || "#/";
  document.querySelectorAll(".ust nav a").forEach(a => a.classList.toggle("aktif", h.startsWith(a.getAttribute("href"))));
  temaUygula(null);
  for (const [re, f] of yollar) {
    const m = h.match(re);
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
    <div class="buyuk-ara"><input id="anaAra" type="search" placeholder="Kulüp adı ya da eski adı yaz…" autocomplete="off" autofocus><div id="anaOneri" class="oneri" hidden></div></div>
    <div class="cipler" style="justify-content:center;margin-top:16px">${ornek.map(a => { const k = kulupAra(a, 1)[0]; return k ? `<a class="cip" href="#/kulup/${k.id}">${esc(a)}</a>` : ""; }).join("")}</div>
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
    <a class="kart" href="#/rekorlar"><h3>Tüm zamanlar rekorları →</h3><p class="soluk">En farklı skorlar, en uzun seriler ve tüm zamanlar puan tabloları.</p></a>
    <a class="kart" href="#/karsilastir"><h3>İki kulübü karşılaştır →</h3><p class="soluk">Aralarındaki bütün maçlar ve genel denge.</p></a>
    <a class="kart" href="#/hakkinda"><h3>Veri hakkında →</h3><p class="soluk">Kaynaklar, kapsam ve bilinen sınırlar.</p></a>
  </section>`;
  oneriKutusu($("#anaAra"), $("#anaOneri"), k => location.hash = `#/kulup/${k.id}`);
}

// ---------------------------------------------------------------- kulüp verisi
async function kulupMaclari(id) {
  const d = await al(`data/kulup/${id}.json`);
  return d.maclar.map(r => ({
    id: r[0], tarih: r[1], sezon: r[2], yar: r[3], lig: r[4], kademe: r[5], tur: r[6], po: r[7] === "p", saha: r[8],
    takim: r[9], rakipId: r[10], rakip: r[11], a: r[12], y: r[13], pa: r[14], py: r[15], durum: r[16], not: r[17], kulup: id,
    iptal: r[7] === "x", s: r[7] === "x" ? "N" : sonuc(r[12], r[13]),   // geçersiz maç istatistiğe girmez
  }));
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
  const oynanan = ms.filter(m => m.s !== "N" && m.tarih);   // tarihsiz hükmen maçlar sıralanamaz
  return tanim.map(([k, ad, f]) => {
    let en = { n: 0 }, cur = { n: 0 };
    for (let i = 0; i < oynanan.length; i++) {
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
      <a class="dugme" href="#/karsilastir" data-a="${id}" id="karsBtn">Karşılaştır</a>
    </div>
  </section>
  ${ardilHtml}
  <div class="kulup-sekme"><nav class="sekmeler">
    ${[["ozet", "Özet"], ["rekorlar", "Rekorlar ve seriler"], ["maclar", "Maçlar"], ["rakipler", "Rakipler"], ["sezonlar", "Sezon sezon"]]
      .map(([s, ad]) => `<a href="#/kulup/${id}/${s}" class="${s === sekme ? "aktif" : ""}">${ad}</a>`).join("")}
  </nav></div>
  <div id="filtreAlan"></div>
  <div id="sekmeIcerik"></div>`;
  $("#karsBtn").addEventListener("click", () => { karsilastirSecim.a = id; });

  const ciz = () => {
    $("#filtreAlan").innerHTML = filtreHtml(durum, tum, sekme, onculler);
    filtreBagla(durum, () => { kulupSayfa(id, sekme); }, ciz);
    const ms = filtrele(tum, durum, sekme);
    const hedef = $("#sekmeIcerik");
    if (sekme === "ozet") hedef.innerHTML = ozetHtml(tum, durum);
    else if (sekme === "rekorlar") hedef.innerHTML = rekorHtml(ms);
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
    <div class="cipler">${cip("Tümü", "", "yar")}${["L", "K", "A", "T"].filter(y => yarlar.includes(y)).map(y => cip(YAR_AD[y], y, "yar")).join("")}</div>
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
  const bolumler = [["", "Bütün resmi maçlar"], ["L", "Lig"], ["K", "Türkiye Kupası"], ["A", "Avrupa kupaları"], ["T", "Terfi maçları"]];
  const kartlar = bolumler.map(([y, ad]) => {
    const alt = ms.filter(m => !y || m.yar === y); if (!alt.length) return "";
    return `<div class="kart"><h3>${ad}</h3>${ozetSatir(toplam(alt))}</div>`;
  }).join("");
  const son = ms.filter(m => m.s !== "N").slice(-10).reverse();
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
  <div class="bolum izgara k2">
    <div class="kart"><h3>Liglerde geçirdiği sezonlar</h3>
      ${Object.keys(ligBas).sort().map(ligSatiri).join("") || `<p class="soluk">Lig maçı yok.</p>`}
      <p class="soluk" style="font-size:12px;margin-top:10px">Ligler bugünkü adlarıyla, seviyeye göre gösterilir (Süper Lig = en üst lig).</p>
    </div>
    <div class="kart"><h3>Son maçlar</h3>
      ${son.map(m => `<div class="son-satir"><span class="son ${m.s}">${m.s}</span>
        <span class="tarih">${tarihYaz(m.tarih)}</span><span class="rakip">${kulupBag(m.rakipId, m.rakip)}${m.saha === "E" ? "" : ` <small class="soluk" title="Deplasman">(D)</small>`}</span>
        <b class="skor">${skorYaz(m.a, m.y, m.pa, m.py, m.durum)}</b></div>`).join("")}
    </div>
  </div>`;
}

function macSatir(m, gosterTakim) {
  return `<tr><td class="o"><span class="son ${m.s}">${m.s === "N" ? "–" : m.s}</span></td>
    <td>${tarihYaz(m.tarih)}</td><td><a class="bag" href="#/sezon/${m.sezon}">${esc(m.sezon)}</a></td>
    <td class="gizle-mobil">${esc(m.lig || YAR_AD[m.yar])}${m.tur ? ` <span class="soluk">· ${esc(m.tur)}</span>` : ""}${m.po ? ` <span class="rozet">play-off</span>` : ""}${m.iptal ? ` <span class="rozet" title="${esc(m.not || "")}">sayılmadı</span>` : ""}</td>
    ${gosterTakim ? `<td class="ad">${logoImg(m.kulup)}${esc(m.takim)}</td>` : ""}
    <td class="o">${m.saha === "E" ? "İç" : "Dış"}</td>
    <td class="ad">${kulupBag(m.rakipId, m.rakip)}</td>
    <td class="s skor">${skorYaz(m.a, m.y, m.pa, m.py, m.durum)}</td></tr>`;
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
  const ad = (id, ad) => id !== m.kulup && id != null && KULUP.has(id) ? `<a class="bag" href="#/kulup/${id}">${esc(ad)}</a>` : `<span>${esc(ad)}</span>`;
  const [evId, evAd, depId, depAd, eg, dg, ep, dp] = m.saha === "E" ? [m.kulup, m.takim, m.rakipId, m.rakip, m.a, m.y, m.pa, m.py] : [m.rakipId, m.rakip, m.kulup, m.takim, m.y, m.a, m.py, m.pa];
  const skor = m.durum === "Çifte H" ? "0-3 / 3-0" : eg == null ? "–" : `${eg} - ${dg}`;
  const ek = ep != null && dp != null ? ` <small class="soluk">(pen ${ep}-${dp})</small>` : m.durum === "Hük." ? ` <small class="soluk">(H)</small>` : "";
  return `<div class="tabela${sonucGoster ? " sonuclu" : ""}" title="${esc(m.lig || YAR_AD[m.yar])}${m.tur ? " · " + esc(m.tur) : ""}">
    ${sonucGoster ? `<span class="son ${m.s}">${m.s === "N" ? "–" : m.s}</span>` : ""}
    <span class="tarih">${tarihYaz(m.tarih)}</span>
    <span class="ev">${logoImg(evId)}${ad(evId, evAd)}</span>
    <b class="skor">${skor}${ek}</b>
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
function rekorHtml(ms) {
  if (!ms.filter(m => m.s !== "N").length) return `<div class="bos">Bu filtreye uyan maç yok.</div>`;
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
      ${enSezon.map(x => `<span class="detay"><a class="bag" href="#/sezon/${x.sezon}">${x.sezon}</a>: <b>${x.GY}</b> / ${x.O} maç</span>`).join("") || `<span class="soluk">—</span>`}</div>`;
  return `
  <h2>Kalesini gole kapattığı maçlar</h2>
  <div class="izgara iki ust-hiza">${gyKart}${seriKart(sr.find(s => s.k === "golyemeden"))}</div>
  <h2 class="bolum">En farklı sonuçlar</h2>
  <div class="izgara iki ust-hiza">${rekorKart("En farklı galibiyet", gal)}${rekorKart("En farklı mağlubiyet", mag)}${rekorKart("En gollü maç", gol)}
  ${rekorKart("İç sahada en farklı galibiyet", evG)}${rekorKart("Deplasmanda en farklı galibiyet", depG)}</div>
  <h2 class="bolum">Seriler <small class="soluk" style="font-weight:400;font-size:14px">— seçili maçlar art arda, sezonlar arası; ayrıntı için karta tıkla</small></h2>
  <div class="izgara iki ust-hiza">${sr.map(seriKart).join("")}</div>
  <p class="soluk" style="font-size:13px;margin-top:16px">Seriler seçili filtredeki maçların tarih sırasıyla hesaplanır. Penaltıyla biten kupa maçları beraberlik sayılır. "İç saha" seçilirse ev sahibi yenilmezlik serisi gibi kayıtlar çıkar.</p>`;
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
      <td>${x.id != null ? `<a class="bag" href="#/h2h/${id}/${x.id}">maçlar →</a>` : ""}</td></tr>`).join("")}</tbody></table></div>`;
    hedef.querySelectorAll("th.sirala").forEach(th => th.addEventListener("click", () => { if (sira === th.dataset.k) ters = !ters; else { sira = th.dataset.k; ters = sira !== "ad"; } ciz(); }));
    const i = $("#rAra"); i.addEventListener("input", e => { ara = e.target.value; clearTimeout(i._t); i._t = setTimeout(() => { ciz(); const n = $("#rAra"); n.focus(); n.setSelectionRange(n.value.length, n.value.length); }, 200); });
  };
  ciz();
}

function sezonSezonHtml(ms) {
  const s = new Map();
  for (const m of ms) {
    const x = s.get(m.sezon) || { sezon: m.sezon, ligler: new Map(), kupa: [], avrupa: [] };
    if (m.yar === "L" || m.yar === "T") {
      const key = `${m.lig}|${m.tur}|${m.yar}`;
      const l = x.ligler.get(key) || { lig: m.lig, grup: m.yar === "T" ? m.tur || "Terfi" : m.tur, kademe: m.kademe, yar: m.yar, ms: [] };
      if (!m.po) l.ms.push(m); x.ligler.set(key, l);
    } else if (m.yar === "K") x.kupa.push(m); else if (m.yar === "A") x.avrupa.push(m);
    s.set(m.sezon, x);
  }
  const satirlar = [...s.values()].sort((a, b) => b.sezon.localeCompare(a.sezon)).map(x => {
    const ligler = [...x.ligler.values()].filter(l => l.ms.length).map(l => {
      const t = toplam(l.ms), p = puan(x.sezon);
      return `<div>${esc(l.lig)}${l.grup ? ` <span class="soluk">· ${esc(l.grup)}</span>` : ""}: <b>${t.O}</b> maç ${t.G}-${t.B}-${t.M}, ${t.AG}:${t.YG}${l.yar === "L" ? `, <b>${t.G * p + t.B}</b> puan` : ""}</div>`;
    }).join("");
    const kupaSon = x.kupa.filter(m => m.s !== "N").at(-1);
    return `<tr><td><a class="bag" href="#/sezon/${x.sezon}">${x.sezon}</a></td><td class="ad">${ligler || `<span class="soluk">—</span>`}</td>
      <td class="ad gizle-mobil">${kupaSon ? `${esc(kupaSon.tur || "")} <span class="soluk">(${x.kupa.length} maç)</span>` : ""}</td>
      <td class="ad gizle-mobil">${x.avrupa.length ? `${esc(x.avrupa[0].lig)} <span class="soluk">(${x.avrupa.length} maç)</span>` : ""}</td></tr>`;
  }).join("");
  return `<p class="soluk" style="font-size:13px">Puanlar maç sonuçlarından hesaplanmıştır (1987-88 öncesi galibiyet 2 puan). Puan silme cezaları dahil değildir. Sezona tıklayınca o sezonun puan tablosu açılır.</p>
  <div class="tablo-kap"><table class="tablo"><thead><tr><th>Sezon</th><th>Lig</th><th class="gizle-mobil">Kupada son tur</th><th class="gizle-mobil">Avrupa</th></tr></thead><tbody>${satirlar}</tbody></table></div>`;
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
    <div class="yan-yana" style="margin-bottom:12px"><h1 style="margin:0">${kulupBag(a)}</h1><span class="vs">vs</span><h1 style="margin:0">${kulupBag(b)}</h1></div>
    <p class="soluk">${ms.length ? `${tarihYaz(ms[0].tarih)} ile ${tarihYaz(ms.at(-1).tarih)} arasında ${ms.length} resmi maç` : "Aralarında kayıtlı maç yok."}</p>
    <div class="filtre"><div class="cipler">${[["", "Tümü"], ["L", "Lig"], ["K", "Kupa"], ["A", "Avrupa"]].map(([v, ad]) => `<button class="cip ${d.yar === v ? "aktif" : ""}" data-y="${v}">${ad}</button>`).join("")}</div>
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
      return `<tr><td class="o"><span class="son ${m.s}">${m.s === "N" ? "–" : m.s}</span></td><td>${tarihYaz(m.tarih)}</td><td><a class="bag" href="#/sezon/${m.sezon}">${m.sezon}</a></td>
        <td class="gizle-mobil">${esc(m.lig || "")}${m.tur ? ` <span class="soluk">· ${esc(m.tur)}</span>` : ""}</td><td class="ad">${ev}</td><td class="s skor">${sk}</td><td class="ad">${dep}</td></tr>`;
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
    <div class="kart"><h3>1. kulüp</h3><div style="position:relative"><input id="kA" type="search" placeholder="Kulüp ara…" autocomplete="off"><div id="oA" class="oneri" hidden></div></div><p id="sA" class="soluk"></p></div>
    <div class="kart"><h3>2. kulüp</h3><div style="position:relative"><input id="kB" type="search" placeholder="Kulüp ara…" autocomplete="off"><div id="oB" class="oneri" hidden></div></div><p id="sB" class="soluk"></p></div>
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
}

// ---------------------------------------------------------------- sezonlar
function sezonlarSayfa() {
  document.title = "Sezonlar · Türk Futbol Arşivi";
  const on = new Map();
  for (const s of [...OZET.sezonlar].reverse()) { const d = s.slice(0, 3) + "0"; (on.get(d) || on.set(d, []).get(d)).push(s); }
  icerik.innerHTML = `<h1>Sezonlar</h1><p class="soluk">Puan tabloları maç sonuçlarından hesaplanır.</p>
    ${[...on].map(([d, ss]) => `<div class="on-dekad">${d}'lar</div><div class="sezon-izgara">${ss.map(s => `<a href="#/sezon/${s}">${s}</a>`).join("")}</div>`).join("")}`;
}
async function sezonSayfa(sezon) {
  document.title = `${sezon} · Türk Futbol Arşivi`;
  icerik.innerHTML = `<div class="yukleniyor">${esc(sezon)} yükleniyor…</div>`;
  const d = await al(`data/sezon/${sezon}.json`);
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
      <tbody>${l.map((x, i) => `<tr><td class="s soluk">${i + 1}</td><td class="takim" title="${esc(x.ad)}">${typeof x.id === "number" ? kulupBag(x.id, x.ad) : esc(x.ad)}</td><td class="s">${x.O}</td><td class="s ek2">${x.G}</td><td class="s ek2">${x.B}</td><td class="s ek2">${x.M}</td><td class="s ek">${x.AG}</td><td class="s ek">${x.YG}</td><td class="s">${x.Av > 0 ? "+" : ""}${x.Av}</td><td class="s p">${x.P}</td></tr>`).join("")}</tbody></table>
      <details><summary>Maçlar</summary>${macListesi(g.ms)}</details></div>`;
  };
  const kupa = ms.filter(m => m.yar === "K"), avrupa = ms.filter(m => m.yar === "A"), po = ms.filter(m => (m.yar === "L" || m.yar === "T") && m.po);
  const turlara = l => { const t = new Map(); for (const m of l) (t.get(m.tur || m.lig) || t.set(m.tur || m.lig, []).get(m.tur || m.lig)).push(m); return [...t]; };
  icerik.innerHTML = `
  <div class="sayfa-bas"><h1>${esc(sezon)} sezonu</h1>
    <div class="yan-yana">${onceki ? `<a class="cip" href="#/sezon/${onceki}">← ${onceki}</a>` : ""}${sonraki ? `<a class="cip" href="#/sezon/${sonraki}">${sonraki} →</a>` : ""}</div></div>
  <p class="soluk">${ms.length} maç · Puan tabloları sonuçlardan hesaplandı (galibiyet ${p} puan; puan silme ve averaj kuralı farkları dahil değil).</p>
  <nav class="sekmeler">${sirali.length ? `<a href="#lig" data-k="lig" class="aktif">Lig</a>` : ""}${po.length ? `<a href="#po" data-k="po">Play-off / baraj</a>` : ""}${kupa.length ? `<a href="#kupa" data-k="kupa">Türkiye Kupası</a>` : ""}${avrupa.length ? `<a href="#avrupa" data-k="avrupa">Avrupa</a>` : ""}</nav>
  <div id="sz-lig" class="izgara puan">${sirali.map(tabloHtml).join("") || ""}</div>
  <div id="sz-po" hidden>${macListesi(po)}</div>
  <div id="sz-kupa" hidden>${turlara(kupa).map(([t, l]) => `<div class="kart" style="margin-bottom:12px"><h3>${esc(t)}</h3>${macListesi(l)}</div>`).join("")}</div>
  <div id="sz-avrupa" hidden>${turlara(avrupa.map(m => ({ ...m, tur: `${m.lig}${m.tur ? " · " + m.tur : ""}` }))).map(([t, l]) => `<div class="kart" style="margin-bottom:12px"><h3>${esc(t)}</h3>${macListesi(l)}</div>`).join("")}</div>`;
  const ilk = sirali.length ? "lig" : po.length ? "po" : kupa.length ? "kupa" : "avrupa";
  const goster = k => { ["lig", "po", "kupa", "avrupa"].forEach(x => { const e = $("#sz-" + x); if (e) e.hidden = x !== k; }); icerik.querySelectorAll(".sekmeler a").forEach(a => a.classList.toggle("aktif", a.dataset.k === k)); };
  icerik.querySelectorAll(".sekmeler a").forEach(a => a.addEventListener("click", e => { e.preventDefault(); goster(a.dataset.k); }));
  goster(ilk);
}
function macListesi(ms) {
  if (!ms.length) return `<div class="bos">Maç yok.</div>`;
  return `<div style="overflow-x:auto"><table class="tablo mac-liste"><tbody>${ms.map(m => `<tr><td class="soluk">${tarihYaz(m.tarih)}</td>
    <td class="ad" style="text-align:right">${kulupBag(m.ev, m.evAd)}</td><td class="o skor">${skorYaz(m.eg, m.dg, m.ep, m.dp, m.durum)}</td><td class="ad">${kulupBag(m.dep, m.depAd)}</td></tr>`).join("")}</tbody></table></div>`;
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
  document.title = "Tüm zamanlar rekorları · Türk Futbol Arşivi";
  icerik.innerHTML = `<div class="yukleniyor">Rekorlar yükleniyor…</div>`;
  const R = await al(`data/rekorlar.json?s=${OZET.surum || ""}`);
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
      <td class="s sira">${r[i]}</td><td class="tarih">${tarihYaz(m[0])}<br><a class="bag" href="#/sezon/${m[1]}">${esc(m[1])}</a></td>
      <td class="ad" style="text-align:right" title="${esc(m[5])}">${kulupBag(m[4], m[5])}</td><td class="o skor">${skorYaz(m[8], m[9], m[10], m[11], m[12])}</td><td class="ad" title="${esc(m[7])}">${kulupBag(m[6], m[7])}</td>
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
    <h1>Tüm zamanlar rekorları</h1>
    <nav class="sekmeler">${R.kapsamlar.map(([k, ad]) => `<a href="#/rekorlar/${k}" class="${k === kap ? "aktif" : ""}">${esc(ad)}</a>`).join("")}</nav>
    <p class="soluk">${esc(kapAd)} · ${esc(v.sezon[0])} – ${esc(v.sezon[1])} · ${sayiYaz(v.mac)} maç.
      ${kap === "pro" ? "Bütün lig seviyeleri bir arada: bir kulübün Süper Lig'den alt lige geçişi seriyi bozmaz." : ""}</p>

    ${v.tablo ? `<h2 class="bolum">Tüm zamanlar tablosu</h2>
    <p class="soluk not">Galibiyet bütün sezonlar için 3 puan sayıldı. ${lig ? "Play-off maçları ve puan silme cezaları dahil değil; hükmen sonuçlar dahil." : "Uzatmada biten maçlar skora göre, penaltıyla biten maçlar beraberlik sayıldı."}</p>
    ${tablo()}` : `<p class="soluk not">Bütün lig seviyeleri ve Türkiye Kupası birlikte. Seriler ve tablolar her yarışma için ayrı sekmelerde.</p>`}

    <h2 class="bolum">Maç rekorları</h2>
    <div class="izgara genis">
      <div><h3>En farklı galibiyetler</h3>${macTablo(v.fark, "fark")}</div>
      <div><h3>En gollü maçlar</h3>${macTablo(v.gollu, "gollu")}</div>
      <div><h3>Deplasmanda en farklı galibiyetler</h3>${macTablo(v.dep_fark, "dep_fark")}</div>
    </div>

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
    <li><b>RSSSF ve Vikipedi</b>: 1995-2003 Intertoto maçları; kulüp ardıllıkları ve eski adlar.</li>
    <li><b>Kulüp logoları</b>: Football Manager topluluk logo paketi (TCM), kulüplerin bugünkü logoları; FM kimlikleri Sortitoutsi'den eşlendi. Logolar kulüplerin tescilli markasıdır.</li>
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
    [KULUPLER, OZET] = await Promise.all([al("data/kulupler.json"), al("data/ozet.json", { cache: "no-cache" })]);
  } catch (e) {
    icerik.innerHTML = `<div class="bos">Veri yüklenemedi (${esc(e.message)}). Sayfayı bir web sunucusu üzerinden açın.</div>`;
    return;
  }
  for (const k of KULUPLER) KULUP.set(k.id, k);
  aramaIndeksi();
  oneriKutusu($("#ustAra"), $("#ustOneri"), k => { location.hash = `#/kulup/${k.id}`; $("#ustAra").value = ""; });
  yonlendir();
})();

"use strict";
(() => {   // app.js ile ad çakışmasın diye kapalı kapsam
/* Grafikler: "Sayılarla Türk futbolu" sayfası (#/sayilar) ve kulüp sayfasındaki lig yolculuğu.
   app.js'ten sonra yüklenir; $, esc, al, OZET, KULUP, kulupBag, KADEME_AD, yollar app.js'ten gelir.
   Çizim düz SVG; renkler style.css'teki .viz değişkenlerinden (açık/koyu tema ayrı ayrı doğrulandı). */

const SVGNS = "http://www.w3.org/2000/svg";
const yuzde = (x, b = 1) => (x * 100).toLocaleString("tr-TR", { minimumFractionDigits: b, maximumFractionDigits: b }) + "%";
const ondalik = (x, b = 2) => x.toLocaleString("tr-TR", { minimumFractionDigits: b, maximumFractionDigits: b });
const sezonYil = s => +String(s).slice(0, 4);
const SERI_RENK = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)"];

function el(ad, attr = {}, ebeveyn) {
  const e = document.createElementNS(SVGNS, ad);
  for (const [k, v] of Object.entries(attr)) e.setAttribute(k, v);
  if (ebeveyn) ebeveyn.appendChild(e);
  return e;
}
// SVG koordinatları kutunun gerçek genişliğinde: yazılar her boyutta 11px kalır
const genislik = (kap, yedek = 760) => Math.max(300, Math.round(kap.getBoundingClientRect().width) || yedek);
function guzelAdim(aralik, hedef = 4) {
  const ham = aralik / hedef, us = 10 ** Math.floor(Math.log10(ham)), n = ham / us;
  return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * us;
}

// ---------------------------------------------------------------- ipucu (tooltip): değer önde, ad arkada, çizgi anahtar
function ipucuKur(kap) {
  const d = document.createElement("div");
  d.className = "ipucu"; d.hidden = true; d.setAttribute("role", "status");
  kap.appendChild(d);
  return {
    goster(px, py, baslik, satirlar) {
      d.replaceChildren();
      const b = document.createElement("div"); b.className = "ipucu-bas"; b.textContent = baslik; d.appendChild(b);
      for (const s of satirlar) {
        const r = document.createElement("div"); r.className = "ipucu-satir";
        if (s.renk) { const k = document.createElement("span"); k.className = s.kare ? "anahtar kare" : "anahtar"; k.style.background = s.renk; r.appendChild(k); }
        const v = document.createElement("b"); v.textContent = s.deger; r.appendChild(v);
        if (s.ad) { const a = document.createElement("span"); a.className = "soluk"; a.textContent = s.ad; r.appendChild(a); }
        d.appendChild(r);
      }
      d.hidden = false;
      const g = kap.getBoundingClientRect(), w = d.offsetWidth, h = d.offsetHeight;
      let x = px + 14, y = py - h - 10;
      if (x + w > g.width) x = px - w - 14;
      if (x < 0) x = 0;
      if (y < 0) y = py + 16;
      d.style.left = x + "px"; d.style.top = y + "px";
    },
    gizle() { d.hidden = true; },
  };
}
const yerel = (kap, e) => { const r = kap.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };

// ---------------------------------------------------------------- çizgi grafik
// xler: etiket listesi (sezon); seriler: [{ad, renk, d: [değer|null] (xler ile aynı uzunluk)}]
function cizgiGrafik(kap, { xler, seriler, bicim, yMin = null, yMax = null, yukseklik = 240, xEtiket = s => String(sezonYil(s)), ipucuBas = s => s }) {
  kap.classList.add("grafik");
  const W = genislik(kap), H = yukseklik, sol = 44, sag = 16, ust = 12, alt = 26;
  const tum = seriler.flatMap(s => s.d).filter(v => v != null);
  let lo = yMin ?? Math.min(...tum), hi = yMax ?? Math.max(...tum);
  const adim = guzelAdim(hi - lo || 1);
  lo = Math.floor(lo / adim) * adim; hi = Math.ceil(hi / adim) * adim;
  const X = i => sol + (xler.length < 2 ? 0 : i * (W - sol - sag) / (xler.length - 1));
  const Y = v => ust + (hi - v) / (hi - lo || 1) * (H - ust - alt);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "grafik-svg", role: "img" });
  for (let v = lo; v <= hi + adim / 2; v += adim) {
    el("line", { x1: sol, x2: W - sag, y1: Y(v), y2: Y(v), class: v === lo ? "eksen" : "izgara-cizgi" }, svg);
    el("text", { x: sol - 6, y: Y(v) + 4, class: "eksen-yazi", "text-anchor": "end" }, svg).textContent = bicim(v, true);
  }
  xler.forEach((s, i) => {
    const y = sezonYil(s);
    if (y % (W < 520 ? 20 : 10) === 0 && (i === 0 || sezonYil(xler[i - 1]) !== y))
      el("text", { x: X(i), y: H - 6, class: "eksen-yazi", "text-anchor": "middle" }, svg).textContent = xEtiket(s);
  });
  for (const s of seriler) {
    let d = "", acik = false;
    s.d.forEach((v, i) => { if (v == null) { acik = false; return; } d += `${acik ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`; acik = true; });
    el("path", { d, class: "cizgi", style: `stroke:${s.renk}` }, svg);
  }
  const imlec = el("line", { y1: ust, y2: H - alt, class: "imlec", visibility: "hidden" }, svg);
  const noktalar = seriler.map(s => el("circle", { r: 4.5, class: "nokta", style: `fill:${s.renk}`, visibility: "hidden" }, svg));
  const kat = el("rect", { x: sol, y: 0, width: W - sol - sag, height: H, fill: "transparent", tabindex: 0, class: "hit" }, svg);
  kap.appendChild(svg);
  const ip = ipucuKur(kap);
  const goster = i => {
    imlec.setAttribute("x1", X(i)); imlec.setAttribute("x2", X(i)); imlec.setAttribute("visibility", "visible");
    seriler.forEach((s, j) => {
      const v = s.d[i];
      noktalar[j].setAttribute("visibility", v == null ? "hidden" : "visible");
      if (v != null) { noktalar[j].setAttribute("cx", X(i)); noktalar[j].setAttribute("cy", Y(v)); }
    });
    const r = svg.getBoundingClientRect(), olcek = r.width / W;
    const sat = seriler.filter(s => s.d[i] != null).sort((a, b) => b.d[i] - a.d[i]).map(s => ({ deger: bicim(s.d[i]), ad: s.ad, renk: s.renk }));
    ip.goster(X(i) * olcek, Math.min(...seriler.map(s => s.d[i] ?? hi).map(Y)) * olcek, ipucuBas(xler[i]), sat.length ? sat : [{ deger: "—" }]);
  };
  let secili = xler.length - 1;
  kat.addEventListener("pointermove", e => {
    const [px] = yerel(svg, e), x = px / svg.getBoundingClientRect().width * W;
    secili = Math.max(0, Math.min(xler.length - 1, Math.round((x - sol) / ((W - sol - sag) / Math.max(1, xler.length - 1)))));
    goster(secili);
  });
  const sakla = () => { ip.gizle(); imlec.setAttribute("visibility", "hidden"); noktalar.forEach(n => n.setAttribute("visibility", "hidden")); };
  kat.addEventListener("pointerleave", sakla);
  kat.addEventListener("focus", () => goster(secili));
  kat.addEventListener("blur", sakla);
  kat.addEventListener("keydown", e => {
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") { secili = Math.max(0, Math.min(xler.length - 1, secili + (e.key === "ArrowLeft" ? -1 : 1))); goster(secili); e.preventDefault(); }
  });
}
function lejant(seriler, cizgi = true) {
  return `<div class="lejant">${seriler.map(s => `<span><i class="${cizgi ? "anahtar" : "anahtar kare"}" style="background:${s.renk}"></i>${esc(s.ad)}</span>`).join("")}</div>`;
}
function tabloGorunum(baslik, basliklar, satirlar) {
  return `<details class="tablo-gorunum"><summary>${esc(baslik)}</summary><div class="tablo-kap"><table class="tablo">
    <thead><tr>${basliklar.map((b, i) => `<th${i ? ' class="s"' : ""}>${esc(b)}</th>`).join("")}</tr></thead>
    <tbody>${satirlar.map(r => `<tr>${r.map((v, i) => `<td${i ? ' class="s"' : ""}>${esc(v)}</td>`).join("")}</tr>`).join("")}</tbody></table></div></details>`;
}

// ---------------------------------------------------------------- Sayılarla Türk futbolu
const sayilarDurum = { skorLig: "1", skorDonem: "tum", skorTur: "oran" };

async function sayilarSayfa() {
  document.title = "Sayılarla Türk futbolu · Türk Futbol Arşivi";
  icerik.innerHTML = `<div class="yukleniyor">Sayılar hazırlanıyor…</div>`;
  const [S, Y] = await Promise.all([al(`data/sayilar.json?s=${OZET.surum || ""}`), al(`data/yolculuk.json?s=${OZET.surum || ""}`)]);
  const A = S.alanlar.reduce((o, a, i) => (o[a] = i, o), {});
  const kademeler = Object.keys(S.sezon).sort();
  const xler = [...new Set(kademeler.flatMap(k => S.sezon[k].map(r => r[0])))].sort((a, b) => sezonYil(a) - sezonYil(b) || a.localeCompare(b));
  const deger = (k, f) => { const m = new Map(S.sezon[k].map(r => [r[0], r])); return xler.map(s => m.has(s) && m.get(s)[A.mac] >= 20 ? f(m.get(s)) : null); };
  const seri = f => kademeler.map((k, i) => ({ ad: KADEME_AD[k], renk: SERI_RENK[i], d: deger(k, f) }));
  const golS = seri(r => r[A.gol] / r[A.mac]), evS = seri(r => r[A.ev] / r[A.mac]), berS = seri(r => r[A.beraberlik] / r[A.mac]);
  // öne çıkan sayılar: Süper Lig'in en az ve en çok gollü sezonu
  const sl = S.sezon["1"].filter(r => r[A.mac] >= 100);
  const enAz = sl.reduce((a, b) => a[A.gol] / a[A.mac] <= b[A.gol] / b[A.mac] ? a : b), enCok = sl.reduce((a, b) => a[A.gol] / a[A.mac] >= b[A.gol] / b[A.mac] ? a : b);
  const toplamMac = kademeler.reduce((t, k) => t + S.sezon[k].reduce((u, r) => u + r[A.mac], 0), 0);
  const toplamGol = kademeler.reduce((t, k) => t + S.sezon[k].reduce((u, r) => u + r[A.gol], 0), 0);

  icerik.innerHTML = `
  <div class="sayfa-bas"><h1>Sayılarla Türk futbolu</h1></div>
  <p class="soluk not">1959'dan bugüne profesyonel liglerin normal sezon maçlarından. Play-off, hükmen ve sayılmayan maçlar dahil değil; 20'den az maçı olan sezonlar çizilmedi.</p>
  <div class="izgara k4 bolum-ust">
    <div class="kart stat"><span class="soluk">Lig maçı</span><b>${sayiYaz(toplamMac)}</b></div>
    <div class="kart stat"><span class="soluk">Gol</span><b>${sayiYaz(toplamGol)}</b></div>
    <div class="kart stat"><span class="soluk">Süper Lig'in en az gollü sezonu</span><b>${esc(enAz[0])}</b><small class="soluk">maç başına ${ondalik(enAz[A.gol] / enAz[A.mac])} gol</small></div>
    <div class="kart stat"><span class="soluk">Süper Lig'in en gollü sezonu</span><b>${esc(enCok[0])}</b><small class="soluk">maç başına ${ondalik(enCok[A.gol] / enCok[A.mac])} gol</small></div>
  </div>

  <h2 class="bolum">Dönemler</h2>
  <div class="kart viz"><h3>Maç başına gol</h3>${lejant(golS)}<div id="gGol"></div>
    ${tabloGorunum("Tablo olarak göster", ["Sezon", ...golS.map(s => s.ad)], xler.map((s, i) => [s, ...golS.map(x => x.d[i] == null ? "—" : ondalik(x.d[i]))]))}</div>
  <div class="izgara k2 bolum-ic">
    <div class="kart viz"><h3>Ev sahibi galibiyeti</h3>${lejant(evS)}<div id="gEv"></div>
      ${tabloGorunum("Tablo olarak göster", ["Sezon", ...evS.map(s => s.ad)], xler.map((s, i) => [s, ...evS.map(x => x.d[i] == null ? "—" : yuzde(x.d[i]))]))}</div>
    <div class="kart viz"><h3>Beraberlik</h3>${lejant(berS)}<div id="gBer"></div>
      ${tabloGorunum("Tablo olarak göster", ["Sezon", ...berS.map(s => s.ad)], xler.map((s, i) => [s, ...berS.map(x => x.d[i] == null ? "—" : yuzde(x.d[i]))]))}</div>
  </div>

  <h2 class="bolum">Skorlar</h2>
  <div id="skorBolum"></div>

  <h2 class="bolum">Büyük dörtlünün birbirleriyle maçları</h2>
  <p class="soluk not">Lig, Türkiye Kupası ve Cumhurbaşkanlığı/Süper Kupa maçları. Çizgi, iki kulübün galibiyet farkının maç maç nasıl değiştiğini gösterir: çizgi yukarıdaysa soldaki kulüp, aşağıdaysa sağdaki kulüp önde. Penaltıyla biten maçlar beraberlik sayılır.</p>
  <div id="derbiler" class="izgara k2"></div>

  <h2 class="bolum">Süper Lig'de oynamış kulüpler</h2>
  <p class="soluk not">Her satır bir kulüp, her kare bir sezon. Koyu kare Süper Lig, açıldıkça alt ligler; noktalı kare şampiyonluk. Süper Lig'de en çok sezon geçirenden en aza sıralı.</p>
  <div class="kart viz" id="matris"></div>`;

  cizgiGrafik($("#gGol"), { xler, seriler: golS, bicim: (v, eksen) => ondalik(v, eksen ? 1 : 2), yMin: 0 });
  cizgiGrafik($("#gEv"), { xler, seriler: evS, bicim: (v, eksen) => yuzde(v, eksen ? 0 : 1), yukseklik: 220 });
  cizgiGrafik($("#gBer"), { xler, seriler: berS, bicim: (v, eksen) => yuzde(v, eksen ? 0 : 1), yukseklik: 220 });
  skorBolumu($("#skorBolum"), S, xler, A);
  derbiCiz($("#derbiler"), S);
  matrisCiz($("#matris"), Y, xler);
}

// ---------------------------------------------------------------- skor ısı haritası + 1-0 / 1-1 / 0-0 payı
function skorBolumu(kap, S, xler, A) {
  const D = sayilarDurum, ust = S.skor_ust;
  const ligler = [["tum", "Bütün ligler"], ...Object.keys(S.sezon).sort().map(k => [k, KADEME_AD[k]])];
  const donemler = Object.keys(S.skor.tum).filter(x => x !== "tum").sort();
  const ciz = () => {
    const sayim = (S.skor[D.skorLig] || {})[D.skorDonem] || {};
    const top = Object.values(sayim).reduce((a, b) => a + b, 0) || 1;
    const enCok = Math.max(...Object.values(sayim), 1);
    const etiket = g => g >= ust ? `${ust}+` : String(g);
    const hucre = (e, d) => {
      const n = sayim[`${e}-${d}`] || 0, t = n / enCok;
      return `<button class="hucre${t > .55 ? " koyu" : ""}" style="--t:${(t * 100).toFixed(1)}%" data-skor="${etiket(e)}-${etiket(d)}" data-n="${n}" data-p="${n / top}">${n ? yuzde(n / top, 1) : ""}</button>`;
    };
    const lig = D.skorLig === "tum" ? "1" : D.skorLig;
    const pay = [["s10", "1-0 (ya da 0-1)"], ["s11", "1-1"], ["s00", "0-0"]].map(([k, ad], i) => {
      const m = new Map(S.sezon[lig].map(r => [r[0], r]));
      return { ad, renk: SERI_RENK[i], d: xler.map(s => m.has(s) && m.get(s)[A.mac] >= 20 ? m.get(s)[A[k]] / m.get(s)[A.mac] : null) };
    });
    kap.innerHTML = `
      <div class="filtre"><div class="cipler">${ligler.map(([v, ad]) => `<button class="cip ${D.skorLig === v ? "aktif" : ""}" data-lig="${v}">${esc(ad)}</button>`).join("")}</div>
        <div class="cipler">${[["tum", "Bütün yıllar"], ...donemler.map(x => [x, `${x}'ler`])].map(([v, ad]) => `<button class="cip ${D.skorDonem === v ? "aktif" : ""}" data-donem="${v}">${esc(ad)}</button>`).join("")}</div></div>
      <div class="izgara k2">
        <div class="kart viz"><h3>En sık görülen skorlar</h3>
          <p class="soluk aciklama">Satır ev sahibinin, sütun deplasmanın golü. Yüzde: seçili dönemdeki maçların payı. ${sayiYaz(top === 1 && !Object.keys(sayim).length ? 0 : top)} maç.</p>
          <div class="isi" style="--n:${ust + 1}">
            <span></span>${[...Array(ust + 1).keys()].map(d => `<span class="isi-bas">${etiket(d)}</span>`).join("")}
            ${[...Array(ust + 1).keys()].map(e => `<span class="isi-bas">${etiket(e)}</span>${[...Array(ust + 1).keys()].map(d => hucre(e, d)).join("")}`).join("")}
          </div>
          <div class="isi-lejant"><span class="soluk">Ev sahibi golü ↓ · Deplasman golü →</span><span class="olcek"><span class="soluk">az</span><i></i><span class="soluk">çok</span></span></div>
        </div>
        <div class="kart viz"><h3>${esc(KADEME_AD[lig])}: 1-0, 1-1 ve 0-0 biten maçların payı</h3>${lejant(pay)}<div id="gPay"></div>
          ${tabloGorunum("Tablo olarak göster", ["Sezon", ...pay.map(s => s.ad)], xler.map((s, i) => [s, ...pay.map(x => x.d[i] == null ? "—" : yuzde(x.d[i]))]))}</div>
      </div>`;
    cizgiGrafik($("#gPay", kap), { xler, seriler: pay, bicim: (v, eksen) => yuzde(v, eksen ? 0 : 1), yMin: 0, yukseklik: 260 });
    const isi = $(".isi", kap), ip = ipucuKur(isi);
    isi.addEventListener("pointerover", e => {
      const h = e.target.closest(".hucre"); if (!h) return;
      const [x, y] = yerel(isi, e);
      ip.goster(x, y, `Skor ${h.dataset.skor}`, [{ deger: yuzde(+h.dataset.p, 1), ad: "maçların payı" }, { deger: sayiYaz(+h.dataset.n), ad: "maç" }]);
    });
    isi.addEventListener("focusin", e => {
      const h = e.target.closest(".hucre"); if (!h) return;
      const r = h.getBoundingClientRect(), g = isi.getBoundingClientRect();
      ip.goster(r.left - g.left + r.width / 2, r.top - g.top, `Skor ${h.dataset.skor}`, [{ deger: yuzde(+h.dataset.p, 1), ad: "maçların payı" }, { deger: sayiYaz(+h.dataset.n), ad: "maç" }]);
    });
    isi.addEventListener("pointerleave", () => ip.gizle());
    isi.addEventListener("focusout", () => ip.gizle());
    kap.querySelectorAll("[data-lig]").forEach(b => b.addEventListener("click", () => { D.skorLig = b.dataset.lig; ciz(); }));
    kap.querySelectorAll("[data-donem]").forEach(b => b.addEventListener("click", () => { D.skorDonem = b.dataset.donem; ciz(); }));
  };
  ciz();
}

// ---------------------------------------------------------------- derbiler: galibiyet farkı (iki yönlü)
function derbiCiz(kap, S) {
  const ad = id => S.derbi_kulup[id];
  const ciftler = [[846, 463], [846, 95], [846, 115], [463, 95], [463, 115], [95, 115]];
  kap.innerHTML = ciftler.map((c, i) => `<div class="kart viz derbi"><h3>${esc(ad(c[0]))} – ${esc(ad(c[1]))}</h3><div class="derbi-ozet" id="dOz${i}"></div><div id="dG${i}"></div></div>`).join("");
  ciftler.forEach(([a, b], i) => {
    const ms = S.derbi.filter(m => (m[3] === a && m[4] === b) || (m[3] === b && m[4] === a)).sort((x, y) => x[0].localeCompare(y[0]));
    let fark = 0, ga = 0, gb = 0, ber = 0;
    const nok = ms.map(m => {
      const [ag, bg] = m[3] === a ? [m[5], m[6]] : [m[6], m[5]];
      if (ag > bg) { fark++; ga++; } else if (bg > ag) { fark--; gb++; } else ber++;
      return { m, fark, ag, bg };
    });
    $(`#dOz${i}`).innerHTML = `<span><b>${ga}</b> <span class="soluk">${esc(ad(a))} galibiyeti</span></span><span><b>${ber}</b> <span class="soluk">beraberlik</span></span><span><b>${gb}</b> <span class="soluk">${esc(ad(b))} galibiyeti</span></span>`;
    farkGrafik($(`#dG${i}`), nok, ad(a), ad(b));
  });
}
function farkGrafik(kap, nok, adA, adB) {
  kap.classList.add("grafik");
  const W = genislik(kap, 380), H = 200, sol = 34, sag = 10, ust = 16, alt = 22;
  const yil0 = +nok[0].m[0].slice(0, 4), yil1 = +nok.at(-1).m[0].slice(0, 4) + 1;
  const zaman = t => { const [y, a, g] = t.split("-").map(Number); return y + ((a - 1) * 30.4 + g) / 365; };
  const X = t => sol + (zaman(t) - yil0) / (yil1 - yil0) * (W - sol - sag);
  const m = Math.max(4, ...nok.map(n => Math.abs(n.fark)));
  const adim = guzelAdim(2 * m, 4), lim = Math.ceil(m / adim) * adim;
  const Y = v => ust + (lim - v) / (2 * lim) * (H - ust - alt);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "grafik-svg", role: "img", "aria-label": `${adA} – ${adB} galibiyet farkı` });
  for (let v = -lim; v <= lim; v += adim) {
    el("line", { x1: sol, x2: W - sag, y1: Y(v), y2: Y(v), class: v === 0 ? "eksen" : "izgara-cizgi" }, svg);
    el("text", { x: sol - 5, y: Y(v) + 4, class: "eksen-yazi", "text-anchor": "end" }, svg).textContent = v > 0 ? "+" + v : String(v);
  }
  for (let y = Math.ceil(yil0 / 20) * 20; y < yil1; y += 20)
    el("text", { x: sol + (y - yil0) / (yil1 - yil0) * (W - sol - sag), y: H - 5, class: "eksen-yazi", "text-anchor": "middle" }, svg).textContent = y;
  // basamaklı çizgi: fark her maçta değişir
  let d = `M${X(nok[0].m[0]).toFixed(1)},${Y(0).toFixed(1)}`;
  for (const n of nok) d += `V${Y(n.fark).toFixed(1)}H${X(n.m[0]).toFixed(1)}`;
  const kirp = (ad, ust_) => { const c = el("clipPath", { id: ad }, svg); el("rect", { x: 0, y: ust_ ? 0 : Y(0), width: W, height: ust_ ? Y(0) : H }, c); };
  const kimlik = "k" + Math.random().toString(36).slice(2, 8);
  kirp(kimlik + "u", true); kirp(kimlik + "a", false);
  const alan = d + `V${Y(0).toFixed(1)}Z`;
  el("path", { d: alan, class: "alan", style: "fill:var(--div-a)", "clip-path": `url(#${kimlik}u)` }, svg);
  el("path", { d: alan, class: "alan", style: "fill:var(--div-b)", "clip-path": `url(#${kimlik}a)` }, svg);
  el("path", { d, class: "cizgi ince", style: "stroke:var(--div-a)", "clip-path": `url(#${kimlik}u)` }, svg);
  el("path", { d, class: "cizgi ince", style: "stroke:var(--div-b)", "clip-path": `url(#${kimlik}a)` }, svg);
  el("text", { x: sol + 4, y: ust - 4, class: "eksen-yazi" }, svg).textContent = `↑ ${adA} önde`;
  el("text", { x: sol + 4, y: H - alt - 5, class: "eksen-yazi" }, svg).textContent = `↓ ${adB} önde`;
  const imlec = el("line", { y1: ust, y2: H - alt, class: "imlec", visibility: "hidden" }, svg);
  const nokta = el("circle", { r: 4.5, class: "nokta", visibility: "hidden" }, svg);
  const kat = el("rect", { x: sol, y: 0, width: W - sol - sag, height: H, fill: "transparent", tabindex: 0, class: "hit" }, svg);
  kap.appendChild(svg);
  const ip = ipucuKur(kap);
  let secili = nok.length - 1;
  const goster = i => {
    const n = nok[i], x = X(n.m[0]), y = Y(n.fark), olcek = svg.getBoundingClientRect().width / W;
    imlec.setAttribute("x1", x); imlec.setAttribute("x2", x); imlec.setAttribute("visibility", "visible");
    nokta.setAttribute("cx", x); nokta.setAttribute("cy", y); nokta.setAttribute("visibility", "visible");
    nokta.style.fill = n.fark >= 0 ? "var(--div-a)" : "var(--div-b)";
    const ev = n.m[3] === KULUP_ID(adA) ? adA : adB;
    const pen = n.m[7] != null ? ` (pen. ${n.m[7]}-${n.m[8]})` : "";
    ip.goster(x * olcek, y * olcek, `${tarihYaz(n.m[0])} · ${YAR_AD[n.m[2]]}`, [
      { deger: `${S_AD(n.m[3], adA, adB)} ${n.m[5]}-${n.m[6]}${pen} ${S_AD(n.m[4], adA, adB)}` },
      { deger: n.fark === 0 ? "eşit" : `${n.fark > 0 ? adA : adB} +${Math.abs(n.fark)}`, ad: "galibiyet farkı" }]);
  };
  kat.addEventListener("pointermove", e => {
    const [px] = yerel(svg, e), x = px / svg.getBoundingClientRect().width * W;
    let en = 0, ef = Infinity;
    nok.forEach((n, i) => { const f = Math.abs(X(n.m[0]) - x); if (f < ef) { ef = f; en = i; } });
    secili = en; goster(en);
  });
  const sakla = () => { ip.gizle(); imlec.setAttribute("visibility", "hidden"); nokta.setAttribute("visibility", "hidden"); };
  kat.addEventListener("pointerleave", sakla);
  kat.addEventListener("focus", () => goster(secili));
  kat.addEventListener("blur", sakla);
  kat.addEventListener("keydown", e => {
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") { secili = Math.max(0, Math.min(nok.length - 1, secili + (e.key === "ArrowLeft" ? -1 : 1))); goster(secili); e.preventDefault(); }
  });
}
const DERBI_ID = { "Galatasaray": 846, "Fenerbahçe": 463, "Beşiktaş": 95, "Trabzonspor": 115 };
const KULUP_ID = ad => DERBI_ID[ad];
const S_AD = (id, adA, adB) => id === KULUP_ID(adA) ? adA : adB;

// ---------------------------------------------------------------- Süper Lig kulüpleri matrisi
function matrisCiz(kap, Y, xler) {
  const A = Y.alanlar.reduce((o, a, i) => (o[a] = i, o), {});
  const satir = Object.entries(Y.kulup).map(([id, l]) => ({ id: +id, l, sl: l.filter(x => x[A.kademe] === 1).length, sam: l.filter(x => x[A.kademe] === 1 && x[A.sira] === 1).length }))
    .filter(r => r.sl > 0).sort((a, b) => b.sl - a.sl || b.sam - a.sam || kulupAd(a.id).localeCompare(kulupAd(b.id), "tr"));
  const sutun = xler.filter(s => s !== "1959");   // 1959 tek yıllık sezon: 1959-60 ile aynı yıla düşer
  const idx = new Map(sutun.map((s, i) => [s, i]));
  kap.innerHTML = `<div class="matris-lejant lejant">${[1, 2, 3, 4].map(k => `<span><i class="anahtar kare kd${k}"></i>${esc(KADEME_AD[k])}</span>`).join("")}<span><i class="anahtar kare kd1 sampiyon"></i>Şampiyon</span></div>
    <div class="matris-kap"><div class="matris" style="--sutun:${sutun.length}">
      <span class="m-ad"></span>${sutun.map(s => `<span class="m-yil">${sezonYil(s) % 10 === 0 ? sezonYil(s) : ""}</span>`).join("")}
      ${satir.map(r => {
        const h = new Array(sutun.length).fill(null);
        for (const x of r.l) if (idx.has(x[A.sezon])) h[idx.get(x[A.sezon])] = x;
        return `<a class="m-ad bag" href="#/kulup/${r.id}" title="${esc(kulupAd(r.id))}">${esc(kulupAd(r.id))}<small class="soluk">${r.sl}</small></a>` +
          h.map((x, i) => x ? `<span class="m-h kd${x[A.kademe]}${x[A.kademe] === 1 && x[A.sira] === 1 ? " sampiyon" : ""}" data-k="${r.id}" data-s="${esc(sutun[i])}" data-kd="${x[A.kademe]}" data-r="${x[A.sira]}" data-n="${x[A.takim]}"></span>` : `<span class="m-h"></span>`).join("");
      }).join("")}
    </div></div>
    ${tabloGorunum("Tablo olarak göster", ["Kulüp", "Süper Lig sezonu", "Şampiyonluk"], satir.map(r => [kulupAd(r.id), r.sl, r.sam]))}`;
  const m = $(".matris-kap", kap), ip = ipucuKur(m);
  m.addEventListener("pointerover", e => {
    const h = e.target.closest(".m-h[data-k]"); if (!h) { ip.gizle(); return; }
    const [x, y] = yerel(m, e);
    ip.goster(x + m.scrollLeft, y, `${kulupAd(+h.dataset.k)} · ${h.dataset.s}`, [{ deger: `${h.dataset.r}. / ${h.dataset.n}`, ad: KADEME_AD[h.dataset.kd], renk: `var(--kd${h.dataset.kd})`, kare: true }]);
  });
  m.addEventListener("pointerleave", () => ip.gizle());
}

// ---------------------------------------------------------------- kulüp sayfası: lig yolculuğu
async function yolculukCiz(hedef, id) {
  const kap = $("#yolculuk", hedef);
  if (!kap) return;
  let Y;
  try { Y = await al(`data/yolculuk.json?s=${OZET.surum || ""}`); } catch { return; }
  const l = Y.kulup[id];
  if (!l || !l.length || !kap.isConnected) return;
  const A = Y.alanlar.reduce((o, a, i) => (o[a] = i, o), {});
  kap.hidden = false;
  const ilk = sezonYil(l[0][A.sezon]), son = sezonYil(l.at(-1)[A.sezon]);
  const kdMax = Math.max(...l.map(x => x[A.kademe])), kdMin = Math.min(...l.map(x => x[A.kademe]));
  const bant = kdMax - kdMin + 1;
  const W = genislik(kap) - 40, sol = 82, sag = 12, ust = 8, alt = 22, bantH = 46, H = ust + alt + bant * bantH;
  const yil0 = Math.min(ilk, son - 9), yil1 = Math.max(son, yil0 + 10);
  const X = y => sol + (y - yil0) / (yil1 - yil0) * (W - sol - sag);
  const Yp = x => ust + (x[A.kademe] - kdMin) * bantH + 6 + (x[A.takim] > 1 ? (x[A.sira] - 1) / (x[A.takim] - 1) : 0) * (bantH - 12);
  const sl = l.filter(x => x[A.kademe] === 1).length, sam = l.filter(x => x[A.kademe] === 1 && x[A.sira] === 1).length;
  kap.hidden = false;
  kap.innerHTML = `<h3>Lig yolculuğu</h3><p class="soluk aciklama">Her nokta bir sezon: hangi ligde oynadığı ve o ligdeki (gruplu sezonlarda grubundaki) sırası. Bant içinde yukarısı daha iyi sıra.${sl ? ` Süper Lig'de ${sl} sezon${sam ? `, ${sam} şampiyonluk` : ""}.` : ""}</p><div class="yolculuk-g"></div>
    ${tabloGorunum("Tablo olarak göster", ["Sezon", "Lig", "Sıra"], l.map(x => [x[A.sezon], KADEME_AD[x[A.kademe]], `${x[A.sira]} / ${x[A.takim]}`]))}`;
  const g = $(".yolculuk-g", kap);
  g.classList.add("grafik");
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "grafik-svg", role: "img", "aria-label": "Lig yolculuğu" });
  for (let k = kdMin; k <= kdMax; k++) {
    const y0 = ust + (k - kdMin) * bantH;
    el("rect", { x: sol, y: y0, width: W - sol - sag, height: bantH - 2, class: (k - kdMin) % 2 ? "bant" : "bant b2" }, svg);
    el("text", { x: sol - 8, y: y0 + bantH / 2 + 4, class: "eksen-yazi", "text-anchor": "end" }, svg).textContent = KADEME_AD[k];
  }
  for (let y = Math.ceil(yil0 / 10) * 10; y <= yil1; y += 10)
    el("text", { x: X(y), y: H - 6, class: "eksen-yazi", "text-anchor": "middle" }, svg).textContent = y;
  let d = "", onceki = null;
  for (const x of l) {
    const y = sezonYil(x[A.sezon]);
    d += `${onceki != null && y - onceki <= 1 ? "L" : "M"}${X(y).toFixed(1)},${Yp(x).toFixed(1)}`;
    onceki = y;
  }
  el("path", { d, class: "cizgi", style: "stroke:var(--vurgu)" }, svg);
  const noktalar = l.map(x => el("circle", { cx: X(sezonYil(x[A.sezon])), cy: Yp(x), r: x[A.kademe] === 1 && x[A.sira] === 1 ? 5.5 : 4,
    class: "nokta" + (x[A.kademe] === 1 && x[A.sira] === 1 ? " sampiyon" : ""), style: "fill:var(--vurgu)" }, svg));
  const kat = el("rect", { x: sol, y: 0, width: W - sol - sag, height: H, fill: "transparent", tabindex: 0, class: "hit" }, svg);
  g.appendChild(svg);
  const ip = ipucuKur(g);
  let secili = l.length - 1;
  const goster = i => {
    const x = l[i], olcek = svg.getBoundingClientRect().width / W;
    noktalar.forEach((n, j) => n.classList.toggle("secili", j === i));
    ip.goster(X(sezonYil(x[A.sezon])) * olcek, Yp(x) * olcek, x[A.sezon], [{ deger: `${x[A.sira]}. / ${x[A.takim]}`, ad: KADEME_AD[x[A.kademe]] + (x[A.kademe] === 1 && x[A.sira] === 1 ? " · şampiyon" : "") }]);
  };
  kat.addEventListener("pointermove", e => {
    const [px] = yerel(svg, e), xx = px / svg.getBoundingClientRect().width * W;
    let en = 0, ef = Infinity;
    l.forEach((x, i) => { const f = Math.abs(X(sezonYil(x[A.sezon])) - xx); if (f < ef) { ef = f; en = i; } });
    secili = en; goster(en);
  });
  const sakla = () => { ip.gizle(); noktalar.forEach(n => n.classList.remove("secili")); };
  kat.addEventListener("pointerleave", sakla);
  kat.addEventListener("focus", () => goster(secili));
  kat.addEventListener("blur", sakla);
  kat.addEventListener("keydown", e => {
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") { secili = Math.max(0, Math.min(l.length - 1, secili + (e.key === "ArrowLeft" ? -1 : 1))); goster(secili); e.preventDefault(); }
  });
}

yollar.splice(yollar.length - 1, 0, [/^#\/sayilar$/, sayilarSayfa]);
window.yolculukCiz = yolculukCiz;
})();

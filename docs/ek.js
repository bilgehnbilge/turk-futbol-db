"use strict";
/* Sayfa eklentileri (oyuncular, oyuncu, milli takım, rekorlar, Elo, karşılaştır): grafikler ve etkileşimler.
   app.js'ten sonra yüklenir; sayfa çizen fonksiyonlar buradaki EK.* fonksiyonlarını çağırır. Çizimler düz SVG/HTML;
   kulüp renkleri takimTema'dan (açık ve koyu temada okunur tonlar, CSS'te .tr-renk). Hareketler hareket azaltmaya uyar. */
const EK = (() => {
const SVGNS = "http://www.w3.org/2000/svg";
const azHareket = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const renkAyarla = (e, id) => { const t = id != null ? takimTema(KULUP.get(id)) : null; e.style.setProperty("--ca", t ? t["--tv-acik"] : "#8a919c"); e.style.setProperty("--ck", t ? t["--tv-koyu"] : "#8a919c"); };
const renk = id => { const t = id != null ? takimTema(KULUP.get(id)) : null; return t ? `--ca:${t["--tv-acik"]};--ck:${t["--tv-koyu"]}` : "--ca:#8a919c;--ck:#8a919c"; };
const sezonYil = s => +String(s).slice(0, 4);
const kisaSz = s => s.length > 4 ? `${s.slice(2, 4)}/${s.slice(7)}` : s;
const genislik = (kap, yedek = 760) => Math.max(300, Math.round(kap.getBoundingClientRect().width) || yedek);

// basit ipucu: kap içinde konumlanır
function ipucu(kap) {
  kap.classList.add("grafik");
  const d = document.createElement("div"); d.className = "ipucu"; d.hidden = true; d.setAttribute("role", "status"); kap.appendChild(d);
  return {
    goster(e, html) {
      d.innerHTML = html; d.hidden = false;
      const k = kap.getBoundingClientRect(), w = d.offsetWidth, h = d.offsetHeight;
      let x = e.clientX - k.left + 14, y = e.clientY - k.top - h - 12;
      if (x + w > k.width) x = e.clientX - k.left - w - 14;
      d.style.left = Math.max(0, x) + "px"; d.style.top = (y < 0 ? e.clientY - k.top + 16 : y) + "px";
    },
    gizle() { d.hidden = true; },
  };
}

// ---------------------------------------------------------------- tablolar: sütuna tıklayıp sıralama (th[data-sira])
// hücre değeri: td[data-v] ya da metindeki sayı; ilk tık büyükten küçüğe. Sıra sütunu (td.sira) yeniden numaralanır.
function siralanir(tablo) {
  const thler = [...tablo.querySelectorAll("thead th")];
  thler.forEach((th, i) => {
    if (!th.hasAttribute("data-sira")) return;
    th.classList.add("sirala"); th.tabIndex = 0; th.setAttribute("aria-sort", "none");
    const yap = () => {
      const yon = th.getAttribute("aria-sort") === "descending" ? 1 : -1;
      thler.forEach(x => x.hasAttribute("data-sira") && x.setAttribute("aria-sort", "none"));
      th.setAttribute("aria-sort", yon < 0 ? "descending" : "ascending");
      const tb = tablo.tBodies[0], deger = tr => { const c = tr.cells[i]; return c.dataset.v != null ? +c.dataset.v : +String(c.textContent).replace(/\./g, "").replace(",", ".").replace(/[^\d.-]/g, "") || 0; };
      const sat = [...tb.rows].sort((a, b) => (deger(a) - deger(b)) * yon);
      sat.forEach((tr, j) => { const s = tr.querySelector("td.sira"); if (s) s.textContent = j + 1; tb.appendChild(tr); });
    };
    th.addEventListener("click", yap);
    th.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); yap(); } });
  });
}

// ---------------------------------------------------------------- Oyuncular: golcüler/maç listesi eklentileri
// veri çubuğu (sütunun en büyüğüne göre), kulübe göre süzgeç, sıralama
function oyuncuListesi(kap, sekme) {
  const tablo = kap.querySelector("table.tablo"); if (!tablo) return;
  const sut = sekme === "gol" ? 5 : 4, enb = Math.max(...[...tablo.tBodies[0].rows].map(r => +r.cells[sut].textContent.replace(/\./g, "") || 0), 1);
  for (const r of tablo.tBodies[0].rows) { const c = r.cells[sut], v = +c.textContent.replace(/\./g, "") || 0; c.classList.add("cubuklu"); c.style.setProperty("--w", (v / enb * 100).toFixed(1) + "%"); }
  siralanir(tablo);
  const f = document.createElement("div"); f.className = "filtre liste-suz";
  f.innerHTML = `<input type="search" placeholder="Kulübe göre süz (son kulüp)…" aria-label="Kulübe göre süz" autocomplete="off"><span class="soluk" aria-live="polite"></span>`;
  kap.insertBefore(f, tablo.closest(".tablo-kap"));
  const inp = f.querySelector("input"), say = f.querySelector("span");
  inp.addEventListener("input", () => {
    const n = norm(inp.value); let k = 0;
    for (const r of tablo.tBodies[0].rows) { const g = !n || norm(r.cells[2].textContent).includes(n); r.hidden = !g; if (g) k++; }
    say.textContent = n ? `${k} oyuncu` : "";
  });
}

// golcüler yarışı: listenin ilk 10 oyuncusunun sezon sezon biriken golleri (ya da maçları), çubuk yarışı
async function golcuYarisi(kap, liste, kapsam, olcu) {
  const ilk = liste.slice(0, 10);
  kap.innerHTML = `<div class="yukleniyor" style="padding:30px 0">Yarış hazırlanıyor…</div>`;
  const dosya = new Map();
  for (const x of ilk) { const f = x[0] % 500; if (!dosya.has(f)) dosya.set(f, al(`data/tff/o/${f}.json?s=${OZET.surum || ""}`)); }
  const uygun = r => kapsam === "sl" ? r[2] === "L" && r[3] === 1 : kapsam === "lig" ? r[2] === "L" : kapsam === "kupa" ? r[2] === "K" : true;
  const O = [];
  for (const x of ilk) {
    const p = (await dosya.get(x[0] % 500)).oyuncu[x[0]]; if (!p?.s) continue;
    const m = new Map();
    for (const r of p.s) if (uygun(r)) { const s = m.get(r[0]) || { v: 0, kulup: r[1], mac: 0 }; s.v += olcu === "gol" ? r[6] : r[4]; s.mac += r[4]; if (r[4] >= s.mac - r[4]) s.kulup = r[1]; m.set(r[0], s); }
    O.push({ id: x[0], ad: x[1], m });
  }
  const sezonlar = [...new Set(O.flatMap(o => [...o.m.keys()]))].sort();
  if (sezonlar.length < 2) { kap.innerHTML = ""; return; }
  const durum = sezonlar.map((s, i) => O.map(o => {
    let t = 0, kulup = null; for (const z of sezonlar.slice(0, i + 1)) { const v = o.m.get(z); if (v) { t += v.v; kulup = v.kulup; } }
    return { o, t, kulup };
  }).sort((a, b) => b.t - a.t));
  const enb = Math.max(...durum.at(-1).map(x => x.t), 1);
  kap.innerHTML = `<div class="yaris-bas"><h3>${olcu === "gol" ? "Golcüler yarışı" : "En çok maç yarışı"}</h3><p class="aciklama soluk">Listenin ilk 10 oyuncusu: sezon sonu itibarıyla biriken ${olcu === "gol" ? "goller" : "maçlar"}. Çubuk rengi o sezonki kulübü.</p></div>
    <div class="hafta-sec"><button type="button" class="oynat" aria-label="Yarışı oynat">▶</button><input type="range" min="0" max="${sezonlar.length - 1}" value="${sezonlar.length - 1}" aria-label="Sezon"><output></output></div>
    <div class="cubuk-yaris" style="height:${O.length * 34}px" role="img" aria-label="Biriken ${olcu} sıralaması"></div>`;
  const alan = kap.querySelector(".cubuk-yaris"), rng = kap.querySelector("input"), out = kap.querySelector("output"), btn = kap.querySelector(".oynat");
  alan.innerHTML = O.map(o => `<a class="cy-sat tr-renk" href="#/oyuncu/k${o.id}" data-o="${o.id}"><span class="cy-ad">${esc(o.ad)}</span><span class="cy-cubuk"><i></i></span><b class="cy-say">0</b></a>`).join("");
  const ciz = i => {
    out.innerHTML = `<b>${sezonlar[i]}</b> sonu`;
    durum[i].forEach((x, sira) => {
      const e = alan.querySelector(`[data-o="${x.o.id}"]`);
      e.style.transform = `translateY(${sira * 34}px)`; renkAyarla(e, x.kulup);
      e.querySelector("i").style.width = (x.t / enb * 100).toFixed(1) + "%";
      e.querySelector(".cy-say").textContent = sayiYaz(x.t);
      e.classList.toggle("bos", !x.t);
    });
  };
  let z = null;
  const dur = () => { clearInterval(z); z = null; btn.textContent = "▶"; btn.setAttribute("aria-label", "Yarışı oynat"); };
  rng.addEventListener("input", () => { dur(); ciz(+rng.value); });
  btn.addEventListener("click", () => {
    if (z) { dur(); return; }
    btn.textContent = "❚❚"; btn.setAttribute("aria-label", "Durdur");
    let i = +rng.value >= sezonlar.length - 1 ? 0 : +rng.value + 1; rng.value = i; ciz(i);
    z = setInterval(() => { i++; if (i >= sezonlar.length || !alan.isConnected) { dur(); return; } rng.value = i; ciz(i); }, azHareket() ? 900 : 650);
  });
  ciz(sezonlar.length - 1);
}

// gol kralları zaman çizelgesi: sezon başına bir çubuk (boy gol, renk kulüp)
function kralCizelgesi(kap, krallar, kd) {
  const S = Object.keys(krallar).filter(s => krallar[s][kd]).sort();
  if (S.length < 3) return;
  const W = genislik(kap), H = 200, sol = 30, sag = 8, ust = 14, alt = 24;
  const enb = Math.max(...S.map(s => krallar[s][kd][0][2])), bw = (W - sol - sag) / S.length;
  const Y = v => ust + (1 - v / enb) * (H - ust - alt);
  let h = "";
  for (let v = 0; v <= enb; v += enb > 30 ? 10 : 5) h += `<line class="izgara-cizgi" x1="${sol}" x2="${W - sag}" y1="${Y(v)}" y2="${Y(v)}"/><text class="eksen-yazi" x="${sol - 6}" y="${Y(v) + 4}" text-anchor="end">${v}</text>`;
  S.forEach((s, i) => {
    const l = krallar[s][kd], x = sol + i * bw;
    h += `<g class="kr tr-renk" data-i="${i}" style="${renk(l[0][4])}"><rect class="kr-cubuk" x="${(x + bw * .12).toFixed(1)}" y="${Y(l[0][2]).toFixed(1)}" width="${Math.max(1, bw * .76).toFixed(1)}" height="${(H - alt - Y(l[0][2])).toFixed(1)}" rx="${Math.min(3, bw / 4).toFixed(1)}"/>
      <rect class="hit" x="${x}" y="${ust}" width="${bw}" height="${H - ust - alt}" fill="transparent"/></g>`;
    if (sezonYil(s) % 10 === 0 && (i === 0 || sezonYil(S[i - 1]) !== sezonYil(s))) h += `<text class="eksen-yazi" x="${x + bw / 2}" y="${H - 6}" text-anchor="middle">${sezonYil(s)}</text>`;
  });
  kap.innerHTML = `<h3>Sezon sezon gol kralları</h3><p class="aciklama soluk">Çubuk boyu kralın gol sayısı, rengi kulübü. Üzerine gel; tıklayınca oyuncu sayfası açılır.</p>
    <svg class="grafik-svg kral-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Sezon sezon gol kralları, ${S.length} sezon">${h}</svg>`;
  const svg = kap.querySelector("svg"), ip = ipucu(kap);
  svg.addEventListener("pointermove", e => {
    const g = e.target.closest(".kr"); if (!g) { ip.gizle(); return; }
    const s = S[+g.dataset.i], l = krallar[s][kd], esit = l.filter(x => x[2] === l[0][2]), sonra = l.filter(x => x[2] !== l[0][2]);
    svg.querySelectorAll(".kr.on").forEach(x => x.classList.remove("on")); g.classList.add("on");
    ip.goster(e, `<div class="ipucu-bas">${s}</div>${esit.map(x => `<div class="ipucu-satir"><b>${x[2]}</b><span>${esc(x[1])}</span><span class="soluk">${esc(KULUP.get(x[4])?.ad || "")}</span></div>`).join("")}
      ${sonra.slice(0, 2).map(x => `<div class="ipucu-satir soluk"><span>${x[2]}</span><span>${esc(x[1])}</span></div>`).join("")}`);
  });
  svg.addEventListener("pointerleave", () => { ip.gizle(); svg.querySelectorAll(".kr.on").forEach(x => x.classList.remove("on")); });
  svg.addEventListener("click", e => { const g = e.target.closest(".kr"); if (g) location.hash = `#/oyuncu/k${krallar[S[+g.dataset.i]][kd][0][0]}`; });
}

// ---------------------------------------------------------------- oyuncu sayfası: kariyer şeridi
// üstte kulüp şeridi (sezonda birden çok kulüp varsa maç sayısına göre bölünür), altında sezon sezon maç ve gol çubukları
function kariyer(kap, S, kaleci) {
  const say = new Map();
  for (const r of S) { const s = say.get(r.sezon) || { mac: 0, gol: 0, gy: 0, kmac: 0, k: new Map() }; s.mac += r.mac; s.gol += r.gol; s.gy += r.gy; s.kmac += r.kmac; s.k.set(r.kulup, (s.k.get(r.kulup) || 0) + r.mac); say.set(r.sezon, s); }
  const ilk = [...say.keys()].sort()[0], son = [...say.keys()].sort().at(-1);
  const sezonlar = OZET.sezonlar.filter(s => s >= ilk && s <= son && s.length > 4);
  if (sezonlar.length < 2) { kap.remove(); return; }
  const W = genislik(kap), sol = 30, sag = 8, bandY = 6, bandH = 22, ust = 44, H = 200, alt = 22;
  const bw = (W - sol - sag) / sezonlar.length, enMac = Math.max(...[...say.values()].map(s => s.mac), 1);
  const Y = v => ust + (1 - v / enMac) * (H - ust - alt);
  let h = "";
  for (let v = 0; v <= enMac; v += enMac > 30 ? 10 : 5) h += `<line class="izgara-cizgi" x1="${sol}" x2="${W - sag}" y1="${Y(v)}" y2="${Y(v)}"/><text class="eksen-yazi" x="${sol - 6}" y="${Y(v) + 4}" text-anchor="end">${v}</text>`;
  const adim = sezonlar.length > 24 ? 5 : sezonlar.length > 10 ? 2 : 1;
  sezonlar.forEach((s, i) => {
    const x = sol + i * bw, z = say.get(s);
    if (i % adim === 0) h += `<text class="eksen-yazi" x="${x + bw / 2}" y="${H - 6}" text-anchor="middle">${kisaSz(s)}</text>`;
    if (!z) return;
    let ox = x;
    const kl = [...z.k].sort((a, b) => b[1] - a[1]);
    for (const [k, m] of kl) { const w = bw * m / z.mac; h += `<rect class="tr-renk band" style="${renk(k)}" x="${ox.toFixed(1)}" y="${bandY}" width="${Math.max(.5, w - .6).toFixed(1)}" height="${bandH}"/>`; ox += w; }
    const ana = kl[0][0], cx = (x + bw * .16).toFixed(1), cw = Math.max(1, bw * .68).toFixed(1);
    h += `<g class="kr tr-renk" data-s="${s}" style="${renk(ana)}"><rect class="kr-mac" x="${cx}" y="${Y(z.mac).toFixed(1)}" width="${cw}" height="${(H - alt - Y(z.mac)).toFixed(1)}" rx="2"/>
      ${!kaleci && z.gol ? `<rect class="kr-cubuk" x="${cx}" y="${Y(z.gol).toFixed(1)}" width="${cw}" height="${(H - alt - Y(z.gol)).toFixed(1)}" rx="2"/>` : ""}
      <rect class="hit" x="${x}" y="0" width="${bw}" height="${H - alt}" fill="transparent"/></g>`;
  });
  const kulupler = [...new Map(S.map(r => [r.kulup, 0]))].map(([k]) => k);
  kap.innerHTML = `<h3>Kariyer</h3><p class="aciklama soluk">Üstteki şerit sezon sezon kulübü; çubuklar maç (açık) ve ${kaleci ? "kaleci olarak başladığı maçlar dahil toplam maç" : "gol (koyu)"}.</p>
    <svg class="grafik-svg kariyer-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Kariyer: ${sezonlar.length} sezon, ${kulupler.length} kulüp">${h}</svg>
    <div class="lejant">${kulupler.map(k => `<span class="tr-renk" style="${renk(k)}"><i class="anahtar kare" style="background:var(--c)"></i>${esc(KULUP.get(k)?.ad || "?")}</span>`).join("")}</div>`;
  const svg = kap.querySelector("svg"), ip = ipucu(kap);
  svg.addEventListener("pointermove", e => {
    const g = e.target.closest(".kr"); if (!g) { ip.gizle(); return; }
    const z = say.get(g.dataset.s);
    svg.querySelectorAll(".kr.on").forEach(x => x.classList.remove("on")); g.classList.add("on");
    ip.goster(e, `<div class="ipucu-bas">${g.dataset.s}</div>${[...z.k].map(([k, m]) => `<div class="ipucu-satir"><b>${m}</b><span>maç · ${esc(KULUP.get(k)?.ad || "?")}</span></div>`).join("")}
      <div class="ipucu-satir"><b>${kaleci ? z.gy : z.gol}</b><span>${kaleci ? "maçta gol yemedi" : "gol"}</span></div>`);
  });
  svg.addEventListener("pointerleave", () => { ip.gizle(); svg.querySelectorAll(".kr.on").forEach(x => x.classList.remove("on")); });
  svg.addEventListener("click", e => { const g = e.target.closest(".kr"); if (g) location.hash = `#/${K}sezon/${g.dataset.s}`; });
}

// ---------------------------------------------------------------- Rekorlar: rekor maçların zaman dağılımı
// x tarih, y toplam gol; nokta boyu gol farkı; renk listesi (en farklı / deplasmanda / en gollü); aynı maç bir kez
function rekorZaman(kap, v) {
  const tur = [["fark", "En farklı galibiyetler", "var(--s1)"], ["dep_fark", "Deplasmanda en farklı", "var(--s2)"], ["gollu", "En gollü maçlar", "var(--s3)"]];
  const M = new Map();
  for (const [k, ad, c] of tur) for (const m of v[k] || []) { const id = m[13] ?? m.join("|"); if (!M.has(id)) M.set(id, { m, ad, c, k }); }
  const l = [...M.values()].filter(x => x.m[0] && x.m[8] != null);
  if (l.length < 3) { kap.remove(); return; }
  const yil = t => +t.slice(0, 4) + (+t.slice(5, 7) - 1) / 12;
  const a = Math.floor(Math.min(...l.map(x => yil(x.m[0]))) / 10) * 10, b = Math.ceil((Math.max(...l.map(x => yil(x.m[0]))) + .5) / 10) * 10;
  const enb = Math.max(...l.map(x => x.m[8] + x.m[9])), alt0 = Math.max(0, Math.min(...l.map(x => x.m[8] + x.m[9])) - 2);
  const W = genislik(kap), H = 230, sol = 30, sag = 12, ust = 12, alt = 24;
  const X = t => sol + (yil(t) - a) / (b - a) * (W - sol - sag), Y = v => ust + (1 - (v - alt0) / (enb - alt0 || 1)) * (H - ust - alt);
  let h = "";
  for (let v2 = Math.ceil(alt0 / 2) * 2; v2 <= enb; v2 += enb - alt0 > 12 ? 4 : 2) h += `<line class="izgara-cizgi" x1="${sol}" x2="${W - sag}" y1="${Y(v2)}" y2="${Y(v2)}"/><text class="eksen-yazi" x="${sol - 6}" y="${Y(v2) + 4}" text-anchor="end">${v2}</text>`;
  for (let y = a; y <= b; y += 10) h += `<text class="eksen-yazi" x="${sol + (y - a) / (b - a) * (W - sol - sag)}" y="${H - 6}" text-anchor="middle">${y}</text>`;
  l.forEach((x, i) => { const m = x.m, f = Math.abs(m[8] - m[9]); h += `<circle class="rz" data-i="${i}" cx="${X(m[0]).toFixed(1)}" cy="${Y(m[8] + m[9]).toFixed(1)}" r="${(3 + f / 3).toFixed(1)}" style="fill:${x.c}"/>`; });
  kap.innerHTML = `<h3>Rekor maçlar zamanda</h3><p class="aciklama soluk">Aşağıdaki listelerdeki maçlar: yatay eksen tarih, dikey eksen maçtaki toplam gol, nokta büyüklüğü gol farkı. Noktaya tıklayınca maç (ya da sezon) açılır.</p>
    <div class="lejant">${tur.map(([, ad, c]) => `<span><i class="anahtar kare" style="background:${c}"></i>${ad}</span>`).join("")}</div>
    <svg class="grafik-svg rz-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Rekor maçların zaman dağılımı, ${l.length} maç">${h}</svg>`;
  const svg = kap.querySelector("svg"), ip = ipucu(kap);
  svg.addEventListener("pointermove", e => {
    const c = e.target.closest(".rz"); if (!c) { ip.gizle(); return; }
    const { m, ad } = l[+c.dataset.i];
    ip.goster(e, `<div class="ipucu-bas">${tarihYaz(m[0])} · ${esc(m[2] || "")}${m[3] ? ` · ${esc(m[3])}` : ""}</div><div class="ipucu-satir"><span>${esc(m[5])}</span><b>${m[8]}-${m[9]}</b><span>${esc(m[7])}</span></div><div class="soluk">${ad}</div>`);
  });
  svg.addEventListener("pointerleave", () => ip.gizle());
  svg.addEventListener("click", e => { const c = e.target.closest(".rz"); if (!c) return; const m = l[+c.dataset.i].m; location.hash = detayVar(m[13]) ? `#/${K}mac/${m[13]}` : `#/${K}sezon/${m[1]}`; });
}

// ---------------------------------------------------------------- Elo yarışı: sezon sonu Elo'ya göre ilk 12 kulüp, çubuk yarışı
function eloYarisi(kap, E, sezonlar) {
  const N = 12, ALT = 1300;
  const D = sezonlar.map(s => Object.entries(E.kulup).map(([k, l]) => [+k, l.find(x => x[0] === s)?.[1]]).filter(x => x[1] != null).sort((a, b) => b[1] - a[1]).slice(0, N));
  const hepsi = [...new Set(D.flatMap(l => l.map(x => x[0])))];
  const enb = Math.max(...D.flat().map(x => x[1]));
  kap.innerHTML = `<h3>Elo yarışı</h3><p class="aciklama soluk">Her sezonun sonunda en yüksek Elo'lu 12 kulüp. Oynat'a bas ya da kaydırıcıyla bir sezona git; çubuk rengi kulübün rengi.</p>
    <div class="hafta-sec"><button type="button" class="oynat" aria-label="Elo yarışını oynat">▶</button><input type="range" min="0" max="${sezonlar.length - 1}" value="${sezonlar.length - 1}" aria-label="Sezon"><output></output></div>
    <div class="cubuk-yaris elo-yaris" style="height:${N * 34}px" role="img" aria-label="Sezon sonu Elo sıralaması">${hepsi.map(id => `<a class="cy-sat tr-renk" href="#/kulup/${id}" data-k="${id}"><span class="cy-ad">${logoImg(id)}${esc(KULUP.get(id)?.ad || "?")}</span><span class="cy-cubuk"><i></i></span><b class="cy-say"></b></a>`).join("")}</div>`;
  const alan = kap.querySelector(".cubuk-yaris"), rng = kap.querySelector("input"), out = kap.querySelector("output"), btn = kap.querySelector(".oynat");
  alan.querySelectorAll(".cy-sat").forEach(e => renkAyarla(e, +e.dataset.k));
  const ciz = i => {
    out.innerHTML = `<b>${sezonlar[i]}</b> sonu`;
    const sira = new Map(D[i].map((x, j) => [x[0], [j, x[1]]]));
    alan.querySelectorAll(".cy-sat").forEach(e => {
      const v = sira.get(+e.dataset.k);
      e.classList.toggle("disarda", !v); e.tabIndex = v ? 0 : -1;
      e.style.transform = `translateY(${(v ? v[0] : N) * 34}px)`;
      if (v) { e.querySelector("i").style.width = ((v[1] - ALT) / (enb - ALT) * 100).toFixed(1) + "%"; e.querySelector(".cy-say").textContent = v[1]; }
    });
  };
  let z = null;
  const dur = () => { clearInterval(z); z = null; btn.textContent = "▶"; btn.setAttribute("aria-label", "Elo yarışını oynat"); };
  rng.addEventListener("input", () => { dur(); ciz(+rng.value); });
  btn.addEventListener("click", () => {
    if (z) { dur(); return; }
    btn.textContent = "❚❚"; btn.setAttribute("aria-label", "Durdur");
    let i = +rng.value >= sezonlar.length - 1 ? 0 : +rng.value + 1; rng.value = i; ciz(i);
    z = setInterval(() => { i++; if (i >= sezonlar.length || !alan.isConnected) { dur(); return; } rng.value = i; ciz(i); }, azHareket() ? 900 : 600);
  });
  ciz(sezonlar.length - 1);
}

// ---------------------------------------------------------------- maç beklentisi: bugünkü Elo'ya göre beklenen puan payı
function beklenti(kap, E) {
  const G = E.guncel_alanlar.reduce((o, a, i) => (o[a] = i, o), {});
  const elo = id => { const g = E.guncel.find(r => r[G.kulup] === id); if (g) return [g[G.elo], true]; const l = E.kulup[id]; return l ? [l.at(-1)[1], false] : [null, false]; };
  const d = { a: 846, b: 463, saha: "a" };
  kap.innerHTML = `<h3>Maç beklentisi</h3><p class="aciklama soluk">İki kulüp ve saha seç: bugünkü Elo'ya göre maçtan beklenen puan payı (galibiyet 1, beraberlik ½). Kazanma olasılığı değil; beraberlikler payı ikiye böler.</p>
    <div class="bk-sec"><div class="ust-ara"><input id="bkA" type="search" data-yalniz-kulup="1" placeholder="1. kulüp…" autocomplete="off" aria-label="1. kulüp"><div id="bkOA" class="oneri" hidden></div></div>
      <div class="ust-ara"><input id="bkB" type="search" data-yalniz-kulup="1" placeholder="2. kulüp…" autocomplete="off" aria-label="2. kulüp"><div id="bkOB" class="oneri" hidden></div></div></div>
    <div class="cipler bk-saha" role="group" aria-label="Saha"></div><div class="bk-sonuc" aria-live="polite"></div>`;
  const sonuc = kap.querySelector(".bk-sonuc"), saha = kap.querySelector(".bk-saha");
  const ciz = async () => {
    const [ea, ga] = elo(d.a), [eb, gb] = elo(d.b), A = KULUP.get(d.a), B = KULUP.get(d.b);
    kap.querySelector("#bkA").value = A?.ad || ""; kap.querySelector("#bkB").value = B?.ad || "";
    saha.innerHTML = [["a", `${esc(A?.ad || "1.")} evinde`], ["b", `${esc(B?.ad || "2.")} evinde`], ["n", "Tarafsız saha"]].map(([k, ad]) => `<button class="cip ${d.saha === k ? "aktif" : ""}" data-s="${k}">${ad}</button>`).join("");
    if (ea == null || eb == null) { sonuc.innerHTML = `<p class="soluk">Bu kulüplerden birinin Elo'su yok.</p>`; return; }
    const ev = d.saha === "a" ? E.ev_avantaji : d.saha === "b" ? -E.ev_avantaji : 0, p = 1 / (1 + 10 ** (-(ea + ev - eb) / 400));
    const pay = x => Math.round(x * 100);
    sonuc.innerHTML = `<div class="bk-cubuk"><span class="tr-renk" style="${renk(d.a)};width:${(p * 100).toFixed(1)}%"><b>%${pay(p)}</b></span><span class="tr-renk" style="${renk(d.b)};width:${((1 - p) * 100).toFixed(1)}%"><b>%${pay(1 - p)}</b></span></div>
      <div class="bk-alt"><span>${logoImg(d.a)}<b>${esc(A.ad)}</b> ${ea}${ga ? "" : " <small class=soluk>(son sezon)</small>"}</span><span class="soluk">Elo farkı ${ea - eb > 0 ? "+" : ""}${ea - eb}${ev ? `, ev avantajı ${ev > 0 ? "+" : ""}${Math.round(ev)}` : ""}</span><span>${ea && eb ? `${eb}${gb ? "" : " <small class=soluk>(son sezon)</small>"} <b>${esc(B.ad)}</b>${logoImg(d.b)}` : ""}</span></div>
      <p class="bk-gecmis soluk">Aralarındaki maçlar yükleniyor…</p>`;
    const ms = (await kulupMaclari(d.a).catch(() => [])).filter(m => m.rakipId === d.b), t = toplam(ms);
    const g = kap.querySelector(".bk-gecmis"); if (!g) return;
    g.innerHTML = ms.length ? `Geçmişte ${t.O} maç: <b>${esc(A.ad)}</b> ${t.G} galibiyet, ${t.B} beraberlik, <b>${esc(B.ad)}</b> ${t.M} galibiyet (gerçekleşen puan payı %${pay((t.G + t.B / 2) / t.O)}). <a class="bag" href="#/h2h/${d.a}/${d.b}">Bütün maçlar →</a>` : "Aralarında kayıtlı maç yok.";
  };
  saha.addEventListener("click", e => { const b = e.target.closest("[data-s]"); if (b) { d.saha = b.dataset.s; ciz(); } });
  oneriKutusu(kap.querySelector("#bkA"), kap.querySelector("#bkOA"), k => { d.a = k.id; ciz(); });
  oneriKutusu(kap.querySelector("#bkB"), kap.querySelector("#bkOB"), k => { d.b = k.id; ciz(); });
  ciz();
}

// ---------------------------------------------------------------- iki kulüp: denge grafiği, skor dağılımı, en farklılar, seriler, Elo
async function ikili(kap, f, a, b) {
  const l = f.filter(m => m.s !== "N").sort((x, y) => x.tarih.localeCompare(y.tarih));
  if (l.length < 2) { kap.innerHTML = ""; return; }
  const A = KULUP.get(a), B = KULUP.get(b);
  // denge: A galibiyeti +1, B galibiyeti −1, birikimli
  let t = 0; const nok = l.map(m => (t += m.s === "G" ? 1 : m.s === "M" ? -1 : 0, [m, t]));
  const W = genislik(kap), H = 220, sol = 30, sag = 10, ust = 18, alt = 24;
  const lo = Math.min(0, ...nok.map(x => x[1])), hi = Math.max(0, ...nok.map(x => x[1])), pay = Math.max(2, (hi - lo) * .1);
  const yil = d => +d.slice(0, 4) + (+d.slice(5, 7) - 1) / 12, x0 = yil(l[0].tarih), x1 = yil(l.at(-1).tarih) + .01;
  const X = d => sol + (yil(d) - x0) / (x1 - x0) * (W - sol - sag), Y = v => ust + (hi + pay - v) / (hi - lo + 2 * pay) * (H - ust - alt);
  const yol = nok.map(([m, v], i) => `${i ? "L" : "M"}${X(m.tarih).toFixed(1)},${Y(v).toFixed(1)}`).join("");
  let h = `<defs><clipPath id="ikUst"><rect x="0" y="0" width="${W}" height="${Y(0)}"/></clipPath><clipPath id="ikAlt"><rect x="0" y="${Y(0)}" width="${W}" height="${H}"/></clipPath></defs>`;
  const adim = Math.max(1, Math.round((hi - lo) / 4));
  for (let v = Math.ceil((lo - pay) / adim) * adim; v <= hi + pay; v += adim) h += `<line class="${v === 0 ? "eksen" : "izgara-cizgi"}" x1="${sol}" x2="${W - sag}" y1="${Y(v)}" y2="${Y(v)}"/><text class="eksen-yazi" x="${sol - 6}" y="${Y(v) + 4}" text-anchor="end">${v > 0 ? "+" : ""}${v}</text>`;
  for (let y = Math.ceil(x0 / 10) * 10; y <= x1; y += 10) h += `<text class="eksen-yazi" x="${sol + (y - x0) / (x1 - x0) * (W - sol - sag)}" y="${H - 6}" text-anchor="middle">${y}</text>`;
  const alan = `${yol}L${X(l.at(-1).tarih).toFixed(1)},${Y(0)}L${X(l[0].tarih).toFixed(1)},${Y(0)}Z`;
  h += `<path d="${alan}" class="tr-renk ik-alan" style="${renk(a)}" clip-path="url(#ikUst)"/><path d="${alan}" class="tr-renk ik-alan" style="${renk(b)}" clip-path="url(#ikAlt)"/>
    <path d="${yol}" class="cizgi" style="stroke:var(--yazi2)"/><text class="ik-etiket" x="${sol + 6}" y="${ust + 2}">↑ ${esc(A.ad)} önde</text><text class="ik-etiket" x="${sol + 6}" y="${H - alt - 6}">↓ ${esc(B.ad)} önde</text>
    <line class="imlec" y1="${ust}" y2="${H - alt}" visibility="hidden"/><circle class="nokta" r="4.5" visibility="hidden" style="fill:var(--yazi)"/><rect class="hit" x="${sol}" y="0" width="${W - sol - sag}" height="${H}" fill="transparent"/>`;
  // skor dağılımı (A'nın golü satır, B'nin golü sütun)
  const S = Array.from({ length: 6 }, () => Array(6).fill(0));
  for (const m of l) S[Math.min(5, m.a)][Math.min(5, m.y)]++;
  const enS = Math.max(...S.flat());
  const isi = `<div class="isi" style="--n:6"><span></span>${[0, 1, 2, 3, 4, "5+"].map(x => `<span class="isi-bas">${x}</span>`).join("")}
    ${S.map((r, i) => `<span class="isi-bas">${i === 5 ? "5+" : i}</span>${r.map((n, j) => `<button class="hucre${n / enS > .55 ? " koyu" : ""}" style="--t:${(n / enS * 100).toFixed(0)}%" title="${esc(A.ad)} ${i === 5 ? "5+" : i} – ${j === 5 ? "5+" : j} ${esc(B.ad)}: ${n} maç">${n || ""}</button>`).join("")}`).join("")}</div>
    <div class="isi-lejant"><span>Satır: ${esc(A.ad)} golü · sütun: ${esc(B.ad)} golü</span></div>`;
  // en farklılar ve seriler
  const fark = (k, n = 3) => l.filter(m => k === "a" ? m.a > m.y : m.y > m.a).sort((x, y) => Math.abs(y.a - y.y) - Math.abs(x.a - x.y) || (y.a + y.y) - (x.a + x.y)).slice(0, n);
  const seri = f2 => { let en = { n: 0 }, c = { n: 0 }; l.forEach((m, i) => { if (f2(m)) { if (!c.n) c.b = i; c.n++; if (c.n > en.n) en = { n: c.n, b: c.b, e: i }; } else c = { n: 0 }; }); return { en, son: c.n }; };
  const sr = [[`${esc(A.ad)} yenilmedi`, m => m.s !== "M"], [`${esc(B.ad)} yenilmedi`, m => m.s !== "G"], [`${esc(A.ad)} kazandı`, m => m.s === "G"], [`${esc(B.ad)} kazandı`, m => m.s === "M"]].map(([ad, f2]) => ({ ad, ...seri(f2) }));
  const macS = m => `<li><span class="kim">${skorBag(m.id, `<b class="skor">${m.saha === "E" ? `${m.a}-${m.y}` : `${m.y}-${m.a}`}</b>`)} <small class="soluk">${tarihYaz(m.tarih)} · ${m.saha === "E" ? `${esc(A.ad)} evinde` : `${esc(B.ad)} evinde`} · ${esc(m.lig || "")}</small></span></li>`;
  const E = await al(`data/elo.json?s=${OZET.surum || ""}`).catch(() => null);
  kap.innerHTML = `<div class="izgara ikili-ek">
    <div class="kart ik-denge"><h3>Zaman içinde denge</h3><p class="aciklama soluk">Her galibiyet çizgiyi kazananın tarafına bir adım taşır; beraberlik yerinde bırakır. Üzerine gel: o güne kadarki denge.</p><div class="ik-g"><svg class="grafik-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(A.ad)} ile ${esc(B.ad)} arasındaki galibiyet farkı zaman içinde">${h}</svg></div></div>
    <div class="kart"><h3>Skor dağılımı</h3><p class="aciklama soluk">Hangi skor kaç kez çıktı (${l.length} maç).</p>${isi}</div>
    <div class="kart"><h3>En farklı galibiyetler</h3><h4 class="po-agac" style="border:0;margin-top:0">${esc(A.ad)}</h4><ol class="sirali">${fark("a").map(macS).join("") || `<li class="soluk">—</li>`}</ol>
      <h4 class="po-agac">${esc(B.ad)}</h4><ol class="sirali">${fark("b").map(macS).join("") || `<li class="soluk">—</li>`}</ol></div>
    <div class="kart"><h3>En uzun seriler</h3><ol class="sirali">${sr.map(x => `<li><span class="kim">${x.ad}<small class="soluk">${x.en.n ? `${tarihYaz(l[x.en.b].tarih)} – ${tarihYaz(l[x.en.e].tarih)}` : ""}${x.son > 1 ? ` · sürüyor: ${x.son}` : ""}</small></span><b class="n">${x.en.n}</b></li>`).join("")}</ol></div>
    ${E?.kulup?.[a] && E.kulup[b] ? `<div class="kart ik-elo"><h3>Elo (sezon sonu)</h3><div class="lejant"><span><i class="anahtar" style="background:var(--s1)"></i>${esc(A.ad)}</span><span><i class="anahtar" style="background:var(--s2)"></i>${esc(B.ad)}</span></div><div class="ik-elo-g"></div></div>` : ""}
  </div>`;
  // denge grafiği etkileşimi
  const svg = kap.querySelector(".ik-denge svg"), ip = ipucu(kap.querySelector(".ik-g")), im = svg.querySelector(".imlec"), nk = svg.querySelector(".nokta");
  svg.querySelector(".hit").addEventListener("pointermove", e => {
    const r = svg.getBoundingClientRect(), x = (e.clientX - r.left) / r.width * W;
    let j = 0; for (let i = 0; i < nok.length; i++) if (X(nok[i][0].tarih) <= x) j = i;
    const [m, v] = nok[j];
    im.setAttribute("x1", X(m.tarih)); im.setAttribute("x2", X(m.tarih)); im.setAttribute("visibility", "visible");
    nk.setAttribute("cx", X(m.tarih)); nk.setAttribute("cy", Y(v)); nk.setAttribute("visibility", "visible");
    ip.goster(e, `<div class="ipucu-bas">${tarihYaz(m.tarih)} · ${j + 1}. maç</div><div class="ipucu-satir"><b>${m.saha === "E" ? `${m.a}-${m.y}` : `${m.y}-${m.a}`}</b><span>${m.saha === "E" ? `${esc(A.ad)} evinde` : `${esc(B.ad)} evinde`}</span></div><div class="ipucu-satir"><span>Denge</span><b>${v === 0 ? "eşit" : `${v > 0 ? esc(A.ad) : esc(B.ad)} +${Math.abs(v)}`}</b></div>`);
  });
  svg.querySelector(".hit").addEventListener("pointerleave", () => { ip.gizle(); im.setAttribute("visibility", "hidden"); nk.setAttribute("visibility", "hidden"); });
  if (kap.querySelector(".ik-elo-g") && window.cizgiGrafik) {
    const sz = [...new Set([...E.kulup[a], ...E.kulup[b]].map(x => x[0]))].sort((x, y) => sezonYil(x) - sezonYil(y) || x.localeCompare(y));
    const m1 = new Map(E.kulup[a]), m2 = new Map(E.kulup[b]);
    window.cizgiGrafik(kap.querySelector(".ik-elo-g"), { xler: sz, seriler: [{ ad: A.ad, renk: "var(--s1)", d: sz.map(s => m1.get(s) ?? null) }, { ad: B.ad, renk: "var(--s2)", d: sz.map(s => m2.get(s) ?? null) }], bicim: v => String(Math.round(v)), yukseklik: 220 });
  }
}

// karşılaştır sayfası: büyük derbiler tek tıkla
const DERBILER = [[846, 463, "Kıtalararası derbi"], [463, 95, "İstanbul derbisi"], [846, 95, "İstanbul derbisi"], [115, 463, "Karadeniz–İstanbul"], [115, 846, "Karadeniz–İstanbul"], [115, 95, "Karadeniz–İstanbul"],
  [21, 984, "İzmir derbisi"], [984, 490, "İzmir derbisi"], [568, 838, "Ankara derbisi"], [435, 621, "Marmara derbisi"]];
function derbiler(kap) {
  kap.innerHTML = `<h2 class="bolum">Büyük derbiler</h2><div class="derbi-kartlar">${DERBILER.filter(([x, y]) => KULUP.has(x) && KULUP.has(y)).map(([x, y, ad]) => `<a class="derbi-kart" href="#/h2h/${x}/${y}">
    <span class="dk-logo tr-renk" style="${renk(x)}">${logoImg(x)}</span><span class="dk-ad"><b>${esc(KULUP.get(x).ad)} – ${esc(KULUP.get(y).ad)}</b><small>${ad}</small></span><span class="dk-logo tr-renk" style="${renk(y)}">${logoImg(y)}</span></a>`).join("")}</div>`;
}

return { eloYarisi, beklenti, ikili, derbiler, rekorZaman, ipucu, renk, siralanir, oyuncuListesi, golcuYarisi, kralCizelgesi, kariyer, genislik, sezonYil, kisaSz, azHareket };
})();

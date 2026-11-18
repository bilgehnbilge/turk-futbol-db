"use strict";
/* Site geneli etkileşimler: kulüp önizleme kartı, hızlı arama (Ctrl+K ya da /), görünür olunca sayıların sayılması ve
   grafik çizgilerinin çizilmesi. app.js'ten sonra yüklenir; KULUP, K, BOLUM, OZET, al, esc, norm, sayiYaz, logoImg,
   takimTema, kulupAra, oyuncuAra, oyuncuDiziniAl, sezonOzetAl app.js'ten gelir. Hepsi hareket azaltma tercihine uyar. */
(() => {
const azHareket = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const icerik = document.getElementById("icerik");

// ---------------------------------------------------------------- kulüp önizleme kartı (fareyle üzerine gelince)
// şampiyonluk ve kupa sayıları sezon özetlerinden, Elo güncel listeden (ilk açılışta bir kez yüklenir)
let SAYAC = null, ELO = null;
async function sayacAl() {
  if (SAYAC) return SAYAC;
  const Z = await sezonOzetAl(); SAYAC = { sp: new Map(), kupa: new Map() };
  for (const o of Object.values(Z)) { if (o.sampiyon != null) SAYAC.sp.set(o.sampiyon, (SAYAC.sp.get(o.sampiyon) || 0) + 1); if (o.kupa != null) SAYAC.kupa.set(o.kupa, (SAYAC.kupa.get(o.kupa) || 0) + 1); }
  return SAYAC;
}
async function eloAl() {
  if (ELO) return ELO;
  const d = await al(`data/elo.json?s=${OZET.surum || ""}`).catch(() => null);
  ELO = new Map((d?.guncel || []).map((r, i) => [r[0], { elo: r[1], sira: i + 1 }]));
  return ELO;
}
if (matchMedia("(hover: hover) and (pointer: fine)").matches) {
  const kart = document.createElement("div");
  kart.className = "kulup-onizleme"; kart.hidden = true; kart.setAttribute("aria-hidden", "true");
  document.body.appendChild(kart);
  let zaman = null, hedef = null;
  const kapat = () => { clearTimeout(zaman); hedef = null; kart.classList.remove("acik"); kart.hidden = true; };
  const ac = async a => {
    const m = (a.getAttribute("href") || "").match(/^#\/(kadin\/)?kulup\/(\d+)$/);
    if (!m || (m[1] || "") !== K) return;
    const k = KULUP.get(+m[2]); if (!k) return;
    const [S, E] = BOLUM === "erkek" ? await Promise.all([sayacAl(), eloAl()]) : [null, null];
    if (hedef !== a) return;
    const r = k.renk?.length ? k.renk : null, e = E?.get(k.id);
    const sp = S?.sp.get(k.id), ku = S?.kupa.get(k.id);
    kart.style.cssText = r ? `--f1:${r[0]};--f2:${r[1] || r[0]}` : "";
    kart.innerHTML = `${r ? `<i class="ko-serit"></i>` : ""}<div class="ko-bas">${k.logo ? `<img src="logo/${k.logo}.png" alt="">` : `<span class="ko-harf">${esc(k.ad.slice(0, 2))}</span>`}
      <div><b>${esc(k.ad)}</b><small>${k.ilk.slice(0, 4)}–${k.son.slice(0, 4)} · ${sayiYaz(k.mac)} maç</small></div></div>
      ${sp || ku || e ? `<div class="ko-sayi">${sp ? `<span><b>${sp}</b> şampiyonluk</span>` : ""}${ku ? `<span><b>${ku}</b> kupa</span>` : ""}${e ? `<span><b>${e.elo}</b> Elo · ${e.sira}.</span>` : ""}</div>` : ""}
      ${k.adlar?.length > 1 ? `<small class="ko-ad">Eski adları: ${esc(k.adlar.map(x => x[0]).filter(x => x !== k.tamAd && x !== k.ad).slice(0, 3).join(", "))}</small>` : ""}`;
    kart.hidden = false;
    const b = a.getBoundingClientRect(), w = kart.offsetWidth, h = kart.offsetHeight;
    let x = Math.min(innerWidth - w - 12, Math.max(12, b.left)), y = b.bottom + 8;
    if (y + h > innerHeight - 8) y = b.top - h - 8;
    kart.style.left = x + "px"; kart.style.top = y + "px";
    requestAnimationFrame(() => kart.classList.add("acik"));
  };
  document.addEventListener("pointerover", e => {
    const a = e.target.closest?.('a[href*="kulup/"]');
    if (!a || a === hedef) return;
    if (a.closest(".oneri, .ust, .kulup-hero, .karsilasma, .hizli-ara")) return;
    kapat(); hedef = a; zaman = setTimeout(() => ac(a), 380);
  });
  document.addEventListener("pointerout", e => { if (hedef && !hedef.contains(e.relatedTarget)) kapat(); });
  addEventListener("scroll", kapat, { passive: true });
  addEventListener("hashchange", kapat);
}

// ---------------------------------------------------------------- hızlı arama: Ctrl+K / ⌘K ya da "/"
const SAYFALAR = [["Sezonlar", "#/sezonlar"], ["Oyuncular", "#/oyuncular"], ["Gol kralları", "#/oyuncular/krallar"], ["Oyuncu karşılaştır", "#/oyuncular/karsilastir"],
  ["Milli Takım", "#/milli"], ["Kadın futbolu", "#/kadin"], ["Rekorlar", "#/rekorlar"], ["Sayılarla Türk futbolu", "#/sayilar"], ["Elo puan durumu", "#/elo"],
  ["Kulüp karşılaştır", "#/karsilastir"], ["Hakkında", "#/hakkinda"], ["Ana sayfa", "#/"]];
const dlg = document.createElement("dialog");
dlg.className = "hizli-ara"; dlg.setAttribute("aria-label", "Hızlı arama");
dlg.innerHTML = `<div class="ha-kutu"><input type="search" placeholder="Kulüp, oyuncu, sezon (ör. 1995) ya da sayfa…" autocomplete="off" aria-label="Ara" aria-controls="haListe" aria-autocomplete="list">
  <kbd>Esc</kbd></div><div id="haListe" class="ha-liste" role="listbox"></div><div class="ha-alt"><span><kbd>↑</kbd><kbd>↓</kbd> seç</span><span><kbd>Enter</kbd> aç</span><span><kbd>Ctrl</kbd><kbd>K</kbd> ya da <kbd>/</kbd> her sayfada</span></div>`;
document.body.appendChild(dlg);
const inp = dlg.querySelector("input"), liste = dlg.querySelector(".ha-liste");
let sonuc = [], sec = 0;
const ciz = () => {
  const q = inp.value.trim(), n = norm(q);
  const grup = [];
  if (n) {
    const sz = OZET.sezonlar.filter(s => /\d/.test(q) && s.includes(q.replace(/\D+/g, "").slice(0, 4))).slice(-4).reverse();
    grup.push(["Kulüpler", kulupAra(q, 6).map(k => ({ ad: k.ad, alt: `${k.ilk.slice(0, 4)}–${k.son.slice(0, 4)} · ${sayiYaz(k.mac)} maç`, href: `#/${K}kulup/${k.id}`, logo: k.id }))]);
    grup.push(["Oyuncular", oyuncuAra(q, 5).map(o => ({ ad: o.ad, alt: `${o.ilk.slice(0, 4)}–${o.son.slice(5)} · ${o.mac} maç${o.gol ? ` · ${o.gol} gol` : ""}`, href: `#/${K}oyuncu/k${o.kisi}` }))]);
    grup.push(["Sezonlar", sz.map(s => ({ ad: `${s} sezonu`, alt: "puan tabloları, maçlar", href: `#/${K}sezon/${s}` }))]);
    grup.push(["Sayfalar", SAYFALAR.filter(([a]) => norm(a).includes(n)).map(([ad, href]) => ({ ad, href }))]);
  } else grup.push(["Sayfalar", SAYFALAR.map(([ad, href]) => ({ ad, href }))]);
  sonuc = grup.flatMap(g => g[1]);
  sec = Math.min(sec, Math.max(0, sonuc.length - 1));
  let i = 0;
  liste.innerHTML = grup.filter(g => g[1].length).map(([bas, l]) => `<div class="ha-bas">${bas}</div>${l.map(x => { const j = i++;
    return `<a href="${x.href}" role="option" id="ha${j}" data-i="${j}" aria-selected="${j === sec}">${x.logo != null ? logoImg(x.logo) : ""}<span>${esc(x.ad)}</span>${x.alt ? `<small>${esc(x.alt)}</small>` : ""}</a>`; }).join("")}`).join("")
    || `<div class="bos">“${esc(q)}” için sonuç yok.</div>`;
  inp.setAttribute("aria-activedescendant", sonuc.length ? "ha" + sec : "");
  liste.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" });
};
const ac = () => { if (dlg.open) return; inp.value = ""; sec = 0; ciz(); dlg.showModal(); inp.focus(); if (!OYUNCULAR) oyuncuDiziniAl().then(() => dlg.open && ciz()).catch(() => {}); };
window.hizliAraAc = ac;
inp.addEventListener("input", () => { sec = 0; ciz(); });
inp.addEventListener("keydown", e => {
  if (e.key === "ArrowDown" || e.key === "ArrowUp") { sec = (sec + (e.key === "ArrowDown" ? 1 : -1) + sonuc.length) % Math.max(1, sonuc.length); ciz(); e.preventDefault(); }
  else if (e.key === "Enter" && sonuc[sec]) { location.hash = sonuc[sec].href; dlg.close(); e.preventDefault(); }
});
liste.addEventListener("click", e => { if (e.target.closest("a")) dlg.close(); });
dlg.addEventListener("click", e => { if (e.target === dlg) dlg.close(); });   // dışına tıklayınca kapan
document.addEventListener("keydown", e => {
  const yaziyor = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName) || document.activeElement?.isContentEditable;
  if ((e.key === "k" || e.key === "K") && (e.ctrlKey || e.metaKey)) { e.preventDefault(); dlg.open ? dlg.close() : ac(); }
  else if (e.key === "/" && !yaziyor && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); ac(); }
});
document.getElementById("hizliAraDugme")?.addEventListener("click", ac);

// ---------------------------------------------------------------- görünür olunca: büyük sayılar sayılır, çizgiler çizilir
const gozcu = "IntersectionObserver" in window ? new IntersectionObserver(es => es.forEach(x => {
  if (!x.isIntersecting) return; gozcu.unobserve(x.target);
  const t = x.target;
  if (t.matches("b")) {
    const n = +t.dataset.hedef, t0 = performance.now();
    const adim = z => { const p = Math.min(1, (z - t0) / 800), e = 1 - (1 - p) ** 3; t.textContent = sayiYaz(Math.round(n * e)); if (p < 1 && t.isConnected) requestAnimationFrame(adim); };
    requestAnimationFrame(adim);
  } else t.classList.add("ciz");
}), { threshold: .3 }) : null;
function girisleriKur() {
  if (!gozcu || azHareket()) return;
  for (const b of icerik.querySelectorAll(".ana-sayilar b:not([data-hedef]), .ozet-sat b:not([data-hedef]), .kart.stat b:not([data-hedef])")) {
    const m = b.textContent.trim(); if (!/^\d{1,3}(\.\d{3})*$/.test(m)) { b.dataset.hedef = ""; continue; }
    b.dataset.hedef = m.replace(/\./g, ""); if (+b.dataset.hedef < 10) continue;
    b.style.minWidth = b.offsetWidth ? b.offsetWidth + "px" : ""; b.textContent = "0"; gozcu.observe(b);
  }
  for (const s of icerik.querySelectorAll(".grafik-svg:not(.yaris-svg):not([data-giris])")) {
    s.dataset.giris = "";
    const yollar = s.querySelectorAll("path.cizgi");
    if (!yollar.length) continue;
    yollar.forEach(p => p.setAttribute("pathLength", "1"));
    s.classList.add("cizilecek"); gozcu.observe(s);
  }
}
let gz = 0;
new MutationObserver(() => { if (!gz) gz = requestAnimationFrame(() => { gz = 0; girisleriKur(); }); }).observe(icerik, { childList: true, subtree: true });
})();

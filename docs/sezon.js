"use strict";
/* Sezon sayfasının lig bölümü: lig/grup seçici, hafta kaydırıcılı puan tablosu (çıkan/düşen işaretli), sıralama yarışı
   grafiği ve maçlar (hafta hafta ya da sonuç matrisi). app.js'ten sonra yüklenir; esc, KULUP, K, kulupBag, kisaAd, logoImg,
   skorBag, skorYaz, tarihYaz, takimTema, puan, sayiYaz app.js'ten gelir. sezonSayfa ligBolumu'nu çağırır.
   Hafta: her takımın tarih sırasıyla kaçıncı maçı (ertelenen maçlar takımın kendi sırasına girer); bir maçın haftası iki
   takımınkinden büyüğü. Puan tablosu ve yarış grafiği bu haftalarla geri sarılır. */
(() => {
const SVGNS = "http://www.w3.org/2000/svg";
const azHareket = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const tid = (m, s) => s === "ev" ? (m.ev ?? "a" + m.evAd) : (m.dep ?? "a" + m.depAd);

// grubun haftaları ve hafta hafta puan durumu
function ligHesapla(g, sezon) {
  const p = puan(sezon);
  const ms = [...g.ms].sort((a, b) => (a.tarih || "").localeCompare(b.tarih || "") || a.id - b.id);
  const sira = new Map(), ad = new Map();
  for (const m of ms) {
    if (m.durum === "Çifte H" || m.iptal) { m.hafta = null; continue; }
    const e = tid(m, "ev"), d = tid(m, "dep");
    ad.set(e, m.evAd); ad.set(d, m.depAd);
    const ie = (sira.get(e) || 0) + 1, id = (sira.get(d) || 0) + 1;
    sira.set(e, ie); sira.set(d, id); m.hafta = Math.max(ie, id);
  }
  for (const m of ms) for (const s of ["ev", "dep"]) if (!ad.has(tid(m, s))) ad.set(tid(m, s), s === "ev" ? m.evAd : m.depAd);
  const takimlar = [...ad.keys()];
  const oynanan = ms.filter(m => m.eg != null && m.hafta != null);
  const sonHafta = Math.max(0, ...oynanan.map(m => m.hafta));
  const toplamHafta = Math.max(sonHafta, ...ms.map(m => m.hafta || 0));
  const durum = r => {   // r. haftadan sonraki tablo
    const t = new Map(takimlar.map(id => [id, { id, ad: ad.get(id), O: 0, G: 0, B: 0, M: 0, AG: 0, YG: 0, son: [] }]));
    for (const m of ms) {
      if (m.durum === "Çifte H") { if (r >= sonHafta) for (const s of ["ev", "dep"]) { const x = t.get(tid(m, s)); x.O++; x.M++; x.YG += 3; } continue; }
      if (m.eg == null || m.hafta == null || m.hafta > r) continue;
      const e = t.get(tid(m, "ev")), d = t.get(tid(m, "dep"));
      e.O++; d.O++; e.AG += m.eg; e.YG += m.dg; d.AG += m.dg; d.YG += m.eg;
      if (m.eg > m.dg) { e.G++; d.M++; e.son.push("G"); d.son.push("M"); } else if (m.eg < m.dg) { d.G++; e.M++; e.son.push("M"); d.son.push("G"); } else { e.B++; d.B++; e.son.push("B"); d.son.push("B"); }
    }
    return [...t.values()].map(x => ({ ...x, P: x.G * p + x.B, Av: x.AG - x.YG }))
      .sort((a, b) => b.P - a.P || b.Av - a.Av || b.AG - a.AG || String(a.ad).localeCompare(String(b.ad), "tr"));
  };
  const yaris = new Map(takimlar.map(id => [id, []]));   // takım -> her hafta sırası
  for (let r = 1; r <= sonHafta; r++) durum(r).forEach((x, i) => yaris.get(x.id).push(i + 1));
  return { ms, takimlar, ad, sonHafta, toplamHafta, durum, yaris };
}

// takım rengi: açık ve koyu temada okunur çizgi rengi (takimTema'nın vurgu renkleri)
const renkStil = id => { const t = typeof id === "number" ? takimTema(KULUP.get(id)) : null; return t ? `--ca:${t["--tv-acik"]};--ck:${t["--tv-koyu"]}` : "--ca:#8a919c;--ck:#8a919c"; };
const adKisa = (L, id) => kisaAd(typeof id === "number" ? id : null, L.ad.get(id));

function ligBolumu(kap, sezon, sirali, Z) {
  const o = Z[sezon] || {};
  // seviyeler: aynı yarışma + kademe bir düğme; grupları ayrı düğmeler
  const seviyeler = new Map();
  for (const g of sirali) { const k = `${g.yar}|${g.kademe ?? 9}`; (seviyeler.get(k) || seviyeler.set(k, []).get(k)).push(g); }
  const svAd = l => l[0].yar === "T" ? `${l[0].lig}` : (l.length > 1 && /grup|·/i.test(l[0].lig) ? l[0].lig : l[0].lig.replace(/\s*[-–·]\s*\S+$/, "") || l[0].lig);
  const durum = { sv: [...seviyeler.keys()][0], gi: 0, takim: null, gorunum: "hafta", hafta: null };
  kap.innerHTML = `<div class="cipler lig-sec" role="tablist" aria-label="Lig">${[...seviyeler].map(([k, l]) => `<button class="cip" role="tab" data-sv="${k}">${esc(svAd(l))}${l.length > 1 ? ` <small>${l.length} grup</small>` : ""}</button>`).join("")}</div>
    <div class="cipler grup-sec" role="tablist" aria-label="Grup"></div><div class="lig-govde"></div>`;
  const govde = kap.querySelector(".lig-govde");
  const svSec = k => {
    durum.sv = k; durum.gi = 0; durum.takim = null;
    kap.querySelectorAll(".lig-sec .cip").forEach(b => { b.classList.toggle("aktif", b.dataset.sv === k); b.setAttribute("aria-selected", b.dataset.sv === k); });
    const l = seviyeler.get(k), gs = kap.querySelector(".grup-sec");
    gs.hidden = l.length < 2;
    gs.innerHTML = l.map((g, i) => `<button class="cip" role="tab" data-gi="${i}">${esc(g.grup || g.lig)}</button>`).join("");
    grupSec(0);
  };
  const grupSec = i => {
    durum.gi = i; durum.takim = null; durum.hafta = null;
    kap.querySelectorAll(".grup-sec .cip").forEach(b => { b.classList.toggle("aktif", +b.dataset.gi === i); b.setAttribute("aria-selected", +b.dataset.gi === i); });
    grupCiz(seviyeler.get(durum.sv)[i]);
  };
  kap.querySelector(".lig-sec").addEventListener("click", e => { const b = e.target.closest("[data-sv]"); if (b) svSec(b.dataset.sv); });
  kap.querySelector(".grup-sec").addEventListener("click", e => { const b = e.target.closest("[data-gi]"); if (b) grupSec(+b.dataset.gi); });

  function grupCiz(g) {
    const L = ligHesapla(g, sezon);
    durum.hafta = L.sonHafta;
    const bolge = o.k?.[String(g.kademe)] || {};
    const isaret = id => o.sampiyon === id && g.kademe === 1 && g.yar === "L" && L.sonHafta === L.toplamHafta ? ["sp", "★", "Şampiyon"]
      : bolge.c?.includes(id) ? ["c", "↑", "Bir üst lige çıktı"] : bolge.d?.includes(id) ? ["d", "↓", "Bir alt lige düştü"] : bolge.a?.includes(id) ? ["a", "↓", "Ertesi sezon profesyonel liglerde yok"] : null;
    const oynanmamis = L.ms.filter(m => m.eg == null && m.durum !== "Çifte H").length;
    govde.innerHTML = `
      <div class="lig-duzen">
        <div class="kart puan-kart lig-tablo">
          <div class="bas"><h3>${esc(g.lig)}${g.grup ? ` · ${esc(g.grup)}` : ""}</h3><span>${L.takimlar.length} takım · ${L.ms.length} maç${oynanmamis ? `, ${oynanmamis} oynanmadı` : ""}</span></div>
          ${L.sonHafta > 1 ? `<div class="hafta-sec"><button type="button" class="oynat" aria-label="Haftaları oynat">▶</button>
            <input type="range" min="1" max="${L.sonHafta}" value="${L.sonHafta}" aria-label="Puan durumu hangi haftadan sonra">
            <output><b>${L.sonHafta}.</b> hafta sonu</output></div>` : ""}
          <table class="tablo"><thead><tr><th class="s">#</th><th>Takım</th><th class="s">O</th><th class="s ek2">G</th><th class="s ek2">B</th><th class="s ek2">M</th><th class="s ek">AG</th><th class="s ek">YG</th><th class="s">Av</th><th class="s">P</th><th class="ek form-bas">Son 5</th></tr></thead><tbody></tbody></table>
          <p class="lig-not soluk">Bir takıma tıkla: grafikte ve maçlarda o takım öne çıkar. ${Object.keys(bolge).length || o.sampiyon ? "★ şampiyon · ↑ çıktı · ↓ düştü (ertesi sezonun liglerinden)." : ""}</p>
        </div>
        <div class="kart yaris-kart"><h3>Sıralama yarışı</h3><p class="aciklama soluk">Hafta hafta sıra. Bir çizginin üstüne gel ya da tablodan takım seç.</p><div class="yaris"></div></div>
      </div>
      <div class="kart maclar-kart">
        <div class="akis-bas"><h3>Maçlar</h3><div class="cipler gorunum" role="tablist"><button class="cip aktif" data-g="hafta">Hafta hafta</button><button class="cip" data-g="matris">Sonuç matrisi</button></div></div>
        <div class="maclar-ic"></div>
      </div>`;
    const tbody = govde.querySelector(".lig-tablo tbody"), rng = govde.querySelector(".hafta-sec input"), out = govde.querySelector(".hafta-sec output");
    const yarisKap = govde.querySelector(".yaris"), macKap = govde.querySelector(".maclar-ic");
    const tabloCiz = () => {
      const l = L.durum(durum.hafta), son = durum.hafta === L.sonHafta;
      tbody.innerHTML = l.map((x, i) => { const s = son ? isaret(x.id) : null;
        return `<tr data-t="${esc(x.id)}" class="${s ? "bolge-" + s[0] : ""}${durum.takim === x.id ? " secili" : ""}" tabindex="0"><td class="s soluk">${i + 1}</td>
        <td class="takim" title="${esc(x.ad)}">${s ? `<span class="bolge ${s[0]}" title="${s[2]}" aria-label="${s[2]}">${s[1]}</span>` : ""}${typeof x.id === "number" ? kulupBag(x.id, adKisa(L, x.id)) : esc(adKisa(L, x.id))}</td>
        <td class="s">${x.O}</td><td class="s ek2">${x.G}</td><td class="s ek2">${x.B}</td><td class="s ek2">${x.M}</td><td class="s ek">${x.AG}</td><td class="s ek">${x.YG}</td><td class="s">${x.Av > 0 ? "+" : ""}${x.Av}</td><td class="s p">${x.P}</td>
        <td class="ek form">${x.son.slice(-5).map(r => `<i class="son ${r}" aria-label="${{ G: "galibiyet", B: "beraberlik", M: "mağlubiyet" }[r]}">${r}</i>`).join("")}</td></tr>`; }).join("");
      if (out) out.innerHTML = `<b>${durum.hafta}.</b> hafta sonu${durum.hafta < L.sonHafta ? ` <button type="button" class="bag sifirla">son duruma dön</button>` : ""}`;
      yaris.imlec(durum.hafta);
    };
    const takimSec = id => {
      durum.takim = durum.takim === id ? null : id;
      tbody.querySelectorAll("tr").forEach(tr => tr.classList.toggle("secili", tr.dataset.t === String(durum.takim)));
      yaris.vurgula(durum.takim, true); macCiz();
    };
    tbody.addEventListener("click", e => { if (e.target.closest("a")) return; const tr = e.target.closest("tr[data-t]"); if (tr) takimSec(L.takimlar.find(t => String(t) === tr.dataset.t)); });
    tbody.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { const tr = e.target.closest("tr[data-t]"); if (tr && !e.target.closest("a")) { e.preventDefault(); takimSec(L.takimlar.find(t => String(t) === tr.dataset.t)); } } });
    tbody.addEventListener("pointerover", e => { const tr = e.target.closest("tr[data-t]"); if (tr) yaris.vurgula(L.takimlar.find(t => String(t) === tr.dataset.t)); });
    tbody.addEventListener("pointerleave", () => yaris.vurgula(durum.takim, true));
    let zam = null;
    const haftaKur = r => { durum.hafta = r; if (rng) rng.value = r; tabloCiz(); if (durum.gorunum === "hafta" && durum.takim == null) { macHafta = Math.min(r, L.toplamHafta); macCiz(); } };
    const dur = () => { clearInterval(zam); zam = null; const b = govde.querySelector(".oynat"); if (b) { b.textContent = "▶"; b.setAttribute("aria-label", "Haftaları oynat"); } };
    rng?.addEventListener("input", () => { dur(); haftaKur(+rng.value); });
    govde.querySelector(".hafta-sec")?.addEventListener("click", e => {
      if (e.target.closest(".sifirla")) { dur(); haftaKur(L.sonHafta); return; }
      const b = e.target.closest(".oynat"); if (!b) return;
      if (zam) { dur(); return; }
      b.textContent = "❚❚"; b.setAttribute("aria-label", "Durdur");
      let r = durum.hafta >= L.sonHafta ? 1 : durum.hafta + 1; haftaKur(r);
      zam = setInterval(() => { r++; if (r > L.sonHafta) { dur(); return; } haftaKur(r); }, azHareket() ? 700 : 420);
    });
    const yaris = yarisCiz(yarisKap, L, takimSec, id => tbody.querySelectorAll("tr").forEach(tr => tr.classList.toggle("vurgu-sat", id != null && tr.dataset.t === String(id))));
    // maçlar
    let macHafta = Math.min(L.sonHafta || 1, L.toplamHafta || 1);
    const satir = m => `<div class="tabela${durum.takim != null ? " sonuclu" : ""}">${durum.takim != null ? `<span class="son ${sonucBak(m, durum.takim)}">${sonucBak(m, durum.takim)}</span>` : ""}<span class="tarih">${tarihYaz(m.tarih)}${durum.takim != null && m.hafta ? ` · ${m.hafta}. h` : ""}</span>
      <span class="ev">${typeof m.ev === "number" ? logoImg(m.ev) : ""}<span>${esc(kisaAd(m.ev, m.evAd))}</span></span>${skorBag(m.id, `<b class="skor">${skorYaz(m.eg, m.dg, m.ep, m.dp, m.durum)}</b>`)}
      <span class="dep"><span>${esc(kisaAd(m.dep, m.depAd))}</span>${typeof m.dep === "number" ? logoImg(m.dep) : ""}</span></div>`;
    const sonucBak = (m, id) => { if (m.eg == null) return "N"; const ev = tid(m, "ev") === id; const a = ev ? m.eg : m.dg, b = ev ? m.dg : m.eg; return a > b ? "G" : a < b ? "M" : "B"; };
    const macCiz = () => {
      govde.querySelectorAll(".maclar-kart .gorunum .cip").forEach(b => b.classList.toggle("aktif", b.dataset.g === durum.gorunum));
      if (durum.gorunum === "matris") { macKap.innerHTML = matrisHtml(L, durum); return; }
      if (durum.takim != null) {
        const l = L.ms.filter(m => tid(m, "ev") === durum.takim || tid(m, "dep") === durum.takim);
        macKap.innerHTML = `<div class="hafta-bas"><b>${esc(adKisa(L, durum.takim))}: ${l.length} maç</b><button type="button" class="cip kaldir-sec">Seçimi kaldır ✕</button></div><div class="tabelalar">${l.map(satir).join("")}</div>`;
        return;
      }
      const l = L.ms.filter(m => m.hafta === macHafta), ertelenen = L.ms.filter(m => m.hafta == null && m.durum !== "Çifte H");
      macKap.innerHTML = `<div class="hafta-bas"><button type="button" class="cip" data-h="-1" ${macHafta <= 1 ? "disabled" : ""} aria-label="Önceki hafta">‹</button>
        <label><select aria-label="Hafta">${Array.from({ length: L.toplamHafta }, (_, i) => `<option value="${i + 1}" ${i + 1 === macHafta ? "selected" : ""}>${i + 1}. hafta</option>`).join("")}</select></label>
        <button type="button" class="cip" data-h="1" ${macHafta >= L.toplamHafta ? "disabled" : ""} aria-label="Sonraki hafta">›</button>
        <span class="soluk">${l.length ? `${tarihYaz(l[0].tarih)}${l.length > 1 && l.at(-1).tarih !== l[0].tarih ? ` – ${tarihYaz(l.at(-1).tarih)}` : ""}` : ""}</span></div>
        <div class="tabelalar">${l.map(satir).join("") || `<div class="bos">Bu haftada maç yok.</div>`}</div>
        ${ertelenen.length && macHafta === L.toplamHafta ? `<p class="soluk not">Haftaya bağlanamayan ${ertelenen.length} maç (iptal) listede yok.</p>` : ""}`;
    };
    macKap.addEventListener("click", e => {
      if (e.target.closest(".kaldir-sec")) { takimSec(durum.takim); return; }
      const b = e.target.closest("[data-h]"); if (b) { macHafta = Math.max(1, Math.min(L.toplamHafta, macHafta + +b.dataset.h)); macCiz(); }
      const h = e.target.closest("td[data-t], th[data-t]"); if (h) takimSec(L.takimlar.find(t => String(t) === h.dataset.t));
    });
    macKap.addEventListener("change", e => { if (e.target.matches("select")) { macHafta = +e.target.value; macCiz(); } });
    macKap.addEventListener("pointerover", e => {   // sonuç matrisinde imlecin satırı ve sütunu
      const c = e.target.closest("td[data-r]"), t = macKap.querySelector(".matris-sonuc"); if (!t) return;
      t.querySelectorAll(".hl").forEach(x => x.classList.remove("hl"));
      if (!c) return;
      t.querySelectorAll(`td[data-r="${c.dataset.r}"], td[data-c="${c.dataset.c}"]`).forEach(x => x.classList.add("hl"));
      t.rows[+c.dataset.r + 1]?.cells[0].classList.add("hl"); t.rows[0].cells[+c.dataset.c + 1]?.classList.add("hl");
    });
    macKap.addEventListener("pointerleave", () => macKap.querySelectorAll(".matris-sonuc .hl").forEach(x => x.classList.remove("hl")));
    govde.querySelector(".maclar-kart .gorunum").addEventListener("click", e => { const b = e.target.closest("[data-g]"); if (b) { durum.gorunum = b.dataset.g; macCiz(); } });
    tabloCiz(); macCiz();
  }
  svSec(durum.sv);
}

// ---------------------------------------------------------------- sıralama yarışı (bump chart)
const etiket = a => a.length > 17 ? a.slice(0, 16).trimEnd() + "…" : a;
function yarisCiz(kap, L, secince, satirVurgu) {
  const R = L.sonHafta, n = L.takimlar.length;
  if (R < 2) { kap.innerHTML = `<p class="soluk">Grafik için en az iki hafta gerekli.</p>`; return { imlec() {}, vurgula() {} }; }
  const W = Math.max(320, Math.round(kap.getBoundingClientRect().width) || 560), adim = n > 14 ? 17 : 20;
  const sol = 26, sag = 112, ust = 10, alt = 24, H = ust + alt + (n - 1) * adim;
  const X = r => sol + (r - 1) * (W - sol - sag) / (R - 1), Y = s => ust + (s - 1) * adim;
  const svg = document.createElementNS(SVGNS, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("class", "grafik-svg yaris-svg");
  svg.setAttribute("role", "img"); svg.setAttribute("aria-label", `Sıralama yarışı: ${R} hafta, ${n} takım`);
  let h = "";
  for (let s = 1; s <= n; s++) h += `<text class="eksen-yazi" x="${sol - 8}" y="${Y(s) + 4}" text-anchor="end">${s}</text>`;
  const ad = R > 30 ? 5 : R > 12 ? 4 : 2;
  const isaretler = [...new Set([1, ...Array.from({ length: R }, (_, i) => i + 1).filter(r => r % ad === 0 && R - r >= ad / 2), R])];
  for (const r of isaretler) h += `<text class="eksen-yazi" x="${X(r)}" y="${H - 6}" text-anchor="middle">${r}</text>`;
  h += `<line class="imlec yaris-imlec" y1="${ust - 6}" y2="${H - alt + 6}" x1="${X(R)}" x2="${X(R)}"/>`;
  const sirali = [...L.takimlar].sort((a, b) => L.yaris.get(a).at(-1) - L.yaris.get(b).at(-1));
  for (const id of sirali) {
    const y = L.yaris.get(id), d = y.map((s, i) => `${i ? "L" : "M"}${X(i + 1).toFixed(1)},${Y(s).toFixed(1)}`).join("");
    const son = y.at(-1);
    h += `<g class="seri" data-t="${esc(id)}" style="${renkStil(id)}"><path class="cizgi" d="${d}"/><path class="hit-yol" d="${d}"/>
      <circle class="uc" r="3.5" cx="${X(R)}" cy="${Y(son)}"/><text class="seri-ad" x="${X(R) + 8}" y="${Y(son) + 4}">${esc(etiket(adKisa(L, id)))}</text>
      <circle class="imlec-nokta" r="4" cx="${X(R)}" cy="${Y(son)}"/></g>`;
  }
  svg.innerHTML = h;
  kap.replaceChildren(svg);
  const ip = document.createElement("div"); ip.className = "ipucu"; ip.hidden = true; kap.appendChild(ip);
  kap.classList.add("grafik");
  const g = id => svg.querySelector(`.seri[data-t="${CSS.escape(String(id))}"]`);
  let kilitli = null, imlecR = R;
  const vurgula = (id, kilit) => {
    if (kilit) kilitli = id;
    const v = id ?? kilitli;
    svg.classList.toggle("vurgulu", v != null);
    svg.querySelectorAll(".seri").forEach(s => s.classList.toggle("on", v != null && s.dataset.t === String(v)));
    if (v != null) g(v)?.parentNode.appendChild(g(v));   // öne getir
    satirVurgu(id ?? null);
  };
  const imlec = r => {
    imlecR = r;
    const l = svg.querySelector(".yaris-imlec"); l.setAttribute("x1", X(r)); l.setAttribute("x2", X(r));
    svg.classList.toggle("geride", r < R);
    for (const id of L.takimlar) { const c = g(id)?.querySelector(".imlec-nokta"); if (c) { c.setAttribute("cx", X(r)); c.setAttribute("cy", Y(L.yaris.get(id)[r - 1])); } }
  };
  svg.addEventListener("pointerover", e => { const s = e.target.closest(".seri"); if (s) vurgula(L.takimlar.find(t => String(t) === s.dataset.t)); });
  svg.addEventListener("pointermove", e => {
    const s = e.target.closest(".seri"); if (!s) { ip.hidden = true; return; }
    const id = L.takimlar.find(t => String(t) === s.dataset.t), b = svg.getBoundingClientRect(), x = (e.clientX - b.left) / b.width * W;
    const r = Math.max(1, Math.min(R, Math.round((x - sol) / ((W - sol - sag) / (R - 1))) + 1));
    ip.innerHTML = `<div class="ipucu-bas">${r}. hafta</div><div class="ipucu-satir"><b>${L.yaris.get(id)[r - 1]}.</b> <span>${esc(adKisa(L, id))}</span></div>`;
    ip.hidden = false; const k = kap.getBoundingClientRect();
    ip.style.left = Math.min(k.width - ip.offsetWidth, e.clientX - k.left + 12) + "px"; ip.style.top = Math.max(0, e.clientY - k.top - ip.offsetHeight - 10) + "px";
  });
  svg.addEventListener("pointerleave", () => { ip.hidden = true; vurgula(null); });
  svg.addEventListener("click", e => { const s = e.target.closest(".seri"); if (s) secince(L.takimlar.find(t => String(t) === s.dataset.t)); });
  // ilk görünüşte çizgiler soldan sağa çizilir (bir kez; hareket azaltmada yok)
  if (!azHareket() && "IntersectionObserver" in window) {
    svg.classList.add("cizilecek");
    const io = new IntersectionObserver(es => { if (es.some(x => x.isIntersecting)) { svg.classList.add("ciz"); io.disconnect(); } }, { threshold: .25 });
    io.observe(svg);
  }
  return { imlec, vurgula };
}

// ---------------------------------------------------------------- sonuç matrisi: ev sahibi satır, konuk sütun
function matrisHtml(L, durum) {
  const sira = L.durum(L.sonHafta).map(x => x.id);
  const hucre = new Map();
  for (const m of L.ms) { const k = `${tid(m, "ev")}|${tid(m, "dep")}`; (hucre.get(k) || hucre.set(k, []).get(k)).push(m); }
  const kis = id => { const a = adKisa(L, id); return a.length > 3 ? a.slice(0, 3).toLocaleUpperCase("tr") : a.toLocaleUpperCase("tr"); };
  const bas = id => `<th data-t="${esc(id)}" class="mt-bas${durum.takim === id ? " secili" : ""}" title="${esc(adKisa(L, id))}" style="${renkStil(id)}">${typeof id === "number" && KULUP.get(id)?.logo ? logoImg(id) : `<span>${esc(kis(id))}</span>`}</th>`;
  return `<p class="soluk aciklama">Satır ev sahibi, sütun konuk. Renk ev sahibinin sonucu: yeşil galibiyet, sarı beraberlik, kırmızı mağlubiyet. Hücreye tıklayınca maç açılır (ayrıntısı olan maçlarda).</p>
  <div class="tablo-kap matris-sonuc-kap"><table class="matris-sonuc"><thead><tr><th class="mt-kose">Ev \\ Konuk</th>${sira.map(bas).join("")}</tr></thead><tbody>
  ${sira.map((a, r) => `<tr class="${durum.takim === a ? "secili" : ""}"><td data-t="${esc(a)}" class="mt-ad" style="${renkStil(a)}">${typeof a === "number" ? logoImg(a) : ""}<span>${esc(adKisa(L, a))}</span></td>${sira.map((b, c) => {
    if (a === b) return `<td class="mt-bos" data-r="${r}" data-c="${c}"></td>`;
    const l = hucre.get(`${a}|${b}`) || [];
    if (!l.length) return `<td data-r="${r}" data-c="${c}"></td>`;
    return `<td data-r="${r}" data-c="${c}" class="mt ${l.length === 1 ? (l[0].eg == null ? "N" : l[0].eg > l[0].dg ? "G" : l[0].eg < l[0].dg ? "M" : "B") : "cok"}${durum.takim === a || durum.takim === b ? " secili" : ""}" title="${esc(adKisa(L, a))} – ${esc(adKisa(L, b))}${l.map(m => `\n${tarihYaz(m.tarih)}: ${m.eg ?? "–"}-${m.dg ?? "–"}`).join("")}">${l.map(m => skorBag(m.id, m.eg == null ? "·" : `${m.eg}-${m.dg}`)).join("<br>")}</td>`;
  }).join("")}</tr>`).join("")}</tbody></table></div>`;
}

window.ligBolumu = ligBolumu;
})();

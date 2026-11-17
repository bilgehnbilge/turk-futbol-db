/* Kadın ligleri: sezonlar ve puan tabloları, kulüpler, oyuncular, maç ayrıntıları. Erkek verisinden tamamen ayrı.
   Veri: data/kadin/ (kadin_site.py; TFF arşivi pageID=848 ve maç sayfaları pageID=29).
   app.js'ten sonra yüklenir; $, esc, al, tarihYaz, sayiYaz, yuzde, sonuc, skorYaz, macCiz, temaUygula, takimTema, yollar app.js'ten gelir. */
(() => {
let KZ = null, KM = null, KOY = null;
const KK = new Map();
const kOzet = async () => {
  if (!KZ) { KZ = await al("data/kadin/ozet.json", { cache: "no-cache" }); for (const k of KZ.kulupler) KK.set(k.id, k); }
  return KZ;
};
const s_ = () => KZ.surum || "";
const kMaclar = async () => KM ||= (await al(`data/kadin/maclar.json?s=${s_()}`)).maclar.map(r => ({
  tff: r[0], tarih: r[1], sezon: r[2], kademe: r[3], lig: r[4], grup: r[5], asama: r[6], hafta: r[7], ev: r[8], dep: r[9],
  eg: r[10], dg: r[11], ep: r[12], dp: r[13], ayr: r[14], durum: r[15] }));
const kOyuncular = async () => KOY ||= (await al(`data/kadin/oyuncular.json?s=${s_()}`)).oyuncular.map(r => ({ kisi: r[0], ad: r[1], mac: r[2], gol: r[3], ilk: r[4], son: r[5], kulup: r[6] }));
const kAd = id => KK.get(id)?.ad ?? "?";
const kLogo = (id, cls = "logo-k") => { const l = KK.get(id)?.logo; return l ? `<img class="${cls}" src="logo/${l}.png" alt="" loading="lazy" onerror="this.remove()">` : ""; };
const kBag = (id, ayni) => id == null ? "?" : id === ayni ? `<span>${kLogo(id)}${esc(kAd(id))}</span>` : `<a class="bag" href="#/kadin/kulup/${id}">${kLogo(id)}${esc(kAd(id))}</a>`;
const kSkor = m => { const h = m.eg == null ? `<span class="soluk">${m.durum === "H" ? "hükmen" : "oynanmadı"}</span>` : skorYaz(m.eg, m.dg, m.ep, m.dp);
  return m.ayr ? `<a class="skor bagli" href="#/kadin/mac/${m.tff}" title="Maç ayrıntısı">${h}</a>` : h; };
const oyBag = (kisi, ad) => `<a class="oyuncu-bag" href="#/oyuncu/w${kisi}">${esc(ad)}</a>`;
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
async function kadinSayfa(sekme = "sezonlar") {
  document.title = "Kadın Futbolu · Türk Futbol Arşivi";
  icerik.innerHTML = `<div class="yukleniyor">Kadın ligleri yükleniyor…</div>`;
  const z = await kOzet();
  const SEK = [["sezonlar", "#/kadin", "Sezonlar"], ["kulupler", "#/kadin/kulupler", "Kulüpler"], ["oyuncular", "#/kadin/oyuncular", "Oyuncular"]];
  const ust = `${basOn("Kadın Futbolu", `TFF kadın ligleri, ${z.sezonlar[0]}'den bugüne. Erkek liglerinden ayrı tutulur; erkek takımıyla aynı kulüp olanlar "(Kadın)" ekiyle yazılır.`)}
    <div class="kart bolum"><div class="ozet-sat">
      <div><b>${sayiYaz(z.oynanan)}</b><span>Maç</span></div><div><b>${sayiYaz(z.kulupler.length)}</b><span>Kulüp</span></div>
      <div><b>${sayiYaz(z.oyuncu)}</b><span>Oyuncu</span></div><div><b>${z.sezonlar.length}</b><span>Sezon</span></div>
      <div><b>${sayiYaz(z.ayrintili)}</b><span>Kadrolu maç</span></div></div></div>
    ${sekmeler(SEK, sekme)}<div id="kadinIc"></div><p class="soluk not bolum">${NOT}</p>`;
  icerik.innerHTML = ust;
  const ic = $("#kadinIc");
  if (sekme === "sezonlar") {
    ic.innerHTML = `<div class="sezon-izgara">${[...z.sezonlar].reverse().map(s => `<a href="#/kadin/sezon/${s}">${s}</a>`).join("")}</div>
      <h2 class="bolum">Gol kralları</h2>
      <div class="tablo-kap"><table class="tablo"><thead><tr><th>Sezon</th><th class="ad">Lig</th><th class="ad">Oyuncu</th><th class="ad">Kulüp</th><th class="s">Gol</th></tr></thead><tbody>
      ${[...z.sezonlar].reverse().map(s => { const k = z.krallar[s]?.[1]; return k ? `<tr><td><a class="bag" href="#/kadin/sezon/${s}">${s}</a></td><td class="ad soluk">${esc(kademeAd(s, 1))}</td>
        <td class="ad">${k.map(x => oyBag(x[0], x[1])).join(", ")}</td><td class="ad">${k.map(x => kBag(x[3])).join(", ")}</td><td class="s"><b>${k[0][2]}</b></td></tr>` : ""; }).join("")}</tbody></table></div>`;
  } else if (sekme === "kulupler") {
    const ciz = () => {
      const q = norm(anaDurum.kulupAra);
      const l = z.kulupler.filter(k => !q || norm(k.ad).includes(q) || k.adlar.some(a => norm(a[0]).includes(q)));
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
  const gruplar = new Map();
  for (const m of km.filter(m => !m.asama)) (gruplar.get(m.grup) || gruplar.set(m.grup, []).get(m.grup)).push(m);
  const tabloHtml = ([grup, l]) => {
    const t = puanTablosu(l), oyn = l.filter(m => m.eg == null).length;
    return `<div class="kart puan-kart"><div class="bas"><h3>${esc(kademeAd(sezon, kad))}${grup ? ` · ${esc(/^\d+$/.test(grup) ? `${+grup}. grup` : grup)}` : ""}</h3>
      <span>${l.length} maç${oyn ? `, ${oyn} oynanmadı` : ""}</span></div>
      <table class="tablo"><thead><tr><th class="s">#</th><th>Takım</th><th class="s">O</th><th class="s ek2">G</th><th class="s ek2">B</th><th class="s ek2">M</th><th class="s ek">AG</th><th class="s ek">YG</th><th class="s">Av</th><th class="s">P</th></tr></thead>
      <tbody>${t.map((x, i) => `<tr><td class="s soluk">${i + 1}</td><td class="takim" title="${esc(kAd(x.id))}">${kBag(x.id)}</td><td class="s">${x.O}</td><td class="s ek2">${x.G}</td><td class="s ek2">${x.B}</td><td class="s ek2">${x.M}</td><td class="s ek">${x.AG}</td><td class="s ek">${x.YG}</td><td class="s">${x.Av > 0 ? "+" : ""}${x.Av}</td><td class="s p">${x.P}</td></tr>`).join("")}</tbody></table>
      <details><summary>Maçlar</summary>${macListe(l)}</details></div>`;
  };
  const po = new Map();
  for (const m of km.filter(m => m.asama)) { const k = m.asama === "play-off" ? "Play-off maçları" : m.asama; (po.get(k) || po.set(k, []).get(k)).push(m); }
  const kral = z.krallar[sezon]?.[kad];
  icerik.innerHTML = `
  <div class="sayfa-bas"><h1>Kadın ligleri ${esc(sezon)}</h1>
    <div class="yan-yana">${onceki ? `<a class="cip" href="#/kadin/sezon/${onceki}">← ${onceki}</a>` : ""}${sonraki ? `<a class="cip" href="#/kadin/sezon/${sonraki}">${sonraki} →</a>` : ""}</div></div>
  <p class="soluk"><a class="bag" href="#/kadin">Kadın Futbolu</a> · ${ms.length} maç · Puan tabloları sonuçlardan hesaplandı (galibiyet 3 puan; puan silme cezaları dahil değil).</p>
  ${sekmeler(kademeler.map(k => [k, `#/kadin/sezon/${sezon}/${k}`, esc(kademeAd(sezon, k))]), kad)}
  ${kral ? `<p class="bolum">⚽ Gol kralı: ${kral.map(x => `${oyBag(x[0], x[1])} <span class="soluk">(${kBag(x[3])})</span>`).join(", ")} · <b>${kral[0][2]} gol</b></p>` : ""}
  <div class="izgara puan">${[...gruplar].sort((a, b) => a[0].localeCompare(b[0], "tr", { numeric: true })).map(tabloHtml).join("")}</div>
  ${po.size ? `<h2 class="bolum">Play-off ve final maçları</h2>${[...po].map(([k, l]) => `<div class="kart" style="margin-bottom:12px"><h3>${esc(k)}${l[0].grup ? ` · ${esc(l[0].grup)}` : ""}</h3>${macListe(l)}</div>`).join("")}` : ""}
  <p class="soluk not bolum">${NOT}</p>`;
}

// ---------------------------------------------------------------- kulüp
const kulupDurum = { sezon: "" };
async function kadinKulup(id) {
  icerik.innerHTML = `<div class="yukleniyor">Kulüp yükleniyor…</div>`;
  const z = await kOzet(), k = KK.get(id);
  if (!k) { icerik.innerHTML = `<div class="bos">Kulüp bulunamadı.</div>`; return; }
  document.title = `${k.ad} · Türk Futbol Arşivi`;
  temaUygula(k);
  const tum = await kMaclar(), ms = tum.filter(m => m.ev === id || m.dep === id);
  const oy = await al(`data/kadin/k/${id}.json?s=${s_()}`).catch(() => ({ oyuncular: [] }));
  const T = ms.reduce((t, m) => { if (m.eg == null) return t; const [a, y] = m.ev === id ? [m.eg, m.dg] : [m.dg, m.eg]; t.O++; t.AG += a; t.YG += y; t[sonuc(a, y)]++; return t; }, { O: 0, G: 0, B: 0, M: 0, AG: 0, YG: 0 });
  // sezon sezon: ligdeki yeri (grubunun puan tablosundan)
  const sezonlar = [...new Set(ms.map(m => m.sezon))].sort().reverse();
  const sezonSat = sezonlar.map(s => {
    const lm = ms.find(m => m.sezon === s && !m.asama);
    if (!lm) return { s };
    const grup = tum.filter(m => m.sezon === s && !m.asama && m.kademe === lm.kademe && m.grup === lm.grup);
    const t = puanTablosu(grup), sira = t.findIndex(x => x.id === id);
    return { s, kademe: lm.kademe, grup: lm.grup, sira: sira + 1, n: t.length, x: t[sira] };
  });
  const ciz = () => {
    const l = ms.filter(m => !kulupDurum.sezon || m.sezon === kulupDurum.sezon).reverse();
    $("#kkMac").innerHTML = macListe(l, id);
  };
  const tema = takimTema(k);
  icerik.innerHTML = `
  <div class="sayfa-bas"><div><h1>${k.logo ? `<img src="logo/${k.logo}.png" alt="" style="height:44px;vertical-align:middle;margin-right:12px">` : ""}${esc(k.ad)}</h1>
    <p class="soluk"><a class="bag" href="#/kadin">Kadın Futbolu</a> · ${k.ilk?.slice(0, 4)}–${k.son?.slice(5)} · ${ms.length} maç${k.erkek != null ? ` · <a class="bag" href="#/kulup/${k.erkek}">Erkek takımı →</a>` : ""}</p>
    ${k.adlar.length > 1 || (k.adlar[0] && k.adlar[0][0] !== k.ad) ? `<p class="soluk">TFF'deki adları: ${k.adlar.map(a => `${esc(a[0])} <small>(${a[1].slice(0, 4)}–${a[2].slice(5)})</small>`).join(" · ")}</p>` : ""}</div></div>
  <div class="kart bolum"><div class="ozet-sat">
    <div><b>${T.O}</b><span>Maç</span></div><div><b>${T.G}</b><span>Galibiyet</span></div><div><b>${T.B}</b><span>Beraberlik</span></div>
    <div><b>${T.M}</b><span>Mağlubiyet</span></div><div><b>${T.AG}</b><span>Attığı gol</span></div><div><b>${T.YG}</b><span>Yediği gol</span></div>
    <div><b>%${yuzde(T.G, T.O)}</b><span>Kazanma</span></div></div>
    <div class="cubuk"><i class="g" style="width:${yuzde(T.G, T.O)}%"></i><i class="b" style="width:${yuzde(T.B, T.O)}%"></i><i class="m" style="width:${yuzde(T.M, T.O)}%"></i></div></div>
  <h2 class="bolum">Sezon sezon</h2>
  <div class="tablo-kap"><table class="tablo"><thead><tr><th>Sezon</th><th class="ad">Lig</th><th class="s">Sıra</th><th class="s">O</th><th class="s">G</th><th class="s">B</th><th class="s">M</th><th class="s">AG</th><th class="s">YG</th><th class="s">P</th></tr></thead><tbody>
  ${sezonSat.map(r => `<tr><td><a class="bag" href="#/kadin/sezon/${r.s}${r.kademe ? "/" + r.kademe : ""}">${r.s}</a></td>${r.x ? `<td class="ad">${esc(kademeAd(r.s, r.kademe))}${r.grup ? ` <span class="soluk">· ${esc(/^\d+$/.test(r.grup) ? `${+r.grup}. grup` : r.grup)}</span>` : ""}</td>
    <td class="s"><b>${r.sira}</b><span class="soluk">/${r.n}</span></td><td class="s">${r.x.O}</td><td class="s">${r.x.G}</td><td class="s">${r.x.B}</td><td class="s">${r.x.M}</td><td class="s">${r.x.AG}</td><td class="s">${r.x.YG}</td><td class="s"><b>${r.x.P}</b></td>` : `<td class="ad soluk" colspan="9">yalnız play-off / final maçları</td>`}</tr>`).join("")}</tbody></table></div>
  ${oy.oyuncular.length ? `<h2 class="bolum">Oyuncular</h2>
  <div class="izgara iki ust-hiza">
    <div class="tablo-kap"><table class="tablo"><thead><tr><th class="ad">En çok maça çıkanlar</th><th>Yıllar</th><th class="s">Maç</th><th class="s">Gol</th></tr></thead><tbody>
      ${oy.oyuncular.slice(0, 25).map(p => `<tr><td class="ad">${oyBag(p[0], p[1])}</td><td class="soluk">${p[4].slice(0, 4)}–${p[5].slice(5)}</td><td class="s"><b>${p[2]}</b></td><td class="s">${p[3]}</td></tr>`).join("")}</tbody></table></div>
    <div class="tablo-kap"><table class="tablo"><thead><tr><th class="ad">En golcüler</th><th>Yıllar</th><th class="s">Maç</th><th class="s">Gol</th></tr></thead><tbody>
      ${[...oy.oyuncular].sort((a, b) => b[3] - a[3] || a[2] - b[2]).slice(0, 25).filter(p => p[3]).map(p => `<tr><td class="ad">${oyBag(p[0], p[1])}</td><td class="soluk">${p[4].slice(0, 4)}–${p[5].slice(5)}</td><td class="s">${p[2]}</td><td class="s"><b>${p[3]}</b></td></tr>`).join("")}</tbody></table></div>
  </div>` : ""}
  <h2 class="bolum">Maçlar</h2>
  <div class="filtre"><select id="kkSezon"><option value="">Bütün sezonlar</option>${sezonlar.map(s => `<option ${s === kulupDurum.sezon ? "selected" : ""}>${s}</option>`).join("")}</select></div>
  <div id="kkMac"></div>
  <p class="soluk not bolum">${NOT}</p>`;
  $("#kkSezon").addEventListener("change", e => { kulupDurum.sezon = e.target.value; ciz(); });
  if (kulupDurum.id !== id) { kulupDurum.id = id; kulupDurum.sezon = ""; $("#kkSezon").value = ""; }
  ciz();
}

// ---------------------------------------------------------------- maç
async function kadinMac(tff) {
  icerik.innerHTML = `<div class="yukleniyor">Maç yükleniyor…</div>`;
  await kOzet();
  const m = (await kMaclar()).find(x => x.tff === tff);
  const b = await al(`data/kadin/m/${tff % 250}.json?s=${s_()}`).catch(() => null), r = b?.mac[tff];
  if (!m || !r) { icerik.innerHTML = `<div class="bos">Bu maçın ayrıntısı yok.</div>`; return; }
  const ad = k => b.ad[k] || "";
  const TUR = { Y: "YELLOW_CARD", R: "RED_CARD", YR: "YELLOW_CARD_SECOND", S: "SUBSTITUTION", G: "GOAL" };
  const hakem = r.h.find(h => h[1] === "Hakem");
  macCiz({
    tarih: m.tarih, sezon: m.sezon, ev: [m.ev, kAd(m.ev)], dep: [m.dep, kAd(m.dep)], skor: [m.eg, m.dg, m.ep, m.dp, null],
    stad: r.s, kaynak: "TFF", tff, uyum: r.u, oyuncuOnek: "w", hakem: hakem ? hakem[0] : null, hakemler: r.h,
    kulupHref: kid => kid != null && KK.has(kid) ? `#/kadin/kulup/${kid}` : null, kulupBilgi: kid => KK.get(kid),
    ustHtml: `<a class="bag" href="#/kadin">Kadın</a> · <a class="bag" href="#/kadin/sezon/${m.sezon}/${m.kademe}">${esc(m.sezon)}</a> · ${esc(m.lig)}${m.grup ? ` · ${esc(/^\d+$/.test(m.grup) ? `${+m.grup}. grup` : m.grup)}` : ""}${m.asama ? ` · ${esc(m.asama)}` : ""}`,
    kadro: r.k.map(l => l.map(([forma, k, ilk11]) => [forma, ad(k), ilk11, 0, k])),
    teknik: r.t, olay: r.o.map(([taraf, tur, dk, ek, k1, k2, tip]) => [taraf, TUR[tur], dk, ek || null, ad(k1), k2 ? ad(k2) : null,
      tip === "P" ? "PENALTY" : tip === "K" ? "OWN" : tip === "H" ? "HEADER" : null, k1, k2]),
  });
}

// ---------------------------------------------------------------- oyuncu
async function kadinOyuncu(kisi) {
  icerik.innerHTML = `<div class="yukleniyor">Yükleniyor…</div>`;
  const z = await kOzet();
  const d = await al(`data/kadin/o/${kisi % 250}.json?s=${s_()}`), p = d.oyuncu[kisi];
  if (!p) { icerik.innerHTML = `<div class="bos">Oyuncu bulunamadı.</div>`; return; }
  document.title = `${p.ad} · Türk Futbol Arşivi`;
  const S = p.s.map(r => ({ sezon: r[0], kulup: r[1], kademe: r[2], mac: r[3], ilk: r[4], gol: r[5], pen: r[6], sari: r[7], kirmizi: r[8] }));
  const topla = l => l.reduce((t, r) => { for (const k of ["mac", "ilk", "gol", "pen", "sari", "kirmizi"]) t[k] += r[k]; return t; }, { mac: 0, ilk: 0, gol: 0, pen: 0, sari: 0, kirmizi: 0 });
  const T = topla(S);
  const grupla = (l, f) => [...l.reduce((m, r) => { const k = f(r); return m.set(k, [...(m.get(k) || []), r]); }, new Map())];
  const hucre = t => `<td class="s">${t.mac}</td><td class="s">${t.ilk}</td><td class="s"><b>${t.gol || ""}</b></td><td class="s">${t.pen || ""}</td><td class="s">${t.sari || ""}</td><td class="s">${t.kirmizi || ""}</td>`;
  const bas = ek => `<thead><tr>${ek.map((x, i) => `<th${i ? ' class="ad"' : ""}>${x}</th>`).join("")}<th class="s">Maç</th><th class="s" title="İlk 11'de başladığı maç">İlk 11</th><th class="s">Gol</th><th class="s" title="Penaltıdan gol">Pen.</th><th class="s" title="Sarı kart">Sarı</th><th class="s" title="Kırmızı kart (ikinci sarıdan dahil)">Kırm.</th></tr></thead>`;
  const kulupler = grupla(S, r => r.kulup).sort((a, b) => topla(b[1]).mac - topla(a[1]).mac);
  const sezonlar = grupla(S, r => `${r.sezon}|${r.kulup}`).sort((a, b) => b[0].localeCompare(a[0]));
  const ilk = S.reduce((a, r) => a < r.sezon ? a : r.sezon, "9999"), son = S.reduce((a, r) => a > r.sezon ? a : r.sezon, "");
  icerik.innerHTML = `
  <div class="sayfa-bas"><div><h1>${esc(p.ad)}</h1>
    <p class="soluk"><a class="bag" href="#/kadin/oyuncular">Kadın Futbolu</a> · ${ilk.slice(0, 4)}–${son.slice(5)} · ${kulupler.map(([k]) => kBag(k)).join(", ")}</p></div></div>
  <div class="kart bolum"><div class="ozet-sat">
    <div><b>${sayiYaz(T.mac)}</b><span>Maç</span></div><div><b>${sayiYaz(T.ilk)}</b><span>İlk 11</span></div><div><b>${T.gol}</b><span>Gol</span></div>
    <div><b>${T.pen}</b><span>Penaltı golü</span></div><div><b>${T.sari}</b><span>Sarı kart</span></div><div><b>${T.kirmizi}</b><span>Kırmızı kart</span></div>
    <div><b>${T.mac ? (T.gol / T.mac).toFixed(2) : "–"}</b><span>Maç başı gol</span></div></div></div>
  <div class="tablo-kap bolum"><table class="tablo">${bas(["Kulüp"])}<tbody>${kulupler.map(([k, l]) => `<tr><td class="ad">${kBag(+k)}</td>${hucre(topla(l))}</tr>`).join("")}
    ${kulupler.length > 1 ? `<tr class="toplam"><td class="ad"><b>Toplam</b></td>${hucre(T)}</tr>` : ""}</tbody></table></div>
  <h2 class="bolum">Sezon sezon</h2>
  <div class="tablo-kap"><table class="tablo">${bas(["Sezon", "Kulüp", "Lig"])}<tbody>${sezonlar.map(([k, l]) => {
    const [sz, kid] = k.split("|");
    return `<tr><td><a class="bag" href="#/kadin/sezon/${sz}">${sz}</a></td><td class="ad">${kBag(+kid)}</td><td class="ad soluk">${[...new Set(l.map(r => r.kademe ? kademeAd(sz, r.kademe) : "Play-off / final"))].join(", ")}</td>${hucre(topla(l))}</tr>`;
  }).join("")}</tbody></table></div>
  <p class="soluk not">Kaynak: <a class="bag" href="https://www.tff.org/Default.aspx?pageId=30&kisiId=${kisi}" target="_blank" rel="noopener">TFF</a> maç sayfaları (kadın ligleri). Oyun dışında kalan yedekler maç sayılmaz; kendi kalesine goller ve seri penaltılar gole katılmaz.</p>`;
}

yollar.splice(yollar.length - 1, 0,
  [/^#\/kadin$/, () => kadinSayfa("sezonlar")],
  [/^#\/kadin\/(kulupler|oyuncular)$/, s => kadinSayfa(s)],
  [/^#\/kadin\/sezon\/([\d-]+)(?:\/(\d))?$/, (s, k) => kadinSezon(s, k)],
  [/^#\/kadin\/kulup\/(\d+)$/, id => kadinKulup(+id)],
  [/^#\/kadin\/mac\/(\d+)$/, id => kadinMac(+id)],
  [/^#\/oyuncu\/w(\d+)$/, id => kadinOyuncu(+id)]);
})();

/* 1959 öncesi: Türkiye Futbol Şampiyonası (1924-1951), Millî Küme (1937-1951), Başbakanlık Kupası (1944-1950),
   Federasyon Kupası (1956-1958) ve 1924 İstanbul Ligi. Veri: data/eski.json (eski_site.py; kaynak RSSSF, Baki Demirkiran).
   Bu maçlar resmî lig istatistiklerine, rekorlara ve kulüp sayfalarındaki sayılara katılmaz.
   app.js'ten sonra yüklenir; $, esc, al, KULUP, kulupBag, logoImg, tarihYaz, sayiYaz, icerik, yollar app.js'ten gelir. */
(() => {
let ESKI = null;
const eskiAl = async () => ESKI ||= await al("data/eski.json");
const YAR_RENK = { milli_kume: "var(--vurgu)", sampiyona: "var(--g)", basbakanlik: "var(--b)", federasyon: "var(--m)", istanbul: "var(--s1)", ankara: "var(--s2)", izmir: "var(--s3)",
  istanbul2: "var(--soluk)", ankara2: "var(--soluk)", diger: "var(--yazi2)" };

// eski kulüp: sitedeki kulübe bağlıysa onun sayfasına (logosuyla), değilse düz ad
const kAd = (d, i) => { const k = d.kulupler[i]; return k ? k.ad : "?"; };
const eLogo = k => k?.logo ? `<img class="logo-k" src="logo/${k.logo}.png" alt="" loading="lazy" onerror="this.remove()">` : "";   // sitede kulübü olmayan eski kulüp
const kBag = (d, i) => { const k = d.kulupler[i]; if (!k) return "?";
  if (k.kulup != null && KULUP.has(k.kulup)) return kulupBag(k.kulup, k.ad);
  const o = k.ayni != null ? d.kulupler[k.ayni] : null;   // aynı kulübün öbür dönem adı (Harbiye = Harp Okulu)
  return o ? `<span title="Aynı kulüp: ${esc(o.ad)}">${eLogo(k)}${esc(k.ad)}</span>` : eLogo(k) + esc(k.ad); };
const yarAd = (d, y) => (d.yarismalar.find(x => x[0] === y) || [, y])[1];
const sezonAd = s => s.length === 4 ? s : s.replace("-", "–");
const ust = (baslik, alt) => `<p class="soluk ust-bag"><a class="bag" href="#/sezonlar">Sezonlar</a> · <a class="bag" href="#/eski">1959 öncesi</a></p>
  <h1>${baslik}</h1>${alt ? `<p class="soluk">${alt}</p>` : ""}`;
const KAYNAK = `<p class="soluk not bolum">Kaynak: <a class="bag" href="https://www.rsssf.org/tablest/turkhist.html" target="_blank" rel="noopener">RSSSF</a> (Baki Demirkiran); ayrı maddesi olan maçların golcüleri <a class="bag" href="https://tr.wikipedia.org/wiki/Kategori:T%C3%BCrkiye_futbol_kul%C3%BCplerinin_ma%C3%A7lar%C4%B1" target="_blank" rel="noopener">Vikipedi</a>'den. İstanbul, Ankara ve İzmir lig maçları (tarih, kadro, gol) <a class="bag" href="https://arsiv.mackolik.com" target="_blank" rel="noopener">Maçkolik arşivinden</a>. Bu maçlar 1959'da başlayan profesyonel ligin istatistiklerine ve kulüp sayfalarındaki sayılara katılmaz; Rekorlar'ın "1959 öncesi dahil" sekmesinde yer alır. Gol atanlar Başbakanlık Kupası, bazı finaller, Vikipedi'de ayrı maddesi olan maçlar ve Maçkolik'te kadrosu olan lig maçlarında var.</p>`;

async function eskiSayfa() {
  document.title = "1959 öncesi · Türk Futbol Arşivi";
  const d = await eskiAl();
  const yillar = [...new Set(d.sezonlar.map(s => s.sezon))];
  const say = new Map();   // kulüp -> şampiyonluk sayısı (Millî Küme + Türkiye Şampiyonası)
  for (const s of d.sezonlar) if (s.sampiyon != null && (s.yarisma === "milli_kume" || s.yarisma === "sampiyona")) say.set(s.sampiyon, (say.get(s.sampiyon) || 0) + 1);
  const top = [...say].sort((a, b) => b[1] - a[1]);
  const mac = d.sezonlar.reduce((n, s) => n + s.maclar.length, 0);
  icerik.innerHTML = `${ust("1959 öncesi", `Millî Lig'den önceki yarışmalar ve şehir ligleri · ${yillar[0]} – ${sezonAd(yillar.at(-1))} · ${sayiYaz(mac)} maç`)}
  <div class="izgara iki bolum">${d.yarismalar.filter(([k]) => d.sezonlar.some(s => s.yarisma === k)).map(([k, ad, ac]) => {
    const l = d.sezonlar.filter(s => s.yarisma === k);
    return `<div class="kart"><h2 class="h3" style="box-shadow:inset 3px 0 0 ${YAR_RENK[k]};padding-left:10px">${esc(ad)}</h2>
      <p class="soluk">${esc(ac)}</p>
      ${k === "diger" ? `<table class="tablo"><thead><tr><th>Tarih</th><th class="ad">Maç</th></tr></thead><tbody>
      ${l.flatMap(s => s.maclar.map((m, i) => `<tr><td><a class="bag" href="#/eski/${k}/${s.sezon}">${tarihYaz(m[5])}</a></td><td class="ad">${kBag(d, m[0])} ${skorBagE(k, s.sezon, i, m, `<b>${m[2]}-${m[3]}</b>`)} ${kBag(d, m[1])}</td></tr>`)).join("")}
      </tbody></table></div>` : `<table class="tablo"><thead><tr><th>Sezon</th><th class="ad">Şampiyon</th><th class="s">Maç</th></tr></thead><tbody>
      ${l.map(s => `<tr><td><a class="bag" href="#/eski/${k}/${s.sezon}">${sezonAd(s.sezon)}</a></td><td class="ad">${s.sampiyon != null ? kBag(d, s.sampiyon) : "<span class='soluk'>—</span>"}</td><td class="s">${s.maclar.length}</td></tr>`).join("")}
      </tbody></table></div>`}`;
  }).join("")}</div>
  <h2 class="bolum">En çok şampiyonluk</h2>
  <p class="soluk not">Millî Küme ve Türkiye Futbol Şampiyonası birlikte.</p>
  <div class="tablo-kap"><table class="tablo"><thead><tr><th class="s">#</th><th class="ad">Kulüp</th><th class="s">Millî Küme</th><th class="s">Türkiye Şamp.</th><th class="s">Toplam</th></tr></thead><tbody>
  ${top.map(([k, n], i) => { const mk = d.sezonlar.filter(s => s.yarisma === "milli_kume" && s.sampiyon === k).length;
    return `<tr><td class="s">${i + 1}</td><td class="ad">${kBag(d, k)}</td><td class="s">${mk || ""}</td><td class="s">${n - mk || ""}</td><td class="s"><b>${n}</b></td></tr>`; }).join("")}
  </tbody></table></div>
  ${KAYNAK}`;
}

// goller: [ad, dakika, tip, taraf]; aynı oyuncunun golleri birleşir ("Celal İbrahim 4", "Necdet 15', 80', 89'")
const golHtml = (d, m) => [1, 2].map(t => {
  const l = m[11].filter(g => g[3] === t); if (!l.length) return "";
  const by = new Map(); for (const g of l) (by.get(g[0]) || by.set(g[0], []).get(g[0])).push(g);
  return `${esc(kAd(d, m[t - 1]))}: ${[...by].map(([ad, gs]) => `${esc(ad)} ${(() => { const b = gs.filter(g => g[1] != null), n = gs.length - b.length;   // dakikası bilinmeyenler sayıyla: "5', 9' +1"
    return b.length ? b.map(g => `${g[1]}'${g[2] === "pen" ? " (pen.)" : g[2] === "og" ? " (k.k.)" : ""}`).join(", ") + (n ? ` +${n}` : "") : n > 1 ? n : ""; })()}`.trim()).join(", ")}`;
}).filter(Boolean).join(" · ");
// maç sayfası (sitenin ortak maç düzeni, macCiz): kadrosu ya da golcüsü bilinen maçlar; #/eski/mac/<yarışma>/<sezon>/<sıra>
const macVar = m => m[11]?.length || m[13];
const macHref = (y, sz, i) => `#/eski/mac/${y}/${sz}/${i}`;
const skorBagE = (y, sz, i, m, html) => macVar(m) ? `<a class="skor bagli" href="${macHref(y, sz, i)}" title="Maç ayrıntısı">${html}</a>` : html;
async function eskiMacSayfa(y, sz, i) {
  icerik.innerHTML = `<div class="yukleniyor">Maç yükleniyor…</div>`;
  const d = await eskiAl(), s = d.sezonlar.find(x => x.yarisma === y && x.sezon === sz), m = s?.maclar[+i];
  if (!m) { icerik.innerHTML = `<div class="bos">Bu maçın ayrıntısı yok.</div>`; return; }
  // kulüp kimliği: sitedeki kulüp no ya da "e<sıra>" (sitede sayfası olmayan eski kulüp)
  const kid = t => { const k = d.kulupler[m[t]]; return k?.kulup != null && KULUP.has(k.kulup) ? k.kulup : `e${m[t]}`; };
  const k = m[13] || [[], [], [], []];
  // goller: taraf golün yazıldığı takım (olayLehine); değişiklikler kadrodaki giriş/çıkış dakikalarından eşlenir
  const olay = (m[11] || []).map(g => [g[3], "GOAL", g[1], null, g[0], null, g[2] === "pen" ? "PENALTY" : g[2] === "og" ? "OWN" : null, null, null]);
  [0, 1].forEach(t => {
    const gir = k[t].filter(p => p[2] != null).sort((a, b) => a[2] - b[2]), cik = k[t].filter(p => p[3] != null).sort((a, b) => a[3] - b[3]);
    gir.forEach((p, j) => olay.push([t + 1, "SUBSTITUTION", p[2], null, cik[j]?.[0] || null, p[0], null, null, null]));
  });
  olay.sort((a, b) => (a[2] ?? 999) - (b[2] ?? 999));
  const kaynak = m[12] ? "Vikipedi" : m[13] ? "Maçkolik" : "RSSSF";
  macCiz({
    tarih: m[5], saat: null, sezon: sz, lig: yarAd(d, y), tur: m[4], ev: [kid(0), kAd(d, m[0])], dep: [kid(1), kAd(d, m[1])],
    skor: [m[2], m[3], null, null, m[6] || "MS"], stad: m[9] ? `${m[9]}` : null, sehir: m[8] || null, hakem: m[10],
    ustHtml: `<a class="bag" href="#/eski">1959 öncesi</a> · <a class="bag" href="#/eski/${y}/${sz}">${esc(yarAd(d, y))} ${sezonAd(sz)}</a>${m[4] ? ` · ${esc(m[4])}` : ""}`,
    kulupHref: id => typeof id === "number" ? `#/kulup/${id}` : null,
    kulupBilgi: id => typeof id === "number" ? KULUP.get(id) : { ad: d.kulupler[+id.slice(1)]?.ad, logo: d.kulupler[+id.slice(1)]?.logo },
    kaynak, madde: m[12], olayLehine: true, hikaye: m[15],
    ekNot: m[16] ? `Ek bilgi ve maçın hikâyesi: <a class="bag" href="${esc(m[16][1])}" target="_blank" rel="noopener">${esc(m[16][0])}</a>.` : null,
    kadro: [0, 1].map(t => k[t].map(p => ["", p[0], p[1], 0, null])), teknik: [k[2] || [], k[3] || []], olay,
  });
}
const wikiBag = madde => `<a class="bag" href="https://tr.wikipedia.org/wiki/${encodeURIComponent(madde.replace(/ /g, "_"))}" target="_blank" rel="noopener">Vikipedi maddesi</a>`;
const skorHtml = m => m[2] == null ? `<span class="soluk">${esc({ abd: "yarıda kaldı", "o/w": "hükmen", "w/o": "hükmen", awd: "hükmen", "n/p": "oynanmadı" }[m[6]] || m[6] || "–")}</span>` : `<b>${m[2]}-${m[3]}</b>`;

async function eskiSezonSayfa(y, sz) {
  const d = await eskiAl();
  const s = d.sezonlar.find(x => x.yarisma === y && x.sezon === sz);
  if (!s) { icerik.innerHTML = `<div class="bos">Bu sezon bulunamadı.</div>`; return; }
  const ad = yarAd(d, y);
  document.title = `${ad} ${sezonAd(sz)} · Türk Futbol Arşivi`;
  const ayni = d.sezonlar.filter(x => x.yarisma === y), i = ayni.indexOf(s);
  const gez = `<div class="sezon-gez">${i > 0 ? `<a class="dugme" href="#/eski/${y}/${ayni[i - 1].sezon}">← ${sezonAd(ayni[i - 1].sezon)}</a>` : ""}${i < ayni.length - 1 ? `<a class="dugme" href="#/eski/${y}/${ayni[i + 1].sezon}">${sezonAd(ayni[i + 1].sezon)} →</a>` : ""}</div>`;
  const gol = s.maclar.reduce((n, m) => n + (m[2] ?? 0) + (m[3] ?? 0), 0), oyn = s.maclar.filter(m => m[2] != null).length;
  // puan tablosu (RSSSF'nin verdiği gibi; o yılların puan sistemi: galibiyet 3, beraberlik 2, mağlubiyet 1 puan)
  const tablo = (s.tablo || []).map(t => `${t.tur && t.tur !== "Lig" ? `<h3 class="bolum">${esc(t.tur)}</h3>` : ""}
    <div class="tablo-kap"><table class="tablo"><thead><tr><th class="s">#</th><th class="ad">Kulüp</th><th class="s">O</th><th class="s">G</th><th class="s">B</th><th class="s">M</th><th class="s">AG</th><th class="s">YG</th><th class="s">Av</th><th class="s">P</th></tr></thead><tbody>
    ${t.satir.map(r => `<tr><td class="s">${r[0]}</td><td class="ad">${r[1] != null ? kBag(d, r[1]) : esc(r[2])}</td>${[3, 4, 5, 6, 7, 8].map(k => `<td class="s">${r[k]}</td>`).join("")}<td class="s">${r[7] - r[8] > 0 ? "+" : ""}${r[7] - r[8]}</td><td class="s"><b>${r[9]}</b></td></tr>`).join("")}
    </tbody></table></div>`).join("");
  // Millî Küme: sonuç tablosu (ev sahibi satır); öbürleri: tur tur maç listesi
  let maclar;
  if (y === "milli_kume") {
    const sira = (s.tablo?.[0]?.satir || []).map(r => r[1]).filter(x => x != null);
    const kul = sira.length ? sira : [...new Set(s.maclar.flatMap(m => [m[0], m[1]]))];
    const h = new Map(); for (const m of s.maclar) if (m[2] != null) h.set(`${m[0]}|${m[1]}`, m);
    const kis = i => { const a = kAd(d, i); return a.length > 3 ? a.slice(0, 3).toLocaleUpperCase("tr") : a.toLocaleUpperCase("tr"); };
    const lg = i => { const k = d.kulupler[i]; return k?.kulup != null && kulupLogo(k.kulup, k.ad) ? logoImg(k.kulup, "logo-k", k.ad) : eLogo(k); };
    maclar = `<h2 class="bolum">Sonuçlar</h2><p class="soluk aciklama">Satır ev sahibi, sütun konuk. Renk ev sahibinin sonucu: yeşil galibiyet, sarı beraberlik, kırmızı mağlubiyet. Maç tarihleri kaynakta yok.</p>
    <div class="tablo-kap matris-sonuc-kap"><table class="matris-sonuc"><thead><tr><th class="mt-kose">Ev \\ Konuk</th>${kul.map(k => `<th class="mt-bas" title="${esc(kAd(d, k))}">${lg(k) || `<span>${esc(kis(k))}</span>`}</th>`).join("")}</tr></thead><tbody>
    ${kul.map(a => `<tr><td class="mt-ad">${lg(a)}<span>${esc(kAd(d, a))}</span></td>${kul.map(b => {
      if (a === b) return `<td class="mt-bos"></td>`;
      const m = h.get(`${a}|${b}`); if (!m) return `<td></td>`;
      const sk = macVar(m) ? `<a href="${macHref(y, sz, s.maclar.indexOf(m))}">${m[2]}-${m[3]}</a>` : `${m[2]}-${m[3]}`;
      return `<td class="mt ${m[2] > m[3] ? "G" : m[2] < m[3] ? "M" : "B"}" title="${esc(kAd(d, a))} – ${esc(kAd(d, b))}">${sk}</td>`;
    }).join("")}</tr>`).join("")}</tbody></table></div>`;
    const ek = s.maclar.filter(m => m[2] == null || m[7]);
    if (ek.length) maclar += `<p class="soluk not">${ek.map(m => `${esc(kAd(d, m[0]))} – ${esc(kAd(d, m[1]))}: ${esc(m[7] || m[6] || "")}`).join("<br>")}</p>`;
    const gl = s.maclar.filter(m => m[11]?.length);
    if (gl.length) maclar += `<div class="kart bolum"><h3 class="h3">Golcüleri bilinen maçlar</h3>${gl.map(m => `<p><b>${esc(kAd(d, m[0]))} ${skorBagE(y, sz, s.maclar.indexOf(m), m, `${m[2]}-${m[3]}`)} ${esc(kAd(d, m[1]))}</b>${m[5] ? ` <span class="soluk">· ${tarihYaz(m[5])}</span>` : ""}<br><span class="soluk kucuk">${golHtml(d, m)}${m[12] ? ` · ${wikiBag(m[12])}` : ""}</span></p>`).join("")}</div>`;
  } else {
    const turlar = []; for (const m of s.maclar) { const t = m[4] || "Maçlar"; let g = turlar.at(-1); if (!g || g.tur !== t) turlar.push(g = { tur: t, ms: [] }); g.ms.push(m); }
    maclar = `<h2 class="bolum">Maçlar</h2>${turlar.map(g => `<div class="kart bolum eski-tur"><h3 class="h3">${esc(g.tur)}${g.ms[0][5] ? ` <span class="soluk">· ${tarihYaz(g.ms[0][5])}</span>` : ""}</h3>
      <table class="tablo eski-maclar"><tbody>${g.ms.map(m => {
        const ayr = [m[8], m[5] && m[5] !== g.ms[0][5] ? tarihYaz(m[5]) : "", m[9] ? `Stat: ${m[9]}` : "", m[10] ? `Hakem: ${m[10]}` : "", m[7]].filter(Boolean).map(esc);
        if (m[11]?.length) ayr.push(golHtml(d, m));
        if (m[12]) ayr.push(wikiBag(m[12]));
        return `<tr${ayr.length ? ` class="ayr-var"` : ""}><td class="ad sag">${kBag(d, m[0])}</td><td class="s skor-h">${skorBagE(y, sz, s.maclar.indexOf(m), m, skorHtml(m))}</td><td class="ad">${kBag(d, m[1])}</td></tr>
        ${ayr.length ? `<tr class="eski-ayr"><td colspan="3" class="soluk kucuk">${ayr.join(" · ")}</td></tr>` : ""}`; }).join("")}</tbody></table></div>`).join("")}`;
  }
  const kral = s.kral.length ? `<div class="kart"><h2 class="h3">Gol kralı</h2>${s.kral.map(k => `<p><b>${esc(k[0])}</b> <span class="soluk">(${esc(k[1])})</span> · ${k[2]} gol</p>`).join("")}</div>` : "";
  icerik.innerHTML = `${ust(`${esc(ad)} ${sezonAd(sz)}`, `${oyn} maç · ${gol} gol${oyn ? ` · maç başı ${(gol / oyn).toFixed(2).replace(".", ",")}` : ""}`)}
  ${gez}
  ${s.sampiyon != null || kral ? `<div class="izgara iki bolum">${s.sampiyon != null ? `<div class="kart"><h2 class="h3">Şampiyon</h2><p>${kBag(d, s.sampiyon)}</p></div>` : ""}${kral}</div>` : ""}
  ${tablo ? `<h2 class="bolum">Puan durumu</h2><p class="soluk not">${s.tablo[0].hesap ? `Maçkolik arşivindeki maç sonuçlarından hesaplandı (galibiyet 2, beraberlik 1 puan; sıralama dönemin 3-2-1 sistemiyle aynı çıkar).${s.tablo[0].eksik ? " Arşivde bu sezonun bazı maçları eksik; tablo tamam değil, şampiyon gösterilmiyor." : ""}` : "Kaynaktaki gibi; o yıllarda galibiyet 3, beraberlik 2, mağlubiyet 1 puandı."}</p>${tablo}` : ""}
  ${maclar}
  ${KAYNAK}`;
}

yollar.splice(yollar.length - 1, 0, [/^#\/eski$/, eskiSayfa], [/^#\/eski\/(\w+)\/([\d-]+)$/, (y, s) => eskiSezonSayfa(y, s)],
  [/^#\/eski\/mac\/(\w+)\/([\d-]+)\/(\d+)$/, (y, s, i) => eskiMacSayfa(y, s, i)]);
})();

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

  <h2 class="bolum">Kırmızı kartın etkisi</h2>
  <div id="kirmizi"><div class="yukleniyor">Hazırlanıyor…</div></div>

  <h2 class="bolum">Süper Lig'de oynamış kulüpler</h2>
  <p class="soluk not">Her satır bir kulüp, her kare bir sezon. Koyu kare Süper Lig, açıldıkça alt ligler; noktalı kare şampiyonluk. Süper Lig'de en çok sezon geçirenden en aza sıralı.</p>
  <div class="kart viz" id="matris"></div>`;

  cizgiGrafik($("#gGol"), { xler, seriler: golS, bicim: (v, eksen) => ondalik(v, eksen ? 1 : 2), yMin: 0 });
  cizgiGrafik($("#gEv"), { xler, seriler: evS, bicim: (v, eksen) => yuzde(v, eksen ? 0 : 1), yukseklik: 220 });
  cizgiGrafik($("#gBer"), { xler, seriler: berS, bicim: (v, eksen) => yuzde(v, eksen ? 0 : 1), yukseklik: 220 });
  skorBolumu($("#skorBolum"), S, xler, A);
  derbiCiz($("#derbiler"), S);
  matrisCiz($("#matris"), Y, xler);
  al(`data/kirmizi.json?s=${OZET.surum || ""}`).then(K => kirmiziBolumu($("#kirmizi"), K)).catch(() => { $("#kirmizi").innerHTML = `<p class="soluk">Kırmızı kart verisi yüklenemedi.</p>`; });
}

// ---------------------------------------------------------------- kırmızı kart
const kirmiziDurum = { gecis: 0, saha: 0 };
function kirmiziBolumu(kap, K) {
  const md = K.model, kp = K.kapsam;
  const c = (x, b = 2) => ondalik(x, b);
  const ilk = K.durumlar.find(d => d.kendi === 10 && d.rakip === 11);
  const gecisAd = ["İlk kırmızı (11'e 11 → 10'a 11)", "İkinci kırmızı (10'a 11 → 9'a 11)", "Rakip 10 kişiyken (11'e 10 → 10'a 10)", "Üçüncü kırmızı (9'a 11 → 8'e 11)"];
  const P = K.puan_alanlar.reduce((o, a, i) => (o[a] = i, o), {});
  const ber15 = K.puan.find(r => r[P.gecis] === 0 && r[P.dakika] === 15 && !r[P.uzatma] && r[P.saha] === 0 && r[P.fark] === 0);
  kap.innerHTML = `
    <p class="soluk not">Süper Lig ${esc(kp.sezon_ilk)}–${esc(kp.sezon_son.slice(5))}, gol ve kart dakikaları TFF maç sayfalarından: ${sayiYaz(kp.mac)} maç, ${sayiYaz(kp.kirmizili)} maçta ${sayiYaz(kp.kirmizi)} kırmızı kart (ikinci sarıdan olanlar dahil). Gol listesi skorla tutmayan ya da dakikası eksik ${sayiYaz(Object.values(kp.cikarilan).reduce((a, b) => a + b, 0))} maç çıkarıldı.</p>
    <div class="izgara k4 bolum-ic">
      <div class="kart stat"><span class="soluk">10 kişi kalan takımın attığı gol</span><b>×${c(md.kendi[0].carpan)}</b><small class="soluk">11'e 11'e göre (%95 aralık ${c(md.kendi[0].alt)}–${c(md.kendi[0].ust)})</small></div>
      <div class="kart stat"><span class="soluk">10 kişi kalan takımın yediği gol</span><b>×${c(md.rakip[0].carpan)}</b><small class="soluk">rakibin attığı gol (${c(md.rakip[0].alt)}–${c(md.rakip[0].ust)})</small></div>
      <div class="kart stat"><span class="soluk">Her eksik oyuncu</span><b>×${c(md.oyuncu_basina.kendi)} / ×${c(md.oyuncu_basina.rakip)}</b><small class="soluk">attığı / yediği gol çarpanı</small></div>
      <div class="kart stat"><span class="soluk">15. dakikada berabereyken kırmızı</span><b>−${c(ber15[P.puan_once] - ber15[P.puan_sonra])} puan</b><small class="soluk">ev sahibinin beklenen puanı ${c(ber15[P.puan_once])} → ${c(ber15[P.puan_sonra])}</small></div>
    </div>
    <div class="izgara k2 bolum-ic">
      <div class="kart viz"><h3>Kırmızının dakikasına göre maç sonu gol farkına etkisi</h3>
        <p class="soluk aciklama">Yalnız bir kırmızı kartın çıktığı ${sayiYaz(kp.tek)} maç. Kırmızı gören takımın kart sonrası gol farkı, aynı dakikada aynı skor durumunda (önde/berabere/geride) ve aynı sahadaki 11'e 11 maçlarla karşılaştırıldı. Çubuk: gözlenen ortalama, çizgi: %95 güven aralığı, nokta: model. 1-15 diliminde maç az, aralık geniş; 90+ diliminde model etkiyi gözlenenden küçük buluyor (uzatmalardaki kartlı maçlar daha uzun sürüyor olabilir).</p>
        ${lejant([{ ad: "Gözlenen", renk: "var(--s2)" }], false)}<div id="kSutun"></div>
        ${tabloGorunum("Tablo olarak göster", ["Kart dakikası", "Maç", "Gol farkına etki", "%95 aralık", "Kart sonrası attığı (beklenen)", "Yediği (beklenen)", "Model"],
          K.gozlenen.map(g => [g.kova, g.n, (g.etki > 0 ? "+" : "") + c(g.etki), `±${c(g.ga)}`, `${c(g.atilan)} (${c(g.atilan_bek)})`, `${c(g.yenen)} (${c(g.yenen_bek)})`, c(g.model)]))}</div>
      <div class="kart viz"><h3>Kırmızı kartın beklenen puan maliyeti</h3>
        <p class="soluk aciklama">Kart gören takımın maç sonunda alacağı beklenen puan, kart görmeseydi alacağından ne kadar az? Gol modelinden: dakika, skor durumu, saha ve sahadaki oyuncu sayısına göre.</p>
        <div class="filtre"><div class="cipler">${gecisAd.map((a, i) => `<button class="cip ${kirmiziDurum.gecis === i ? "aktif" : ""}" data-gecis="${i}">${esc(a)}</button>`).join("")}</div>
          <div class="cipler">${["Ev sahibi", "Deplasman"].map((a, i) => `<button class="cip ${kirmiziDurum.saha === i ? "aktif" : ""}" data-ksaha="${i}">${a}</button>`).join("")}</div></div>
        <div id="kPuanLejant"></div><div id="kPuan"></div><div id="kPuanTablo"></div></div>
    </div>
    <div class="kart viz bolum-ic"><h3>Sahadaki oyuncu sayısına göre gol</h3>
      <p class="soluk aciklama">Maçların hangi oyuncu sayısıyla kaç dakika oynandığı ve o sürede atılan goller (takım bakışıyla, 90 dakikaya oranlanmış). Az oynanmış durumlarda sayılar güvenilir değildir; 3 ve 4 kart için model "her eksik oyuncu aynı çarpan" varsayımıyla tahmin eder. Sahada 7'den az oyuncu kalırsa maç tatil edilir.</p>
      <div class="tablo-kap"><table class="tablo"><thead><tr><th>Durum</th><th class="s">Oynanan dakika</th><th class="s">Attığı / 90 dk</th><th class="s">Yediği / 90 dk</th><th class="s">Gol</th></tr></thead><tbody>
      ${K.durumlar.filter(d => d.kendi <= d.rakip).sort((a, b) => (11 - a.kendi) + (11 - a.rakip) - ((11 - b.kendi) + (11 - b.rakip)) || a.kendi - b.kendi).map(d => `<tr${d.dakika < 1000 ? ' class="soluk"' : ""}>
        <td>${esc(d.durum)}${d.dakika < 1000 ? " <small>(az veri)</small>" : ""}</td><td class="s">${sayiYaz(d.dakika)}</td><td class="s">${c(d.atilan90)}</td><td class="s">${c(d.yenen90)}</td><td class="s">${d.kendi === d.rakip ? `${sayiYaz(d.atilan * 2)} toplam` : `${d.atilan}–${d.yenen}`}</td></tr>`).join("")}
      </tbody></table></div>
      <p class="soluk aciklama" style="margin-top:10px">Örnek okuma: "10'a 11" satırı, 10 kişi kalan takımın bakışıyla. 11'e 11'de takım başına 90 dakikada ${c(K.durumlar.find(d => d.kendi === 11 && d.rakip === 11).atilan90)} gol atılırken, 10 kişi kalan takım ${c(ilk.atilan90)} atıp ${c(ilk.yenen90)} yiyor. İki takımın da 10 kişi kaldığı maçlar daha açık geçiyor.</p>
      <p class="soluk aciklama">Puan maliyeti tablosunun tamamı (bütün dakikalar, skor farkları ve geçişler) <a class="bag" href="https://github.com/bilgehnbilge/turk-futbol-db/blob/main/kirmizi_kart_puan.csv">kirmizi_kart_puan.csv</a> dosyasında.</p>
    </div>`;
  sutunGrafik($("#kSutun", kap), K.gozlenen);
  const ciz = () => {
    const sat = K.puan.filter(r => r[P.gecis] === kirmiziDurum.gecis && r[P.saha] === kirmiziDurum.saha);
    const xler = [...new Set(sat.map(r => r[P.uzatma] ? `${r[P.dakika]}+${r[P.uzatma]}` : String(r[P.dakika])))];
    const seri = [[-1, "1 gol geride"], [0, "Berabere"], [1, "1 gol önde"]].map(([f, ad], i) => {
      const m = new Map(sat.filter(r => r[P.fark] === f).map(r => [r[P.uzatma] ? `${r[P.dakika]}+${r[P.uzatma]}` : String(r[P.dakika]), r[P.puan_once] - r[P.puan_sonra]]));
      return { ad, renk: SERI_RENK[i], d: xler.map(x => m.get(x) ?? null) };
    });
    $("#kPuanLejant", kap).innerHTML = lejant(seri);
    const g = $("#kPuan", kap); g.replaceChildren();
    cizgiGrafik(g, { xler, seriler: seri, bicim: (v, eksen) => ondalik(v, eksen ? 1 : 2), yMin: 0, yukseklik: 240, xEtiket: s => s, ipucuBas: s => `${s}. dakikada kırmızı · puan kaybı` });
    const ornek = ["15", "30", "45", "60", "75", "85", "90+3"];
    $("#kPuanTablo", kap).innerHTML = tabloGorunum("Tablo olarak göster", ["Dakika", ...seri.map(s => s.ad)], ornek.map(x => [x, ...seri.map(s => { const v = s.d[xler.indexOf(x)]; return v == null ? "—" : ondalik(v); })]));
  };
  ciz();
  kap.querySelectorAll("[data-gecis]").forEach(b => b.addEventListener("click", () => { kirmiziDurum.gecis = +b.dataset.gecis; kap.querySelectorAll("[data-gecis]").forEach(x => x.classList.toggle("aktif", x === b)); ciz(); }));
  kap.querySelectorAll("[data-ksaha]").forEach(b => b.addEventListener("click", () => { kirmiziDurum.saha = +b.dataset.ksaha; kap.querySelectorAll("[data-ksaha]").forEach(x => x.classList.toggle("aktif", x === b)); ciz(); }));
}

// sütun grafik: negatif değerler sıfırdan aşağı; güven aralığı çizgisi ve model noktası
function sutunGrafik(kap, l) {
  kap.classList.add("grafik");
  const W = genislik(kap, 380), H = 240, sol = 40, sag = 10, ust = 12, alt = 26;
  const lo = Math.min(...l.map(g => g.etki - g.ga), ...l.map(g => g.model), 0), hi = Math.max(0, ...l.map(g => g.etki + g.ga));
  const adim = guzelAdim(hi - lo, 4), ymin = Math.floor(lo / adim) * adim, ymax = Math.ceil(hi / adim) * adim || adim / 2;
  const Y = v => ust + (ymax - v) / (ymax - ymin) * (H - ust - alt);
  const bw = (W - sol - sag) / l.length, cub = Math.min(24, bw * .5);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, class: "grafik-svg", role: "img", "aria-label": "Kırmızının dakikasına göre gol farkı etkisi" });
  for (let v = ymin; v <= ymax + adim / 2; v += adim) {
    el("line", { x1: sol, x2: W - sag, y1: Y(v), y2: Y(v), class: Math.abs(v) < 1e-9 ? "eksen" : "izgara-cizgi" }, svg);
    el("text", { x: sol - 5, y: Y(v) + 4, class: "eksen-yazi", "text-anchor": "end" }, svg).textContent = ondalik(v, 1);
  }
  const ip = ipucuKur(kap);
  l.forEach((g, i) => {
    const x = sol + bw * i + bw / 2, y0 = Y(0), y1 = Y(g.etki), r = 4;
    const h = Math.abs(y1 - y0);
    // veri ucu aşağıda: alt köşeler yuvarlak, sıfır çizgisinde düz
    el("path", { d: `M${x - cub / 2},${y0}V${y1 - Math.min(r, h)}Q${x - cub / 2},${y1} ${x - cub / 2 + Math.min(r, h)},${y1}H${x + cub / 2 - Math.min(r, h)}Q${x + cub / 2},${y1} ${x + cub / 2},${y1 - Math.min(r, h)}V${y0}Z`, style: "fill:var(--s2)" }, svg);
    el("line", { x1: x, x2: x, y1: Y(g.etki - g.ga), y2: Y(g.etki + g.ga), class: "ga-cizgi" }, svg);
    for (const v of [g.etki - g.ga, g.etki + g.ga]) el("line", { x1: x - 5, x2: x + 5, y1: Y(v), y2: Y(v), class: "ga-cizgi" }, svg);
    el("circle", { cx: x, cy: Y(g.model), r: 4.5, class: "nokta model-nokta" }, svg);
    el("text", { x, y: H - 6, class: "eksen-yazi", "text-anchor": "middle" }, svg).textContent = g.kova;
    const hit = el("rect", { x: sol + bw * i, y: ust, width: bw, height: H - ust - alt, fill: "transparent", tabindex: 0, class: "hit" }, svg);
    const goster = () => { const o = svg.getBoundingClientRect().width / W; ip.goster(x * o, Y(Math.min(g.etki + g.ga, 0)) * o, `${g.kova}. dakikada kırmızı · ${sayiYaz(g.n)} maç`, [
      { deger: `${g.etki > 0 ? "+" : ""}${ondalik(g.etki)} (±${ondalik(g.ga)})`, ad: "gözlenen gol farkı etkisi", renk: "var(--s2)", kare: true },
      { deger: ondalik(g.model), ad: "model" },
      { deger: `${ondalik(g.atilan)} / ${ondalik(g.yenen)}`, ad: `kart sonrası attığı / yediği (beklenen ${ondalik(g.atilan_bek)} / ${ondalik(g.yenen_bek)})` }]); };
    hit.addEventListener("pointerenter", goster); hit.addEventListener("focus", goster);
    hit.addEventListener("pointerleave", () => ip.gizle()); hit.addEventListener("blur", () => ip.gizle());
  });
  kap.appendChild(svg);
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

// ---------------------------------------------------------------- Elo
const eloDurum = { kademe: "", kulupler: [846, 463, 95, 115] };
async function eloSayfa() {
  document.title = "Elo puan durumu · Türk Futbol Arşivi";
  icerik.innerHTML = `<div class="yukleniyor">Elo puanları yükleniyor…</div>`;
  const E = await al(`data/elo.json?s=${OZET.surum || ""}`);
  const G = E.guncel_alanlar.reduce((o, a, i) => (o[a] = i, o), {});
  const kademeler = [...new Set(E.guncel.map(r => r[G.kademe]))].sort();
  const sezonlar = [...new Set(Object.values(E.kulup).flatMap(l => l.map(x => x[0])))].sort((a, b) => sezonYil(a) - sezonYil(b) || a.localeCompare(b));
  icerik.innerHTML = `
  <div class="sayfa-bas"><h1>Elo puan durumu</h1></div>
  <p class="soluk not">Elo, her maçtan sonra güncellenen bir güç puanı: beklenenden iyi sonuç alan kazanır, kötü sonuç alan kaybeder; güçlü rakibi yenmek, zayıfı yenmekten çok puan getirir. 1959'dan bugüne ${sayiYaz(E.mac)} lig, play-off, Türkiye Kupası ve Cumhurbaşkanlığı/Süper Kupa maçından hesaplandı. Süper Lig'in ortalaması her sezon 1500 kabul edilir, yani puanlar dönemler arasında karşılaştırılabilir. Avrupa maçları dahil değil.</p>
  <div class="izgara k2 bolum-ust">
    <div class="kart"><h3>Bugünkü sıralama</h3><p class="soluk aciklama">${tarihYaz(E.son_tarih)} itibarıyla, bu sezon ligde oynayan kulüpler. Son sütun: son 10 maçtaki değişim.</p>
      <div class="filtre"><div class="cipler">${[["", "Bütün ligler"], ...kademeler.map(k => [String(k), KADEME_AD[k]])].map(([v, a]) => `<button class="cip ${eloDurum.kademe === v ? "aktif" : ""}" data-ek="${v}">${esc(a)}</button>`).join("")}</div></div>
      <div id="eloTablo"></div></div>
    <div>
      <div class="kart viz"><h3>Yıllara göre Elo (sezon sonu)</h3>
        <div class="ust-ara" style="max-width:320px;margin:4px 0 8px"><input id="eloEkle" type="search" placeholder="Grafiğe kulüp ekle…" autocomplete="off"><div id="eloOneri" class="oneri" hidden></div></div>
        <div id="eloLejant"></div><div id="eloGrafik"></div></div>
      <div class="kart bolum-ic"><h3>Tüm zamanların zirveleri</h3><p class="soluk aciklama">Her kulübün ulaştığı en yüksek Elo.</p>
        <ol class="sirali">${E.zirve.slice(0, 20).map((z, i) => `<li><span class="sira">${i + 1}</span><span class="kim">${kulupBag(z[0])}<small class="soluk">${tarihYaz(z[2])} · ${esc(z[3])}</small></span><b class="n">${z[1]}</b></li>`).join("")}</ol></div>
    </div>
  </div>
  <div class="kart bolum"><h3>En büyük sürprizler</h3><p class="soluk aciklama">Maçtan önceki Elo'ya göre kazanma şansı en düşük olan takımın kazandığı maçlar (1965 sonrası).</p>
    <div class="tablo-kap"><table class="tablo"><thead><tr><th>Tarih</th><th class="ad" style="text-align:right">Ev sahibi</th><th class="s">Skor</th><th>Deplasman</th><th class="s">Kazananın şansı</th></tr></thead><tbody>
    ${E.surpriz.slice(0, 20).map(m => `<tr><td>${tarihYaz(m[1])}<br><a class="bag" href="#/sezon/${m[2]}">${esc(m[2])}</a></td>
      <td class="ad" style="text-align:right">${kulupBag(m[3])} <small class="soluk">${m[7]}</small></td><td class="s skor">${skorBag(m[0], `${m[5]}-${m[6]}`)}</td>
      <td class="ad">${kulupBag(m[4])} <small class="soluk">${m[8]}</small></td><td class="s">${yuzde(m[9], 1)}</td></tr>`).join("")}</tbody></table></div></div>
  <p class="soluk not bolum">Hesap: maçtan önce beklenen sonuç = 1 / (1 + 10^(−(ev Elo + ev avantajı − deplasman Elo) / 400)); maçtan sonra puan, K (${E.ayar.K}) × gol farkı çarpanı × (sonuç − beklenen) kadar değişir. Ev avantajı maçlardan öğrenilir (bugün ${ondalik(E.ev_avantaji, 0)} puan). Yeni kulüp ilk ligin ortalamasının biraz altından başlar; her sezon başında puanın %${Math.round(E.ayar.cekim * 100)}'ı kulübün yeni liginin ortalamasına çekilir (yükselme/düşme, kadro değişimi). Ayarlar, geçmiş maçların sonucunu en iyi tahmin edecek şekilde seçildi.</p>`;
  const tablo = () => {
    const l = E.guncel.filter(r => !eloDurum.kademe || String(r[G.kademe]) === eloDurum.kademe);
    $("#eloTablo").innerHTML = `<div class="tablo-kap" style="max-height:640px;overflow:auto"><table class="tablo"><thead><tr><th class="s">#</th><th>Kulüp</th><th class="gizle-mobil">Lig</th><th class="s">Elo</th><th class="s">Son 10</th></tr></thead><tbody>
      ${l.map((r, i) => `<tr><td class="s soluk">${i + 1}</td><td class="ad elo-ad">${kulupBag(r[G.kulup])}</td><td class="gizle-mobil soluk">${esc(KADEME_AD[r[G.kademe]])}</td><td class="s p">${r[G.elo]}</td>
        <td class="s ${r[G.son10] > 0 ? "artı" : r[G.son10] < 0 ? "eksi" : ""}">${r[G.son10] > 0 ? "+" : ""}${r[G.son10]}</td></tr>`).join("")}</tbody></table></div>`;
  };
  tablo();
  icerik.querySelectorAll("[data-ek]").forEach(b => b.addEventListener("click", () => { eloDurum.kademe = b.dataset.ek; icerik.querySelectorAll("[data-ek]").forEach(x => x.classList.toggle("aktif", x === b)); tablo(); }));
  const grafik = () => {
    const seriler = eloDurum.kulupler.filter(k => E.kulup[k]).map((k, i) => {
      const m = new Map(E.kulup[k].map(x => [x[0], x[1]]));
      return { ad: kulupAd(k), renk: SERI_RENK[i], d: sezonlar.map(s => m.get(s) ?? null), id: k };
    });
    $("#eloLejant").innerHTML = `<div class="lejant">${seriler.map(s => `<span><i class="anahtar" style="background:${s.renk}"></i>${esc(s.ad)} <button class="kaldir" data-kal="${s.id}" aria-label="${esc(s.ad)} kaldır">×</button></span>`).join("")}</div>`;
    const g = $("#eloGrafik"); g.replaceChildren();
    if (seriler.length) cizgiGrafik(g, { xler: sezonlar, seriler, bicim: v => String(Math.round(v)), yukseklik: 280 });
    icerik.querySelectorAll("[data-kal]").forEach(b => b.addEventListener("click", () => { eloDurum.kulupler = eloDurum.kulupler.filter(k => k !== +b.dataset.kal); grafik(); }));
  };
  grafik();
  oneriKutusu($("#eloEkle"), $("#eloOneri"), k => {
    if (!E.kulup[k.id]) return;
    eloDurum.kulupler = [...eloDurum.kulupler.filter(x => x !== k.id), k.id].slice(-4);   // en fazla 4 kulüp (renk sırası)
    $("#eloEkle").value = ""; grafik();
  });
}

async function eloCiz(hedef, id) {
  const kap = $("#elo", hedef);
  if (!kap) return;
  let E;
  try { E = await al(`data/elo.json?s=${OZET.surum || ""}`); } catch { return; }
  const l = E.kulup[id];
  if (!l || l.length < 2 || !kap.isConnected) return;
  kap.hidden = false;
  const zirve = E.zirve.find(z => z[0] === id) || (() => { const m = l.reduce((a, b) => b[1] > a[1] ? b : a); return [id, m[1], null, m[0]]; })();
  const g = E.guncel.find(r => r[0] === id);
  kap.innerHTML = `<h3>Elo puanı</h3><p class="soluk aciklama">Sezon sonu Elo (Süper Lig ortalaması = 1500). ${g ? `Bugün <b>${g[1]}</b>, ` : ""}en yüksek ${zirve[1]} (${esc(zirve[3])}). <a class="bag" href="#/elo">Elo puan durumu →</a></p><div class="elo-g"></div>`;
  const sezonlar = l.map(x => x[0]);
  cizgiGrafik($(".elo-g", kap), { xler: sezonlar, seriler: [{ ad: "Elo", renk: "var(--vurgu)", d: l.map(x => x[1]) }], bicim: v => String(Math.round(v)), yukseklik: 200 });
}

yollar.splice(yollar.length - 1, 0, [/^#\/sayilar$/, sayilarSayfa]);
yollar.splice(yollar.length - 1, 0, [/^#\/elo$/, eloSayfa]);
window.eloCiz = eloCiz;
window.yolculukCiz = yolculukCiz;
})();

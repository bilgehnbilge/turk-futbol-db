/* A Milli Takım: bütün maçlar, rakiplere ve yarışmalara göre performans, oyuncular, teknik direktörler.
   Veri: data/milli.json (milli.py; TFF maç listesi pageID=425 ve maç sayfaları pageID=440), data/milli_detay.json.
   app.js'ten sonra yüklenir; $, esc, al, OZET, tarihYaz, sayiYaz, yuzde, sonuc, macCiz, yollar app.js'ten gelir. */
(() => {
// bölüme göre (erkek: data/, kadın: data/kadin/; kadin_milli.py) ayrı önbellek
const MILLI = {}, MILLI_DETAY = {};
const milliAl = async () => MILLI[BOLUM] ||= await al(`${V}milli.json?s=${OZET.surum || ""}`);
const milliDetayAl = async () => MILLI_DETAY[BOLUM] ||= await al(`${V}milli_detay.json?s=${OZET.surum || ""}`);
const milliAd = () => BOLUM === "kadin" ? "Kadın A Milli Takımı" : "Erkek A Milli Takımı";
// erkek / kadın seçimi: iki kart (bayrak, ad, dönem ve maç sayısı); öbür bölümün maç listesi küçük, bir kez yüklenir
const cinsKart = async () => {
  const [e, k] = await Promise.all([al("data/milli.json").catch(() => null), al("data/kadin/milli.json").catch(() => null)]);
  const kart = (ad, href, d, aktif, cins) => {
    const ms = d?.maclar || [];
    return `<a class="milli-cins-kart ${cins} ${aktif ? "aktif" : ""}" href="${href}">${bayrakImg("tr", "bayrak")}
      <span class="mc-ad"><small>${cins === "erkek" ? "ERKEK" : "KADIN"}</small><b>${ad}</b>
      <span class="soluk">${ms.length ? `${ms[0][1].slice(0, 4)}–${ms.at(-1)[1].slice(0, 4)} · ${ms.length} maç` : ""}</span></span></a>`;
  };
  return `<nav class="milli-cins bolum" aria-label="Erkek ve kadın milli takımı">${kart("Erkek A Milli Takımı", "#/milli", e, BOLUM === "erkek", "erkek")}${kart("Kadın A Milli Takımı", "#/kadin/milli", k, BOLUM === "kadin", "kadin")}</nav>`;
};
const durum = { kat: "", onyil: "", rakip: "", tum: false, yil: "", konf: "" };
// konfederasyon (rakipler mozaiğinin süzgeci): bayrak kodundan; listede olmayanlar UEFA (tarihî ülkeler dahil)
const KONF = { AFC: "ae af au bh bd cn hk id in iq ir jo jp kg kp kr kw la lb mm mn mo my np om ph pk ps qa sa sg sy th tj tm tw uz vn ye",
  CAF: "dz ao bj bw bf bi cm cv cf td km cg cd ci dj eg gq er et ga gm gh gn gw ke ls lr ly mg mw ml mr mu ma mz na ne ng rw st sn sc sl so za ss sd sz tz tg tn ug zm zw",
  CONMEBOL: "ar bo br cl co ec py pe uy ve", CONCACAF: "us ca mx cr jm hn sv gt pa tt ht cu bz ni sr gy bb ag lc vc gd dm kn bs", OFC: "nz fj pg sb vu nc" };
const konfBul = kod => Object.keys(KONF).find(k => KONF[k].split(" ").includes(kod)) || "UEFA";
// bayraklar docs/bayrak/<kod>.svg: circle-flags (MIT); Doğu Almanya Wikimedia Commons'tan (CSS ile daireye kırpılıyor)
const bayrakImg = (kod, sinif = "bayrak") => kod ? `<img class="${sinif}" src="bayrak/${kod}.svg" alt="" loading="lazy">` : "";
const TR_BAYRAK = () => bayrakImg("tr");

function maclar(d) {
  return d.maclar.map(r => ({ tff: r[0], tarih: r[1], rakip: r[2], kod: r[3], saha: r[4], a: r[5], y: r[6], kat: r[7], org: r[8], ayr: r[9],
    bayrak: bayrakImg((d.ulke[r[3]] || [])[2]), bkod: (d.ulke[r[3]] || [])[2], s: sonuc(r[5], r[6]) }));
}
const KAT_SIRA = ["Dünya Kupası", "Dünya Kupası elemeleri", "Avrupa Şampiyonası", "Avrupa Şampiyonası elemeleri", "Uluslar Ligi", "Diğer turnuvalar", "Özel maç"];
const say = l => l.reduce((t, m) => (t.O++, t[m.s]++, t.AG += m.a, t.YG += m.y, t.GY += m.y === 0, t), { O: 0, G: 0, B: 0, M: 0, AG: 0, YG: 0, GY: 0 });
const hucre = t => `<td class="s">${t.O}</td><td class="s">${t.G}</td><td class="s">${t.B}</td><td class="s">${t.M}</td><td class="s">${t.AG}</td><td class="s">${t.YG}</td>
  <td class="s">${t.AG - t.YG > 0 ? "+" : ""}${t.AG - t.YG}</td><td class="s"><b>%${yuzde(t.G, t.O)}</b></td>`;
const bas = ilk => `<thead><tr>${ilk.map((x, i) => `<th${i ? "" : ' class="ad"'}>${x}</th>`).join("")}<th class="s">O</th><th class="s">G</th><th class="s">B</th><th class="s">M</th>
  <th class="s" title="Attığı gol">AG</th><th class="s" title="Yediği gol">YG</th><th class="s">Av</th><th class="s" title="Galibiyet yüzdesi">G%</th></tr></thead>`;
const skorHtml = m => { const s = `${m.saha === "E" ? `${m.a}-${m.y}` : `${m.y}-${m.a}`}`; return m.ayr ? `<a class="skor bagli" href="#/${K}milli/mac/${m.tff}">${s}</a>` : `<b class="skor">${s}</b>`; };

async function milliSayfa(sekme = "ozet") {
  document.title = `${milliAd()} · Türk Futbol Arşivi`;
  icerik.innerHTML = `<div class="yukleniyor">Milli takım yükleniyor…</div>`;
  const [d, cins] = await Promise.all([milliAl(), cinsKart()]), tum = maclar(d);
  const ciz = () => {
    const ms = tum.filter(m => (!durum.kat || (durum.kat === "resmi" ? m.kat !== "Özel maç" : m.kat === durum.kat)) &&
      (!durum.onyil || m.tarih.slice(0, 3) === durum.onyil.slice(0, 3)) && (!durum.yil || m.tarih.startsWith(durum.yil)) && (!durum.rakip || m.kod === durum.rakip));
    const T = say(ms);
    const kat = KAT_SIRA.map(k => [k, ms.filter(m => m.kat === k)]).filter(x => x[1].length);
    const onyil = [...ms.reduce((a, m) => a.set(m.tarih.slice(0, 3) + "0", [...(a.get(m.tarih.slice(0, 3) + "0") || []), m]), new Map())].sort();
    const rakip = [...ms.reduce((a, m) => a.set(m.kod, [...(a.get(m.kod) || []), m]), new Map())].sort((x, y) => y[1].length - x[1].length || x[1][0].rakip.localeCompare(y[1][0].rakip, "tr"));
    const liste = [...ms].reverse(), n = durum.tum ? liste.length : 40;
    const onyillar = [...new Set(tum.map(m => m.tarih.slice(0, 3) + "0"))].sort();
    const rk = durum.rakip ? tum.find(m => m.kod === durum.rakip) : null;
    const SEKME = [["ozet", "", "Özet"], ["maclar", "/maclar", "Maçlar"], ["rakipler", "/rakipler", "Rakipler"], ["rekorlar", "/rekorlar", "Rekorlar ve seriler"]];
    // rakipler sekmesi rakip filtresinden bağımsız (bütün rakipleri gösterir)
    const msR = sekme === "rakipler" ? tum.filter(m => (!durum.kat || (durum.kat === "resmi" ? m.kat !== "Özel maç" : m.kat === durum.kat)) &&
      (!durum.onyil || m.tarih.slice(0, 3) === durum.onyil.slice(0, 3))) : ms;
    const rakipT = [...msR.reduce((a, m) => a.set(m.kod, [...(a.get(m.kod) || []), m]), new Map())].sort((x, y) => y[1].length - x[1].length || x[1][0].rakip.localeCompare(y[1][0].rakip, "tr"));
    const ozetHtml = () => `
    <div class="bolum">${anaOzet(T, durum.kat || durum.onyil || durum.rakip || durum.yil ? "Seçili maçlar" : "Bütün maçlar")}</div>
    <div class="kart bolum milli-yil" id="milliYil"></div>
    <div class="izgara iki bolum ust-hiza milli-iki">
      <div class="tablo-kap"><table class="tablo">${bas(["Yarışma"])}<tbody>${kat.map(([k, l]) => `<tr><td class="ad">${esc(k)}</td>${hucre(say(l))}</tr>`).join("")}${kat.length > 1 ? `<tr class="toplam"><td class="ad">Toplam</td>${hucre(T)}</tr>` : ""}</tbody></table></div>
      <div class="tablo-kap"><table class="tablo">${bas(["Dönem"])}<tbody>${onyil.map(([k, l]) => `<tr><td class="ad">${k}'lar</td>${hucre(say(l))}</tr>`).join("")}</tbody></table></div>
    </div>
    <div class="bolum">
      <div class="tablo-kap"><table class="tablo">${bas(["Saha"])}<tbody>${[["E", "Türkiye'de (ev sahibi)"], ["D", "Deplasmanda / tarafsız"]].map(([s, ad]) => [ad, ms.filter(m => m.saha === s)]).filter(x => x[1].length)
        .map(([ad, l]) => `<tr><td class="ad">${ad}</td>${hucre(say(l))}</tr>`).join("")}</tbody></table>
        <p class="soluk not">Ev sahibi, TFF listesinde ilk yazılan takım. Turnuva finallerindeki tarafsız saha maçları TFF'nin yazdığı sıraya göre ayrılıyor.</p></div>
    </div>
    <h2 class="bolum">Son maçlar</h2>
    ${macListe(liste.slice(0, 10))}
    <p class="soluk not"><a class="bag" href="#/${K}milli/maclar">Bütün maçlar →</a></p>
    <div id="milliOyuncular"></div>`;
    const macListe = l => `<div class="tablo-kap"><table class="tablo"><thead><tr><th>Tarih</th><th class="ad">Rakip</th><th class="s">Saha</th><th class="s">Skor</th><th class="s"><span class="gorunmez">Sonuç</span></th><th class="ad">Yarışma</th></tr></thead>
      <tbody>${l.map(m => `<tr><td class="tarih">${tarihYaz(m.tarih)}</td><td class="ad">${m.bayrak} ${esc(m.rakip)}</td><td class="s soluk">${m.saha === "E" ? "İç" : "Dış"}</td>
        <td class="s">${skorHtml(m)}</td><td class="s"><span class="son ${m.s}">${m.s}</span></td><td class="ad soluk">${esc(m.org)}</td></tr>`).join("")}</tbody></table></div>`;
    const maclarHtml = () => `${rk ? `<h2 class="bolum">${rk.bayrak} ${esc(rk.rakip)} ile oynanan maçlar</h2>
      <div class="kart bolum"><div class="ozet-sat"><div><b>${T.O}</b><span>Maç</span></div><div><b>${T.G}</b><span>Galibiyet</span></div><div><b>${T.B}</b><span>Beraberlik</span></div>
        <div><b>${T.M}</b><span>Mağlubiyet</span></div><div><b>${T.AG}-${T.YG}</b><span>Gol</span></div></div></div>` : ""}
    ${macListe(liste.slice(0, n))}
    ${liste.length > n ? `<button class="dugme daha" id="mTum">${liste.length} maçın hepsini göster</button>` : ""}
    <p class="soluk not">Skor her zaman ev sahibi önce yazılır; "İç" Türkiye'nin ev sahibi olduğu maçlar. Skora tıklayınca maç sayfası açılır.</p>`;
    const rakipK = rakipT.filter(([k, l]) => !durum.konf || konfBul(l[0].bkod) === durum.konf);
    const konflar = [...new Set(rakipT.map(([k, l]) => konfBul(l[0].bkod)))].sort((a, b) => a === "UEFA" ? -1 : b === "UEFA" ? 1 : a.localeCompare(b));
    const mozaik = () => `<div class="cipler konf-sec bolum" role="group" aria-label="Konfederasyon"><button class="cip ${!durum.konf ? "aktif" : ""}" data-konf="">Bütün rakipler</button>${konflar.map(k => `<button class="cip ${durum.konf === k ? "aktif" : ""}" data-konf="${k}">${k} <small>${rakipT.filter(([, l]) => konfBul(l[0].bkod) === k).length}</small></button>`).join("")}</div>
      <div class="rakip-mozaik">${rakipK.map(([k, l]) => { const t = say(l), p = t.O ? (t.G + t.B / 2) / t.O : .5;
        return `<a href="#" data-rakip="${esc(k)}" class="rm ${t.O >= 25 ? "b3" : t.O >= 10 ? "b2" : ""}" style="--p:${p.toFixed(3)}" title="${esc(l[0].rakip)}: ${t.O} maç, ${t.G} G, ${t.B} B, ${t.M} M, gol ${t.AG}-${t.YG}">
          ${l[0].bayrak}<span class="rm-ad">${esc(l[0].rakip)}</span><span class="rm-say"><b>${t.G}-${t.B}-${t.M}</b> <small>${t.O} maç</small></span>
          <span class="rm-cubuk"><i class="g" style="width:${yuzde(t.G, t.O)}%"></i><i class="b" style="width:${yuzde(t.B, t.O)}%"></i><i class="m" style="width:${yuzde(t.M, t.O)}%"></i></span></a>`; }).join("")}</div>
      <p class="soluk not">Renk, rakibe karşı puan payı (galibiyet 1, beraberlik ½): yeşil Türkiye üstün, kırmızı rakip üstün. Büyük kartlar 10 ve 25 maçın üstü. Karta tıklayınca maçlar açılır.</p>`;
    const rakiplerHtml = () => `${mozaik()}<h2 class="bolum">Tablo</h2><p class="soluk not">${rakipT.length} farklı rakip. Satıra tıklayınca o ülkeyle oynanan maçlar açılır.</p>
    <div class="tablo-kap"><table class="tablo milli-rakip">${bas(["Rakip"])}<tbody>${rakipT.map(([k, l]) => `<tr data-rakip="${esc(k)}" class="tiklanir">
      <td class="ad">${l[0].bayrak} ${esc(l[0].rakip)}</td>${hucre(say(l))}</tr>`).join("")}</tbody></table></div>`;
    icerik.innerHTML = `
    ${cins}
    <div class="sayfa-bas"><div><h1>${bayrakImg("tr", "bayrak baslik")} ${milliAd()}</h1>
      <p class="soluk">${tarihYaz(tum[0].tarih)} – ${tarihYaz(tum.at(-1).tarih)} · ${tum.length} resmi ve özel maç</p></div></div>
    <div class="kulup-sekme"><nav class="sekmeler">${SEKME.map(([k, y, ad]) => `<a href="#/${K}milli${y}" class="${k === sekme ? "aktif" : ""}">${ad}</a>`).join("")}</nav></div>
    <div class="filtre milli-filtre bolum">
      <select id="mKat" aria-label="Maç türü"><option value="">Bütün maçlar</option><option value="resmi" ${durum.kat === "resmi" ? "selected" : ""}>Resmi maçlar (özel maçlar hariç)</option>
        ${KAT_SIRA.map(k => `<option ${durum.kat === k ? "selected" : ""}>${k}</option>`).join("")}</select>
      <select id="mOnyil" aria-label="On yıl"><option value="">Bütün yıllar</option>${onyillar.map(o => `<option value="${o}" ${durum.onyil === o ? "selected" : ""}>${o}'lar</option>`).join("")}</select>
      ${rk && sekme !== "rakipler" ? `<span class="rozet">${rk.bayrak} ${esc(rk.rakip)} <a href="#" id="mRakipSil" title="Rakip filtresini kaldır">✕</a></span>` : ""}
      ${durum.yil ? `<span class="rozet">${durum.yil} <a href="#" id="mYilSil" title="Yıl filtresini kaldır">✕</a></span>` : ""}
    </div>
    ${!msR.length ? `<div class="bos">Bu filtreye uyan maç yok.</div>` : { ozet: ozetHtml, maclar: maclarHtml, rakipler: rakiplerHtml, rekorlar: () => rekorHtml(d, ms) }[sekme]()}`;
    $("#mKat").onchange = e => { durum.kat = e.target.value; ciz(); };
    $("#mOnyil").onchange = e => { durum.onyil = e.target.value; ciz(); };
    $("#mRakipSil")?.addEventListener("click", e => { e.preventDefault(); durum.rakip = ""; ciz(); });
    $("#mYilSil")?.addEventListener("click", e => { e.preventDefault(); durum.yil = ""; ciz(); });
    if ($("#milliYil")) yilGrafik($("#milliYil"), ms, y => { durum.yil = y; durum.tum = true; location.hash = `#/${K}milli/maclar`; });
    icerik.querySelectorAll(".rakip-mozaik [data-rakip]").forEach(a => a.addEventListener("click", e => { e.preventDefault(); durum.rakip = a.dataset.rakip; durum.tum = true; location.hash = `#/${K}milli/maclar`; }));
    icerik.querySelector(".konf-sec")?.addEventListener("click", e => { const b = e.target.closest("[data-konf]"); if (b) { durum.konf = b.dataset.konf; ciz(); } });
    $("#mTum")?.addEventListener("click", () => { durum.tum = true; const y = scrollY; ciz(); scrollTo(0, y); });
    icerik.querySelectorAll("tr[data-rakip]").forEach(tr => tr.addEventListener("click", () => { durum.rakip = tr.dataset.rakip; durum.tum = true; location.hash = `#/${K}milli/maclar`; }));
    if ($("#milliOyuncular")) oyuncular(d, $("#milliOyuncular"));
    icerik.querySelectorAll("details[data-seri]").forEach(x => x.addEventListener("toggle", () => x.open && (x.querySelector(".seri-liste").innerHTML ||= seriListe(JSON.parse(x.dataset.seri)))));
  };
  ciz();
}

// ---- yıl yıl sonuçlar: yığılmış G/B/M çubukları; Dünya Kupası ve Avrupa Şampiyonası finallerinin yılları işaretli
function yilGrafik(kap, ms, secince) {
  if (!ms.length) { kap.remove(); return; }
  const yillar = new Map();
  for (const m of ms) { const y = m.tarih.slice(0, 4), t = yillar.get(y) || { G: 0, B: 0, M: 0, tur: new Set() }; t[m.s]++; if (m.kat === "Dünya Kupası" || m.kat === "Avrupa Şampiyonası") t.tur.add(m.kat === "Dünya Kupası" ? "DK" : "AŞ"); yillar.set(y, t); }
  const a = +[...yillar.keys()].sort()[0], b = +[...yillar.keys()].sort().at(-1);
  const Y = []; for (let y = a; y <= b; y++) Y.push(String(y));
  const W = EK.genislik(kap), H = 210, sol = 28, sag = 8, ust = 22, alt = 22, bw = (W - sol - sag) / Y.length;
  const enb = Math.max(...[...yillar.values()].map(t => t.G + t.B + t.M), 1), YY = v => ust + (1 - v / enb) * (H - ust - alt);
  let h = "";
  for (let v = 0; v <= enb; v += enb > 12 ? 5 : 2) h += `<line class="izgara-cizgi" x1="${sol}" x2="${W - sag}" y1="${YY(v)}" y2="${YY(v)}"/><text class="eksen-yazi" x="${sol - 6}" y="${YY(v) + 4}" text-anchor="end">${v}</text>`;
  Y.forEach((y, i) => {
    const x = sol + i * bw, t = yillar.get(y);
    if (+y % (W < 600 ? 20 : 10) === 0) h += `<text class="eksen-yazi" x="${x + bw / 2}" y="${H - 6}" text-anchor="middle">${y}</text>`;
    if (!t) return;
    let alt0 = 0;
    h += `<g class="yl" data-y="${y}">`;
    for (const [k, c] of [["G", "var(--g)"], ["B", "var(--b)"], ["M", "var(--m)"]]) { if (!t[k]) continue; const y1 = YY(alt0 + t[k]), y0 = YY(alt0); h += `<rect x="${(x + bw * .1).toFixed(1)}" y="${y1.toFixed(1)}" width="${Math.max(1, bw * .8).toFixed(1)}" height="${Math.max(.5, y0 - y1 - .6).toFixed(1)}" style="fill:${c}"/>`; alt0 += t[k]; }
    if (t.tur.size) h += `<text class="tur-isaret" x="${x + bw / 2}" y="${YY(alt0) - 5}" text-anchor="middle">${[...t.tur].join("·")}</text>`;
    h += `<rect class="hit" x="${x}" y="0" width="${bw}" height="${H - alt}" fill="transparent"/></g>`;
  });
  kap.innerHTML = `<h3>Yıl yıl sonuçlar</h3><p class="aciklama soluk">Her çubuk bir yıl: yeşil galibiyet, sarı beraberlik, kırmızı mağlubiyet. DK: Dünya Kupası, AŞ: Avrupa Şampiyonası finalleri. Çubuğa tıklayınca o yılın maçları.</p>
    <svg class="grafik-svg milli-yil-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Yıl yıl milli takım sonuçları">${h}</svg>`;
  const svg = kap.querySelector("svg"), ip = EK.ipucu(kap);
  svg.addEventListener("pointermove", e => {
    const g = e.target.closest(".yl"); if (!g) { ip.gizle(); return; }
    const t = yillar.get(g.dataset.y), l = ms.filter(m => m.tarih.startsWith(g.dataset.y));
    svg.querySelectorAll(".yl.on").forEach(x => x.classList.remove("on")); g.classList.add("on");
    ip.goster(e, `<div class="ipucu-bas">${g.dataset.y} · ${l.length} maç</div><div class="ipucu-satir"><b>${t.G}</b><span>G</span><b>${t.B}</b><span>B</span><b>${t.M}</b><span>M</span></div>
      ${l.slice(0, 6).map(m => `<div class="ipucu-satir soluk"><span>${m.bayrak}</span><span>${esc(m.rakip)}</span><b>${m.saha === "E" ? `${m.a}-${m.y}` : `${m.y}-${m.a}`}</b></div>`).join("")}${l.length > 6 ? `<div class="soluk">…</div>` : ""}`);
  });
  svg.addEventListener("pointerleave", () => { ip.gizle(); svg.querySelectorAll(".yl.on").forEach(x => x.classList.remove("on")); });
  svg.addEventListener("click", e => { const g = e.target.closest(".yl"); if (g) secince(g.dataset.y); });
}

// ---- rekorlar ve seriler (seçili filtredeki maçlar)
let SERI_MS = [];
const macSatir = m => `<tr><td class="tarih">${tarihYaz(m.tarih)}</td><td class="ad">${m.bayrak} ${esc(m.rakip)}</td><td class="s soluk">${m.saha === "E" ? "İç" : "Dış"}</td>
  <td class="s">${skorHtml(m)}</td><td class="ad soluk">${esc(m.org)}</td></tr>`;
const macTablo = l => `<div class="tablo-kap"><table class="tablo"><tbody>${l.map(macSatir).join("")}</tbody></table></div>`;
const seriListe = ([b, e]) => macTablo(SERI_MS.slice(b, e + 1));
function rekorHtml(d, ms) {
  SERI_MS = ms;
  const ilk = (l, f, n = 10) => { l = [...l].sort(f); const s = l.length > n ? f(l[n - 1], l[n]) : 1; return l.slice(0, n); };
  const gal = ilk(ms.filter(m => m.a > m.y), (x, y) => (y.a - y.y) - (x.a - x.y) || y.a - x.a || x.tarih.localeCompare(y.tarih));
  const mag = ilk(ms.filter(m => m.a < m.y), (x, y) => (y.y - y.a) - (x.y - x.a) || y.y - x.y || x.tarih.localeCompare(y.tarih));
  const gol = ilk(ms, (x, y) => (y.a + y.y) - (x.a + x.y) || x.tarih.localeCompare(y.tarih));
  const tanim = [
    ["Galibiyet serisi", m => m.s === "G"], ["Yenilmezlik serisi", m => m.s !== "M"], ["Gol yemeden", m => m.y === 0], ["Gol atarak", m => m.a > 0],
    ["Mağlubiyet serisi", m => m.s === "M"], ["Galibiyetsiz seri", m => m.s !== "G"], ["Gol atamadan", m => m.a === 0],
  ];
  const seri = tanim.map(([ad, f]) => {
    let en = { n: 0 }, cur = { n: 0 };
    ms.forEach((m, i) => { if (f(m)) { if (!cur.n) cur.b = i; cur.n++; if (cur.n > en.n) en = { n: cur.n, b: cur.b, e: i }; } else cur = { n: 0 }; });
    return { ad, en, devam: cur.n ? { n: cur.n, b: cur.b, e: ms.length - 1 } : null };
  });
  const seriKart = s => `<details class="kart rekor" data-seri="${s.en.n ? JSON.stringify([s.en.b, s.en.e]) : "[0,-1]"}"><summary><span class="baslik">${s.ad}</span>
    ${s.en.n ? `<span class="deger">${s.en.n} maç</span><span class="detay">${tarihYaz(ms[s.en.b].tarih)} – ${tarihYaz(ms[s.en.e].tarih)}</span>` : `<span class="soluk">—</span>`}
    ${s.devam && s.devam.n > 1 ? `<span class="detay"><b>Süren seri:</b> ${s.devam.n} maç</span>` : ""}</summary><div class="seri-liste"></div></details>`;
  const sira = (l, f) => { let r = 0, onc; return l.map((x, i) => { const v = f(x); if (v !== onc) { r = i + 1; onc = v; } return [r, x]; }); };
  const filtreli = ms.length !== d.maclar.length;
  const mg = d.mac_gol.filter(x => ms.some(m => m.tff === x[3]));
  const mgN = mg.filter((x, i) => i < 10 || x[2] === mg[9]?.[2]);
  const gk = d.kaleci.slice(0, 10);
  return `
  <h2 class="bolum">Maç rekorları</h2>
  <div class="izgara iki ust-hiza milli-iki">
    <div><h3>En farklı galibiyetler</h3>${macTablo(gal)}</div>
    <div><h3>En farklı mağlubiyetler</h3>${macTablo(mag)}</div>
    <div><h3>En gollü maçlar</h3>${macTablo(gol)}</div>
  </div>
  <h2 class="bolum">Seriler <small class="soluk" style="font-weight:400;font-size:14px">— seçili maçlar art arda; ayrıntı için karta tıkla</small></h2>
  <div class="izgara iki ust-hiza">${seri.map(seriKart).join("")}</div>
  <h2 class="bolum">Oyuncu rekorları</h2>
  <div class="izgara iki ust-hiza">
    <div class="kart rekor-kart"><h3>Bir maçta en çok gol</h3><p class="soluk aciklama">Hat-trick ve üstü${filtreli ? ", seçili maçlarda" : ""}</p>
      ${mgN.length ? `<ol class="sirali">${sira(mgN, x => x[2]).map(([r, x]) => `<li><span class="sira">${r}</span><span class="kim"><a class="bag" href="#/${K}oyuncu/k${x[0]}">${esc(x[1])}</a>
        <small class="soluk">${tarihYaz(x[4])} · ${esc(x[5])} · <a class="bag" href="#/${K}milli/mac/${x[3]}">maç</a></small></span><b class="n">${x[2]}</b></li>`).join("")}</ol>
        ${mg.length > mgN.length ? `<p class="soluk aciklama">ve ${mg.length - mgN.length} hat-trick daha</p>` : ""}` : `<p class="soluk">—</p>`}</div>
    <div class="kart rekor-kart"><h3>Kalesini en çok gole kapatan kaleciler</h3><p class="soluk aciklama">İlk 11'de başladığı maçlar (bütün maçlar)</p>
      <ol class="sirali">${sira(gk, x => x[3]).map(([r, x]) => `<li><span class="sira">${r}</span><span class="kim"><a class="bag" href="#/${K}oyuncu/k${x[0]}">${esc(x[1])}</a>
        <small class="soluk">${x[2]} maç · %${yuzde(x[3], x[2])} · maç başı ${(x[4] / x[2]).toFixed(2)} gol</small></span><b class="n">${x[3]}</b></li>`).join("")}</ol></div>
  </div>
  <p class="soluk not">Seriler ve maç rekorları yukarıdaki filtreye göre hesaplanır (ör. yalnız resmi maçlar). Kaleci, TFF'nin ilk 11'i kaleciyle başlatmasından bulunuyor.</p>`;
}

function oyuncular(d, kap) {
  const O = Object.entries(d.oyuncu).map(([k, v]) => ({ kisi: k, ad: v[0], mac: v[1], ilk: v[2], gol: v[3], pen: v[4], sari: v[5], kirmizi: v[6], bas: v[7], son: v[8], kulup: v[9] }));
  const sira = (l, f) => { let r = 0, onc; return l.map((x, i) => { const v = f(x); if (v !== onc) { r = i + 1; onc = v; } return [r, x]; }); };
  const kart = (baslik, aciklama, l, f, alt) => `<div class="kart rekor-kart"><h3>${baslik}</h3><p class="soluk aciklama">${aciklama}</p>
    <ol class="sirali">${sira(l.slice(0, 15), f).map(([r, x]) => `<li><span class="sira">${r}</span><span class="kim"><a class="bag" href="#/${K}oyuncu/k${x.kisi}">${esc(x.ad)}</a>
      <small class="soluk">${x.bas.slice(0, 4)}–${x.son.slice(0, 4)} · ${alt(x)}</small>${donem(x)}</span><b class="n">${f(x)}</b></li>`).join("")}</ol>
    <div class="donem-eksen" aria-hidden="true"><span>${ilkY}</span><span>${Math.round((ilkY + sonY) / 2)}</span><span>${sonY}</span></div></div>`;
  // dönem çizgisi: oyuncunun ilk ve son milli maçı, takımın bütün tarihine göre
  const ilkY = +d.maclar[0][1].slice(0, 4), sonY = +d.maclar.at(-1)[1].slice(0, 4), yer = t => ((+t.slice(0, 4) + (+t.slice(5, 7) - 1) / 12 - ilkY) / (sonY + 1 - ilkY) * 100).toFixed(2);
  const donem = x => `<span class="donem-cizgi" title="${x.bas.slice(0, 4)}–${x.son.slice(0, 4)}"><i style="left:${yer(x.bas)}%;width:${Math.max(.8, yer(x.son) - yer(x.bas)).toFixed(2)}%"></i></span>`;
  const by = f => O.filter(x => f(x)).sort((a, b) => f(b) - f(a) || b.mac - a.mac);
  // teknik direktörler
  const ms = new Map(maclar(d).map(m => [m.tff, m]));
  const td = Object.entries(d.teknik).map(([k, [ad, l]]) => ({ ad, t: say(l.map(t => ms.get(t)).filter(Boolean)), bas: ms.get(l[0])?.tarih, son: ms.get(l.at(-1))?.tarih }))
    .filter(x => x.t.O).sort((a, b) => b.t.O - a.t.O);
  kap.innerHTML = `<h2 class="bolum">Oyuncular</h2>
  <div class="izgara iki ust-hiza">
    ${kart("En çok milli olanlar", "İlk 11'de ya da oyuna sonradan girerek", by(x => x.mac), x => x.mac, x => `${x.gol} gol`)}
    ${kart("En çok gol atanlar", "Penaltı golleri dahil, kendi kalesine goller hariç", by(x => x.gol), x => x.gol, x => `${x.mac} maç${x.pen ? ` · ${x.pen} penaltı` : ""}`)}
    ${kart("En çok sarı kart görenler", "", by(x => x.sari), x => x.sari, x => `${x.mac} maç`)}
    ${kart("En çok kırmızı kart görenler", "İkinci sarıdan kırmızı dahil", by(x => x.kirmizi), x => x.kirmizi, x => `${x.mac} maç`)}
  </div>
  ${td.length ? `<h2 class="bolum">Teknik direktörler</h2>
  <div class="tablo-kap"><table class="tablo">${bas(["Teknik direktör", "Dönem"])}<tbody>${td.map(x => `<tr><td class="ad">${esc(x.ad)}</td><td class="soluk">${x.bas?.slice(0, 4)}–${x.son?.slice(0, 4)}</td>${hucre(x.t)}</tr>`).join("")}</tbody></table></div>` : ""}
  <p class="soluk not">Kaynak: <a class="bag" href="https://www.tff.org/Default.aspx?pageID=425" target="_blank" rel="noopener">TFF A Milli Takım maçları</a> (kadrolar, kartlar, değişiklikler, goller);
    TFF'nin gol listesi eksik olan maçlarda gol atanlar, ayrıca stat, seyirci ve hakem İngilizce Vikipedi'nin milli takım maç listelerinden. Oyuncu listeleri bütün maçlardan (filtreden bağımsız). Eski maçlarda kart bilgisi eksik olabilir.</p>`;
}

async function milliMacSayfa(tff) {
  icerik.innerHTML = `<div class="yukleniyor">Maç yükleniyor…</div>`;
  const [d, D] = await Promise.all([milliAl(), milliDetayAl()]);
  const m = maclar(d).find(x => x.tff === tff), r = D[tff];
  if (!m || !r) { icerik.innerHTML = `<div class="bos">Bu maçın ayrıntısı yok.</div>`; return; }
  const tr = ["Türkiye", bayrakImg("tr", "bayrak buyuk")], rk = [m.rakip, bayrakImg(m.bkod, "bayrak buyuk")], ev = m.saha === "E";
  const TUR = { Y: "YELLOW_CARD", R: "RED_CARD", YR: "YELLOW_CARD_SECOND", S: "SUBSTITUTION", G: "GOAL" };
  macCiz({
    tarih: m.tarih, ev: [null, (ev ? tr : rk)[0]], dep: [null, (ev ? rk : tr)[0]], bayrak: [(ev ? tr : rk)[1], (ev ? rk : tr)[1]],
    skor: [ev ? m.a : m.y, ev ? m.y : m.a, null, null, null], ustHtml: `<a class="bag" href="#/${K}milli">${milliAd()}</a> · ${esc(m.org)}`,
    stad: r.s, seyirci: r.sy, hakem: r.hk, kaynak: "TFF", tff, kaynakUrl: `https://www.tff.org/Default.aspx?pageID=440&macID=${tff}`, oyuncuOnek: "k",
    kadro: r.k.map(l => l.map(([forma, ad, ilk11, kisi]) => [forma, ad, ilk11, 0, kisi])), teknik: r.t.map(l => l.map(([ad, k]) => BOLUM === "erkek" ? [ad, "a" + k] : ad)),
    olay: r.o.map(([taraf, tur, dk, ek, a1, a2, tip, k1, k2]) => [taraf, TUR[tur], dk, ek || null, a1, a2, tip === "P" ? "PENALTY" : tip === "K" ? "OWN" : tip === "H" ? "HEADER" : null, k1, k2]),
  });
  document.title = `${(ev ? tr : rk)[0]} - ${(ev ? rk : tr)[0]} · ${milliAd()}`;
}

// oyuncu sayfasında milli takım bölümü; yalnizMilli: kulüp kaydı olmayan oyuncu (sayfanın tamamı)
window.milliOyuncu = async (kap, kisi, yalnizMilli) => {
  const d = await milliAl(), v = d.oyuncu[kisi];
  if (!v) return false;
  const [ad, mac, ilk, gol, pen, sari, kirmizi, bas, son, kulup] = v;
  if (yalnizMilli) document.title = `${ad} · Türk Futbol Arşivi`;
  kap.innerHTML = `${yalnizMilli ? `<div class="sayfa-bas"><div><h1>${esc(ad)}</h1><p class="soluk">${esc(kulup.join(", "))}</p></div></div>` : `<h2 class="bolum">${bayrakImg("tr")} ${milliAd()}</h2>`}
    <div class="kart bolum"><div class="ozet-sat">
      <div><b>${mac}</b><span>Maç</span></div><div><b>${ilk}</b><span>İlk 11</span></div><div><b>${gol}</b><span>Gol</span></div>
      <div><b>${pen}</b><span>Penaltı golü</span></div><div><b>${sari}</b><span>Sarı kart</span></div><div><b>${kirmizi}</b><span>Kırmızı kart</span></div></div>
      <p class="soluk not">İlk maçı ${tarihYaz(bas)}, son maçı ${tarihYaz(son)}. Milli takıma çağrıldığı kulüpler: ${esc(kulup.join(", ") || "—")}. <a class="bag" href="#/${K}milli">Milli takım sayfası →</a></p></div>`;
  return true;
};

yollar.splice(yollar.length - 1, 0, [/^#\/milli$/, () => milliSayfa("ozet")], [/^#\/milli\/(maclar|rakipler|rekorlar)$/, s => milliSayfa(s)], [/^#\/milli\/mac\/(\d+)$/, id => milliMacSayfa(+id)]);
})();

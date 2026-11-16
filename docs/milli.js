/* A Milli Takım: bütün maçlar, rakiplere ve yarışmalara göre performans, oyuncular, teknik direktörler.
   Veri: data/milli.json (milli.py; TFF maç listesi pageID=425 ve maç sayfaları pageID=440), data/milli_detay.json.
   app.js'ten sonra yüklenir; $, esc, al, OZET, tarihYaz, sayiYaz, yuzde, sonuc, macCiz, yollar app.js'ten gelir. */
(() => {
let MILLI = null, MILLI_DETAY = null;
const milliAl = async () => MILLI ||= await al(`data/milli.json?s=${OZET.surum || ""}`);
const milliDetayAl = async () => MILLI_DETAY ||= await al(`data/milli_detay.json?s=${OZET.surum || ""}`);
const durum = { kat: "", onyil: "", rakip: "", tum: false };
// bayraklar docs/bayrak/<kod>.svg: flag-icons (MIT) ve tarihi ülkeler için Wikimedia Commons (Yugoslavya, SSCB, Çekoslovakya, Doğu Almanya)
const bayrakImg = (kod, sinif = "bayrak") => kod ? `<img class="${sinif}" src="bayrak/${kod}.svg" alt="" loading="lazy">` : "";
const TR_BAYRAK = () => bayrakImg("tr");

function maclar(d) {
  return d.maclar.map(r => ({ tff: r[0], tarih: r[1], rakip: r[2], kod: r[3], saha: r[4], a: r[5], y: r[6], kat: r[7], org: r[8], ayr: r[9],
    bayrak: bayrakImg((d.ulke[r[3]] || [])[2]), bkod: (d.ulke[r[3]] || [])[2], s: sonuc(r[5], r[6]) }));
}
const KAT_SIRA = ["Dünya Kupası", "Dünya Kupası elemeleri", "Avrupa Şampiyonası", "Avrupa Şampiyonası elemeleri", "Uluslar Ligi", "Diğer turnuvalar", "Özel maç"];
const say = l => l.reduce((t, m) => (t.O++, t[m.s]++, t.AG += m.a, t.YG += m.y, t), { O: 0, G: 0, B: 0, M: 0, AG: 0, YG: 0 });
const hucre = t => `<td class="s">${t.O}</td><td class="s">${t.G}</td><td class="s">${t.B}</td><td class="s">${t.M}</td><td class="s">${t.AG}</td><td class="s">${t.YG}</td>
  <td class="s">${t.AG - t.YG > 0 ? "+" : ""}${t.AG - t.YG}</td><td class="s"><b>%${yuzde(t.G, t.O)}</b></td>`;
const bas = ilk => `<thead><tr>${ilk.map((x, i) => `<th${i ? "" : ' class="ad"'}>${x}</th>`).join("")}<th class="s">O</th><th class="s">G</th><th class="s">B</th><th class="s">M</th>
  <th class="s" title="Attığı gol">AG</th><th class="s" title="Yediği gol">YG</th><th class="s">Av</th><th class="s" title="Galibiyet yüzdesi">G%</th></tr></thead>`;
const skorHtml = m => { const s = `${m.saha === "E" ? `${m.a}-${m.y}` : `${m.y}-${m.a}`}`; return m.ayr ? `<a class="skor bagli" href="#/milli/mac/${m.tff}">${s}</a>` : `<b class="skor">${s}</b>`; };

async function milliSayfa(sekme = "ozet") {
  document.title = "A Milli Takım · Türk Futbol Arşivi";
  icerik.innerHTML = `<div class="yukleniyor">Milli takım yükleniyor…</div>`;
  const d = await milliAl(), tum = maclar(d);
  const ciz = () => {
    const ms = tum.filter(m => (!durum.kat || (durum.kat === "resmi" ? m.kat !== "Özel maç" : m.kat === durum.kat)) &&
      (!durum.onyil || m.tarih.slice(0, 3) === durum.onyil.slice(0, 3)) && (!durum.rakip || m.kod === durum.rakip));
    const T = say(ms);
    const kat = KAT_SIRA.map(k => [k, ms.filter(m => m.kat === k)]).filter(x => x[1].length);
    const onyil = [...ms.reduce((a, m) => a.set(m.tarih.slice(0, 3) + "0", [...(a.get(m.tarih.slice(0, 3) + "0") || []), m]), new Map())].sort();
    const rakip = [...ms.reduce((a, m) => a.set(m.kod, [...(a.get(m.kod) || []), m]), new Map())].sort((x, y) => y[1].length - x[1].length || x[1][0].rakip.localeCompare(y[1][0].rakip, "tr"));
    const liste = [...ms].reverse(), n = durum.tum ? liste.length : 40;
    const onyillar = [...new Set(tum.map(m => m.tarih.slice(0, 3) + "0"))].sort();
    const rk = durum.rakip ? tum.find(m => m.kod === durum.rakip) : null;
    icerik.innerHTML = `
    <div class="sayfa-bas"><div><h1>${bayrakImg("tr", "bayrak baslik")} A Milli Takım</h1>
      <p class="soluk">${tarihYaz(tum[0].tarih)} – ${tarihYaz(tum.at(-1).tarih)} · ${tum.length} resmi ve özel maç</p></div></div>
    <div class="filtre milli-filtre">
      <select id="mKat"><option value="">Bütün maçlar</option><option value="resmi" ${durum.kat === "resmi" ? "selected" : ""}>Resmi maçlar (özel maçlar hariç)</option>
        ${KAT_SIRA.map(k => `<option ${durum.kat === k ? "selected" : ""}>${k}</option>`).join("")}</select>
      <select id="mOnyil"><option value="">Bütün yıllar</option>${onyillar.map(o => `<option value="${o}" ${durum.onyil === o ? "selected" : ""}>${o}'lar</option>`).join("")}</select>
      ${rk ? `<span class="rozet">${rk.bayrak} ${esc(rk.rakip)} <a href="#" id="mRakipSil" title="Rakip filtresini kaldır">✕</a></span>` : ""}
    </div>
    <nav class="sekmeler bolum">${[["", "Özet ve maçlar"], ["/rekorlar", "Rekorlar ve seriler"]].map(([y, ad]) => `<a href="#/milli${y}" class="${(sekme === "rekorlar") === (y === "/rekorlar") ? "aktif" : ""}">${ad}</a>`).join("")}</nav>
    ${sekme === "rekorlar" ? (ms.length ? rekorHtml(d, ms) : `<div class="bos">Bu filtreye uyan maç yok.</div>`) : `
    ${!ms.length ? `<div class="bos">Bu filtreye uyan maç yok.</div>` : `
    <div class="kart bolum"><div class="ozet-sat">
      <div><b>${T.O}</b><span>Maç</span></div><div><b>${T.G}</b><span>Galibiyet</span></div><div><b>${T.B}</b><span>Beraberlik</span></div>
      <div><b>${T.M}</b><span>Mağlubiyet</span></div><div><b>${T.AG}</b><span>Attığı gol</span></div><div><b>${T.YG}</b><span>Yediği gol</span></div>
      <div><b>%${yuzde(T.G, T.O)}</b><span>Kazanma</span></div></div>
      <div class="cubuk"><i class="g" style="width:${yuzde(T.G, T.O)}%"></i><i class="b" style="width:${yuzde(T.B, T.O)}%"></i><i class="m" style="width:${yuzde(T.M, T.O)}%"></i></div></div>
    <div class="izgara iki bolum ust-hiza milli-iki">
      <div class="tablo-kap"><table class="tablo">${bas(["Yarışma"])}<tbody>${kat.map(([k, l]) => `<tr><td class="ad">${esc(k)}</td>${hucre(say(l))}</tr>`).join("")}</tbody></table></div>
      <div class="tablo-kap"><table class="tablo">${bas(["Dönem"])}<tbody>${onyil.map(([k, l]) => `<tr><td class="ad">${k}'lar</td>${hucre(say(l))}</tr>`).join("")}</tbody></table></div>
    </div>
    <div class="bolum">
      <div class="tablo-kap"><table class="tablo">${bas(["Saha"])}<tbody>${[["E", "Türkiye'de (ev sahibi)"], ["D", "Deplasmanda / tarafsız"]].map(([s, ad]) => [ad, ms.filter(m => m.saha === s)]).filter(x => x[1].length)
        .map(([ad, l]) => `<tr><td class="ad">${ad}</td>${hucre(say(l))}</tr>`).join("")}</tbody></table>
        <p class="soluk not">Ev sahibi, TFF listesinde ilk yazılan takım. Turnuva finallerindeki tarafsız saha maçları TFF'nin yazdığı sıraya göre ayrılıyor.</p></div>
    </div>
    <h2 class="bolum">Rakiplere göre</h2>
    <p class="soluk not">${rakip.length} farklı rakip. Satıra tıklayınca o ülkeyle oynanan maçlar listelenir.</p>
    <div class="tablo-kap"><table class="tablo milli-rakip">${bas(["Rakip"])}<tbody>${rakip.map(([k, l]) => `<tr data-rakip="${esc(k)}" class="tiklanir">
      <td class="ad">${l[0].bayrak} ${esc(l[0].rakip)}</td>${hucre(say(l))}</tr>`).join("")}</tbody></table></div>
    <h2 class="bolum">Maçlar</h2>
    <div class="tablo-kap"><table class="tablo"><thead><tr><th>Tarih</th><th class="ad">Rakip</th><th class="s">Saha</th><th class="s">Skor</th><th class="s"></th><th class="ad">Yarışma</th></tr></thead>
      <tbody>${liste.slice(0, n).map(m => `<tr><td class="tarih">${tarihYaz(m.tarih)}</td><td class="ad">${m.bayrak} ${esc(m.rakip)}</td><td class="s soluk">${m.saha === "E" ? "İç" : "Dış"}</td>
        <td class="s">${skorHtml(m)}</td><td class="s"><span class="son ${m.s}">${m.s}</span></td><td class="ad soluk">${esc(m.org)}</td></tr>`).join("")}</tbody></table></div>
    ${liste.length > n ? `<button class="dugme daha" id="mTum">${liste.length} maçın hepsini göster</button>` : ""}
    <p class="soluk not">Skor her zaman ev sahibi önce yazılır; "İç" Türkiye'nin ev sahibi olduğu maçlar.</p>`}
    <div id="milliOyuncular"></div>`}`;
    $("#mKat").onchange = e => { durum.kat = e.target.value; ciz(); };
    $("#mOnyil").onchange = e => { durum.onyil = e.target.value; ciz(); };
    $("#mRakipSil")?.addEventListener("click", e => { e.preventDefault(); durum.rakip = ""; ciz(); });
    $("#mTum")?.addEventListener("click", () => { durum.tum = true; const y = scrollY; ciz(); scrollTo(0, y); });
    icerik.querySelectorAll("tr[data-rakip]").forEach(tr => tr.addEventListener("click", () => { durum.rakip = tr.dataset.rakip; durum.tum = true; ciz(); scrollTo(0, 0); }));
    if ($("#milliOyuncular")) oyuncular(d, $("#milliOyuncular"));
    icerik.querySelectorAll("details[data-seri]").forEach(x => x.addEventListener("toggle", () => x.open && (x.querySelector(".seri-liste").innerHTML ||= seriListe(JSON.parse(x.dataset.seri)))));
  };
  ciz();
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
      ${mgN.length ? `<ol class="sirali">${sira(mgN, x => x[2]).map(([r, x]) => `<li><span class="sira">${r}</span><span class="kim"><a class="bag" href="#/oyuncu/k${x[0]}">${esc(x[1])}</a>
        <small class="soluk">${tarihYaz(x[4])} · ${esc(x[5])} · <a class="bag" href="#/milli/mac/${x[3]}">maç</a></small></span><b class="n">${x[2]}</b></li>`).join("")}</ol>
        ${mg.length > mgN.length ? `<p class="soluk aciklama">ve ${mg.length - mgN.length} hat-trick daha</p>` : ""}` : `<p class="soluk">—</p>`}</div>
    <div class="kart rekor-kart"><h3>Kalesini en çok gole kapatan kaleciler</h3><p class="soluk aciklama">İlk 11'de başladığı maçlar (bütün maçlar)</p>
      <ol class="sirali">${sira(gk, x => x[3]).map(([r, x]) => `<li><span class="sira">${r}</span><span class="kim"><a class="bag" href="#/oyuncu/k${x[0]}">${esc(x[1])}</a>
        <small class="soluk">${x[2]} maç · %${yuzde(x[3], x[2])} · maç başı ${(x[4] / x[2]).toFixed(2)} gol</small></span><b class="n">${x[3]}</b></li>`).join("")}</ol></div>
  </div>
  <p class="soluk not">Seriler ve maç rekorları yukarıdaki filtreye göre hesaplanır (ör. yalnız resmi maçlar). Kaleci, TFF'nin ilk 11'i kaleciyle başlatmasından bulunuyor.</p>`;
}

function oyuncular(d, kap) {
  const O = Object.entries(d.oyuncu).map(([k, v]) => ({ kisi: k, ad: v[0], mac: v[1], ilk: v[2], gol: v[3], pen: v[4], sari: v[5], kirmizi: v[6], bas: v[7], son: v[8], kulup: v[9] }));
  const sira = (l, f) => { let r = 0, onc; return l.map((x, i) => { const v = f(x); if (v !== onc) { r = i + 1; onc = v; } return [r, x]; }); };
  const kart = (baslik, aciklama, l, f, alt) => `<div class="kart rekor-kart"><h3>${baslik}</h3><p class="soluk aciklama">${aciklama}</p>
    <ol class="sirali">${sira(l.slice(0, 15), f).map(([r, x]) => `<li><span class="sira">${r}</span><span class="kim"><a class="bag" href="#/oyuncu/k${x.kisi}">${esc(x.ad)}</a>
      <small class="soluk">${x.bas.slice(0, 4)}–${x.son.slice(0, 4)} · ${alt(x)}</small></span><b class="n">${f(x)}</b></li>`).join("")}</ol></div>`;
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
    skor: [ev ? m.a : m.y, ev ? m.y : m.a, null, null, null], ustHtml: `<a class="bag" href="#/milli">A Milli Takım</a> · ${esc(m.org)}`,
    stad: r.s, seyirci: r.sy, hakem: r.hk, kaynak: "TFF", tff, kaynakUrl: `https://www.tff.org/Default.aspx?pageID=440&macID=${tff}`, oyuncuOnek: "k",
    kadro: r.k.map(l => l.map(([forma, ad, ilk11, kisi]) => [forma, ad, ilk11, 0, kisi])), teknik: r.t.map(l => l.map(([ad, k]) => [ad, "a" + k])),
    olay: r.o.map(([taraf, tur, dk, ek, a1, a2, tip, k1, k2]) => [taraf, TUR[tur], dk, ek || null, a1, a2, tip === "P" ? "PENALTY" : tip === "K" ? "OWN" : tip === "H" ? "HEADER" : null, k1, k2]),
  });
  document.title = `${(ev ? tr : rk)[0]} - ${(ev ? rk : tr)[0]} · A Milli Takım`;
}

// oyuncu sayfasında milli takım bölümü; yalnizMilli: kulüp kaydı olmayan oyuncu (sayfanın tamamı)
window.milliOyuncu = async (kap, kisi, yalnizMilli) => {
  const d = await milliAl(), v = d.oyuncu[kisi];
  if (!v) return false;
  const [ad, mac, ilk, gol, pen, sari, kirmizi, bas, son, kulup] = v;
  if (yalnizMilli) document.title = `${ad} · Türk Futbol Arşivi`;
  kap.innerHTML = `${yalnizMilli ? `<div class="sayfa-bas"><div><h1>${esc(ad)}</h1><p class="soluk">${esc(kulup.join(", "))}</p></div></div>` : `<h2 class="bolum">${bayrakImg("tr")} A Milli Takım</h2>`}
    <div class="kart bolum"><div class="ozet-sat">
      <div><b>${mac}</b><span>Maç</span></div><div><b>${ilk}</b><span>İlk 11</span></div><div><b>${gol}</b><span>Gol</span></div>
      <div><b>${pen}</b><span>Penaltı golü</span></div><div><b>${sari}</b><span>Sarı kart</span></div><div><b>${kirmizi}</b><span>Kırmızı kart</span></div></div>
      <p class="soluk not">İlk maçı ${tarihYaz(bas)}, son maçı ${tarihYaz(son)}. Milli takıma çağrıldığı kulüpler: ${esc(kulup.join(", ") || "—")}. <a class="bag" href="#/milli">Milli takım sayfası →</a></p></div>`;
  return true;
};

yollar.splice(yollar.length - 1, 0, [/^#\/milli$/, () => milliSayfa("ozet")], [/^#\/milli\/rekorlar$/, () => milliSayfa("rekorlar")], [/^#\/milli\/mac\/(\d+)$/, id => milliMacSayfa(+id)]);
})();

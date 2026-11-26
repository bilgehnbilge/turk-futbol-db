# Türk Futbol Arşivi

Türkiye'de 1959'dan bugüne oynanan profesyonel lig maçları (5 kademe), terfi maçları, Türkiye Kupası, Süper Kupa ve Türk kulüplerinin resmi Avrupa kupası maçları; maç kadroları, goller, kartlar ve oyuncu sayfalarıyla.

**Site:** https://bilgehnbilge.github.io/turk-futbol-db/ (GitHub Pages, `docs/` klasörü). Her gün bot tarafından güncellenir.

## Sitede neler var

| Bölüm | İçerik |
|---|---|
| Kulüpler | 1.864 kulüp: sezon sezon puan tabloları, maçlar, rekorlar, seriler (yenilmezlik, gol yemeden…), geri dönüşler, rakipler, oyuncu ve teknik direktör listeleri, Elo |
| Maçlar | 184.682 maç (174.539 lig, 7.901 Türkiye Kupası, 1.506 Avrupa, 651 terfi, 85 Süper Kupa); 1990'dan bugüne TFF maç sayfalarından kadro, gol, kart, oyuncu değişikliği ve hakemler; 1959-1990 Süper Lig, Türkiye Kupası ve Süper Kupa kadroları Maçkolik arşivinden; Avrupa maçları UEFA'dan |
| Oyuncular | 69 bin oyuncu sayfası: kulüp, sezon ve yarışma kırılımlı maç, gol, kart, dakika (kalecilerde gol yemeden); doğum tarihi ve yeri; TFF lisans hareketleri (transfer, kiralık, sözleşme); Avrupa ve milli takım maçları. Gol, maç ve yaş rekorları (5 lig ve kupa ayrı) |
| Ligler | Süper Lig, 1. Lig, 2. Lig, 3. Lig ve Profesyonelliğe Geçiş Ligi (BAL, 2010-11'den); 1959 öncesi milli küme ve federasyon kupası maçları ayrı bölümde |
| Milli Takım | A Milli Takım'ın 657 maçı, kadroları ve golleri |
| Kadın | Kadın ligleri (2007-08'den bugüne) ayrı bölümde: 13 bin maç, 17 bin oyuncu, Avrupa ve milli maçlar |
| Rekorlar, Sayılar, Elo, Karşılaştır | Genel rekorlar, sezon istatistikleri, Elo puanları, iki kulübü ya da oyuncuyu karşılaştırma |

## Depo düzeni

| Dosya | Açıklama |
|---|---|
| `docs/` | Statik site (`index.html`, `app.js` ve bölüm dosyaları, `style.css`) ve üretilen `docs/data/` |
| `futbol.db` | SQLite veritabanı: `mac`, `kulup`, `kulup_kimlik`, `kulup_adi`, `kulup_ardil` tabloları ve `takim_maci` görünümü. Depodaki kopya eski olabilir; güncelini bot her çalışmada Releases'e ("veritabani" sürümü) yükler |
| `guncelle.py`, `.github/workflows/guncelle.yml` | Bot: güncel sezonu TFF ve UEFA'dan çeker, veritabanını ve siteyi yeniden üretir, gönderir (günde bir kez) |
| `girdiler.py` | Depoya girmeyen büyük girdiler (maç ayrıntıları, kişi bilgileri, kadın ligleri, Maçkolik kadroları…) Releases'te `girdiler.tar.gz` olarak durur; bot her çalışmada indirip günceller |
| `topla.py`, `bal.py`, `kadin.py` | TFF lig arşivleri (erkek ligleri, BAL, kadın ligleri) |
| `oyuncu.py`, `tff_kisi_ek.py` | TFF maç sayfaları (kadro, gol, kart), kişi sayfaları (doğum, lisans hareketleri), teknik direktör ve hakem sayfaları |
| `mackolik*.py`, `avrupa.py`, `uefa_detay.py`, `milli.py` | Maçkolik (1959-1990 maçlar ve arşiv kadroları), UEFA (Avrupa maçları), A Milli Takım |
| `rsssf_*.py`, `wiki_*.py` | RSSSF ve Vikipedi: Intertoto, 1959 öncesi, Süper Kupa, kulüp ardıllıkları ve logolar |
| `birlestir.py` | Bütün kaynakları kulüp kimlikleriyle birleştirip `futbol.db`'yi kurar |
| `web_aktar.py`, `tff_detay.py`, `kadin_site.py` | `futbol.db` ve girdilerden site verisini üretir |
| `kulup_duzeltme.json`, `dogum_duzeltme.json` | Elle verilen kararlar: kulüp eşleştirme/ardıllık ve kullanıcının bildirdiği doğum tarihi düzeltmeleri |
| `yedekle.py` | `raw/` ve `futbol.db`'yi bir yedek klasörüne (ör. Google Drive) yazar, yalnız değişenleri |

Ham indirmeler (`raw/`, ~15 GB) depoda yoktur.

## Güncelleme

Bot her gün kendisi çalışır; elle başlatmak için:

```bash
gh workflow run guncelle.yml
```

Yerelde yeni bir girdi ürettikten sonra (ör. yeni indirilen kadrolar) Releases'teki `girdiler.tar.gz` güncellenmeli; yoksa bot eski girdilerle çalışıp sitedeki yeni bilgiyi geri alır (bkz. `girdiler.py`).

## Örnek sorgu

```sql
-- Bir kulübün lig maçlarındaki en farklı galibiyetleri
SELECT tarih, takim, rakip, attigi, yedigi
FROM takim_maci
WHERE kulup = (SELECT id FROM kulup WHERE ad = 'Pendikspor') AND yarisma = 'lig'
ORDER BY fark DESC, attigi DESC LIMIT 5;
```

## Kaynaklar ve sınırlar

- **TFF:** 1984-85'ten bugüne Süper Lig, 1990-91'den bugüne alt ligler ve kupa; maç sayfaları (kadro 1990-91'den, gol dakikaları 1991-92'den), kişi, teknik direktör ve hakem sayfaları. Doğum tarihleri TFF kayıtlarındaki gibidir.
- **Maçkolik:** 1959-1990 ligler, Türkiye Kupası ve Avrupa kupaları; arşivden 1959-1991 Süper Lig ve 1962-1990 kupa kadroları.
- **UEFA:** Avrupa kupası maç kadroları, olayları ve istatistikleri.
- **RSSSF ve Vikipedi:** 1959 öncesi, Intertoto, Süper Kupa ve kulüp ardıllıkları.
- Puan tabloları maç sonuçlarından hesaplanır; puan silme cezaları dahil değildir.
- Ankara, İstanbul ve İzmir mahalli ligleri kapsam dışıdır. 1990 öncesi 2. ve 3. Lig maçlarında kadro ve gol bilgisi yoktur.

# Türk Futbol Arşivi

1959'dan bugüne Türkiye'deki profesyonel lig maçları, terfi maçları, Türkiye Kupası ve Türk kulüplerinin resmi Avrupa kupası maçları: **149.489 maç, 1.190 kulüp**.

Arama arayüzü GitHub Pages üzerinde yayınlanır (`site/` klasörü). Kulüp ara; rekorlarına, serilerine (yenilmezlik, gol yemeden…), rakiplerine ve sezon sezon puan tablolarına bak.

## İçerik

| Dosya | Açıklama |
|---|---|
| `futbol.db` | SQLite veritabanı: `mac`, `kulup`, `kulup_kimlik`, `kulup_adi`, `kulup_ardil`, `kapsam` tabloları ve `takim_maci` görünümü |
| `site/` | Statik arayüz (`index.html`, `app.js`, `style.css`) ve `web_aktar.py`'nin ürettiği `site/data/*.json` |
| `kulup_duzeltme.json` | Elle yapılan kulüp eşleştirme kararları (ayırma, birleştirme, ardıllık, dönem adları) ve gerekçeleri |
| `mackolik_maclar.csv`, `avrupa_maclar.csv` | Maçkolik'ten ayıklanmış maçlar |
| `topla.py` | TFF arşivini indirir ve `raw/tff.db`'yi kurar |
| `mackolik.py`, `avrupa.py`, `rsssf_intertoto.py` | Maçkolik, Avrupa kupaları ve RSSSF Intertoto verisi |
| `birlestir.py` | Bütün kaynakları kulüp kimlikleriyle birleştirip `futbol.db`'yi kurar |
| `wiki_kulup.py` | Vikipedi/Wikidata'dan kulüp kuruluş, kapanış ve TFF numaralarını çeker (kontrol için) |
| `web_aktar.py` | `futbol.db`'den arayüz verisini üretir |

Ham indirmeler (`raw/`, birkaç GB) depoda yoktur.

## Örnek sorgu

```sql
-- Bir kulübün lig maçlarındaki en farklı galibiyetleri
SELECT tarih, takim, rakip, attigi, yedigi
FROM takim_maci
WHERE kulup = (SELECT id FROM kulup WHERE ad = 'Pendikspor') AND yarisma = 'lig'
ORDER BY fark DESC, attigi DESC LIMIT 5;
```

## Güncelleme

```bash
python3 birlestir.py     # futbol.db
python3 web_aktar.py     # site/data
```

## Kaynaklar ve sınırlar

- TFF (1984-85'ten bugüne Süper Lig, 1990-91'den bugüne alt ligler), Maçkolik (1959-1990 ligler, kupa, Avrupa), RSSSF ve Vikipedi.
- Puan tabloları maç sonuçlarından hesaplanır; puan silme cezaları dahil değildir.
- Ankara, İstanbul ve İzmir mahalli ligleri kapsam dışıdır. Oyuncu, gol ve kart verisi henüz yoktur.

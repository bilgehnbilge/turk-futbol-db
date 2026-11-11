# Denetim raporu — 12.11.2026

Kapsam: `futbol.db`'nin tamamı (149.574 maç) ve yerel sitedeki 71 sezon sayfası ile 108 kulübün bütün sekmeleri.

Ana yöntem: TFF ve Maçkolik'in resmi puan tablolarındaki 8.429 takım satırı, bizim maçlarımızdan hesaplanan değerlerle karşılaştırıldı (O/G/B/M/AG/YG). 7.836 satır birebir tutuyor; tutmayan 93 grup aşağıda türlerine göre ayrıldı.

## 1. Şu anki kurulumun düzelttiği

- **2. Lig 2007-10 Yükselme Grubu** (10+10+9 takım, 90+90+72 maç) "play-off" etiketliydi, sezon sayfasında görünmüyordu. Maçların hepsi elimizde; yeni kurulumda kendi grubu olarak geliyor.

## 2. Gerçek veri hataları (birleştirme kodunda düzeltilebilir, kurulum gerektirmez)

| # | Sorun | Etki | Örnek |
|---|---|---|---|
| 2.1 | **Çift kayıt**: TFF'nin 1. Lig 2008-09 sayfalarında maç numarası yok; son hafta iki kez kaydedilmiş | 9 maç iki kez sayılıyor | Orduspor 1-2 Manisaspor (09.05.2009) ×2 |
| 2.2 | **İptal edilip tekrar oynanan maç** iki kez sayılıyor | 7 maç fazla | Samsunspor–Beşiktaş 09.09.2001 0-0 (iptal) ve 10.10.2001 2-1; Beşiktaş–Gençlerbirliği 06.02.2005 1-1 ve 09.03.2005 0-0; Karagümrük–İnegöl 2003-04; Orduspor–Eskişehir ve Adıyaman–Osmaniye 2004-05; Altay–Sakarya 2005-06 (1. Lig); Nilüfer–Akseki 2005-06 |
| 2.3 | **Play-off maçları lig maçı sayılıyor** | 1. Lig 2008-09 ve 2011-20 arası her sezon 5 maç; 2. Lig Yükselme 1994-95, 1998-99, 1999-2000'de 1'er maç | Göztepe 1-0 Rizespor (30.05.1999, eşitlik maçı) |
| 2.4 | **Skor tutarsızlığı**: resmi tablo ile maç skoru arasında 1-2 gol fark | 14 grup, büyük olasılıkla her birinde tek maç | Maçkolik 1974-88'de 2. Lig'den 8 grup; TFF: Süper Lig 1994-95 (Gaziantepspor–Denizlispor), 1. Lig 2006-07 (Gençlerbirliği Oftaş–Elazığspor), 3. Lig 2011-12, 2012-13, 2014-15 |
| 2.5 | **Çifte hükmen**: 2022-23 Göztepe–Altay maçında resmi tabloda iki takım da 0-3 yenik sayılmış | Bizde "oynanmadı"; tek bir skorla yazılamıyor | Karar gerekiyor (bkz. Sorular) |
| 2.6 | **Tarih hatası** | Fenerbahçe aynı gün iki lig maçında | 24.09.1961: Fenerbahçe–Şekerhilal ve Fenerbahçe–Ankaragücü (Maçkolik) |
| 2.7 | **Ligden çekilen takımın fikstürü** | 36 skorsuz maç | GMG Kastamonuspor 2021-22 2. Lig Beyaz: sezon başlamadan çekilmiş (resmi tabloda 0 maç), fikstürü "oynanmadı" diye görünüyor |

## 3. Benim eşleştirme hatam

- **Resmi tablo yanlış gruba bağlanıyor** (1992-2007 arası 2. ve 3. Lig'in ilk aşama grupları, 70 grup): TFF'nin bu sayfalarda gösterdiği 8 takımlı klasman tablosu, 10 takımlı ilk aşama grubuna bağlanmış. Veri hatası değil. Puan silme bilgisi bu gruplarda yanlış olabilir. Düzeltme: tablo ancak takım sayısı tutuyorsa bağlanacak.

## 4. Kapsam

| Konu | Durum |
|---|---|
| **2026-27 lig sezonu** | **Yok.** Kupa ve Avrupa'da 2026-27 maçları var ama dört ligin bu sezonu indirilmedi. Şu an sürmekte olan sezon. |
| 1959-1963 | Yalnız en üst lig var: doğru, 2. Lig 1963'te kuruldu |
| 3. Lig 1980-84 | Yok: doğru, lig o yıllarda oynanmadı |
| 2019-20 alt ligler | 265 maç skorsuz: lig COVID nedeniyle yarıda bitirildi, doğru |
| Avrupa | 62 maç tarafının kulübü yok: RSSSF'ten gelen yabancı Intertoto rakipleri |
| Mahalli ligler | Kapsam dışı (senin kararın) |
| Oyuncu/gol/kart | Henüz yok |

## 5. Site

- **Düzeltildi**: Arama, alakasız sorgularda da Galatasaray/Fenerbahçe/Beşiktaş'ı öneriyordu ("1461" yazınca Galatasaray çıkıyordu). Yerelde düzeltildi, bir sonraki gönderimde canlıya geçer.
- Otomatik taramada hiçbir sayfada JavaScript hatası, "undefined" ya da "NaN" çıkmadı.
- **Kısaltmalarla arama yok**: "GS", "FB", "BJK", "KSK" sonuç vermiyor.
- **Bazı kulüp adları Maçkolik kısaltmasıyla**: "Ç. Rizespor", "Ankara Demir".
- **Yedek takımlar aramada çıkıyor**: "Galatasaray (2P)", "Beşiktaş II" gibi eski kupa ve lig kayıtları ayrı kulüp olarak listeleniyor.
- **Puan tabloları hâlâ hesaplanmış**: Resmi tablolar (puan silmeli) veritabanında var, senin isteğinle sitede değil. Madde 2.1-2.3 düzelince hesaplanan tablolar da resmisine yaklaşacak.
- **Tarihsiz hükmen maçlar seri hesabına girmiyor**: Bu 85 maçın tarihi olmadığı için sırası belirsiz.
- **Yalnızca kupada görünen kulüpler**: 196 amatör kulübün 1-3 maçı var; bunlar arama sonuçlarını kalabalıklaştırıyor.

## Sorular

1. Göztepe–Altay 2022-23 çifte hükmeni nasıl yazalım? Seçenekler: "0-3 / 3-0 (çifte H)" diye özel bir sonuç; ya da maçı listede bırakıp tablo hesabına "iki takıma yenilgi" olarak katmak.
2. 2026-27 lig sezonunu şimdi ekleyelim mi? TFF'den dört lig için yaklaşık 200 sayfa, birkaç dakika sürer.

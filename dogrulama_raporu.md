# Erkek ligleri doğrulama raporu

`python3 dogrula.py` ile üretildi. 669 resmi puan tablosu (TFF: 481, Maçkolik arşivi: 188) futbol.db'deki maçlardan hesaplanan tablolarla karşılaştırıldı.

| Sonuç | Tablo |
|---|---|
| tam | 648 |
| skor | 3 |
| eksik | 1 |
| fazla | 0 |
| eksik+fazla | 0 |
| kulüp eşlemesi | 2 |
| farklı aşama | 2 |
| bağlanamadı | 13 |

Bağlanan tablolardaki 9.589 takım satırının 9.563 tanesi birebir tutuyor.

Resmi tablosu bulunmayan lig grubumuz: 111.

## Lig seviyesine göre

| Lig | tam | skor | eksik | fazla | eksik+fazla | kulüp eşlemesi | farklı aşama | bağlanamadı |
|---|---|---|---|---|---|---|---|---|
| 1. Lig | 191 | 3 | 1 | 0 | 0 | 2 | 1 | 1 |
| 2. Lig | 294 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3. Lig | 95 | 0 | 0 | 0 | 0 | 0 | 0 | 10 |
| Süper Lig | 68 | 0 | 0 | 0 | 0 | 0 | 1 | 2 |

## Eksik maç (1 tablo)

| Sezon | Lig | Grup | Kaynak | Resmi maç | Bizde | Farklı takım | Örnek (resmi O/G/B/M/AG/YG → bizde) ya da tutmayan maç |
|---|---|---|---|---|---|---|---|
| 1990-1991 | 1. Lig | A | Maçkolik | 306 | 306 | 1/18 | Düzce Kervan Doğsanspor: 34/9/13/12/32/38 → yok |

## Skor farkı (3 tablo)

| Sezon | Lig | Grup | Kaynak | Resmi maç | Bizde | Farklı takım | Örnek (resmi O/G/B/M/AG/YG → bizde) ya da tutmayan maç |
|---|---|---|---|---|---|---|---|
| 1974-1975 | 1. Lig | Kırmızı | Maçkolik | 240 | 240 | 4/16 | Gaziantepspor: 30/14/10/6/31/18 → 30/14/10/6/30/18; Mersin İ.Y.: 30/14/6/10/36/23 → 30/14/6/10/36/22 |
| 1977-1978 | 1. Lig | Beyaz | Maçkolik | 240 | 240 | 2/16 | Resmi tabloda İSKENDERUNSPOR, Altınordu için G+B+M ≠ O (kaynak hatası).  |
| 1986-1987 | 1. Lig | A Grubu | Maçkolik | 272 | 272 | 9/17 | Adana Demirspor: 32/23/7/2/77/27 → 32/24/6/2/78/26; Gaziantepspor: 32/12/11/9/34/40 → 32/12/11/9/35/41 |

## Kulüp eşlemesi (maçlar tam, bir takım başka kimlikle) (2 tablo)

| Sezon | Lig | Grup | Kaynak | Resmi maç | Bizde | Farklı takım | Örnek (resmi O/G/B/M/AG/YG → bizde) ya da tutmayan maç |
|---|---|---|---|---|---|---|---|
| 1990-1991 | 1. Lig | B | Maçkolik | 306 | 306 | 1/18 | Afyonspor: 34/8/10/16/30/53 → 0/0/0/0/0/0 |
| 1990-1991 | 1. Lig | C | Maçkolik | 272 | 272 | 1/17 | PTT: 32/11/6/15/41/52 → 0/0/0/0/0/0 |

## Farklı aşamanın tablosu (karşılaştırılamadı) (2 tablo)

| Sezon | Lig | Grup | Kaynak | Resmi maç | Bizde | Farklı takım | Örnek (resmi O/G/B/M/AG/YG → bizde) ya da tutmayan maç |
|---|---|---|---|---|---|---|---|
| 2009-2010 | 1. Lig | - | TFF | 6 | 306 | 4/4 | Konyaspor: 3/2/1/0/6/3 → 34/15/10/9/42/37; Altay: 3/1/2/0/4/3 → 34/17/8/9/48/36 |
| 2011-2012 | Süper Lig | - | TFF | 12 | 330 | 4/4 | Galatasaray: 6/2/3/1/9/6 → 40/25/11/4/78/30; Fenerbahçe: 6/4/1/1/9/4 → 40/24/9/7/70/38 |

## Bağlanamayan resmi tablolar (13)

Takımları hiçbir lig grubumuzla %70 örtüşmüyor. Çoğu ikinci aşama (klasman, play-off, yükselme) tablosu ya da kulüp eşlemesi yapılamamış eski kayıt.

| Sezon | Lig | Grup | Kaynak | Takım | Ortak takım |
|---|---|---|---|---|---|
| 1959 | Süper Lig | Milli Ligi | Maçkolik | 16 | %50 |
| 1962-1963 | Süper Lig | Milli Ligi | Maçkolik | 12 | %50 |
| 1965-1966 | 1. Lig | 2.Futbol Ligi Yükselme Grubu | Maçkolik | 8 | %50 |
| 2008-2009 | 3. Lig | 01 | TFF | 10 | %30 |
| 2008-2009 | 3. Lig | 02 | TFF | 10 | %30 |
| 2008-2009 | 3. Lig | 03 | TFF | 10 | %30 |
| 2008-2009 | 3. Lig | 04 | TFF | 10 | %30 |
| 2008-2009 | 3. Lig | 05 | TFF | 10 | %30 |
| 2008-2009 | 3. Lig | 1. Klasman Grubu | TFF | 10 | %30 |
| 2008-2009 | 3. Lig | 2. Klasman Grubu | TFF | 10 | %30 |
| 2008-2009 | 3. Lig | 3. Klasman Grubu | TFF | 10 | %30 |
| 2008-2009 | 3. Lig | 4. Klasman Grubu | TFF | 10 | %30 |
| 2008-2009 | 3. Lig | 5. Klasman Grubu | TFF | 10 | %30 |

## Resmi tablosu olmayan lig gruplarımız (111)

- **1. Lig** (45): 1992-1993 01, 1992-1993 02, 1992-1993 03, 1992-1993 04, 1992-1993 05, 1993-1994 01, 1993-1994 02, 1993-1994 03, 1993-1994 04, 1993-1994 05, 1994-1995 01, 1994-1995 02, 1994-1995 03, 1994-1995 04, 1994-1995 05, 1995-1996 01, 1995-1996 02, 1995-1996 03, 1995-1996 04, 1995-1996 05, 1996-1997 01, 1996-1997 02, 1996-1997 03, 1996-1997 04, 1996-1997 05, 1997-1998 01, 1997-1998 02, 1997-1998 03, 1997-1998 04, 1997-1998 05, 1998-1999 01, 1998-1999 02, 1998-1999 03, 1998-1999 04, 1998-1999 05, 1999-2000 01, 1999-2000 02, 1999-2000 03, 1999-2000 04, 1999-2000 05, 2000-2001 01, 2000-2001 02, 2000-2001 03, 2000-2001 04, 2000-2001 05
- **2. Lig** (43): 2001-2002 01, 2001-2002 02, 2001-2002 03, 2001-2002 04, 2001-2002 05, 2005-2006 01, 2005-2006 02, 2005-2006 03, 2005-2006 04, 2005-2006 05, 2006-2007 01, 2006-2007 02, 2006-2007 03, 2006-2007 04, 2006-2007 05, 2007-2008 01, 2007-2008 02, 2007-2008 03, 2007-2008 04, 2007-2008 05, 2007-2008 1. Klasman Grubu, 2007-2008 2. Klasman Grubu, 2007-2008 3. Klasman Grubu, 2007-2008 4. Klasman Grubu, 2007-2008 5. Klasman Grubu, 2008-2009 01, 2008-2009 02, 2008-2009 03, 2008-2009 04, 2008-2009 05, 2008-2009 1. Klasman Grubu, 2008-2009 2. Klasman Grubu, 2008-2009 3. Klasman Grubu, 2008-2009 4. Klasman Grubu, 2008-2009 5. Klasman Grubu, 2009-2010 01, 2009-2010 02, 2009-2010 03, 2009-2010 04, 2009-2010 1. Klasman Grubu, 2009-2010 2. Klasman Grubu, 2009-2010 3. Klasman Grubu, 2009-2010 4. Klasman Grubu
- **3. Lig** (21): 2008-2009 01, 2008-2009 02, 2008-2009 03, 2008-2009 04, 2008-2009 05, 2008-2009 1. Klasman Grubu, 2008-2009 2. Klasman Grubu, 2008-2009 3. Klasman Grubu, 2008-2009 4. Klasman Grubu, 2008-2009 5. Klasman Grubu, 2008-2009 Yükselme Grubu, 2009-2010 01, 2009-2010 02, 2009-2010 03, 2009-2010 04, 2009-2010 05, 2009-2010 1. Klasman Grubu, 2009-2010 2. Klasman Grubu, 2009-2010 3. Klasman Grubu, 2009-2010 4. Klasman Grubu, 2009-2010 5. Klasman Grubu
- **Süper Lig** (2): 1959 Beyaz, 1959 Kırmızı

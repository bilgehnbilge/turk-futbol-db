#!/bin/bash
# Pilot indirme: az sayida sayfayi ham haliyle raw/pilot klasorune kaydeder.
# Yalnizca indirir, baska hicbir sey degistirmez. Istekler arasinda 3 saniye bekler.
cd "$(dirname "$0")" || exit 1
mkdir -p raw/pilot
UA="turk-futbol-db/0.1 (kisisel arsiv)"

while read -r ad url; do
  [ -z "$ad" ] && continue
  sonuc=$(curl -sL -m 45 -A "$UA" -o "raw/pilot/$ad.html" -w '%{http_code} %{size_download}' "$url")
  echo "$ad -> ${sonuc:-hata}"
  sleep 3
done <<'LISTE'
tff_robots https://www.tff.org/robots.txt
mackolik_robots https://www.mackolik.com/robots.txt
tff_arsiv_superlig https://www.tff.org/default.aspx?pageID=545
tff_arsiv_1lig https://www.tff.org/default.aspx?pageID=563
tff_arsiv_2lig_a https://www.tff.org/default.aspx?pageID=371
tff_arsiv_2lig_b https://www.tff.org/default.aspx?pageID=571
tff_arsiv_3lig https://www.tff.org/default.aspx?pageID=376
tff_3lig_1990_varsayilan https://www.tff.org/default.aspx?pageID=792
tff_3lig_1990_grup1 https://www.tff.org/Default.aspx?pageID=792&grupID=396
tff_2lig_2025 https://www.tff.org/Default.aspx?pageID=1769&hafta=1
tff_mac_detay_1990 https://www.tff.org/Default.aspx?pageID=29&macId=66078
mackolik_superlig_1961 https://www.mackolik.com/puan-durumu/t%C3%BCrkiye-trendyol-s%C3%BCper-lig/1961-1962/482ofyysbdbeoxauk19yg7tdt
mackolik_2lig_1973 https://www.mackolik.com/puan-durumu/t%C3%BCrkiye-2-lig/1973-1974/2nttcoriwf5co73vmz1vr8frm
mackolik_2lig_1978 https://www.mackolik.com/puan-durumu/t%C3%BCrkiye-tff-2-lig/1978-1979/2nttcoriwf5co73vmz1vr8frm
mackolik_3lig https://www.mackolik.com/puan-durumu/t%C3%BCrkiye-tff-3-lig/fikstur/907l7wtxdvugdo9i2249wcmr0
LISTE
echo "Bitti. Dosyalar: raw/pilot"

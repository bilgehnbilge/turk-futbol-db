#!/bin/zsh
# Arsiv sitesinden kalan her seyi sirayla indirir: terfi ligleri -> Turkiye Kupasi -> takim sayisi kontrolu -> CSV.
# Site saatlik kota uyguluyor (429). Bir adim 429 ile durursa 30 dk bekleyip kaldigi yerden surer.
# Inmis dosyalar atlanir; yarida kalirsa ayni komutla yeniden baslatilabilir:  ./arsiv_toplu.sh
cd "$(dirname "$0")"
LOG=arsiv_toplu.log
for adim in terfi kupa kontrol; do
  for deneme in $(seq 1 40); do
    echo "== $adim deneme $deneme $(date '+%Y-%m-%d %H:%M')" >> $LOG
    if python3 -u mackolik.py $adim >> $LOG 2>&1; then
      echo "== $adim TAMAM $(date '+%H:%M')" >> $LOG
      break
    fi
    echo "== $adim durdu (muhtemelen 429), 30 dk bekleniyor" >> $LOG
    sleep 1800
  done
done
python3 mackolik.py ayikla > ayikla.log 2>&1
echo "== HEPSI BITTI $(date '+%H:%M')" >> $LOG

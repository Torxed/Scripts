# WIFI:
# remove examples from /etc/wpa_supplicant/wpa_supplicant.conf
# run: wpa_passphrase "SSID" "PASSWD"
# wpa_supplicant -i wlp3s0 -c /etc/wpa_supplicant_wpa_supplicant.conf &
# dhcpcd wlp3s0

pacman -Syu --ignore filesystem,bash
pacman -S bash
pacman -Su
pacman -S python2
wget https://raw.github.com/Torxed/Scripts/master/python/archinstaller/install.py
wget https://raw.github.com/Torxed/Scripts/master/python/archinstaller/inside_install.py
python2 install.py

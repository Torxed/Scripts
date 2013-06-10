# WIFI:
# remove examples from /etc/wpa_supplicant/wpa_supplicant.conf
# run: wpa_passphrase "SSID" "PASSWD"
# wpa_supplicant -i wlp3s0 -c /etc/wpa_supplicant_wpa_supplicant.conf &
# dhcpcd wlp3s0

echo y | pacman -Syu --ignore filesystem,bash
echo y | pacman -S bash
echo y | pacman -Su
echo y | pacman -S python2
# module.py is a module import library that dynamicly fetches required modules.
# It fetches output, system-executions modules etc needed in install.py.
wget https://raw.github.com/Torxed/Scripts/master/python/module.py
wget https://raw.github.com/Torxed/Scripts/master/python/archinstaller/install.py
wget https://raw.github.com/Torxed/Scripts/master/python/archinstaller/inside_install.py
python2 install.py

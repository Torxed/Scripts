# WIFI:
# remove examples from /etc/wpa_supplicant/wpa_supplicant.conf
# run: wpa_passphrase "SSID" "PASSWD"
# wpa_supplicant -i wlp3s0 -c /etc/wpa_supplicant_wpa_supplicant.conf &
# dhcpcd wlp3s0

#echo y | pacman -Syu --ignore filesystem,bash
#echo y | pacman -S bash
#echo y | pacman -Su

clear
echo "  ____________________________________________"
echo " | Welcome to the ArchLinux Automated install |"
echo " |  -   -   -   -   -   -   -   -   -   -   - |"

## We say no to the update, we just want to update the package lists..
## Unless the original ISO source wasn't to old upon build, this should work fine.
echo " | Updating package lists"
echo n | pacman -Syu &>/dev/null
echo " | Installing Python2 in Live environment"
echo y | pacman -S python2 &>/dev/null

# module.py is a module import library that dynamicly fetches required modules.
# It fetches output, system-executions modules etc needed in install.py.
echo " | Downloading Installer scripts"
wget https://raw.github.com/Torxed/Scripts/master/python/module.py &>/dev/null
wget https://raw.github.com/Torxed/Scripts/master/python/archinstaller/install.py &>/dev/null
wget https://raw.github.com/Torxed/Scripts/master/python/archinstaller/inside_install.py &>/dev/null

python2 install.py

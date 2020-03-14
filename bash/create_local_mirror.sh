#!/bin/bash

TMP_DB="/tmp/pacdb"
ROOT_PATH="/srv/http/local_mirror"
BIN_PATH="os/x86_64"
# expac simply resolves dependencies, splits them into new lines and tr just wraps them on the same line
PACKAGES="base base-devel linux linux-firmware btrfs-progs efibootmgr nano wpa_supplicant dialog nano lollypop gstreamer gst-plugins-good gnome-keyring nemo gpicview-gtk3 chromium awesome xorg-server xorg-xrandr xorg-xinit xterm feh slock xscreensaver terminus-font-otb gnu-free-fonts ttf-liberation xsel qemu ovmf openssh sshfs git htop pkgfile scrot dhclient wget smbclient cifs-utils libu2f-host pulseaudio pulseaudio-alsa pavucontrol python git python-psutil python-systemd python-pygeoip geoip-database syslinux haveged intel-ucode amd-ucode memtest86+ mkinitcpio-nfs-utils nbd zsh efitools"
#PACKAGES=$(expac -S '%E' -l '\n' ${PACKAGES} | tr '\n' ' ')

mkdir -p "${TMP_DB}"
mkdir -p "${BIN_PATH}"
sudo pacman --dbpath "${TMP_DB}" -Syu -w --root "${ROOT_PATH}" --cachedir "${BIN_PATH}" ${PACKAGES}
sudo repo-add "${ROOT_PATH}/${BIN_PATH}/local_repo.db.tar.gz" "${ROOT_PATH}/${BIN_PATH}/{*.pkg.tar.xz,*.pkg.tar.zst}"

cat <<EOF
[local_repo]
Server = http://local-repo/$repo/os/$arch
SigLevel = Optional TrustAll
EOF

# packages (video-vmware may not be needed)
virtualbox-guest-utils
xf86-video-vmware
wmctrl
xorg-xwininfo

git clone --recursive https://github.com/Torxed/archinstall_gui.git
cd archinstall_gui/dependencies/archinstall; git checkout cleanup; cd -
cp archinstall_gui/INSTALL/archinstall_gui.service /etc/systemd/system/
cp archinstall_gui/INSTALL/xinitrc /etc/X11/xinit/
cp -r archinstall_gui /srv/
chmod +x /srv/archinstall_gui/webgui.py
systemctl daemon-reload
systemctl enable archinstall_gui.service

# VirtualBox hacks:
systemctl enable vboxservice.service
mkdir -p /etc/modules-load.d
echo 'modprobe -a vboxguest vboxsf vboxvideo' >> /etc/modules-load.d/virtualbox.conf
# https://bbs.archlinux.org/viewtopic.php?id=119015

# To expand chromium to full screensize without a WM:
sed -i 's/chromium/for (( i = 0; i < 10; i += 1)); do\nchromium/' /etc/X11/xinit/xinitrc
sed -i 's/chromium/  windowID=$(printf '"'"'%#x'"'"'  "0x${i}00001")\nchromium/' /etc/X11/xinit/xinitrc
sed -i 's/chromium/  $(sleep 1; wmctrl -i -r ${windowID} -e 0,0,0,1280,1024) \&\nchromium/' /etc/X11/xinit/xinitrc
sed -i 's/chromium/done\nchromium/' /etc/X11/xinit/xinitrc

# Setup screen resolutions:
sed -i 's/sda3 rw/sda3 rw vga=1280x1024 video=1280x1024/' /boot/syslinux/syslinux.cfg
sed -i 's/chromium/xrandr --output VGA-1 --mode "1280x1024"\nchromium/' /etc/X11/xinit/xinitrc

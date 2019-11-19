# packages (video-vmware may not be needed)
virtualbox-guest-utils
xf86-video-vmware
wmctrl

# VirtualBox hacks:
systemctl enable vboxservice.service
sed -i 's/sda3 rw/sda3 rw video=1280x1024/' /boot/syslinux/syslinux.cfg
sed -i 's/chromium/VBoxClient --display\nchromium/' /etc/X11/xinit/xinitrc
sed -i 's/chromium/VBoxClient --vmsvga-x11\nchromium/' /etc/X11/xinit/xinitrc
sed -i 's/chromium/xrandr --output VGA-1 --mode "1280x1024"\nchromium/' /etc/X11/xinit/xinitrc
sed -i 's/chromium/$(sleep 0.5; wmctrl -i -r 0x800001 -e 0,0,0,1280,1024) &\nchromium/' /etc/X11/xinit/xinitrc

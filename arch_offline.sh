cp /etc/pacman.conf /etc/pacman_32.conf
# modify /etc/pacman_32.conf:
# Architecture = auto -> i686

cp /etc/makepkg.conf /etc/makepkg_32.conf
# modify /etc/makepkgs_32.conf:
# CARCH="i686"
# CHOST="i686-unknown-linux-gnu"
# CFLAGS="-march=i686 -mtune=generic -O2 -pipe"
# CXXFLAGS="-march=i686 -mtune=generic -O2 -pipe"

sudo mkarchroot -C /etc/pacman_32.conf -M /etc/makepkg_32.conf /opt/arch32/root base base-devel

mkdir -p /tmp/32bit
mkdir -p /tmp/64bit
pacman --root /opt/arch32 --config /etc/pacman_32.conf --cachedir /tmp/32bit/ -S -w awesome xorg-xinit xorg-server xorg-server-utils base base-devel
pacman --cachedir /tmp/64bit/ -S -w awesome xorg-xinit xorg-server xorg-server-utils base base-devel

mkdir -p ~/customrepo/x86_64/
mkdir -p ~/customrepo/i686/

cp /tmp/32bit/* ~/customrepo/i686/
cp /tmp/64bit/* ~/customrepo/x86_64/

repo-add ~/customrepo/i686/customrepo.db.tar.gz ~/customrepo/i686/*.pkg.tar.xz
repo-add ~/customrepo/x86_64/customrepo.db.tar.gz ~/customrepo/x86_64/*.pkg.tar.xz

# Now, modify /etc/pacman.conf ** ON A LIVE CD ALREADY RUNNING **
# [customrepo]
# SigLevel = Optional TrustAll
# Server = file:///tmp/usb/customrepo/$arch

# And make sure you've mounted the USB/CD/DVD under /tmp/usb <----

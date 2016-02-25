# cp /etc/pacman.conf /etc/pacman_32.conf      # <--- Uncomment for first ever build/setup
# cp /etc/makepkg.conf /etc/makepkg_32.conf    # <--- Uncomment for first ever build/setup

# Setup stuff
mkdir -p /tmp/32bit
mkdir -p /tmp/64bit
mkdir -p ~/customrepo/x86_64
mkdir -p ~/customrepo/i686

#--sudo mkarchroot -C /etc/pacman_32.conf -M /etc/makepkg_32.conf /opt/arch32/root base base-devel

# Clean out old crap from previous build
rm -rf airootfs/root/customrepo/
rm /tmp/32bit/*
rm /tmp/64bit/*
rm ~/customrepo/x86_64/*
rm ~/customrepo/i686/*

# Download 64 and 32bit packages needed for a live-CD+base install of Arch to a HDD
# (remember, most of these packages are used by "base" and "base-devel" which are
# absolut dependencies of what Arch will require you to have. nano, xorg-server and a few
# others are stuff I like to have)
# --> expac -S '%E' -l '\n' <package> <package> ... 
#     this would solve the depedency issue nicely.
rm -rf /tmp/pacdb; mkdir /tmp/pacdb
pacman --dbpath /tmp/pacdb/ -Syu -w --cachedir /tmp/64bit/ awesome xorg-xinit xorg-server xorg-server-utils xterm nano screen sudo iptables xf86-video-intel mesa-libgl dhclient dnsmasq darkhttpd openssh sshfs python git openssl gcc base base-devel grub os-prober

rm -rf /tmp/pacdb; mkdir /tmp/pacdb
pacman --dbpath /tmp/pacdb/ -Syu -w --root /opt/aur/root --config /etc/pacman_32.conf --cachedir /tmp/32bit/ awesome xorg-xinit xorg-server xorg-server-utils xterm nano screen sudo iptables xf86-video-intel mesa-libgl dhclient dnsmasq darkhttpd openssh sshfs python git openssl gcc base base-devel grub os-prober

# These are now placed in /tmp/32bit and /tmp/64bit respectively.
# So we copy these "offline packages" to the custom repo we're trying to build
cp /tmp/32bit/* ~/customrepo/i686/
cp /tmp/64bit/* ~/customrepo/x86_64/

# Then when all packages are in a neat folder structure that pacman likes..
# we use repo-add to create a package database that pacman will look for.
# Then we copy sad custom repo called "customrepo" to our live-cd /root folder for later use.
repo-add ~/customrepo/x86_64/customrepo.db.tar.gz ~/customrepo/x86_64/*.pkg.tar.xz
repo-add ~/customrepo/i686/customrepo.db.tar.gz ~/customrepo/i686/*.pkg.tar.xz
cp -r ~/customrepo airootfs/root/

# We clean out any old builds
# and we build a new Live-CD (with our customrepo in /root)
rm -rf work/*
./build.sh -v

# use 'cdw' or something to burn this DVD
# Boot it, and modify /etc/pacman.conf to have the following:

# [customrepo]
# SigLevel = Optional TrustAll
# Server = file:///root/customrepo/$arch

# And when you're following "Beginners guide" in the Arch-Wiki,
# and you hit the step "pacstrap -i /mnt base base-devel" DO THE FOLLOWING:
#                                                                |
#                                                               \/
# pacstrap -i /mnt base base-devel grub os-prober xorg-server awesome nano screen ...
#
# Because it's a hell of a lot easier than trying to fiddle with the CD afterwards :P

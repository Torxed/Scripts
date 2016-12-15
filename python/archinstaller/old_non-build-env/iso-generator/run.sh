#!/bin/bash

#Dependencies:
# squashfs-tools cdrkit

ORIGINAL_ISO="/arch.iso"
DESTINATION_DIR="$HOME/isos"
GIT_FOLDER="$HOME/github"

sudo umount /mnt/archiso &>/dev/null
sudo umount /mnt/rootfs &>/dev/null
sudo rm -rf /mnt/archiso &>/dev/null
sudo rm -rf /mnt/rootfs &>/dev/null
sudo rm -rf ./customiso &>/dev/null
sudo rm -rf ./squashfs-root &>/dev/null
sudo rm root-image.fs.sfs &>/dev/null
sudo rm arch-auto-dual.iso &>/dev/null

sudo mkdir /mnt/archiso
sudo mount -t iso9660 -o loop $ORIGINAL_ISO /mnt/archiso
mkdir customiso
cp -a /mnt/archiso/* ./customiso/
cp ./customiso/arch/x86_64/root-image.fs.sfs ./
unsquashfs root-image.fs.sfs
rm root-image.fs.sfs
sudo mkdir /mnt/rootfs
sudo mount ./squashfs-root/root-image.fs /mnt/rootfs
sudo cp $GIT_FOLDER/Scripts/python/archinstaller/*.py /mnt/rootfs/root/
sudo cp $GIT_FOLDER/Scripts/python/archinstaller/*.sh /mnt/rootfs/etc/profile.d/
sudo umount /mnt/rootfs
mksquashfs squashfs-root root-image.fs.sfs
cp root-image.fs.sfs customiso/arch/x86_64/root-image.fs.sfs
genisoimage -l -r -J -V "ARCH_201307" -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 -boot-info-table -c isolinux/boot.cat -o $DESTINATION_DIR/arch-auto-dual.iso ./customiso

sudo umount /mnt/archiso
rm -rf ./customiso
rm -rf ./squashfs-root
rm root-image.fs.sfs

# Done

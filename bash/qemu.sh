 # Windows 10:
 qemu-img create -f qcow2 win10.img 25G
 qemu-system-x86_64 --enable-kvm -hda win10.img -net nic -net user,smb=/tmp/shared/ -vga std -m 8196 -cdrom Downloads/Win10_1709_English_x64.iso -cpu host,hv_relaxed,hv_spinlocks=0x1fff,hv_vapic,hv_time -smp 2

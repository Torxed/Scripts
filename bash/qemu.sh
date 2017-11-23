 # Windows 10:
 qemu-system-x86_64 --enable-kvm -net nic -net user,smb=/tmp/shared/ -vga std -m 8196 -cdrom Downloads/Win10_1709_English_x64.iso -cpu host,hv_relaxed,hv_spinlocks=0x1fff,hv_vapic,hv_time -smp 2

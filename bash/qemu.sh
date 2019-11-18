#!/bin/bash

#sudo mkdir -p /mnt/archiso
#sudo mount -o loop,ro /home/torxed/Downloads/archlinux_guided-12.10.2018.iso /mnt/archiso/

MAC='00:11:22:33:44:55'
TAP='tap1'
BRIDGE='br0'
INTERNET='ens4u2'
CD=''
IMAGE="$1"

REDIRECT=$(sysctl -a 2>/dev/null | grep 'net.ipv4.ip_forward = 1')
if [[ -z $REDIRECT ]]; then
	sudo sysctl net.ipv4.ip_forward=1
	sudo iptables -t nat -A POSTROUTING -o ${BRIDGE} -j MASQUERADE
	sudo iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
	sudo iptables -A FORWARD -i ${TAP} -o ${BRIDGE} -j ACCEPT
	sudo iptables -A FORWARD -i ${BRIDGE} -o ${BRIDGE} -j ACCEPT
fi

if [[ -n $2 ]]; then
	CD="-drive file=$2,media=cdrom,bus=0,index=0"
	CD="-drive id=cdrom0,if=none,format=raw,readonly=on,file=$2"
	CD+=" -device virtio-scsi-pci,id=scsi0"
	CD+=" -device scsi-cd,bus=scsi0.0,drive=cdrom0,bootindex=1"
fi

if [[ -z $(ip addr | grep ${BRIDGE}) ]]; then
	sudo brctl addbr ${BRIDGE}
	sudo brctl addif ${BRIDGE} ${INTERNET}
	sudo ip link set dev ${BRIDGE} up
	sudp ip addr flush ${INTERNET}
	#sudo ip addr add 192.168.0.1/24 dev ${BRIDGE}
	sudo dhclient -v ${BRIDGE}
fi

if [[ -z $(ip addr | grep ${TAP}) ]]; then
	sudo ip tuntap add dev ${TAP} mode tap user anton group anton
	sudo ip link set dev ${TAP} master ${BRIDGE}
	sudo ip link set dev ${TAP} up
	sudo brctl addif ${BRIDGE} ${TAP}
fi

# Windows 10:
# -cpu host,hv_relaxed,hv_spinlocks=0x1fff,hv_vapic,hv_time -smp 2
# -device e1000,netdev=network0,mac=${MAC} -netdev tap,id=network0,ifname=${TAP},script=no,downscript=no
qemu-system-x86_64 -enable-kvm -machine q35,accel=kvm -device intel-iommu \
	-cpu host \
	-m 4096 \
	${CD} \
	-boot order=d \
	-netdev tap,ifname=${TAP},id=network0,script=no,downscript=no \
	-device ioh3420,bus=pcie.0,id=root.0,slot=1 \
	-device ioh3420,bus=pcie.0,id=root.1,slot=2 \
	-device virtio-net-pci,mac=${MAC},id=net0,netdev=network0,status=on,bus=root.1,bootindex=2 \
	-global i82557b.romfile="efi-eepro100.rompxe" \
	-drive file=${IMAGE},format=qcow2 \
	-drive if=pflash,format=raw,readonly,file=/usr/share/ovmf/x64/OVMF_CODE.fd \
	-drive if=pflash,format=raw,readonly,file=/usr/share/ovmf/x64/OVMF_VARS.fd

#  -netdev tap,ifname=${TAP},id=network0,script=no,downscript=no -device i82559b,netdev=network0,mac=${MAC} \
#  -option-rom /usr/share/qemu/pxe-rtl8139.rom \
ip tuntap delete dev ${TAP} mode tap

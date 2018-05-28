#!/bin/bash

MAC='00:11:22:33:44:55'
TAP='tap0'
CD=''
IMAGE='test_deploy.qcow2'

if [[ -n $1 ]]; then
  $CD="-cdrom $1"
fi

# Windows 10:
# -cpu host,hv_relaxed,hv_spinlocks=0x1fff,hv_vapic,hv_time -smp 2

if [[ -z $(ip addr | grep ${TAP}) ]]; then
  sudo ip tuntap add dev ${TAP} mode tap user torxed group torxed
  sudo ip link set dev ${TAP} master br0
  sudo ip link set dev ${TAP} up
fi

# -device e1000,netdev=network0,mac=${MAC} -netdev tap,id=network0,ifname=${TAP},script=no,downscript=no
qemu-system-x86_64 -enable-kvm -machine q35,accel=kvm -device intel-iommu \
  -cpu host \
  -mem 4096 \
  -netdev tap,ifname=${TAP},id=network0,script=no,downscript=no -device i82559c,netdev=network0,mac=${MAC} \
  ${CD} \
  -drive file=${IMAGE},format=qcow2 \
  -boot order=d \
  -drive if=pflash,format=raw,readonly,file=/usr/share/ovmf/x64/OVMF_CODE.fd \
  -drive if=pflash,format=raw,readonly,file=/usr/share/ovmf/x64/OVMF_VARS.fd

ip tuntap delete dev tap0 mode tap0

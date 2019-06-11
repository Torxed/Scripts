#!/bin/bash

BUILD_DIR="/tmp/archlive_unattended"
FINAL_DESTINATION="/srv/http/default/archiso"
FINAL_NAME="archlinux_guided-$(date +'%d.%m.%Y').iso"

## Clean slate
rm -rf ${BUILD_DIR}/
mkdir -p ${BUILD_DIR}
cp -r /usr/share/archiso/configs/releng/* ${BUILD_DIR}/

cd ${BUILD_DIR}
## == PATCHES ==
##
#* ISSUE: https://bugs.archlinux.org/task/59135
sed -i '/zd1211-firmware/d' packages.x86_64
#* ISSUE: https://bugs.archlinux.org/task/62279
sed -i '/wpa_actiond/d' packages.x86_64
#* ISSUE: https://bugs.archlinux.org/task/59137
sed -i 's/pcmcia//g' mkinitcpio.conf
##
## ^-----------------^
echo -e "git\npython-psutil\nwpa_supplicant" >> packages.x86_64

cat <<EOF >> ./airootfs/root/customize_airootfs.sh
cd /root
git clone https://github.com/Torxed/archinstall.git
chmod +x ~/archinstall/archinstall.py
EOF

mkdir ./airootfs/etc/skel
echo '[[ -z $DISPLAY && $XDG_VTNR -eq 1 ]] && sh -c "~/archinstall/archinstall.py"' >> ./airootfs/etc/skel/.zprofile

rm -v work*; ./build.sh -v

mkdir -p ${FINAL_DESTINATION}
rm ${FINAL_DESTINATION}/archlinux_guided*
mv out/* ${FINAL_DESTINATION}/${FINAL_NAME}

rm -rf ${BUILD_DIR}

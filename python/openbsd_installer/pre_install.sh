#!/bin/sh

## Array:
## - Note that sh lists are different than bash lists.
## - In bash we would do packagaes=("python" "wget" "nano")
packages="python-2.7.3p1 nano wget"

## Cleanup prep-steps:
mkdir installer_tmp
cd installer_tmp

if [ "$1" = "online" ]; then
	export PKG_PATH=ftp://ftp.eu.openbsd.org/pub/OpenBSD/5.3/packages/`machine -a`/
elif [ "$1" == "offline" ]; then
	if [ -f "/python*" ]; then
		echo "Python located..."
	fi
else
	SSH_SERVER="10.0.2.2"
	SSH_USER="root"
	SSH_PATH="/home/doxid/Downloads"

	SCP="scp $SSH_USER@$SSH_SERVER"
	`$SCP:"$SSH_PATH/{*.tgz,*.py}" ./`
fi

for f in "${packages[@]}"; do
	pkg_add $f
done

if [ "$1" = "online" ]; then
	wget -O ../install.py https://raw.github.com/Torxed/Scripts/master/python/openbsd_installer/install.py
fi

ln -sf /usr/local/bin/python2.7 /usr/local/bin/python
ln -sf /usr/local/bin/python2.7-2to3 /usr/local/bin/2to3
ln -sf /usr/local/bin/python2.7-config /usr/local/bin/python-config
ln -sf /usr/local/bin/pydoc2.7 /usr/local/bin/pydoc

## Cleanup post-steps
cd ..
rm -rf installer_tmp

python install.py

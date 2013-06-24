#!/bin/sh
SSH_SERVER="10.0.2.2"
SSH_USER="root"
SSH_PATH="/home/doxid/Downloads"

source="scp $SSH_USER@$SSH_SERVER:$SSH_PATH"
echo Downloading packages...
`$source/*.tgz ./`
echo Installing packages
for f in *.tgz; do
	echo " - Installing $f"
	pkg_add $f
done

ln -sf /usr/local/bin/python2.7 /usr/local/bin/python
ln -sf /usr/local/bin/python2.7-2to3 /usr/local/bin/2to3
ln -sf /usr/local/bin/python2.7-config /usr/local/bin/python-config
ln -sf /usr/local/bin/pydoc2.7 /usr/local/bin/pydoc


python install.py



#export PKG_PATH=ftp://ftp.eu.openbsd.org/pub/OpenBSD/5.3/packages/`machine -a`/

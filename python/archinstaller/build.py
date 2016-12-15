#!/usr/bin/python3
## Description: a python copy of archiso/build.sh from the baseline branch.
import platform
from subprocess import Popen, STDOUT, PIPE
from time import strftime
from os import makedirs, path
from shutil import copy2, copytree

conf = {}
conf['iso_name'] = 'archer'
conf['iso_label'] = 'archer_{}'.format(strftime('%Y%m'))
conf['install_dir'] = 'arch'
conf['arch'] = {'64bit' : 'x86_64', '32bit' : 'i686'}[platform.architecture()[0]]
conf['work_dir'] = 'work'
conf['out_dir'] = 'out'
conf['script_path'] = './'

additional_pkgs = ['wget', 'nano']

def sed(file, d):
	with open(file, 'r+') as source:
		data = source.read()
		source.seek(0)
		source.truncate()
		for key in d:
			data.replace('%{}%'.format(key), d[key])
		source.write(data)

def run(cmd):
	handle = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
	while handle.poll() is None:
		print(handle.stdout.read(1).decode('utf-8'), end='')
	print(handle.stdout.read(1).decode('utf-8'), end='') # Last byte, if there is any.
	handle.stdout.close()
	return handle.poll()

def smart_copy(source, destination, conf={}):
	source, destination = (source.format(**conf), destination.format(**conf))
	base, optional_alt_name = path.split(destination)
	makedirs(base, exist_ok=True)

	if path.isfile(source):
		copy2(source, base+'/'+optional_alt_name)
	else:
		copytree(source, base+'/'+optional_alt_name)

copy_from_to = {}
## Different stages of copy will be used
## category = {from -> to}
copy_from_to['rootfs'] = {'/usr/lib/initcpio/hooks/archiso' : '{work_dir}/airootfs/etc/initcpio/hooks/',
							'/usr/lib/initcpio/install/archiso' : '{work_dir}/airootfs/etc/initcpio/install/',
							'{script_path}/mkinitcpio.conf' : '{work_dir}/airootfs/etc/mkinitcpio-archiso.conf'}

copy_from_to['boot'] = {'{work_dir}/airootfs/boot/archiso.img' : '{work_dir}/iso/{install_dir}/boot/{arch}/',
							'{work_dir}/airootfs/boot/vmlinuz-linux' : '{work_dir}/iso/{install_dir}/boot/{arch}/vmlinuz'}

				# Prepare /${install_dir}/boot/syslinux
copy_from_to['syslinux'] = {'{script_path}/syslinux/syslinux.cfg' : '{work_dir}/iso/{install_dir}/boot/syslinux/syslinux.cfg',
							'{work_dir}/airootfs/usr/lib/syslinux/bios/ldlinux.c32' : '{work_dir}/iso/{install_dir}/boot/syslinux/',
							'{work_dir}/airootfs/usr/lib/syslinux/bios/menu.c32' : '{work_dir}/iso/{install_dir}/boot/syslinux/',
							'{work_dir}/airootfs/usr/lib/syslinux/bios/libutil.c32' : '{work_dir}/iso/{install_dir}/boot/syslinux/'}

				# Prepare /isolinux
copy_from_to['isolinux'] = {'{script_path}/isolinux/isolinux.cfg' : '{work_dir}/iso/isolinux/isolinux.cfg',
							'{work_dir}/airootfs/usr/lib/syslinux/bios/isolinux.bin' : '{work_dir}/iso/isolinux/',
							'{work_dir}/airootfs/usr/lib/syslinux/bios/isohdpfx.bin' : '{work_dir}/iso/isolinux/',
							'{work_dir}/airootfs/usr/lib/syslinux/bios/ldlinux.c32' : '{work_dir}/iso/isolinux/'}
				
# Setup base root-fs
for key, val in copy_from_to['rootfs'].items():
	smart_copy(key, val, conf)

run('mkarchiso -v -w "{work_dir}" -D "{install_dir}" init'.format(**conf))
if len(additional_pkgs):
	run('mkarchiso -v -w "{work_dir}" -D "{install_dir}" -p '+' -p '.join(additional_pkgs)+' install'.format(**conf))

# mkinitcpio
run('mkarchiso -v -w "{work_dir}" -D "{install_dir}" -r \'mkinitcpio -c /etc/mkinitcpio-archiso.conf -k /boot/vmlinuz-linux -g /boot/archiso.img\' run'.format(**conf))

# make boot
for key, val in copy_from_to['boot'].items():
	smart_copy(key, val, conf)

# Prepare /${install_dir}/boot/syslinux
for key, val in copy_from_to['syslinux'].items():
	smart_copy(key, val, conf)
sed('{work_dir}/iso/{install_dir}/boot/syslinux/syslinux.cfg'.format(**conf), conf)

# Prepare /isolinux
for key, val in copy_from_to['isolinux'].items():
	smart_copy(key, val, conf)
sed('{work_dir}/iso/isolinux/isolinux.cfg'.format(**conf), conf)

# Build airootfs filesystem image
run('mkarchiso -v -w "{work_dir}" -D "{install_dir}" prepare'.format(**conf))

# Build ISO
run('mkarchiso -v -w "{work_dir}" -D "{install_dir}" -L "{iso_label}" -o "{out_dir}" iso "{iso_name}-{iso_label}-{arch}.iso"'.format(**conf))

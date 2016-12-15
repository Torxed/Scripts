#!/usr/bin/python3

from glob import glob
from os import makedirs, chdir, remove, getenv, environ
from os.path import isdir, isfile, abspath
from subprocess import Popen, PIPE, STDOUT
from select import epoll, EPOLLIN, EPOLLOUT, EPOLLHUP
from shutil import rmtree, move

def run(cmd, variables=environ.copy()):
	poll = epoll()
	handle = Popen(cmd, env=variables, shell=True, stdout=PIPE, stderr=STDOUT, stdin=PIPE)
	poll.register(handle.stdout.fileno(), EPOLLIN)

	while handle.poll() is None:
		events = poll.poll(1)
		for fileno, event in events:
			print(handle.stdout.read().decode('utf-8'))

	poll.unregister(handle.stdout.fileno())
	handle.stdout.close()
	handle.stdin.close()
	poll.close()

def copy(source, destination, replace=None):
	with open(source, 'r') as src:
		with open(destination, 'w') as dst:
			if replace:
				data = src.read()
				for stxt, dtxt in replace.items():
					data = data.replace(stxt, dtxt)
				dst.write(data)
			else:
				for line in src:
					dst.write(line)

AUR = 'https://aur.archlinux.org/cgit/aur.git/snapshot/'
DST = '/home/torxed/customrepo/i686/'
ARCH = 'i686'
USER = getenv('SUDO_USER')
if USER == '':
	USER = getenv('USER')
#USER = 'root'
#env = environ.copy()
#env['SUDO_UID'] = USER
#env['builduser_uid'] = USER

print('Running as:',USER)

if isdir('/opt/aur'):
	rmtree('/opt/aur')
run('pacman --noconfirm -S devtools')
makedirs('/opt/arch32', exist_ok=True)
makedirs('/opt/aur', exist_ok=True)
copy('/etc/pacman.conf', '/opt/arch32/pacman.conf', {'Architecture = auto' : 'Architecture = ' + ARCH})
copy('/etc/makepkg.conf', '/opt/arch32/makepkg.conf', {'x86_64' : ARCH})
print('Creating chroot, this will take some time...')
run('mkarchroot -C /opt/arch32/pacman.conf -M /opt/arch32/makepkg.conf /opt/aur/'+USER+' base base-devel')

#with open('/opt/aur/'+USER+'/root/.bashrc', 'w') as fh:
#	fh.write('alias makepkg="makepkg --skippgpcheck"\n')

print('[WARNING] Adding cower workaround in chroot environ')
run('arch-chroot /opt/aur/'+USER+ ' rm -rf /root/'+USER+'/.gnupg')
run('arch-chroot /opt/aur/'+USER+ ' gpg --recv-key 1EB2638FF56C0C53') # Fix for cower shitty pgp signature
print('[WARNING] Adding cower workaround in live environ')
run('gpg --recv-key 1EB2638FF56C0C53')				 # Might just need this.. who cares.. shitty cower..

install = []
if isfile('packages.install'):
	with open('packages.install', 'r')as fh:
		for line in fh:
			install.append(line.strip())

with open('packages.aur', 'r') as aur_list:
	for package in aur_list:
		package = package.strip()
		chdir('/tmp')
		print('Downloading package:',AUR+package+'.tar.gz')
		run('rm -rf ' + package + '*')
		run('wget ' + AUR + package + '.tar.gz')
		run('tar xvf ' + package + '*')
		run('chmod 777 ' + package)
		chdir(package)
		print('Building package...')
		run('makechrootpkg -r /opt/aur/')
#		for fname in glob('./*.xz'):
#			if isfile(DST + fname):
#				remove(DST + fname)
#			move(fname, DST)
#			if package in install:
#				print('Creating symlink into chroot:', abspath(DST+fname) + ' /opt/aur/'+USER+'/tmp/')
#				run('cp ' + abspath(DST + fname) + ' /opt/aur/'+USER+'/tmp/')
#				run('arch-chroot /opt/aur/'+USER+' pacman -U ' + abspath('/tmp/' + fname))
#		chdir('../')

#with open('packages.aur', 'r') as fh:


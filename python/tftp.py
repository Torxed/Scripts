import struct, time
from os.path import isfile, abspath, getsize
from socket import *
from select import epoll, EPOLLIN

__TFTProot__ = './pxe_files/'

	## -- Trying to boot windows as natively as possible:
	#
	# create bootx64.efi:
	# grub-mkstandalone -d /usr/lib/grub/x86_64-efi/ -O x86_64-efi --fonts="unicode" -o bootx64.efi boot/grub/grub.cfg
	#
	# x32 --- :
	# cd /srv/tftp/pxe_grub/
	# cp /usr/lib/grub/i386-pc/kernel.img boot/grub/
	# cp /usr/lib/grub/i386-pc/lzma_decompress.img boot/grub/
	# cp /usr/lib/grub/i386-pc/diskboot.img boot/grub/
	# Ish minimal for linux:
	# grub-mkstandalone -d boot/grub/ -O i386-pc-pxe --fonts="unicode" -o grub.pxe boot/grub/grub.cfg  --modules="ntfs msdospart gfxmenu vga net tftp gzio part_gpt memdisk lspci pxe linux"
	#
	# Generate Windows ISO from iso-extracted-folder:
	# cp grub.exe windows/
	# genisoimage -sysid "" -A "" -V "Windows" -d -N -b boot/etfsboot.com -no-emul-boot -c boot/boot.cat -hide etfsboot.com -hide -boot.cat -o windows_pe.iso windows
	# genisoimage -r -V "Windows" -cache-inodes -J -l -b boot/bootfix.bin -c bootmgr -no-emul-boot -boot-load-size 4 -boot-info-table -o windows.iso windows/
    #
	# Stuff iv'e tried
	# grub-mkimage -d . --format=i386-pc -d boot/grub/ --output=core.img --prefix="(pxe)/boot/grub" pxe pxechain
	# cp /usr/lib/grub/i386-pc/pxeboot.img ./
	# cat pxeboot.img core.img > grub2pxe
	# 
	# grub-mkimage --format=i386-pc-pxe -d /usr/lib/grub/i386-pc/ --output=grub.pxe --prefix='(pxe)/boot/grub' pxe pxechain

class tftp():
	def __init__(self, root, interface=None):
		if not interface: interface = 'br0'
		if not root: root = __TFTProot__
		self.sock = socket(AF_INET, SOCK_DGRAM) # UDP

		## https://www.freepascal.org/docs-html/current/rtl/sockets/index-2.html
		self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
		self.sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
		## Not sure we need this:
		self.sock.setsockopt(SOL_SOCKET, 25, bytes(interface, 'UTF-8')+b'\0') ## http://fxr.watson.org/fxr/source/net/wanrouter/af_wanpipe.c?v=linux-2.6
		self.sock.bind(('172.16.0.1', 69))
		self.main_so_id = self.sock.fileno()

		self.pollobj = epoll()
		self.pollobj.register(self.main_so_id, EPOLLIN)

		self.active_file = None
		self.block_size = None
		self.root = root

	def poll(self, timeout=0.001, fileno=None):
		d = dict(self.pollobj.poll(timeout))
		if fileno: return d[fileno] if fileno in d else None
		return d

	def close(self):
		self.pollobj.unregister(self.main_so_id)
		self.sock.close()

	def parse(self):
		if self.poll():
			data, addr = self.sock.recvfrom(8192)
			print(addr, data)

			msg_type = struct.unpack('>H', data[:2])

			if msg_type[0] == 1: # READ request
				file, data = data[2:].split(b'\x00',1)
				file = file.decode('utf-8')
				abspath_pxefile = abspath(self.root+'/'+file)
				print('TFTP:', abspath(abspath_pxefile))
				if isfile(abspath_pxefile):
					self.active_file = abspath_pxefile

					data = data.split(b'\x00')
					conf = {}
					conf[b'tsize'] = bytes(str(getsize(abspath_pxefile)), 'UTF-8')
					if b'blksize' in data:
						conf[b'blksize'] = data[data.index(b'blksize')+1]
					else:
						conf[b'blksize'] = b'1408'
						#print('Defaulting blocksize to 1408 because:', data)
					self.block_size = int(conf[b'blksize'])

					resp = b'\x00\x06'
					if b'tsize' in data and b'tsize' in conf:
						resp += b'tsize\x00'+conf[b'tsize']+b'\x00'
					if b'blksize' in conf:
						resp += b'blksize\x00'+conf[b'blksize']+b'\x00'

					#print('>>', addr, [resp])
					print('TFTP:',self.active_file,'[ACK]', conf[b'tsize'])
					self.sock.sendto(resp, (addr[0], addr[1]))
				else:
					print('** File missing:', abspath_pxefile)
					self.sock.sendto(b'\x00\x05\x00\x01File not found', (addr[0], addr[1]))

			elif msg_type[0] == 4: # ACK on the file
				block = struct.unpack('>H', data[2:4])[0]
				#print('Trying to retrieve block', block+1, 'of', self.active_file)
				with open(self.active_file, 'rb') as fh:
					fh.seek(block*self.block_size)
					data = fh.read(self.block_size)
					if len(data) <= 0:
						resp = b'\x00\x03'+struct.pack('>H', block+1)
						self.sock.sendto(resp, (addr[0], addr[1]))
						print('TFTP:',self.active_file,'[DONE]')
						return

					resp = b'\x00\x03'+struct.pack('>H', block+1)+data
					self.sock.sendto(resp, (addr[0], addr[1]))

if __name__ == '__main__':
	t = tftp(__TFTProot__)
	while 1:
		if t.poll():
			t.parse()

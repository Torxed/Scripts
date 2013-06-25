#!/usr/local/bin/python
import sys, zlib
from time import sleep
from subprocess import Popen, PIPE, STDOUT

def clean(s):
	s = s.replace('	', ' ').strip()
	last = ''
	cleaned = ''
	for c in s:
		if c == ' ' and last == ' ': continue
		cleaned += c
		last = c
	return cleaned

def humanify(s):
	size = int(s)
	if float(size) <= 1024.0: return float(size), 'B'
	human = ['MB', 'GB', 'TB']
	for i in range(0, len(human)-1):
		size = size/1024.0
		if size < 1024.0:
			break
	return str(size)[:str(size).find('.')+3], human[i]

class e():
	def __init__(self, c=None):
		self.c = c
		self.stdout = None
		self.stderr = None
		self.stdin = None
		self.handle = None
		if c:
			self.e()

	def finish(self, output=False):
		while self.poll() == None:
			if output:
				print self.stdout.readline()
			sleep(0.25)
		self.close()
	def e(self, c=None):
		if not c:
			c = self.c
		self.handle = Popen(c, shell=True, stdout=PIPE, stderr=STDOUT, stdin=PIPE)
		self.stdout = self.handle.stdout
		self.stderr = self.handle.stderr
		self.stdin = self.handle.stdin
	def input(self, what):
		for c in what:
			#sys.stdout.write('*')
			try:
				sys.stdin.write(c)
			except:
				self.handle.stdin.write(c)
			#sys.stdout.flush()
			sleep(0.05)
		try:
			self.handle.stdin.flush()
		except:
			pass
	def close(self):
		try:
			self.stdout.close()
		except:
			pass
		try:
			self.stderr.close()
		except:
			pass
		try:
			self.stdin.close()
		except:
			pass
	def poll(self):
		return self.handle.poll()


x = e('egrep \'ad[0-9] |cd[0-0] |sd[0-9] |wd[0-9] \' /var/run/dmesg.boot')
drives = {}
for line in x.stdout.readlines():
	disk, desc = line.split(' ',1)
	if '<' in desc:
		start = desc.find('<')
		end = desc.find('>', start)
		desc = desc[start+1:end]
	else:
		desc = 'Unknown'
	drives[disk] = {'title' : desc, 'parts' : [], 'physical' : None}
x.close()


for drive in drives.keys():
	x = e('disklabel ' + drive)
	driveinfo = x.stdout.readlines()

	physical_drive = driveinfo[0][2:].strip().replace(':','')
	drives[drive]['physical'] = physical_drive

	partitioning = False
	for line in driveinfo[1:]:
		if len(line) == 0: continue
		if 'partitions:' in line:
			partitioning = True
		if partitioning and line[3] == ':':
			letter, size, offset, fstype = clean(line).split(' ',3)
			if ' ' in fstype:
				fstype = fstype.split(' ', 1)[0]
			drives[drive]['parts'].append((letter[:-1], size, fstype))

raidvolumes = []
total_raid_size = 0
for drive in drives:
	for part in drives[drive]['parts']:
		## Todo:
		## reason for isalpha() is to exlude existing softraid crypto vaolumes.
		## they will show up as sd0 or sd1 without any partition number and for
		## some reason they show up here.
		if 'raid' in part[2].lower() and part[0][-1].isalpha():
			raidvolumes.append(drive + part[0])
			total_raid_size += int(part[1])

print ' | Following raidvolumes will be engaged:'
print ' | ' + ','.join(raidvolumes)
print ' | Total size for raidvolume: ' + ''.join(humanify(total_raid_size))

sys.stdout.write(' |-- You have two seconds to abort ..')
sys.stdout.flush()
sleep(1)
sys.stdout.write('\b')
sys.stdout.flush()
sleep(1)
sys.stdout.write('\b')
sys.stdout.flush()
sleep(1)
sys.stdout.write('\n')
sys.stdout.flush()

print ' |'
print ' | Zeroing on the raidvolume:'
fuse_string = ''
for raidvolume in raidvolumes:
	print ' | - /dev/r' + raidvolume
	e('dd if=/dev/zero of=/dev/r' + raidvolume + ' bs=1m count=1').finish()
	fuse_string += '/dev/' + raidvolume + ','
#x.finish()
#x = e('dd if=/dev/zero of=/dev/rwd0d bs=1m count=1')
#x.finish()

print ' | Fusing raidvolumes into one entity'
x = e('bioctl -c 1 -l ' + fuse_string[:-1] + ' softraid0')
unenc_attached_as = None
while x.poll() == None:
	tmp = x.stdout.readline()
	if 'softraid0' in tmp:
		unenc_attached_as = tmp.replace('\n','').strip().split(' ')[-1]
print ' | Unencrypted RAID attached as ' + str(unenc_attached_as)
x.finish()

print ' | Partitioning the fused entity...'
x = e('disklabel -E ' + unenc_attached_as)
x.input('a a\n\n\nRAID\nw\nq\n')
x.finish()

##### DONT dd if=/dev/zero of=/dev/sd0a bs=1m count=1

print ' | Encrypting the entire entity into a new entity'
print ' !'
print ' ! When asked for a password, remember it!'
print ' ! Because there are NO restore functions for disk-enc passwds.'
print ' !'
sleep(1.5)
x = e('bioctl -c C -l /dev/' + unenc_attached_as + 'a softraid0')
enc_attached_as = None
while x.poll() == None:
	tmp = x.stdout.readline()
	if 'softraid0' in tmp:
		enc_attached_as = tmp.replace('\n','').strip().split(' ')[-1]
print ' | Encrypted RAID attached as ' + str([enc_attached_as])
x.finish()

print ' | Paritioning inside the encrypted volume'
x = e('disklabel -E ' + enc_attached_as)
x.input('a a\n\n\n\nw\nq\n')
x.finish()

print ' | Generating filesystem'
x = e('newfs ' + enc_attached_as + 'a')
x.finish()

print ' | Extracting helper scripts:'

print ' | * nuke.py -> /usr/bin/nuke.py'
# wget alternative:
# e('wget -O /usr/bin/nuke.py https://raw.github.com/Torxed/Scripts/master/python/openbsd_installer/nuke.py')
with open('/usr/bin/nuke.py', 'wb') as fh:
	fh.write(zlib.decompress('x\x9c\x95SMo\xdb0\x0c=G\xbf\x82\xc50\xd8n\x9d\xc4N\x83\xf5\x03\xf0eX1\xf4\xb2\x05[vY\xd7\x83?\xe8\x84\x88,\x19\x92\xbc&\xc1~\xfcd\xd91Z$\xe8\xba\x83a>\x91||\xa6\x9f\xde\x9dM\x1b\xad\xa6\\\xe6)\x9ff$\xa6\xf5\xce\xac\xa5`T\xd5R\x19\xd0;\xcdJ%+\xd0MV+\x99\xa3\xd6\xd0\xa7\x16\xb2F\x11\xc2\xe2~q\x17\xc2\xf7\xe5\xa7\xaf?\x96]\xa9JEa_}Y\x8b\xec\xb3\xc2.i\xa8\xc2CJs\xc4\x9a1\x83J\xa5\xd9\xce $\x10GW\x97W\xf3\xf8z6g\xac\xc0\x12\xd0\x7fZ\xa7&\xb8e\xa3\xad\xcd\xba\x91\xee$\x04\xbdF\xce\x93\xa5j\xd0\xc6\xa6\x90\x8dI:)\x16X\xc2\xa4S\xe4 \t\x97\n\xd8\xe8iM\x1ca;\xa9%\xe7\x90$\xf0E\n\xb4\xdc#\xa7\xc4\x8f&Ql\x8b\xb6\x93\x8eo\x92s\xa9\xd1?\x9c\x90\x18\x0eX\xadH\x18\xf0\xe0\x0f\xdc\xa9T\x93X\xc1\x06w\x1a\xdc\x17VXI\xb5\xf3\x18\xfa^F27\x1c\xc6\x05\xe8"\xf6\x82gm?Q\xc9\xb6\xad$\xa5\rdv\xfd\x1b\xedZ\x8a\x02\xa8L\xa6\x05\xfe\x9e\xeem\r\xc8\x1e(]D9d:\x99G7\x1f \x97\x8d0I\x1c\xcd\xe6/X\xbf\xb9\xcd\xef\xffE\xdc\xff\xa07P\x9fP\\QQ\xdb\xc0\xfc\xb7Z\x17j\xc4Mr\x1d\xdf\xccN\xe8\xa6\xfdk\xfco\x10}4\xe1\xd9\x88{A\x86R\xde\xcd\xe0\xa96c\x85\xba5\xa1h6hY!\x85\xd9\xe7\x8fg\x1e\xb3\x8e?\xfc\xff\'E\xc6\x8ah\xbb\xadGSCR\xdc\x02X^\xb2^\x8c\x18\x8a\x15\x89\xd6\xb4\x0f\xde\xb0\x01/\x84\x0e4\x9d\xde\x01\xf7\xf0\x91u\x16\x8c\xad\xeb\x8e\'\xfd\xca\xbcsn\x1d\xae\x8d\xf2)\x08\xac\xf3\x08.\xec\xa58Q\xdb\x97\xbc\xc8\x94\xbc\xd1\xeb\xd6\xaf\xc3\xe6<\xb8\x80N\xe6\x03\xbdo\x99;\x10\x8c\xe3G\x9b\xf1^\xddf\xdb\xdbN\x19.\xb0\xdf\x9a"\x04\xbb\xdb\xcb\x10\xda8\x08\x1c\x89\xdb\xf8qu\x14\xc2p\xb3\xcf\xe3CG0)I\x90\x93\xf9\x17\x18\xbela'))
e('chmod +x /usr/bin/nuke.py').finish()

print ' | * decrypt.sh -> /usr/bin/decrypt.sh'
with open('/usr/bin/decrypt.sh', 'wb') as fh:
	fh.write('bioctl -c C -l /dev/' + unenc_attached_as + 'a softraid0\n')
e('chmod +x /usr/bin/decrypt.sh').finish()

print ' | * reencrypt.sh -> /usr/bin/reencrypt.sh'
with open('/usr/bin/reencrypt.sh', 'wb') as fh:
	fh.write('bioctl -d ' + enc_attached_as +\n')
e('chmod +x /usr/bin/reencrypt.sh').finish()

print ' - Done'
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

	def finish(self):
		while self.poll() == None:
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
		if 'raid' in part[2].lower():
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
for drive in drives:
	for part in drives[drive]['parts']:
		print ' |\t/dev/r'+drive+part[0]
x = e('dd if=/dev/zero of=/dev/rwd0b bs=1m count=1')
x.finish()
x = e('dd if=/dev/zero of=/dev/rwd0d bs=1m count=1')
x.finish()

print ' | Fusing raidvolumes into one entity'
x = e('bioctl -c 1 -l /dev/wd0b,/dev/wd0d softraid0')
x.finish()

print ' | Partitioning the fused entity...'
x = e('disklabel -E sd0')
x.input('a a\n\n\nRAID\nw\nq\n')
x.finish()

##### DONT dd if=/dev/zero of=/dev/sd0a bs=1m count=1

print ' | Encrypting the entire entity into a new entity'
print ' !'
print ' ! When asked for a password, remember it!'
print ' ! Because there are NO restore functions for disk-enc passwds.'
print ' !'
sleep(1.5)
x = e('bioctl -c C -l /dev/sd0a softraid0')
x.finish()

print ' | Paritioning inside the encrypted volume'
x = e('disklabel -E sd1')
x.input('a a\n\n\n\nw\nq\n')
x.finish()

print ' | Generating filesystem'
x = e('newfs sd1a')
x.finish()

print ' | Extracting helper scripts:'

print ' | * nuke.py -> /usr/bin/nuke.py'
with open('/usr/bin/nuke.py', 'wb') as fh:
	zlib.decompress('x\xda\x95SMo\xdb0\x0c=G\xbf\x82\xc50\xd8^\x9d\xd8\xee\x8aa)\xa0\xdbz\xe8e+\xb6\xec\xb2\xae\x07\x7f0\r\x11Y2$y\xf9\xc0~\xfc$\xcb\t\xda5\xe8:_\xcc\'\x92\xefQ\xf4\xf3\x9b\xb3\xac7:\x13\xaa.EV\x91\xcc\xba\x9d])\xc9\xa8\xed\x94\xb6`v\x86-\xb5j\xc1\xf4U\xa7U\x8d\xc6\xc0\x98\xbaU\x1d\xca\x14non\xafS\xf8\xb6\xf8\xf4\xe5\xfb"\x94\xeaR6\xee5\x96yD\xd2\x86\x94\xa5\x16\x0f\t#\x10;\xc6\x1a\\\x02\xc6\x9bUi\x93+6\xd9\x02\x0f\xc4\xc3I\nf\x85B\xf0\x85\xee\xd1\xc5\xb6Q\xbd\xe5A\xd0\x01\xd4\x9a\x07\xdd\x01\x92\x1cR\t\x9blV$\x10\xb6\xb3N\t\x01\x9c\xc3g%\xd1qO\x06\xc58\x9f\xe5\x85+\xda\xce\x02\xdf\xac\x16\xca`|8!y<`\x9dv\x83C\x04\xbf\xe1Z\x97\x86\xe4\x03\xacqg`\xb8I\x8b\xad\xd2\xbb\x88a\x1cU\xa4j+`\xda\x80i\x8a(y\xd4\xf6\x03\xb5\xf2mK\xd2\xc6B\xe5\x96\xbc6CK\xd3\x00-y\xd6\xe0\xafl\xefj@\x8d@\x9b&\xaf\xa12\xfc2\x9f\x7f\x80Z\xf5\xd2\xf2"\xbf\xb8|\xc2\xfau\xd8\xef\xfe_\xc4\xe3gx\x05\xf5\x89\x89[j:\x17\xd8\xff\x9ev\x08\r\xe2\x9a\x7f,\xe6\x17\'\xe6\xa6\xfdK\xfc\xaf\x18\xfa\x99\xc2#\x89\x1bI\x96J\x114Di\xecT\xa3\xf1f\x93\xfd\x1a\xcf"\xe6\xec|\xf8\xec\x1bM\xd6i\xfb&\x8b\xba\xb4\xa4\xe4\x15\x80\xa3#g\xc1\x9c\xa1| \x89.\xbc\x8b\x8e\x17\x8fR\x08\xa0\x0fc\x1e\xf1\x08\xefYp^\xe1\xcc\xf6\\\xe9g\x15\xbd\x13\xce\xd8\xc6\xea\x98\x92\xc4\x19\x8e\xe0\x9cCq\xa2v,y\x92Y\x8a\xde\xac\xbcM\x8f\x0b\x8b\xe0\x1c\xc2\x98w\xf4\xd63\x07\x90L\x8b{\x97\x89^\\\xa2\xef\xf5*\xe3\xdf\x19{\'\xa4\xe0\x16\xfa>\x05\x1f\'\xc9@1\xac\xf9\xef\xda<\x85y\xee\x1e\x7f\x87?\xd1\x1bZ\x1b')
e('chmod +x /usr/bin/nuke.py').finish()

print ' | * decrypt.sh -> /usr/bin/decrypt.sh'
with open('/usr/bin/decrypt.sh', 'wb') as fh:
	fh.write('bioctl -c C -l /dev/sd0 softraid0\n')
e('chmod +x /usr/bin/decrypt.sh').finish()

print ' | * encrypt.sh -> /usr/bin/encrypt.sh'
with open('/usr/bin/encrypt.sh', 'wb') as fh:
	fh.write('bioctl -d sd1\n')
e('chmod +x /usr/bin/encrypt.sh').finish()

print ' - Done'
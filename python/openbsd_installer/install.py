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

try:
	sys.stdout.write(' |-- You have two seconds to abort ..')
	sys.stdout.flush()
	sleep(1)
	sys.stdout.write('\b ')
	sys.stdout.flush()
	sleep(1)
	sys.stdout.write('\b ')
	sys.stdout.flush()
	sleep(1)
	sys.stdout.write(' \n')
	sys.stdout.flush()
except:
	print ' | Since you aborted the engage,'
	raidvolumes = raw_input('Enter disks to use: (wd0,wd1..): ').split(',')

print ' |'
print ' | Zeroing on the raidvolume (5 sec to abort for each drive):'
fuse_string = ''
for raidvolume in raidvolumes:
	print ' | - /dev/r' + raidvolume
	sleep(5)
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
	fh.write(zlib.decompress('x\xda\x95SMo\xdb0\x0c=G\xbf\x82\xc50\xd8n\x9d\xd8N\x83\xf5\x03\xf0eX1\xf4\xb2\x05[vY\xd7\x83?\x98D\x88,\x19\x92\xbc&\xc1~\xfch\xcb1Z$\xe8\xba\x83a>\x91||\xa6\x9f\xde\x9dE\x8d\xd1\x91PE&\xa2\x9c\xcb\xa8\xde\xd9\xb5\x92\x8cW\xb5\xd2\x16\xcc\xce\xb0\xa5V\x15\x98&\xaf\xb5*\xd0\x18\xe8SsU\xa3\x0ca~?\xbf\x0b\xe1\xfb\xe2\xd3\xd7\x1f\x0bW\xaa3Y\xd2\xab/k\x11=+tI\xcb+<\xa4\x8c@\xac\x19\xb3\xa8u\x96\xef,B\nI|uy5K\xae\xa73\xc6J\\\x02\xfaO\xeb\xcc\x06\xb7l\xb4\xa5l7\xb2;\t\xc1\xacQ\x88t\xa1\x1b\xa4\xd8\x96\xaa\xb1\xa9\x93B\x80\x08S\xa7\xa8\x83\\v\xa9\x80\x8d\x9e\xd6\\ l\'\xb5\x12\x02\xd2\x14\xbe(\x89\xc4=\xea\x94\xf8\xf1$N\xa8h;q|\x93B(\x83\xfe\xe1\x84\xcb\xe1\x80\xd5\x9aK\x0b\x1e\xfc\x81;\x9d\x19.W\xb0\xc1\x9d\x81\xee\x0b+\xac\x94\xdey\x0c}/\xe7\xaa\xb0\x02\xc6%\x982\xf1\x82gm?Q\xab\xb6m\xc9\xb5\xb1\x90\xd3\xfa7\xa6k)K\xe0\xcb4*\xf1w\xb4\xa7\x1aP=\xd0\xa6\x8c\x0b\xc8M:\x8bo>@\xa1\x1ai\xd3$\x9e\xce^\xb0~\xeb6\xbf\xff\x17q\xff\x83\xde@}Bq\xc5\xcb\x9a\x02\xfb\xdfj\xbb\xd0 n\xd2\xeb\xe4fzB7\xdf\xbf\xc6\xff\x06\xd1G\x13\x9e\x8d\xb8\x97\xdc\xf2L\xb8\x19"3v\xac\xd1\xb4&\x94\xcd\x06\x89\x152\x98~\xfex\xe61r\xfc\xe1\xff?inID\xdbM\x1e\xcd,W\xf2\x16\x80x9y1f(W\\\xb6\xa6}\xf0\x86\rx!8\xd08\xbd\x03\xee\xe1#s\x16L\xc8u\xc7\x93~\xe5\xde\xb9 \x87\x1b\xab}\x1e\x04\xe4<\x0e\x17t)N\xd4\xf6%/2K\xd1\x98u\xeb\xd7as\x1e\\\x80\x93\xf9\xc0\xdf\xb7\xcc\x0e\x04\xe3\xe4\x912\xde\xab\xdbl{\xdb)\xc3\x05\xf6[S\x84@\xbb\xbd\x0c\xa1\x8d\x83\xa0#\xe96~\\\x1d\x870\xdc\xec\xf3\xe4\xd0\x11\xfc\x05\xe88iW'))
e('chmod +x /usr/bin/nuke.py').finish()

print ' | * decrypt.sh -> /usr/bin/decrypt.sh'
with open('/usr/bin/decrypt.sh', 'wb') as fh:
	fh.write('bioctl -c C -l /dev/' + unenc_attached_as + 'a softraid0\n')
e('chmod +x /usr/bin/decrypt.sh').finish()

print ' | * reencrypt.sh -> /usr/bin/reencrypt.sh'
with open('/usr/bin/reencrypt.sh', 'wb') as fh:
	fh.write('bioctl -d ' + enc_attached_as + '\n')
e('chmod +x /usr/bin/reencrypt.sh').finish()

print ' - Done'
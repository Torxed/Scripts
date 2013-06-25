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
	fh.write(zlib.decompress('x\x9c\x95SMo\xdb0\x0c=G\xbf\x82\xc50\xd8n\x9d\xc4N\x83\xf5\x03\xf0eX1\xf4\xb2\x05[vY\xd7\x83?\xe8D\x88,\x19\x92\xbc&\xc1~\xfch\xd91Z$\xe8\xba\x83a=\x91||\xa6\x1f\xdf\x9dM\x1b\xa3\xa7B\xe5\xa9\x98f\\N\xeb\x9d]+\xc9xU+m\xc1\xec\x0c+\xb5\xaa\xc04Y\xadU\x8e\xc6@\x1fZ\xa8\x1ae\x08\x8b\xfb\xc5]\x08\xdf\x97\x9f\xbe\xfeXv\xa9:\x95\x05\xbd\xfa\xb4\x16\xd1\xb3\xc2.hy\x85\x87\x90\x11\x885c\x16\xb5N\xb3\x9dEH \x8e\xae.\xaf\xe6\xf1\xf5l\xceX\x81%\xa0\xff\xb4Nmp\xcbF[\x8a\xba\x96\xee&\x04\xb3F!\x92\xa5n\x90\xce\xb6P\x8dM:)\x04\x880\xe9\x149\xc8\xa5\x0b\x05l\xf4\xb4\xe6\x02a;\xa9\x95\x10\x90$\xf0EI$\xee\x91S\xe2G\x93(\xa6\xa4\xed\xa4\xe3\x9b\xe4B\x19\xf4\x0f7\\\x0e\x17\xac\xd6\\Z\xf0\xe0\x0f\xdc\xe9\xd4p\xb9\x82\r\xee\x0c\xb8/\xac\xb0Rz\xe71\xf4\xbd\x8c\xab\xdc\n\x18\x17`\x8a\xd8\x0b\x9e\x95\xfdD\xad\xda\xb2\x92kc!\xa3\xf1o\x8c+)\n\xe0e2-\xf0\xf7tO9\xa0z\xa0M\x11\xe5\x90\x99d\x1e\xdd|\x80\\5\xd2&q4\x9b\xbf`\xfd\xe6&\xbf\xff\x17q\xff\x83\xde@}Bq\xc5\x8b\x9a\x0e\xf6\xbf\xd5\xba\xa3A\xdc$\xd7\xf1\xcd\xec\x84n\xbe\x7f\x8d\xff\r\xa2\x8f:<kq/\xb9\xe5\xa9\xe8z\x88\xd4\xd8\xb1F\xd3\x9aP6\x1b$VHa\xf6\xf9\xe3\x99\xc7\xc8\xf1\x87\xff\xff\xa4\xb9%\x11m5y4\xb5\\\xc9[\x00\xe2\xe5\xe4\xc5\x88\xa1\\q\xd9\x9a\xf6\xc1\x1b&\xe0\x85\xd0\x81\xa6\xd3;\xe0\x1e>\xb2\xce\x821\xb9\xee\xb8\xd3\xaf\xcc;\x17\xe4pc\xb5\xcf\x83\x80\x9c\xc7\xe1\x82\x96\xe2Dn\x9f\xf2"R\x8a\xc6\xac\x9d_I\xd40=\x0f.\xa0\x93\xfa\xc0\xdf\xb7\xec\x1d\x08\xc6\xf1#E\xbcW\'\xda\xd6\xb6\x9d\x86%\xf6[c\x84@\xf3\xbd\x0c\xa1=\x07\x81#qS?\xce\x8eB\x18\xb6\xfb<>T\xb8\x8d*\xb9\xe4N\xed_\xf0\x8em\xe1'))
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
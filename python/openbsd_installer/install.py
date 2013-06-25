#!/usr/local/bin/python
import sys
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

print ' - Done'
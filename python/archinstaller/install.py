import sys, time, os, getopt
from subprocess import PIPE, Popen, STDOUT
from shutil import copy2 as copy

if os.geteuid() >  0:
	sys.stdout.write(" ![ERROR] Must be root to run this script\n")
	sys.exit(1)

params = {'root' : 100}
opts, args = getopt.getopt(sys.argv[1:],"x",["no-internet"])
for key, val in opts:
	params[key] = val

def output(what, flush=True):
	sys.stdout.write(what)
	if flush:
		sys.stdout.flush()

class output_line():
	def __init__(self, starter=''):
		self.len = 0
		self.line = starter
		if self.line != '':
			output(self.line)

	def add(self, what, flush=True):
		self.line += what
		output(what, flush)

	def beginning(self, what, linebreak=True, flush=True):
		output('\b' * len(self.line), False)
		self.line = what + self.line
		if linebreak:
			self.line += '\n'
		output(self.line)

	def replace(self, what, num=1):
		output('\b' * num, False)
		self.line = self.line[:0-num] + what
		output(what)

class run():
	def __init__(self, cmd):
		self.cmd = cmd
		self.stdout = None
		self.stdin = None
		self.x = None
		self.run()

	def run(self):
		self.x = Popen(self.cmd, shell=True, stdout=PIPE, stderr=STDOUT, stdin=PIPE)
		self.stdout, self.stdin = self.x.stdout, self.x.stdin

	def wait(self, text):
		i = 0
		self.output = output_line(text)
		graphics = ['/', '-', '\\', '|']
		while self.x.poll() == None:
			self.output.replace(graphics[i%len(graphics)-1])
			i += 1
			time.sleep(0.2)

		self.output.replace(' ')
		if self.poll() in (0, '0'):
			self.output.beginning(' [OK] ')
			self.close()
			return True
		else:
			self.output.beginning(' ![Error] ')
			self.close()
			return False

	def write(self, what, enter=True):
		if enter:
			if len(what) <= 0 or not what[-1] == '\n':
				what += '\n'
		self.stdin.write(what)

	def poll(self):
		return self.x.poll()

	def getline(self):
		while True:
			line = self.stdout.readline()
			if len(line) <= 0: break
			yield line

	def getlines(self):
		return self.stdout.readlines()

	def close(self):
		self.stdout.close()
		self.stdin.close()

def checkInternet():
	x = output_line('Checking for a internet connection ')
	internet = run('ping -c 2 www.google.com')
	for line in internet.getline():
		x.add('.')
		if '0% packet loss' in line and not '100% packet loss' in line:
			internet.close()
			x.beginning(' [OK] ')
			del x
			return True
	try:
		internet.close()
	except:
		pass
	x.beginning(' ![ERROR] ')
	del x
	return False

def listHDDs():
	## TODO: Show the device name
	hdds = []
	for root, folders, files in os.walk('/sys/block'):
		for drive in folders:
			if drive[:4] == 'loop': continue
			with open(os.path.abspath(root + '/' + drive + '/removable')) as fh:
				if int(fh.readline().strip()) == 0:
					hdds.append(drive)
	return hdds

def listPartitions(drive):
	parts = []
	for root, folders, files in os.walk(os.path.abspath('/sys/block/' + drive + '/')):
		for partition in folders:
			if not drive in partition: continue
			parts.append(partition[len(drive):])
	return parts

def select(List, text=''):
	index = {}
	output(' | Select one of the following' + text + ':\n', False)
	for i in range(0, len(List)):
		output('   ' + str(i) + ': ' + List[i] + '\n', False)
	output(' | Choice: ')
	choice = sys.stdin.readline()
	if len(choice) <= 0:
		choice = 0
	return List[int(choice)]

output('Assuming:\n', False)
output(' | Bootload: MBR for bootloader\n', False)
output(' | Language: ENG (US) base-language\n', False)
output(' | ' + str(params['root']) + r'% Diskspace for root directory' + '\n')

if '--no-internet' in params:
	internet = checkInternet()
	if not internet:
		x = output_line(' - Restarting DHCP service in 9')
		for i in range(9,0,-1):
			x.replace(str(i))
			time.sleep(1)
		x.add('\n')
		del x
		output(' - Stopping DHCP (if started)\n')
		run('systemctl stop dhcpcd.service')
		time.sleep(1)
		output(' - Starting DHCP again\n')
		run('systemctl start dhcpcd.service')
		output(' - Giving time to get an IP (TODO: Inset run::poll()\n')
		time.sleep(5)
		internet = checkInternet()
		if not internet:
			sys.stdout.write(' ![ERROR] No internet connection on any interface, aborting!\n')
			os._exit(1)

output(' | \n')
HDD_TARGET = select(listHDDs(), ' Hard drives')

output(' |\n | You have selected device `/dev/' + HDD_TARGET + '` for partitioning!\n', False)
output(' |\n | If you would like to abort now, press Ctrl+C!\n', False)
line = output_line(' | You have until.. 8')
for i in range(9,-1,-1):
	line.replace(str(i))
	time.sleep(1)
line.add('\n')
del line

output(' | Partitioning\n')
partitioning = run('fdisk /dev/' + HDD_TARGET)
HDD_PARTITIONS = listPartitions(HDD_TARGET)
for i in range(0, len(HDD_PARTITIONS)):
	partitioning.write('d')
	partitioning.write('') # Enter
partitioning.write('n')
partitioning.write('p')
partitioning.write('') # <- Default partition number
partitioning.write('') # <- Default starting position
if params['root'] == 100:
	partitioning.write('') # <- Default last sector, entire disk
else:
	partitioning.write('+' + str(params['root']) + 'M')
partitioning.write('w')
partitioning.close()

filesystem = run('mkfs.ext4 /dev/' + HDD_TARGET)
filesystem.wait(' Generating filesystem on /dev/'+HDD_TARGET+' |')
x = run('mount /dev/' + HDD_TARGET + ' /mnt')
x.wait(' Mounting /dev/' + HDD_TARGET + ' >> /mnt |')

base_install = run('pacstrap -i /mnt base')
time.sleep(5)
base_install.write('')
time.sleep(5)
base_install.write('y')
if not base_install.wait(' Installing base on /dev/' + HDD_TARGET + ' |'):
	output('Failed to install base!')
	os._exit(1)

output(' | Generating fstab /dev/' + HDD_TARGET + '/etc/fstab\n')
run('genfstab -U -p /mnt >> /mnt/etc/fstab').close()
output(' | Copying inside_install.py to /dev/' + HDD_TARGET + '/root/\n')
copy('inside_install.py', '/mnt/root/')
output(' | \n')
python = run('arch-chroot /mnt pacman -S python2')
time.sleep(5)
python.write('y')
if not python.wait(' Installing Python2 on /dev/' + HDD_TARGET + ' |'):
	output('Failed to install Python!')
	os._exit(1)

## Special Popen without any redirections,
## Any PIPE here will cause the inside installer to loose
## it's ability to redirect output to the console and catch input...
output(' | Running inside installer.\n')
x = Popen('arch-chroot /mnt python2 /root/inside_install.py ' + HDD_TARGET, shell=True)
while x.poll() == None:
	time.sleep(0.1)

output(' |\n | Congratulations.. Your system is now installed. Enjoy //Torxed@GitHub ;D\n')
x = run('umount /mnt')
time.sleep(1)
x.close()
run('reboot').close()
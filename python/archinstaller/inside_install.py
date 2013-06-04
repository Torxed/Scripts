import sys, time, os
from subprocess import PIPE, Popen, STDOUT

if os.geteuid() >  0:
	sys.stdout.write(" ![ERROR] Must be root to run this script\n")
	sys.exit(1)

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
	output(' Select one of the following' + text + ':\n', False)
	for i in range(0, len(List)):
		output(' ' + str(i) + ': ' + List[i] + '\n', False)
	output('Choice: ')
	choice = sys.stdin.readline()
	if len(choice) <= 0:
		choice = 0
	return List[int(choice)]

output(' |\n')
output(' | Welcome root to your your environment, let me prepare it for you!\n |\n')
output(' |--- Assuming:\n', False)
output(' | Bootload: MBR for bootloader\n', False)
output(' | Language: ENG (US) base-language\n', False)
output(' | Keyboard: SWE layout\n',False)
output(' | Timezone: Europe/Stockholm\n')


## We don't really need to check for internet here,
## since the main install.py does this.
"""
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
output('\n')
"""

lang = output_line(' | Writing language configuration')
with open('/etc/locale.gen', 'wb') as fh:
	fh.write('en_US.UTF-8 UTF-8\n')
with open('/etc/locale.conf', 'wb') as fh:
	fh.write('LANG=en_US.UTF-8\n')
with open('/etc/vconsole.conf', 'wb') as fh:
	fh.write('KEYMAP=sv-latin1\n')
	fh.write('FONT=lat1-12\n')
lang.beginning(' [OK] ')

x = run('locale-gen')
x.wait(' Generating language files |')
x.close()

run('ln -s /usr/share/zoneinfo/Europe/Stockholm /etc/localtime').close()
clock = run('hwclock --systohc --utc')
clock.wait(' Setting system clock to UTC (Installing Windows later might get time issues) |')
clock.close()

output(' [<<] Enter a bad-ass hostname for your machine: ')
with open('/etc/hostname', 'wb') as fh:
	fh.write(sys.stdin.readline())

output(' | == Don\'t forget to run: "systemctl start dhcpcd" after reboot!\n')
#dhcp = run('systemctl enable dhcpcd')
#dhcp.wait(' Enabling DHCP |')

passwd = run('passwd')
output(' [<<] Enter your root password (visible for now): ')
passwd.write(sys.stdin.readline())
passwd.close()

pacman = run('pacman -S grub-bios')
time.sleep(5)
pacman.write('y')
pacman.wait(' Installing GRUB binaries |')

grub = run('grub-install --recheck /dev/' + sys.argv[1])
grub.wait(' Installing GRUB to MBR |')
run('cp /usr/share/locale/en\@quot/LC_MESSAGES/grub.mo /boot/grub/locale/en.mo').close()

grubcfg = run('grub-mkconfig -o /boot/grub/grub.cfg')
grubcfg.wait(' Generating GRUB configuration |')
print ' | Done, inside installer handing off'
import os
import shlex
import subprocess
import pathlib
import shutil
import sys
import time
import getpass
import glob
from select import epoll, EPOLLIN, EPOLLHUP
from typing import Union

class RequirementError(BaseException):
	pass

"""
 /* Code borrowed from archinstall:
    https://github.com/archlinux/archinstall/blob/ca52c796a55fd34cc1309f26bab86e15da722182/archinstall/lib/general.py#L153-L409
 */
"""

def locate_binary(name):
	for PATH in os.environ['PATH'].split(':'):
		for root, folders, files in os.walk(PATH):
			for file in files:
				if file == name:
					return os.path.join(root, file)
			break  # Don't recurse

	raise RequirementError(f"Binary {name} does not exist.")

def pid_exists(pid: int):
	try:
		return any(subprocess.check_output(['/usr/bin/ps', '--no-headers', '-o', 'pid', '-p', str(pid)]).strip())
	except subprocess.CalledProcessError:
		return False

class SysCallError(BaseException):
	def __init__(self, message, exit_code=-1):
		super(SysCallError, self).__init__(message)
		self.message = message
		self.exit_code = exit_code

class SysCommandWorker:
	def __init__(self, cmd, callbacks=None, peak_output=False, environment_vars=None, logfile=None, working_directory='./'):
		if not callbacks:
			callbacks = {}
		if not environment_vars:
			environment_vars = {}

		if type(cmd) is str:
			cmd = shlex.split(cmd)

		if cmd[0][0] != '/' and cmd[0][:2] != './':
			# "which" doesn't work as it's a builtin to bash.
			# It used to work, but for whatever reason it doesn't anymore.
			# We there for fall back on manual lookup in os.PATH
			cmd[0] = locate_binary(cmd[0])

		self.cmd = cmd
		self.callbacks = callbacks
		self.peak_output = peak_output
		self.environment_vars = environment_vars
		self.logfile = logfile
		self.working_directory = working_directory

		self.exit_code = None
		self._trace_log = b''
		self._trace_log_pos = 0
		self.poll_object = epoll()
		self.child_fd = None
		self.started = None
		self.ended = None

	def __contains__(self, key: bytes):
		"""
		Contains will also move the current buffert position forward.
		This is to avoid re-checking the same data when looking for output.
		"""
		assert type(key) == bytes

		if (contains := key in self._trace_log[self._trace_log_pos:]):
			self._trace_log_pos += self._trace_log[self._trace_log_pos:].find(key) + len(key)

		return contains

	def __iter__(self, *args, **kwargs):
		for line in self._trace_log[self._trace_log_pos:self._trace_log.rfind(b'\n')].split(b'\n'):
			if line:
				yield line + b'\n'

		self._trace_log_pos = self._trace_log.rfind(b'\n')

	def __repr__(self):
		self.make_sure_we_are_executing()
		return str(self._trace_log)

	def __enter__(self):
		return self

	def __exit__(self, *args):
		# b''.join(sys_command('sync')) # No need to, since the underlying fs() object will call sync.
		# TODO: https://stackoverflow.com/questions/28157929/how-to-safely-handle-an-exception-inside-a-context-manager

		if self.child_fd:
			try:
				os.close(self.child_fd)
			except:
				pass

		if self.peak_output:
			# To make sure any peaked output didn't leave us hanging
			# on the same line we were on.
			sys.stdout.write("\n")
			sys.stdout.flush()

		if len(args) >= 2 and args[1]:
			log(args[1], level=logging.ERROR, fg='red')

		if self.exit_code != 0:
			raise SysCallError(f"{self.cmd} exited with abnormal exit code: {self.exit_code}", self.exit_code)

	def is_alive(self):
		self.poll()

		if self.started and self.ended is None:
			return True

		return False

	def write(self, data: bytes, line_ending=True):
		assert type(data) == bytes  # TODO: Maybe we can support str as well and encode it

		self.make_sure_we_are_executing()

		os.write(self.child_fd, data + (b'\n' if line_ending else b''))

	def make_sure_we_are_executing(self):
		if not self.started:
			return self.execute()

	def tell(self) -> int:
		self.make_sure_we_are_executing()
		return self._trace_log_pos

	def seek(self, pos):
		self.make_sure_we_are_executing()
		# Safety check to ensure 0 < pos < len(tracelog)
		self._trace_log_pos = min(max(0, pos), len(self._trace_log))

	def peak(self, output: Union[str, bytes]) -> bool:
		if self.peak_output:
			if type(output) == bytes:
				try:
					output = output.decode('UTF-8')
				except UnicodeDecodeError:
					return False

			sys.stdout.write(output)
			sys.stdout.flush()
		return True

	def poll(self):
		self.make_sure_we_are_executing()

		got_output = False
		for fileno, event in self.poll_object.poll(0.1):
			try:
				output = os.read(self.child_fd, 8192)
				got_output = True
				self.peak(output)
				self._trace_log += output
			except OSError:
				self.ended = time.time()
				break

		if self.ended or (got_output is False and pid_exists(self.pid) is False):
			self.ended = time.time()
			try:
				self.exit_code = os.waitpid(self.pid, 0)[1]
			except ChildProcessError:
				try:
					self.exit_code = os.waitpid(self.child_fd, 0)[1]
				except ChildProcessError:
					self.exit_code = 1

	def execute(self) -> bool:
		import pty

		if (old_dir := os.getcwd()) != self.working_directory:
			os.chdir(self.working_directory)

		# Note: If for any reason, we get a Python exception between here
		#   and until os.close(), the traceback will get locked inside
		#   stdout of the child_fd object. `os.read(self.child_fd, 8192)` is the
		#   only way to get the traceback without loosing it.
		self.pid, self.child_fd = pty.fork()
		os.chdir(old_dir)

		if not self.pid:
			try:
				os.execve(self.cmd[0], self.cmd, {**os.environ, **self.environment_vars})
				if storage['arguments'].get('debug'):
					log(f"Executing: {self.cmd}", level=logging.DEBUG)
			except FileNotFoundError:
				log(f"{self.cmd[0]} does not exist.", level=logging.ERROR, fg="red")
				self.exit_code = 1
				return False

		self.started = time.time()
		self.poll_object.register(self.child_fd, EPOLLIN | EPOLLHUP)

		return True

	def decode(self, encoding='UTF-8'):
		return self._trace_log.decode(encoding)


class SysCommand:
	def __init__(self, cmd, callback=None, start_callback=None, peak_output=False, environment_vars=None, working_directory='./'):
		_callbacks = {}
		if callback:
			_callbacks['on_end'] = callback
		if start_callback:
			_callbacks['on_start'] = start_callback

		self.cmd = cmd
		self._callbacks = _callbacks
		self.peak_output = peak_output
		self.environment_vars = environment_vars
		self.working_directory = working_directory

		self.session = None
		self.create_session()

	def __enter__(self):
		return self.session

	def __exit__(self, *args, **kwargs):
		# b''.join(sys_command('sync')) # No need to, since the underlying fs() object will call sync.
		# TODO: https://stackoverflow.com/questions/28157929/how-to-safely-handle-an-exception-inside-a-context-manager

		if len(args) >= 2 and args[1]:
			log(args[1], level=logging.ERROR, fg='red')

	def __iter__(self, *args, **kwargs):

		for line in self.session:
			yield line

	def __getitem__(self, key):
		if type(key) is slice:
			start = key.start if key.start else 0
			end = key.stop if key.stop else len(self.session._trace_log)

			return self.session._trace_log[start:end]
		else:
			raise ValueError("SysCommand() doesn't have key & value pairs, only slices, SysCommand('ls')[:10] as an example.")

	def __repr__(self, *args, **kwargs):
		return self.session._trace_log.decode('UTF-8')

	def __json__(self):
		return {
			'cmd': self.cmd,
			'callbacks': self._callbacks,
			'peak': self.peak_output,
			'environment_vars': self.environment_vars,
			'session': True if self.session else False
		}

	def create_session(self):
		if self.session:
			return True

		try:
			self.session = SysCommandWorker(self.cmd, callbacks=self._callbacks, peak_output=self.peak_output, environment_vars=self.environment_vars)

			while self.session.ended is None:
				self.session.poll()

			if self.peak_output:
				sys.stdout.write('\n')
				sys.stdout.flush()

		except SysCallError:
			return False

		return True

	def decode(self, fmt='UTF-8'):
		return self.session._trace_log.decode(fmt)

	@property
	def exit_code(self):
		return self.session.exit_code

	@property
	def trace_log(self):
		return self.session._trace_log

if __name__ == '__main__':
	from argparse import ArgumentParser
	parser = ArgumentParser(description="A set of common parameters for the tooling", add_help=False)
	
	parser.add_argument("--build-dir", nargs="?", help="Path to where archiso will be built", default="~/archiso")
	parser.add_argument("--rebuild", action="store_true", help="To rebuild ISO or not", default=False)
	parser.add_argument("--bios", action="store_true", help="Disables UEFI and uses BIOS support instead", default=False)
	parser.add_argument("--memory", nargs="?", help="Ammount of memory to supply the machine", default=8192)
	parser.add_argument("--boot", nargs="?", help="Selects if hdd or cdrom should be booted first.", default="cdrom")
	parser.add_argument("--new-drives", action="store_true", help="This flag will wipe drives before boot.", default=False)
	parser.add_argument("--harddrives", nargs="?", help="A list of harddrives and size (~/disk.qcow2:40G,~/disk2.qcow2:15G)", default="~/test.qcow2:15G,~/test_large.qcow2:70G")
	parser.add_argument("--bridge", nargs="?", help="What bridge interface should be setup for internet access.", default='br0')
	parser.add_argument("--bridge-mac", nargs="?", help="Force a MAC address on the bridge", default=None) # be:fa:41:b8:ef:ad
	parser.add_argument("--internet", nargs="?", help="What internet interface should be used.", default=None)
	parser.add_argument("--interface-name", nargs="?", help="What TAP interface name should be used.", default='tap0')
	parser.add_argument("--passthrough", nargs="?", help="Any /dev/disk/by-id/ to pass through?.", default='tap0')
	args, unknowns = parser.parse_known_args()

	module_entrypoints = ArgumentParser(parents=[parser], description="A set of archinstall specific parameters", add_help=True)
	module_entrypoints.add_argument("--repo", nargs="?", help="URL for repository", default="https://github.com/Torxed/archinstall.git")
	module_entrypoints.add_argument("--branch", nargs="?", help="Which branch of archinstall to use", default="master")
	module_entrypoints.add_argument("--conf", nargs="?", help="[optional] configure a `archinstall --conf` to autorun with", default=None)
	module_entrypoints.add_argument("--disk-layout", nargs="?", help="[optional] configure a `archinstall --disk-layout` to autorun with", default=None)
	module_entrypoints.add_argument("--creds", nargs="?", help="[optional] configure a `archinstall --creds` to autorun with", default=None)
	module_entrypoints.add_argument("--silent", default=False, action="store_true", help="Sets archinstall to --silent mode skipping any GUI interaction (requires --conf, --creds and --disk-layout).")

	args, unknown = module_entrypoints.parse_known_args(namespace=args)

	sudo_pw = None

	if pathlib.Path('/usr/share/archiso/configs/releng').exists() is False:
		raise RequirementError(f"archiso or '/usr/share/archiso/configs/releng' is missing.")

	if pathlib.Path('/usr/share/ovmf/x64/OVMF_CODE.fd').exists() is False and args.bios is False:
		raise RequirementError(f"archiso cannot boot in UEFI because OVMF is not installed.")

	username = 'anton'
	groupname = 'anton'
	if args.rebuild is not False or args.internet is not None or args.interface_name is not None:
		sudo_pw = getpass.getpass(f"Enter sudo password in order to setup archinstall test environment: ")
	builddir = pathlib.Path(args.build_dir).expanduser()
	harddrives={}
	for drive in args.harddrives.split(','):
		path, size = drive.split(':')
		harddrives[pathlib.Path(path.strip()).expanduser()] = size.strip()

	for hdd, size in harddrives.items():
		if args.new_drives is not False:
			pathlib.Path(hdd).unlink(missing_ok=True)

		if not pathlib.Path(hdd).exists():
			if (handle := SysCommand(f"qemu-img create -f qcow2 {hdd} {size}")).exit_code != 0:
				raise ValueError(f"Could not create harddrive {hdd}: {handle}")

	if args.rebuild is not False:
		if builddir.exists():
			try:
				shutil.rmtree(str(builddir))
			except PermissionError:
				handle = SysCommandWorker(f"sudo rm -rf {builddir}")
				while handle.is_alive():
					if b'password for' in handle:
						handle.write(bytes(sudo_pw, 'UTF-8'))

		shutil.copytree('/usr/share/archiso/configs/releng', str(builddir), symlinks=True, ignore=None)

		if (handle := SysCommand(f"git clone {args.repo} -b {args.branch} {builddir}/airootfs/root/archinstall-git")).exit_code != 0:
			raise SysCallError(f"Could not clone repository: {handle}")

		with open(f"{builddir}/packages.x86_64", "a") as packages:
			packages.write(f"git\n")
			packages.write(f"python\n")
			packages.write(f"python-setuptools\n")

		autorun_string = "[[ -z $DISPLAY && $XDG_VTNR -eq 1 ]] &&"
		autorun_string += ' sh -c "cd /root/archinstall-git;'
		autorun_string += ' git config --global pull.rebase false;'
		autorun_string += ' git pull;'
		autorun_string += ' cp examples/guided.py ./;'
		autorun_string += ' time python guided.py'
		# Append options to archinstall (aka guided.py)
		if args.conf:
			autorun_string += f' --conf {args.conf}'
		if args.disk_layout:
			autorun_string += f' --disk_layout {args.disk_layout}'
		if args.creds:
			autorun_string += f' --creds {args.creds}'
		if args.silent:
			autorun_string += f' --silent'

		autorun_string += '";\n'

		with open(f"{builddir}/airootfs/root/.zprofile", "a") as zprofile:
			zprofile.write(autorun_string)

		handle = SysCommandWorker(f"bash -c '(cd {builddir} && sudo mkarchiso -v -w work/ -o out/ ./)'", working_directory=str(builddir) , peak_output=True)
		pw_prompted = False
		while handle.is_alive():
			if b'password for' in handle and pw_prompted is False:
				handle.write(bytes(sudo_pw, 'UTF-8'))
				pw_prompted = True

		if not handle.exit_code == 0:
			raise SysCallError(f"Could not build ISO: {handle}", handle.exit_code)

	ISO = glob.glob(f"{builddir}/out/*.iso")[0]

	if args.internet is not None:
		# Set IPv4 forward
		with open('/proc/sys/net/ipv4/ip_forward', 'r') as fh:
			ip_forward = int(fh.read().strip())

		if ip_forward == 0:
			handle = SysCommandWorker(f"sudo sysctl net.ipv4.ip_forward=1")
			pw_prompted = False
			while handle.is_alive():
				if b'password for' in handle and pw_prompted is False:
					handle.write(bytes(sudo_pw, 'UTF-8'))
					pw_prompted = True

	if args.bridge is not None:
		# Bridge
		if not glob.glob(f'/sys/class/net/{args.bridge}'):
			handle = SysCommandWorker(f"sudo ip link add name {args.bridge} type bridge")
			pw_prompted = False
			while handle.is_alive():
				if b'password for' in handle and pw_prompted is False:
					handle.write(bytes(sudo_pw, 'UTF-8'))
					pw_prompted = True

			if args.bridge_mac:
				handle = SysCommandWorker(f"sudo ip link set dev {args.bridge} address {args.bridge_mac}")
				pw_prompted = False
				while handle.is_alive():
					if b'password for' in handle and pw_prompted is False:
						handle.write(bytes(sudo_pw, 'UTF-8'))
						pw_prompted = True

			if args.internet:
				handle = SysCommandWorker(f"sudo ip link set dev {args.internet} master {args.bridge}")
				pw_prompted = False
				while handle.is_alive():
					if b'password for' in handle and pw_prompted is False:
						handle.write(bytes(sudo_pw, 'UTF-8'))
						pw_prompted = True

			handle = SysCommandWorker(f"sudo ip link set dev {args.bridge} up")
			pw_prompted = False
			while handle.is_alive():
				if b'password for' in handle and pw_prompted is False:
					handle.write(bytes(sudo_pw, 'UTF-8'))
					pw_prompted = True

	if args.interface_name is not None:
		# Tap interface
		if not glob.glob(f'/sys/class/net/{args.interface_name}'):
			handle = SysCommandWorker(f"sudo ip tuntap add dev {args.interface_name} mode tap user {username} group {groupname}")
			pw_prompted = False
			while handle.is_alive():
				if b'password for' in handle and pw_prompted is False:
					handle.write(bytes(sudo_pw, 'UTF-8'))
					pw_prompted = True

		if args.bridge:
			print(f"sudo ip link set dev {args.interface_name} master {args.bridge}")
			handle = SysCommandWorker(f"sudo ip link set dev {args.interface_name} master {args.bridge}")
			pw_prompted = False
			while handle.is_alive():
				if b'password for' in handle and pw_prompted is False:
					handle.write(bytes(sudo_pw, 'UTF-8'))
					pw_prompted = True

		print(f"sudo ip link set dev {args.interface_name} up")
		handle = SysCommandWorker(f"sudo ip link set dev {args.interface_name} up")
		pw_prompted = False
		while handle.is_alive():
			if b'password for' in handle and pw_prompted is False:
				handle.write(bytes(sudo_pw, 'UTF-8'))
				pw_prompted = True

	if args.bridge:
		# IP on bridge
		handle = SysCommandWorker(f"sudo dhclient -v {args.bridge}")
		pw_prompted = False
		while handle.is_alive():
			if b'password for' in handle and pw_prompted is False:
				handle.write(bytes(sudo_pw, 'UTF-8'))
				pw_prompted = True

		if args.internet:
			if handle.exit_code == 0:
				# Flush IP on internet interface
				handle = SysCommandWorker(f"sudo ip addr flush {args.internet}")
				pw_prompted = False
				while handle.is_alive():
					if b'password for' in handle and pw_prompted is False:
						handle.write(bytes(sudo_pw, 'UTF-8'))
						pw_prompted = True

			iptables = SysCommandWorker(f"bash -c 'sudo iptables-save'")
			pw_prompted = False
			while iptables.is_alive():
				if b'password for' in iptables and pw_prompted is False:
					iptables.write(bytes(sudo_pw, 'UTF-8'))
					pw_prompted = True

			print(f"Adding iptable rules if nessecary")
			if not bytes(f'-A POSTROUTING -o {args.bridge} -j MASQUERADE', 'UTF-8') in iptables:
				handle = SysCommandWorker(f"bash -c 'sudo iptables -t nat -A POSTROUTING -o {args.bridge} -j MASQUERADE'")
				pw_prompted = False
				while handle.is_alive():
					if b'password for' in handle and pw_prompted is False:
						handle.write(bytes(sudo_pw, 'UTF-8'))
						pw_prompted = True
			if not bytes(f'-A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT', 'UTF-8') in iptables:
				handle = SysCommandWorker(f"bash -c 'sudo iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT'")
				pw_prompted = False
				while handle.is_alive():
					if b'password for' in handle and pw_prompted is False:
						handle.write(bytes(sudo_pw, 'UTF-8'))
						pw_prompted = True
			if not bytes(f'-A FORWARD -i {args.interface_name} -o {args.bridge} -j ACCEPT', 'UTF-8') in iptables:
				handle = SysCommandWorker(f"bash -c 'sudo iptables -A FORWARD -i {args.interface_name} -o {args.bridge} -j ACCEPT'")
				pw_prompted = False
				while handle.is_alive():
					if b'password for' in handle and pw_prompted is False:
						handle.write(bytes(sudo_pw, 'UTF-8'))
						pw_prompted = True
			if not bytes(f'-A FORWARD -i {args.bridge} -o {args.bridge} -j ACCEPT', 'UTF-8') in iptables:
				handle = SysCommandWorker(f"bash -c 'sudo iptables -A FORWARD -i {args.bridge} -o {args.bridge} -j ACCEPT'")
				pw_prompted = False
				while handle.is_alive():
					if b'password for' in handle and pw_prompted is False:
						handle.write(bytes(sudo_pw, 'UTF-8'))
						pw_prompted = True
			print("<- Done")

	if args.boot == 'cdrom':
		hdd_boot_priority = 2
		cdrom_boot_priority = 1
	else:
		hdd_boot_priority = 1
		cdrom_boot_priority = len(harddrives)+1

	qemu = 'sudo qemu-system-x86_64'
	qemu += f' -cpu host'
	qemu += f' -enable-kvm'
	qemu += f' -machine q35,accel=kvm'
	qemu += f' -device intel-iommu'
	qemu += f' -m {args.memory}'
	if args.bios is False:
		qemu += f' -drive if=pflash,format=raw,readonly=on,file=/usr/share/ovmf/x64/OVMF_CODE.fd'
		qemu += f' -drive if=pflash,format=raw,readonly=on,file=/usr/share/ovmf/x64/OVMF_VARS.fd'
	for index, hdd in enumerate(harddrives):
		# qemu += f' -device virtio-scsi-pci,bus=pcie.0,id=scsi{index}'
		# qemu += f'  -device scsi-hd,drive=hdd{index},bus=scsi{index}.0,id=scsi{index}.0,bootindex={hdd_boot_priority+index}'
		# qemu += f'   -drive file={hdd},if=none,format=qcow2,discard=unmap,aio=native,cache=none,id=hdd{index}'
		qemu += f' -device virtio-scsi-pci,bus=pcie.0,id=scsi{index},addr=0x{index+8}'
		qemu += f'  -device scsi-hd,drive=libvirt-{index}-format,bus=scsi{index}.0,id=scsi{index}-0-0-0,channel=0,scsi-id=0,lun=0,device_id=drive-scsi0-0-0-0,bootindex={index+2},write-cache=on'
		qemu += f'   -blockdev \'{{"driver":"file","filename":"{hdd}","aio":"threads","node-name":"libvirt-{index}-storage","cache":{{"direct":false,"no-flush":false}},"auto-read-only":true,"discard":"unmap"}}\''
		qemu += f'   -blockdev \'{{"node-name":"libvirt-{index}-format","read-only":false,"discard":"unmap","cache":{{"direct":true,"no-flush":false}},"driver":"qcow2","file":"libvirt-{index}-storage","backing":null}}\''
	qemu += f' -device virtio-scsi-pci,bus=pcie.0,id=scsi{index+1}'
	qemu += f'  -device scsi-cd,drive=cdrom0,bus=scsi{index+1}.0,bootindex={cdrom_boot_priority}'
	qemu += f'   -drive file={ISO},media=cdrom,if=none,format=raw,cache=none,id=cdrom0'
	#qemu += f' -device pcie-root-port,multifunction=on,bus=pcie.0,id=port9-0,addr=0x9,chassis=0'
	qemu += f'  -device virtio-net-pci,mac=FE:00:00:00:00:00,id=network0,netdev=network0.0,status=on,bus=pcie.0'
	qemu += f'   -netdev tap,ifname={args.interface_name},id=network0.0,script=no,downscript=no'

	if args.passthrough:
		qemu += f' --drive format=raw,file={args.passthrough}'

	handle = SysCommandWorker(qemu, peak_output=True)
	while handle.is_alive():
		if b'password for' in handle:
			if not sudo_pw:
				sudo_pw = getpass.getpass(f"Enter sudo password in order to boot the machine: ")
			handle.write(bytes(sudo_pw, 'UTF-8'))
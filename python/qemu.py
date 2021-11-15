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
	parser = ArgumentParser()
	
	parser.add_argument("--repo", nargs="?", help="URL for repository", default="https://github.com/Torxed/archinstall.git")
	parser.add_argument("--branch", action="store_true", help="Which branch of archinstall to use", default="master")
	parser.add_argument("--build-dir", nargs="?", help="Path to where archiso will be built", default="~/archiso")
	parser.add_argument("--rebuild", action="store_true", help="To rebuild ISO or not", default=False)
	parser.add_argument("--bios", nargs="?", help="Disables UEFI and uses BIOS support instead", default=False)
	parser.add_argument("--memory", nargs="?", help="Ammount of memory to supply the machine", default=8192)
	parser.add_argument("--boot", nargs="?", help="Selects if hdd or cdrom should be booted first.", default="cdrom")
	parser.add_argument("--new-drives", nargs="?", help="This flag will wipe drives before boot.", default=False)
	parser.add_argument("--harddrives", nargs="?", help="A list of harddrives and size (~/disk.qcow2:40G,~/disk2.qcow2:15G)", default="~/test.qcow2:15G,~/test_large.qcow2:40G")
	parser.add_argument("--bridge", nargs="?", help="What bridge interface should be setup for internet access.", default='br0')
	parser.add_argument("--internet", nargs="?", help="What internet interface should be used.", default='auto')
	parser.add_argument("--interface-name", nargs="?", help="What TAP interface name should be used.", default='tap0')
	args, unknowns = parser.parse_known_args()

	sudo_pw = None
	builddir = pathlib.Path(args.build_dir).expanduser()
	harddrives={}
	for drive in args.harddrives.split(','):
		path, size = drive.split(':')
		harddrives[pathlib.Path(path.strip()).expanduser()] = size.strip()

	if args.new_drives is not False:
		for hdd, size in harddrives.items():
			pathlib.Path(hdd).unlink(missing_ok=True)

			if (handle := SysCommand(f"qemu-img create -f qcow2 {hdd} {size}")).exit_code != 0:
				raise ValueError(f"Could not create harddrive {hdd}: {handle}")

	if args.rebuild is not False:
		try:
			shutil.rmtree(str(builddir), ignore_errors=True)
		except PermissionError:
			handle = SysCommandWorker(f"sudo rm -rf {builddir}")
			while handle.is_alive():
				if b'password for' in handle:
					if not sudo_pw:
						sudo_pw = getpass.getpass(f"Enter sudo password for this user in order to remove old builddir: ")
					handle.write(bytes(sudo_pw, 'UTF-8'))

		shutil.copytree('/usr/share/archiso/configs/releng', str(builddir), symlinks=True, ignore=None)

		SysCommand(f"git clone {args.repo} -b {args.branch} {builddir}/airootfs/root/archinstall-git")

		with open(f"{builddir}/packages.x86_64", "a") as packages:
			packages.write(f"git\n")
			packages.write(f"python\n")
			packages.write(f"python-setuptools\n")

		with open(f"{builddir}/airootfs/root/.zprofile", "a") as zprofile:
			zprofile.write('[[ -z $DISPLAY && $XDG_VTNR -eq 1 ]] && sh -c "cd /root/archinstall-git; git config --global pull.rebase false; git pull; cp examples/guided.py ./; python guided.py"\n')

		handle = SysCommandWorker(f"bash -c '(cd {builddir} && sudo mkarchiso -v -w work/ -o out/ ./)'", working_directory=str(builddir) , peak_output=True)
		pw_prompted = False
		while handle.is_alive():
			if b'password for' and pw_prompted is False:
				if not sudo_pw:
					sudo_pw = getpass.getpass(f"Enter sudo password for this user in order to build the ISO: ")
				handle.write(bytes(sudo_pw, 'UTF-8'))
				pw_prompted = True

		if not handle.exit_code == 0:
			raise SysCallError(f"Could not build ISO: {handle}", handle.exit_code)

	ISO = glob.glob(f"{builddir}/out/*.iso")[0]

	qemu = 'qemu-system-x86_64'
	qemu += f' -cpu host'
	qemu += f' -enable-kvm'
	qemu += f' -machine q35,accel=kvm'
	qemu += f' -device intel-iommu'
	qemu += f' -m {args.memory}'
	if args.bios is False:
		qemu += f' -drive if=pflash,format=raw,readonly=on,file=/usr/share/ovmf/x64/OVMF_CODE.fd'
		qemu += f' -drive if=pflash,format=raw,readonly=on,file=/usr/share/ovmf/x64/OVMF_VARS.fd'
	for index, hdd in enumerate(harddrives):
		qemu += f' -device virtio-scsi-pci,bus=pcie.0,id=scsi{index}'
		qemu += f'  -device scsi-hd,drive=hdd{index},bus=scsi{index}.0,id=scsi{index}.0,bootindex={2+index}'
		qemu += f'   -drive file={hdd},if=none,format=qcow2,discard=unmap,aio=native,cache=none,id=hdd{index}'
	qemu += f' -device virtio-scsi-pci,bus=pcie.0,id=scsi{index+1}'
	qemu += f'  -device scsi-cd,drive=cdrom0,bus=scsi{index+1}.0,bootindex=1'
	qemu += f'   -drive file={ISO},media=cdrom,if=none,format=raw,cache=none,id=cdrom0'

	handle = SysCommandWorker(qemu, peak_output=True)
	while handle.is_alive():
		time.sleep(0.025)

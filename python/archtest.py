import os
import shlex
import subprocess
import pathlib
import shutil
import sys
import time
import getpass
import glob
import stat
import re
from typing import Callable, Optional, Dict, Any, List, Union, Iterator, TYPE_CHECKING
from select import epoll, EPOLLIN, EPOLLHUP
from typing import Union

storage: Dict[str, Any] = {
	'LOG_PATH': pathlib.Path('./'),
	'LOG_FILE': pathlib.Path('install.log'),
	'CMD_LOCALE':{'LC_ALL':'C'}, # default locale for execution commands. Can be overridden with set_cmd_locale()
	'CMD_LOCALE_DEFAULT':{'LC_ALL':'C'}, # should be the same as the former. Not be used except in reset_cmd_locale()
}

class RequirementError(BaseException):
	pass

"""
 /* Code borrowed from archinstall:
    https://github.com/archlinux/archinstall/blob/ca52c796a55fd34cc1309f26bab86e15da722182/archinstall/lib/general.py#L153-L409
 */
"""

def _pid_exists(pid: int) -> bool:
	try:
		return any(subprocess.check_output(['/usr/bin/ps', '--no-headers', '-o', 'pid', '-p', str(pid)]).strip())
	except subprocess.CalledProcessError:
		return False

def clear_vt100_escape_codes(data :Union[bytes, str]) -> Union[bytes, str]:
	# https://stackoverflow.com/a/43627833/929999
	vt100_escape_regex = r'\x1B\[[?0-9;]*[a-zA-Z]'
	if isinstance(data, bytes):
		return re.sub(vt100_escape_regex.encode(), b'', data)
	return re.sub(vt100_escape_regex, '', data)

def locate_binary(name):
	for PATH in os.environ['PATH'].split(':'):
		for root, folders, files in os.walk(PATH):
			for file in files:
				if file == name:
					return os.path.join(root, file)
			break  # Don't recurse

	raise RequirementError(f"Binary {name} does not exist.")

class SysCallError(BaseException):
	def __init__(self, message :str, exit_code :Optional[int] = None, worker :Optional['SysCommandWorker'] = None) -> None:
		super(SysCallError, self).__init__(message)
		self.message = message
		self.exit_code = exit_code
		self.worker = worker

class SysCommandWorker:
	def __init__(
		self,
		cmd :Union[str, List[str]],
		callbacks :Optional[Dict[str, Any]] = None,
		peek_output :Optional[bool] = False,
		environment_vars :Optional[Dict[str, Any]] = None,
		logfile :Optional[None] = None,
		working_directory :Optional[str] = './',
		remove_vt100_escape_codes_from_lines :bool = True
	):
		callbacks = callbacks or {}
		environment_vars = environment_vars or {}

		if isinstance(cmd, str):
			cmd = shlex.split(cmd)

		if cmd:
			if cmd[0][0] != '/' and cmd[0][:2] != './': # pathlib.Path does not work well
				cmd[0] = locate_binary(cmd[0])

		self.cmd = cmd
		print(self.cmd)
		self.callbacks = callbacks
		self.peek_output = peek_output
		# define the standard locale for command outputs. For now the C ascii one. Can be overridden
		self.environment_vars = {**storage.get('CMD_LOCALE',{}),**environment_vars}
		self.logfile = logfile
		self.working_directory = working_directory

		self.exit_code :Optional[int] = None
		self._trace_log = b''
		self._trace_log_pos = 0
		self.poll_object = epoll()
		self.child_fd :Optional[int] = None
		self.started :Optional[float] = None
		self.ended :Optional[float] = None
		self.remove_vt100_escape_codes_from_lines :bool = remove_vt100_escape_codes_from_lines

	def __contains__(self, key: bytes) -> bool:
		"""
		Contains will also move the current buffert position forward.
		This is to avoid re-checking the same data when looking for output.
		"""
		assert isinstance(key, bytes)

		index = self._trace_log.find(key, self._trace_log_pos)
		if index >= 0:
			self._trace_log_pos += index + len(key)
			return True

		return False

	def __iter__(self, *args :str, **kwargs :Dict[str, Any]) -> Iterator[bytes]:
		last_line = self._trace_log.rfind(b'\n')
		lines = filter(None, self._trace_log[self._trace_log_pos:last_line].splitlines())
		for line in lines:
			if self.remove_vt100_escape_codes_from_lines:
				line = clear_vt100_escape_codes(line)  # type: ignore

			yield line + b'\n'

		self._trace_log_pos = last_line

	def __repr__(self) -> str:
		self.make_sure_we_are_executing()
		return str(self._trace_log)

	def __str__(self) -> str:
		try:
			return self._trace_log.decode('utf-8')
		except UnicodeDecodeError:
			return str(self._trace_log)

	def __enter__(self) -> 'SysCommandWorker':
		return self

	def __exit__(self, *args :str) -> None:
		# b''.join(sys_command('sync')) # No need to, since the underlying fs() object will call sync.
		# TODO: https://stackoverflow.com/questions/28157929/how-to-safely-handle-an-exception-inside-a-context-manager

		if self.child_fd:
			try:
				os.close(self.child_fd)
			except:
				pass

		if self.peek_output:
			# To make sure any peaked output didn't leave us hanging
			# on the same line we were on.
			sys.stdout.write("\n")
			sys.stdout.flush()

		if len(args) >= 2 and args[1]:
			print(args[1])

		if self.exit_code != 0:
			raise SysCallError(
				f"{' '.join(self.cmd)} exited with abnormal exit code [{self.exit_code}]: {str(self)[-500:]}",
				self.exit_code,
				worker=self
			)

	def is_alive(self) -> bool:
		self.poll()

		if self.started and self.ended is None:
			return True

		return False

	def write(self, data: bytes, line_ending :bool = True) -> int:
		assert type(data) == bytes  # TODO: Maybe we can support str as well and encode it

		self.make_sure_we_are_executing()

		if self.child_fd:
			return os.write(self.child_fd, data + (b'\n' if line_ending else b''))

		return 0

	def make_sure_we_are_executing(self) -> bool:
		if not self.started:
			return self.execute()
		return True

	def tell(self) -> int:
		self.make_sure_we_are_executing()
		return self._trace_log_pos

	def seek(self, pos :int) -> None:
		self.make_sure_we_are_executing()
		# Safety check to ensure 0 < pos < len(tracelog)
		self._trace_log_pos = min(max(0, pos), len(self._trace_log))

	def peak(self, output: Union[str, bytes]) -> bool:
		if self.peek_output:
			if isinstance(output, bytes):
				try:
					output = output.decode('UTF-8')
				except UnicodeDecodeError:
					return False

			peak_logfile = pathlib.Path(f"{storage['LOG_PATH']}/cmd_output.txt")

			change_perm = False
			if peak_logfile.exists() is False:
				change_perm = True

			with peak_logfile.open("a") as peek_output_log:
				peek_output_log.write(str(output))

			if change_perm:
				os.chmod(str(peak_logfile), stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)

			sys.stdout.write(str(output))
			sys.stdout.flush()

		return True

	def poll(self) -> None:
		self.make_sure_we_are_executing()

		if self.child_fd:
			got_output = False
			for fileno, event in self.poll_object.poll(0.1):
				try:
					output = os.read(self.child_fd, 8192)
					got_output = True
					self.peak(output)
					self._trace_log += output
				except OSError as error:
					if not 'Input/output error' in str(error):
						print(f"OS Error: {error}")
					self.ended = time.time()
					break

			if self.ended or (not got_output and not _pid_exists(self.pid)):
				self.ended = time.time()
				try:
					wait_status = os.waitpid(self.pid, 0)[1]
					self.exit_code = os.waitstatus_to_exitcode(wait_status)
				except ChildProcessError:
					try:
						wait_status = os.waitpid(self.child_fd, 0)[1]
						self.exit_code = os.waitstatus_to_exitcode(wait_status)
					except ChildProcessError:
						self.exit_code = 1

	def execute(self) -> bool:
		import pty

		if (old_dir := os.getcwd()) != self.working_directory:
			os.chdir(str(self.working_directory))

		# Note: If for any reason, we get a Python exception between here
		#   and until os.close(), the traceback will get locked inside
		#   stdout of the child_fd object. `os.read(self.child_fd, 8192)` is the
		#   only way to get the traceback without losing it.

		self.pid, self.child_fd = pty.fork()
		self.started = time.time()

		# https://stackoverflow.com/questions/4022600/python-pty-fork-how-does-it-work
		if not self.pid:
			history_logfile = pathlib.Path(f"{storage['LOG_PATH']}/cmd_history.txt")
			try:
				change_perm = False
				if history_logfile.exists() is False:
					change_perm = True

				try:
					with history_logfile.open("a") as cmd_log:
						cmd_log.write(f"{time.time()} {self.cmd}\n")

					if change_perm:
						os.chmod(str(history_logfile), stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
				except (PermissionError, FileNotFoundError):
					# If history_logfile does not exist, ignore the error
					pass
				except Exception as e:
					exception_type = type(e).__name__
					print(f"Unexpected {exception_type} occurred in {self.cmd}: {e}")
					raise e

				os.execve(self.cmd[0], list(self.cmd), {**os.environ, **self.environment_vars})
				if storage['arguments'].get('debug'):
					print(f"Executing: {self.cmd}")

			except FileNotFoundError:
				print(f"{self.cmd[0]} does not exist.")
				self.exit_code = 1
				return False
		else:
			# Only parent process moves back to the original working directory
			os.chdir(old_dir)

		self.poll_object.register(self.child_fd, EPOLLIN | EPOLLHUP)

		return True

	def decode(self, encoding :str = 'UTF-8') -> str:
		return self._trace_log.decode(encoding)


class SysCommand:
	def __init__(self,
		cmd :Union[str, List[str]],
		callbacks :Dict[str, Callable[[Any], Any]] = {},
		start_callback :Optional[Callable[[Any], Any]] = None,
		peek_output :Optional[bool] = False,
		environment_vars :Optional[Dict[str, Any]] = None,
		working_directory :Optional[str] = './',
		remove_vt100_escape_codes_from_lines :bool = True):

		self._callbacks = callbacks.copy()
		if start_callback:
			self._callbacks['on_start'] = start_callback

		self.cmd = cmd
		self.peek_output = peek_output
		self.environment_vars = environment_vars
		self.working_directory = working_directory
		self.remove_vt100_escape_codes_from_lines = remove_vt100_escape_codes_from_lines

		self.session :Optional[SysCommandWorker] = None
		self.create_session()

	def __enter__(self) -> Optional[SysCommandWorker]:
		return self.session

	def __exit__(self, *args :str, **kwargs :Dict[str, Any]) -> None:
		# b''.join(sys_command('sync')) # No need to, since the underlying fs() object will call sync.
		# TODO: https://stackoverflow.com/questions/28157929/how-to-safely-handle-an-exception-inside-a-context-manager

		if len(args) >= 2 and args[1]:
			print(args[1])

	def __iter__(self, *args :List[Any], **kwargs :Dict[str, Any]) -> Iterator[bytes]:
		if self.session:
			for line in self.session:
				yield line

	def __getitem__(self, key :slice) -> Optional[bytes]:
		if not self.session:
			raise KeyError(f"SysCommand() does not have an active session.")
		elif type(key) is slice:
			start = key.start or 0
			end = key.stop or len(self.session._trace_log)

			return self.session._trace_log[start:end]
		else:
			raise ValueError("SysCommand() doesn't have key & value pairs, only slices, SysCommand('ls')[:10] as an example.")

	def __repr__(self, *args :List[Any], **kwargs :Dict[str, Any]) -> str:
		return self.decode('UTF-8', errors='backslashreplace') or ''

	def __json__(self) -> Dict[str, Union[str, bool, List[str], Dict[str, Any], Optional[bool], Optional[Dict[str, Any]]]]:
		return {
			'cmd': self.cmd,
			'callbacks': self._callbacks,
			'peak': self.peek_output,
			'environment_vars': self.environment_vars,
			'session': self.session is not None
		}

	def create_session(self) -> bool:
		"""
		Initiates a :ref:`SysCommandWorker` session in this class ``.session``.
		It then proceeds to poll the process until it ends, after which it also
		clears any printed output if ``.peek_output=True``.
		"""
		if self.session:
			return True

		with SysCommandWorker(
			self.cmd,
			callbacks=self._callbacks,
			peek_output=self.peek_output,
			environment_vars=self.environment_vars,
			remove_vt100_escape_codes_from_lines=self.remove_vt100_escape_codes_from_lines,
			working_directory=self.working_directory) as session:

			self.session = session

			while not self.session.ended:
				self.session.poll()

		if self.peek_output:
			sys.stdout.write('\n')
			sys.stdout.flush()

		return True

	def decode(self, *args, **kwargs) -> Optional[str]:
		if self.session:
			return self.session._trace_log.decode(*args, **kwargs)
		return None

	@property
	def exit_code(self) -> Optional[int]:
		if self.session:
			return self.session.exit_code
		else:
			return None

	@property
	def trace_log(self) -> Optional[bytes]:
		if self.session:
			return self.session._trace_log
		return None

if __name__ == '__main__':
	from argparse import ArgumentParser
	parser = ArgumentParser(description="A set of common parameters for the tooling", add_help=False)
	
	parser.add_argument("--iso", nargs="?", help="Defines which ISO to run (skips build all together)", default=None, type=pathlib.Path)
	parser.add_argument("--build-dir", nargs="?", help="Path to where archiso will be built", default="~/archiso")
	parser.add_argument("--rebuild", action="store_true", help="To rebuild ISO or not", default=False)
	parser.add_argument("--rebuild-cache", action="store_true", help="When --rebuild, also clear the package cache", default=False)
	parser.add_argument("--offline", action="store_true", help="Attempts to build in a offline version", default=False)
	parser.add_argument("--bios", action="store_true", help="Disables UEFI and uses BIOS support instead", default=False)
	parser.add_argument("--memory", nargs="?", help="Ammount of memory to supply the machine", default=8192)
	parser.add_argument("--boot", nargs="?", help="Selects if hdd or cdrom should be booted first.", default="cdrom")
	parser.add_argument("--new-drives", action="store_true", help="This flag will wipe drives before boot.", default=False)
	parser.add_argument("--harddrives", nargs="?", help="A list of harddrives and size (~/disk.qcow2:40G,~/disk2.qcow2:15G)", default="~/test.qcow2:15G,~/test_large.qcow2:70G")
	parser.add_argument("--bridge", nargs="?", help="What bridge interface should be setup for internet access.", default=None)
	parser.add_argument("--bridge-mac", nargs="?", help="Force a MAC address on the bridge", default=None) # be:fa:41:b8:ef:ad
	parser.add_argument("--dhcp", nargs="?", help="Force DHCP on --bridge.", default=False)
	parser.add_argument("--static", nargs="?", help="Force IP on --bridge (format. ip/subnet).", default=True)
	parser.add_argument("--internet", nargs="?", help="What internet interface should be used.", default=None)
	parser.add_argument("--interface-name", nargs="?", help="What TAP interface name should be used.", default=None)
	parser.add_argument("--interface-mac", nargs="?", help="MAC for the interface", default='FE:00:00:00:00:10')
	parser.add_argument("--passthrough", nargs="?", help="Any /dev/disk/by-id/ to pass through?.", default=None)
	parser.add_argument("--packages", nargs="?", help="Any additional packages to bundle in the ISO?.", default=None)

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

	if args.bridge or (args.rebuild is not False and args.iso is None) or args.internet is not None or args.interface_name is not None:
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

	if args.iso is None and args.rebuild is False and (found_iso := glob.glob(f"{pathlib.Path('~/archiso/out/').expanduser()}/*.iso")):
		args.iso = pathlib.Path(found_iso[0])
	elif args.iso and args.iso.exists():
		pass
	else:
		args.iso = None

	if args.rebuild is True and args.iso is None:
		if builddir.exists():
			# Clear existing build dir,
			# but preserve package cache if not --rebuild-cache was given
			skip_deletes = [
				'packages',
				'packagedb'
			] if args.rebuild_cache is False else []

			for root, folders, files in os.walk(str(builddir)):
				for item in files:
					if item in skip_deletes:
						continue

					try:
						(pathlib.Path(root) / item).unlink()
					except PermissionError:
						handle = SysCommandWorker(f"sudo rm '{pathlib.Path(root) / item}'")
						pw_prompted = False
						while handle.is_alive():
							if b'password for' in handle and pw_prompted is False:
								handle.write(bytes(sudo_pw, 'UTF-8'))
								pw_prompted = True
				for item in folders:
					if item in skip_deletes:
						continue

					try:
						shutil.rmtree(str(pathlib.Path(root) / item))
					except PermissionError:
						handle = SysCommandWorker(f"sudo rm -rf '{pathlib.Path(root) / item}'")
						pw_prompted = False
						while handle.is_alive():
							if b'password for' in handle and pw_prompted is False:
								handle.write(bytes(sudo_pw, 'UTF-8'))
								pw_prompted = True
				break

		for root, folders, files in os.walk('/usr/share/archiso/configs/releng'):
			for folder in folders:
				shutil.copytree(f"{root}/{folder}", f"{builddir}/{folder}", symlinks=True, ignore=None)
			for file in files:
				shutil.copy2(f"{root}/{file}", f"{builddir}/{file}")
			break

		with (builddir / 'pacman_offline_cache.conf').open('w') as fh:
			fh.write(f"""[options]
HoldPkg     = pacman glibc
Architecture = auto

DBPath      = {builddir / 'packagedb'}
CacheDir    = {builddir / 'packages'}

CheckSpace

SigLevel    = Required DatabaseOptional
LocalFileSigLevel = Optional

[mkarchiso]
Server = file://{(builddir / 'packages').absolute()}
SigLevel    = Optional
""")


		if args.offline:
			with (builddir / "airootfs/etc/pacman.conf").open('w') as fh:
				fh.write(f"""[options]
HoldPkg     = pacman glibc
Architecture = auto

DBPath      = /root/packagedb
CacheDir    = /root/packages

CheckSpace

SigLevel    = Required DatabaseOptional
LocalFileSigLevel = Optional

# We have to patch this in after the fact,
# because pacman -Q --sysroot is called on this file
# and it won't be able to locate /root/packages/ because
# the path is not normalized before execution
[mkarchiso]
Server = file:///root/packages/
""")

		(builddir / 'packages').mkdir(parents=True, exist_ok=True)
		(builddir / 'packagedb').mkdir(parents=True, exist_ok=True)

		if (handle := SysCommand(f"git clone {args.repo} -b {args.branch} {builddir}/airootfs/root/archinstall-git")).exit_code != 0:
			raise SysCallError(f"Could not clone repository: {handle}")

		with open(f"{builddir}/packages.x86_64", "a") as packages:
			packages.write(f"git\n")
			packages.write(f"python\n")
			packages.write(f"python-setuptools\n")
			packages.write(f"python-pyparted\n")
			packages.write(f"python-simple-term-menu\n")

			if args.packages:
				for package in args.packages.split(','):
					packages.write(f"{package}\n")

		required_build_packages = []
		with (builddir / 'packages.x86_64').open('r') as fh:
			for line in fh:
				if (clean_line := line.strip()):
					required_build_packages.append(clean_line)

		if args.offline is False:
			handle = SysCommandWorker(f"bash -c 'sudo pacman --noconfirm --cachedir \"{builddir / 'packages'}\" --dbpath \"{builddir / 'packagedb'}\" -Syw {' '.join(required_build_packages)}'", peek_output=True)
			pw_prompted = False
			while handle.is_alive():
				if b'password for' in handle and pw_prompted is False:
					handle.write(bytes(sudo_pw, 'UTF-8'))
					pw_prompted = True

		else:
			# This is needed because of mkarchiso's use of pacman -Q --sysroot
			handle = SysCommandWorker(f"sudo ln -s \"{builddir / 'packages'}\" /root/", peek_output=True)
			pw_prompted = False
			while handle.is_alive():
				if b'password for' in handle and pw_prompted is False:
					handle.write(bytes(sudo_pw, 'UTF-8'))
					pw_prompted = True

			handle = SysCommandWorker(f"sudo ln -s \"{builddir / 'packagedb'}\" /root/", peek_output=True)
			pw_prompted = False
			while handle.is_alive():
				if b'password for' in handle and pw_prompted is False:
					handle.write(bytes(sudo_pw, 'UTF-8'))
					pw_prompted = True

		handle = SysCommandWorker(f'bash -c "sudo repo-add --nocolor --new {builddir / "packages"}/mkarchiso.db.tar.gz {builddir / "packages"}/{{*.pkg.tar.xz,*.pkg.tar.zst}}"', peek_output=True)
		pw_prompted = False
		while handle.is_alive():
			if b'password for' in handle and pw_prompted is False:
				handle.write(bytes(sudo_pw, 'UTF-8'))
				pw_prompted = True

		if args.offline:
			shutil.copytree(f"{builddir / 'packagedb'}", f"{builddir}/airootfs/root/packagedb")
			shutil.copytree(f"{builddir / 'packages'}", f"{builddir}/airootfs/root/packages")

		autorun_string = 'echo -n "pacman-init: "\n'
		autorun_string = 'systemctl show --no-pager -p SubState --value pacman-init.service\n'
		autorun_string += 'echo ""\n'
		autorun_string += 'echo -n "archlinux-keyring-wkd-sync.timer: "\n'
		autorun_string += 'systemctl show --property=ActiveEnterTimestamp --no-pager archlinux-keyring-wkd-sync.timer\n'
		autorun_string += 'echo ""\n'
		autorun_string += 'echo -n "archlinux-keyring-wkd-sync.service: "\n'
		autorun_string += 'systemctl show --no-pager -p SubState --value archlinux-keyring-wkd-sync.service\n'
		autorun_string += 'echo ""\n'
		autorun_string += "[[ -z $DISPLAY && $XDG_VTNR -eq 1 ]] &&"
		autorun_string += ' sh -c "cd /root/archinstall-git;'
		autorun_string += ' git config --global pull.rebase false;'
		autorun_string += ' git pull;'
		autorun_string += ' cp archinstall/scripts/guided.py ./;'
		autorun_string += ' time python guided.py' + (f' --conf {args.conf}' if args.conf else '') + (f' --creds {args.creds}' if args.creds else '') + (' --silent' if args.silent else '')
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

		if args.offline:
			handle = SysCommandWorker(f"bash -c '(cd {builddir} && sudo mkarchiso -C {builddir / 'pacman_offline_cache.conf'} -v -w work/ -o out/ ./)'", working_directory=str(builddir) , peek_output=True)
		else:
			handle = SysCommandWorker(f"bash -c '(cd {builddir} && sudo mkarchiso -v -w work/ -o out/ ./)'", working_directory=str(builddir) , peek_output=True)
		pw_prompted = False
		while handle.is_alive():
			if b'password for' in handle and pw_prompted is False:
				handle.write(bytes(sudo_pw, 'UTF-8'))
				pw_prompted = True

		if not handle.exit_code == 0:
			raise SysCallError(f"Could not build ISO: {handle}", handle.exit_code)

		ISO = glob.glob(f"{builddir}/out/archlinux-{time.strftime('%Y.%m.%d')}*.iso")[0]
	elif args.iso:
		ISO = pathlib.Path(args.iso)
		if ISO.exists() is False:
			raise RequirementError(f"ISO {args.iso} does not exist.")

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
		if args.dhcp and args.static is None:
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
			elif args.static:
				handle = SysCommandWorker(f"bash -c 'sudo ip addr add {args.static} dev {args.bridge}'")
				pw_prompted = False
				while handle.is_alive():
					if b'password for' in handle and pw_prompted is False:
						handle.write(bytes(sudo_pw, 'UTF-8'))
						pw_prompted = True

	if args.boot == 'cdrom':
		hdd_boot_priority = 2
		cdrom_boot_priority = 1
	else:
		hdd_boot_priority = 1
		cdrom_boot_priority = len(harddrives)+2

	qemu = 'sudo qemu-system-x86_64'
	qemu += f' -cpu host'
	qemu += f' -enable-kvm'
	qemu += f' -machine q35,accel=kvm'
	qemu += f' -vga virtio'
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
	if args.interface_name:
		qemu += f'  -device virtio-net-pci,mac={args.interface_mac},id=network0,netdev=network0.0,status=on,bus=pcie.0'
		qemu += f'   -netdev tap,ifname={args.interface_name},id=network0.0,script=no,downscript=no'

	if args.passthrough:
		qemu += f' --drive format=raw,file={args.passthrough}'

	handle = SysCommandWorker(qemu, peek_output=True)
	while handle.is_alive():
		if b'password for' in handle:
			if not sudo_pw:
				sudo_pw = getpass.getpass(f"Enter sudo password in order to boot the machine: ")
			handle.write(bytes(sudo_pw, 'UTF-8'))

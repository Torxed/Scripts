#!/usr/bin/python3
import logging, json
import os, stat, grp, pwd
from ctypes import *
from ctypes.util import find_library
from systemd.journal import JournalHandler

ADMINS_GID = grp.getgrnam('admingroup').gr_gid
SHARE_DIRECTORY = 'uploads'
DOMAIN = 'domain.int'
IGNORE_USERGROUPS = ['admingroup', 'wheel', 'domain admins']

log_adapter = logging.getLogger('test')
log_fmt = logging.Formatter("%(levelname)s:%(message)s")
log_ch = JournalHandler()
log_ch.setFormatter(log_fmt)
log_adapter.addHandler(log_ch)
log_adapter.setLevel(logging.DEBUG)

def get_user_info(uid):
	groups = {}
	user = pwd.getpwuid(uid)
	libc = cdll.LoadLibrary(find_library('libc'))

	getgrouplist = libc.getgrouplist
	ngroups = 50 # Ammount of groups to return
	getgrouplist.argtypes = [c_char_p, c_uint, POINTER(c_uint * ngroups), POINTER(c_int)]
	getgrouplist.restype = c_int32

	grouplist = (c_uint * ngroups)()
	ngrouplist = c_int(ngroups)

	user = pwd.getpwuid(uid)

	ct = getgrouplist(bytes(user.pw_name, 'UTF-8'), user.pw_gid, byref(grouplist), byref(ngrouplist))
	if ct < 0: # -1 simply means that there wasn't enough room, so re-poke for groups.
		getgrouplist.argtypes = [c_char_p, c_uint, POINTER(c_uint *int(ngrouplist.value)), POINTER(c_int)]
		grouplist = (c_uint * int(ngrouplist.value))()
		ct = getgrouplist(bytes(user.pw_name, 'UTF-8'), user.pw_gid, byref(grouplist), byref(ngrouplist))

	for i in range(0, ct):
		gid = grouplist[i]
		groups[gid] = grp.getgrgid(gid).gr_name

	return {
		'username' : user.pw_name,
		'uid' : user.pw_uid,
		'displayname' : user.pw_gecos,
		'homedir' : user.pw_dir,
		'shell' : user.pw_shell,
		'main_group' : user.pw_gid,
		'groups' : groups,
		'group_list' : list(groups.values())
	}

def is_local_user(u):
	for group in grp.getgrall(): # getgrall() only returns local users (a bug/feature we can exploit)
		for user in group[3]:
			if user == u:
				return True
	return False

if not 'PAM_USER' in os.environ:
	log_adapter.error(f'No PAM_USER for session')
	exit(2)
if not 'XDG_RUNTIME_DIR' in os.environ:
	log_adapter.error(f'No XDG_RUNTIME_DIR for session')
	exit(3)

UID = int(os.path.basename(os.environ['XDG_RUNTIME_DIR']))

USER_INFO = get_user_info(UID)
log_adapter.info(json.dumps(USER_INFO))

if is_local_user(USER := os.environ['PAM_USER']):
	log_adapter.info(f'{USER} is a local user.')
	exit(0) # Allow all local users
if set(USER_INFO['group_list']) & set(IGNORE_USERGROUPS):
	log_adapter.info(f'{USER} is in a trusted group(s): {set(USER_INFO["group_list"]) & set(IGNORE_USERGROUPS)}.')
	exit(0) # Allow all admin users (even if non-local)

if not USER_INFO['homedir']:
	log_adapter.error(f'{USER} has no home directory.')
	exit(4)

os.chown(os.path.abspath(f'{USER_INFO["homedir"]}'), 0, ADMINS_GID)
os.chown(os.path.abspath(f'{USER_INFO["homedir"]}/{SHARE_DIRECTORY}'), UID, ADMINS_GID)
os.chmod(os.path.abspath(f'{USER_INFO["homedir"]}'), stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
os.chmod(os.path.abspath(f'{USER_INFO["homedir"]}/{SHARE_DIRECTORY}'), stat.S_IRUSR | stat.S_IXUSR | stat.S_IRWXG)

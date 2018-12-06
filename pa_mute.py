#!/usr/bin/python3
import sys
from subprocess import Popen, STDOUT, PIPE

args = {}
positionals = []
for arg in sys.argv[1:]:
	if '--' == arg[:2]:
		if '=' in arg:
			key, val = [x.strip() for x in arg[2:].split('=')]
		else:
			key, val = arg[2:], True
		args[key] = val
	else:
		positionals.append(arg)

def run(cmd, *args, **kwargs):
	handle = Popen(cmd, shell='True', stdout=PIPE, stderr=STDOUT, **kwargs)
	output = b''
	while handle.poll() is None:
		data = handle.stdout.read()
		if len(data):
			output += data
	data = handle.stdout.read()
	output += data
	handle.stdout.close()
	return output

o = run('/usr/bin/pacmd list-sink-inputs')
index = 0
state = 'no'
apps = {}
for line in o.split(b'\n'):
	if b'index' in line:
		index = int(line.split(b':',1)[1])
	if b'application.name' in line:
		if not index in apps: apps[index] = {}
		apps[index]['name'] = line.split(b'=',1)[1].strip(b'" \\.;-').decode('UTF-8').lower()
	if b'muted' in line:
		if not index in apps: apps[index] = {}
		apps[index]['muted'] = line.split(b':',1)[1].strip().decode('UTF-8').lower()


if 'mute' in args:
	for index in apps:
		if apps[index]['name'] == args['mute']:
			if apps[index]['muted'] == 'yes':
				run(f'/usr/bin/pacmd set-sink-input-mute {index} 0')
			else:
				run(f'/usr/bin/pacmd set-sink-input-mute {index} 1')

print(apps)

import sys
from os.path import isfile
if sys.version_info.major == 2:
	from urllib2 import Request, urlopen
else:
	import urllib.request

def download(url, _file=None):
	if not _file:
		if sys.version_info.major == 2:
			req = Request(url)
			x = urlopen(req)
			data = x.read()
			x.close()
			return data
		else:
			return urllib.request.urlopen(url).read().decode('utf-8')
	else:
		if sys.version_info.major == 3:
			urllib.request.urlretrieve(url, _file)
			return True
		else:
			pass
		return True

def local_output(what, flush=True):
	sys.stdout.write(what)
	if flush:
		sys.stdout.flush()	

def Import(name):
	local_output('MOD::REQ::' + name + '\n')
	module = True
	module_file = None
	if not isfile(name + '.py'):
		local_output('MOD::GET::INDEX\n')
		index = download('https://raw.github.com/Torxed/Scripts/master/INDEX')
		if not index:
			if isfile('INDEX'):
				with open('INDEX', 'rb') as INDEX:
					index = INDEX.read()
			else:
				return None

		for line in index.split('\n'):
			if len(line) <= 0 or line[0] == '#': continue
		
			module_name, module_link = line.split(' - ',1)
			if ' - ' in module_link:
				module_link, index_functions = module_link.split(' - ',1)
				tmp = {}
				index_functions = index_functions.split(',')
				for func in index_functions:
					if ' - ' in func:
						key, val = func.split(' - ',1)
					else:
						key, val = func, ''
					tmp[key] = val
				index_functions = tmp
				#local_output(str(index_functions)+'\n')
			else:
				index_functions = {}
				
			if name in module_name or name in index_functions:
				if name in module_name:
					local_output('MOD::MAP::FILE::"' + name + '"[>>]' + module_name + '.py\n')
				else:
					local_output('MOD::MAP::FUNC::"' + name + '"[>>]' + module_name + '.py\n')
				module_file = module_name
				with open(module_file + '.py', 'w') as fh_module:
					fh_module.write(download(module_link.strip()))
				if name in index_functions and name not in module_name:
					module = False
				break
	else:
		module_file = name

	if module_file == None or not isfile(module_file + '.py'):
		local_output('MOD::ERR::Could not find module/function\n')
		return None
	
	local_output('MOD::IMP::'+str(module_file)+'\n')
	if module:
		return __import__(module_file)
	else:
		return getattr(__import__(module_file), name)

if __name__ == '__main__':
	import sys
	sys.stdout.write('Module                   |  Functions\n')
	sys.stdout.write('--- --- --- --- --- --- --- --- --- -\n')
	sys.stdout.flush()
	for line in download('https://raw.github.com/Torxed/Scripts/master/INDEX').split('\n'):
		if len(line) <= 0 or line[0] == '#': continue
		module_name, module_link = line.split(' - ',1)
		sys.stdout.write(module_name + '     ' + ('-'*(20-len(module_name))) + '|  \n')
		if ' - ' in module_link:
			module_link, index_functions = module_link.split(' - ',1)
			for func in index_functions.split(','):
				sys.stdout.write((' '*25) + '|  ' + func + '\n')
		else:
			sys.stdout.write('    ?')

		sys.stdout.write('\n')
		sys.stdout.flush()

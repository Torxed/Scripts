from urllib2 import Request, urlopen
from os.path import isfile
def download(url):
	req = Request(url)
	x = urlopen(req)
	data = x.read()
	x.close()
	return data
	
def Import(name):
	module = True
	module_file = None
	if not isfile(name + '.py'):
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
				index_functions = index_functions.split(',')
			else:
				index_functions = []
				
			if name in module_name or name in index_functions:
				module_file = module_name
				with open(module_file + '.py', 'wb') as fh_module:
					fh_module.write(download(module_link.strip()))
				if name in index_functions:
					module = False
				break
	else:
		module_file = name

	if module_file == None or not isfile(module_file):
		return None
		
	if module:
		return __import__(module_file)
	else:
		return __import__(module_file).name

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

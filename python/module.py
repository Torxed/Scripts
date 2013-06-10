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
	if not isfile(absname):
		for line in download('https://raw.github.com/Torxed/Scripts/master/INDEX').split('\n'):
			if len(line) <= 0 or line[0] == '#': continue
		
			module_name, module_link = line.split(' - ',1)
			if ' - ' in module_link:
				index_functions = module_link.split(' - ',1).split(',')
			else:
				index_functions = []
				
			if name in module_name or name in index_functions:
				module_file = module_name + '.py'
				with open(module_name, 'wb') as fh_module:
					fh_module.write(download(module_link.strip()))
				if name in index_functions:
					module = False
				break
			
	if module_file == None or not isfile(module_file):
		return None
		
	if module:
		return __import__(module_file)
	else:
		return __import__(module_file).name

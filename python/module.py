from urllib2 import Request, urlopen
from os.path import isfile
def download(url):
	req = Request(url)
	x = urlopen(req)
	data = x.read()
	x.close()
	return data
	
def Import(name):
	absname = name+'.py'
	module = True
	module_file = None
	if not isfile(absname):
		for line in download('https://raw.github.com/Torxed/Scripts/master/INDEX').split('\n'):
			if len(line) <= 0 or line[0] == '#': continue
		
			index_modname, index_modlink = line.split(' - ',1)
			if ' - ' in index_modlink:
				index_functions = index_modlink.split(' - ',1).split(',')
			else:
				index_functions = []
				
			if absname in index_modname or name in index_functions:
				module_file = index_modname
				with open(index_modname, 'wb') as fh_module:
					fh_module.write(download(index_modlink.strip()))
				if name in index_functions:
					module = False
				break
			
	if module_file == None or not isfile(index_modname + '.py'):
		return None
		
	if module:
		return __import__(index_modname)
	else:
		return __import__(index_modname).name

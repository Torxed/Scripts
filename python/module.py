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
	if not isfile(absname):
		for line in download('https://raw.github.com/Torxed/Scripts/master/INDEX').split('\n'):
			if len(line) <= 0 or line[0] == '#': continue
			index_modname, index_modlink = line.split(' - ',1)
			if absname in index_modname:
				with open(absname, 'wb') as fh_module:
					fh_module.write(download(index_modlink.strip()))
				break
	if not isfile(absname):
		return None
	return __import__(name)

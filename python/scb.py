from socket import *
from json import *


class HTTP_session():
	def __init__(self, base, connect=False):
		self.base = base
		self.s = None
		if connect:
			self.connect()

	def connect(self):
		self.s = socket()
		self.s.connect(('api.scb.se', 80))
		
	def disconnect(self):
		self.s.close()

	def parseHeader(self, hd):
		headers = {}
		for row in hd.split('\r\n'):
			if ': ' in row:
				key, val = row.split(': ', 1)
				headers[key.lower()] = val
		return headers

	def recv(self, ammount=8192):
		return self.s.recv(ammount)

	def parse(self, d):
		if not '\r\n\r\n' in d:
			return None, None

		headerdata, d = d.split('\r\n\r\n',1)
		return self.parseHeader(headerdata), d

	def fetchUrl(self, u=''):
		request = ''
		request += 'GET ' + self.base + '/' + u + ' HTTP/1.1\r\n'
		request += 'Host: api.scb.se\r\n'
		request += 'Connection: keep-alive\r\n'
		request += 'Cache-Control: max-age=0\r\n'
		request += 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n'
		request += 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.63 Safari/537.31\r\n'
		#request += 'Referer: http://www.scb.se/Pages/List____354082.aspx\r\n'
		request += 'Accept-Encoding: gzip,deflate,sdch\r\n'
		request += 'Accept-Language: en-US,en;q=0.8\r\n'
		request += 'Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.3\r\n'
		#request += 'Cookie: __utma=2306226.713130778.1369250695.1369250695.1369250695.1; __utmb=2306226.1.10.1369250695; __utmc=2306226; __utmz=2306226.1369250695.1.1.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided)\r\n'
		return request +'\r\n'

	def send(self, what):
		self.s.send(what)

def swe(d):
	return d.encode('iso-8859-1')

def select(options):
	remap = {}
	index = 0
	for key, val in options.items():
		print index,'-',swe(key)
		remap[index] = val
		index += 1
	s = raw_input('Selection: ')
	return remap[int(s)]

base = '/OV0104/v1/doris/sv/ssd'
for i in range(0,4):
	handle = HTTP_session(base, True)
	handle.send(handle.fetchUrl())
	data = handle.recv()
	headers, tmp = handle.parse(data)
	if tmp:
		data = tmp

	while len(data) < int(headers['content-length']):
		data += handle.recv()

	data = loads(data)

	if 'variables' in data:
		"""
		Here's where a POST should be made.
		The POST URL is the same as the current base.
		Each variable has a code connected to it.
		
		A example:
		{   
			"query": [{"code": "ContentsCode",
						"selection": {         
							"filter": "item",         
							"values": ["BE0101N1"]
						}     
					  },
					  {"code": "Tid",
						"selection": {         
							"filter": "item",         
							"values": ["2010", "2011"]
						}
					  }],
			"response": {"format": "json",}
		}
		"""
		print base
		print swe(data['title'])
		print ''
		for block in data['variables']:
			print block
			print ''
	else:
		options = {}
		for obj in data:
			options[obj['text']] = obj['id']

		base += '/' + select(options)
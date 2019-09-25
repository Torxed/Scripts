import json, ssl
from socket import *
from select import epoll, EPOLLIN

ENCODING = 'UTF-8'

class HTTPRequest():
	def __init__(self, address, url, payload=b'', headers={}, method_keyword='_method', hostname=None, config={'ssl' : True, 'build' : True, 'send' : True}):
		if type(address) == socket:
			self.hostname = hostname
			self.socket = address
		elif type(address) == tuple:

			self.socket = socket()
			self.socket.connect(address)
			self.hostname = address[0]

			if address[1] == 443 or config['ssl']:
				context = ssl.create_default_context()
				self.socket = context.wrap_socket(self.socket, server_hostname=address[0])

		self.url = url
		self.method_keyword = method_keyword
		self.headers = headers
		self.config = config
		self.raw_response = b''
		if not self.method_keyword in self.headers: self.headers[self.method_keyword] = 'GET'

		if 'build' in config and config['build']:
			self.request = self.build()
			if 'send' and config['send']:
				self.send(self.request)

	def __repr__(self):
		return f"{str(self.socket)}-{self.headers[self.method_keyword]}:{self.url}"

	def build(self):
		payload = b''
		payload += bytes(f'{self.headers[self.method_keyword]} {self.url} HTTP/1.1\r\n', ENCODING)

		if self.headers[self.method_keyword] == 'POST' and 'content-length' not in self.headers: self.headers['content-length'] = str(len(self.payload))
		if not 'host' in self.headers: self.headers['host'] = self.hostname

		del(self.headers[self.method_keyword])
		for key, val in self.headers.items():
			payload += bytes(f'{key}: {val}\r\n', ENCODING)
		payload += b'\r\n'

		print(payload.decode(ENCODING))
		return payload

	def send(self, data):
		self.socket.send(self.request)

#	def recv(self, *args, **kwargs):
#		return self.socket.recv(*args, **kwargs)


class HTTPResponse():
	def __init__(self, socket, raw_response):
		self.socket = socket
		self.raw_response = raw_response
		self.raw_headers = b''
		self.raw_payload = b''
		self.raw_parsed = 0
		self.raw_header_ending = 0

		self.headers = {}
		self.payload = b''
		self.delivered = False
		self.poller = epoll()
		self.poller.register(self.socket.fileno(), EPOLLIN)

	def recv(self, buf=8192, timeout=0.025):
		for fileno, event in self.poller.poll(timeout):
			self.raw_response += self.socket.recv(buf)

	def get_all(self):
		while not self.peak():
			self.recv(timeout=5)
		self.clean_payload()
		return True

	def peak(self):
		if b'\r\n\r\n' in self.raw_response and len(self.headers) <= 0:
			self.raw_headers, self.raw_payload = self.raw_response.split(b'\r\n\r\n', 1)
			self.raw_header_ending += len(self.raw_headers) + len('\r\n\r\n') + len(self.raw_payload)

			for index, item in enumerate(self.raw_headers.split(b'\r\n')):
				if type(item) == bytes: item = item.decode(ENCODING)
				if index == 0:
					version, code, message = item.split(' ', 2)
					self.headers['_response-code'] = [float(version.split('/')[1]), int(code), message]
					continue
				if ':' in item:
					key, val = item.split(':',1)
					self.headers[key.lower()] = val.strip()
		elif len(self.headers):
			self.raw_payload += self.raw_response[self.raw_header_ending:]

		self.parse_headers()
		return self.delivered
		#self.clean_payload()

	def append_chunk(self, chunk):
		length, self.raw_payload = self.raw_payload.split(b'\r\n',1)
	
	def parse_headers(self):
		for key,val in self.headers.items():
			if type(key) == bytes: key = key.decode(ENCODING) #TODO: Redundant
			if type(val) == bytes: val = val.decode(ENCODING) #TODO: Redundant
			if type(val) == str:
				if val.isdigit(): self.headers[key] = float(val)
			if key[:len('content-type')] == 'content-type' and ';' in val: self.headers[key] = val.split(';',1)[0]
			if key[:len('transfer-encoding')] == 'transfer-encoding' and val.lower() == 'chunked':
				length, payload = self.raw_payload[self.raw_parsed:].split(b'\r\n',1)
				self.raw_parsed += len(length) + len('\r\n') + int(length, 16)
				if int(length, 16) == 0:
					self.delivered = True
				self.payload += payload
			elif key[:len('content-length')] == 'content-length' and val == len(self.raw_payload):
				self.payload = self.raw_payload
				self.delivered = True

	def clean_payload(self):
		if 'content-type' in self.headers and self.headers['content-type'] == 'application/json':
			try:
				self.payload = json.loads(self.raw_payload)
			except:
				self.payload = self.raw_payload
		else:
			self.payload = self.raw_payload

	def __repr__(self):
		return json.dumps({'_headers' : self.headers, '_body' : self.payload.decode(ENCODING)}, indent=4)

request = HTTPRequest(('hvornum.se', 443), url='/ip/')
response = HTTPResponse(request.socket, request.raw_response)

while not response.get_all():
	pass

print(response)
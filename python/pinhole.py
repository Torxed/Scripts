import ssl
from socket import *
from select import epoll, EPOLLIN, EPOLLHUP

# v1.0 - 2004 Anton Hvornum
# v2.0 - 2019 Anton Hvornum

class endpoint():
	def __init__(self, host, port, relay=None, server=False, ssl=False, *args, **kwargs):
		self.host = host
		self.port = port
		self.relay_target = relay
		self.ssl = ssl
		self.args = args
		self.kwargs = kwargs
		self.server = server

		self.poller = epoll()
		self.sockets = {}

		self.socket = None
		if self.server:
			self.socket = socket()
			self.socket.bind((self.host, self.port))
			self.socket.listen(4)

			self.poller.register(self.socket.fileno(), EPOLLIN | EPOLLHUP)
		else:
			if not 'UNIQUE_PER_CLIENT' in kwargs: kwargs['UNIQUE_PER_CLIENT'] = False
			if not kwargs['UNIQUE_PER_CLIENT']:
				self.connect()

	def __repr__(self):
		return f'<endpoint@{self.host}:{self.port}>'

	def attach(self, relay):
		self.relay_target = relay

	def connect(self):
		if self.socket is None:
			print(f'{self} is connecting.')
			self.socket = socket()
			self.socket.connect((self.host, self.port))
			if self.ssl:
				self.ssl_wrap()

			self.poller.register(self.socket.fileno(), EPOLLIN | EPOLLHUP)

	def ssl_wrap(self, fileno=None):
		if self.server:
			if not 'DO_HANDSHAKE' in self.kwargs: self.kwargs['DO_HANDSHAKE'] = True

			context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
			context.load_cert_chain(self.kwargs['ssl_cert'], self.kwargs['ssl_key'])

			if fileno in self.sockets:
				self.sockets[fileno]['socket'] = context.wrap_socket(self.sockets[fileno]['socket'], server_side=True, do_handshake_on_connect=self.kwargs['DO_HANDSHAKE'])
		else:
			context = ssl.create_default_context()
			self.socket = context.wrap_socket(self.socket, server_hostname=self.host, do_handshake_on_connect=self.kwargs['DO_HANDSHAKE'])

	def send(self, data, fileno=None, encoding='UTF-8'):
		if type(data) == dict:
			data = json.dumps(data)
		if type(data) == str:
			data = bytes(data, encoding)

		if self.server:
			if fileno:
				return self.sockets[fileno]['socket'].send(data)
			else:
				resp = -1
				for fileno in self.sockets:
					r = self.sockets[fileno]['socket'].send(data)
					if resp == -1 or r < resp:
						resp = r
				return resp
		else:
			return self.socket.send(data)

	def relay(self, sender_fileno, data):
		if self.relay_target:
			if not self.kwargs['UNIQUE_PER_CLIENT']:
				if self.relay_target.server == False and self.relay_target.socket is None:
					self.relay_target.connect()
				return self.relay_target.send(data)
			else:
				relayer = self.sockets[sender_fileno]

			print(f'Relaying to {self.relay_target}: {data[:120]}')
		raise ValueError('No relay host defined')

	def poll(self, timeout=0.25):
		for fileno, event in self.poller.poll(timeout):
			if fileno == self.socket.fileno() and self.server:
				ns, na = self.socket.accept()
				fileno = ns.fileno()
				self.sockets[fileno] = {'socket' : ns, 'address' : na}
				if self.server and self.ssl:
					self.ssl_wrap(fileno)
				self.poller.register(fileno, EPOLLIN | EPOLLHUP)
			elif fileno == self.socket.fileno() and not self.server:
				data = self.socket.recv(8192)
				if len(data) <= 0:
					self.poller.unregister(fileno)
					self.socket.close()
					continue

				yield data
			elif fileno in self.sockets:
				data = self.sockets[fileno]['socket'].recv(8192)
				if len(data) <= 0:
					self.poller.unregister(fileno)
					del(self.sockets[fileno])
					continue

				yield data
			else:
				print('Error:', fileno)
				print('Master:', self.socket.fileno())
				for socket in self.sockets:
					print('', 'socket:', socket, self.sockets[socket])

print(' ** Setting up [local]')
local = endpoint('', 587, server=True, ssl=False, ssl_cert='cert.pem', ssl_key='key.pem')
print(' !! Setting up [smtp.gmail.com]')
hvornum = endpoint('smtp.gmail.com', 587, UNIQUE_PER_CLIENT=True)

local.attach(hvornum)
hvornum.attach(local)

while True:
	for fileno, data in local.poll():
		print(' ** [local] got data:', data[:120])
		local.relay(fileno, data)

	for fileno, data in hvornum.poll():
		print(' !! [smtp.gmail.com] got data:', data[:120])
		hvornum.relay(fileno, data)

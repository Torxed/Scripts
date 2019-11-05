import ssl
from socket import *
from select import epoll, EPOLLIN, EPOLLHUP

# v1.0 - 2004 Anton Hvornum
# v2.0 - 2019 Anton Hvornum

class endpoint():
	def __init__(self, host, port, relay=None, server=False, ssl=False, _socket=None, *args, **kwargs):
		if not 'UNIQUE_PER_CLIENT' in kwargs: kwargs['UNIQUE_PER_CLIENT'] = False
		if not 'AUTO_RELAY' in kwargs: kwargs['AUTO_RELAY'] = False
		if not 'SSL_TRIGGERS' in kwargs: kwargs['SSL_TRIGGERS'] = {}
		if not 'MUTE_SSL_HANDSHAKE' in kwargs: kwargs['MUTE_SSL_HANDSHAKE'] = False
		if not 'SSL_DO_HANDSHAKE' in kwargs: kwargs['SSL_DO_HANDSHAKE'] = True
		if not 'SERVER_SIDE' in kwargs: kwargs['SERVER_SIDE'] = False

		self.host = host
		self.port = port
		self.relay_target = relay
		self.ssl = ssl
		self.args = args
		self.kwargs = kwargs
		self.server = server
		self.ssl_active = False

		self.poller = epoll()
		self.sockets = {}

		self.socket = _socket
		if self.server:
			self.socket = socket()
			self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
			self.socket.bind((self.host, self.port))
			self.socket.listen(4)

			self.poller.register(self.socket.fileno(), EPOLLIN | EPOLLHUP)
		elif self.socket is None:
			if not kwargs['UNIQUE_PER_CLIENT']:
				self.connect()

	def __repr__(self):
		return f'<endpoint@{self.host}:{self.port}>'

	def attach(self, relay, *args, **kwargs):
		if isinstance(relay, endpoint):
			print(f'Attaching endpoint({relay}) instance to {self}.relay_target')
			self.relay_target = relay
		elif issubclass(relay, endpoint):
			print(f'Storing endpoint() for further use.')
			self.relay_target = {'class' : relay, 'args' : args, 'kwargs' : kwargs}

	def connect(self):
		if self.socket is None:
			print(f'{self} is connecting.')
			self.socket = socket()
			self.socket.connect((self.host, self.port))
			if self.ssl:
				self.ssl_wrap()

			self.poller.register(self.socket.fileno(), EPOLLIN | EPOLLHUP)

	def ssl_wrap(self, fileno=None):
		print(f'{self} wrapping socket ({self.server, fileno})')
		self.ssl_active = True
		if self.kwargs['SERVER_SIDE']:
		#if self.server:
			context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
			context.load_cert_chain(self.kwargs['ssl_cert'], self.kwargs['ssl_key'])

			if fileno in self.sockets:
				print(f'Wrapping {self.sockets[fileno]["handle"]} as server_side=True')
				self.sockets[fileno]['socket'] = context.wrap_socket(self.sockets[fileno]['socket'], server_side=True, do_handshake_on_connect=True, suppress_ragged_eofs=False)#, server_side=True)#, do_handshake_on_connect=self.kwargs['SSL_DO_HANDSHAKE'])
			else:
				self.socket = context.wrap_socket(self.socket, server_side=True, do_handshake_on_connect=True, suppress_ragged_eofs=False)#, server_side=True)#, do_handshake_on_connect=self.kwargs['SSL_DO_HANDSHAKE'])
		else:
			print(f'Wrapping {self}.socket as server_side=False')
			context = ssl.create_default_context()
			self.socket = context.wrap_socket(self.socket, server_hostname=self.host)#, do_handshake_on_connect=self.kwargs['SSL_DO_HANDSHAKE'])

	def send(self, data, fileno=None, encoding='UTF-8'):
		if type(data) == dict:
			data = json.dumps(data)
		if type(data) == str:
			data = bytes(data, encoding)

		if self.server:
			if fileno:
				print('* Sending data:', data)
				return self.sockets[fileno]['socket'].send(data)
			else:
				resp = -1
				for fileno in self.sockets:
					print('** Sending data:', data)
					r = self.sockets[fileno]['socket'].send(data)
					if resp == -1 or r < resp:
						resp = r
				return resp
		else:
			print('*** Sending data:', data)
			return self.socket.send(data)

	def relay(self, sender_fileno, data):
		if self.relay_target:
			if self.kwargs['UNIQUE_PER_CLIENT']:
				print(f'{self.sockets[sender_fileno]["handle"]} -> {self.sockets[sender_fileno]["relay"]}: {data[:120]}')
				return self.sockets[sender_fileno]['relay'].send(data)
			else:
				if self.relay_target.server == False and self.relay_target.socket is None:
					self.relay_target.connect()
				print(f'{self} -> {self.relay_target}: {data[:120]}')
				return self.relay_target.send(data)

		raise ValueError('No relay host defined')

	def poll(self, timeout=0.25):
		for fileno, event in self.poller.poll(timeout):
			if fileno == self.socket.fileno() and self.server:
				ns, na = self.socket.accept()
				fileno = ns.fileno()
				print(f'{na} connected via {fileno}.')

				self.sockets[fileno] = {'socket' : ns, 'ssl_active' : False, 'address' : na, 'handle' : endpoint(na[0], na[1], _socket=ns, SERVER_SIDE=True, ssl_cert=self.kwargs['ssl_cert'], ssl_key=self.kwargs['ssl_key'])}
				if self.kwargs['UNIQUE_PER_CLIENT']:
					print(f'Opening relay for {ns.fileno()} to ({self.relay_target["args"]}, {self.relay_target["kwargs"]})')
					self.sockets[fileno]['relay'] = self.relay_target['class'](*self.relay_target['args'], **self.relay_target['kwargs'])
					self.sockets[fileno]['relay'].attach(self.sockets[fileno]['handle'])
				if self.server and self.ssl:
					print('Wrapping in SSL')
					self.ssl_wrap(fileno)
#				print(f'{fileno} registered for polling.')
				self.poller.register(fileno, EPOLLIN | EPOLLHUP)
			elif fileno == self.socket.fileno() and not self.server:
				data = self.socket.recv(8192)
				if len(data) <= 0:
					self.poller.unregister(fileno)
					self.socket.close()
					continue

				mute = False
				if not self.ssl_active:
					for key in self.kwargs['SSL_TRIGGERS']:
						if key.lower() in data.lower():
							print(f'{self} got a TLS trigger, starting wrapping procedure.')
							self.ssl_wrap()

							if not self.kwargs['MUTE_SSL_HANDSHAKE'] and self.kwargs['AUTO_RELAY']:
								self.relay(self.socket.fileno(), data)
							else:
								print(f'{self} *Muted*: {data[:120]}')
								mute = True

							if self.kwargs['SSL_BOTH_ENDPOINTS']:
								print(f'{self} is triggering ssl_wrap() on endpoint {self.relay_target}')
								self.relay_target.ssl_wrap()
							
				if mute: continue

				if self.kwargs['AUTO_RELAY']:
					self.relay(self.socket.fileno(), data)
				else:
					print(f'{self} got: {data[:120]}')
					yield fileno, data

			elif fileno in self.sockets:
				data = self.sockets[fileno]['socket'].recv(8192)
				if len(data) <= 0:
					print(f'{self.sockets[fileno]["address"]} disconnected.')
					self.poller.unregister(fileno)
					del(self.sockets[fileno])
					continue

				if not self.sockets[fileno]['handle'].ssl_active:
					for key in self.kwargs['SSL_TRIGGERS']:
						if key.lower() in data.lower():
							print(f'{self} got a TLS trigger, starting wrapping procedure.')
							self.ssl_wrap(fileno)
							if self.kwargs['SSL_BOTH_ENDPOINTS']:
								print(f'{self} is triggering ssl_wrap() on endpoint {self.relay_target}')
								self.relay_target.ssl_wrap()
							break

					if self.ssl_active:
						if self.kwargs['MUTE_SSL_HANDSHAKE']:
							print(f'{self.sockets[fileno]["handle"]}: Handshake muted')
							continue

				yield fileno, data
			else:
				print('Error:', fileno)
				print('Master:', self.socket.fileno())
				for s in self.sockets:
					print('', 'socket:', socket, self.sockets[socket])

		for s in self.sockets:
			if 'relay' in self.sockets[s]:
				for fileno, data in self.sockets[s]['relay'].poll():
					yield fileno, data

print(' ** Setting up [local]')
local = endpoint('', 587, server=True, ssl=False, ssl_cert='cert.pem', ssl_key='key.pem', UNIQUE_PER_CLIENT=True, SERVER_SIDE=True)
local.attach(endpoint, 'smtp.gmail.com', 587, AUTO_RELAY=True, SSL_TRIGGERS={b'Ready to start TLS'}, SSL_BOTH_ENDPOINTS=True)

while True:
	for fileno, data in local.poll():
		local.relay(fileno, data)

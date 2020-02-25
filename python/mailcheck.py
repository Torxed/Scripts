import sys, dns.resolver, signal, logging, ssl, time
from select import epoll, EPOLLIN, EPOLLHUP
from systemd.journal import JournalHandler
from socket import *

class CustomAdapter(logging.LoggerAdapter):
	def process(self, msg, kwargs):
		return '[{}] {}'.format(self.extra['origin'], msg), kwargs

## == Setup logging:
logger = logging.getLogger() # __name__
journald_handler = JournalHandler()
journald_handler.setFormatter(logging.Formatter('[{levelname}] {message}', style='{'))
logger.addHandler(journald_handler)
logger.setLevel(logging.DEBUG)
LOG_LEVEL = 5

def log(*msg, origin='UNKNOWN', level=5, **kwargs):
	if level <= LOG_LEVEL:
		msg = [item.decode('UTF-8', errors='backslashreplace') if type(item) == bytes else item for item in msg]
		msg = [str(item) if type(item) != str else item for item in msg]
		log_adapter = CustomAdapter(logger, {'origin': origin})
		if level <= 1:
			print('[!] ' + ' '.join(msg))
			log_adapter.critical(' '.join(msg))
		elif level <= 2:
			print('[E] ' + ' '.join(msg))
			log_adapter.error(' '.join(msg))
		elif level <= 3:
			print('[W] ' + ' '.join(msg))
			log_adapter.warning(' '.join(msg))
		elif level <= 4:
			print('[-] ' + ' '.join(msg))
			log_adapter.info(' '.join(msg))
		else:
			print('[ ] ' + ' '.join(msg))
			log_adapter.debug(' '.join(msg))

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

if not 'domain' in args:
	raise ParameterError('mailcheck needs at least --domain "domain.example" as an argument.')
if not 'from' in args: args['from'] = f'admin@{args["domain"]}'
if not 'to' in args: args['to'] = f'admin@{args["domain"]}'
if not '@' in args['from']: args['from'] = f'{args["from"]}@{args["domain"]}'
if not '@' in args['to']: args['to'] = f'{args["to"]}@{args["domain"]}'
if not 'subject' in args: args['subject'] = 'Test mail from outside.'
datestamp = time.strftime('%a, %d %b %Y %H:%M:%S') # Tue, 15 Jan 2008 16:02:43 -0500

def recv_all(s, poll):
	data = b''
	while poll.poll(0.5):
		data += s.recv(8192)
	return data

log(f'Querying domain "{args["domain"]}"', level=4, origin='mailcheck')
context = ssl.create_default_context()
for mx_record in dns.resolver.query(args['domain'], 'MX'):
	mail_server = mx_record.to_text().split()[1][:-1]

	mail_socket = socket()
	mail_socket.connect((mail_server, 25))
	mail_poll = epoll()
	mail_poll.register(mail_socket.fileno(), EPOLLIN | EPOLLHUP)

	if not mail_poll.poll(1):
		log('Server did not greet us properly. Manual checks needed.', level=2, origin='mailcheck::greeting')
		exit(1)

	data = recv_all(mail_socket, mail_poll)
	for line in data.split(b'\r\n'):
		if len(line.strip()) == 0: continue
		if line.split(b' ', 1)[0] != b'220':
			log(f'Server did not greet us properly (Unusual greeting code: {data[:50]}). Manual checks needed.', level=2, origin='mailcheck::greeting')
			exit(1)
		elif line.split(b' ', 1)[0] == b'250':
			break

	mail_socket.send(b'HELO test.com\r\n')
	if not mail_poll.poll(1):
		log('Server did not welcome us after HELLO, rude. Investigate why.', level=2, origin='mailcheck::HELLO')
		exit(1)

	data = recv_all(mail_socket, mail_poll)
	for line in data.split(b'\r\n'):
		if len(line.strip()) == 0: continue
		if line.split(b' ', 1)[0] != b'250':
			log(f'Server sent unusual welcome code: {data[:50]}. Manual checks neeeded.', level=2, origin='mailcheck::HELLO')
			exit(1)
		elif line.split(b' ', 1)[0] == b'250':
			break

	log(f'Sending mail as {args["from"]}', level=5, origin='MAIL_FROM')
	mail_socket.send(bytes(f'MAIL FROM:<{args["from"]}>\r\n', 'UTF-8'))
	if not mail_poll.poll(1):
		log('Server did not answer our MAIL FROM, rude. Investigate why.', level=2, origin='mailcheck::MAIL_FROM')
		exit(1)

	data = recv_all(mail_socket, mail_poll)
	for line in data.split(b'\r\n'):
		if len(line.strip()) == 0: continue
		if line.split(b' ', 1)[0] != b'250':
			log(f'Server sent unusual response code for MAIL FROM: {data[:50]}. Manual checks neeeded.', level=2, origin='mailcheck::MAIL_FROM')
			exit(1)
		elif line.split(b' ', 1)[0] == b'250':
			break

	log(f'Sending mail to {args["to"]}', level=5, origin='MAIL_FROM')
	mail_socket.send(bytes(f'RCPT TO:<{args["to"]}>\r\n', 'UTF-8'))
	if not mail_poll.poll(1):
		log('Server did not answer our RCPT TO, rude. Investigate why.', level=2, origin='mailcheck::RCPT_TO')
		exit(1)

	data = recv_all(mail_socket, mail_poll)
	for line in data.split(b'\r\n'):
		if len(line.strip()) == 0: continue
		if line.split(b' ', 1)[0] != b'250':
			log(f'Server sent unusual response code for MAIL TO: {data[:50]}. Manual checks neeeded.', level=2, origin='mailcheck::RCPT_TO')
			exit(1)
		elif line.split(b' ', 1)[0] == b'250':
			break

	log(f'Sending DATA request.', level=5, origin='DATA')
	mail_socket.send(bytes(f'DATA\r\n', 'UTF-8'))
	if not mail_poll.poll(1):
		log('Server did not answer our DATA request, rude. Investigate why.', level=2, origin='mailcheck::DATA')
		exit(1)

	data = recv_all(mail_socket, mail_poll)
	for line in data.split(b'\r\n'):
		if len(line.strip()) == 0: continue
		if line.split(b' ', 1)[0] != b'354':
			log(f'Server sent unusual response code for MAIL TO: {data[:50]}. Manual checks neeeded.', level=2, origin='mailcheck::DATA')
			exit(1)
		elif line.split(b' ', 1)[0] == b'354':
			break

	log(f'Sending mail body data, with subject: "{args["subject"]}".', level=5, origin='DATA')
	mail_socket.send(bytes(f'From: "{" ".join(args["from"].split("@", 1)[0].split("."))} <{args["from"]}>\r\n', 'UTF-8'))
	mail_socket.send(bytes(f'To: "{" ".join(args["to"].split("@", 1)[0].split("."))} <{args["to"]}>\r\n', 'UTF-8'))
	mail_socket.send(bytes(f'Date: {datestamp}\r\n', 'UTF-8'))
	mail_socket.send(bytes(f'Subject: {args["subject"]}\r\n', 'UTF-8'))
	mail_socket.send(bytes(f'\r\n', 'UTF-8'))
	mail_socket.send(bytes(f'Unauthenticated test from the outside.\r\n', 'UTF-8'))
	mail_socket.send(bytes(f'This domain does not appear to be secure: {args["domain"]}.\r\n', 'UTF-8'))
	mail_socket.send(bytes(f'\r\n', 'UTF-8'))
	mail_socket.send(bytes(f'//anton@hvornum.se\r\n', 'UTF-8'))
	mail_socket.send(bytes(f'.\r\n', 'UTF-8'))

	log(f'Waiting for send status...', level=5, origin='DATA_END')
	if not mail_poll.poll(2):
		log('Server did not answer us after DATA was sent, rude. Investigate why.', level=2, origin='mailcheck::DATA_END')
		exit(1)

	data = recv_all(mail_socket, mail_poll)
	for line in data.split(b'\r\n'):
		if len(line.strip()) == 0: continue
		if line.split(b' ', 1)[0] != b'250':
			log(f'Server sent unusual response code for DATA_END: {data[:200]}. Manual checks neeeded.', level=2, origin='mailcheck::DATA_END')
			exit(1)
		elif line.split(b' ', 1)[0] == b'250':
			break

	log(f'Mail check omplete, mail-server seems to accept unauthenticated mails ({data}).', level=4, origin='DONE')
	mail_socket.send(b'QUIT')

	mail_poll.unregister(mail_socket.fileno())
	mail_socket.close()

	exit(0)

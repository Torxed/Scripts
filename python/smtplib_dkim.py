import smtplib, dns.resolver, os, logging, socket, ssl, dkim, json, time, pathlib, hashlib
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from flanker.addresslib import address # requires

"""
mailman = MailService(host=os.environ.get('MAIL_SERVER'), port=os.environ.get('MAIL_PORT'), tls=True, username=os.environ.get('MAIL_USERNAME'), password=os.environ.get('MAIL_PASSWORD'))

with open('./test.png', 'rb') as fh:
	test_img = MIMEImage(fh.read())

attachments = {
	'test1' : test_img,
}

mailman.send(
	sender=os.environ['MAIL_USERNAME'],
	reciever=recipient,
	subject=f'{prices.day.date()}\'s electric prices',
	txt='This is a mail :)',
	html='<html><body>This is a mail <img src="cid:test1"></body></html>',
	attachments=attachments
)
"""

configuration = {
	"nameservers" : ["8.8.8.8", "4.4.4.4"],
	"TRY_ONE_MAILSERVER" : False
}

def uuid(length=24):
	"""
	Generate a unique ID using sha512()
	"""
	return hashlib.sha512(os.urandom(length)).hexdigest()

class MailService:
	def __init__(self, host=None, port=None, tls=True, username=None, password=None):
		self.host = host
		self.port = port
		self.tls = tls
		self.username = username
		self.password = password

	def send(self, sender, reciever, subject, txt, html=None, attachments=None, sign=False, encoding='UTF-8'):
		"""
		Note that all emails will be sent as ISO-8859-1 to allow
		for Swedish characters.
		"""

		recieving_domain = address.parse(reciever).ace_hostname
		recieving_address = address.parse(reciever).ace_address
		sender_domain = address.parse(sender).ace_hostname
		sender_address = address.parse(sender).ace_address

		email = MIMEMultipart('related')
		email['Subject'] = subject
		email['From'] = sender
		email['To'] = reciever
		email['Message-ID'] = f'<{time.time()}.{uuid()}@{sender_domain}'
		email.preamble = subject

		if not html:
			html = txt

		email_body_text = MIMEText(txt.encode(encoding), 'plain', encoding)
		email_body_html = MIMEBase('text', 'html')
		email_body_html.set_payload(html.encode(encoding))
		encoders.encode_quopri(email_body_html)
		email_body_html.set_charset(encoding)

		email.attach(email_body_html)
		email.attach(email_body_text)

		if attachments:
			for image_id, image_obj in attachments.items():
				# Define the image's ID as referenced above
				image_obj.add_header('Content-ID', f'<{image_id}>')
				email.attach(image_obj)

		if sign:
			if (dkim_signature := self.sign_email(email, domain=sender_domain)):
				email["DKIM-Signature"] = dkim_signature
			else:
				print('Could not sign the email')

		if self.host and self.port:
			try:
				if self.tls:
					server = smtplib.SMTP_SSL(self.host, port=self.port, timeout=10)
				else:
					server = smtplib.SMTP(self.host, port=self.port, timeout=10)
			except socket.gaierror:
				print(f"Could not connect to pre-configured mail server {self.host}:{self.port}[tls={self.tls}]")
				return False

			if self.username:
				server.login(self.username, self.password)

			server.sendmail(sender_address, recieving_address, email.as_string().encode(encoding))
			server.quit()

			return True
		else:
			# context = ssl.create_default_context()
			context = ssl._create_unverified_context()
			resolver = dns.resolver.Resolver()
			resolver.nameservers = configuration['nameservers']
			resolver.timeout = 2

			for mx_record in resolver.query(recieving_domain, 'MX'):
				mail_server = mx_record.to_text().split()[1][:-1]
				try:
					server = smtplib.SMTP(mail_server, port=25, timeout=10) # 587 = TLS, 465 = SSL
					if server.starttls(context=context)[0] != 220:
						print('Could not start TLS.')
					
					server.sendmail(sender_address, recieving_address, email.as_string())
					server.quit()
				#		server.close()
					return True
				except Exception as e:
					print("Could not send email via: {}!!".format(mail_server))
					print("{}".format(e))

				if configuration['TRY_ONE_MAILSERVER']:
					break

		return False

	def sign_email(self, email, domain, selector='default'):
		if type(selector) != bytes: selector = bytes(selector, 'UTF-8')
		if type(domain) != bytes: domain = bytes(domain, 'UTF-8')

		if not pathlib.Path(os.environ['DKIM_KEY']).exists():
			print('Missing DKIM key: {DKIM_KEY}'.format(**os.environ))
			return None

		with open(os.environ['DKIM_KEY'], 'rb') as fh:
			dkim_private_key = fh.read()

		sig = dkim.sign(message=bytes(email.as_string(), 'UTF-8'),
						selector=selector,
						domain=domain,
						privkey=dkim_private_key,
						include_headers=["To", "From", "Subject"])

		return sig.lstrip(b"DKIM-Signature: ").decode('UTF-8')

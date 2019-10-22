#!/usr/bin/python

import smtplib, dns.resolver, os, logging, psutil, socket, ssl, dkim
from time import time, localtime
from hashlib import md5
from systemd.journal import JournalHandler
from sys import argv
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from os.path import isfile
from json import load as jload, dump as jdump

log = logging.getLogger('ssh-gateway')
log.addHandler(JournalHandler())
log.setLevel(logging.WARNING)

cache = {}
if isfile('/tmp/sshmailer.json'):
	with open('/tmp/sshmailer.json', 'r') as fh:
		try:
			cache = jload(fh)
		except:
			pass # Invalid format, probably a crash or something.

t = time()
meta = {
	'USER' : None,
	'IP' : None,
	'RESOLV' : None,
	'ENVIRON' : os.environ,
	'PARAMS' : argv,
	'USERS' : psutil.users(),
	'TIME' : '{}-{}-{} {}:{}:{}'.format(*localtime(t)),
	'RAW_TIME' : t,
	'SUBJECT' : None,
	'Message-ID' : '<{}.{}@domain.com>'.format(time(), md5(b'user@domain.com'+b'reciever@domain.com').hexdigest())
}

if 'PAM_TYPE' in os.environ and os.environ['PAM_TYPE'] == 'close_session':
	meta['SUBJECT'] = 'SSH Logout: {USER}@domain.com'.format(**meta)
else:
	meta['SUBJECT'] = 'SSH Login: {USER}@domain.com'.format(**meta)

if 'SSH_CONNECTION' in os.environ:
	meta['IP'] = os.environ['SSH_CONNECTION'].split()[0]
elif 'PAM_RHOST' in os.environ:
	meta['IP'] = os.environ['PAM_RHOST']
else:
	meta['IP'] = 'Unknown' # Hard to detect, maybe dump all of netstat -an | grep :22?
	log.warning("{}".format(os.environ))

if meta['IP'] in cache and time()-cache[meta['IP']]['time']<86400:
	meta['RESOLV'] = cache[meta['IP']]['resolved']
else:
	try:
		meta['RESOLV'] = socket.gethostbyaddr(meta['IP'])
		cache[meta['IP']] = {'time' : time(), 'resolved' : meta['RESOLV']}
	except:
		meta['RESOLV'] = meta['IP']

## Save the cached resolves for speed up reasons
with open('/tmp/sshmailer.json', 'w') as fh:
	try:
		jdump(cache, fh)
	except:
		pass

if 'USER' in os.environ:
	meta['USER'] = os.environ['USER']
elif 'PAM_USER' in os.environ:
	meta['USER'] = os.environ['PAM_USER']
else:
	meta['USER'] = 'root' # Just default and scare the shit out of us!
	log.warning("{}".format(os.environ))

log.warning("User {USER} Logged in from {IP}.".format(**meta))

## TODO: https://support.google.com/mail/answer/81126
## TODO:(DKIM) https://russell.ballestrini.net/quickstart-to-dkim-sign-email-with-python/
## TODO:(S/MIME) https://tools.ietf.org/doc/python-m2crypto/howto.smime.html
## TODO: https://support.rackspace.com/how-to/create-an-spf-txt-record/
##
## https://toolbox.googleapps.com/apps/checkmx/check?domain=domain.com&dkim_selector=
## https://github.com/PowerDNS/pdns/issues/2881

email = MIMEMultipart('alternative')
email['Subject'] = "SSH Login: {USER}@domain.com".format(**meta)
email['From'] = "SSH Guard <user@domain.com>"
email['To'] = "Anton Hvornum <reciever@domain.com>"
email['Message-ID'] = meta['Message-ID']
email.preamble = 'SSH Login {USER}@domain.com'.format(**meta)

t = time()
text = """\
The following information is available:
 * Remote-IP: {IP}
 * Resolves to: {RESOLV}
 * Time of occurance: {TIME} ({RAW_TIME})
 * Environment variable: {ENVIRON}
 * Parameters: {PARAMS}
 * Logged On Users: {USERS}
""".format(**meta)

html = """\
<html>
	<head>
		<title>{SUBJECT}</title>
	</head>
	<body>
		<div>
			<h3>The following information is available:</h3>
			<ul>
				<li><b><u>Remote-IP:</u></b> {IP}</li>
				<li><b>Resolves to:</b> {RESOLV}</li>
				<li><b>Time of occurance:</b> {TIME} ({RAW_TIME})</li>
				<li><b>Environment Variable:</b> {ENVIRON}</li>
				<li><b>Parameters:</b> {PARAMS}</li>
				<li><b>Logged On Users:</b> {USERS}</li>
			</ul>
		</div>
	</body>
</html>""".format(**meta)

email_body_text = MIMEText(text, 'plain')
email_body_html = MIMEBase('text', 'html')
email_body_html.set_payload(html)
encoders.encode_quopri(email_body_html)
email_body_html.set_charset('UTF-8')

email.attach(email_body_text)
email.attach(email_body_html)

with open("/etc/sshmailer/sshmailer.pem", 'rb') as fh:
	dkim_private_key = fh.read()

headers = ["To", "From", "Subject"]
sig = dkim.sign(message=bytes(email.as_string(), 'UTF-8'), selector=b"default", domain=b"domain.com", privkey=dkim_private_key, include_headers=headers)
email["DKIM-Signature"] = sig.lstrip(b"DKIM-Signature: ").decode('UTF-8')

context = ssl.create_default_context()
for mx_record in dns.resolver.query('gmail.com', 'MX'):
	mail_server = mx_record.to_text().split()[1][:-1]
	try:
		server = smtplib.SMTP(mail_server, port=25, timeout=10) # 587 = TLS, 465 = SSL
		if server.starttls(context=context)[0] != 220:
			raise ValueError('Could not start TLS.')
		#server = smtplib.SMTP_SSL(mail_server)
		server.sendmail('user@domain.com', 'reciever@domain.com', email.as_string())
		server.quit()
	#		server.close()
		break
	except Exception as e:
		log.warning("Could not notify our chief of command @ {}!!".format(mail_server))
		log.warning("{}".format(e))


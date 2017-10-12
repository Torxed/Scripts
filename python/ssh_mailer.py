#!/usr/bin/python

import smtplib, dns.resolver, os, logging, psutil, socket
from time import time
from hashlib import md5
from systemd.journal import JournalHandler
from sys import argv
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

DOMAIN = 'domain.com'
FROM = 'ssh@{}'.format(DOMAIN)
FROM_FANCY = 'SSH Guard <{}>'.format(FROM)
TO_DOMAIN = 'reciever.com'
TO = 'user@{}'.format(TO_DOMAIN)
TO_FANCY = 'Users Name <{}>'.format(TO)
PROXY_MAIL = None

log = logging.getLogger('ssh-gateway')
log.addHandler(JournalHandler())
log.setLevel(logging.WARNING)

if 'SSH_CONNECTION' in os.environ:
	IP = os.environ['SSH_CONNECTION'].split()[0]
elif 'PAM_RHOST' in os.environ:
	IP = os.environ['PAM_RHOST']
else:
	IP = 'Unknown' # Hard to detect, maybe dump all of netstat -an | grep :22?
	log.warning("{}".format(os.environ))

if 'USER' in os.environ:
	USER = os.environ['USER']
elif 'PAM_USER' in os.environ:
	USER = os.environ['PAM_USER']
else:
	USER = 'root' # Just default and scare the shit out of us!
	log.warning("{}".format(os.environ))

try:
	RESOLV = socket.gethostbyaddr(IP)
except:
	RESOLV = None

log.warning("User {} Logged in from {}.".format(USER, IP))

email = MIMEMultipart('alternative')
email['Subject'] = "SSH Login: {}@{}".format(USER, DOMAIN)
email['From'] = "{} <{}>".format(FROM_FANCY, FROM)
email['To'] = "{} <{}@{}>".format(TO_FANCY, TO, TO_DOMAIN)
email['Message-ID'] = '{}-{}'.format(time(), md5(b'{}{}@{}'.format(FROM, TO, TO_DOMAIN)).hexdigest())
email.preamble = 'SSH Login {}@{}'.format(USER, DOMAIN)

text = """\
The following information is available:
 * Remote-IP: {IP}
 * Resolves to: {RESOLV}
 * Environment variable: {ENVIRON}
 * Parameters: {PARAMS}
 * Logged On Users: {USERS}
""".format(IP=IP, RESOLV=RESOLV, ENVIRON=os.environ, PARAMS=argv, USERS=psutil.users())
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
				<li><b>Time of occurance:</b> {TIME}</li>
				<li><b>Environment Variable:</b> {ENVIRON}</li>
				<li><b>Parameters:</b> {PARAMS}</li>
				<li><b>Logged On Users:</b> {USERS}</li>
			</ul>
		</div>
	</body>
</html>""".format(IP=IP, RESOLV=RESOLV, TIME=time(), ENVIRON=os.environ, PARAMS=argv, USERS=psutil.users(), SUBJECT="SSH Login: {}@{}".format(USER, DOMAIN))

email_body_text = MIMEText(text, 'plain')

#email_body_html = MIMEText(html, 'html')
email_body_html = MIMEBase('text', 'html')
email_body_html.set_payload(html)
encoders.encode_quopri(email_body_html)
email_body_html.set_charset('UTF-8')

email.attach(email_body_text)
email.attach(email_body_html)

if not PROXY_MAIL:
	for mx_record in dns.resolver.query(TO_DOMAIN, 'MX'):
		mail_server = mx_record.to_text().split()[1][:-1]
		try:
			server = smtplib.SMTP(mail_server)
			server.sendmail(FROM, '{}@{}'.format(TO), email.as_string())
			server.close()
			break
		except Exception as e:
			log.warning("Could not notify our chief of command @ {}!!".format(mail_server))
			log.warning("{}".format(e))
else:
	mail_server = mx_record.to_text().split()[1][:-1]
	try:
		server = smtplib.SMTP(PROXY_MAIL)
		server.sendmail(FROM, '{}@{}'.format(TO), email.as_string())
		server.close()
		break
	except Exception as e:
		log.warning("Could not notify our chief of command @ {}!!".format(mail_server))
		log.warning("{}".format(e))

#!/usr/bin/python

## Requirements:
#  * python-dnspython
#  * python-dkim
#  * python-pygeoip

import smtplib, dns.resolver, os, logging, psutil, socket, ssl, dkim, json
from time import time, localtime
from hashlib import md5
from systemd.journal import JournalHandler
from sys import argv
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from os.path import isfile, dirname, isdir
from json import load as jload, dump as jdump

log = logging.getLogger('ssh-gateway')
log.addHandler(JournalHandler())
log.setLevel(logging.WARNING)

## Load the cached RESOLVE hits from disk:
cache = {}
if isfile('/tmp/sshmailer.json'):
	with open('/tmp/sshmailer.json', 'r') as fh:
		try:
			cache = jload(fh)
		except:
			pass # Invalid format, probably a crash or something.

def get_ip():
	if 'SSH_CONNECTION' in os.environ:
		return os.environ['SSH_CONNECTION'].split()[0]
	elif 'PAM_RHOST' in os.environ:
		return os.environ['PAM_RHOST']
	
	log.warning("Missing remote IP in environment variables: {}".format(os.environ))
	return '127.0.0.1' # Hard to detect, maybe dump all of netstat -an | grep :22?

def country(ip):
	if isfile(configuration['GEOIP_DB']):
		import pygeoip
		gi = pygeoip.GeoIP(configuration['GEOIP_DB'])
		result = gi.country_name_by_addr(ip)
		if result == '' or not result:
			result = 'Unknown Country'
		return result
	
	log.warning("Missing GeoIP database at: {GEOIP_DB}".format(**configuration))
	return "Unknown"

def resolv(ip):
	if ip in cache and time()-cache[ip]['time']<86400:
		return cache[ip]['resolved']

	try:
		result = socket.gethostbyaddr(ip)
		if result:
			result = result[0]
			#result = ':'.join(str(x) for x in result)
		cache[ip] = {'time' : time(), 'resolved' : result}
		return cache[ip]['resolved']
	except:
		pass
	
	return ip

def load_text_template():
	template = """\
The following information is available:
 * Remote-IP: {IP} [{COUNTRY}] ({RESOLV})
 * Time of occurance: {TIME} ({RAW_TIME})
 * Environment variable: {ENVIRON}
 * Parameters: {PARAMS}
 * Logged On Users: {USERS}
"""
	if not isdir(dirname(configuration['TEXT_TEMPLATE'])):
		return template.format(**configuration)

	if not isfile(configuration['TEXT_TEMPLATE']):
		with open(configuration['TEXT_TEMPLATE'], 'w') as fh:
			fh.write(template)

	with open(configuration['TEXT_TEMPLATE'], 'r') as fh:
		return fh.read().format(**configuration)

def load_html_template():
	template = """\
<html>
	<head>
		<title>{SUBJECT}</title>
	</head>
	<body>
		<div>
			<h3>The following information is available:</h3>
			<ul>
				<li><b><u>Remote-IP:</u></b> {IP} [{COUNTRY}] ({RESOLV})</li>
				<li><b>Time of occurance:</b> {TIME} ({RAW_TIME})</li>
				<li><b>Environment Variable:</b> {ENVIRON}</li>
				<li><b>Parameters:</b> {PARAMS}</li>
				<li><b>Logged On Users:</b> {USERS}</li>
			</ul>
		</div>
	</body>
</html>"""

	if not isdir(dirname(configuration['HTML_TEMPLATE'])):
		return template.format(**configuration)

	if not isfile(configuration['HTML_TEMPLATE']):
		with open(configuration['HTML_TEMPLATE'], 'w') as fh:
			fh.write(template)

	with open(configuration['HTML_TEMPLATE'], 'r') as fh:
		return fh.read().format(**configuration)

def sign_email(email, selector='default', domain=None):
	if not domain: domain = configuration['DOMAIN']
	if type(selector) != bytes: selector = bytes(selector, 'UTF-8')
	if type(domain) != bytes: domain = bytes(domain, 'UTF-8')

	if not isdir(dirname(configuration['DKIM_KEY'])):
		log.warning('Missing DKIM key: {DKIM_KEY}'.format(**configuration))
		return None 
	if not isfile(configuration['DKIM_KEY']):
		log.warning('Missing DKIM key: {DKIM_KEY}'.format(**configuration))
		return None

	with open(configuration['DKIM_KEY'], 'rb') as fh:
		dkim_private_key = fh.read()

	sig = dkim.sign(message=bytes(email.as_string(), 'UTF-8'),
					selector=selector,
					domain=domain,
					privkey=dkim_private_key,
					include_headers=["To", "From", "Subject"])

	return sig.lstrip(b"DKIM-Signature: ").decode('UTF-8')

def get_logedonuser():
	if 'USER' in os.environ:
		return os.environ['USER']
	elif 'PAM_USER' in os.environ:
		return os.environ['PAM_USER']
	else:
		log.warning("Missing USER definition in environment: {}".format(os.environ))
	
	return 'root' # Just a default to scare the shit out of us!

t = time()
configuration = {
	'DOMAIN' : 'example.com',
	'SSH_MAIL_USER_FROM' : 'ssh', # ssh@example.com
	'SSH_MAIL_USER_TO' : 'reciever', # reciever@example.com
	'SSH_MAIL_USER_TODOMAIN' : 'example.com',
	'SSH_MAIL_TO_REALNAME' : 'Recievers Name'
	'RAW_TIME' : t,
	'TIME' : '{}-{}-{} {}:{}:{}'.format(*localtime(t)),
	'SUBJECT' : None,
	'COUNTRY' : None,
	'USER' : None,
	'IP' : None,
	'RESOLV' : None,
	'ENVIRON' : dict(os.environ),
	'PARAMS' : argv,
	'USERS' : psutil.users(),
	'TRY_ONE_MAILSERVER' : False,
	'TEXT_TEMPLATE' : '/etc/sshmailer/text.template',
	'HTML_TEMPLATE' : '/etc/sshmailer/html.template',
	'DKIM_KEY' : "/etc/sshmailer/sshmailer.pem",
	'GEOIP_DB' : '/usr/share/GeoIP/GeoIP.dat'
}

configuration['USER'] = get_logedonuser()
configuration['HASH'] = md5(bytes('{SSH_MAIL_USER_FROM}@{DOMAIN}+{SSH_MAIL_USER_TO}@{SSH_MAIL_USER_TODOMAIN}'.format(**configuration), 'UTF-8')).hexdigest()
configuration['Message-ID'] = '<{RAW_TIME}.{HASH}@{DOMAIN}>'.format(**configuration)
configuration['SUBJECT'] = 'SSH Session: {USER}@{DOMAIN}'.format(**configuration)

configuration['IP'] = get_ip()
configuration['RESOLV'] = resolv(configuration['IP'])
configuration['COUNTRY'] = country(configuration['IP'])
if configuration['COUNTRY'].lower() != 'sweden':
	configuration['COUNTRY'] = '<font color="red">{COUNTRY}</font>'.format(**configuration)

log.warning("User {USER} Logged in from {IP}.".format(**configuration))

## Save the cached resolves for speed up reasons
with open('/tmp/sshmailer.json', 'w') as fh:
	try:
		jdump(cache, fh)
	except:
		pass

## TODO: https://support.google.com/mail/answer/81126
## TODO:(DKIM) https://russell.ballestrini.net/quickstart-to-dkim-sign-email-with-python/
## TODO:(S/MIME) https://tools.ietf.org/doc/python-m2crypto/howto.smime.html
## TODO: https://support.rackspace.com/how-to/create-an-spf-txt-record/
##
## https://toolbox.googleapps.com/apps/checkmx/check?domain={DOMAIN}&dkim_selector=
## https://github.com/PowerDNS/pdns/issues/2881

email = MIMEMultipart('alternative')
email['Subject'] = configuration['SUBJECT']
email['From'] = "SSH Guard <{SSH_MAIL_USER_FROM}@{DOMAIN}>".format(**configuration)
email['To'] = "{SSH_MAIL_TO_REALNAME} <{SSH_MAIL_USER_TO}@{SSH_MAIL_USER_TODOMAIN}>".format(**configuration)
email['Message-ID'] = configuration['Message-ID']
email.preamble = configuration['SUBJECT']

text = load_text_template()
html = load_html_template()


email_body_text = MIMEText(text, 'plain')
email_body_html = MIMEBase('text', 'html')
email_body_html.set_payload(html)
encoders.encode_quopri(email_body_html)
email_body_html.set_charset('UTF-8')

email.attach(email_body_text)
email.attach(email_body_html)

email["DKIM-Signature"] = sign_email(email)

context = ssl.create_default_context()
for mx_record in dns.resolver.query('gmail.com', 'MX'):
	mail_server = mx_record.to_text().split()[1][:-1]
	try:
		server = smtplib.SMTP(mail_server, port=25, timeout=10) # 587 = TLS, 465 = SSL
		if server.starttls(context=context)[0] != 220:
			log.warning('Could not start TLS.')
		
		server.sendmail('{SSH_MAIL_USER_FROM}@{DOMAIN}'.format(**configuration), '{SSH_MAIL_USER_TO}@{SSH_MAIL_USER_TODOMAIN}'.format(**configuration), email.as_string())
		server.quit()
	#		server.close()
		break
	except Exception as e:
		log.warning("Could not send email via: {}!!".format(mail_server))
		log.warning("{}".format(e))

	if configuration['TRY_ONE_MAILSERVER']:
		break


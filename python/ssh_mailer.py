#!/usr/bin/python

import smtplib, dns.resolver, os, logging
from time import time
from hashlib import md5
from systemd.journal import JournalHandler
from sys import argv
from email.mime.multipart import MIMEMultipart

IP = os.environ['SSH_CONNECTION'].split()[0]
USER = os.environ['USER']

DOMAIN = 'domain.com'
FROM = 'ssh@'+DOMAIN
FROM_FANCY = 'SSH Guard'
TO = 'reciever'
TO_DOMAIN = 'gmail.com'
TO_FANCY = 'Users Name'

log = logging.getLogger('ssh-gateway')
log.addHandler(JournalHandler())
log.setLevel(logging.WARNING)
log.warning("User {} Logged in from {}.".format(USER, IP))

email = MIMEMultipart()
email['Subject'] = "SSH Login: {}@{}".format(USER, DOMAIN)
email['From'] = "{} <{}>".format(FROM_FANCY, FROM)
email['To'] = "{} <{}@{}>".format(TO_FANCY, TO, TO_DOMAIN)
email['Message-ID'] = '{}-{}'.format(time(), md5(b'{}{}@{}'.format(FROM, TO, TO_DOMAIN)).hexdigest())
email.preamble = 'SSH Login {}@{}'.format(USER, DOMAIN)

for mx_record in dns.resolver.query(TO_DOMAIN, 'MX'):
	mail_server = mx_record.to_text().split()[1][:-1]
	try:
		server = smtplib.SMTP(mail_server)
		server.sendmail(FROM, '{}@{}'.format(TO, TO_DOMAIN), email.as_string())
		server.close()
		break
	except Exception as e:
		log.warning("Could not notify our chief of command @ {}!!".format(mail_server))
		log.warning("{}".format(e))

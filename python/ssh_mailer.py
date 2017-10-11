#!/usr/bin/python

import smtplib, dns.resolver, os, logging
from time import time
from hashlib import md5
from systemd.journal import JournalHandler
from sys import argv
from email.mime.multipart import MIMEMultipart

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

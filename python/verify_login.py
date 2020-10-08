#!/usr/bin/python
#-> /etc/pam.d/sshd: session   required  pam_exec.so          /usr/bin/verify_login.py

import dns.resolver # dnspython (https://www.dnspython.org/)
import dkim
import os, time, hashlib, ssl, smtplib, email, hashlib, http.client, json, logging
from systemd.journal import JournalHandler
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase

CONFIG = {
	'domain' : 'hvornum.se', # Mail is sent and signed as this domain
	'domain_priv_key' : "/etc/pempath/keys/hvornum.se.pem",
	'domain_selector' : 'default'
}
USERS = {
	'username1' : {'mail' : 'user1-email@gmail.com', 'real_name' : 'Anton Hvornum'},
}

# get an instance of the logger object this module will use
logger = logging.getLogger(__name__)
# instantiate the JournaldLogHandler to hook into systemd
journald_handler = JournalHandler()
# set a formatter to include the level name
journald_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
# add the journald handler to the current logger
logger.addHandler(journald_handler)
# optionally set the logging level
logger.setLevel(logging.DEBUG)


def gen_uid(seed_len=24):
	return hashlib.sha512(os.urandom(seed_len)).hexdigest()

def sign_email(email, domain='hvornum.se', domain_priv_key="/etc/pempath/keys/hvornum.se.pem", selector='default'):
	if not domain: domain = domain
	if type(selector) != bytes: selector = bytes(selector, 'UTF-8')
	if type(domain) != bytes: domain = bytes(domain, 'UTF-8')

	if not os.path.isfile(domain_priv_key):
		logger.error(f'Missing private DKIM key: {domain_priv_key}')
		return None

	with open(domain_priv_key, 'rb') as fh:
		dkim_private_key = fh.read()

	sig = dkim.sign(message=bytes(email.as_string(), 'UTF-8'),
					selector=selector,
					domain=domain,
					privkey=dkim_private_key,
					include_headers=["To", "From", "Subject"])

	return sig.lstrip(b"DKIM-Signature: ").decode('UTF-8')

def txt_template(user, ip, uid=None, session='open_session'):
	if not uid: uid = gen_uid()
	if session == 'open_session':
		return f'To verify your login from {ip}, please click this link: https://webapi.hvornum.se/ssh-verify/?uid={uid}'

def html_template(user, ip, uid=None, session='open_session'):
	if not uid: uid = gen_uid()
	if session == 'open_session':
		return f"""
			<html>
			<body>
				To verify your login from <b>{ip}</b>, please click this link: <a href="https://webapi.hvornum.se/ssh-verify/?uid={uid}">https://webapi.hvornum.se/ssh-verify/?uid={uid}</a>
			</body>
			</html>
		""".replace('\t\t\t', '')

# 'PAM_USER': 'anton', 'PAM_TTY': 'ssh', 'PAM_RHOST': '89.253.87.215', 'PAM_TYPE': 'open_session'
ip = os.environ.get('PAM_RHOST')
pam_type = os.environ.get('PAM_TYPE')
uid = gen_uid()

conn = http.client.HTTPSConnection("webapi.hvornum.se")
conn.request("PUT", f"/ssh-reg/?uid={uid}")
res = conn.getresponse()
if res.status == 204:
	if (user := os.environ.get('PAM_USER')) in USERS and (text := txt_template(user, ip, uid, session=pam_type)) and (html := html_template(user, ip, uid, session=pam_type)):
		output.write(f"User logging in: {user} | mailing: {USERS[user]['mail']}")

		mail_time = time.time()
		mail_hash = hashlib.md5(bytes(f"ssguard@{CONFIG['domain']}+{USERS[user]['mail']}", 'UTF-8')).hexdigest()

		mail_struct = MIMEMultipart('alternative')
		mail_struct['Subject'] = 'Verify SSH login'
		mail_struct['From'] = f"SSH Guard <sshguard@{CONFIG['domain']}>"
		mail_struct['To'] = f"{USERS[user]['real_name']} <{USERS[user]['mail']}>"
		mail_struct['Message-ID'] = f"<{mail_time}.{mail_hash}@{CONFIG['domain']}>"
		mail_struct.preamble = 'Verify SSH login'

		email_body_text = MIMEText(text, 'plain')
		email_body_html = MIMEBase('text', 'html')
		email_body_html.set_payload(html)
		email.encoders.encode_quopri(email_body_html)
		email_body_html.set_charset('UTF-8')

		mail_struct.attach(email_body_text)
		mail_struct.attach(email_body_html)

		mail_struct["DKIM-Signature"] = sign_email(mail_struct, CONFIG['domain'], CONFIG['domain_priv_key'], CONFIG['domain_selector'])

		context = ssl.create_default_context()
		for mx_record in dns.resolver.query(USERS[user]['mail'].split('@', 1)[1], 'MX'):
			mail_server = mx_record.to_text().split()[1][:-1]
			try:
				server = smtplib.SMTP(mail_server, port=25, timeout=5) # 587 = TLS, 465 = SSL
				if server.starttls(context=context)[0] != 220:
					server.close()
					logger.error(f'Could not initiate TLS with the mailserver: {mail_server}')
					continue
				
				server.sendmail(f"SSH Guard <sshguard@{CONFIG['domain']}>", f"{USERS[user]['mail']}", mail_struct.as_string())
				server.quit()
			#		server.close()
				break
			except Exception as e:
				logger.error(f"Could not send email via: {mail_server}")
				logger.error(e)

			exit(1)

		logger.info(f"Waiting for verification for login {ip} ({user}) [{uid}]")
		for i in range(30):
			conn = http.client.HTTPSConnection("webapi.hvornum.se")
			conn.request("GET", f"/ssh-check/?uid={uid}")
			res = conn.getresponse()
			#print(res.status, res.reason, res.read())

			if res.status == 200:
				data = json.loads(res.read().decode('UTF-8'))
				if 'status' in data and data['status'] == True:
					exit(0)
			time.sleep(1)

		logger.warning(f"User never verified via e-mail {ip} ({user}) [{uid}]")
	else:
		logger.error(f"Not enough environment data.")
else:
	logger.error(f"Could not register UID {uid} on connection from {ip} ({user})")
exit(1)
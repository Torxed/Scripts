from json import loads, dumps
import psycopg2, psycopg2.extras
from subprocess import Popen, STDOUT, PIPE

con = psycopg2.connect("dbname=PowerDNS user=PowerDNS_User", cursor_factory=psycopg2.extras.RealDictCursor)
cur = con.cursor()

def cmd(c):
	handle = Popen(c, shell=True, stdout=PIPE, stderr=STDOUT, stdin=PIPE)
	while handle.poll() is None:
		row = handle.stdout.readline().decode('UTF-8')
		if len(row) <= 0: continue

		## Ugly assumptions that the row starts with JSON data but ends with \n (according to the plugin, but this might change)
		if row[0] == '{' and row[-1] == '\n':
			challenge = loads(row[:-1])
			yield challenge
		elif 'error' in row.lower():
			print('[E]', row)
			yield None

## Create a domain->id dictionary.
DOMAINS = {}
cur.execute("SELECT * FROM domains;")
if cur.rowcount:
	for row in cur:
		DOMAINS[row['name']] = row['id']

## Create the '-d "example" -d "test.example.com"' string.
domain_str = ''
cur.execute("SELECT * FROM records WHERE type='A';")
if cur.rowcount:
	for row in cur:
		domain_str += ' -d "' + row['name'] + '"'

## Start the signing process.
for challenge in cmd('certbot --staging --text --agree-tos --config-dir /tmp/letsencrypt --work-dir /tmp/letsencrypt --logs-dir /tmp/letsencrypt --email anton@domain.com --expand --renew-by-default --configurator certbot-external-auth:out --certbot-external-auth:out-public-ip-logging-ok'+domain_str+' --preferred-challenges dns certonly'):
	if not challenge: continue

	# {'cmd': 'perform_challenge', 'type': 'dns-01', 'domain': 'matrin.xn--frvirrad-n4a.se', 'token': 'Lb-mYenvipIpxqsVFL-coSl3PgbH2iXRee5ERYjFvn4', 'validation': 'DbCnmL0vIHxb1WvGtc1nq3DO-tWwl6iT0y9ufa5jrJc', 'txt_domain': '_acme-challenge.matrin.xn--frvirrad-n4a.se', 'key_auth': 'Lb-mYenvipIpxqsVFL-coSl3PgbH2iXRee5ERYjFvn4.4fvJYRjjbIw6fZrC5RC2T-4IMwQx94sB6LY6m3YfE34'}
	if 'cmd' in challenge and challenge['cmd'] == 'perform_challenge':
		domain_part = '.'.join(challenge['domain'].split('.')[-2:])
		print('[Updating]', challenge['txt_domain'],'=',challenge['token'])

		cur.execute("INSERT INTO records (domain_id, name, type, content, ttl) VALUES({domain_id}, '{txt_record}', 'TXT', '{token}', 60) ON CONFLICT (name, type) DO UPDATE SET content='{token}';".format(domain_id=DOMAINS[domain_part], txt_record=challenge['txt_domain'], token=challenge['token']))
		con.commit()
	else:
		print('Unkown challenge:')
		print(challenge)

cur.execute("SELECT * FROM records WHERE type='TXT';")
if cur.rowcount:
	for row in cur: print(row)

for domain in DOMAINS:
	## Post successful
	with open('/etc/lighttpd2/certs/'+domain+'.pem', 'wb') as web:
		with open('/tmp/letsencrypt/live/'+domain+'/fullchain.pem', 'rb') as cert:
			web.write(cert.read())
		with open('/tmp/letsencrypt/live/'+domain+'/privkey.pem', 'rb') as key:
			web.write(key.read())

# from synapse:
# scp user@domain:/tmp/letsencrypt/live/domain/cert.pem /etc/synapse/
# scp user@domain:/tmp/letsencrypt/live/domain/privkey.pem /etc/synapse/

print('sudo systemctl restart lighttpd2')

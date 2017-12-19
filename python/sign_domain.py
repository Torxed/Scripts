from subprocess import Popen, STDOUT, PIPE
from json import loads, dumps
import psycopg2, psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from time import sleep

db_domains = {}

con = psycopg2.connect("dbname=database user=username")
con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT * FROM domains;")
for row in cur:
	db_domains[row['name']] = row['id']

domains = ['domain.se',
			'sub.domain.se'
		  ]
cmd = 'certbot --text --agree-tos --email root@domain.se --expand --renew-by-default --configurator certbot-external-auth:out --certbot-external-auth:out-public-ip-logging-ok -d {domains} certonly'.format(domains=' -d '.join(domains))

handle = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
while handle.poll() is None:
	line = handle.stdout.readline().strip().decode('UTF-8')
	if len(line) == 0:
		sleep(0.25)
		continue
	print('DEBUG:', line)
	if '{' in line and '}' in line and 'txt_domain' in line:
		data = loads(line)
		if 'validation' in data:
			cur.execute("UPDATE records SET content='{data}' WHERE name='{record}';".format(data=data['validation'], record=data['txt_domain']))
			if not cur.rowcount:
				domain = '.'.join(data['domain'].split('.')[-2:])
				cur.execute("INSERT INTO records (domain_id, name, type, content, ttl) VALUES ({id}, '{name}', 'TXT', '{content}', {ttl});".format(id=db_domains[domain], name=data['txt_domain'], content=data['validation'], ttl=60))
				print('Inserted {} for domain {}'.format(data['txt_domain'], domain))
			else:
				print('Updated {}'.format(data['txt_domain']))
			handle.stdin.write(b'\n')
			handle.stdin.flush()

print(handle.stdout.read().decode('UTF-8'))
handle.stdout.close()
handle.stdin.close()

# /etc/letsencrypt/live/domain/cert#.pem > /etc/certs/domain.pem
# /etc/letsencrypt/live/domain/privkey#.pem >> /etc/certs/domain.pem

import psycopg2, psycopg2.extras, sys
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

con = psycopg2.connect("dbname=database user=username")
con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT * FROM domains;")

db_domains = {}
for row in cur:
	db_domains[row['name']] = row['id']

domain = sys.argv[1]
subdomains = None

if len(sys.argv) > 2:
	subdomains = sys.argv[2:]

if not domain in db_domains:
	cur.execute("SELECT id FROM domains ORDER BY id DESC LIMIT 1;")
	for row in cur:
		domain_id = row['id']+1
	
	print('Creating domain:', domain)
	cur.execute("INSERT INTO domains (id, name, type) VALUES ({id}, '{name}', '{type}');".format(id=domain_id, name=domain, type='NATIVE'))
	cur.execute("INSERT INTO records (domain_id, name, type, content, ttl) VALUES ({id}, '{name}', 'SOA', '{name} root@{name} 1', 360);".format(id=domain_id, name=domain))
	cur.execute("INSERT INTO records (domain_id, name, type, content, ttl) VALUES ({id}, '{name}', 'NS', '{name}', 60);".format(id=domain_id, name=domain))
	cur.execute("INSERT INTO records (domain_id, name, type, content, ttl) VALUES ({id}, '{name}', 'A', '{ip}', 60);".format(id=domain_id, name=domain, ip=ip))
else:
	domain_id = db_domains[domain]
	
if subdomains:
	for subdomain in subdomains:
		print('Adding subdomain:', subdomain)
		cur.execute("INSERT INTO records (domain_id, name, type, content, ttl) VALUES ({id}, '{name}', 'A', '{ip}', 60);".format(id=domain_id, name=subdomain, ip=ip))

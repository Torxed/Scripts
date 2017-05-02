
## == A quick test to see where and what type of logic is faster
##    for comparing a arbitrary web-request (REST API) with a known
##    database of files/functions to call depending on the URL given.
##
##    I will call these two subdicts and listdict, because one is a
##    actual dict structure and the other more resembles a list.
##
##    If the request is compared against a subset either 1000 subdicts
##    or 1000 listdicts, the listdict wins - this is because it takes less
##    time to iterate over 1000 unique keys than it takes to iterate
##    through a hashmap of 1000 keys to find the matching subdict.

model = '/_matrix/r0/client/room/!something:domain.com/messages'

from time import *

def test_func():
	return True

d = {}
d['_matrix'] = {}
d['_matrix']['r0'] = {}
d['_matrix']['r0']['client'] = {}
d['_matrix']['r0']['client']['room'] = test_func

for i in range(1000):
	d['_matrix']['r0']['test'+str(i)] = test_func

start = time()
for i in range(1000000):
	tmp = model.split('/')
	p = d
	for key in tmp:
		if key in p:
			if type(p[key]) == dict:
				p = p[key]
			else:
				x = p[key]()
				break

print('List->Dict conversion took',time()-start, 'seconds to complete')

## == This should in theory be quite slow, because most of the strings
##    have a matching start - but to be fair, i left those here.
##    Even then, if the known paths is below 1000, this will still be
##    faster than trying to navigate down a hashmap to find the proper func.
##    so iterate+string-comparison is quite fast <1000 keys.

d = {}
d['/_matrix/r0/client/room'] = test_func
d['/_matrix/r0/client/profile'] = test_func
d['/_matrix/r0/client/messages'] = test_func
d['/_matrix/r0/client/something'] = test_func
d['/_matrix/r0/client/wham'] = test_func
d['/_matrix/r0/client/external'] = test_func
d['/_matrix/r0/client/whatever'] = test_func
d['/_matrix/r0/client/testmore'] = test_func
d['/_matrix/r0/client/apples'] = test_func
d['/_matrix/r0/client/cats'] = test_func
d['/_matrix/r0/client/water'] = test_func
for i in range(1000):
	d['/_matrix/r0/client/random'+str(i)] = test_func

start = time()
for k in d:
	if k in model:
		test_func()
		break
print('Dict->Str conversion took', time()-start, 'seconds to complete')
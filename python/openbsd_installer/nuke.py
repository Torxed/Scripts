#!/usr/local/bin/python
import sys
from subprocess import Popen, PIPE, STDOUT
from random import randint
from time import sleep

def e(what):
	x = Popen(what, shell=True, stdout=PIPE, stderr=STDOUT, stdin=PIPE)
	while x.poll == None:
		sleep(0.01)
	x.stdout.close()
	x.stdin.close()

print ' | Erasing keys from memory'
e('bioctl -d sd1')
print ' | Zeroing first blocks'
e('dd if=/dev/zero of=/dev/rsd0c bs=4096 count=1024')
print ' | Randomzing first blocks'
e('dd if=/dev/random of=/dev/rsd0c bs=4096 count=1024')

print ' | Zeroing midpoint'
e('dd if=/dev/zero of=/dev/rsd0c bs=4096 count=4096 seek=8192')
print ' | Randomizing midpoint'
e('dd if=/dev/random of=/dev/rsd0c bs=4096 count=4096 seek=8192')

print ' | Initializing last-resort nuke!'
sys.stdout.write(' | Iteration:  ')
i = 0
engine = ['/dev/zero', '/dev/urandom', '/dev/random']
while 1:
	sys.stdout.write('\b'*len(str(i)))
	i += 1
	sys.stdout.write(str(i))
	sys.stdout.flush()
	e('dd if=' + engine[i%len(engine)-1] + ' of=/dev/rsd0c bs=4096 count=1024 seek=' + str(randint(0, 90000)))

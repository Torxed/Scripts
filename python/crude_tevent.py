from time import time, sleep
from threading import *

speed = 1.0

class worker(Thread):
	def __init__(self, *args, **kvargs):
		Thread.__init__(self)
		self.ags = args
		for key, val in kvargs.items():
			self.__dict__[key] = val
		self.mainThread = None
		for t in enumerate():
			if t.name == 'MainThread':
				self.mainThread = t
				break
		self.start()

	def main(self):
		return self.mainThread.isAlive()

	def run(self):
		pass

class timer():
	def __init__(self):
		self.started = time()

	def ended(self):
		print(time()-self.started)

class event(worker):
	def __init__(self):
		super(event, self).__init__(queue={})

		## This event loop can generate 750 000 iterations per second.
		## It should be good enough. (i7 tho, running a slim Arch Linux).

	def register(self, ms, func):
		# Microseconds
		t = (time()*1000)+(ms)
		rounded_t = int(t)

		if not rounded_t in self.queue:
			self.queue[rounded_t] = {t : {'funcs' : [func], 'delay' : ms}}
		elif not t in self.queue[rounded_t]:
			self.queue[rounded_t][t] = {'funcs' : [func], 'delay' : ms}
		else:
			self.queue[rounded_t][t]['funcs'].append(func)

		#print('', time()*1000)
		#sleep(1)
		#print('', time()*1000)
		#print(self.queue)

	def run(self):
		now = time()*1000
		while self.main():
			#elapsed = time() - last
			#crude_elapse = int(elapsed*1000)
			#now = time()*1000
			now += 0.001
			rounded_now = int(now)
			if rounded_now in self.queue:
				for ms, settings in list(self.queue[rounded_now].items()):
					if ms >= now:
						del(self.queue[rounded_now])
						for f in settings['funcs']:
							f()
							## Either register each individual function, or make sure
							## that register() takes a list of functions as parameter.
							## These functions can not be blocking either...
							self.register(settings['delay'], f) # settings['funcs']
			sleep(0.001)


counter = 0
def x():
	global counter
	counter += 1
	#print('I got executed')

e = event()
e.register(10, x)

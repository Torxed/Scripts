from time import time, sleep
from threading import *

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

class test(worker):
	def __init__(self):
		super(test, self).__init__(nob=0, delay=0.5)
		print(self.delay) # This doesn't get printed first

	def calc_next(self):
		return time()+self.delay

	def run(self):
		next_hop = self.calc_next()

		while self.main():
			t = time()
			if next_hop >= t:
				self.nob = (self.nob + 1) %2
				next_hop = self.calc_next()
				print(self.nob)

			sleep(self.delay)

c = test()
sleep(60)

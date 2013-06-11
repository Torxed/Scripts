import time
from subprocess import PIPE, Popen, STDOUT

output_line = Import('output_line')

class run():
	def __init__(self, cmd):
		self.cmd = cmd
		self.stdout = None
		self.stdin = None
		self.x = None
		self.run()

	def run(self):
		self.x = Popen(self.cmd, shell=True, stdout=PIPE, stderr=STDOUT, stdin=PIPE)
		self.stdout, self.stdin = self.x.stdout, self.x.stdin

	def wait(self, text):
		i = 0
		self.output = output_line(text)
		graphics = ['/', '-', '\\', '|']
		while self.x.poll() == None:
			self.output.replace(graphics[i%len(graphics)-1])
			i += 1
			time.sleep(0.2)

		self.output.replace(' ')
		if self.poll() in (0, '0'):
			self.output.beginning(' [OK] ')
			self.close()
			return True
		else:
			self.output.beginning(' ![Error] ')
			self.close()
			return False

	def write(self, what, enter=True):
		if enter:
			if len(what) <= 0 or not what[-1] == '\n':
				what += '\n'
		self.stdin.write(what)

	def poll(self):
		return self.x.poll()

	def getline(self):
		while True:
			line = self.stdout.readline()
			if len(line) <= 0: break
			yield line

	def getlines(self):
		return self.stdout.readlines()

	def close(self):
		self.stdout.close()
		self.stdin.close()

import sys

def output(what, flush=True):
	sys.stdout.write(what)
	if flush:
		sys.stdout.flush()

class output_line():
	def __init__(self, starter=''):
		self.len = 0
		self.line = starter
		if self.line != '':
			output(self.line)

	def add(self, what, flush=True):
		self.line += what
		output(what, flush)

	def beginning(self, what, linebreak=True, flush=True):
		output('\b' * len(self.line), False)
		self.line = what + self.line
		if linebreak:
			self.line += '\n'
		output(self.line)

	def replace(self, what, num=1):
		output('\b' * num, False)
		self.line = self.line[:0-num] + what
		output(what)

if __name__ == '__main__':
	import time
	output(' [OK] Tested the output function\n')
	x = output_line(' Testing the output graphics |')
	for c in ['/', '-', '\\', '|', '/', '-', '\\', '|']:
		x.replace(c)
		time.sleep(0.3)
	x.replace('\b')
	x.beginning(' [OK]')

import itertools

valids = "123456789"
TARGET = "1239"

tries = 0
for combination in itertools.product(valids, repeat=4):
	if ''.join(combination) == TARGET:
		print(tries, ''.join(combination))
	tries += 1

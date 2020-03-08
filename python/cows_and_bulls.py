import signal, json, os, random
from collections import OrderedDict

def sig_handler(signal, frame):
	exit(0)
signal.signal(signal.SIGINT, sig_handler)

TEST_TARGET = "4256"
def get_exact_and_unpositioned(guess):
	unpositioned, exact = 0, 0

	for index, i in enumerate(guess):
		found = TEST_TARGET.find(i)
		if found == index:
			exact += 1
		elif found >= 0:
			unpositioned += 1

	return {'exact' : exact, 'unpositioned' : unpositioned}

def select_one_shrodinger_number():
	if len(potential['schrodingers']):
		return random.choice(list(potential['schrodingers'].keys()))
	return None

def select_one_guess_where_num(n):
	for guess in guess_history:
		if n in guess:
			return guess
	return None

def select_one_random_guess_not_eq(guess):
	for history_item in guess_history:
		if guess != history_item:
			return history_item
	return None

def select_one_unpositioned_num():
	return random.choice(list(unpositioned.keys()))

def select_one_schrodinger_num():
	return random.choice(list(potential['schrodingers'].keys()))

def select_one_potential_unpositioned_num():
	return random.choice(list(potential['unpositioned'].keys()))

def build_combination_of_unvalids_with_one_valid(num, ignore=[]):
	print(f'[ ] Building guess based on {num} and it\'s previous positions: {ignore}')
	possible_positions = ["0","1","2","3"]
	# Eliminate already tried positions:
	for index in ignore:
		index = str(index)
		if possible_positions.count(index) > 0:
			possible_positions = possible_positions[:possible_positions.index(index)] + possible_positions[possible_positions.index(index)+1:]
	test_position = random.choice(possible_positions)
	print(f'[ ] Going for position {int(test_position)+1}')

	guess = ''
	#for index, invalid_num in enumerate(eliminated_numbers.keys()):
	#	if index == test_position:
	#		guess += num
	#	guess += invalid_num
	#	if len(guess) >= 4:
	#		break
	index = 0
	invalid_numbers_left = list(eliminated_numbers.keys())
	while len(guess) != 4:
		if index == int(test_position):
			guess += num
		else:
			guess += invalid_numbers_left.pop(0)

		index += 1

	return guess

def build_win():
	guess = ''
	for item in sorted(exact.items(), key=lambda item: item[1]):
		guess += item[0]
	return guess

guess_history = OrderedDict()
shadow_guess_history = OrderedDict()
exact = {}
unpositioned = {}
potential = {
	'schrodingers' : OrderedDict(),
	'unpositioned' : OrderedDict(),
	'exacts' : OrderedDict()
}
unique_results = 0
eliminated_numbers = OrderedDict()

guess_order = ['1234', '5678']
guess_index = 0
guess_verified = {}

super_positioning = None
isolating_guess = None
isolating_against = None
isolating_number = None
isolation_elimination = []

def choice(guess, ignore=[]):
	raw_guess = guess
	ignored = []
	while len(ignored) <= len(raw_guess):
		i = random.choice(guess)
		print('Choice picking:', i, ignore.count(i))
		if ignore.count(i) >= 1:
			if i not in ignored:
				guess = guess[:guess.find(i)] + guess[guess.find(i)+1:]
				ignored.append(i)
				continue

		return raw_guess.find(i), i
	print('---- ERROR in 3... 2... 1... -----')
	print(len(ignored) >= len(guess))
	print(len(ignored) > len(ignore))
	print(len(ignore) == 0)
	return None, None

tries = 0
for x in range(30):
	print()
	tries += 1
	for i in range(1, 10):
		i = str(i)
		#if i in eliminated_numbers: continue

		if i in potential['unpositioned'] and i in potential['exacts']:
			try:
				del(potential['unpositioned'][i])
			except:
				pass
			try:
				del(potential['exacts'][i])
			except:
				pass
			potential['schrodingers'][i] = [] # guess.find(i) # Don't add the position, as it counts as a failed position later.

		if i in exact:
			print(f'\033[92m\033[1m{i}\033[0m ', end='') 
		elif i in unpositioned:
			print(f'\033[92m\033[1m({i})\033[0m ', end='') 
		elif i in potential['schrodingers']:
			print(f'\033[38;5;106m[{i}]\033[0m ', end='')
		elif i in potential['unpositioned']:
			print(f'\033[38;5;226m{i}\033[0m ', end='')
		elif i in potential['exacts']:
			print(f'\033[92m{{{i}}}\033[0m ', end='') 
		elif i in eliminated_numbers:
			print(f'\033[38;5;160m\033[09m{i}\033[0m ', end='')
		else:
			print(f'{i} ', end='')

	print()
	print('[+] History:')
	for guess in guess_history:
		if guess_history[guess]['type'] == 'normal':
			print(f'[ ] {guess} | {guess_history[guess]["score"]}')
		elif guess_history[guess]['type'] == 'super':
			print(f'[ ] \033[38;5;202m{guess} | {guess_history[guess]["score"]}\033[0m')
		elif guess_history[guess]['type'] == 'shadow':
			print(f'[ ] \033[38;5;238m{guess} | {guess_history[guess]["score"]}\033[0m')
		elif guess_history[guess]['type'] == 'eliminated':
			print(f'[ ] \033[38;5;160m\033[09m{guess} | {guess_history[guess]["score"]}\033[0m')

	#print('[ ] Guess history:', json.dumps({k: v['score'] for k,v in guess_history.items()}, indent=4))
	print('[ ] Potentials:', json.dumps(potential, indent=4))
	print('[ ] Unpositioned:', json.dumps(unpositioned, indent=4))
	print('[ ] Exacts:', json.dumps(exact, indent=4))

	if len(exact) == 4:
		guess = build_win()
		print(f'[W] You\'ve won in {tries} guesses, winning combo: {guess}')
		exit(0)

	if len(isolation_elimination) == 4:
		print(f'[!] Exhausted all combinations of {isolating_guess}, should now have 3 invalids.')
		guess_verified[isolating_guess] = True
		isolating_guess = None
		isolating_number = None
		isolating_against = None
		isolation_elimination = []

	if len(eliminated_numbers) < 3 and guess_index > len(guess_order)-1:
		if not isolating_guess:
			potential_positional = select_one_shrodinger_number()
			isolating_guess = select_one_guess_where_num(potential_positional)
			print(f'[+] Picked a new guess to investigate: {isolating_guess}')
		if not isolating_against:
			isolating_against = select_one_random_guess_not_eq(isolating_guess)

		print(f'[-] Picking candidate from {isolating_guess} with ignores: {isolation_elimination}')
		index, isolating_number = choice(isolating_guess, ignore=isolation_elimination)
		if index is None:
			print('Didn\'t get an index...?!', isolating_guess, isolation_elimination)
		replaced = isolating_against[index]
		guess = isolating_against[:index] + isolating_number + isolating_against[index+1:]

		print(f'[ ] Using {isolating_number} in isolation sequence: {isolating_against}')
		print(f'[ ] Replacing number: {replaced}')
		print(f'[+] Result guess is: {guess}')
		#print('[X] Trying shrodinger:', bullzying)
		#guess = input('Enter a guess: ')
	elif len(eliminated_numbers) >= 3 and len(unpositioned):
		print(f'[+] Trying to identify correct position for known valid numbers {list(unpositioned.keys())}')
		super_positioning = select_one_unpositioned_num()
		print(f'[ ] Picked \033[38;5;202m\033[1m{super_positioning}\033[0m for initial target practice')
		guess = build_combination_of_unvalids_with_one_valid(super_positioning, ignore=unpositioned[super_positioning])
		print(f'[ ] Final guess with a bunch of invalids: {guess}')
		unpositioned[super_positioning].append(guess.index(super_positioning))
	elif len(eliminated_numbers) >= 3 and len(potential['schrodingers']):
		print(f'[+] Trying to identify correct position for schrodingers {list(potential["schrodingers"].keys())}')
		super_positioning = select_one_schrodinger_num()
		print(f'[ ] Picked \033[38;5;202m\033[1m{super_positioning}\033[0m for initial target practice')
		if len(potential['schrodingers'][super_positioning]) >= 4:
			print(f'[!] {super_positioning} has been tried in all combinations: {potential["schrodingers"][super_positioning]}')
			eliminated_numbers[super_positioning] = True
			try:
				del(potential['schrodingers'][super_positioning])
			except:
				pass
			try:
				del(potential['unpositioned'][super_positioning])
			except:
				pass
			try:
				del(potential['exacts'][super_positioning])
			except:
				pass
			try:
				del(unpositioned[super_positioning])
			except:
				pass
			continue
		guess = build_combination_of_unvalids_with_one_valid(super_positioning, ignore=potential['schrodingers'][super_positioning])
		print(f'[ ] Final guess with a bunch of invalids: {guess}')
		potential['schrodingers'][super_positioning].append(guess.index(super_positioning))
	elif guess_index > len(guess_order)-1 and len(potential['unpositioned']):
		print(f'[+] Trying to identify correct position for unpositioned {list(potential["unpositioned"].keys())}')
		super_positioning = select_one_potential_unpositioned_num()
		print(f'[ ] Picked \033[38;5;202m\033[1m{super_positioning}\033[0m for initial target practice')
		if len(potential['unpositioned'][super_positioning]) >= 4:
			print(f'[!] {super_positioning} has been tried in all combinations: {potential["unpositioned"][super_positioning]}')
			eliminated_numbers[super_positioning] = True
			try:
				del(potential['unpositioned'][super_positioning])
			except:
				pass
			try:
				del(potential['unpositioned'][super_positioning])
			except:
				pass
			try:
				del(potential['exacts'][super_positioning])
			except:
				pass
			try:
				del(unpositioned[super_positioning])
			except:
				pass
			continue
		guess = build_combination_of_unvalids_with_one_valid(super_positioning, ignore=potential['unpositioned'][super_positioning])
		print(f'[ ] Final guess with a bunch of invalids: {guess}')
		potential['unpositioned'][super_positioning].append(guess.index(super_positioning))
	else:
		print(len(eliminated_numbers), len(unpositioned))
		guess = guess_order[guess_index]
		guess_index += 1
	
	print(f'[!] Trying guess: \033[38;5;164m{guess}\033[0m')
	#os.system('cls');
	#print(f'[?]: ', end='')

	hits = get_exact_and_unpositioned(guess)
	unique_results += hits['exact'] + hits['unpositioned']

	if isolating_against and not super_positioning:
		guess_history[guess] = {'score' : ('X' * hits['exact'])+('/' * hits['unpositioned']), 'type' : 'shadow'}

		if hits['exact'] < guess_history[isolating_against]["score"].count('X') and hits['unpositioned'] < (+guess_history[isolating_against]["score"].count('/')):
			print(f'[+] Guess {guess} was lower in score than {isolating_against}')
			print(f'[ ] {"X"*hits["exact"]}{"/"*hits["unpositioned"]} vs {guess_history[isolating_against]["score"]}')
			print(f'[ ] Number {isolating_number} was not a valid number.')
			eliminated_numbers[isolating_number] = True
			isolation_elimination.append(isolating_number)
			try:
				del(potential['schrodingers'][isolating_number])
			except:
				pass
			try:
				del(potential['unpositioned'][isolating_number])
			except:
				pass
			try:
				del(potential['exacts'][isolating_number])
			except:
				pass

			continue
		elif hits['exact'] > guess_history[isolating_against]["score"].count('X'):
			print(f'[+] Score was higher in {guess} than {isolating_against}')
			print(f'[ ] {"X"*hits["exact"]}{"/"*hits["unpositioned"]} vs {guess_history[isolating_against]["score"]}')
			print(f'[ ] Number {isolating_number} was a \033[92mhit!\033[0m.')
			isolation_elimination.append(isolating_number)
			exact[isolating_number] = index
			try:
				del(potential['schrodingers'][isolating_number])
			except:
				pass
			try:
				del(potential['unpositioned'][isolating_number])
			except:
				pass
			try:
				del(potential['exacts'][isolating_number])
			except:
				pass

			continue
		elif hits['unpositioned'] > guess_history[isolating_against]["score"].count('/'):
			unpositioned[isolating_number] = [index]
			isolation_elimination.append(isolating_number)
			## TODO: Check if there was one X in the isolating_against/isolating_guess
			##       if so, and the other numbers have been rejected, it means that the other/last
			##       number was an exact match and we can skip one guess.
			print(f'[+] {isolating_number} was confirmed but not an exact yet.')
			print(f'[ ] {"X"*hits["exact"]}{"/"*hits["unpositioned"]} vs {guess_history[isolating_against]["score"]}')
			continue
		elif hits['unpositioned'] == guess_history[isolating_against]["score"].count('/'):
			print(f'[+] Score was unaffected by guess {guess}.')
			print(f'[ ] {"X"*hits["exact"]}{"/"*hits["unpositioned"]} vs {guess_history[isolating_against]["score"]}')
			print(f'[ ] Number {isolating_number} was not a valid number.')
			print(f'[ ] Number {replaced} was not a valid number either.')

			eliminated_numbers[isolating_number] = True
			isolation_elimination.append(isolating_number)
			eliminated_numbers[replaced] = True
			#isolation_elimination.append(replaced)
			try:
				del(potential['schrodingers'][isolating_number])
			except:
				pass
			try:
				del(potential['unpositioned'][isolating_number])
			except:
				pass
			try:
				del(potential['exacts'][isolating_number])
			except:
				pass

			try:
				del(potential['schrodingers'][replaced])
			except:
				pass
			try:
				del(potential['unpositioned'][replaced])
			except:
				pass
			try:
				del(potential['exacts'][replaced])
			except:
				pass

			continue
		else:
			print('ELSE CASE?!')

	if (super_positioning):
		guess_history[guess] = {'score' : ('X' * hits['exact'])+('/' * hits['unpositioned']), 'type' : 'super'}
	else:
		guess_history[guess] = {'score' : ('X' * hits['exact'])+('/' * hits['unpositioned']), 'type' : 'normal'}

	if hits['exact'] + hits['unpositioned'] == 4:
		# We got lucky, and these are the only combinations.
		for i in range(1, 10):
			i = str(i)
			if i not in guess:
				eliminated_numbers[i] = True
			if i in potential['unpositioned']:
				del(potential['unpositioned'][i])
			elif i in potential['exacts']:
				del(potential['exacts'][i])
	elif hits['exact'] + hits['unpositioned'] == 0:
		print(f'[+] All numbers in guess was eliminated: \033[38;5;160m\033[09m{guess}\033[0m')
		guess_history[guess] = {'score' : ('X' * hits['exact'])+('/' * hits['unpositioned']), 'type' : 'eliminated'}
		for num in guess:
			eliminated_numbers[num] = True
			try:
				del(potential['schrodingers'][num])
			except:
				pass
			try:
				del(potential['unpositioned'][num])
			except:
				pass
			try:
				del(potential['exacts'][num])
			except:
				pass
			continue
	elif unique_results >= 4:
		potential_eliminations = {}
		ignore = {}
		for history_item in guess_history:
			for i in range(1,10):
				i = str(i)
				if i in ignore: continue

				if i in history_item and ('X' in guess_history[history_item]["score"] or '/' in guess_history[history_item]["score"]):
					if i in potential_eliminations:
						del(potential_eliminations[i])
					ignore[i] = True
					continue

				potential_eliminations[i] = True
		for num in potential_eliminations:
			eliminated_numbers[num] = True
			try:
				del(potential['schrodingers'][num])
			except:
				pass
			try:
				del(potential['unpositioned'][num])
			except:
				pass
			try:
				del(potential['exacts'][num])
			except:
				pass

	
	if(hits['unpositioned']):
		for index, num in enumerate(guess):
			if super_positioning:
				continue

			if num in unpositioned and num in exact and num in eliminated_numbers:
				continue

			if not num in eliminated_numbers:
				potential['unpositioned'][num] = [index]
	if(hits['exact']):
		for index, num in enumerate(guess):
			if super_positioning:
				if num == super_positioning:
					print(f'[+] Found super position for \033[38;5;82m{num} @ {index+1}\033[0m.')
					exact[num] = index
					try:
						del(potential['schrodingers'][num])
					except:
						pass
					try:
						del(unpositioned[num])
					except:
						pass
					super_positioning = None
				continue

			if num in unpositioned and num in exact and num in eliminated_numbers:
				continue

			elif not num in eliminated_numbers:
				potential['exacts'][num] = index

import random, json
from collections import OrderedDict

TARGET = '8361'

PHASE = 1
phase_one_guess_order = ['1234', '5678']
phase_one_guess_order_index = 0

digits_positions = {
	'1' : {},
	'2' : {},
	'3' : {},
	'4' : {},
	'5' : {},
	'6' : {},
	'7' : {},
	'8' : {},
	'9' : {}
}
position_digits = {
	
}
known_digits = {
	
}
bulls = {
	
}
cows = {

}
eliminated_digits = {}
history = OrderedDict()

def sum_guess(guess_history):
	return guess_history['cows'] + guess_history['bulls']

def pick_biggest_guess_from_history():
	return random.choice(list(history.keys()))

def pick_random_digit_from_guess(guess, ignore=[]):
	while (choice := random.choice(guess)) in ignore:
		pass
	return choice

def get_known_numbers(ammount=1, ignore=[]):
	digits = []
	for digit in eliminated_digits:
		if digit in ignore: continue

		digits.append(digit)
		if len(digits) >= ammount: break
	
	for digit in known_digits:
		if digit in ignore: continue

		digits.append(digit)
		if len(digits) >= ammount: break

	return digits[:ammount]

def run_guess(guess):
	cows, bulls = 0, 0

	for index, i in enumerate(guess):
		found = TARGET.find(i)
		if found == index:
			bulls += 1
		elif found >= 0:
			cows += 1

	history[guess] = {'bulls' : bulls, 'cows' : cows}
	return history[guess]

while True:
	if PHASE == 1:
		guess = phase_one_guess_order[phase_one_guess_order_index]
		result = run_guess(guess)

		print(guess,'|',result)

		phase_one_guess_order_index += 1
		if phase_one_guess_order_index > len(phase_one_guess_order)-1:
			total_score_in_phase_one = 0
			phase_one_guessed_numbers = ''
			for guess_history_item, guess_history_score in history.items():
				phase_one_guessed_numbers += guess_history_item
				total_score_in_phase_one += guess_history_score['cows'] + guess_history_score['bulls']

			if total_score_in_phase_one == 4:
				for i in range(1,10):
					if str(i) not in phase_one_guessed_numbers:
						eliminated_digits[str(i)] = True
						PHASE = 2.1
			else:
				for i in range(1,10):
					if str(i) not in phase_one_guessed_numbers:
						known_digits[str(i)] = True
						PHASE = 2.2


	elif PHASE == 2.1:
		# Phase 1 gave us an eliminiated number.
		isolated_guess = pick_biggest_guess_from_history()
		expected_result = history[isolated_guess]
		print(f'[+] Isolated guess: {isolated_guess} (Expected result: {sum_guess(expected_result)})')
		isolated_digit = pick_random_digit_from_guess(isolated_guess, ignore=[])
		digit_position = isolated_guess.find(isolated_digit)
		print(f'[ ] Isolating digit: {isolated_digit} @ position {digit_position+1}')

		replacement_number = get_known_numbers(1)[0]
		print(f'[ ] Replacing isolation digit with {replacement_number}')

		isolation_history = OrderedDict()
		isolation_history[isolated_digit] = {'number' : replacement_number, 'score' : 0, 'delta' : 0}


		iterated_guess = isolated_guess
		iterated_guess = iterated_guess[:digit_position] + replacement_number + iterated_guess[digit_position+1:]

		print(f'[ ] Trying guess: {iterated_guess}')

		result = run_guess(iterated_guess)
		isolation_history[isolated_digit]['score'] = sum_guess(result)
		isolation_history[isolated_digit]['delta'] = sum_guess(expected_result) - sum_guess(result)
		print(f'[ ] Result was: {sum_guess(result)}')

		if sum_guess(result) != sum_guess(expected_result):
			print(f'[ ] {isolated_digit} exists!')

			# TODO Find if it is cow or bull, bare in mind that if replacement_number exisits, then 
			# cows and bulls can remain the same number (ex 1234->///, 9234->/// which means both 1 and 9 are / on the same 0 position)
			
			# TODO Is the replacement_number also exisitng -> then find if it is cow or bull

			#bulls[isolated_digit] = digit_position
			if result['bulls'] < expected_result['bulls']:
				print(f'[ ] {isolated_digit} is a bull of some kind!')
				bulls[isolated_digit] = digit_position
			else:
				if isolated_digit not in cows: cows[isolated_digit] = []
				print(f'[ ] {isolated_digit} is a cow of some kind!')
				cows[isolated_digit].append(digit_position)

			known_digits[isolated_digit] = True # TODO: Unnecessary?
		else:
			print(f'[-] {isolated_digit} is eliminated!')

			# TODO Is the replacement_number exisitng -> then find if it is cow or bull
			eliminated_digits[isolated_digit] = True

		PHASE = 3
	
	elif PHASE == 2.2:
		# Phase 1 gave us a verified number, but unknown location.
		pass

	elif PHASE == 3:
		print(f'[+] Still using isolated guess: {isolated_guess}')

		current_isolated_guess_iteration = isolated_guess
		isolation_history_ignores = []
		for digit, digit_meta in isolation_history.items():
			isolation_history_ignores.append(digit_meta['number'])
			position = current_isolated_guess_iteration.find(digit)
			current_isolated_guess_iteration = current_isolated_guess_iteration[:position] + digit_meta['number'] + current_isolated_guess_iteration[position+1:]

		print(f'[ ] Currently on iteration: {current_isolated_guess_iteration}')
		isolated_digit = pick_random_digit_from_guess(isolated_guess, ignore=isolation_history_ignores)
		digit_position = isolated_guess.find(isolated_digit)
		replacement_number = get_known_numbers(1, ignore=[replacement_number])[0]
		print(f'[ ] Replacing: {isolated_digit} (@pos: {digit_position+1}) with {replacement_number}')
		new_guess = current_isolated_guess_iteration[:digit_position] + replacement_number + current_isolated_guess_iteration[digit_position+1:]

		expected_result = history[isolated_guess]

		isolation_history[isolated_digit] = {'number' : replacement_number, 'score' : 0, 'delta' : 0}
		total_isolation_delta = 0
		for digit in isolation_history:
			print(f'[?] Digit {digit} gave a delta score of {isolation_history[digit]["delta"]}')
			total_isolation_delta += isolation_history[digit]["delta"]

		print(f'[ ] Expected score: {sum_guess(expected_result)}')
		result = run_guess(new_guess)
		isolation_history[isolated_digit]['score'] = sum_guess(result)
		isolation_history[isolated_digit]['delta'] = sum_guess(expected_result) - sum_guess(result)
		print(f'[ ] Trying new guess: {new_guess}')
		print(f'[ ] Score was: {sum_guess(result)}')
		print(f'[ ] Total isolation delta-sum is: {total_isolation_delta}')

		if sum_guess(result) < sum_guess(expected_result):
			if result['bulls'] < expected_result['bulls']:
				print(f'[-] {isolated_digit} is a bull of some kind!')
				bulls[isolated_digit] = digit_position
			else:
				if isolated_digit not in cows: cows[isolated_digit] = []
				print(f'[-] {isolated_digit} is a cow of some kind!')
				cows[isolated_digit].append(digit_position)

			known_digits[isolated_digit] = True # TODO: Unnecessary?
		else:
			print(f'[-] {isolated_digit} is eliminated!')

			# TODO Is the replacement_number exisitng -> then find if it is cow or bull
			eliminated_digits[isolated_digit] = True

		if abs(total_isolation_delta) >= sum_guess(expected_result):
			PHASE = 4

	elif PHASE == 4:

		print('history:', json.dumps(history, indent=4))
		print('Known Digits:', json.dumps(known_digits, indent=4))
		print('Eliminated Digits:', json.dumps(eliminated_digits, indent=4))
		print('Cows:', json.dumps(cows, indent=4))
		print('Bulls:', json.dumps(bulls, indent=4))
		break

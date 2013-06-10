from module import Import
output = Import('output').output

def select(List, text=''):
  index = {}
	output(' | Select one of the following' + text + ':\n', False)
	for i in range(0, len(List)):
		output('   ' + str(i) + ': ' + List[i] + '\n', False)
	output(' | Choice: ')
	choice = sys.stdin.readline()
	if len(choice) <= 0:
		choice = 0
	return List[int(choice)]

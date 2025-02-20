raw_arguments = {}
positionals = []
skips=[]
for index, arg in enumerate(sys.argv[1:]):
	if index in skips:
		continue

	if arg.startswith('--'):
		if '=' in arg:
			key, val = [x.strip() for x in arg[2:].split('=', 1)]
		elif index+2 <= len(sys.argv[1:]) and sys.argv[1 + index + 1].startswith('--') is False:
			key, val = (arg.lstrip('-'), sys.argv[1 + index + 1])
			skips.append(index)
		else:
			key, val = arg[2:], True
		raw_arguments[key] = val
	else:
		positionals.append(arg)

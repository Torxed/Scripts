class autodict(dict):
	def __init__(self, *args, **kwargs):
		super(autodict, self).__init__(*args, **kwargs)
		#self.update(*args, **kwargs)

	def __getitem__(self, key):
		if not key in self:
			self[key] = autodict()

		val = dict.__getitem__(self, key)
		return val

	def __setitem__(self, key, val):
		dict.__setitem__(self, key, val)

	def dump(self, *args, **kwargs):
		copy = {}
		for key, val in self.items():
			if type(key) == bytes and b'*' in key: continue
			elif type(key) == str and '*' in key: continue
			elif type(val) == dict or type(val) == autodict:
				val = val.dump()
				copy[key] = val
			else:
				copy[key] = val
		return copy

class DupeDict(dict):
	"""
	DupeDict is a simple attempt at trying to support
	multiple identical keys in a dictionary, while remaining some speed.
	There's probably an academic word for this but I just call it DuplicateDict.
	"""
	internal_list = None

	def __setitem__(self, key, value):
		if self.internal_list is None:
			self.internal_list = []

		index = len(self.internal_list)
		self.internal_list.append((key, value))
		if not self.get(key):
			dict.__setitem__(self, key, [index,])
		else:
			dict.__getitem__(self, key).append(index)

	def __getitem__(self, key):
		indexes = dict.__getitem__(self, key)
		for index in indexes:
			yield dict([self.internal_list[index]])

	def __iter__(self):
		for key in dict.__iter__(self):
			for index in dict.__getitem__(self, key):
				yield self.internal_list[index]

	def __repr__(self):
		return str([dict([x]) for x in self.internal_list])

if __name__ == '__main__':
	base_hardware = DupeDict()
	base_hardware["cpu"] = "host"
	base_hardware["device"] = "if=pflash,format=raw,readonly=on,file=/usr/share/ovmf/x64/OVMF_CODE.fd"
	base_hardware["device"] = "if=pflash,format=raw,readonly=on,file=/usr/share/ovmf/x64/OVMF_VARS.fd"

	for key, val in struct: # Haven't fixed .items(), it's implied
		print(key, val)

from typing import Optional, Any, List, Tuple, Iterator, Dict

class DupeDict(dict[Any, Any]):
	"""
	DupeDict is a simple attempt at trying to support
	multiple identical keys in a dictionary, while remaining some speed.
	There's probably an academic word for this but I just call it DuplicateDict.
	"""
	internal_list :Optional[List[Tuple[Any, Any]]] = None

	def __setitem__(self, key :Any, value :Any) -> None:
		if self.internal_list is None:
			self.internal_list :List[Tuple[Any, Any]] = []

		index = len(self.internal_list)
		self.internal_list.append((key, value))
		if not self.get(key):
			dict.__setitem__(self, key, [index,])
		else:
			dict.__getitem__(self, key).append(index)

	def __getitem__(self, key :Any) -> Iterator[Any]:
		if self.internal_list:
			indexes = dict.__getitem__(self, key)
			for index in indexes:
				yield dict([self.internal_list[index]])

	def __iter__(self) -> Iterator[Any]:
		if self.internal_list:
			for key in dict.__iter__(self):
				for index in dict.__getitem__(self, key):
					yield self.internal_list[index]

	def __repr__(self) -> str:
		if self.internal_list:
			return str([dict([x]) for x in self.internal_list])
		else:
			return ''

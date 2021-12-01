if sys.platform == 'linux':
	from select import epoll, EPOLLIN, EPOLLHUP
else:
	import select
	EPOLLIN = 0
	EPOLLHUP = 0

	class epoll():
		""" #!if windows
		Create a epoll() implementation that simulates the epoll() behavior.
		This so that the rest of the code doesn't need to worry weither we're using select() or epoll().
		"""
		def __init__(self) -> None:
			self.sockets: Dict[str, Any] = {}
			self.monitoring: Dict[int, Any] = {}

		def unregister(self, fileno :int, *args :List[Any], **kwargs :Dict[str, Any]) -> None:
			try:
				del(self.monitoring[fileno])
			except:
				pass

		def register(self, fileno :int, *args :int, **kwargs :Dict[str, Any]) -> None:
			self.monitoring[fileno] = True

		def poll(self, timeout: float = 0.05, *args :str, **kwargs :Dict[str, Any]) -> List[Any]:
			try:
				return [[fileno, 1] for fileno in select.select(list(self.monitoring.keys()), [], [], timeout)[0]]
			except OSError:
				return []

import os, sys, importlib.util

"""
	Works in a similar way to `import time`, but instead you
	have the option to do:

	with Imported('/path/to/time.py') as time:
		print(time.time())
	
	And if any exceptions occurs, it's re-thrown as `ModuleError`.
	Useful for when you need to import python files by absolute path.
	But you're not sure if the file contains any errors and you don't
	want to break your main loop.
"""

class ModuleError(BaseException):
	def __init__(self, message, path):
		print(f'[Error] {message} in {path}')
		
class _Sys():
	modules = {}
	specs = {}
class VirtualStorage():
	def __init__(self):
		self.sys = _Sys()
internal = VirtualStorage()

class Imported():
	"""
	A wrapper around absolute-path-imported via string modules.
	Supports context wrapping to catch errors.

	Will partially reload *most* of the code in the module in runtime.
	Certain things won't get reloaded fully (this is a slippery dark slope)
	"""
	def __init__(self, path, namespace=None):
		if not namespace:
			namespace = os.path.splitext(os.path.basename(path))[0]
		self.namespace = namespace

		self._path = path
		self.spec = None
		self.imported = None
		if namespace in internal.sys.modules:
			self.imported = internal.sys.modules[namespace]
			self.spec = internal.sys.specs[namespace]

	def __repr__(self):
		if self.imported:
			return self.imported.__repr__()
		else:
			return f"<unloaded-module '{os.path.splitext(os.path.basename(self._path))[0]}' from '{self.path}' (Imported-wrapped)>"

	def __enter__(self, *args, **kwargs):
		"""
		Opens a context to the absolute-module.
		Errors are caught and through as a :ref:`~slimHTTP.ModuleError`.

		.. warning::
		
		    It will re-load the code and thus re-instanciate the memory-space for the module.
		    So any persistant data or sessions **needs** to be stowewd away between imports.
		    Session files *(`pickle.dump()`)* is a good option *(or god forbid, `__builtins__['storage'] ...` is an option for in-memory stuff)*.
		"""

		if not self.spec and not self.imported:
			self.spec = internal.sys.specs[self.namespace] = importlib.util.spec_from_file_location(self.namespace, self.path)
			self.imported = internal.sys.modules[self.namespace] = importlib.util.module_from_spec(self.spec)

		try:
			self.spec.loader.exec_module(self.imported)
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			raise ModuleError(traceback.format_exc())

		return self.imported

	def __exit__(self, *args, **kwargs):
		# TODO: https://stackoverflow.com/questions/28157929/how-to-safely-handle-an-exception-inside-a-context-manager
		if len(args) >= 2 and args[1]:
			raise args[1]

	@property
	def path(self):
		return os.path.abspath(self._path)

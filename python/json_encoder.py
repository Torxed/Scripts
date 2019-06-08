from json import JSONEncoder, dumps, loads

class JSON_Typer(JSONEncoder):
	def _encode(self, obj):
		## Workaround to handle keys in the dictionary being bytes() objects etc.
		## Also handles recursive JSON encoding. In case sub-keys are bytes/date etc.
		##
		## README: If you're wondering why we're doing loads(dumps(x)) instad of just dumps(x)
		##         that's because it would become a escaped string unless we loads() it back as
		##         a regular object - before getting passed to the super(JSONEncoder) which will
		##         do the actual JSON encoding as it's last step. All this shananigans are just
		##         to recursively handle different data types within a nested dict/list/X struct.
		if isinstance(obj, dict):
			def check_key(o):
				if type(o) == bytes:
					o = o.decode('UTF-8', errors='replace')
				elif type(o) == set:
					o = loads(dumps(o, cls=JSON_Typer))
				elif type(o) in (custom_class, custom_class_two):
					o = o.dump()
				return o
			## We'll need to iterate not just the value that default() usually gets passed
			## But also iterate manually over each key: value pair in order to trap the keys.
			
			for key, val in list(obj.items()):
				if isinstance(val, dict):
					val = loads(dumps(val, cls=JSON_Typer)) # This, is a EXTREMELY ugly hack..
                                                            # But it's the only quick way I can think of to 
                                                            # trigger a encoding of sub-dictionaries. (I'm also very tired, yolo!)
				else:
					val = check_key(val)
				del(obj[key])
				obj[check_key(key)] = val
			return obj
		elif isinstance(obj, (datetime, date)):
			return obj.isoformat()
		elif isinstance(obj, (custom_class, custom_class_two)):
			return loads(dumps(obj.dump(), cls=JSON_Typer))
		elif isinstance(obj, (list, set, tuple)):
			r = []
			for item in obj:
				r.append(loads(dumps(item, cls=JSON_Typer)))
			return r
		else:
			return obj

	def encode(self, obj):
		return super(JSON_Typer, self).encode(self._encode(obj))

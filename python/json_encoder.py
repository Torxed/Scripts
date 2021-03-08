from json import JSONEncoder, dumps, loads
from datetime import date, datetime

class JSON_Encoder:
	def _encode(obj):
		if isinstance(obj, dict):
			## We'll need to iterate not just the value that default() usually gets passed
			## But also iterate manually over each key: value pair in order to trap the keys.
			
			copy = {}
			for key, val in list(obj.items()):
				if isinstance(val, dict):
					val = loads(dumps(val, cls=JSON_Typer)) # This, is a EXTREMELY ugly hack..
                                                            # But it's the only quick way I can think of to 
                                                            # trigger a encoding of sub-dictionaries. (I'm also very tired, yolo!)
				else:
					val = JSON_Encoder._encode(val)
				copy[JSON_Encoder._encode(key)] = val
			return copy
		elif hasattr(obj, 'json'):
			return obj.json()
		elif isinstance(obj, (datetime, date)):
			return obj.isoformat()
		elif isinstance(obj, (list, set, tuple)):
			r = []
			for item in obj:
				r.append(loads(dumps(item, cls=JSON_Typer)))
			return r
		else:
			return obj

class JSON_Typer(JSONEncoder):
	def _encode(self, obj):
		return JSON_Encoder._encode(obj)

	def encode(self, obj):
		return super(JSON_Typer, self).encode(self._encode(obj))

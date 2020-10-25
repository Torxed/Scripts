x = b'E'

@bytes.new_function
def function(*args, **kwargs):
	print(args, kwargs)

x.new_function(8)

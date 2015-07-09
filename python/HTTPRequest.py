def HTTPRequest(data):
	if not b'\r\n\r\n' in data: raise ValueError('Not a valid HTTP request')

	headers = {}
	content = b''
	raw_header, content = data.split(b'\r\n\r\n')
	raw_header = raw_header.split(b'\r\n')

	request = b''
	requestURI = {}
	if raw_header[0][:4] in (b'POST', b'GET '):
		request = raw_header[0].split(b' ', 2)[1]
		if b'?' in request:
			request, tmp = request.split(b'?',1)
			for item in tmp.decode('utf-8').split('&'):
				if len(item) == 0: continue
				key, val = item.split('=',1)
				key = key.strip()
				val = val.strip()
				try:
					key = urllib.parse.unquote(key)
				except:
					pass
				try:
					val = urllib.parse.unquote(val)
				except:
					pass
				requestURI[key] = val
			del(tmp)
	else:
		raise ValueError('Not a valid HTTP request')

	for item in raw_header[1:]:
		if len(item) == 0: continue
		if not b': ' in item:
			print('Malformed header-item:', [item])
			continue
		key, val = item.split(b': ', 1)
		headers[key.strip()] = val.strip()

	del raw_header

	headers['Request'] = request
	headers['RequestURI'] = requestURI
	return headers, content
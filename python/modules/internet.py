from socket import socket
def checkInternet(reliableHost='www.google.com', port=80):
	s = socket()
	try:
		s.connect((reliableHost, port))
		s.close()
		return True
	except:
		return False

if __name__ == '__main__':
	import sys
	sys.stdout.write(str(checkInternet()) + '\n')
	sys.stdout.flush()

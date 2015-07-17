import socket

s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
def binary(b):
	res = ''
	for i in b:
		res += bin(i)[2:].zfill(8)
	return res

while True:
	c = binary(s.recvfrom(1987)[0])
	print(c)

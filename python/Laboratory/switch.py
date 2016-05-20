## A simple switch.

import socket, signal
import fcntl, ctypes
import struct
import binascii


## Handle process signals:
def sig_handler(signal, frame):
	global s
	global promisciousMode

	promisciousmode.off()
	s.close()

	exit(0)

## This is a ctype structure that matches the
## requirements to set a socket in promisc mode.
## In all honesty don't know where i found the values :)
class ifreq(ctypes.Structure):
        _fields_ = [("ifr_ifrn", ctypes.c_char * 16),
                    ("ifr_flags", ctypes.c_short)]

class promisc():
	def __init__(self, s, interface=b'ens33'):
		self.s = s
		self.interface = interface
		self.ifr = ifreq()

	def on(self):
		## -- Set up promisc mode:
		## 

		IFF_PROMISC = 0x100
		SIOCGIFFLAGS = 0x8913
		SIOCSIFFLAGS = 0x8914

		self.ifr.ifr_ifrn = self.interface

		fcntl.ioctl(self.s.fileno(), SIOCGIFFLAGS, self.ifr)
		self.ifr.ifr_flags |= IFF_PROMISC

		fcntl.ioctl(self.s.fileno(), SIOCSIFFLAGS, self.ifr)
		## ------------- DONE

	def off(self):
		## Turn promisc mode off:
		self.ifr.ifr_flags &= ~IFF_PROMISC
		fcntl.ioctl(self.s.fileno(), SIOCSIFFLAGS, self.ifr)
		## ------------- DONE

## Register a signal to the handler:
signal.signal(signal.SIGINT, sig_handler)

## AF_PACKET and ntohs(0x0003) ensures we recieve all contents of a packet.
## (if socket is set to promisc mode later on we'll also recive outbound packets)
s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
promisciousMode = promisc(s, b'ens33')
promisciousMode.on()

while 1:
	frame, meta = s.recvfrom(65565)
#	print(frame, meta)

	ethernet = frame[0:14]
	ethernet_segments = struct.unpack("!6s6s2s", ethernet)

	mac_source, mac_dest = (binascii.hexlify(mac) for mac in ethernet_segments[:2])
		
	ip = frame[14:34]
	ip_segments = struct.unpack("!12s4s4s", ip)

	ip_source, ip_dest = (socket.inet_ntoa(section) for section in ip_segments[1:3])
		
	tcp = frame[34:54]
	tcp_segments = struct.unpack("!2s2s16s", tcp)

	print('MAC Source:', b':'.join(mac_source[i:i+2] for i in range(0, len(mac_source), 2)))
	print('MAC Dest:', b':'.join(mac_dest[i:i+2] for i in range(0, len(mac_dest), 2)))
	print('IP Source:', ip_source)
	print('IP Dest:', ip_dest)

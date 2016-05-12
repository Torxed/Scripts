## A simple switch.

import socket
import fcntl
import ctypes

class ifreq(ctypes.Structure):
        _fields_ = [("ifr_ifrn", ctypes.c_char * 16),
                    ("ifr_flags", ctypes.c_short)]

s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))

## Set up promisc mode:
IFF_PROMISC = 0x100
SIOCGIFFLAGS = 0x8913
SIOCSIFFLAGS = 0x8914

ifr = ifreq()
ifr.ifr_ifrn = b'inside'

fcntl.ioctl(s.fileno(), SIOCGIFFLAGS, ifr)
ifr.ifr_flags |= IFF_PROMISC

fcntl.ioctl(s.fileno(), SIOCSIFFLAGS, ifr)
## ------------- DONE

try:
        while 1:
                print(s.recvfrom(65565))
except KeyboardInterrupt:
        ## Turn promisc mode off:
        ifr.ifr_flags &= ~IFF_PROMISC
        fcntl.ioctl(s.fileno(), SIOCSIFFLAGS, ifr)
        ## ------------- DONE
        s.close()

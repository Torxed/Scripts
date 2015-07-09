import socket, sys
from struct import *
from binascii import hexlify, unhexlify
from random import randint
from collections import OrderedDict as odict

## As ugly as code can get.
## But this will send a SYN package (not 100% perfectly formatted, but a SYN package)
## Will rework the IP frame part a bit to use bitPack for those odd length sections of
## the IP frame just as the TCP frame contains irregular lengthened packets (which.. bothers me)
##
## Not to forget: The "Uniqueue" Initial Sequence Number Selection of the protocol is mindboggling.
##                The way the Urgent flag works and the ECN flag works is beyond reason at this time lol
##
## Oh and last but not least, drink more caffeine when you start to think you can create 1/2 byte frames with struck.pack
##

def HalfBit(num, name=''):
	val = bin(num)[2:]
	while len(val) < 4:
		val = '0' + val
	return val
def JoinHalvs(binaryString):
	return int(binaryString, 2)

def humanHex(hexdump, _map=None):
	if not _map:
		width = 0
		for pairIndex in range(0, len(hexdump), 2):
			print(hexdump[pairIndex:pairIndex+2], end=' ')
			width += 1
			if width == 8:
				print('| ', end='')
			elif width == 16:
				width = 0
				print()
		if width != 0:
			print()
	else:
		offset = 0
		for key, length in _map.items():
			print(key + ': ', end='')
			valueString = hexdump[offset:offset+(length*2)]
			width = 0
			for pairIndex in range(0, len(valueString), 2):
				print(valueString[pairIndex:pairIndex+2], end=' ')
				if width == 8:
					print('| ', end='')
				elif width == 16:
					width = 0
					print()
					print(' ' * length(key)+2, end='')
			print()
			offset += (length*2)

def hexdump(bstr):
	return hexlify(bstr).decode('ascii')
	

def checksum(msg):
	s = 0
	# loop taking 2 characters at a time
	for i in range(0, len(msg), 2):
		w = (msg[i] << 8) + (msg[i+1] )
		s = s + w
	 
	s = (s>>16) + (s & 0xffff);
	#s = s + (s >> 16);
	#complement and mask to 4 byte short
	s = ~s & 0xffff
	 
	return s

s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

source_ip = socket.gethostbyname('hvornum.se')
dest_ip = socket.gethostbyname('www.google.se')

## IP Header:
#    0               1                   2                   3   
#     0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |Version|  IHL  |Type of Service|          Total Length         |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |         Identification        |Flags|      Fragment Offset    |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |  Time to Live |    Protocol   |         Header Checksum       |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |                       Source Address                          |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |                    Destination Address                        |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |                    Options                    |    Padding    |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

Version__Length = pack('!B', JoinHalvs(HalfBit(4, 'IP Version')+HalfBit(5, 'Header Length')))
TypeOfService = pack('!B', 0) # 8 bit (1 byte)
TotalLength = pack('!H', 52) # 16 bit (2 byte)
Identification = pack('!H', randint(30000, 60000))
## Since flags is just 3 bits, and fragment offset is 13, we need to creatively join the two.
## Since the length of this particular package isn't above 1, it will fuse with "Flags" thus
## enabling us to just pad with a blank 8 bit at the end :) Ugly hack, will work this away once
## we rebuild this to work with binary stuff.
Flags__FragmentOffset = pack('!B', JoinHalvs(HalfBit(4, 'Flags: 0100')+HalfBit(0, 'Fragment offset'))) + pack('!B', 0)
TTL = pack('!B', 128)
Protocol = pack('!B', 6) # TCP
Checksum_Good__Bad = pack('!B', 0) + pack('!B', 0) # Validation disabled
source = socket.inet_aton ( source_ip )
destination = socket.inet_aton ( dest_ip )

_map = odict()
_map['version'] = 1
_map['Type of service'] = 1
_map['Total Length'] = 2
_map['Identification'] = 2
_map['Flags'] = 1
_map['Fragment Offset'] = 1
_map['TTL'] = 1
_map['Protocol'] = 1
_map['Checksum'] = 2
_map['source'] = 4
_map['destination'] = 4
IP_package = Version__Length+TypeOfService+TotalLength+Identification+Flags__FragmentOffset+TTL+Protocol+Checksum_Good__Bad+source+destination

print('IP Header:')
humanHex(hexdump(IP_package), _map)


## TCP Header:
#    0               1                   2                   3   
#     0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |          Source Port          |       Destination Port        |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |                        Sequence Number                        |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |                    Acknowledgment Number                      |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |  Data |           |U|A|P|R|S|F|                               |
#    | Offset| Reserved  |R|C|S|S|Y|I|            Window             |
#    |       |           |G|K|H|T|N|N|                               |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |           Checksum            |         Urgent Pointer        |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |                    Options                    |    Padding    |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |                             data                              |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

def bitPack(binary):
	ret = b''
	for index in range(0, len(binary), 8):
		print('Packing:',binary[index:index+8])
		ret += pack('!B', int(binary[index:index+8], 2))
	return ret

sport = pack('!H', 1234)
dport = pack('!H', 1987)
# Note: This should be "Uniqueue", read: "Initial Sequence Number Selection" @ http://www.ietf.org/rfc/rfc793.txt
sequenceNumber = pack('!L', randint(0, 4294967295))
ackNumber = pack('!L', 0) # We're sending a SYN, we can't ACK on a number yet.

dataOffset = HalfBit(5) # TODO: Understand why this always is "5" aka 0101 (01010000 with the borrowed two bit from Reserved)
#dataOffset = '1000'
Reserved = '000000'
ControlBits = '000010' # [ URG | ACK | PSH | RST | SYN | FIN ]
DataOffset__Resrv__Flags = bitPack(dataOffset+Reserved+ControlBits)

Window = pack('!H', 8192) # My Favourite number of all times!
Checksum = pack('!H', 0) # We don't need it for data transfer?
UrgentPointer = pack('!H', 0)

TCP_package = sport+dport+sequenceNumber+ackNumber+DataOffset__Resrv__Flags
print('\nTCP Header:')
humanHex(hexdump(TCP_package))

#print(hexlify(pack('!L',int(int_to_binary(32)+int_to_binary(2), 2))).decode('ascii'))

# final full packet - syn packets dont have any data
package = IP_package + TCP_package

print('Sending:')
humanHex(hexdump(package))

s.sendto(package, (dest_ip , 0 ))
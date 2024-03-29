#!/usr/bin/python

# A modification on https://stackoverflow.com/a/20730442/929999 to support netmask and python3

from socket import AF_INET, AF_INET6, inet_ntop
from ctypes import (
	Structure, Union, POINTER, 
	pointer, get_errno, cast,
	c_ushort, c_byte, c_void_p, c_char_p, c_uint, c_int, c_uint16, c_uint32
)
import ctypes.util
import ctypes

class struct_sockaddr(Structure):
	 _fields_ = [
		('sa_family', c_ushort),
		('sa_data', c_byte * 14),]

class struct_sockaddr_in(Structure):
	_fields_ = [
		('sin_family', c_ushort),
		('sin_port', c_uint16),
		('sin_addr', c_byte * 4)]

class struct_sockaddr_in6(Structure):
	_fields_ = [
		('sin6_family', c_ushort),
		('sin6_port', c_uint16),
		('sin6_flowinfo', c_uint32),
		('sin6_addr', c_byte * 16),
		('sin6_scope_id', c_uint32)]

class union_ifa_ifu(Union):
	_fields_ = [
		('ifu_broadaddr', POINTER(struct_sockaddr)),
		('ifu_dstaddr', POINTER(struct_sockaddr)),]

class struct_ifaddrs(Structure):
	pass

def ifap_iter(ifap):
	ifa = ifap.contents
	while True:
		yield ifa
		if not ifa.ifa_next:
			break
		ifa = ifa.ifa_next.contents

def getfamaddr(sa):
	family = sa.sa_family
	addr = None
	if family == AF_INET:
		sa = cast(pointer(sa), POINTER(struct_sockaddr_in)).contents
		addr = inet_ntop(family, sa.sin_addr)
	elif family == AF_INET6:
		sa = cast(pointer(sa), POINTER(struct_sockaddr_in6)).contents
		addr = inet_ntop(family, sa.sin6_addr)
	return family, addr

class NetworkInterface(object):
	def __init__(self, name):
		self.name = name
		self.index = libc.if_nametoindex(name)
		self.addresses = {}

	def __str__(self):
		return "%s [index=%d, IPv4=%s, IPv6=%s]" % (
			self.name, self.index,
			self.addresses.get(AF_INET),
			self.addresses.get(AF_INET6))

def get_network_interfaces():
	ifap = POINTER(struct_ifaddrs)()
	result = libc.getifaddrs(pointer(ifap))
	if result != 0:
		raise OSError(get_errno())
	del result
	try:
		retval = {}
		for ifa in ifap_iter(ifap):
			name = ifa.ifa_name
			if not name.decode('UTF-8') in retval:
				retval[name.decode('UTF-8')] = {}
			try:
				family, addr = getfamaddr(ifa.ifa_addr.contents)
				family, subnet = getfamaddr(ifa.ifa_netmask.contents)
			except ValueError:
				family, addr, subnet = None, None, None

			if addr:
				retval[name.decode('UTF-8')][addr] = subnet
		return retval
	finally:
		libc.freeifaddrs(ifap)

struct_ifaddrs._fields_ = [
	('ifa_next', POINTER(struct_ifaddrs)),
	('ifa_name', c_char_p),
	('ifa_flags', c_uint),
	('ifa_addr', POINTER(struct_sockaddr)),
	('ifa_netmask', POINTER(struct_sockaddr)),
	('ifa_ifu', union_ifa_ifu),
	('ifa_data', c_void_p),]

libc = ctypes.CDLL(ctypes.util.find_library('c'))

if __name__ == '__main__':
	print(get_network_interfaces())

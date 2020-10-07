try:
	from OpenSSL.crypto import load_certificate, SSL, crypto, load_privatekey, PKey, FILETYPE_PEM, TYPE_RSA, X509, X509Req, dump_certificate, dump_privatekey
	from OpenSSL._util import ffi as _ffi, lib as _lib
except:
	class MOCK_CERT_STORE():
		def __init__(self):
			pass
		def add_cert(self, *args, **kwargs):
			pass

	class SSL():
		"""
		This is *not* a crypto implementation!
		
		This is a mock class to get the native lib `ssl` to behave like `PyOpenSSL.SSL`.
		The net result should be a transparent experience for programmers by default opting out of `PyOpenSSL`.

		.. warning::

		    PyOpenSSL is optional, but certain expectations of behavior might be scewed if you don't have it.
		    Most importantly, some flags will have no affect unless the optional dependency is met - but the behavior
		    of the function-call should remain largely the same.

		"""
		TLSv1_2_METHOD = 0b110
		VERIFY_PEER = 0b1
		VERIFY_FAIL_IF_NO_PEER_CERT = 0b10
		MODE_RELEASE_BUFFERS = 0b10000
		def __init__(self):
			self.key = None
			self.cert = None
		def Context(*args, **kwargs):
			return SSL()
		def set_verify(self, *args, **kwargs):
			pass
		def set_verify_depth(self, *args, **kwargs):
			pass
		def use_privatekey_file(self, path, *args, **kwargs):
			self.key = path
		def use_certificate_file(self, path, *args, **kwargs):
			self.cert = path
		def set_default_verify_paths(self, *args, **kwargs):
			pass
		def set_mode(self, *args, **kwargs):
			pass
		def load_verify_locations(self, *args, **kwargs):
			pass
		def get_cert_store(self, *args, **kwargs):
			return MOCK_CERT_STORE()
		def Connection(context, socket):
			if type(context) == SSL:
				new_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
				new_context.load_cert_chain(context.cert, context.key)
				context = new_context
			return context.wrap_socket(socket, server_side=True)

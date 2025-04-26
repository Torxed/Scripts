import dataclasses
import pydantic
import base64
import json
import cryptography.x509
import cryptography.hazmat.backends
import cryptography.hazmat.primitives
import cryptography.hazmat.primitives.asymmetric
from Crypto import Random
from Crypto.Cipher import AES
from OpenSSL import crypto


class DecryptionError(Exception):
	def __init__(self, message :str, errcode :int) -> None:
		super(DecryptionError, self).__init__(message)
		self.errcode = errcode


class RSADecryptionError(Exception):
	def __init__(self, message :str, errcode :int) -> None:
		super(RSADecryptionError, self).__init__(message)
		self.errcode = errcode


class AESCipher(object):
	@staticmethod
	def encrypt(data, key :bytes, on_encrypted=None):
		print(data)
		if isinstance(data, dict):
			data = json.dumps(data)

		#data = self._pad(data)
		iv = Random.new().read(AES.block_size)
		cipher = AES.new(key, AES.MODE_GCM, iv)

		encrypted_data, tag = cipher.encrypt_and_digest(data.encode('UTF-8'))

		struct = {
			'data' : base64.b64encode(encrypted_data + tag).decode('UTF-8'),
			'key': base64.b64encode(key).decode('UTF-8'),
			'iv': base64.b64encode(iv).decode('UTF-8')
		}

		if on_encrypted and (response := on_encrypted(struct)):
			struct = response

		return struct

	@staticmethod
	def decrypt(data, key, iv):
		cipher = AES.new(base64.b64decode(key), AES.MODE_GCM, nonce=base64.b64decode(iv))
		e_data = base64.b64decode(data)
		return cipher.decrypt_and_verify(e_data[:-16], e_data[-16:]).decode('UTF-8')

		# return AESCipher._unpad(cipher.decrypt(data[AES.block_size:])).decode('utf-8')

	@staticmethod
	def _pad(s):
		return s + (AES.block_size - len(s) % AES.block_size) * bytes(chr(AES.block_size - len(s) % AES.block_size), 'UTF-8')

	@staticmethod
	def _unpad(s):
		return s[:-ord(s[len(s)-1:])]


class RSA(object):
	@staticmethod
	def encrypt(data :bytes, certificate :str):
		key_obj = cryptography.x509.load_pem_x509_certificate(certificate.encode('UTF-8')).public_key()

		if encrypted_data := key_obj.encrypt(
			data,
			cryptography.hazmat.primitives.asymmetric.padding.OAEP(
				mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
					algorithm=cryptography.hazmat.primitives.hashes.SHA256()
				),
				algorithm=cryptography.hazmat.primitives.hashes.SHA256(),
				label=None
			)
		):
			return encrypted_data

		raise RSAEncryptionError("Could not encrypt data", errcode=100005)

	def sign(data :dict|str|bytes, private_key=None):
		from .session import key

		if isinstance(data, dict):
			data = json.dumps(
				data,
				separators=(',', ':'),
				sort_keys=True,
				ensure_ascii=False,
				allow_nan=False
			)

		if isinstance(data, str):
			data = data.encode('UTF-8')

		if private_key is None:
			private_key = key

		signature = private_key.sign(
			data,
			cryptography.hazmat.primitives.asymmetric.padding.PSS(
				mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(cryptography.hazmat.primitives.hashes.SHA256()),
				salt_length=cryptography.hazmat.primitives.asymmetric.padding.PSS.MAX_LENGTH
			),
			cryptography.hazmat.primitives.hashes.SHA256()
		)

		return base64.b64encode(signature).decode('UTF-8')

	def verify(data, signature, public_key):
		return public_key.verify(
			signature,
			data,
			cryptography.hazmat.primitives.asymmetric.padding.PSS(
				mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(cryptography.hazmat.primitives.hashes.SHA256()),
				salt_length=cryptography.hazmat.primitives.asymmetric.padding.PSS.MAX_LENGTH
			),
			cryptography.hazmat.primitives.hashes.SHA256()
		)

	def verify_payload(data, public_key):
		signature = data.pop("signature")

		return RSA.verify(data, base64.b64decode(signature['b64data']), public_key)

	def sign_payload(data, private_key):
		from .session import cert as ca_cert

		return {
			**data,
			"signature": {
				"b64data": RSA.sign(data, private_key),
				"fingerprint": base64.b64encode(
					cryptography.x509.load_pem_x509_certificate(
						ca_cert.encode('UTF-8')
					).fingerprint(
						cryptography.hazmat.primitives.hashes.SHA256()
					)
				).decode('UTF-8')
			}
		}

class EncryptedPayload(pydantic.BaseModel):
	iv: str
	key: str
	data: str


@dataclasses.dataclass
class EncryptedRequest:
	type: str
	payload: EncryptedPayload
	signed :bool = False
	json :str|None = None

	def __post_init__(self):
		if self.type not in {'encryption', }:
			raise ValueError("Invalid type in payload.")

		try:
			key_obj = crypto.load_privatekey(crypto.FILETYPE_PEM, os.environ['CA_KEY'])
			key_session = key_obj.to_cryptography_key()

			if RSA_KEY := key_session.decrypt(
				base64.b64decode(self.payload.key),
				cryptography.hazmat.primitives.asymmetric.padding.OAEP(
					mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
						algorithm=cryptography.hazmat.primitives.hashes.SHA256()
					),
					algorithm=cryptography.hazmat.primitives.hashes.SHA256(),
					label=None
				)
			):
				if not (AES_KEY := json.loads(RSA_KEY.decode('UTF-8')).get('aes_key')):
					raise DecryptionError("Invalid AES key in payload", errcode=100000)

				plaintext = AESCipher.decrypt(self.payload.data, AES_KEY, self.payload.iv)
				if plaintext[0] != '{' or plaintext[-1] != '}':
					raise DecryptionError("Could not decrypt message", errcode=100001)

				self.json = json.loads(plaintext)

				if (signature_data := self.json.get('signature')):
					fingerprint = signature_data.get('fingerprint')
					signature = signature_data.get('b64data')
					public_key = cryptography.x509.load_pem_x509_certificate(os.environ['CERTIFICATE']).public_key()
					RSA.verify_payload(self.json, public_key)
		except ValueError as err:
			if len(err.args) and err.args[0] == 'Encryption/decryption failed.':
				raise RSADecryptionError("Could not decrypt payload.", errcode=100009)
			raise err


	def has_data(self):
		return self.json is not None
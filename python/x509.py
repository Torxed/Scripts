import base64
import datetime
import cryptography.x509
import cryptography.hazmat.backends
import cryptography.hazmat.primitives.asymmetric
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.hazmat.bindings._rust.openssl.ec
try:
	import PyKCS11
except ModuleNotFoundError:
	PyKCS11 = None

class RSAEncryptionError(BaseException):
	pass

class RSADecryptionError(BaseException):
	pass

class RSAInvalidSignature(BaseException):
	pass

class RSAInvalidCertificate(BaseException):
	pass

class NotYetImplemented(BaseException):
	pass

class X509:
	def __init__(self, ca=None, privkey=None, pubkey=None, certificate=None, hsm_session=None, *args, **kwargs):
		self.ca = ca
		self.privkey = privkey
		self.pubkey = pubkey
		self.certificate_data = certificate
		self.hsm_session = hsm_session

		self._certificate_authority = None
		self._privkey = None
		self._pubkey = None
		self._certificate = None

		self.args = args
		self.kwargs = kwargs

		if not any([self.privkey, self.pubkey, self.certificate_data]):
			if self.ca:
				self.generate_csr()
			else:
				self.generate_certificate()

		if self.ca:
			self.validate_certificate()

	@property
	def certificate_authority(self):
		if not self._certificate_authority:
			self._certificate_authority = cryptography.x509.load_pem_x509_certificate(
				self.ca.encode(),
				cryptography.hazmat.backends.default_backend()
			)

		return self._certificate_authority

	@property
	def private_key(self) -> cryptography.hazmat.bindings._rust.openssl.rsa.RSAPrivateKey:
		if not self._privkey:
			self._privkey = cryptography.hazmat.primitives.serialization.load_pem_private_key(
				self.privkey.encode(),
				password=None, # If the private key is encrypted, provide the password here as bytes: password=b"your_password"
			)

		return self._privkey

	@property
	def public_key(self) -> cryptography.hazmat.bindings._rust.openssl.rsa.RSAPublicKey:
		if not self._pubkey:
			self._pubkey = cryptography.hazmat.primitives.serialization.load_pem_public_key(
			self.pubkey.encode()
		)

		return self._pubkey

	@property
	def certificate(self) -> cryptography.hazmat.bindings._rust.x509.Certificate:
		if not self._certificate:
			self._certificate = cryptography.x509.load_pem_x509_certificate(
				self.certificate_data.encode(),
				cryptography.hazmat.backends.default_backend()
			)

		return self._certificate

	def validate_certificate(self):
		ca_public_key = self.certificate_authority.public_key()
		signature = certificate.signature
		tbs_certificate_bytes = self.certificate.tbs_certificate_bytes
		hash_algorithm = self.certificate.signature_hash_algorithm

		try:
			if isinstance(ca_public_key, cryptography.hazmat.bindings._rust.openssl.rsa.RSAPublicKey):
				# Check if the signature algorithm uses PSS
				if certificate.signature_algorithm_oid._name == "RSASSA-PSS":
					padding_scheme = cryptography.hazmat.primitives.asymmetric.padding.PSS(
						mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(hash_algorithm),
						salt_length=cryptography.hazmat.primitives.asymmetric.padding.PSS.MAX_LENGTH,
					)
				else:
					padding_scheme = cryptography.hazmat.primitives.asymmetric.padding.PKCS1v15()

				# Verify the signature using RSA public key
				ca_public_key.verify(
					signature,
					tbs_certificate_bytes,
					padding_scheme,
					hash_algorithm,
				)

			elif isinstance(ca_public_key, cryptography.hazmat.bindings._rust.openssl.ec.EllipticCurvePublicKey):
				# ECDSA signatures do not use padding
				ca_public_key.verify(
					signature,
					tbs_certificate_bytes,
					cryptography.hazmat.bindings._rust.openssl.ec.ECDSA(hash_algorithm),
				)

			else:
				raise NotYetImplemented("Unsupported public key type.")

			return True

		except Exception as e:
			raise RSAInvalidCertificate(str(e))

	def generate_private_key(self, keysize=4096):
		return cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key(
			public_exponent=65537, # https://stackoverflow.com/a/45293558/929999
			key_size=keysize,
		)

	def generate_certificate(self):
		private_key = self.generate_private_key(4096)

		# Step 2: Get the public key from the private key
		public_key = private_key.public_key()

		# Optional Step 3: Create a self-signed certificate using x509
		# Define subject and issuer details
		subject = issuer = cryptography.x509.Name([
			cryptography.x509.NameAttribute(cryptography.x509.oid.NameOID.COUNTRY_NAME, self.kwargs.get('COUNTRY', 'SE')),
			cryptography.x509.NameAttribute(cryptography.x509.oid.NameOID.STATE_OR_PROVINCE_NAME, self.kwargs.get('STATE', 'Stockholm')),
			cryptography.x509.NameAttribute(cryptography.x509.oid.NameOID.LOCALITY_NAME, self.kwargs.get('CITY', 'Stockholm')),
			cryptography.x509.NameAttribute(cryptography.x509.oid.NameOID.ORGANIZATION_NAME, self.kwargs.get('ORGANIZATION', 'ShyShare')),
			cryptography.x509.NameAttribute(cryptography.x509.oid.NameOID.COMMON_NAME, self.kwargs.get('COMMON_NAME', 'share.blyg.se')),
		])

		# Build the certificate
		certificate = (
			cryptography.x509.CertificateBuilder()
			.subject_name(subject)
			.issuer_name(issuer)
			.public_key(public_key)
			.serial_number(cryptography.x509.random_serial_number())
			.not_valid_before(datetime.datetime.utcnow())
			.not_valid_after(
				# Certificate valid for one year
				datetime.datetime.utcnow() + datetime.timedelta(days=365)
			)
			.sign(private_key, cryptography.hazmat.primitives.hashes.SHA256())
		)

		self.privkey = private_key.private_bytes(
			encoding=cryptography.hazmat.primitives.serialization.Encoding.PEM,
			format=cryptography.hazmat.primitives.serialization.PrivateFormat.TraditionalOpenSSL,  # or PKCS8
			encryption_algorithm=cryptography.hazmat.primitives.serialization.NoEncryption(),      # or use BestAvailableEncryption(b"your_password")
		).decode()

		self.pubkey = public_key.public_bytes(
			encoding=cryptography.hazmat.primitives.serialization.Encoding.PEM,
			format=cryptography.hazmat.primitives.serialization.PublicFormat.SubjectPublicKeyInfo,
		).decode()

		self.certificate_data = certificate.public_bytes(
			cryptography.hazmat.primitives.serialization.Encoding.PEM
		).decode()

		return self.certificate_data

	def generate_csr(self):
		csr_subject = cryptography.x509.Name([
			cryptography.x509.NameAttribute(cryptography.x509.oid.NameOID.COUNTRY_NAME, self.kwargs.get('COUNTRY', 'SE')),
			cryptography.x509.NameAttribute(cryptography.x509.oid.NameOID.STATE_OR_PROVINCE_NAME, self.kwargs.get('STATE', 'Stockholm')),
			cryptography.x509.NameAttribute(cryptography.x509.oid.NameOID.LOCALITY_NAME, self.kwargs.get('CITY', 'Stockholm')),
			cryptography.x509.NameAttribute(cryptography.x509.oid.NameOID.ORGANIZATION_NAME, self.kwargs.get('ORGANIZATION', 'ShyShare')),
			cryptography.x509.NameAttribute(cryptography.x509.oid.NameOID.COMMON_NAME, self.kwargs.get('COMMON_NAME', 'share.blyg.se')),
		])

		csr_builder = cryptography.x509.CertificateSigningRequestBuilder()
		csr_builder = csr_builder.subject_name(csr_subject)

		# Optional Step 3: Add extensions (e.g., Subject Alternative Names)
		if 'subjectAltNames' in self.kwargs:
			csr_builder = csr_builder.add_extension(
				cryptography.x509.SubjectAlternativeName([
					cryptography.x509.DNSName(altname)
					for altname in self.kwargs['subjectAltNames']
					# TODO: Support IP addresses
				]),
				critical=False  # Set to True if you want the extension to be marked as critical
			)

		# Optional: Add more extensions as needed
		# For example, Key Usage extension
		csr_builder = csr_builder.add_extension(
			cryptography.x509.KeyUsage(
				digital_signature=True,
				content_commitment=False,
				key_encipherment=True,
				data_encipherment=False,
				key_agreement=False,
				key_cert_sign=False,
				crl_sign=False,
				encipher_only=False,
				decipher_only=False,
			),
			critical=True
		)

		# Step 4: Sign the CSR with the private key
		csr = csr_builder.sign(
			private_key,
			cryptography.hazmat.primitives.hashes.SHA256(),
		)

		return csr.public_bytes(cryptography.hazmat.primitives.serialization.Encoding.PEM)

	def sign(self, data :bytes, urlsafe=True):
		if PyKCS11 is not None and self.hsm_session and isinstance(self.private_key, PyKCS11.CK_OBJECT_HANDLE):
			result = bytes(
				self.hsm_session.sign(
					self.private_key,
					data,
					PyKCS11.RSA_PSS_Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS_PSS, PyKCS11.CKM_SHA256, PyKCS11.CKG_MGF1_SHA256, PyKCS11.LowLevel.CK_RSA_PKCS_PSS_PARAMS_LENGTH)
				)
			)
		else:
			result = self.private_key.sign(
				data,
				cryptography.hazmat.primitives.asymmetric.padding.PSS(
					mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(cryptography.hazmat.primitives.hashes.SHA256()),
					salt_length=cryptography.hazmat.primitives.asymmetric.padding.PSS.MAX_LENGTH
				),
				cryptography.hazmat.primitives.hashes.SHA256()
			)

		if urlsafe:
			return base64.urlsafe_b64encode(result).decode()
		else:
			return result

	def encrypt(self, data :bytes, urlsafe=True):
		if encrypted_data := self.public_key.encrypt(
			data,
			cryptography.hazmat.primitives.asymmetric.padding.OAEP(
				mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
					algorithm=cryptography.hazmat.primitives.hashes.SHA256()
				),
				algorithm=cryptography.hazmat.primitives.hashes.SHA256(),
				label=None
			)
		):
			if urlsafe:
				return base64.urlsafe_b64encode(encrypted_data).decode()
			else:
				return encrypted_data

		raise RSAEncryptionError("Could not encrypt data")

	def decrypt(self, data :bytes|str, urlsafe=True):
		if isinstance(data, str):
			if urlsafe:
				data = base64.urlsafe_b64decode(data)
			else:
				data = data.encode()

		try:
			if plaintext := self.private_key.decrypt(
				data,
				cryptography.hazmat.primitives.asymmetric.padding.OAEP(
					mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
						algorithm=cryptography.hazmat.primitives.hashes.SHA256()
					),
					algorithm=cryptography.hazmat.primitives.hashes.SHA256(),
					label=None
				)
			):
				return plaintext
		except ValueError:
			raise RSADecryptionError(f"Could not decrypt RSA data")

	def verify_signature(self, data :str|bytes, signature :str|bytes, urlsafe=True):
		if isinstance(data, str):
			if urlsafe:
				data = base64.urlsafe_b64decode(data)
			else:
				data = data.encode()

		if isinstance(signature, str):
			if urlsafe:
				signature = base64.urlsafe_b64decode(signature)
			else:
				signature = signature.encode()

		try:
			if self.public_key.verify(
				signature,
				data,
				cryptography.hazmat.primitives.asymmetric.padding.PSS(
					mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(cryptography.hazmat.primitives.hashes.SHA256()),
					salt_length=cryptography.hazmat.primitives.asymmetric.padding.PSS.MAX_LENGTH
				),
				cryptography.hazmat.primitives.hashes.SHA256()
			) is None:
				return True
		except cryptography.exceptions.InvalidSignature:
			raise RSAInvalidSignature("Invalid signature, data was not signed by this public key")
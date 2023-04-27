import base64
import hashlib
import os

password = '1234'

salt = base64.b64encode(os.urandom(12))
password = base64.b64encode(hashlib.pbkdf2_hmac('sha512', bytes(password, 'UTF-8'), salt, 200000, 64))
print(f"SHA512 :: $6${salt.decode('UTF-8')}${password.decode('UTF-8')}")

# Verify with (not sure why crypt.crypt(password, password_hash) doesn't work):
def validate_hash(password, password_hash):
	* _, salt, password_hash = password_hash.split('$')
	return base64.b64encode(hashlib.pbkdf2_hmac('sha512', password.encode(), salt.encode(), 200000, 64)).decode() == password_hash

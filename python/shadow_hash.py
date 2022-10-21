import base64
import hashlib
import os

password = '1234'

salt = base64.b64encode(os.urandom(12))
password = base64.b64encode(hashlib.pbkdf2_hmac('sha512', bytes(password, 'UTF-8'), salt, 200000, 64))
print(f"SHA512 :: $6${salt.decode('UTF-8')}${password.decode('UTF-8')}")

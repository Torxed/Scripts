signature = b'b64enc(sigdata(msg))'

import rsa
from base64 import b64encode as benc
from base64 import b64decode as bdec

plaintext = b"msg"
with open(keyfile) as fh:
	data = fh.read()
	privkey = rsa.PrivateKey.load_pkcs1(data)
	pubkey = rsa.PublicKey.load_pkcs1(data)

rsasignature = rsa.sign(plaintext, privkey, 'SHA-256')

print('Ext-Sig:', signature)
print('RSA-Sig:', benc(rsasignature))

print(rsa.verify(plaintext, bdec(signature), pubkey))

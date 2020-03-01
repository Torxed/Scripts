from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.asymmetric import dh as _dh
from cryptography.hazmat.backends.interfaces import DHBackend
from cryptography.hazmat.backends.openssl.backend import backend
from cryptography.hazmat.primitives.serialization import ParameterFormat

# This equals (?): openssl dhparam -out dh1024.pem 1024

def generate_diffie_hellman(key_size):
    # "generator is often 2 or 5" / "generator must be 2 or 5.." (depending on where you read)
    DHBackend.generate_dh_parameters(backend, generator=2, key_size=key_size)
    dh_parameters = _dh.generate_parameters(generator=2, key_size=key_size, backend=backend)
    return dh_parameters.parameter_bytes(Encoding.PEM, ParameterFormat.PKCS3)

with open('dh1024.pem', 'wb') as output:
    output.write(generate_diffie_hellman(1024))

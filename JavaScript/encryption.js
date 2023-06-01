const x509 = {
	default_key_type: "RSA-OAEP",
	default_key_length: 2048,
	default_hash: "SHA-256",

	formatAsPem: (str) => {
		let finalString = '-----BEGIN PUBLIC KEY-----\n';

		while(str.length > 0) {
			finalString += str.substring(0, 64) + '\n';
			str = str.substring(64);
		}

		finalString = finalString + "-----END PUBLIC KEY-----";

		return finalString;
	},
	spkiToPEM: (key_data) => {
		const keydataS = arrayBufferToString(key_data);
		const keydataB64 = window.btoa(keydataS);
		const keydataB64Pem = x509.formatAsPem(keydataB64);
		return keydataB64Pem;
	},
	generate_keys: () => {
		return new Promise((resolve, reject) => {
			let options = {
				name: x509.default_key_type,
				modulusLength: x509.default_key_length, //can be 2048, or 4096
				publicExponent: new Uint8Array([0x01, 0x00, 0x01]), // https://stackoverflow.com/a/51180579/929999
				hash: {name: x509.default_hash}, //can be "SHA-256", "SHA-384", or "SHA-512"
			};

			keys = {}

			// ["encrypt", "decrypt"]
			window.crypto.subtle.generateKey(options, true, ["wrapKey", "unwrapKey"])
			.then(function(key){
				for(let key_type in {'publicKey':true, 'privateKey':true}) {
					window.crypto.subtle.exportKey("jwk", key[key_type])
					.then((key_data) => {
						keys[key_type] = key_data

						// When both keys are exported, resolve our promise on generating the keys
						if(Object.keys(keys).length >= 2)
							resolve(keys)

					}).catch(function(err){
						reject(err)
					});
				}
			})
		})
	},
	import_PEM: (PEM_CERTIFICATE) => {
		return new Promise((resolve, reject) => {
			const b64 = PEM_CERTIFICATE
				.replaceAll('\n', '')
				.replace(/[-]+BEGIN PUBLIC KEY[-]+/i, '')
				.replace(/[-]+END PUBLIC KEY[-]+/i, '')
			const key_data = str2ab(window.atob(b64))

			window.crypto.subtle.importKey("spki", key_data, {name: x509.default_key_type, hash: x509.default_hash,}, true, ["encrypt"])
			.then((public_key) => {
				resolve(public_key)
			})
			.catch((error) => {
				reject(error)
			})
		})
	},
	encrypt: (data, public_key) => {
		return new Promise((resolve, reject) => {
			const enc = new TextEncoder();

			window.crypto.subtle.encrypt({name: x509.default_key_type}, public_key, enc.encode(data))
			.then((encrypted_message) => {
				const base64_encrypted_data = btoa(new Uint8Array(encrypted_message).reduce((data, byte) => data + String.fromCharCode(byte), ''));
				resolve(base64_encrypted_data)
			})
		})
	},
	export_pubkey_to_pem: (keys) => {
		return new Promise((resolve, reject) => {
			window.crypto.subtle.importKey("jwk", keys['publicKey'], {name: x509.default_key_type, hash: {name: x509.default_hash}}, true, ["wrapKey"])
			.then((publicKey) => {
				window.crypto.subtle.exportKey("spki", publicKey)
				.then((key_data) => {
					resolve(x509.spkiToPEM(key_data))
				})
				.catch((error) => {
					reject(error)
				})
			})
			.catch((error) => {
				reject(error)
			})

			//window.crypto.subtle.exportKey("spki", key.publicKey)
		})
	}
}

const AES = {
	encryption: (data, aes_key) => {
		return new Promise((resolve, reject) => {
			const enc = new TextEncoder();
			const iv_data = window.crypto.getRandomValues(new Uint8Array(12));

			window.crypto.subtle.encrypt({name: "AES-GCM", iv: iv_data}, aes_key, enc.encode(data))
			.then((encrypted_message) => {
				const iv = window.btoa(arrayBufferToString(iv_data));

				// https://stackoverflow.com/a/74256265/929999
				const [base64_encrypted_data, auth_tag] = [
					btoa(new Uint8Array(encrypted_message.slice(0, encrypted_message.byteLength - 16)).reduce((data, byte) => data + String.fromCharCode(byte), '')),
					window.btoa(arrayBufferToString(encrypted_message.slice(encrypted_message.byteLength - 16))),
				];

				resolve({"iv": iv, "encrypted_data": base64_encrypted_data, 'tag' : auth_tag})
			})
			.catch(function(err){
				console.error(err);
			});
		})
	},
	generate_key: (length = 256) => {
		return new Promise((resolve, reject) => {
			window.crypto.subtle.generateKey({name: "AES-GCM", length: length}, true, ["encrypt", "decrypt"])
			.then((key) => {
				resolve(key)
			})
			.catch((error) => {
				reject(error)
			})
		})
	},
	export_aes_key: (key_obj) => {
		return new Promise((resolve, reject) => {
			window.crypto.subtle.exportKey("raw", key_obj)
			.then((key) => {
				resolve(key)
			})
			.catch((error) => {
				reject(error)
			})
		})
	},
	import_aes_key: (key_data) => {
		return new Promise((resolve, reject) => {
			window.crypto.subtle.importKey("raw", key_data, {name: "AES-GCM"}, false, ["encrypt", "decrypt"])
			.then((aes_key) => {
				resolve(aes_key)
			})
			.catch((error) => {
				reject(error)
			})
		})
	}
}

// Example usage:
x509.generate_keys()
.then((keys) => {
	x509.export_pubkey_to_pem(keys)
	.then((PEM_CERTIFICATE) => {
		x509.import_PEM(PEM_CERTIFICATE)
		.then((public_key) => {
			x509.encrypt(JSON.stringify({"key_length" : x509.default_key_length}), public_key)
			.then((encrypted_data) => {
				// Get a AES key from a remote server or generate one locally
				AES.generate_key()
				.then((aes_key) => {
					AES.export_aes_key(aes_key)
					.then((raw_key) => {
						AES.import_aes_key(raw_key)
						.then((aes_key) => {
							AES.encryption(JSON.stringify({"username" : "willy", "password": "nilly"}), aes_key)
							.then((struct) => {
								console.log(struct)
							})
						})
					})
				})
			})
		})
	})
})

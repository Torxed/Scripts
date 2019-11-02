#!/usr/bin/python3
# -*- coding: utf-8 -*-

import yubico
import os
import binascii
import string
from Crypto.Cipher import AES

def Program():
    try:
        yk = yubico.find_yubikey(debug=False)
        print("Version : %s " % yk.version())
    except yubico.yubico_exception.YubicoError as e:
        print("ERROR: %s" % e.reason)
        return

    cfg = yk.init_config()

    key = binascii.hexlify(os.urandom(16))
    keyFixed = binascii.hexlify(os.urandom(16))

    cfg.aes_key("h:" + key.decode("utf-8"))
    cfg.config_flag('STATIC_TICKET', True)
    cfg.fixed_string("h:" + keyFixed.decode("utf-8"))
    yk.write_config(cfg, slot=1) 

    # Predict aes128 result and add the fixed key
    ## This is a static key, no idea where it comes from.
    fixed = b'000000000000ffffffffffffffff0f2e' 
    enc = AES.new(binascii.unhexlify(key), AES.MODE_CBC, b'\x00' * 16)
    data = enc.encrypt(binascii.unhexlify(fixed))
    
    # translate 
    #key = binascii.hexlify(os.urandom(16))
    try:
        # Python 2
        maketrans = string.maketrans
    except AttributeError:
        # Python 3
        maketrans = bytes.maketrans
    t_map = maketrans(b"0123456789abcdef", b"cbdefghijklnrtuv")

    outKey = binascii.hexlify(data).translate(t_map).decode("utf-8")
    outKeyFixed = keyFixed.decode("utf-8").translate(t_map)

    print("The whole key is: {}{}".format(outKeyFixed, outKey))

if __name__ == "__main__":
    Program()

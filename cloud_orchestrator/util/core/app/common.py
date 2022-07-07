from copy import deepcopy
    
    
def recr_dict(_dict, func):
    _tmp = deepcopy(_dict)
    for key, value in _dict.items():
        if isinstance(value, dict):
            _tmp[key] = recr_dict(value, func)
        elif isinstance(value, str):
            if key.startswith('__e__'):
                _value = func(_tmp.pop(key))
                _tmp[key.strip('__e__')] = _value.strip()
            else:
                _tmp[key] = value.strip()
    return _tmp



import base64
from Crypto.Cipher import AES

BS = 16
pad = lambda s: bytes(s + (BS - len(s) % BS) * chr(BS - len(s) % BS), 'utf-8')
unpad = lambda s : s[0:-ord(s[-1:])]
class AESCipher:

    def __init__(self, key, iv):
        self.key = bytes(key, 'utf-8')
        self.iv = bytes(iv, 'utf-8')

    def encrypt( self, raw ):
        raw = pad(raw)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return base64.b64encode(cipher.encrypt( raw ) )

    def decrypt( self, enc ):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return unpad(cipher.decrypt(base64.b64decode(enc))).decode('utf8')
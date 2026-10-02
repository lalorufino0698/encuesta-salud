import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

def encrypt_password(plain_text):
    key_string = "SgDPasswordSecretPasswor"
    sha1 = hashlib.sha1()
    sha1.update(key_string.encode('utf-8'))
    key = sha1.digest()[:16] 
    
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plain_text.encode('utf-8')) + padder.finalize()
    
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded_data) + encryptor.finalize()
    return ct.hex().upper()

def decrypt_password(hex_string):
    key_string = "SgDPasswordSecretPasswor"
    sha1 = hashlib.sha1()
    sha1.update(key_string.encode('utf-8'))
    key = sha1.digest()[:16] 
    
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    decryptor = cipher.decryptor()
    ct = bytes.fromhex(hex_string)
    padded_data = decryptor.update(ct) + decryptor.finalize()
    
    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()
    return data.decode('utf-8')

print("ADMIN encrypted:", encrypt_password("ADMIN"))
print("ADMIN test decrypt:", decrypt_password("BC7C1B7868D616458085C3B3910E5978CB672E7A618F08F4804F63EADA6EA19D"))


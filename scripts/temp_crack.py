import hashlib
target = "CC24EE1B7E78C8881FDF4AF9EF04694E"

common = ["123456", "12345678", "1234", "12345", "password", "admin", "123456789", "1234567", "111111", "000000", "0000", "123123"]
for p in common:
    if hashlib.md5(p.encode()).hexdigest().upper() == target:
        print("MD5:", p)
    if hashlib.md5(hashlib.md5(p.encode()).hexdigest().encode()).hexdigest().upper() == target:
        print("Double MD5:", p)
    if hashlib.sha256(p.encode()).hexdigest().upper()[:32] == target:
        print("SHA256 half:", p)

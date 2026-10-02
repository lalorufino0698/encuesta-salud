import hashlib
target = "CC24EE1B7E78C8881FDF4AF9EF04694E"

words = ["CAFED", "cafed", "SGD", "sgd", "ADMIN", "admin", "123", "1234", "12345", "123456", "12345678", "password", "clave", "usuario", "sistema"]
for w in words:
    if hashlib.md5(w.encode()).hexdigest().upper() == target:
        print("FOUND:", w)
    if hashlib.md5((w+"cafed").encode()).hexdigest().upper() == target:
        print("FOUND:", w)

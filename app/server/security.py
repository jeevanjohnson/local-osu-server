from hashlib import md5
from bcrypt import checkpw, gensalt, hashpw


def hash_password(password: str) -> bytes:
    password_md5 = md5(password.encode()).hexdigest()
    return hashpw(password_md5.encode(), gensalt())


def check_password(password: str, hashword: bytes):
    checkpw(password.encode(), hashword)

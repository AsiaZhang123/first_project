from hashlib import sha1


def get_hash(password):
    sh = sha1()
    sh.update(password.encode('utf-8'))
    return sh.hexdigest()
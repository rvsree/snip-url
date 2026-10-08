import hashlib


# Return the salted sha256 hex digest of an ip address.
def hash_ip(ip: str, salt: str) -> str:
    return hashlib.sha256((salt + ":" + ip).encode("utf-8")).hexdigest()

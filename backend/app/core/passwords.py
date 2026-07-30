from pwdlib import PasswordHash

# argon2id — pwdlib's recommended default, and the current consensus choice
# for password storage (memory-hard, so it resists GPU cracking far better
# than bcrypt). Unlike the share-link tokens in app/modules/shares/tokens.py,
# a *slow* hash is exactly what's wanted here: passwords are low-entropy and
# human-chosen, so making each guess expensive is the whole defence.
_hasher = PasswordHash.recommended()

MIN_PASSWORD_LENGTH = 8


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """False rather than raising on a malformed/absent hash — an invited user
    who hasn't set a password yet has none, and that's a normal 'wrong
    credentials' outcome, not an error worth a 500."""
    if not hashed:
        return False
    try:
        return _hasher.verify(plain, hashed)
    except Exception:
        return False

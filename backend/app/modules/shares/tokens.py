import hashlib
import secrets

# 32 bytes of CSPRNG output, URL-safe encoded (~43 characters). The link is
# the credential, so this is the number that has to make guessing hopeless:
# 2^256 possibilities means brute force is not a realistic attack even
# against an endpoint with no rate limiting.
_TOKEN_BYTES = 32


def generate_token() -> str:
    """A fresh share token. `secrets`, never `random` — the latter is a
    predictable PRNG, and a predictable share token is a public document."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """What actually gets stored.

    Plain SHA-256 rather than a slow password hash (bcrypt/argon2) on
    purpose: those exist to make *low-entropy* human passwords expensive to
    guess. A 256-bit random token has nothing to guess, so the slow hash
    would buy no security while adding real latency to every public page
    view. Storing the hash still means a leaked database yields no usable
    links."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

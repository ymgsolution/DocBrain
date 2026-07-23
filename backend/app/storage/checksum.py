import hashlib
from typing import BinaryIO


def sha256_of_stream(stream: BinaryIO, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.sha256()
    for chunk in iter(lambda: stream.read(chunk_size), b""):
        hasher.update(chunk)
    return hasher.hexdigest()

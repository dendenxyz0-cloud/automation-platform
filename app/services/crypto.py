from __future__ import annotations

import os

from cryptography.fernet import Fernet


def get_fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY") or os.getenv("SECRET_KEY")
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is not configured")

    normalized = key.encode("utf-8")
    if len(normalized) < 32:
        normalized = normalized.ljust(32, b"0")
    if len(normalized) > 32:
        normalized = normalized[:32]

    return Fernet(base64_urlsafe(normalized))


def base64_urlsafe(value: bytes) -> bytes:
    import base64

    return base64.urlsafe_b64encode(value)

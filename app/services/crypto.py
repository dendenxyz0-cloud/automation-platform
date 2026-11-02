from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class CredentialEncryptionError(ValueError):
    pass


def _fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY") or settings.ENCRYPTION_KEY
    if not key:
        raise CredentialEncryptionError("ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise CredentialEncryptionError("ENCRYPTION_KEY is not a valid Fernet key") from exc


def encrypt_credentials(plaintext: str) -> str:
    if not plaintext:
        raise CredentialEncryptionError("Credentials cannot be empty")
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_credentials(ciphertext: str) -> str:
    if not ciphertext:
        raise CredentialEncryptionError("Encrypted credentials cannot be empty")
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise CredentialEncryptionError("Credentials could not be decrypted") from exc

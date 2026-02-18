"""Encryption service for storing API keys at rest."""

from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet() -> Fernet:
    key = settings.master_encryption_key
    # If the key doesn't look like a valid Fernet key, generate a deterministic one
    # In production, always set a proper Fernet key via env
    if len(key) < 32:
        import hashlib
        import base64
        derived = hashlib.sha256(key.encode()).digest()
        key = base64.urlsafe_b64encode(derived).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value. Returns base64 ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt an encrypted value."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()

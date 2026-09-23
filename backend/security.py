"""Security utilities — API key encryption, token handling, etc.

Sprint 6: AES-256-GCM encryption for BYOK API keys.
In production, the master key should come from a KMS (AWS KMS, GCP KMS, HashiCorp Vault).
For development, we derive from an env var.
"""

from __future__ import annotations

import os
from base64 import b64decode, b64encode
from typing import Final

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# In production, this key should be fetched from a KMS.
# For dev, we derive from an env var (must be 32 bytes for AES-256).
# Generate with: python -c "import os; print(os.urandom(32).hex())"
_MASTER_KEY_HEX: Final[str] = os.environ.get("MASTER_ENCRYPTION_KEY", "0" * 64)

if len(_MASTER_KEY_HEX) != 64:
    raise ValueError("MASTER_ENCRYPTION_KEY must be a 64-character hex string (32 bytes)")

_MASTER_KEY: Final[bytes] = bytes.fromhex(_MASTER_KEY_HEX)


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key using AES-256-GCM.

    Returns a base64-encoded string: nonce(12) + ciphertext + tag(16)
    """
    if not plaintext:
        return ""

    aesgcm = AESGCM(_MASTER_KEY)
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # nonce + ciphertext (includes tag at the end)
    return b64encode(nonce + ciphertext).decode("ascii")


def decrypt_api_key(encrypted_b64: str) -> str:
    """Decrypt an API key encrypted with encrypt_api_key()."""
    if not encrypted_b64:
        return ""

    data = b64decode(encrypted_b64)
    if len(data) < 12 + 16:  # nonce(12) + min ciphertext(1) + tag(16)
        raise ValueError("Invalid encrypted data: too short")

    nonce = data[:12]
    ciphertext = data[12:]

    aesgcm = AESGCM(_MASTER_KEY)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def generate_master_key_hex() -> str:
    """Generate a new 32-byte master key as hex. Run once and store securely."""
    return os.urandom(32).hex()


__all__ = ["encrypt_api_key", "decrypt_api_key", "generate_master_key_hex", "generate_token_hash"]


def generate_token_hash(length: int = 32) -> str:
    """Generate a cryptographically secure random token hash."""
    return os.urandom(length).hex()
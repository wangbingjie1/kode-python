"""
Encryption utilities for sensitive data.

Provides Fernet symmetric encryption for database passwords and other secrets.
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Manages encryption/decryption of sensitive data using Fernet.

    Uses ENCRYPTION_KEY environment variable or generates a key from SECRET_KEY.
    """

    _instance: Optional["EncryptionManager"] = None
    _fernet: Optional[Fernet] = None

    def __new__(cls) -> "EncryptionManager":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize encryption with key from environment."""
        if self._fernet is not None:
            return

        # Try to get encryption key from environment
        encryption_key = os.getenv("ENCRYPTION_KEY")

        if encryption_key:
            # Use provided encryption key
            try:
                # Ensure key is properly formatted (32 url-safe base64 bytes)
                if len(encryption_key) == 44 and encryption_key.endswith("="):
                    key = encryption_key.encode()
                else:
                    # Derive key from provided string
                    key = self._derive_key_from_password(encryption_key)

                self._fernet = Fernet(key)
                logger.info("Encryption initialized with ENCRYPTION_KEY")
            except Exception as e:
                logger.error(f"Invalid ENCRYPTION_KEY: {e}")
                raise ValueError(
                    "ENCRYPTION_KEY is invalid. Generate a valid key with: "
                    "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
        else:
            # Fallback: derive from SECRET_KEY (less secure but works)
            secret_key = os.getenv("SECRET_KEY")
            if not secret_key:
                raise ValueError(
                    "Either ENCRYPTION_KEY or SECRET_KEY environment variable must be set. "
                    "Generate ENCRYPTION_KEY with: "
                    "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )

            key = self._derive_key_from_password(secret_key)
            self._fernet = Fernet(key)
            logger.warning(
                "Encryption initialized from SECRET_KEY. "
                "For better security, set ENCRYPTION_KEY environment variable."
            )

    def _derive_key_from_password(self, password: str) -> bytes:
        """
        Derive a Fernet-compatible key from a password using PBKDF2.

        Args:
            password: Password string

        Returns:
            32-byte key encoded as base64
        """
        # Use fixed salt for deterministic key derivation
        # In production, consider storing salt separately
        salt = b"kode-encryption-salt-v1"

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""

        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""

        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data - encryption key may have changed")


# Global singleton instance
encryption_manager = EncryptionManager()


def encrypt_password(password: str) -> str:
    """Convenience function to encrypt a password."""
    return encryption_manager.encrypt(password)


def decrypt_password(encrypted_password: str) -> str:
    """Convenience function to decrypt a password."""
    return encryption_manager.decrypt(encrypted_password)

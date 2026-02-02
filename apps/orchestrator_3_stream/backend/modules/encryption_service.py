#!/usr/bin/env python3
"""
Credential Encryption Service

Provides Fernet-based symmetric encryption for credential storage.
This service is the foundation for all credential storage in the multi-tenant system.

Security considerations:
- Uses Fernet (AES-128-CBC with HMAC-SHA256) for authenticated encryption
- Encryption key loaded from ENCRYPTION_KEY environment variable
- Never logs credential values (plaintext or ciphertext)
- Singleton pattern to ensure single key instance
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

from modules.logger import OrchestratorLogger

# Initialize logger
logger = OrchestratorLogger("encryption_service")

# Singleton instance
_encryption_service_instance: Optional["CredentialEncryptionService"] = None


class CredentialEncryptionService:
    """
    Credential encryption service using Fernet symmetric encryption.

    This service encrypts and decrypts credentials for safe storage.
    The encryption key is loaded from the ENCRYPTION_KEY environment variable.

    Example:
        service = get_encryption_service()
        encrypted = service.encrypt("my-api-key-123")
        decrypted = service.decrypt(encrypted)
        assert decrypted == "my-api-key-123"
    """

    def __init__(self):
        """
        Initialize the encryption service.

        Raises:
            ValueError: If ENCRYPTION_KEY environment variable is not set.
        """
        encryption_key = os.getenv("ENCRYPTION_KEY", "")

        if not encryption_key:
            error_msg = (
                "ENCRYPTION_KEY environment variable is not set. "
                "Generate a key with:\n"
                "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
                "Then add it to your .env file:\n"
                "  ENCRYPTION_KEY=<generated-key>"
            )
            logger.error("Encryption key not configured")
            raise ValueError(error_msg)

        try:
            # Initialize Fernet cipher with the encryption key
            # The key must be 32 url-safe base64-encoded bytes
            self._cipher = Fernet(encryption_key.encode('ascii'))
            logger.info("Credential encryption service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption service: {e}")
            raise ValueError(
                f"Invalid ENCRYPTION_KEY format. Expected base64-encoded Fernet key. "
                f"Generate a valid key with: "
                f"python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            ) from e

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string to base64-encoded ciphertext.

        Args:
            plaintext: The plaintext string to encrypt (e.g., API key, password)

        Returns:
            Base64-encoded ciphertext string

        Raises:
            ValueError: If plaintext is None

        Example:
            encrypted = service.encrypt("my-secret-api-key")
            # Returns: "gAAAAABf..."
        """
        if plaintext is None:
            logger.error("Attempted to encrypt None value")
            raise ValueError("Cannot encrypt None value")

        # Handle empty strings (return empty string, no encryption needed)
        if plaintext == "":
            return ""

        try:
            # Encode plaintext to bytes (UTF-8 encoding)
            plaintext_bytes = plaintext.encode('utf-8')

            # Encrypt with Fernet (returns bytes)
            ciphertext_bytes = self._cipher.encrypt(plaintext_bytes)

            # Decode to ASCII string (Fernet output is base64, which is ASCII-safe)
            ciphertext = ciphertext_bytes.decode('ascii')

            return ciphertext

        except Exception as e:
            # Log error but NEVER log the plaintext value
            logger.error(f"Encryption failed: {type(e).__name__}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt base64-encoded ciphertext back to plaintext.

        Args:
            ciphertext: Base64-encoded ciphertext string (from encrypt())

        Returns:
            Original plaintext string

        Raises:
            InvalidToken: If ciphertext is corrupted or was encrypted with different key

        Example:
            plaintext = service.decrypt("gAAAAABf...")
            # Returns: "my-secret-api-key"
        """
        # Handle empty strings (return empty string, no decryption needed)
        if ciphertext == "":
            return ""

        try:
            # Encode ciphertext to bytes (ASCII encoding)
            ciphertext_bytes = ciphertext.encode('ascii')

            # Decrypt with Fernet (returns bytes)
            plaintext_bytes = self._cipher.decrypt(ciphertext_bytes)

            # Decode to UTF-8 string
            plaintext = plaintext_bytes.decode('utf-8')

            return plaintext

        except InvalidToken as e:
            # Log error but NEVER log the ciphertext value
            logger.error("Decryption failed: Invalid token (corrupted or wrong key)")
            raise
        except Exception as e:
            # Log error but NEVER log the ciphertext value
            logger.error(f"Decryption failed: {type(e).__name__}")
            raise


def get_encryption_service() -> CredentialEncryptionService:
    """
    Get the singleton encryption service instance.

    This function lazily initializes the service on first call to avoid
    creating it at import time (env vars may not be loaded yet).

    Returns:
        Singleton CredentialEncryptionService instance

    Raises:
        ValueError: If ENCRYPTION_KEY is not set

    Example:
        service = get_encryption_service()
        encrypted = service.encrypt("my-api-key")
    """
    global _encryption_service_instance

    if _encryption_service_instance is None:
        _encryption_service_instance = CredentialEncryptionService()

    return _encryption_service_instance

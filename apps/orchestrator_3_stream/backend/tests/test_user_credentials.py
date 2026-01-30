#!/usr/bin/env python3
"""
Tests for user credentials with encryption.

Tests verify:
1. EncryptedString TypeDecorator encrypts/decrypts correctly
2. Credentials stored encrypted in database (not plaintext)
3. Round-trip encryption works for Alpaca key formats
4. Edge cases (empty strings, special characters, None values) handled

Test strategy:
- Use monkeypatch to set ENCRYPTION_KEY for test isolation
- Test TypeDecorator methods directly (unit tests)
- Test with Alpaca-specific key formats (PK..., sp...)
- Database integration tests require DATABASE_URL (marked with skip)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from cryptography.fernet import Fernet


class TestEncryptedStringTypeDecorator:
    """Test EncryptedString TypeDecorator in isolation."""

    @pytest.fixture
    def test_encryption_key(self, monkeypatch):
        """Generate a test encryption key and set it in environment."""
        # Generate a valid Fernet key for testing
        test_key = Fernet.generate_key().decode("ascii")
        monkeypatch.setenv("ENCRYPTION_KEY", test_key)
        return test_key

    def test_encrypt_decrypt_round_trip(self, test_encryption_key):
        """Verify encrypt then decrypt returns original value."""
        from modules.user_models import EncryptedString

        type_decorator = EncryptedString(500)

        test_values = [
            "PK0123456789ABCDEF",  # Alpaca API key format
            "sp0123456789abcdefghijklmnop",  # Alpaca secret format
            "special!@#$%^&*()chars",  # Special characters
            "unicode_test_\u00e9\u00e8\u00ea",  # Unicode characters
        ]

        for plaintext in test_values:
            encrypted = type_decorator.process_bind_param(plaintext, None)
            decrypted = type_decorator.process_result_value(encrypted, None)
            assert (
                decrypted == plaintext
            ), f"Round-trip failed for: {plaintext}"

    def test_none_handling(self, test_encryption_key):
        """Verify None values pass through unchanged."""
        from modules.user_models import EncryptedString

        type_decorator = EncryptedString(500)

        # None should pass through without encryption
        assert type_decorator.process_bind_param(None, None) is None
        assert type_decorator.process_result_value(None, None) is None

    def test_encrypted_value_different_from_plaintext(self, test_encryption_key):
        """Verify encrypted value is not the same as plaintext."""
        from modules.user_models import EncryptedString

        type_decorator = EncryptedString(500)
        plaintext = "my-secret-api-key"

        encrypted = type_decorator.process_bind_param(plaintext, None)

        assert (
            encrypted != plaintext
        ), "Encrypted value should differ from plaintext"
        assert len(encrypted) > len(
            plaintext
        ), "Encrypted value should be longer (includes signature)"

    def test_empty_string_handling(self, test_encryption_key):
        """Verify empty strings are handled correctly."""
        from modules.user_models import EncryptedString

        type_decorator = EncryptedString(500)

        # Empty string should pass through (encryption service returns "")
        encrypted = type_decorator.process_bind_param("", None)
        decrypted = type_decorator.process_result_value(encrypted, None)

        assert encrypted == "", "Empty string should remain empty when encrypted"
        assert decrypted == "", "Empty string should remain empty when decrypted"

    def test_multiple_encryptions_different_ciphertext(self, test_encryption_key):
        """Verify same plaintext encrypts to different ciphertext (IV randomization)."""
        from modules.user_models import EncryptedString

        type_decorator = EncryptedString(500)
        plaintext = "test-api-key-123"

        # Encrypt same value twice
        encrypted1 = type_decorator.process_bind_param(plaintext, None)
        encrypted2 = type_decorator.process_bind_param(plaintext, None)

        # Ciphertexts should differ (Fernet uses random IV)
        assert (
            encrypted1 != encrypted2
        ), "Fernet should produce different ciphertext on each encryption"

        # But both should decrypt to same plaintext
        decrypted1 = type_decorator.process_result_value(encrypted1, None)
        decrypted2 = type_decorator.process_result_value(encrypted2, None)

        assert decrypted1 == plaintext
        assert decrypted2 == plaintext


class TestAlpacaCredentialFormats:
    """Test with real Alpaca credential format patterns."""

    @pytest.fixture
    def test_encryption_key(self, monkeypatch):
        """Generate a test encryption key and set it in environment."""
        test_key = Fernet.generate_key().decode("ascii")
        monkeypatch.setenv("ENCRYPTION_KEY", test_key)
        return test_key

    def test_alpaca_api_key_format(self, test_encryption_key):
        """Test Alpaca API key format: PK followed by alphanumeric."""
        from modules.encryption_service import get_encryption_service

        service = get_encryption_service()

        # Real Alpaca key patterns
        api_keys = [
            "PKABCDEF1234567890",  # Live key format
            "PKTEST12345678901",  # Test key format
            "PK1234567890ABCDEF1234567890AB",  # Longer format
        ]

        for key in api_keys:
            encrypted = service.encrypt(key)
            decrypted = service.decrypt(encrypted)
            assert (
                decrypted == key
            ), f"Round-trip failed for Alpaca API key: {key}"

    def test_alpaca_secret_key_format(self, test_encryption_key):
        """Test Alpaca secret key format: lowercase alphanumeric."""
        from modules.encryption_service import get_encryption_service

        service = get_encryption_service()

        # Real Alpaca secret patterns
        secrets = [
            "abcdefghijklmnopqrstuvwxyz1234567890",
            "sp1234567890abcdefghijklmnopqrstuv",
            "test123secret456key789",
        ]

        for secret in secrets:
            encrypted = service.encrypt(secret)
            decrypted = service.decrypt(encrypted)
            assert (
                decrypted == secret
            ), f"Round-trip failed for Alpaca secret: {secret}"

    def test_alpaca_credentials_through_type_decorator(self, test_encryption_key):
        """Test Alpaca credentials through EncryptedString TypeDecorator."""
        from modules.user_models import EncryptedString

        type_decorator = EncryptedString(500)

        # Simulate storing Alpaca credentials
        alpaca_credentials = {
            "api_key": "PKTEST1234567890ABCDEF",
            "secret_key": "sp0123456789abcdefghijklmnopqrstuv",
        }

        for field, value in alpaca_credentials.items():
            encrypted = type_decorator.process_bind_param(value, None)
            decrypted = type_decorator.process_result_value(encrypted, None)
            assert (
                decrypted == value
            ), f"Round-trip failed for {field}: {value}"


class TestEncryptionServiceIntegration:
    """Test integration with encryption service from Phase 1."""

    @pytest.fixture
    def test_encryption_key(self, monkeypatch):
        """Generate a test encryption key and set it in environment."""
        test_key = Fernet.generate_key().decode("ascii")
        monkeypatch.setenv("ENCRYPTION_KEY", test_key)
        return test_key

    def test_uses_singleton_encryption_service(self, test_encryption_key):
        """Verify EncryptedString uses singleton encryption service."""
        from modules.user_models import EncryptedString
        from modules.encryption_service import get_encryption_service

        # Get service directly
        service1 = get_encryption_service()

        # TypeDecorator should use same singleton
        type_decorator = EncryptedString(500)

        test_value = "test-credential-123"

        # Encrypt with service
        encrypted_by_service = service1.encrypt(test_value)

        # Decrypt with TypeDecorator (should use same service)
        decrypted_by_decorator = type_decorator.process_result_value(
            encrypted_by_service, None
        )

        assert (
            decrypted_by_decorator == test_value
        ), "TypeDecorator should use same encryption service"

    def test_encryption_service_error_handling(self, monkeypatch):
        """Verify encryption service errors are propagated correctly."""
        # Set invalid encryption key
        monkeypatch.setenv("ENCRYPTION_KEY", "invalid-key")

        # Should raise error on service initialization
        with pytest.raises(ValueError, match="Invalid ENCRYPTION_KEY format"):
            from modules.encryption_service import (
                CredentialEncryptionService,
            )

            CredentialEncryptionService()


class TestORMModelIntegration:
    """Test ORM model integration with EncryptedString."""

    @pytest.fixture
    def test_encryption_key(self, monkeypatch):
        """Generate a test encryption key and set it in environment."""
        test_key = Fernet.generate_key().decode("ascii")
        monkeypatch.setenv("ENCRYPTION_KEY", test_key)
        return test_key

    def test_user_credential_orm_has_encrypted_columns(self, test_encryption_key):
        """Verify UserCredentialORM has EncryptedString columns."""
        from modules.user_models import UserCredentialORM, EncryptedString

        # Check that api_key and secret_key columns use EncryptedString
        api_key_column = UserCredentialORM.__table__.columns["api_key"]
        secret_key_column = UserCredentialORM.__table__.columns["secret_key"]

        assert isinstance(
            api_key_column.type, EncryptedString
        ), "api_key should use EncryptedString type"
        assert isinstance(
            secret_key_column.type, EncryptedString
        ), "secret_key should use EncryptedString type"

    def test_user_account_orm_relationship(self, test_encryption_key):
        """Verify UserAccountORM has relationship to UserCredentialORM."""
        from modules.user_models import UserAccountORM

        # Check relationship exists
        assert hasattr(
            UserAccountORM, "credentials"
        ), "UserAccountORM should have credentials relationship"

        # Check relationship configuration
        relationship = UserAccountORM.credentials.property
        assert (
            relationship.cascade.delete_orphan
        ), "Relationship should cascade delete"


class TestCredentialDatabaseIntegration:
    """Integration tests with actual database (requires DATABASE_URL)."""

    @pytest.mark.skipif(
        not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set"
    )
    def test_credential_stored_encrypted_in_db(self):
        """
        Verify credential is encrypted when stored in database.

        This test requires actual database connection.
        Creates credential, then queries raw SQL to verify encryption.

        TODO: Implement when database integration is available.
        Will need to:
        1. Create a test session
        2. Insert UserCredentialORM with plaintext credentials
        3. Query database with raw SQL
        4. Verify stored values are encrypted (not plaintext)
        5. Clean up test data
        """
        pass  # Implementation depends on database setup


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def test_encryption_key(self, monkeypatch):
        """Generate a test encryption key and set it in environment."""
        test_key = Fernet.generate_key().decode("ascii")
        monkeypatch.setenv("ENCRYPTION_KEY", test_key)
        return test_key

    def test_very_long_credential_string(self, test_encryption_key):
        """Test encryption of very long credential strings."""
        from modules.user_models import EncryptedString

        type_decorator = EncryptedString(500)

        # Generate a long credential (512 characters)
        long_credential = "a" * 512

        encrypted = type_decorator.process_bind_param(long_credential, None)
        decrypted = type_decorator.process_result_value(encrypted, None)

        assert decrypted == long_credential, "Should handle long credentials"

    def test_credential_with_newlines(self, test_encryption_key):
        """Test credentials containing newline characters."""
        from modules.user_models import EncryptedString

        type_decorator = EncryptedString(500)

        # Some credentials might contain newlines
        credential_with_newlines = "line1\nline2\nline3"

        encrypted = type_decorator.process_bind_param(
            credential_with_newlines, None
        )
        decrypted = type_decorator.process_result_value(encrypted, None)

        assert (
            decrypted == credential_with_newlines
        ), "Should preserve newlines"

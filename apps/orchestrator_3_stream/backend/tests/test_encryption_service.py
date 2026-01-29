#!/usr/bin/env python3
"""
Tests for CredentialEncryptionService

Tests encryption round-trip, edge cases, and error handling per Phase 1 requirements.
Run with: cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_encryption_service.py -v
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from cryptography.fernet import Fernet, InvalidToken


class TestCredentialEncryptionService:
    """Tests for CredentialEncryptionService"""

    @pytest.fixture(autouse=True)
    def setup_encryption_key(self, monkeypatch):
        """Set up a test encryption key for each test"""
        test_key = Fernet.generate_key().decode()
        monkeypatch.setenv("ENCRYPTION_KEY", test_key)
        # Clear any cached service instance
        import modules.encryption_service as enc_module
        enc_module._encryption_service_instance = None

    def test_encryption_round_trip_basic(self):
        """Test basic encrypt -> decrypt returns original value"""
        from modules.encryption_service import get_encryption_service

        service = get_encryption_service()
        original = "test-api-key-123"

        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)

        assert decrypted == original
        assert encrypted != original  # Should be different

    def test_encryption_round_trip_alpaca_format(self):
        """Test round-trip with Alpaca-style API keys"""
        from modules.encryption_service import get_encryption_service

        service = get_encryption_service()

        # Typical Alpaca API key format
        api_key = "PKABCDEF1234567890"
        encrypted = service.encrypt(api_key)
        decrypted = service.decrypt(encrypted)
        assert decrypted == api_key

        # Typical Alpaca secret key format
        secret_key = "sp0123456789abcdefghijklmnopqrstuvwxyz"
        encrypted = service.encrypt(secret_key)
        decrypted = service.decrypt(encrypted)
        assert decrypted == secret_key

    def test_encryption_round_trip_special_characters(self):
        """Test round-trip preserves special characters"""
        from modules.encryption_service import get_encryption_service

        service = get_encryption_service()
        test_cases = [
            "key!@#$%^&*()",
            "key with spaces",
            "key\twith\ttabs",
            "key\nwith\nnewlines",
            "unicode: éàü",
            "emoji: 🚀",
        ]

        for original in test_cases:
            encrypted = service.encrypt(original)
            decrypted = service.decrypt(encrypted)
            assert decrypted == original, f"Failed for: {repr(original)}"

    def test_empty_string_handling(self):
        """Test that empty strings are handled correctly"""
        from modules.encryption_service import get_encryption_service

        service = get_encryption_service()

        # Empty string should return empty string
        encrypted = service.encrypt("")
        assert encrypted == ""

        decrypted = service.decrypt("")
        assert decrypted == ""

    def test_none_input_raises_error(self):
        """Test that None input raises ValueError"""
        from modules.encryption_service import get_encryption_service

        service = get_encryption_service()

        with pytest.raises(ValueError, match="Cannot encrypt None"):
            service.encrypt(None)

    def test_invalid_ciphertext_raises_error(self):
        """Test that corrupted ciphertext raises InvalidToken"""
        from modules.encryption_service import get_encryption_service

        service = get_encryption_service()

        with pytest.raises(InvalidToken):
            service.decrypt("not-valid-ciphertext")

    def test_ciphertext_is_different_each_time(self):
        """Test that encrypting same value produces different ciphertext (IV changes)"""
        from modules.encryption_service import get_encryption_service

        service = get_encryption_service()
        original = "test-credential"

        encrypted1 = service.encrypt(original)
        encrypted2 = service.encrypt(original)

        # Fernet uses random IV, so ciphertext should differ
        assert encrypted1 != encrypted2

        # But both should decrypt to same value
        assert service.decrypt(encrypted1) == original
        assert service.decrypt(encrypted2) == original

    def test_singleton_returns_same_instance(self):
        """Test that get_encryption_service returns singleton"""
        from modules.encryption_service import get_encryption_service

        service1 = get_encryption_service()
        service2 = get_encryption_service()

        assert service1 is service2


class TestEncryptionKeyValidation:
    """Tests for encryption key validation"""

    def test_missing_encryption_key_raises_error(self, monkeypatch):
        """Test that missing ENCRYPTION_KEY raises ValueError"""
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

        # Clear cached instance
        import modules.encryption_service as enc_module
        enc_module._encryption_service_instance = None

        from modules.encryption_service import CredentialEncryptionService

        with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
            CredentialEncryptionService()

    def test_invalid_encryption_key_raises_error(self, monkeypatch):
        """Test that invalid ENCRYPTION_KEY raises ValueError"""
        monkeypatch.setenv("ENCRYPTION_KEY", "not-a-valid-fernet-key")

        # Clear cached instance
        import modules.encryption_service as enc_module
        enc_module._encryption_service_instance = None

        from modules.encryption_service import CredentialEncryptionService

        with pytest.raises(ValueError, match="Invalid ENCRYPTION_KEY"):
            CredentialEncryptionService()


class TestLogRedaction:
    """Tests for credential redaction in logs"""

    def test_api_key_redacted_in_logs(self):
        """Test that API keys are redacted from log output"""
        from modules.logger import CredentialRedactionFilter
        import logging

        filter_instance = CredentialRedactionFilter()

        test_cases = [
            ("ALPACA_API_KEY=PKabc123def456ghi", "ALPACA_API_KEY=***", "PKabc123def456ghi"),
            ("ALPACA_SECRET_KEY=sp0123456789abcdef", "ALPACA_SECRET_KEY=***", "sp0123456789abcdef"),
            ("ENCRYPTION_KEY=abcdefghijklmnop", "ENCRYPTION_KEY=***", "abcdefghijklmnop"),
            ('{"api_key": "secret123"}', '"api_key":"***"', "secret123"),
            ("Bearer eyJhbGciOiJIUzI1NiJ9.xxx", "Bearer ***", "eyJhbGciOiJIUzI1NiJ9.xxx"),
        ]

        for message, expected_redacted, sensitive_value in test_cases:
            record = logging.LogRecord("test", logging.INFO, "", 0, message, (), None)
            filter_instance.filter(record)
            # Check that sensitive value is not in output
            assert sensitive_value not in record.msg, f"Sensitive value exposed: {message} -> {record.msg}"
            # Check that redaction marker is present
            assert "***" in record.msg, f"Not redacted: {message} -> {record.msg}"

    def test_alpaca_key_formats_redacted(self):
        """Test that Alpaca-specific key formats are redacted"""
        from modules.logger import CredentialRedactionFilter
        import logging

        filter_instance = CredentialRedactionFilter()

        # Alpaca API key format: PK followed by 17+ alphanumeric
        api_key_msg = "Using key PK0123456789ABCDEFGH for trading"
        record = logging.LogRecord("test", logging.INFO, "", 0, api_key_msg, (), None)
        filter_instance.filter(record)
        assert "PK0123456789ABCDEFGH" not in record.msg
        assert "PK***" in record.msg

        # Alpaca secret key format: sp followed by 28+ alphanumeric
        secret_key_msg = "Secret: sp0123456789abcdefghijklmnopqrst"
        record = logging.LogRecord("test", logging.INFO, "", 0, secret_key_msg, (), None)
        filter_instance.filter(record)
        assert "sp0123456789abcdefghijklmnopqrst" not in record.msg
        assert "sp***" in record.msg

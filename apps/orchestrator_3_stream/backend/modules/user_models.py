#!/usr/bin/env python3
"""
SQLAlchemy ORM Models for User Accounts and Credentials

Provides ORM models with transparent encryption for credential storage.
Uses EncryptedString TypeDecorator for automatic encrypt/decrypt during database operations.

Security:
- EncryptedString encrypts on INSERT/UPDATE, decrypts on SELECT
- Uses Fernet encryption from Phase 1's encryption_service
- Credentials (api_key, secret_key) stored encrypted at rest
- Never exposes plaintext credentials to database layer

Models:
- UserAccountORM: User trading account metadata
- UserCredentialORM: Encrypted API credentials for Alpaca/Polygon
"""

import os
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    TypeDecorator,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import declarative_base, relationship

from modules.encryption_service import get_encryption_service

# Base class for all ORM models
Base = declarative_base()


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy TypeDecorator for transparent encryption/decryption.

    Uses Fernet encryption from Phase 1's encryption_service.
    Encrypts on INSERT/UPDATE, decrypts on SELECT.

    This ensures credentials are always encrypted at rest in the database,
    but appear as plaintext strings in application code.

    Example:
        class MyModel(Base):
            api_key = Column(EncryptedString(500))  # Stored encrypted

        # When you insert:
        obj = MyModel(api_key="PK123...")  # Plaintext in code
        session.add(obj)
        session.commit()  # Encrypted in DB

        # When you query:
        obj = session.query(MyModel).first()
        print(obj.api_key)  # Decrypted automatically: "PK123..."

    Security notes:
    - Database contains only encrypted values
    - Encryption key from ENCRYPTION_KEY environment variable
    - Decryption happens transparently on SELECT
    """

    impl = String
    cache_ok = True  # Safe to cache type; encryption service is singleton

    def __init__(self, length=None):
        """
        Initialize EncryptedString with optional length.

        Args:
            length: Maximum length for database column (optional).
                   Encrypted values are longer than plaintext, so use generous length.
                   Recommended: 500 for API keys/secrets
        """
        super().__init__()
        if length:
            self.impl = String(length)

    def process_bind_param(self, value, dialect):
        """
        Encrypt plaintext value before storing in database.

        Called automatically by SQLAlchemy on INSERT/UPDATE.

        Args:
            value: Plaintext string to encrypt (or None)
            dialect: SQLAlchemy database dialect (unused)

        Returns:
            Encrypted ciphertext string, or None if input was None
        """
        if value is None:
            return None

        service = get_encryption_service()
        return service.encrypt(str(value))

    def process_result_value(self, value, dialect):
        """
        Decrypt ciphertext value when reading from database.

        Called automatically by SQLAlchemy on SELECT.

        Args:
            value: Encrypted ciphertext string (or None)
            dialect: SQLAlchemy database dialect (unused)

        Returns:
            Decrypted plaintext string, or None if input was None
        """
        if value is None:
            return None

        service = get_encryption_service()
        return service.decrypt(value)


class UserAccountORM(Base):
    """
    SQLAlchemy ORM model for user_accounts table.

    Represents a user's trading account in the system.
    Each user can have multiple accounts (e.g., paper trading, live trading).

    Relationships:
    - credentials: One-to-many with UserCredentialORM (cascade delete)

    Example:
        account = UserAccountORM(
            user_id="user123",
            account_name="My Paper Trading Account",
            is_active=True
        )
        session.add(account)
        session.commit()
    """

    __tablename__ = "user_accounts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False, unique=True)  # FK to user.id
    account_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship to credentials (one account has many credentials)
    credentials = relationship(
        "UserCredentialORM",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("idx_user_accounts_user_id", "user_id"),)

    def __repr__(self):
        return (
            f"<UserAccountORM(id={self.id}, user_id={self.user_id}, "
            f"account_name={self.account_name}, is_active={self.is_active})>"
        )


class UserCredentialORM(Base):
    """
    SQLAlchemy ORM model for user_credentials table with encrypted columns.

    Stores API credentials for trading platforms (Alpaca, Polygon).
    api_key and secret_key columns use EncryptedString for transparent encryption.

    Security:
    - Credentials are encrypted at rest (EncryptedString TypeDecorator)
    - user_id denormalized for RLS performance (avoids joins)
    - Unique constraint on (user_account_id, credential_type) prevents duplicates

    Relationships:
    - account: Many-to-one with UserAccountORM

    Example:
        credential = UserCredentialORM(
            user_account_id=account.id,
            user_id="user123",
            credential_type="alpaca",
            api_key="PKABCDEF123...",  # Encrypted automatically
            secret_key="sp123abc...",  # Encrypted automatically
            is_active=True
        )
        session.add(credential)
        session.commit()

        # When queried:
        cred = session.query(UserCredentialORM).first()
        print(cred.api_key)  # Decrypted: "PKABCDEF123..."
    """

    __tablename__ = "user_credentials"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_account_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(String(255), nullable=False)  # Denormalized for RLS
    credential_type = Column(String(50), nullable=False)  # "alpaca", "polygon"
    api_key = Column(EncryptedString(500), nullable=False)  # Auto-encrypted
    secret_key = Column(EncryptedString(500), nullable=False)  # Auto-encrypted
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship back to account
    account = relationship("UserAccountORM", back_populates="credentials")

    __table_args__ = (
        Index("idx_user_credentials_user_id", "user_id"),
        Index("idx_user_credentials_account_id", "user_account_id"),
    )

    def __repr__(self):
        return (
            f"<UserCredentialORM(id={self.id}, user_id={self.user_id}, "
            f"credential_type={self.credential_type}, is_active={self.is_active})>"
        )


# Export public API
__all__ = [
    "Base",
    "EncryptedString",
    "UserAccountORM",
    "UserCredentialORM",
]

#!/usr/bin/env python3
"""
Credential Service with Decrypt-on-Demand Pattern

Provides functions for credential storage, retrieval, and validation.
Uses decrypt-on-demand pattern: credentials are decrypted only when needed
and plaintext is immediately discarded after use.

Security:
- get_decrypted_alpaca_credential is async context manager (auto-cleanup)
- Validates credential belongs to user_id before decrypting
- Validates credential is_active before returning
- Never logs credential values (plaintext or ciphertext)
- Uses TypeDecorator for transparent encryption/decryption

Functions:
- get_decrypted_alpaca_credential: Async context manager for decrypt-on-demand
- validate_alpaca_credentials: Validates credentials against Alpaca API
- store_credential: Stores encrypted credential in database
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Tuple
from uuid import UUID, uuid4

import httpx
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncConnection

from modules.user_models import UserCredentialORM, UserAccountORM
from modules.logger import OrchestratorLogger

# Initialize logger
logger = OrchestratorLogger("credential_service")

# Alpaca API base URLs
ALPACA_PAPER_BASE_URL = "https://paper-api.alpaca.markets"
ALPACA_LIVE_BASE_URL = "https://api.alpaca.markets"


@asynccontextmanager
async def get_decrypted_alpaca_credential(
    conn: AsyncConnection,
    credential_id: str,
    user_id: str,
) -> AsyncGenerator[Tuple[str, str], None]:
    """
    Async context manager for decrypt-on-demand credential retrieval.

    Fetches credential from database, validates ownership and active status,
    and yields decrypted (api_key, secret_key) tuple. Plaintext credentials
    are automatically discarded when context exits.

    Args:
        conn: SQLAlchemy async connection
        credential_id: UUID of credential to retrieve
        user_id: User ID to validate ownership

    Yields:
        Tuple[str, str]: (api_key, secret_key) as plaintext

    Raises:
        ValueError: If credential not found, doesn't belong to user, or is inactive

    Example:
        async with get_decrypted_alpaca_credential(conn, cred_id, user_id) as (api_key, secret_key):
            # Use credentials here
            result = await alpaca_api.get_account(api_key, secret_key)
        # Credentials automatically discarded here

    Security:
        - Validates credential belongs to user_id (prevents unauthorized access)
        - Validates credential is_active (prevents use of deactivated credentials)
        - TypeDecorator handles decryption transparently
        - Plaintext discarded on context exit (try/finally pattern)
    """
    api_key = None
    secret_key = None

    try:
        # Query credential by ID
        result = await conn.execute(
            select(UserCredentialORM).where(UserCredentialORM.id == UUID(credential_id))
        )
        credential = result.scalar_one_or_none()

        # Validate credential exists
        if credential is None:
            logger.error(f"Credential not found: {credential_id}")
            raise ValueError(f"Credential {credential_id} not found")

        # Validate credential belongs to user
        if credential.user_id != user_id:
            logger.error(
                f"Credential {credential_id} access denied for user {user_id}"
            )
            raise ValueError(f"Credential {credential_id} does not belong to user {user_id}")

        # Validate credential is active
        if not credential.is_active:
            logger.error(f"Credential {credential_id} is inactive")
            raise ValueError(f"Credential {credential_id} is inactive")

        # TypeDecorator automatically decrypts when accessing these attributes
        api_key = credential.api_key
        secret_key = credential.secret_key

        logger.info(
            f"Credential {credential_id} decrypted for user {user_id}"
        )

        # Yield plaintext credentials
        yield (api_key, secret_key)

    finally:
        # Ensure plaintext is discarded (set to None for garbage collection)
        api_key = None
        secret_key = None


async def validate_alpaca_credentials(
    api_key: str,
    secret_key: str,
    use_paper: bool = True,
) -> Tuple[bool, Optional[str]]:
    """
    Validate credentials against Alpaca API.

    Makes authenticated request to Alpaca GET /v2/account endpoint
    to verify credentials are valid.

    Args:
        api_key: Alpaca API key
        secret_key: Alpaca secret key
        use_paper: Whether to use paper trading API (default: True)

    Returns:
        Tuple[bool, Optional[str]]:
            - (True, "paper" | "live") if credentials are valid
            - (False, None) if credentials are invalid

    Example:
        is_valid, account_type = await validate_alpaca_credentials(
            "PKABCDEF123...",
            "sp123abc...",
            use_paper=True
        )
        if is_valid:
            print(f"Valid {account_type} credentials")

    Security:
        - NEVER logs credential values
        - Uses HTTPS for API calls
        - Validates response before returning
    """
    base_url = ALPACA_PAPER_BASE_URL if use_paper else ALPACA_LIVE_BASE_URL
    url = f"{base_url}/v2/account"

    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": secret_key,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)

            if response.status_code == 200:
                # Credentials are valid
                data = response.json()
                account_type = "paper" if use_paper else "live"

                logger.info(f"Credentials validated successfully (account_type: {account_type})")
                return (True, account_type)

            elif response.status_code in [401, 403]:
                # Authentication failed
                logger.warning("Credential validation failed: Invalid credentials")
                return (False, None)

            else:
                # Unexpected error
                logger.error(
                    f"Credential validation failed: Unexpected status {response.status_code}"
                )
                return (False, None)

    except httpx.TimeoutException:
        logger.error("Credential validation failed: API request timeout")
        return (False, None)

    except Exception as e:
        logger.error(f"Credential validation failed: {type(e).__name__}")
        return (False, None)


async def store_credential(
    conn: AsyncConnection,
    account_id: UUID,
    user_id: str,
    credential_type: str,
    api_key: str,
    secret_key: str,
) -> UUID:
    """
    Store encrypted credential in database.

    Creates UserCredentialORM instance and inserts into database.
    TypeDecorator automatically encrypts api_key and secret_key on INSERT.

    Args:
        conn: SQLAlchemy async connection
        account_id: UUID of user account (user_accounts.id)
        user_id: User ID (denormalized for RLS)
        credential_type: Credential type ("alpaca" or "polygon")
        api_key: Plaintext API key (will be encrypted)
        secret_key: Plaintext secret key (will be encrypted)

    Returns:
        UUID: ID of created credential

    Example:
        credential_id = await store_credential(
            conn,
            account_id=UUID("550e8400-..."),
            user_id="user123",
            credential_type="alpaca",
            api_key="PKABCDEF123...",
            secret_key="sp123abc..."
        )

    Security:
        - TypeDecorator encrypts api_key and secret_key before INSERT
        - Never logs credential values
        - Validates account exists before inserting
    """
    # Validate account exists and belongs to user
    result = await conn.execute(
        select(UserAccountORM).where(
            UserAccountORM.id == account_id,
            UserAccountORM.user_id == user_id,
        )
    )
    account = result.scalar_one_or_none()

    if account is None:
        logger.error(f"Account {account_id} not found for user {user_id}")
        raise ValueError(f"Account {account_id} not found or does not belong to user {user_id}")

    # Generate credential ID
    credential_id = uuid4()

    # Insert credential (TypeDecorator encrypts api_key and secret_key)
    await conn.execute(
        insert(UserCredentialORM).values(
            id=credential_id,
            user_account_id=account_id,
            user_id=user_id,
            credential_type=credential_type,
            api_key=api_key,  # Encrypted by TypeDecorator
            secret_key=secret_key,  # Encrypted by TypeDecorator
            is_active=True,
        )
    )

    logger.info(
        f"Credential stored: id={credential_id}, account_id={account_id}, type={credential_type}"
    )

    return credential_id


# Export public API
__all__ = [
    "get_decrypted_alpaca_credential",
    "validate_alpaca_credentials",
    "store_credential",
]

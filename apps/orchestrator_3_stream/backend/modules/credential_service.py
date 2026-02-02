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

from modules.logger import OrchestratorLogger

# Initialize logger
logger = OrchestratorLogger("credential_service")

# Alpaca API base URLs
ALPACA_PAPER_BASE_URL = "https://paper-api.alpaca.markets"
ALPACA_LIVE_BASE_URL = "https://api.alpaca.markets"


@asynccontextmanager
async def get_decrypted_alpaca_credential(
    conn,
    credential_id: str,
    user_id: str,
) -> AsyncGenerator[Tuple[str, str], None]:
    """
    Async context manager for decrypt-on-demand credential retrieval.

    Fetches credential from database, validates ownership and active status,
    and yields decrypted (api_key, secret_key) tuple. Plaintext credentials
    are automatically discarded when context exits.

    Args:
        conn: asyncpg connection (from get_connection_with_rls)
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
        - Decrypts using encryption service
        - Plaintext discarded on context exit (try/finally pattern)
    """
    api_key = None
    secret_key = None

    try:
        # Query credential by ID using raw SQL
        result = await conn.fetchrow(
            """
            SELECT id, user_id, api_key, secret_key, is_active
            FROM user_credentials
            WHERE id = $1
            """,
            UUID(credential_id),
        )

        # Validate credential exists
        if result is None:
            logger.error(f"Credential not found: {credential_id}")
            raise ValueError(f"Credential {credential_id} not found")

        # Validate credential belongs to user
        if result["user_id"] != user_id:
            logger.error(
                f"Credential {credential_id} access denied for user {user_id}"
            )
            raise ValueError(f"Credential {credential_id} does not belong to user {user_id}")

        # Validate credential is active
        if not result["is_active"]:
            logger.error(f"Credential {credential_id} is inactive")
            raise ValueError(f"Credential {credential_id} is inactive")

        # Decrypt credentials using encryption service
        from modules.encryption_service import get_encryption_service
        encryption_service = get_encryption_service()
        api_key = encryption_service.decrypt(result["api_key"])
        secret_key = encryption_service.decrypt(result["secret_key"])

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
    conn,
    account_id: UUID,
    user_id: str,
    credential_type: str,
    api_key: str,
    secret_key: str,
    nickname: Optional[str] = None,
) -> UUID:
    """
    Store encrypted credential in database.

    Uses raw SQL with asyncpg connection. Encrypts api_key and secret_key
    using the encryption service before INSERT.

    Args:
        conn: asyncpg connection (from get_connection_with_rls)
        account_id: UUID of user account (user_accounts.id)
        user_id: User ID (denormalized for RLS)
        credential_type: Credential type ("alpaca" or "polygon")
        api_key: Plaintext API key (will be encrypted)
        secret_key: Plaintext secret key (will be encrypted)
        nickname: User-friendly label (defaults to credential_type if not provided)

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
        - Encrypts api_key and secret_key before INSERT
        - Never logs credential values
        - Validates account exists before inserting
    """
    # Validate account exists and belongs to user
    result = await conn.fetchrow(
        """
        SELECT id FROM user_accounts
        WHERE id = $1 AND user_id = $2
        """,
        account_id,
        user_id,
    )

    if result is None:
        logger.error(f"Account {account_id} not found for user {user_id}")
        raise ValueError(f"Account {account_id} not found or does not belong to user {user_id}")

    # Default nickname to credential_type if not provided
    if nickname is None or nickname.strip() == "":
        nickname = credential_type

    # Generate credential ID
    credential_id = uuid4()

    # Encrypt credentials using encryption service
    from modules.encryption_service import get_encryption_service
    encryption_service = get_encryption_service()
    encrypted_api_key = encryption_service.encrypt(api_key)
    encrypted_secret_key = encryption_service.encrypt(secret_key)

    # Insert credential with encrypted values
    await conn.execute(
        """
        INSERT INTO user_credentials (
            id, user_account_id, user_id, credential_type,
            api_key, secret_key, nickname, is_active, created_at, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
        """,
        credential_id,
        account_id,
        user_id,
        credential_type,
        encrypted_api_key,
        encrypted_secret_key,
        nickname,
        True,
    )

    logger.info(
        f"Credential stored: id={credential_id}, account_id={account_id}, "
        f"type={credential_type}, nickname={nickname}"
    )

    return credential_id


# Export public API
__all__ = [
    "get_decrypted_alpaca_credential",
    "validate_alpaca_credentials",
    "store_credential",
]

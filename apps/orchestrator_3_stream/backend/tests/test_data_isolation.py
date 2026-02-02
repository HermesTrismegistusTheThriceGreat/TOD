#!/usr/bin/env python3
"""
Integration tests for RLS (Row-Level Security) data isolation.

Tests verify that PostgreSQL RLS policies correctly isolate user data:
1. User A cannot see User B's credentials (database-level isolation)
2. Users can only see their own credentials
3. RLS context is required for queries
4. Multiple users with credentials are isolated correctly

These tests use real database connections (no mocking per CLAUDE.md) with
ephemeral test data (create -> test -> cleanup).

Run with: cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_data_isolation.py -v
"""

import pytest
import sys
from pathlib import Path
from uuid import uuid4
from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.database import get_connection_with_rls, init_pool, close_pool, set_rls_context


# ═══════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def test_encryption_key(monkeypatch):
    """Generate and set test encryption key"""
    test_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("ENCRYPTION_KEY", test_key)
    return test_key


@pytest.fixture
def user_a_id():
    """Generate temporary User A ID for testing"""
    return f"test-user-a-{uuid4()}"


@pytest.fixture
def user_b_id():
    """Generate temporary User B ID for testing"""
    return f"test-user-b-{uuid4()}"


# ═══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════


async def create_test_user(user_id: str, name: str) -> None:
    """Create a test user in the user table"""
    from modules.database import get_connection

    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO "user" (id, name, email)
            VALUES ($1, $2, $3)
            """,
            user_id,
            name,
            f"{user_id}@example.com",
        )


async def delete_test_user(user_id: str) -> None:
    """Delete a test user from the user table"""
    from modules.database import get_connection

    async with get_connection() as conn:
        await conn.execute('DELETE FROM "user" WHERE id = $1', user_id)


# ═══════════════════════════════════════════════════════════
# TESTS: RLS CREDENTIAL ISOLATION
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_user_a_cannot_see_user_b_credentials(test_encryption_key, user_a_id, user_b_id):
    """
    Test that User A cannot see User B's credentials via RLS filtering.

    Scenario:
    1. Create user records for User A and User B
    2. Create account and credential for User B
    3. Query credentials with User A's RLS context
    4. Assert: User A's query returns empty result (RLS filtered User B's data)
    """
    from modules.encryption_service import get_encryption_service
    from modules.database import get_connection

    await init_pool()

    try:
        service = get_encryption_service()
        account_b_id = uuid4()
        credential_id = uuid4()

        # Create user records in user table (required for foreign key constraint)
        await create_test_user(user_a_id, "Test User A")
        await create_test_user(user_b_id, "Test User B")

        # User B creates account and credential
        async with get_connection_with_rls(user_b_id) as conn:
            # Create account
            await conn.execute(
                """
                INSERT INTO user_accounts (id, user_id, account_name, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                """,
                account_b_id,
                user_b_id,
                "User B Test Account",
            )

            # Create credential
            await conn.execute(
                """
                INSERT INTO user_credentials (
                    id, user_account_id, user_id, credential_type, nickname,
                    api_key, secret_key, is_active, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                """,
                credential_id,
                account_b_id,
                user_b_id,
                "alpaca_paper",
                "User B Paper Account",
                service.encrypt("PKUSERB123456"),
                service.encrypt("spuserb123456"),
                True,
            )

        # User A tries to query credentials (should see NONE due to RLS)
        async with get_connection_with_rls(user_a_id) as conn:
            result = await conn.fetch("SELECT * FROM user_credentials")

            # Assert: User A cannot see User B's credential
            assert len(result) == 0, "User A should NOT see User B's credentials (RLS isolation)"

        # Cleanup User B's data
        async with get_connection_with_rls(user_b_id) as conn:
            await conn.execute("DELETE FROM user_credentials WHERE id = $1", credential_id)
            await conn.execute("DELETE FROM user_accounts WHERE id = $1", account_b_id)

        # Delete user records
        await delete_test_user(user_a_id)
        await delete_test_user(user_b_id)

    finally:
        await close_pool()


@pytest.mark.asyncio
async def test_user_can_see_own_credentials(test_encryption_key, user_a_id):
    """
    Test that a user can see their own credentials with RLS context.

    Scenario:
    1. Create user record for User A
    2. Create account and credential for User A
    3. Query with User A's RLS context
    4. Assert: Credential is returned
    """
    from modules.encryption_service import get_encryption_service

    await init_pool()

    try:
        service = get_encryption_service()
        account_id = uuid4()
        credential_id = uuid4()

        # Create user record
        await create_test_user(user_a_id, "Test User A")

        # User A creates account and credential
        async with get_connection_with_rls(user_a_id) as conn:
            # Create account
            await conn.execute(
                """
                INSERT INTO user_accounts (id, user_id, account_name, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                """,
                account_id,
                user_a_id,
                "User A Test Account",
            )

            # Create credential
            await conn.execute(
                """
                INSERT INTO user_credentials (
                    id, user_account_id, user_id, credential_type, nickname,
                    api_key, secret_key, is_active, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                """,
                credential_id,
                account_id,
                user_a_id,
                "alpaca_paper",
                "User A Paper Account",
                service.encrypt("PKUSERA123456"),
                service.encrypt("spusera123456"),
                True,
            )

        # User A queries their credentials
        async with get_connection_with_rls(user_a_id) as conn:
            result = await conn.fetch("SELECT * FROM user_credentials WHERE id = $1", credential_id)

            # Assert: User A can see their own credential
            assert len(result) == 1, "User A should see their own credential"
            assert result[0]["id"] == credential_id
            assert result[0]["user_id"] == user_a_id
            assert result[0]["credential_type"] == "alpaca_paper"

        # Cleanup
        async with get_connection_with_rls(user_a_id) as conn:
            await conn.execute("DELETE FROM user_credentials WHERE id = $1", credential_id)
            await conn.execute("DELETE FROM user_accounts WHERE id = $1", account_id)

        await delete_test_user(user_a_id)

    finally:
        await close_pool()


@pytest.mark.asyncio
async def test_rls_context_required_for_queries(test_encryption_key, user_a_id):
    """
    Test that queries without RLS context return empty results (fail-safe behavior).

    Scenario:
    1. Create user record for User A
    2. Create account and credential for User A
    3. Query WITHOUT setting RLS context (use raw connection)
    4. Assert: Either returns empty or RLS policy enforces null current_user_id()

    Note: With FORCE ROW LEVEL SECURITY, even superuser connections must set RLS context.
    """
    from modules.encryption_service import get_encryption_service
    from modules.database import get_connection

    await init_pool()

    try:
        service = get_encryption_service()
        account_id = uuid4()
        credential_id = uuid4()

        # Create user record
        await create_test_user(user_a_id, "Test User A")

        # User A creates account and credential
        async with get_connection_with_rls(user_a_id) as conn:
            # Create account
            await conn.execute(
                """
                INSERT INTO user_accounts (id, user_id, account_name, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                """,
                account_id,
                user_a_id,
                "User A Test Account",
            )

            # Create credential
            await conn.execute(
                """
                INSERT INTO user_credentials (
                    id, user_account_id, user_id, credential_type, nickname,
                    api_key, secret_key, is_active, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                """,
                credential_id,
                account_id,
                user_a_id,
                "alpaca_paper",
                "User A Paper Account",
                service.encrypt("PKUSERA123456"),
                service.encrypt("spusera123456"),
                True,
            )

        # Query WITHOUT RLS context (raw connection)
        async with get_connection() as conn:
            result = await conn.fetch("SELECT * FROM user_credentials WHERE id = $1", credential_id)

            # Assert: No results returned (RLS enforces isolation even without explicit context)
            # current_user_id() returns NULL when session variable not set, so no rows match
            assert len(result) == 0, "Query without RLS context should return empty (fail-safe)"

        # Cleanup
        async with get_connection_with_rls(user_a_id) as conn:
            await conn.execute("DELETE FROM user_credentials WHERE id = $1", credential_id)
            await conn.execute("DELETE FROM user_accounts WHERE id = $1", account_id)

        await delete_test_user(user_a_id)

    finally:
        await close_pool()


@pytest.mark.asyncio
async def test_credential_isolation_with_multiple_users(test_encryption_key, user_a_id, user_b_id):
    """
    Test comprehensive isolation with multiple users having credentials.

    Scenario:
    1. Create user records for User A and User B
    2. User A creates account and credential
    3. User B creates account and credential
    4. Query with User A's context -> only User A's credential returned
    5. Query with User B's context -> only User B's credential returned
    """
    from modules.encryption_service import get_encryption_service

    await init_pool()

    try:
        service = get_encryption_service()
        account_a_id = uuid4()
        account_b_id = uuid4()
        cred_a_id = uuid4()
        cred_b_id = uuid4()

        # Create user records
        await create_test_user(user_a_id, "Test User A")
        await create_test_user(user_b_id, "Test User B")

        # User A creates account and credential
        async with get_connection_with_rls(user_a_id) as conn:
            # Create account
            await conn.execute(
                """
                INSERT INTO user_accounts (id, user_id, account_name, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                """,
                account_a_id,
                user_a_id,
                "User A Test Account",
            )

            # Create credential
            await conn.execute(
                """
                INSERT INTO user_credentials (
                    id, user_account_id, user_id, credential_type, nickname,
                    api_key, secret_key, is_active, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                """,
                cred_a_id,
                account_a_id,
                user_a_id,
                "alpaca_paper",
                "User A Paper",
                service.encrypt("PKUSERA111"),
                service.encrypt("spusera111"),
                True,
            )

        # User B creates account and credential
        async with get_connection_with_rls(user_b_id) as conn:
            # Create account
            await conn.execute(
                """
                INSERT INTO user_accounts (id, user_id, account_name, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                """,
                account_b_id,
                user_b_id,
                "User B Test Account",
            )

            # Create credential
            await conn.execute(
                """
                INSERT INTO user_credentials (
                    id, user_account_id, user_id, credential_type, nickname,
                    api_key, secret_key, is_active, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                """,
                cred_b_id,
                account_b_id,
                user_b_id,
                "alpaca_paper",
                "User B Paper",
                service.encrypt("PKUSERB222"),
                service.encrypt("spuserb222"),
                True,
            )

        # User A queries credentials -> should ONLY see their own
        async with get_connection_with_rls(user_a_id) as conn:
            result = await conn.fetch("SELECT * FROM user_credentials ORDER BY created_at")

            assert len(result) == 1, "User A should see exactly 1 credential (their own)"
            assert result[0]["id"] == cred_a_id
            assert result[0]["user_id"] == user_a_id
            assert result[0]["nickname"] == "User A Paper"

        # User B queries credentials -> should ONLY see their own
        async with get_connection_with_rls(user_b_id) as conn:
            result = await conn.fetch("SELECT * FROM user_credentials ORDER BY created_at")

            assert len(result) == 1, "User B should see exactly 1 credential (their own)"
            assert result[0]["id"] == cred_b_id
            assert result[0]["user_id"] == user_b_id
            assert result[0]["nickname"] == "User B Paper"

        # Cleanup
        async with get_connection_with_rls(user_a_id) as conn:
            await conn.execute("DELETE FROM user_credentials WHERE id = $1", cred_a_id)
            await conn.execute("DELETE FROM user_accounts WHERE id = $1", account_a_id)
        async with get_connection_with_rls(user_b_id) as conn:
            await conn.execute("DELETE FROM user_credentials WHERE id = $1", cred_b_id)
            await conn.execute("DELETE FROM user_accounts WHERE id = $1", account_b_id)

        await delete_test_user(user_a_id)
        await delete_test_user(user_b_id)

    finally:
        await close_pool()

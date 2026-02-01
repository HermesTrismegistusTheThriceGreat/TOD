#!/usr/bin/env python3
"""
Debug script to verify RLS is working.

This script checks if Row-Level Security is actually enabled and functioning.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.database import init_pool, close_pool, get_connection, set_rls_context


async def check_rls_status():
    """Check if RLS is enabled on user_credentials table"""
    await init_pool()

    async with get_connection() as conn:
        # Check current user and privileges
        user_info = await conn.fetchrow("""
            SELECT current_user, usesuper, usebypassrls
            FROM pg_user
            WHERE usename = current_user
        """)
        print(f"\nCurrent database user: {user_info['current_user']}")
        print(f"Is superuser: {user_info['usesuper']}")
        print(f"Bypass RLS: {user_info['usebypassrls']} ⚠️  THIS IS THE PROBLEM!")

        # Check if RLS is enabled
        result = await conn.fetchrow(
            """
            SELECT relname, relrowsecurity, relforcerowsecurity
            FROM pg_class
            WHERE relname = 'user_credentials'
            """
        )
        print(f"\nRLS Status for user_credentials:")
        print(f"  Table: {result['relname']}")
        print(f"  RLS Enabled: {result['relrowsecurity']}")
        print(f"  Force RLS: {result['relforcerowsecurity']}")

        # Check policies
        policies = await conn.fetch(
            """
            SELECT policyname, cmd, qual
            FROM pg_policies
            WHERE tablename = 'user_credentials'
            """
        )
        print(f"\n  Policies ({len(policies)}):")
        for policy in policies:
            print(f"    - {policy['policyname']} ({policy['cmd']})")

        # Check current_user_id() function
        result = await conn.fetchval("SELECT current_user_id()")
        print(f"\n  current_user_id() without context: {result}")

        # Set context and check again IN A TRANSACTION
        async with conn.transaction():
            await conn.execute("SET LOCAL app.current_user_id = 'test-user-123'")
            result = await conn.fetchval("SELECT current_user_id()")
            print(f"  current_user_id() with context (in transaction): {result}")

            # Count total credentials
            total = await conn.fetchval("SELECT COUNT(*) FROM user_credentials")
            print(f"\n  Total credentials in database (with RLS context in transaction): {total}")

            # Debug: Check what RLS policy is actually evaluating
            sample = await conn.fetch(
                """
                SELECT user_id, credential_type,
                       user_id = current_user_id() as matches_policy,
                       current_user_id() as expected_user_id
                FROM user_credentials
                LIMIT 3
                """
            )
            print(f"\n  Sample credentials (should be filtered by RLS):")
            for row in sample:
                print(f"    user_id={row['user_id'][:20]}... matches={row['matches_policy']} (expected={row['expected_user_id']})")

    # Try querying without context
    async with get_connection() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM user_credentials")
        print(f"  Total credentials (no RLS context): {total}")

    await close_pool()


if __name__ == "__main__":
    asyncio.run(check_rls_status())

#!/usr/bin/env python3
"""
User Account API Router

FastAPI router for user_accounts CRUD operations with row-level security enforcement.

Endpoints:
- GET /api/accounts - List user's accounts (RLS-filtered)
- POST /api/accounts - Create new account
- POST /api/accounts/get-or-create - Get existing or create default account (idempotent)

Security:
- All endpoints require authentication via get_current_user
- RLS context enforced via get_connection_with_rls
- Each user can only access their own accounts
- Logs operations without exposing sensitive data

Purpose:
Frontend needs to know which user_account_id to associate credentials with.
This router provides the account management layer that was missing.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from modules.auth_middleware import get_current_user, AuthUser
from modules.database import get_connection_with_rls
from modules.user_models import UserAccountORM
from modules.logger import get_logger
from schemas.account_schemas import (
    UserAccountResponse,
    ListAccountsResponse,
    CreateAccountRequest,
    GetOrCreateAccountResponse,
)

# Initialize logger
logger = get_logger()

# Create router
router = APIRouter(prefix="/api/accounts", tags=["Accounts"])


@router.get("", response_model=ListAccountsResponse)
async def list_accounts_endpoint(
    user: AuthUser = Depends(get_current_user),
):
    """
    List user's accounts.

    RLS filters to only authenticated user's accounts. Returns metadata only.

    Args:
        user: Current authenticated user

    Returns:
        ListAccountsResponse with list of user's accounts
    """
    try:
        logger.info(f"Listing accounts for user {user.id}")

        async with get_connection_with_rls(user.id) as conn:
            # Query accounts (RLS filters to user's rows)
            result = await conn.fetch(
                """
                SELECT id, user_id, account_name, is_active, created_at, updated_at
                FROM user_accounts
                ORDER BY created_at DESC
                """
            )

            accounts = [
                UserAccountResponse(
                    id=str(row["id"]),
                    user_id=row["user_id"],
                    account_name=row["account_name"],
                    is_active=row["is_active"],
                    created_at=row["created_at"].isoformat(),
                    updated_at=row["updated_at"].isoformat(),
                )
                for row in result
            ]

            logger.info(f"Found {len(accounts)} accounts")

            return ListAccountsResponse(
                status="success",
                accounts=accounts,
                count=len(accounts),
            )

    except Exception as e:
        logger.error(f"Failed to list accounts: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("", response_model=UserAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account_endpoint(
    request: CreateAccountRequest,
    user: AuthUser = Depends(get_current_user),
):
    """
    Create new user account.

    Validates:
    - User is authenticated
    - Account name is provided
    - user_id is unique (one account per user constraint)

    Args:
        request: CreateAccountRequest with account_name
        user: Current authenticated user

    Returns:
        UserAccountResponse with created account metadata

    Raises:
        HTTPException: 409 if user already has an account (unique constraint)
    """
    try:
        logger.info(f"Creating account for user {user.id}: {request.account_name}")

        async with get_connection_with_rls(user.id) as conn:
            # Insert new account
            row = await conn.fetchrow(
                """
                INSERT INTO user_accounts (user_id, account_name, is_active)
                VALUES ($1, $2, $3)
                RETURNING id, user_id, account_name, is_active, created_at, updated_at
                """,
                user.id,
                request.account_name,
                True,
            )

            logger.info(f"Account created: {row['id']}")

            return UserAccountResponse(
                id=str(row["id"]),
                user_id=row["user_id"],
                account_name=row["account_name"],
                is_active=row["is_active"],
                created_at=row["created_at"].isoformat(),
                updated_at=row["updated_at"].isoformat(),
            )

    except IntegrityError:
        logger.warning(f"Duplicate account for user {user.id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User {user.id} already has an account. Use GET /api/accounts to retrieve it.",
        )
    except Exception as e:
        logger.error(f"Failed to create account: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/get-or-create", response_model=GetOrCreateAccountResponse)
async def get_or_create_account_endpoint(
    user: AuthUser = Depends(get_current_user),
):
    """
    Get existing account or create default account.

    This endpoint is idempotent - safe to call multiple times.
    If user has an account, returns it. If not, creates "Default Alpaca Account".

    This is useful for initialization flows where the frontend needs to ensure
    an account exists before adding credentials.

    Args:
        user: Current authenticated user

    Returns:
        GetOrCreateAccountResponse with account and created flag
    """
    try:
        logger.info(f"Get-or-create account for user {user.id}")

        async with get_connection_with_rls(user.id) as conn:
            # Try to get existing account
            existing = await conn.fetchrow(
                """
                SELECT id, user_id, account_name, is_active, created_at, updated_at
                FROM user_accounts
                WHERE user_id = $1
                LIMIT 1
                """,
                user.id,
            )

            if existing:
                logger.info(f"Found existing account: {existing['id']}")
                return GetOrCreateAccountResponse(
                    account=UserAccountResponse(
                        id=str(existing["id"]),
                        user_id=existing["user_id"],
                        account_name=existing["account_name"],
                        is_active=existing["is_active"],
                        created_at=existing["created_at"].isoformat(),
                        updated_at=existing["updated_at"].isoformat(),
                    ),
                    created=False,
                )

            # No existing account, create default
            logger.info(f"Creating default account for user {user.id}")
            row = await conn.fetchrow(
                """
                INSERT INTO user_accounts (user_id, account_name, is_active)
                VALUES ($1, $2, $3)
                RETURNING id, user_id, account_name, is_active, created_at, updated_at
                """,
                user.id,
                "Default Alpaca Account",
                True,
            )

            logger.info(f"Default account created: {row['id']}")

            return GetOrCreateAccountResponse(
                account=UserAccountResponse(
                    id=str(row["id"]),
                    user_id=row["user_id"],
                    account_name=row["account_name"],
                    is_active=row["is_active"],
                    created_at=row["created_at"].isoformat(),
                    updated_at=row["updated_at"].isoformat(),
                ),
                created=True,
            )

    except Exception as e:
        logger.error(f"Failed to get-or-create account: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Export router
__all__ = ["router"]

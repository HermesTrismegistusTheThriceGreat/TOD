#!/usr/bin/env python3
"""
Pydantic Schemas for User Account API

Provides request/response models for user_accounts management endpoints.
Follows the same patterns as credential_schemas.py for consistency.

Security:
- Account data includes no sensitive information (safe to expose in responses)
- RLS policies ensure users can only access their own accounts
- All timestamps returned in ISO 8601 format

Schemas:
- UserAccountResponse: Account metadata response
- ListAccountsResponse: Response for listing accounts
- CreateAccountRequest: Request to create new account
- GetOrCreateAccountResponse: Response from get-or-create endpoint
"""

from typing import List
from pydantic import BaseModel, Field, ConfigDict


class UserAccountResponse(BaseModel):
    """
    Response containing user account metadata.

    Returns account information without sensitive data.
    All timestamps are in ISO 8601 format for frontend parsing.

    Example:
        response = UserAccountResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            user_id="user_123",
            account_name="My Trading Account",
            is_active=True,
            created_at="2026-01-31T14:00:00Z",
            updated_at="2026-01-31T14:00:00Z"
        )
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Account ID (UUID)")
    user_id: str = Field(..., description="User ID (from Better Auth)")
    account_name: str = Field(..., description="Display name for the account")
    is_active: bool = Field(..., description="Whether account is active")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    updated_at: str = Field(..., description="Last update timestamp (ISO 8601)")


class ListAccountsResponse(BaseModel):
    """
    Response for listing user accounts.

    Returns list of account metadata for the authenticated user.

    Example:
        response = ListAccountsResponse(
            status="success",
            accounts=[account1, account2],
            count=2
        )
    """

    status: str = Field(..., description="Response status")
    accounts: List[UserAccountResponse] = Field(
        ...,
        description="List of user accounts"
    )
    count: int = Field(..., description="Number of accounts returned")


class CreateAccountRequest(BaseModel):
    """
    Request to create a new user account.

    Requires only the account name - user_id is automatically set from auth context.

    Example:
        request = CreateAccountRequest(
            account_name="My Paper Trading Account"
        )
    """

    account_name: str = Field(
        ...,
        description="Display name for the account",
        min_length=1,
        max_length=255
    )


class GetOrCreateAccountResponse(BaseModel):
    """
    Response from get-or-create endpoint.

    Returns the account (existing or newly created) along with a flag
    indicating whether it was just created.

    This is useful for idempotent initialization flows where the frontend
    needs to ensure an account exists before adding credentials.

    Example:
        # First call (creates account)
        response = GetOrCreateAccountResponse(
            account=UserAccountResponse(...),
            created=True
        )

        # Subsequent calls (returns existing)
        response = GetOrCreateAccountResponse(
            account=UserAccountResponse(...),
            created=False
        )
    """

    account: UserAccountResponse = Field(
        ...,
        description="The user account (existing or newly created)"
    )
    created: bool = Field(
        ...,
        description="True if account was just created, False if it already existed"
    )


# Export public API
__all__ = [
    "UserAccountResponse",
    "ListAccountsResponse",
    "CreateAccountRequest",
    "GetOrCreateAccountResponse",
]

#!/usr/bin/env python3
"""
Pydantic Schemas for Credential API

Provides request/response models for credential management endpoints.
Uses SecretStr to mask sensitive credential values in logs and error messages.

Security:
- api_key and secret_key fields use SecretStr type for automatic masking
- CredentialResponse NEVER includes plaintext credentials
- All credential values masked in string representation and logs

Schemas:
- StoreCredentialRequest: Request to store new credential
- UpdateCredentialRequest: Request to update existing credential
- CredentialResponse: Credential metadata (NO plaintext credentials)
- ValidateCredentialRequest: Request to validate credentials
- ValidateCredentialResponse: Validation result with account type
- ListCredentialsResponse: Response for listing credentials
"""

from typing import List, Optional
from pydantic import BaseModel, Field, SecretStr, ConfigDict


class StoreCredentialRequest(BaseModel):
    """
    Request to store a new credential.

    Uses SecretStr for api_key and secret_key to ensure they are masked
    in logs, error messages, and string representations.

    Example:
        request = StoreCredentialRequest(
            account_id="550e8400-e29b-41d4-a716-446655440000",
            credential_type="alpaca",
            api_key=SecretStr("PKABCDEF123..."),
            secret_key=SecretStr("sp123abc...")
        )
        # str(request) will mask the credential values
    """

    account_id: str = Field(
        ...,
        description="UUID of the user account (user_accounts.id)"
    )
    credential_type: str = Field(
        ...,
        description="Type of credential: 'alpaca' or 'polygon'"
    )
    api_key: SecretStr = Field(
        ...,
        description="API key (masked in logs and errors)"
    )
    secret_key: SecretStr = Field(
        ...,
        description="Secret key (masked in logs and errors)"
    )


class UpdateCredentialRequest(BaseModel):
    """
    Request to update an existing credential.

    All fields are optional. Only provided fields will be updated.
    Uses SecretStr for api_key and secret_key to ensure masking.

    Example:
        request = UpdateCredentialRequest(
            api_key=SecretStr("PKNEW123..."),
            is_active=True
        )
    """

    api_key: Optional[SecretStr] = Field(
        None,
        description="New API key (masked in logs and errors)"
    )
    secret_key: Optional[SecretStr] = Field(
        None,
        description="New secret key (masked in logs and errors)"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Whether the credential is active"
    )


class CredentialResponse(BaseModel):
    """
    Response containing credential metadata.

    IMPORTANT: This response NEVER includes plaintext credentials.
    Only metadata is exposed (id, type, status, timestamps).

    Clients must use decrypt-on-demand pattern via dedicated endpoints
    to retrieve plaintext credentials when needed.

    Example:
        response = CredentialResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            account_id="123e4567-e89b-12d3-a456-426614174000",
            credential_type="alpaca",
            is_active=True,
            created_at="2026-01-31T14:00:00Z",
            updated_at="2026-01-31T14:00:00Z"
        )
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Credential ID (UUID)")
    account_id: str = Field(..., description="User account ID (UUID)")
    credential_type: str = Field(..., description="Credential type (alpaca/polygon)")
    is_active: bool = Field(..., description="Whether credential is active")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    updated_at: str = Field(..., description="Last update timestamp (ISO 8601)")


class ValidateCredentialRequest(BaseModel):
    """
    Request to validate credentials against external API.

    Uses SecretStr to mask credential values in logs and errors.

    Example:
        request = ValidateCredentialRequest(
            api_key=SecretStr("PKABCDEF123..."),
            secret_key=SecretStr("sp123abc...")
        )
    """

    api_key: SecretStr = Field(
        ...,
        description="API key to validate (masked in logs and errors)"
    )
    secret_key: SecretStr = Field(
        ...,
        description="Secret key to validate (masked in logs and errors)"
    )


class ValidateCredentialResponse(BaseModel):
    """
    Response from credential validation.

    Indicates whether credentials are valid and, if successful,
    the account type (paper or live).

    Example:
        # Success
        response = ValidateCredentialResponse(
            is_valid=True,
            message="Credentials validated successfully",
            account_type="paper"
        )

        # Failure
        response = ValidateCredentialResponse(
            is_valid=False,
            message="Invalid credentials",
            account_type=None
        )
    """

    is_valid: bool = Field(..., description="Whether credentials are valid")
    message: str = Field(..., description="Validation message")
    account_type: Optional[str] = Field(
        None,
        description="Account type if valid: 'paper' or 'live'"
    )


class ListCredentialsResponse(BaseModel):
    """
    Response for listing credentials.

    Returns list of credential metadata (no plaintext credentials).

    Example:
        response = ListCredentialsResponse(
            status="success",
            credentials=[credential1, credential2],
            count=2
        )
    """

    status: str = Field(..., description="Response status")
    credentials: List[CredentialResponse] = Field(
        ...,
        description="List of credential metadata"
    )
    count: int = Field(..., description="Number of credentials returned")


# Export public API
__all__ = [
    "StoreCredentialRequest",
    "UpdateCredentialRequest",
    "CredentialResponse",
    "ValidateCredentialRequest",
    "ValidateCredentialResponse",
    "ListCredentialsResponse",
]

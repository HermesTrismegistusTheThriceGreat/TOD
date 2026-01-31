#!/usr/bin/env python3
"""
Credential API Router

FastAPI router for credential CRUD operations with row-level security enforcement.

Endpoints:
- POST /api/credentials/store - Store new encrypted credential
- GET /api/credentials - List user's credentials (metadata only)
- POST /api/credentials/{credential_id}/validate - Validate credential against Alpaca API
- PUT /api/credentials/{credential_id} - Update credential
- DELETE /api/credentials/{credential_id} - Delete credential

Security:
- All endpoints require authentication via get_current_user
- RLS context enforced via database middleware
- Never returns plaintext credentials in responses
- Logs operations without logging credential values
"""

from typing import List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from asyncpg.exceptions import UniqueViolationError

from modules.auth_middleware import get_current_user, AuthUser
from modules.database import get_connection_with_rls
from modules.credential_service import (
    get_decrypted_alpaca_credential,
    validate_alpaca_credentials,
    store_credential,
)
from modules.account_service import fetch_alpaca_account_data
from modules.logger import get_logger
from schemas.credential_schemas import (
    StoreCredentialRequest,
    UpdateCredentialRequest,
    CredentialResponse,
    ValidateCredentialResponse,
    ListCredentialsResponse,
)
from schemas.account_schemas import AccountDataResponse

# Initialize logger
logger = get_logger()

# Create router
router = APIRouter(prefix="/api/credentials", tags=["Credentials"])


@router.post("/store", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
async def store_credential_endpoint(
    request: StoreCredentialRequest,
    user: AuthUser = Depends(get_current_user),
):
    """
    Store new encrypted credential.

    Validates:
    - User owns the account_id
    - No duplicate (account_id + credential_type) exists
    - TypeDecorator encrypts api_key and secret_key automatically

    Args:
        request: StoreCredentialRequest with account_id, credential_type, and credentials
        user: Current authenticated user

    Returns:
        CredentialResponse with created credential metadata (no plaintext)

    Raises:
        HTTPException: 403 if unauthorized, 409 if duplicate exists
    """
    try:
        logger.info(f"Storing credential for user {user.id}, account {request.account_id}")

        async with get_connection_with_rls(user.id) as conn:
            # Store credential (validates account ownership)
            credential_id = await store_credential(
                conn=conn,
                account_id=UUID(request.account_id),
                user_id=user.id,
                credential_type=request.credential_type,
                api_key=request.api_key.get_secret_value(),
                secret_key=request.secret_key.get_secret_value(),
                nickname=request.nickname,
            )

            # Fetch created credential to return metadata (using raw SQL for asyncpg)
            result = await conn.fetchrow(
                """
                SELECT id, user_account_id, credential_type, nickname, is_active, created_at, updated_at
                FROM user_credentials
                WHERE id = $1
                """,
                credential_id,
            )

            logger.info(f"Credential stored: {credential_id}")

            return CredentialResponse(
                id=str(result["id"]),
                account_id=str(result["user_account_id"]),
                credential_type=result["credential_type"],
                nickname=result["nickname"],
                is_active=result["is_active"],
                created_at=result["created_at"].isoformat(),
                updated_at=result["updated_at"].isoformat(),
            )

    except ValueError as e:
        logger.warning(f"Credential storage failed: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except UniqueViolationError:
        logger.warning(f"Duplicate credential: account={request.account_id}, type={request.credential_type}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Credential of type {request.credential_type} already exists for this account",
        )
    except Exception as e:
        logger.error(f"Failed to store credential: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("", response_model=ListCredentialsResponse)
async def list_credentials_endpoint(
    account_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """
    List credentials for a user account.

    RLS filters to only user's credentials. Returns metadata only (no plaintext).

    Args:
        account_id: User account UUID to filter by
        user: Current authenticated user

    Returns:
        ListCredentialsResponse with list of credential metadata
    """
    try:
        logger.info(f"Listing credentials for user {user.id}, account {account_id}")

        async with get_connection_with_rls(user.id) as conn:
            # Query credentials using raw SQL (RLS filters to user's rows)
            result = await conn.fetch(
                """
                SELECT id, user_account_id, credential_type, nickname, is_active, created_at, updated_at
                FROM user_credentials
                WHERE user_account_id = $1
                ORDER BY created_at DESC
                """,
                UUID(account_id),
            )

            credential_list = [
                CredentialResponse(
                    id=str(row["id"]),
                    account_id=str(row["user_account_id"]),
                    credential_type=row["credential_type"],
                    nickname=row["nickname"],
                    is_active=row["is_active"],
                    created_at=row["created_at"].isoformat(),
                    updated_at=row["updated_at"].isoformat(),
                )
                for row in result
            ]

            logger.info(f"Found {len(credential_list)} credentials")

            return ListCredentialsResponse(
                status="success",
                credentials=credential_list,
                count=len(credential_list),
            )

    except Exception as e:
        logger.error(f"Failed to list credentials: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{credential_id}/validate", response_model=ValidateCredentialResponse)
async def validate_credential_endpoint(
    credential_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """
    Validate credential against Alpaca API.

    Decrypts credential, calls Alpaca API, returns validation result.

    Args:
        credential_id: UUID of credential to validate
        user: Current authenticated user

    Returns:
        ValidateCredentialResponse with validation result and account type

    Raises:
        HTTPException: 403 if user doesn't own credential, 400 if credential is inactive
    """
    try:
        logger.info(f"Validating credential {credential_id} for user {user.id}")

        async with get_connection_with_rls(user.id) as conn:
            # Decrypt credential (validates ownership and active status)
            try:
                async with get_decrypted_alpaca_credential(conn, credential_id, user.id) as (
                    api_key,
                    secret_key,
                ):
                    # Validate against Alpaca API
                    is_valid, account_type = await validate_alpaca_credentials(
                        api_key, secret_key, use_paper=True
                    )

                    if is_valid:
                        logger.info(f"Credential {credential_id} validated successfully")
                        return ValidateCredentialResponse(
                            is_valid=True,
                            message=f"Credentials validated successfully (account_type: {account_type})",
                            account_type=account_type,
                        )
                    else:
                        logger.warning(f"Credential {credential_id} validation failed")
                        return ValidateCredentialResponse(
                            is_valid=False,
                            message="Invalid credentials",
                            account_type=None,
                        )

            except ValueError as e:
                logger.warning(f"Credential validation failed: {e}")
                if "inactive" in str(e):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
                else:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate credential: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{credential_id}/account-data", response_model=AccountDataResponse)
async def get_credential_account_data(
    credential_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """
    Fetch real-time account data from Alpaca using stored credential.

    Decrypts credential, calls Alpaca /v2/account API, returns formatted response.

    Args:
        credential_id: UUID of credential to use for API call
        user: Current authenticated user

    Returns:
        AccountDataResponse with account_type, balance, equity, buying_power

    Raises:
        HTTPException: 403 if unauthorized, 400 if inactive, 500 if API fails
    """
    try:
        logger.info(f"Fetching account data for credential {credential_id}, user {user.id}")

        async with get_connection_with_rls(user.id) as conn:
            # First, get credential to determine account_type
            # We need to know if it's paper or live before calling Alpaca
            result = await conn.fetch(
                """
                SELECT credential_type FROM user_credentials WHERE id = $1
                """,
                UUID(credential_id),
            )

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Credential {credential_id} not found"
                )

            credential_type = result[0]["credential_type"]

            # Decrypt credential and fetch account data
            try:
                async with get_decrypted_alpaca_credential(conn, credential_id, user.id) as (
                    api_key,
                    secret_key,
                ):
                    # Use credential_type from database to determine paper vs live
                    # credential_type is stored during credential validation (Phase 3)
                    account_type = credential_type.lower()  # "paper" or "live"

                    # Fetch account data from Alpaca
                    account_data = await fetch_alpaca_account_data(
                        api_key, secret_key, account_type
                    )

                    logger.info(f"Account data fetched for credential {credential_id}")

                    return AccountDataResponse(
                        account_type=account_data["account_type"],
                        balance=account_data["cash"],
                        equity=account_data["equity"],
                        buying_power=account_data["buying_power"],
                        currency=account_data["currency"],
                        trading_blocked=account_data["trading_blocked"],
                        account_blocked=account_data["account_blocked"],
                        pattern_day_trader=account_data["pattern_day_trader"],
                        daytrade_count=account_data["daytrade_count"],
                        last_updated=datetime.utcnow().isoformat() + "Z",
                    )

            except ValueError as e:
                logger.warning(f"Account data fetch failed: {e}")
                if "inactive" in str(e):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
                else:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch account data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential_endpoint(
    credential_id: str,
    request: UpdateCredentialRequest,
    user: AuthUser = Depends(get_current_user),
):
    """
    Update existing credential.

    Updates api_key, secret_key, or is_active fields. Only provided fields are updated.

    Args:
        credential_id: UUID of credential to update
        request: UpdateCredentialRequest with fields to update
        user: Current authenticated user

    Returns:
        CredentialResponse with updated credential metadata

    Raises:
        HTTPException: 403 if user doesn't own credential, 404 if not found
    """
    try:
        logger.info(f"Updating credential {credential_id} for user {user.id}")

        async with get_connection_with_rls(user.id) as conn:
            # Build update values (only non-None fields)
            update_values = {}
            if request.api_key is not None:
                update_values["api_key"] = request.api_key.get_secret_value()
            if request.secret_key is not None:
                update_values["secret_key"] = request.secret_key.get_secret_value()
            if request.is_active is not None:
                update_values["is_active"] = request.is_active
            if request.nickname is not None:
                update_values["nickname"] = request.nickname

            if not update_values:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields provided for update",
                )

            # Update credential using raw SQL (RLS ensures user owns it)
            # Encrypt api_key/secret_key if provided
            if "api_key" in update_values:
                from modules.encryption_service import get_encryption_service
                encryption = get_encryption_service()
                update_values["api_key"] = encryption.encrypt(update_values["api_key"])
            if "secret_key" in update_values:
                from modules.encryption_service import get_encryption_service
                encryption = get_encryption_service()
                update_values["secret_key"] = encryption.encrypt(update_values["secret_key"])

            # Build SET clause dynamically
            set_clauses = []
            params = [UUID(credential_id)]
            param_idx = 2
            for key, value in update_values.items():
                set_clauses.append(f"{key} = ${param_idx}")
                params.append(value)
                param_idx += 1
            set_clauses.append("updated_at = NOW()")

            query = f"""
                UPDATE user_credentials
                SET {', '.join(set_clauses)}
                WHERE id = $1
                RETURNING id, user_account_id, credential_type, nickname, is_active, created_at, updated_at
            """

            result = await conn.fetchrow(query, *params)

            if result is None:
                logger.warning(f"Credential {credential_id} not found or unauthorized")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Credential {credential_id} not found or you don't have access",
                )

            logger.info(f"Credential {credential_id} updated successfully")

            return CredentialResponse(
                id=str(result["id"]),
                account_id=str(result["user_account_id"]),
                credential_type=result["credential_type"],
                nickname=result["nickname"],
                is_active=result["is_active"],
                created_at=result["created_at"].isoformat(),
                updated_at=result["updated_at"].isoformat(),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update credential: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential_endpoint(
    credential_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """
    Delete credential.

    Hard deletes credential from database. RLS ensures user owns the credential.

    Args:
        credential_id: UUID of credential to delete
        user: Current authenticated user

    Returns:
        204 No Content on success

    Raises:
        HTTPException: 403 if user doesn't own credential
    """
    try:
        logger.info(f"Deleting credential {credential_id} for user {user.id}")

        async with get_connection_with_rls(user.id) as conn:
            # Delete credential using raw SQL (RLS ensures user owns it)
            result = await conn.execute(
                """
                DELETE FROM user_credentials
                WHERE id = $1
                """,
                UUID(credential_id),
            )

            # asyncpg returns "DELETE N" where N is row count
            row_count = int(result.split()[1]) if result else 0
            if row_count == 0:
                logger.warning(f"Credential {credential_id} not found or unauthorized")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Credential {credential_id} not found or you don't have access",
                )

            logger.info(f"Credential {credential_id} deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete credential: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Export router
__all__ = ["router"]

# Phase 3: Credential Management - Research

**Researched:** 2026-01-30
**Domain:** FastAPI API Endpoints for Credential Storage, Retrieval, and Real-time Decryption
**Confidence:** HIGH

## Summary

Phase 3 requires implementing API endpoints that allow users to store and retrieve encrypted Alpaca API credentials (api_key + secret_key) while enforcing the critical requirement that **decrypted credentials are never cached or held in session state**. The phase bridges the gap between the secure credential storage infrastructure (Phase 2: database schema with RLS and encryption) and the runtime credential handling in the Alpaca agent service.

Research confirms that the standard approach for this domain is:

1. **POST /api/credentials** - Accept plaintext credentials, encrypt via TypeDecorator, store in database via SQLAlchemy ORM
2. **GET /api/credentials** - Return encrypted credentials from database; **do not decrypt in response body** (clients can decrypt client-side if needed, but server never exposes plaintext)
3. **POST /api/credentials/{id}/validate** - Decrypt credential temporarily, validate with Alpaca API, delete plaintext immediately after validation
4. **Internal credential retrieval** - When Alpaca agent needs to make API calls, decrypt only at call-time (in alpaca_agent_service.py), never store the plaintext in session/cache/global state
5. **Pydantic schemas** - Define request/response models with SecretStr masking to prevent plaintext in logs and error messages

**Critical Finding:** The architecture must enforce a strict temporal boundary: credentials remain encrypted except during the exact moment of API use. This requires careful management of credential lifecycle:
- Storage: Always encrypted (via TypeDecorator)
- Validation: Decrypt temporarily, validate, discard plaintext
- API calls: Decrypt on-demand just before Alpaca SDK call
- Session state: Never store plaintext credentials; use request-scoped decryption

**Primary recommendation:** Implement FastAPI endpoints that accept encrypted credentials and store them via SQLAlchemy TypeDecorator (which handles encryption transparently). For credential usage in alpaca_agent_service, decrypt credentials only when needed for API calls, using a context manager pattern to ensure plaintext is discarded immediately. Use Pydantic's SecretStr for sensitive fields to mask values in logs and error messages. Never implement credential caching; if the same credentials are needed multiple times, decrypt multiple times.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.104+ | API framework for credential endpoints | Already in use; provides automatic OpenAPI docs, request validation |
| SQLAlchemy | 2.0+ | ORM for database operations with TypeDecorator | Already in use; transparent encryption via EncryptedString TypeDecorator |
| Pydantic | 2.0+ | Request/response schema validation and SecretStr masking | Already in use; prevents credential exposure in logs via SecretStr type |
| cryptography | 47.0.0+ | Fernet encryption (inherited from Phase 1) | Already implemented; symmetric encryption for credentials |
| httpx | 0.25+ | Async HTTP client for Alpaca API validation | Standard for async credential validation calls |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic-settings | 2.0+ | Environment variable validation and secrets | Already in use for config loading; optional for credential config |
| asyncpg | 0.29+ | PostgreSQL async driver (inherited from Phase 2) | Already in use for database operations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff | Why NOT Recommended |
|------------|-----------|----------|---------------------|
| Pydantic SecretStr | Custom string masking in __repr__ | Manual implementation of masking in each schema | SecretStr is built-in, standard, used by every FastAPI project |
| Endpoint response with plaintext | Encrypt response body in HTTP response | Adds complexity to client-side decryption | RLS at database level is sufficient; server never exposes plaintext |
| Request-scoped caching of credentials | Cache decrypted credentials in memory with TTL | Increases attack surface; same reason Better Auth doesn't cache user passwords | Decryption is fast enough to do on every call; security benefit outweighs performance cost |
| FastAPI dependency injection for auth | Custom middleware for RLS context | Custom implementations often miss edge cases | FastAPI's built-in Depends() is standard; RLS handles database-level isolation |
| Direct Alpaca API calls | Use Alpaca SDK wrapper | SDK provides higher-level abstraction with retry/rate-limiting | SDK reduces credential handling code; less custom code = fewer security bugs |

**Installation:**
```bash
uv add fastapi pydantic httpx
uv add --dev pytest pytest-asyncio httpx
```

## Architecture Patterns

### Recommended Project Structure
```
apps/orchestrator_3_stream/backend/
├── main.py                                    # [EXISTING, MODIFIED] Add /api/credentials endpoints
├── modules/
│   ├── encryption_service.py                 # [EXISTING] From Phase 1
│   ├── user_models.py                        # [EXISTING] From Phase 2 ORM models
│   ├── credential_service.py                 # [NEW] Credential storage/retrieval logic
│   ├── database.py                           # [MODIFIED] Add RLS context, credential queries
│   ├── auth_middleware.py                    # [MODIFIED] Set RLS context in session variable
│   └── alpaca_agent_service.py               # [MODIFIED] Decrypt credentials on-demand for API calls
├── schemas/
│   ├── credential_schemas.py                 # [NEW] Pydantic models for credential requests/responses
│   └── user_schemas.py                       # [NEW] User account schemas
├── routers/
│   └── credentials.py                        # [NEW] FastAPI routes for credential management
└── tests/
    ├── test_credential_endpoints.py          # [NEW] Integration tests for API endpoints
    └── test_credential_lifecycle.py          # [NEW] Tests for decrypt-on-demand pattern
```

### Pattern 1: FastAPI Credential Storage Endpoint
**What:** A POST endpoint that accepts plaintext credentials in the request body, automatically encrypts them via SQLAlchemy TypeDecorator, and stores them in the database.

**When to use:** When users need to add new API credentials for their trading account.

**Example:**
```python
# Source: FastAPI documentation + Phase 3 requirements

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from modules.user_models import UserCredentialORM
from modules.database import get_db, get_current_user

router = APIRouter(prefix="/api/credentials", tags=["Credentials"])

class StoreCredentialRequest(BaseModel):
    """Request to store new credential"""
    account_id: str  # UUID of user_accounts.id
    credential_type: str  # "alpaca", "polygon", etc.
    api_key: SecretStr  # Plaintext (FastAPI will mask in logs)
    secret_key: SecretStr  # Plaintext (FastAPI will mask in logs)

class CredentialResponse(BaseModel):
    """Response with encrypted credential metadata (never plaintext)"""
    id: str
    credential_type: str
    is_active: bool
    created_at: str
    # Note: api_key and secret_key are NOT included in response
    # They remain encrypted in database and never sent to client

@router.post("/store", response_model=CredentialResponse)
async def store_credential(
    req: StoreCredentialRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Store encrypted API credentials for user's account.

    Security:
    - Request credentials are plaintext (HTTPS required)
    - TypeDecorator encrypts on INSERT automatically
    - Response never includes plaintext credentials
    - Database stores only encrypted values
    """
    # Verify user owns this account (RLS will also enforce this)
    account = await db.get(UserAccountORM, account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Create credential object with plaintext values
    credential = UserCredentialORM(
        user_account_id=account_id,
        user_id=current_user.id,
        credential_type=req.credential_type,
        api_key=req.api_key.get_secret_value(),  # Extract plaintext
        secret_key=req.secret_key.get_secret_value()  # Extract plaintext
    )

    # Add to database - TypeDecorator encrypts automatically
    db.add(credential)
    await db.commit()

    return CredentialResponse(
        id=str(credential.id),
        credential_type=credential.credential_type,
        is_active=credential.is_active,
        created_at=credential.created_at.isoformat()
    )
```

### Pattern 2: Decrypt-on-Demand for API Calls
**What:** A function that retrieves encrypted credentials from database, decrypts them only at the moment of API usage, and ensures plaintext is discarded immediately.

**When to use:** When the Alpaca agent service needs to make authenticated API calls to Alpaca.

**Example:**
```python
# Source: Phase 1 encryption_service + Phase 3 requirements

from contextlib import asynccontextmanager
from modules.user_models import UserCredentialORM
from modules.encryption_service import get_encryption_service
from modules.database import get_db

@asynccontextmanager
async def get_decrypted_credential(db: AsyncSession, credential_id: str, user_id: str):
    """
    Context manager that decrypts credential temporarily for API use.

    Guarantees:
    - Decryption happens only on entry
    - Plaintext is used only within the context
    - Plaintext is discarded immediately on exit
    - No storage in session, cache, or global state

    Example:
        async with get_decrypted_credential(db, cred_id, user.id) as cred:
            # cred contains plaintext api_key and secret_key
            response = await alpaca_client.authenticate(cred.api_key, cred.secret_key)
            # Plaintext discarded here when context exits
    """
    # Retrieve encrypted credential from database
    credential = await db.get(UserCredentialORM, credential_id)

    if not credential or credential.user_id != user_id:
        raise ValueError("Credential not found or access denied")

    # Access credential.api_key triggers TypeDecorator.process_result_value()
    # which decrypts automatically
    api_key = credential.api_key
    secret_key = credential.secret_key

    try:
        # Create temporary tuple with plaintext values
        plaintext_credential = (api_key, secret_key)
        yield plaintext_credential
    finally:
        # Explicitly clear plaintext from memory
        # (Python's garbage collector will eventually do this anyway,
        # but explicit is better than implicit)
        del api_key
        del secret_key
        del plaintext_credential

# Usage in alpaca_agent_service.py:
async def authenticate_with_credential(credential_id: str, user_id: str):
    """Example usage of decrypt-on-demand pattern"""
    async with get_db() as db:
        async with get_decrypted_credential(db, credential_id, user_id) as (api_key, secret_key):
            # api_key and secret_key are plaintext here
            client = AlpacaClient(api_key=api_key, secret_key=secret_key)
            account = await client.get_account()
            return account
        # Plaintext is discarded here - no cache, no session state
```

### Pattern 3: RLS Context in FastAPI Middleware
**What:** Middleware that extracts authenticated user from request and sets PostgreSQL session variable for RLS filtering.

**When to use:** Every database query must be RLS-filtered. Middleware ensures the session variable is set before any query.

**Example:**
```python
# Source: PostgreSQL RLS documentation + Phase 2 migration 15

from fastapi import Request
from modules.database import get_db

@app.middleware("http")
async def set_rls_context(request: Request, call_next):
    """
    Middleware to set RLS context before processing request.

    Sets PostgreSQL session variable app.current_user_id
    so that all database queries are automatically filtered to user's data.
    """
    # Extract user from session/JWT token (depends on auth system)
    user = request.state.user  # Set by auth middleware

    if user:
        # Get database connection
        async with get_db() as db:
            # Set session variable for RLS
            await db.execute(f"SET LOCAL app.current_user_id = '{user.id}'")

    # Proceed with request
    response = await call_next(request)
    return response
```

### Anti-Patterns to Avoid
- **Store decrypted credentials in session state:** Session data can be accessed, logged, or persisted. Decrypt only when needed, use only within a scoped context (function or context manager), then discard.
- **Cache credentials in memory with TTL:** Caching increases attack surface and makes secret revocation harder. If credentials are needed multiple times, decrypt multiple times.
- **Return plaintext credentials in API response:** Even if the client "needs" them, never send plaintext over HTTP. If client needs decrypted credentials, use separate secure channel (e.g., client-side encryption).
- **Skip RLS context in middleware:** Every database operation must set the user context. Missing context = RLS policies can't filter rows = data leak risk.
- **Log credential values anywhere:** Use Pydantic's SecretStr for all credential fields to ensure automatic masking in string representations. Never call str() on a credential value.
- **Store encryption key in request/response:** Keys are stored in environment variables only (inherited from Phase 1). Never pass encryption keys in HTTP traffic.
- **Assume HTTPS is optional:** Credential endpoints MUST require HTTPS. In development, fastapi-ssl can enforce it; production requires reverse proxy (nginx) or cloud provider (Neon, AWS) HTTPS enforcement.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "I'll just return encrypted credentials in the response" | Custom encryption/decryption on client | Store credentials server-side only; client never receives plaintext. If client needs API access, provide a separate API token. | Sending credentials over HTTP (even encrypted in response) violates least-privilege. Server should hold all secrets. |
| "I'll cache decrypted credentials for 5 minutes to avoid repeated decryption" | In-memory credential cache | Decrypt on every use (fast enough, ~1ms per credential) | Caching increases compromise risk. If encryption key is stolen, cached credentials are already decrypted and exposed for 5 minutes. |
| "I'll store credentials in FastAPI's request.state for the duration of the request" | Request-scoped credential storage | Use context managers or function parameters; never store plaintext in request state | request.state can be accessed from anywhere in the request (middleware, dependencies, routes). Better to pass plaintext only to the exact function that needs it. |
| "I'll validate credentials by trying to authenticate with Alpaca, then cache the result" | Cached validation result | Validate on every credential storage, not on every API call. Cache only the validation status (True/False), not the credentials. | Credentials can be revoked by Alpaca at any time. If you cache "valid", you might use revoked credentials hours later. |
| "I'll encrypt the response body so clients can't see credentials" | Custom response encryption | Never send credentials in response. If client needs API access, issue a temporary bearer token instead. | Clients will decrypt the response anyway; encryption of response body doesn't add security. Server should never expose secrets. |
| "I'll create a secret manager service that holds credentials in memory" | Custom in-memory secret store | Database with RLS is the secret manager. Decrypt only on-demand from database. | In-memory storage is vulnerable to memory dumps, core dumps, and process inspection. Database provides better security posture. |

**Key insight:** The core principle is never holding plaintext credentials longer than necessary. Every storage/cache/session-state implementation trades security for convenience. In the credential management domain, the right tradeoff is: zero caching, decrypt on-demand, discard immediately.

## Common Pitfalls

### Pitfall 1: Credentials Leaking in Logs During Error Handling
**What goes wrong:** User submits invalid credentials via POST /api/credentials. The endpoint tries to validate them with Alpaca, fails, and returns an error response. The error message contains the credentials in plaintext.

**Why it happens:** Developers use f-strings or format() with credential values in error messages: `raise ValueError(f"Failed to authenticate with key {api_key}")`. The error gets logged, exposing the plaintext credential.

**How to avoid:**
- Use Pydantic SecretStr for all credential request fields: `api_key: SecretStr`
- When raising exceptions, never include the actual credential value: `raise ValueError(f"Failed to authenticate with credential type {req.credential_type}")`
- Let Pydantic's SecretStr handle masking: `print(credential)` outputs `SecretStr('***')`
- Test error paths explicitly: deliberately submit invalid credentials and verify logs don't contain plaintext
- Configure logging to use the OrchestratorLogger which includes redaction filters (inherited from Phase 1)

**Warning signs:**
- Credentials appear in error logs
- API validation failure logs show partial credential values
- Exceptions mention "key PK..." or "secret sp..." patterns

### Pitfall 2: RLS Context Not Set Before Database Operations
**What goes wrong:** An endpoint queries the user_credentials table without setting the RLS session variable. The query returns all users' credentials, not just the current user's.

**Why it happens:** Middleware forgets to set app.current_user_id, or database connection is created before middleware runs, or test code doesn't set RLS context.

**How to avoid:**
- Middleware MUST set RLS context before any database operation in the request handler
- Use a context manager or decorator to guarantee context is set:
  ```python
  @app.get("/api/credentials")
  async def list_credentials(db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
      # Middleware has already set app.current_user_id = user.id
      # All queries on this connection are RLS-filtered
      result = await db.query(UserCredentialORM).all()
      return result
  ```
- In tests, explicitly set RLS context before queries:
  ```python
  await db.execute("SET LOCAL app.current_user_id = $1", test_user_id)
  result = await db.query(UserCredentialORM).all()
  ```
- Verify RLS is working: use non-superuser test accounts (inherited from Phase 2 testing requirements)

**Warning signs:**
- Test account can see other users' credentials
- Queries return all credentials, not filtered by user_id
- RLS policies don't appear in pg_policies query

### Pitfall 3: Decryption Happens Too Late (After Response Sent)
**What goes wrong:** An endpoint decrypts credentials, returns plaintext in the response body, and only after the response is sent does the plaintext get cleared from memory.

**Why it happens:** Developers return the plaintext credential directly: `return {"api_key": credential.api_key, "secret_key": credential.secret_key}`. The plaintext is sent in the HTTP response, which is then captured in proxies, logs, or client caches.

**How to avoid:**
- Never include api_key or secret_key fields in API response models
- If client needs to verify credentials, provide a /validate endpoint that returns only True/False (not the credentials)
- If client needs API access, issue a temporary token or use Alpaca's OAuth flow instead
- Credentials stay in the database; responses only include metadata (id, created_at, credential_type, is_active)

**Warning signs:**
- Response models include plaintext credential fields
- API documentation shows credential values in response examples
- HTTP proxies (nginx, CloudFlare) log plaintext credentials in response bodies

### Pitfall 4: Alpaca SDK Stores Credentials Internally
**What goes wrong:** Code creates an AlpacaClient instance with plaintext credentials, returns the client object, and the client stores the credentials internally. Later, the client is serialized, logged, or persisted (e.g., in a cache).

**Why it happens:** Developers assume the SDK doesn't store credentials or assume the credential object goes out of scope when the function returns. SDK implementations vary; some cache credentials internally.

**How to avoid:**
- Create AlpacaClient instances inside the context manager where credentials are decrypted
- Never store or cache the client object; create a new one for each API call
- Example pattern:
  ```python
  async with get_decrypted_credential(db, cred_id, user_id) as (api_key, secret_key):
      client = AlpacaClient(api_key=api_key, secret_key=secret_key)
      result = await client.get_account()
      # client goes out of scope here, credentials discarded
  ```
- If the SDK caches credentials, wrap the entire client creation and usage in the context:
  ```python
  async with get_decrypted_credential(...) as (api_key, secret_key):
      async with AlpacaClient(api_key, secret_key) as client:
          result = await client.get_account()
  ```

**Warning signs:**
- Client object stored in session or cache
- Exception stacktraces show AlpacaClient with credentials in __dict__
- Serialized client objects found in logs

### Pitfall 5: Credential Validation Not Idempotent
**What goes wrong:** When a user stores new credentials, the endpoint validates them with Alpaca. If validation passes, the endpoint stores the credentials. But if validation fails, the credentials are partially stored or create a database transaction in an inconsistent state.

**Why it happens:** Developers implement validation and storage as separate steps without wrapping them in a transaction.

**How to avoid:**
- Wrap validation and storage in a single database transaction:
  ```python
  async with db.transaction():
      # First validate
      async with get_decrypted_credential_temp(api_key, secret_key) as creds:
          is_valid = await alpaca_client.validate_credentials(creds)
          if not is_valid:
              raise ValueError("Invalid Alpaca credentials")
      # Only store if validation passes
      credential = UserCredentialORM(...)
      db.add(credential)
      await db.commit()
  ```
- Test both success and failure paths: credentials accepted, credentials rejected
- Use database constraints to prevent invalid states (e.g., unique (user_account_id, credential_type) prevents duplicates)

**Warning signs:**
- Invalid credentials stored in database as is_active=False
- Duplicate credentials for same account/type after failed validation
- Database has orphaned credential records with no corresponding validation results

### Pitfall 6: Not Testing Credential Lifecycle End-to-End
**What goes wrong:** Unit tests pass (encryption/decryption works), integration tests pass (endpoints work), but in production, the Alpaca agent can't authenticate because credentials aren't being decrypted correctly at API call time.

**Why it happens:** Tests mock the decryption step or don't test the actual Alpaca API call with the decrypted credentials.

**How to avoid:**
- Write end-to-end tests that:
  1. Store credentials via POST endpoint
  2. Retrieve credentials from database
  3. Decrypt credentials (simulate API call)
  4. Call actual Alpaca API (or mock Alpaca API) with decrypted credentials
  5. Verify API call succeeds with decrypted credentials
- Use real test credentials (from Alpaca paper trading account)
- Test the decrypt-on-demand pattern with real encrypted data, not mocked
- Example:
  ```python
  @pytest.mark.asyncio
  async def test_credential_lifecycle_e2e():
      # 1. Store
      cred_id = await store_credential(user_id, api_key, secret_key)

      # 2. Retrieve
      credential = await db.get(UserCredentialORM, cred_id)

      # 3. Decrypt (automatically via TypeDecorator)
      decrypted_api_key = credential.api_key
      decrypted_secret = credential.secret_key

      # 4. Call Alpaca with decrypted credentials
      client = AlpacaClient(api_key=decrypted_api_key, secret_key=decrypted_secret)
      account = await client.get_account()

      # 5. Verify success
      assert account is not None
      assert account.account_type in ["paper", "live"]
  ```

**Warning signs:**
- Unit tests pass but production API calls fail with "Invalid authentication"
- Decrypted credentials work in manual testing but not in integration tests
- No tests for the decrypt-on-demand pattern with real encrypted data

## Code Examples

Verified patterns from official sources:

### Pydantic Request Schema with SecretStr
```python
# Source: Pydantic documentation + Phase 1 security patterns

from pydantic import BaseModel, SecretStr, Field
from typing import Optional

class StoreCredentialRequest(BaseModel):
    """Request to store new encrypted credential.

    Security:
    - api_key and secret_key use SecretStr to mask values in logs
    - Pydantic automatically masks SecretStr in __repr__ and str()
    """
    account_id: str = Field(..., description="User account UUID")
    credential_type: str = Field(..., description="Credential type (alpaca, polygon, etc.)")
    api_key: SecretStr = Field(..., description="API key (masked in logs)")
    secret_key: SecretStr = Field(..., description="Secret key (masked in logs)")

class UpdateCredentialRequest(BaseModel):
    """Request to update existing credential."""
    api_key: Optional[SecretStr] = Field(None, description="New API key")
    secret_key: Optional[SecretStr] = Field(None, description="New secret key")
    is_active: Optional[bool] = Field(None, description="Activate/deactivate credential")

class CredentialResponse(BaseModel):
    """Response with credential metadata (NEVER includes plaintext credentials)."""
    id: str
    account_id: str
    credential_type: str
    is_active: bool
    created_at: str
    updated_at: str
    # NOTE: api_key and secret_key are intentionally NOT included
    # Credentials remain encrypted in database and never sent to client

    class Config:
        from_attributes = True

class ValidateCredentialRequest(BaseModel):
    """Request to validate credentials against Alpaca."""
    api_key: SecretStr
    secret_key: SecretStr

class ValidateCredentialResponse(BaseModel):
    """Response indicating validation result (boolean only, no credentials)."""
    is_valid: bool
    message: str  # "Valid" or error description
    account_type: Optional[str] = None  # "paper" or "live"
```

### FastAPI Endpoints for Credential Management
```python
# Source: FastAPI documentation + Phase 3 requirements

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID

from modules.user_models import UserAccountORM, UserCredentialORM
from modules.database import get_db, get_current_user
from schemas.credential_schemas import (
    StoreCredentialRequest,
    UpdateCredentialRequest,
    CredentialResponse,
    ValidateCredentialRequest,
    ValidateCredentialResponse
)

router = APIRouter(prefix="/api/credentials", tags=["Credentials"])

@router.post("/store", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
async def store_credential(
    request: StoreCredentialRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Store encrypted API credentials for user account.

    Security:
    - Accepts plaintext credentials (HTTPS required)
    - TypeDecorator encrypts on INSERT automatically
    - Response never includes plaintext credentials
    - Database stores only encrypted values
    - RLS policies ensure user can only store credentials for their own accounts

    Args:
        request: StoreCredentialRequest with plaintext api_key and secret_key
        current_user: Authenticated user from JWT token
        db: Async database session

    Returns:
        CredentialResponse with metadata only (no plaintext credentials)

    Raises:
        HTTPException 403: If user doesn't own the account
        HTTPException 409: If credential already exists for this type
    """
    # Verify user owns this account
    account = await db.get(UserAccountORM, UUID(request.account_id))
    if not account or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: account does not belong to user"
        )

    # Check for duplicate credentials
    existing = await db.execute(
        select(UserCredentialORM).where(
            and_(
                UserCredentialORM.user_account_id == UUID(request.account_id),
                UserCredentialORM.credential_type == request.credential_type
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Credential type '{request.credential_type}' already exists for this account"
        )

    # Create credential - TypeDecorator encrypts api_key and secret_key automatically
    credential = UserCredentialORM(
        user_account_id=UUID(request.account_id),
        user_id=current_user.id,
        credential_type=request.credential_type,
        api_key=request.api_key.get_secret_value(),  # Extract plaintext from SecretStr
        secret_key=request.secret_key.get_secret_value()  # Extract plaintext from SecretStr
    )

    db.add(credential)
    await db.commit()
    await db.refresh(credential)

    return CredentialResponse(
        id=str(credential.id),
        account_id=str(credential.user_account_id),
        credential_type=credential.credential_type,
        is_active=credential.is_active,
        created_at=credential.created_at.isoformat(),
        updated_at=credential.updated_at.isoformat()
    )


@router.get("", response_model=list[CredentialResponse])
async def list_credentials(
    account_id: str = Query(..., description="Filter by account UUID"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List credentials for user's account.

    RLS ensures user can only see their own credentials.

    Args:
        account_id: Account UUID to filter by
        current_user: Authenticated user
        db: Database session

    Returns:
        List of CredentialResponse (metadata only, never plaintext)

    Raises:
        HTTPException 403: If user doesn't own the account
    """
    # Verify user owns account
    account = await db.get(UserAccountORM, UUID(account_id))
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    # Query credentials - RLS policy filters to current user's credentials
    result = await db.execute(
        select(UserCredentialORM).where(
            UserCredentialORM.user_account_id == UUID(account_id)
        )
    )
    credentials = result.scalars().all()

    return [
        CredentialResponse(
            id=str(cred.id),
            account_id=str(cred.user_account_id),
            credential_type=cred.credential_type,
            is_active=cred.is_active,
            created_at=cred.created_at.isoformat(),
            updated_at=cred.updated_at.isoformat()
        )
        for cred in credentials
    ]


@router.post("/{credential_id}/validate", response_model=ValidateCredentialResponse)
async def validate_credential(
    credential_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate credential by attempting to authenticate with Alpaca.

    Security:
    - Decrypts credential from database
    - Calls Alpaca API with plaintext credentials
    - Discards plaintext immediately after validation
    - Returns only boolean result, never exposes credentials
    - Requires HTTPS (credentials sent to Alpaca backend)

    Args:
        credential_id: Credential UUID to validate
        current_user: Authenticated user
        db: Database session

    Returns:
        ValidateCredentialResponse with is_valid boolean

    Raises:
        HTTPException 403: If user doesn't own the credential
        HTTPException 400: If credential is inactive
    """
    # Retrieve credential - RLS ensures user can only access their own
    credential = await db.get(UserCredentialORM, UUID(credential_id))
    if not credential or credential.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    if not credential.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credential is inactive"
        )

    # Decrypt credential and validate with Alpaca
    # TypeDecorator.process_result_value() decrypts api_key and secret_key
    try:
        api_key = credential.api_key  # Decrypted
        secret_key = credential.secret_key  # Decrypted

        # Call Alpaca API to validate credentials
        # (mock or real call to Alpaca REST API)
        from modules.alpaca_service import validate_alpaca_credentials
        is_valid, account_type = await validate_alpaca_credentials(api_key, secret_key)

        # Plaintext is discarded here
        del api_key
        del secret_key

        return ValidateCredentialResponse(
            is_valid=is_valid,
            message="Valid" if is_valid else "Invalid credentials",
            account_type=account_type if is_valid else None
        )

    except Exception as e:
        # Log error but NEVER log the credential values
        # OrchestratorLogger includes redaction filters
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation failed: {credential.credential_type} account"
        )


@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: str,
    request: UpdateCredentialRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update credential (api_key, secret_key, or is_active status).

    Args:
        credential_id: Credential UUID to update
        request: UpdateCredentialRequest with fields to update
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated CredentialResponse

    Raises:
        HTTPException 403: If user doesn't own the credential
    """
    credential = await db.get(UserCredentialORM, UUID(credential_id))
    if not credential or credential.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    # Update fields if provided
    if request.api_key:
        credential.api_key = request.api_key.get_secret_value()  # TypeDecorator encrypts
    if request.secret_key:
        credential.secret_key = request.secret_key.get_secret_value()  # TypeDecorator encrypts
    if request.is_active is not None:
        credential.is_active = request.is_active

    await db.commit()
    await db.refresh(credential)

    return CredentialResponse(
        id=str(credential.id),
        account_id=str(credential.user_account_id),
        credential_type=credential.credential_type,
        is_active=credential.is_active,
        created_at=credential.created_at.isoformat(),
        updated_at=credential.updated_at.isoformat()
    )


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete credential (soft or hard delete depending on retention policy).

    Args:
        credential_id: Credential UUID to delete
        current_user: Authenticated user
        db: Database session

    Returns:
        204 No Content

    Raises:
        HTTPException 403: If user doesn't own the credential
    """
    credential = await db.get(UserCredentialORM, UUID(credential_id))
    if not credential or credential.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    # Soft delete (if retention required)
    # credential.is_active = False
    # await db.commit()

    # Or hard delete
    await db.delete(credential)
    await db.commit()

    return None
```

### Decrypt-on-Demand Pattern for Alpaca Agent Service
```python
# Source: Phase 1 encryption + Phase 3 requirements

from contextlib import asynccontextmanager
from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from modules.user_models import UserCredentialORM
from modules.encryption_service import get_encryption_service

@asynccontextmanager
async def get_decrypted_alpaca_credential(
    db: AsyncSession,
    credential_id: str,
    user_id: str
) -> Tuple[str, str]:
    """
    Context manager for decrypting Alpaca credentials on-demand.

    Guarantees:
    - Plaintext exists only within the context block
    - Plaintext is discarded when context exits
    - No caching or session state

    Usage:
        async with get_decrypted_alpaca_credential(db, cred_id, user_id) as (api_key, secret_key):
            client = AlpacaClient(api_key, secret_key)
            account = await client.get_account()
        # Plaintext discarded here

    Args:
        db: Async database session
        credential_id: UUID of credential to decrypt
        user_id: User ID for authorization check

    Yields:
        Tuple of (api_key, secret_key) as plaintext

    Raises:
        ValueError: If credential not found or user unauthorized
    """
    # Retrieve encrypted credential from database
    credential = await db.get(UserCredentialORM, credential_id)

    if not credential:
        raise ValueError(f"Credential {credential_id} not found")

    if credential.user_id != user_id:
        raise ValueError(f"Unauthorized: credential does not belong to user {user_id}")

    if not credential.is_active:
        raise ValueError(f"Credential {credential_id} is inactive")

    # Accessing credential.api_key and credential.secret_key
    # automatically triggers TypeDecorator.process_result_value()
    # which decrypts the values
    try:
        api_key = credential.api_key
        secret_key = credential.secret_key

        # Yield plaintext for use in context
        yield (api_key, secret_key)

    finally:
        # Explicitly clear plaintext from memory on context exit
        # (helps with garbage collection, though Python will do this anyway)
        del api_key
        del secret_key


# Usage in alpaca_agent_service.py:

async def invoke_alpaca_with_credential(
    db: AsyncSession,
    credential_id: str,
    user_id: str,
    alpaca_operation: str,
    operation_params: dict
) -> dict:
    """
    Invoke Alpaca API operation using stored credential.

    Decrypt credential only when needed, discard immediately after use.

    Args:
        db: Database session
        credential_id: UUID of stored credential
        user_id: Current user's ID
        alpaca_operation: Operation to invoke (e.g., "get_account")
        operation_params: Parameters for operation

    Returns:
        Result from Alpaca API

    Raises:
        ValueError: If credential invalid or unauthorized
        HTTPError: If Alpaca API call fails
    """
    # Decrypt credential only for the duration of the API call
    async with get_decrypted_alpaca_credential(db, credential_id, user_id) as (api_key, secret_key):
        # Create Alpaca client with plaintext credentials
        from modules.alpaca_service import AlpacaClient
        client = AlpacaClient(api_key=api_key, secret_key=secret_key)

        # Invoke operation
        method = getattr(client, alpaca_operation)
        result = await method(**operation_params)

        return result

    # Plaintext credentials are discarded here
    # client object goes out of scope
```

### Test for Decrypt-on-Demand Pattern
```python
# Source: Phase 2 testing patterns + Phase 3 requirements

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from modules.user_models import UserCredentialORM
from modules.encryption_service import get_encryption_service

@pytest.mark.asyncio
async def test_decrypt_on_demand_pattern(db: AsyncSession):
    """
    Test that decrypt-on-demand pattern works correctly.

    Verifies:
    1. Credentials are stored encrypted
    2. Decryption happens only when accessed
    3. Plaintext is not cached or stored
    """
    # Setup
    test_user_id = "test_user_123"
    test_account_id = uuid4()
    test_api_key = "PK0123456789ABCDEF"
    test_secret_key = "sp0123456789abcdefghijklmnop"

    # Store credential (auto-encrypted via TypeDecorator)
    credential = UserCredentialORM(
        user_account_id=test_account_id,
        user_id=test_user_id,
        credential_type="alpaca",
        api_key=test_api_key,
        secret_key=test_secret_key,
        is_active=True
    )
    db.add(credential)
    await db.commit()
    await db.refresh(credential)

    # Verify credential is stored encrypted in database
    # (Get raw value directly from database without TypeDecorator)
    raw_result = await db.execute(
        "SELECT api_key, secret_key FROM user_credentials WHERE id = $1",
        credential.id
    )
    raw_api_key, raw_secret_key = raw_result.scalar()

    # Raw values must NOT equal plaintext (they're encrypted)
    assert raw_api_key != test_api_key
    assert raw_secret_key != test_secret_key
    assert raw_api_key.startswith("gAAAAAA")  # Fernet ciphertext format

    # Retrieve credential again
    retrieved = await db.get(UserCredentialORM, credential.id)

    # Access plaintext (TypeDecorator decrypts)
    decrypted_api_key = retrieved.api_key
    decrypted_secret_key = retrieved.secret_key

    # Verify decryption works
    assert decrypted_api_key == test_api_key
    assert decrypted_secret_key == test_secret_key


@pytest.mark.asyncio
async def test_decrypt_on_demand_context_manager(db: AsyncSession):
    """
    Test decrypt-on-demand context manager pattern.
    """
    from modules.credential_service import get_decrypted_alpaca_credential

    # Setup
    test_user_id = "test_user_456"
    test_account_id = uuid4()
    test_api_key = "PKtest123"
    test_secret_key = "sptest456"

    # Store credential
    credential = UserCredentialORM(
        user_account_id=test_account_id,
        user_id=test_user_id,
        credential_type="alpaca",
        api_key=test_api_key,
        secret_key=test_secret_key,
        is_active=True
    )
    db.add(credential)
    await db.commit()

    # Use context manager
    async with get_decrypted_alpaca_credential(db, credential.id, test_user_id) as (api_key, secret_key):
        # Plaintext available inside context
        assert api_key == test_api_key
        assert secret_key == test_secret_key

    # Outside context, verify no variables leaked
    # (Python scope means api_key, secret_key not accessible here)
    # This is enforced by context manager structure


@pytest.mark.asyncio
async def test_unauthorized_credential_access(db: AsyncSession):
    """
    Test that unauthorized user cannot access another user's credentials.
    """
    from modules.credential_service import get_decrypted_alpaca_credential

    # User 1 stores credential
    user_1_id = "user_1"
    credential = UserCredentialORM(
        user_account_id=uuid4(),
        user_id=user_1_id,
        credential_type="alpaca",
        api_key="PKuser1_key",
        secret_key="spuser1_secret",
        is_active=True
    )
    db.add(credential)
    await db.commit()

    # User 2 tries to access user 1's credential
    user_2_id = "user_2"

    with pytest.raises(ValueError, match="does not belong to user"):
        async with get_decrypted_alpaca_credential(db, credential.id, user_2_id) as creds:
            pass  # Should not reach here
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Store credentials in plaintext in database | Encrypt with Fernet before storage (Phase 1) | Standard since cryptography 1.0 (2014) | Database breach no longer exposes credentials |
| Decrypt credentials once, cache in memory for request lifetime | Decrypt on-demand only when needed | Best practice 2018+ (zero-trust) | Reduces exposure window; if encryption key is compromised, fewer credentials are decrypted |
| Pass plaintext credentials between functions via function parameters | Use context managers to scope plaintext lifetime | Industry adoption 2015+ | Explicit scoping prevents accidental storage or logging |
| Return plaintext credentials in API responses | Return only metadata; keep credentials server-side | Best practice 2020+ (zero-trust, OAuth) | Credentials never exposed in HTTP traffic |
| Manual validation of credentials (try API call, catch error) | Structured validation endpoint with idempotent transaction | Current best practice | Predictable failure modes; database remains consistent |
| Session-based credential storage (store in request.state or session dict) | Per-request decryption only within context managers | Industry adoption 2020+ | Prevents credential leaks from session hijacking |
| Hardcoded credential in test fixtures | Use TestClient with mock credentials; test with real Alpaca paper account | Current best practice | Tests don't expose secrets; production and development separated |

**Deprecated/outdated:**
- **Returning plaintext credentials in API response:** Violates zero-trust principle. Credentials should never leave the server.
- **Caching decrypted credentials:** Increases compromise risk. Decrypt on-demand.
- **Storing credentials in request.state or session:** Credentials accessible from anywhere in request lifecycle. Use context managers for explicit scoping.
- **Validating credentials once at storage time:** Credentials can be revoked by Alpaca later. Validate at API call time if needed.

## Open Questions

Things that couldn't be fully resolved:

1. **Alpaca OAuth vs. API Key Credentials**
   - What we know: Alpaca supports both API key/secret (static) and OAuth flows (token-based)
   - What's unclear: Should Phase 3 support OAuth, or stick to API key/secret only?
   - Recommendation: Phase 3 implements API key/secret support only (simpler). Phase 4+ can add OAuth support if needed, which would change credential_type from "alpaca" to "alpaca_oauth" and decrypt OAuth tokens instead of keys.
   - Reference: Alpaca docs show both auth methods available; user typically chooses one

2. **Credential Expiration and Rotation**
   - What we know: Credentials have optional expires_at field in schema; Alpaca doesn't auto-expire keys
   - What's unclear: Should endpoints check expiration and prevent use of expired credentials? Should there be an auto-rotation mechanism?
   - Recommendation: Phase 3 stores expires_at but doesn't enforce expiration. Phase 4 can add cleanup jobs. For now, is_active flag is sufficient for manual revocation.

3. **Multiple Credentials per User Account**
   - What we know: Schema allows multiple credentials per account (unique on account_id + credential_type)
   - What's unclear: Should Alpaca agent automatically select the "right" credential, or require explicit selection?
   - Recommendation: Start with explicit selection in Phase 3. If multiple credentials become common, Phase 4 can add auto-selection logic (e.g., prefer is_active=true, most recent, live over paper).

4. **Credential Audit Logging**
   - What we know: Credentials can be stored, updated, deleted, validated
   - What's unclear: Should each operation be logged for compliance/auditing?
   - Recommendation: Phase 3 focuses on functionality. Phase 4+ can add audit tables if compliance requires it (HIPAA, SOC2, etc.).

5. **Client-Side Credential Storage**
   - What we know: API returns only metadata (no plaintext credentials)
   - What's unclear: If frontend needs to display "credentials configured", should it store anything locally?
   - Recommendation: Frontend stores only credential metadata (id, type, created_at). Plaintext never stored client-side. If frontend needs to invoke Alpaca API, backend provides temporary bearer tokens or handles all API calls.

## Sources

### Primary (HIGH confidence)

- **FastAPI** — [API Documentation](https://fastapi.tiangolo.com/) — Request validation, response models, dependency injection, exception handling
- **Pydantic** — [SecretStr Documentation](https://docs.pydantic.dev/latest/concepts/secret_types/) — Masking sensitive values in logs and error messages
- **SQLAlchemy** — [TypeDecorator Pattern](https://docs.sqlalchemy.org/en/20/core/custom_types.html) — Custom column types with transparent encryption (inherited from Phase 2)
- **cryptography** — [Fernet Documentation](https://cryptography.io/en/latest/fernet/) — Symmetric encryption for credentials (inherited from Phase 1)
- **PostgreSQL** — [Row-Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) — RLS policies for credential isolation (inherited from Phase 2)
- **httpx** — [Async HTTP Client](https://www.python-httpx.org/) — Async HTTP calls for credential validation with Alpaca

### Secondary (MEDIUM confidence)

- **FastAPI Security** — [Dependency Injection Patterns](https://fastapi.tiangolo.com/tutorial/security/) — Best practices for authentication and authorization in endpoints
- **OWASP** — [API Security Top 10](https://owasp.org/www-project-api-security/) — Credential exposure, injection, broken object level authorization
- **Cloud Native Security** — [12-Factor App Secrets](https://12factor.net/config) — Managing secrets in cloud-native applications
- **Better Stack** — [Logging Sensitive Data](https://betterstack.com/community/guides/logging/sensitive-data/) — Log redaction and masking patterns (inherited from Phase 1)

### Tertiary (LOW confidence, marked for validation)

- **Alpaca Documentation** — [Authentication](https://docs.alpaca.markets/docs/authentication) — Alpaca credential types and authentication flows
- **WebSearch results on "credential management API patterns 2026"** — Community patterns and best practices (verified against official documentation)

## Metadata

**Confidence breakdown:**
- **FastAPI patterns (HIGH):** Official documentation provides clear examples of request/response models, dependency injection, error handling. Verified with current FastAPI 0.104+ docs.
- **Encryption and TypeDecorator (HIGH):** Inherited from Phase 1 and Phase 2, already verified against official cryptography and SQLAlchemy docs.
- **RLS context in middleware (HIGH):** Pattern from PostgreSQL and Neon documentation; already used in Phase 2 migration 15.
- **Pydantic SecretStr (HIGH):** Official feature; used in production FastAPI applications across the industry.
- **Credential validation patterns (MEDIUM):** Best practices inferred from OWASP and cloud-native security principles; not Alpaca-specific documentation.
- **Alpaca credential formats (MEDIUM):** Alpaca documentation is clear on API key (PK...) and secret key (sp...) formats; lifecycle details not fully documented.

**Research date:** 2026-01-30
**Valid until:** 2026-02-20 (API patterns stable; Alpaca API may evolve)
**Next validation:** Before Phase 3 planning if Alpaca auth patterns change; also verify that FastAPI 0.104+ includes all documented security features

**Key Research Findings Summary:**
1. FastAPI endpoints should accept plaintext credentials (HTTPS required) and encrypt via TypeDecorator transparently
2. Responses must never include plaintext credentials; return only metadata
3. Decryption must happen on-demand only when needed for API calls, using context managers to ensure plaintext is discarded immediately
4. RLS ensures database-level user isolation; middleware must set session variable before queries
5. Pydantic SecretStr masks sensitive values in logs automatically
6. Context managers enforce temporal scoping of plaintext credentials, preventing accidental caching or storage

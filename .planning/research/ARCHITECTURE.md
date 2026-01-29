# Architecture Patterns: Multi-Tenant Alpaca Trading Platform

**Domain:** Multi-user trading platform with secure credential isolation
**Researched:** 2026-01-29
**Confidence:** HIGH (verified with official PostgreSQL docs, FastAPI security docs, and multi-tenant SaaS patterns)

## Executive Summary

A secure multi-tenant trading platform must implement three core architectural components:

1. **Encrypted credential storage** - API keys stored encrypted at rest in PostgreSQL using application-level encryption
2. **Per-user account isolation** - Database schema with strict tenant_id foreign keys and row-level data filtering
3. **Per-user runtime clients** - Alpaca API client instances created on-demand from decrypted credentials with session-scoped lifecycle

This architecture prevents cross-tenant data leakage, enables account switching without re-authentication, and allows friends to manage isolated trading accounts within a single application instance.

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Frontend (Vue 3)                                                │
│ - User authentication (Better Auth)                             │
│ - Account selector dropdown                                     │
│ - WebSocket connection (shared across accounts)                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ FastAPI Backend                                                 │
│ ┌──────────────────────────────────────────────────────────────┤
│ │ Authentication Layer (Better Auth)                           │
│ │ - Validates user session (HTTPOnly cookie)                   │
│ │ - Returns user_id                                            │
│ └──────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────┤
│ │ Account Context Layer                                        │
│ │ - Extracts account_id from request (header or query param)   │
│ │ - Validates user owns account (foreign key check)            │
│ │ - Injects TenantContext into handler                        │
│ └──────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────┤
│ │ Credential Decryption Layer                                  │
│ │ - Retrieves encrypted API keys from database                 │
│ │ - Decrypts using application-level encryption key            │
│ │ - Returns plaintext only to handler (never stored in memory) │
│ └──────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────┤
│ │ Alpaca Client Factory                                        │
│ │ - Creates per-user Alpaca() instances from credentials       │
│ │ - Scoped to single request or session                        │
│ │ - Automatically disposed after use                           │
│ └──────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────┤
│ │ Route Handlers                                               │
│ │ - Use TenantContext + Alpaca client                          │
│ │ - Read/write operations scoped to user's account             │
│ └──────────────────────────────────────────────────────────────┘
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ PostgreSQL Database (NeonDB)                                    │
│ ┌──────────────────────────────────────────────────────────────┤
│ │ users (Better Auth)                                          │
│ │ - id (PK)                                                    │
│ │ - email, name, created_at                                    │
│ └──────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────┤
│ │ user_accounts (NEW)                                          │
│ │ - id (PK)                                                    │
│ │ - user_id (FK → users)                                       │
│ │ - account_name (e.g., "My Main Account")                     │
│ │ - alpaca_account_id (for reference)                          │
│ │ - is_active (for account switching)                          │
│ │ - created_at, updated_at                                     │
│ └──────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────┤
│ │ user_credentials (NEW)                                       │
│ │ - id (PK)                                                    │
│ │ - account_id (FK → user_accounts) UNIQUE                    │
│ │ - encrypted_api_key (pgcrypto encrypted)                     │
│ │ - encrypted_secret_key (pgcrypto encrypted)                  │
│ │ - encryption_algorithm (e.g., "aes-256-cbc")                 │
│ │ - created_at, updated_at                                     │
│ │ - last_decrypted_at (for audit)                              │
│ └──────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────┤
│ │ trading_positions (scoped by account_id)                     │
│ │ - id (PK)                                                    │
│ │ - account_id (FK → user_accounts)                            │
│ │ - ... position data ...                                      │
│ └──────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────┤
│ │ agent_logs (already has orchestrator_agent_id)               │
│ │ - Could extend with account_id for filtering by account      │
│ └──────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Authentication Layer (Better Auth)** | Validates user session from HTTPOnly cookie, returns authenticated user | FastAPI endpoints, Database (users table) |
| **Account Context Extractor** | Extracts account_id from request, validates user owns account, creates TenantContext | Database (user_accounts), Route handlers |
| **Credential Manager** | Encrypts/decrypts API keys using master key, never exposes plaintext in logs | Database (user_credentials), Alpaca Client Factory |
| **Alpaca Client Factory** | Creates per-user Alpaca() instances from decrypted credentials | Credential Manager, Route handlers |
| **Route Handlers** | Execute trading operations scoped to user's account | Account Context, Alpaca Client Factory, Database |
| **Database (PostgreSQL)** | Stores user data, accounts, encrypted credentials, and trading history | All components |

## Data Flow

### 1. User Login & Account Selection

```
User logs in via frontend
    ↓
Better Auth validates credentials
    ↓
HTTPOnly session cookie created (contains user_id)
    ↓
Frontend fetches list of user's accounts
    GET /api/accounts
    ├─ Authentication middleware verifies session
    ├─ Query: SELECT * FROM user_accounts WHERE user_id = $1
    └─ Return list of account names + IDs
    ↓
User selects account (e.g., "My Main Account")
    ↓
Frontend stores selected account_id in localStorage (NOT sensitive)
```

### 2. Per-User API Request

```
User clicks "Get Positions"
    ↓
Frontend sends:
    POST /api/positions
    Header: X-Account-ID: {account_id}
    ↓
FastAPI middleware:
    ├─ Validates user session (from cookie)
    ├─ Extracts account_id (from header)
    ├─ Queries: SELECT * FROM user_accounts
              WHERE id = $1 AND user_id = $2
    ├─ Ensures user owns this account
    └─ Creates TenantContext(user_id, account_id)
    ↓
Route handler:
    ├─ Receives TenantContext via Depends()
    ├─ Queries: SELECT * FROM user_credentials
              WHERE account_id = $1
    ├─ Decrypts API key (using master encryption key)
    ├─ Creates Alpaca(api_key=decrypted_key, secret=decrypted_secret)
    ├─ Fetches positions from Alpaca API
    ├─ Filters response by account_id (redundant safety)
    └─ Returns positions to frontend
    ↓
Alpaca client automatically disposed (goes out of scope)
Plaintext credentials never stored in memory after decryption
```

### 3. Account Switching (No Re-login)

```
User switches to different account (dropdown selection)
    ↓
Frontend updates X-Account-ID header in next request
    ↓
Middleware validates new account_id ownership
    ↓
Same request flow as above, but with different credentials
    ↓
No session refresh needed - same user, different account context
```

## Patterns to Follow

### Pattern 1: TenantContext Dependency Injection

**What:** A FastAPI dependency that validates user ownership of requested account and provides context to handlers.

**When:** Every handler that touches multi-tenant data must receive TenantContext.

**Example:**

```python
from pydantic import BaseModel
from fastapi import Depends, HTTPException

class TenantContext(BaseModel):
    user_id: str
    account_id: UUID

async def get_tenant_context(
    request: Request,
    user: AuthUser = Depends(get_current_user)
) -> TenantContext:
    """
    Extract and validate account_id from request header.
    Ensures user owns the requested account.
    """
    account_id_str = request.headers.get("X-Account-ID")
    if not account_id_str:
        raise HTTPException(status_code=400, detail="X-Account-ID header required")

    account_id = UUID(account_id_str)

    # Validate ownership
    async with database.get_connection() as conn:
        account = await conn.fetchrow(
            """SELECT id FROM user_accounts
               WHERE id = $1 AND user_id = $2""",
            account_id, user.id
        )

    if not account:
        raise HTTPException(status_code=403, detail="Account not found or unauthorized")

    return TenantContext(user_id=user.id, account_id=account_id)

@app.get("/api/positions")
async def get_positions(
    tenant: TenantContext = Depends(get_tenant_context)
):
    # tenant.account_id is guaranteed to belong to tenant.user_id
    positions = await alpaca_service.get_positions(tenant.account_id)
    return {"positions": positions}
```

### Pattern 2: Encrypted Credential Storage & Retrieval

**What:** Application-level encryption using pgcrypto for API keys. Credentials encrypted in database, decrypted in application, never logged.

**When:** Storing user's Alpaca API keys.

**Example:**

```python
# Storing credentials
async def store_user_credentials(
    account_id: UUID,
    api_key: str,
    secret_key: str,
    encryption_key: str  # Application master key from ENV
) -> None:
    """Encrypt and store Alpaca credentials."""
    async with database.get_connection() as conn:
        await conn.execute(
            """INSERT INTO user_credentials (account_id, encrypted_api_key, encrypted_secret_key)
               VALUES ($1, pgp_sym_encrypt($2, $3), pgp_sym_encrypt($4, $5))""",
            account_id, api_key, encryption_key, secret_key, encryption_key
        )

# Retrieving credentials
async def get_decrypted_credentials(
    account_id: UUID,
    encryption_key: str
) -> Dict[str, str]:
    """Decrypt and retrieve Alpaca credentials."""
    async with database.get_connection() as conn:
        row = await conn.fetchrow(
            """SELECT
                 pgp_sym_decrypt(encrypted_api_key, $2) as api_key,
                 pgp_sym_decrypt(encrypted_secret_key, $2) as secret_key
               FROM user_credentials
               WHERE account_id = $1""",
            account_id, encryption_key
        )

    if not row:
        raise ValueError(f"No credentials found for account {account_id}")

    # Decrypt happened in database, plaintext returned here
    # CRITICAL: Do not log these values
    return {
        "api_key": row["api_key"],
        "secret_key": row["secret_key"]
    }
```

### Pattern 3: Per-User Alpaca Client Factory

**What:** Create Alpaca() client instances scoped to a single request, using decrypted credentials.

**When:** Any handler that needs to interact with Alpaca API.

**Example:**

```python
class AlpacaClientFactory:
    def __init__(self, credential_manager: CredentialManager):
        self.credential_manager = credential_manager

    async def create_client(
        self,
        account_id: UUID,
        encryption_key: str
    ) -> Alpaca:
        """
        Create per-user Alpaca client from decrypted credentials.
        Client goes out of scope at end of request handler.
        """
        creds = await self.credential_manager.get_decrypted_credentials(
            account_id, encryption_key
        )

        # Create Alpaca client with user's credentials
        client = Alpaca(
            api_key=creds["api_key"],
            secret_key=creds["secret_key"],
            base_url="https://api.alpaca.markets"  # Or sandbox for testing
        )

        return client

# In route handler
@app.get("/api/positions")
async def get_positions(
    tenant: TenantContext = Depends(get_tenant_context),
    alpaca_factory: AlpacaClientFactory = Depends()
):
    # Create client (decryption happens here)
    alpaca = await alpaca_factory.create_client(
        tenant.account_id,
        encryption_key=config.ENCRYPTION_KEY  # From ENV
    )

    # Use client
    positions = await alpaca.get_positions()

    # Client goes out of scope here, credentials stay only in process memory
    return {"positions": positions}
```

### Pattern 4: Account Switching via Headers

**What:** Store account_id in localStorage (NOT HTTPOnly), pass in X-Account-ID header per-request.

**When:** Frontend needs to switch between user's multiple accounts.

**Frontend Example:**

```typescript
// Store selected account in localStorage after user selects it
localStorage.setItem('selectedAccountId', accountId)

// Every API request includes account context
async function getPositions() {
    const accountId = localStorage.getItem('selectedAccountId')
    const response = await fetch('/api/positions', {
        headers: {
            'X-Account-ID': accountId
        }
    })
    return response.json()
}

// User clicks dropdown, switch account
function switchAccount(newAccountId: string) {
    localStorage.setItem('selectedAccountId', newAccountId)
    // Next fetch uses new accountId automatically
}
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Storing Plaintext Credentials

**What:** Saving API keys unencrypted in database.

**Why bad:**
- Database breach exposes all user credentials
- Violates PCI/financial compliance
- No audit trail of credential access

**Instead:** Use pgcrypto or application-level encryption. Decrypt only in-memory for immediate use.

---

### Anti-Pattern 2: Credential Caching in Session State

**What:** Storing decrypted API keys in FastAPI `app.state` or session memory.

**Why bad:**
- Credentials persist across requests
- If application crashes/restarts, plaintext might be written to core dumps
- Makes credentials available to unrelated handlers

**Instead:** Decrypt credentials only when needed within handler scope. Let Python garbage collection handle cleanup.

---

### Anti-Pattern 3: Logging Credentials

**What:** Including API keys in logs or error messages.

**Why bad:**
- Log files become attack surface
- Credentials leakable via log aggregation services (e.g., ELK, DataDog)
- Violates compliance requirements

**Instead:**
- Never print credentials
- Use `**REDACTED**` placeholders in logs
- Create audit logs with only `account_id` + timestamp + action

---

### Anti-Pattern 4: Single Alpaca Client for All Users

**What:** Creating one global Alpaca() instance at startup with hardcoded credentials.

**Why bad:**
- All users see same account data
- No data isolation between users
- Impossible to support multiple accounts

**Instead:** Create per-request client instances from user's own credentials.

---

### Anti-Pattern 5: Account ID in Session Cookie

**What:** Including account_id in HTTPOnly session cookie.

**Why bad:**
- Forces session refresh when switching accounts
- Couples session lifecycle to account selection
- Complicates logout and account deletion

**Instead:** Keep session immutable (user_id only). Pass account_id per-request via header.

---

### Anti-Pattern 6: Missing Tenant ID Foreign Key

**What:** Tables have account_id but no database constraint.

**Why bad:**
- SQL injection or bugs can leak data across accounts
- No database-level protection

**Instead:** Add `FOREIGN KEY (account_id) REFERENCES user_accounts(id)` to every tenant-scoped table.

---

## Scalability Considerations

| Concern | At 10 users | At 100 users | At 10K users |
|---------|------------|--------------|--------------|
| **Credential Decryption** | Decrypt on-demand (milliseconds) | Same (in-memory only) | Cache decrypted keys in Redis with TTL (5 min) |
| **Account Ownership Validation** | Query user_accounts table | Same + add index on (user_id) | Add database read replica for reads |
| **Alpaca API Rate Limits** | No concern (low traffic) | Add circuit breaker for API calls | Use queuing system (Celery) for async trades |
| **Database Connections** | One pool fine | One pool still fine | Use connection pooling (PgBouncer) |
| **WebSocket Broadcasting** | Broadcast to all users | Filter by account_id before broadcasting | Use Redis Pub/Sub for cross-instance broadcasting |

## Database Schema Changes

```sql
-- New table: User's trading accounts
CREATE TABLE user_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    account_name VARCHAR(255) NOT NULL,
    alpaca_account_id VARCHAR(255),  -- For reference/audit
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
    UNIQUE (user_id, account_name)  -- Prevent duplicate account names per user
);

-- New table: Encrypted credentials
CREATE TABLE user_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL UNIQUE,
    encrypted_api_key BYTEA NOT NULL,
    encrypted_secret_key BYTEA NOT NULL,
    encryption_algorithm VARCHAR(50) DEFAULT 'pgcrypto-aes-256',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_decrypted_at TIMESTAMP,  -- Audit trail

    FOREIGN KEY (account_id) REFERENCES user_accounts(id) ON DELETE CASCADE
);

-- Extend existing trading tables with account_id
ALTER TABLE alpaca_orders
ADD COLUMN account_id UUID,
ADD FOREIGN KEY (account_id) REFERENCES user_accounts(id) ON DELETE CASCADE;

ALTER TABLE alpaca_positions
ADD COLUMN account_id UUID,
ADD FOREIGN KEY (account_id) REFERENCES user_accounts(id) ON DELETE CASCADE;

ALTER TABLE trading_positions
ADD COLUMN account_id UUID,
ADD FOREIGN KEY (account_id) REFERENCES user_accounts(id) ON DELETE CASCADE;
```

## Security Boundaries

### Encryption at Rest
- API keys encrypted in database using pgcrypto (`pgp_sym_encrypt`)
- Encryption key (master key) stored in ENV variable, never committed to git
- Each credential encrypted with same master key (simpler than per-credential keys for MVP)

### Encryption in Transit
- All communication from frontend to backend over HTTPS
- Better Auth cookies are HTTPOnly + Secure (browser handles)
- API keys never sent from frontend (decryption happens backend-only)

### Access Control
- Every handler validated by `get_tenant_context` dependency
- TenantContext verifies `user_id` owns `account_id`
- Database foreign keys enforce referential integrity
- Row-level filtering on all queries (WHERE account_id = $1)

### Audit Trail
- Log only `action`, `account_id`, `timestamp`, `user_id` - never credentials
- `last_decrypted_at` in user_credentials table for access auditing
- Consider audit log table for compliance (separate from main logs)

## Build Order Implications

**Phase 1: Authentication (Dependency)**
- Ensure Better Auth working
- `get_current_user` dependency must work before adding multi-tenant

**Phase 2: Account Management (Foundation)**
- Create `user_accounts` table
- Create account selector UI (dropdown)
- Create account switching logic (store/retrieve from localStorage)

**Phase 3: Credential Storage (Core)**
- Create `user_credentials` table
- Implement credential encryption/decryption
- Build credential manager service
- Test encryption/decryption end-to-end

**Phase 4: Request Context (Gating)**
- Implement `TenantContext` dependency
- Update ALL handlers to require TenantContext
- Update all queries to filter by account_id

**Phase 5: Per-User Clients (Integration)**
- Build AlpacaClientFactory
- Update Alpaca service to use factory
- Test with multiple user accounts

**Phase 6: Data Migration (Risky)**
- Add account_id to existing trading tables
- Backfill account_id for existing orders/positions
- Update WebSocket broadcasting to filter by account_id

## Sources

- [Multi-Tenant SaaS Data Isolation Patterns](https://www.future-processing.com/blog/multi-tenant-architecture/) - Multi-tenant database design patterns comparison
- [PostgreSQL Encryption Options](https://www.postgresql.org/docs/current/encryption-options.html) - Official PostgreSQL documentation on encryption approaches
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/) - FastAPI authentication and authorization patterns
- [Azure Multi-Tenant Architecture](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/storage-data) - Microsoft's multi-tenant storage and data patterns
- [Multi-Tenant Data Security for Databases](https://baffle.io/blog/multi-tenant-data-security/) - Baffle's credential encryption and isolation strategies
- [AWS Multi-Tenant SaaS Encryption Strategy](https://aws.amazon.com/blogs/architecture/simplify-multi-tenant-encryption-with-a-cost-conscious-aws-key-strategy/) - AWS's keys-per-tenant encryption model
- [Dynatrace Tenant Isolation](https://www.dynatrace.com/news/blog/separated-storage-and-unique-encryption-keys-for-each-tenant/) - Enterprise-scale multi-tenant data isolation
- [API Vault & Credential Management 2026](https://www.digitalapi.ai/blogs/top-api-key-management-tools) - Current credential management tools and patterns
- [Fintech Account Management Trends](https://innowise.com/blog/fintech-trends/) - Session management and multi-account patterns in fintech apps

# Phase 2: Database Schema - Research

**Researched:** 2026-01-29
**Domain:** PostgreSQL user accounts/credentials tables with Row-Level Security
**Confidence:** HIGH

## Summary

Phase 2 requires designing and implementing two new PostgreSQL tables (`user_accounts` and `user_credentials`) that integrate with the encryption service from Phase 1 while enforcing row-level security (RLS) to prevent users from accessing each other's data. The phase bridges the gap between user authentication (Better Auth tables from Phase 1) and secure credential storage.

Research confirms that the standard approach for this domain is:
1. **user_accounts table**: Stores user-specific account metadata linking to Better Auth users (TEXT id reference)
2. **user_credentials table**: Stores encrypted API credentials with foreign keys to user_accounts for isolation
3. **Row-Level Security**: PostgreSQL native RLS policies enforcing user_id-based filtering on credentials queries
4. **Encrypted Columns**: SQLAlchemy TypeDecorator pattern for transparent encryption/decryption in ORM

**Critical Finding:** PostgreSQL RLS is mature and production-ready for single-tenant-per-user isolation, but performance must be validated at scale. Key gotchas: missing indexes on policy columns (100x performance impact), function call overhead in policies, and queries with aggregations/limits. Testing must use non-superuser accounts with `FORCE ROW LEVEL SECURITY` to catch bugs that would otherwise be hidden.

**Primary recommendation:** Implement straightforward RLS policies using indexed user_id columns and SECURITY DEFINER functions for complex authorization. Design the schema with denormalization (storing user_id directly on credentials table) rather than requiring joins, which provides simpler policies and better performance. Use SQLAlchemy's TypeDecorator for encrypted columns to abstract encryption/decryption from business logic.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PostgreSQL | 15+ | Native RLS and constraint support | Industry standard; Neon provides managed PostgreSQL; RLS is built-in |
| SQLAlchemy | 2.0+ | ORM for encrypted column types | Already in use; TypeDecorator pattern is official approach for transparent encryption |
| cryptography | 47.0.0+ | Fernet encryption (inherited from Phase 1) | Already implemented; provides AES-128 + HMAC authentication |
| alembic | 1.13.0+ | Database schema migrations | Industry standard for SQLAlchemy migration management |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.0.0+ | Environment variable loading (inherited from Phase 1) | Already in use for ENCRYPTION_KEY |

### Alternatives Considered
| Instead of | Could Use | Tradeoff | Why NOT Recommended |
|------------|-----------|----------|---------------------|
| PostgreSQL RLS | Application-level authorization in FastAPI | Must check permissions in every endpoint; duplicates access control logic | RLS is database-enforced; prevents accidental data leaks from application bugs |
| PostgreSQL RLS | pgcrypto for database encryption | Database encrypts, but key must be stored in DB or queries; performance overhead per row | Key exposure risk; application-level encryption with environment key is more secure |
| SQLAlchemy TypeDecorator | Manual encrypt/decrypt in model methods | Code duplication; easy to forget encryption on some paths | TypeDecorator centralizes encryption; transparent to business logic |
| Foreign key constraint | Application-level relationship validation | Must check in FastAPI endpoints; inconsistent state possible | Database constraints prevent inconsistent state at the storage layer |
| Indexed user_id in RLS policy | Subqueries for complex authorization | Queries scale exponentially with rows; 100x performance penalty | Direct indexed column lookup is linear; scales to millions of rows |

**Installation:**
```bash
uv add sqlalchemy alembic
uv add --dev pytest pytest-asyncio httpx asyncpg
```

## Architecture Patterns

### Recommended Project Structure
```
apps/orchestrator_db/
├── models.py                     # [MODIFIED] Add UserAccount, UserCredential models
├── migrations/
│   ├── 14_user_accounts.sql     # [NEW] user_accounts table + indexes
│   └── 15_user_credentials.sql  # [NEW] user_credentials table + RLS policies
├── sync_models.py               # [EXISTING] Sync models to app directories

apps/orchestrator_3_stream/backend/
├── modules/
│   ├── encryption_service.py    # [EXISTING] From Phase 1
│   ├── database.py              # [MODIFIED] Add user account queries
│   └── models/
│       └── user_models.py       # [NEW] SQLAlchemy ORM models with TypeDecorator
├── schemas/
│   └── user_schemas.py          # [NEW] Pydantic schemas for API
└── routers/
    └── users.py                 # [NEW] FastAPI endpoints for user accounts

.planning/phases/02-database-schema/
├── 02-RESEARCH.md               # This file
├── 02-CONTEXT.md                # (Optional) User decisions from discussion
└── 02-PLAN.md                   # Task breakdown for phase execution
```

### Pattern 1: Row-Level Security with PostgreSQL
**What:** PostgreSQL's native RLS mechanism that evaluates policies as implicit WHERE clauses on every query, preventing unauthorized row access at the database layer (not application).

**When to use:** Every table containing user-sensitive data (user_credentials, user_accounts). RLS is the database's responsibility, not the application's.

**Example:**
```sql
-- Source: PostgreSQL documentation + Supabase best practices
-- Enable RLS on the table
ALTER TABLE user_credentials ENABLE ROW LEVEL SECURITY;

-- Policy: SELECT - Users can only see their own credentials
CREATE POLICY select_own_credentials ON user_credentials
    FOR SELECT
    USING (user_id = current_user_id());  -- Function wraps auth.uid() to enable caching

-- Policy: INSERT - Users can only insert credentials for themselves
CREATE POLICY insert_own_credentials ON user_credentials
    FOR INSERT
    WITH CHECK (user_id = current_user_id());

-- Policy: UPDATE/DELETE - Users can only modify their own credentials
CREATE POLICY delete_own_credentials ON user_credentials
    FOR DELETE
    USING (user_id = current_user_id());

-- CRITICAL: Create indexes on policy columns for performance
CREATE INDEX idx_user_credentials_user_id ON user_credentials(user_id);
```

**Performance optimization tips** (from research):
- Always index columns used in RLS policies (user_id). Missing indexes cause 100x performance penalty.
- Wrap functions like `auth.uid()` in `(SELECT current_user_id())` to enable query planner caching—up to 99.99% improvement.
- Denormalize authorization data into arrays instead of joins; use `IN` or `ANY` operations.
- For complex checks, create SECURITY DEFINER functions to bypass RLS on helper tables.

### Pattern 2: SQLAlchemy TypeDecorator for Encrypted Columns
**What:** Custom SQLAlchemy type that transparently encrypts data on INSERT and decrypts on SELECT, keeping encryption logic out of business logic.

**When to use:** For API key, secret key, and any credential fields that need encryption before storage.

**Example:**
```python
# Source: SQLAlchemy Wiki DatabaseCrypt pattern + phase requirements
from sqlalchemy import TypeDecorator, String
from sqlalchemy.ext.hybrid import hybrid_property
from modules.encryption_service import get_encryption_service

class EncryptedString(TypeDecorator):
    """
    Encrypted column type using Fernet (from Phase 1).
    Transparently encrypts on INSERT, decrypts on SELECT.
    """
    impl = String  # Database storage type
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt on INSERT/UPDATE"""
        if value is None:
            return None
        service = get_encryption_service()
        return service.encrypt(str(value))

    def process_result_value(self, value, dialect):
        """Decrypt on SELECT"""
        if value is None:
            return None
        service = get_encryption_service()
        return service.decrypt(value)

# Usage in model:
from sqlalchemy import Column, String, UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UserCredential(Base):
    __tablename__ = "user_credentials"

    id = Column(UUID, primary_key=True)
    user_id = Column(String, nullable=False)  # FK to user_accounts
    api_key = Column(EncryptedString(500))    # Auto-encrypted
    secret_key = Column(EncryptedString(500)) # Auto-encrypted
    created_at = Column(DateTime, default=datetime.utcnow)

# Transparently encrypted:
credential = UserCredential(user_id="user123", api_key="secret_key_xyz")
session.add(credential)
session.commit()

# Transparently decrypted on access:
retrieved = session.query(UserCredential).first()
print(retrieved.api_key)  # Returns plaintext, no decryption call needed
```

### Pattern 3: User Accounts and Credentials Table Relationship
**What:** Two-table structure where user_accounts bridges Better Auth users to their credentials, with foreign key cascade delete for data cleanup.

**When to use:** Whenever a user needs to store multiple API credentials. The user_accounts table provides the isolation boundary; user_credentials references it.

**Example (SQL):**
```sql
-- Source: PostgreSQL documentation + phase requirements

-- user_accounts: Links Better Auth user to our system
CREATE TABLE user_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE,
    account_name VARCHAR(255) NOT NULL,  -- Display name (e.g., "Trading Account 1")
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_accounts_user_id ON user_accounts(user_id);

-- user_credentials: Encrypted API keys per account
CREATE TABLE user_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,  -- Denormalized for RLS filtering
    credential_type VARCHAR(50) NOT NULL,  -- "alpaca", "polygon", etc.
    api_key TEXT NOT NULL,  -- Encrypted via TypeDecorator
    secret_key TEXT NOT NULL,  -- Encrypted via TypeDecorator
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMPTZ,  -- Optional: credential expiration
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_credentials_user_id ON user_credentials(user_id);
CREATE INDEX idx_user_credentials_account_id ON user_credentials(user_account_id);
CREATE UNIQUE INDEX idx_user_credentials_unique ON user_credentials(user_account_id, credential_type);
```

**Why this structure:**
- `user_account_id` on user_credentials maintains relationship to accounts
- `user_id` is denormalized for RLS filtering (no join required in policy)
- CASCADE DELETE ensures when an account is deleted, all credentials are cleaned up
- Unique constraint on (user_account_id, credential_type) prevents duplicate credentials

### Anti-Patterns to Avoid
- **RLS policy without indexes:** Creates sequential scans; 100x+ performance penalty on tables with millions of rows. ALWAYS index columns used in USING/WITH CHECK.
- **RLS policy with function calls on row data:** Every row triggers a function call; causes N+1 query problem. Instead, use SECURITY DEFINER functions to bypass RLS on helper tables.
- **Storing user_id directly without user_account_id:** Complicates multi-account support. Always include both for flexibility.
- **Testing RLS with superuser accounts:** Superusers bypass RLS silently. Test with non-superuser accounts and use FORCE ROW LEVEL SECURITY to catch hidden bugs.
- **Forgetting CASCADE DELETE on credentials:** Orphaned credential records remain after user/account deletion, causing data leaks. Always cascade.
- **Using application-level RLS instead of database RLS:** Duplicates logic; missed endpoint = data leak. Database RLS prevents the leak even if app logic is skipped.
- **Storing encryption key in database (pgcrypto):** Defeats encryption purpose. Keep keys in environment (inherited from Phase 1).

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "I'll encrypt columns manually in my ORM model methods" | Custom encrypt/decrypt on save/load | SQLAlchemy TypeDecorator | TypeDecorator centralizes encryption; one implementation, used everywhere. Manual methods lead to forgotten calls in some code paths. |
| "I'll check user permissions in my FastAPI endpoints" | Application-level authorization checks | PostgreSQL RLS policies | RLS is database-enforced; prevents leaks even if endpoint code has bugs. Application checks are app-tier; RLS is storage-tier (defense in depth). |
| "I'll test RLS with my admin account" | Testing with superuser/admin | Create non-superuser test accounts + FORCE ROW LEVEL SECURITY | Superusers bypass RLS silently; you won't catch bugs until production. Testing with restricted accounts reveals policy issues. |
| "I'll use a string user_id and join tables to enforce RLS" | Subqueries in RLS policies | Denormalize user_id directly on credentials table | Subqueries cause per-row joins; O(n²) complexity. Direct column access is O(n) with index. |
| "I'll store the encryption key in .env with the other config" | Key in .env or config files | Environment variable set at runtime (via secrets manager in prod) | Config files can be committed, backed up unencrypted, or leaked in container images. Environment variables follow cloud-native best practices. |
| "I'll auto-delete credentials using application cleanup jobs" | Application-level cascade delete | Database-level ON DELETE CASCADE constraint | App jobs can fail, be skipped, or forgotten. Database constraints guarantee cleanup happens. |

**Key insight:** Database-level constraints (RLS, CASCADE DELETE, unique indexes) are cheaper than application code because they're enforced by the storage layer, not vulnerable to bugs in higher layers.

## Common Pitfalls

### Pitfall 1: Missing Indexes on RLS Policy Columns
**What goes wrong:** RLS policies work, but queries are extremely slow (10-100x slower than expected) on tables with thousands of rows.

**Why it happens:** If a column used in RLS policy `USING` or `WITH CHECK` clauses isn't indexed, PostgreSQL does sequential scans—checking the policy against every row.

**How to avoid:**
- For every column referenced in an RLS policy, create an index: `CREATE INDEX idx_user_credentials_user_id ON user_credentials(user_id);`
- Verify index creation in migration files before deploying to production
- Run EXPLAIN ANALYZE on sample queries to confirm index is being used
- Test with realistic data volumes (thousands or millions of rows) before declaring success

**Warning signs:**
- SELECT queries on user_credentials table take >100ms
- Application logs show "Seq Scan" in EXPLAIN output
- Performance degrades as data volume grows

### Pitfall 2: Testing RLS with Superuser Accounts
**What goes wrong:** RLS policies pass all tests but fail in production for regular users. The gap occurs because superusers bypass RLS entirely without warning.

**Why it happens:** PostgreSQL allows superusers (database owners) to ignore RLS policies. Developers test with their admin account, which silently bypasses the policy.

**How to avoid:**
- Create test accounts with limited permissions (not superuser)
- Use `ALTER TABLE user_credentials FORCE ROW LEVEL SECURITY;` to enforce RLS even for table owner
- Write test cases that connect as specific users and verify isolation
- Example test:
  ```python
  # Test as user_1 (not superuser)
  result = await db.fetch(
      "SELECT * FROM user_credentials WHERE user_id = $1",
      "user_1",
      user=authenticated_user_1  # Use restricted user, not admin
  )
  assert len(result) > 0  # user_1 sees their own creds

  # Test isolation: user_2 cannot see user_1's creds
  result = await db.fetch(
      "SELECT * FROM user_credentials WHERE user_id = $1",
      "user_1",
      user=authenticated_user_2  # Different user, should see nothing
  )
  assert len(result) == 0  # user_2 does NOT see user_1's creds
  ```

**Warning signs:**
- No test database users with restricted permissions
- Tests pass with localhost admin connection
- `SELECT current_user;` in tests returns `"postgres"` or table owner

### Pitfall 3: RLS Policies Using Uncached Functions
**What goes wrong:** Queries are slow even with indexes because the RLS policy calls a function for every row, causing redundant computation.

**Why it happens:** Functions like `auth.uid()` that aren't marked STABLE are evaluated once per row instead of once per statement. When processing 1,000 rows, the function runs 1,000 times.

**How to avoid:**
- Wrap expensive functions in a subquery to enable caching: `(SELECT current_user_id())` instead of `current_user_id()`
- Mark custom functions as STABLE or IMMUTABLE if they have no side effects: `CREATE FUNCTION current_user_id() STABLE AS ...`
- Test query performance with EXPLAIN ANALYZE to confirm function caching is working

**Warning signs:**
- EXPLAIN output shows repeated function calls instead of single caching
- Queries slow down linearly with row count (O(n) instead of O(1) check)

### Pitfall 4: Cascade Delete Causing Unexpected Data Loss
**What goes wrong:** Deleting a single user account unexpectedly deletes all their credentials, and the credentials aren't backed up.

**Why it happens:** CASCADE DELETE is powerful but dangerous if not carefully planned. The constraint silently deletes related rows.

**How to avoid:**
- Document which tables have CASCADE DELETE and which don't
- For sensitive data like credentials, prefer soft deletes (is_deleted flag) or audit logging
- Create triggers to log deleted credentials to an audit table before cascade delete removes them
- Test delete operations in a non-production environment first
- Example:
  ```sql
  -- Add audit logging before cascade delete
  CREATE TABLE user_credentials_audit (
      id UUID,
      user_account_id UUID,
      user_id TEXT,
      action TEXT,  -- 'deleted'
      deleted_at TIMESTAMPTZ DEFAULT NOW()
  );

  CREATE TRIGGER log_credential_delete
  BEFORE DELETE ON user_credentials
  FOR EACH ROW
  EXECUTE FUNCTION log_deleted_credential();
  ```

**Warning signs:**
- Deleting a user results in silent deletion of all their credentials
- No audit trail of what was deleted
- Credentials unrecoverable after account deletion

### Pitfall 5: RLS Policies with Complex Subqueries or Joins
**What goes wrong:** RLS policy depends on a subquery or join to helper tables, causing exponential performance degradation.

**Why it happens:** Each row in user_credentials triggers the subquery/join; 1,000 rows means 1,000 subquery evaluations (N+1 problem).

**How to avoid:**
- Denormalize authorization data onto the table itself (store user_id directly, not just user_account_id)
- Use SECURITY DEFINER functions to bypass RLS on helper tables, then cache results
- Use array-based checks (`IN` or `ANY`) instead of joins
- Example (bad):
  ```sql
  CREATE POLICY check_via_join ON user_credentials
  USING (user_account_id IN (
      SELECT id FROM user_accounts WHERE user_id = current_user_id()
  ));  -- This subquery runs per row!
  ```
- Example (good):
  ```sql
  CREATE POLICY check_via_denormalization ON user_credentials
  USING (user_id = current_user_id());  -- Direct column; no subquery
  ```

**Warning signs:**
- RLS subqueries involving joins or aggregates
- Query plans showing "Subquery" repeated multiple times
- Performance degrades exponentially with row count

### Pitfall 6: Encrypted Columns Without Testing Round-Trip Encryption
**What goes wrong:** API key is encrypted and stored, but when retrieved and used in Alpaca API call, authentication fails (decrypted value differs from original).

**Why it happens:** Encryption/decryption round-trips with UTF-8 encoding can lose data if not carefully handled. Whitespace might be trimmed; special characters might be mangled.

**How to avoid:**
- Always test round-trip encryption in unit tests: encrypt(X) → decrypt → assert equals X
- Test with real Alpaca key formats (e.g., "PK..." and "sp...")
- Test edge cases: empty strings, special characters, Unicode
- Example test:
  ```python
  def test_credential_encryption_round_trip():
      service = get_encryption_service()

      test_cases = [
          "PK0123456789ABCDEF",  # Real Alpaca API key format
          "sp0123456789abcdefghijklmnop",  # Real Alpaca secret format
          "special!@#$%^&*()chars",  # Edge case
          "",  # Empty string
      ]

      for plaintext in test_cases:
          encrypted = service.encrypt(plaintext)
          decrypted = service.decrypt(encrypted)
          assert decrypted == plaintext, f"Round-trip failed: {plaintext} != {decrypted}"
  ```

**Warning signs:**
- Credentials fail to authenticate after storage/retrieval
- InvalidToken errors from Fernet during decrypt
- Decrypted values have missing characters or garbled text

## Code Examples

Verified patterns from official sources:

### SQLAlchemy ORM Model with Encrypted Columns
```python
# Source: SQLAlchemy Wiki DatabaseCrypt pattern + cryptography.io

from datetime import datetime
from uuid import uuid4, UUID
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, TypeDecorator, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import declarative_base, relationship
from modules.encryption_service import get_encryption_service

Base = declarative_base()

class EncryptedString(TypeDecorator):
    """Custom type that transparently encrypts/decrypts strings."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt on INSERT/UPDATE"""
        if value is None:
            return None
        service = get_encryption_service()
        return service.encrypt(str(value))

    def process_result_value(self, value, dialect):
        """Decrypt on SELECT"""
        if value is None:
            return None
        service = get_encryption_service()
        return service.decrypt(value)


class UserAccount(Base):
    """User's account (linked to Better Auth user)."""
    __tablename__ = "user_accounts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False, unique=True)  # FK to user.id from Better Auth
    account_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to credentials
    credentials = relationship("UserCredential", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_user_accounts_user_id', 'user_id'),
    )


class UserCredential(Base):
    """Encrypted API credentials for a user account."""
    __tablename__ = "user_credentials"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_account_id = Column(PGUUID(as_uuid=True), ForeignKey('user_accounts.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String(255), nullable=False)  # Denormalized for RLS
    credential_type = Column(String(50), nullable=False)  # "alpaca", "polygon", etc.
    api_key = Column(EncryptedString(500), nullable=False)  # Auto-encrypted
    secret_key = Column(EncryptedString(500), nullable=False)  # Auto-encrypted
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to account
    account = relationship("UserAccount", back_populates="credentials")

    __table_args__ = (
        Index('idx_user_credentials_user_id', 'user_id'),
        Index('idx_user_credentials_account_id', 'user_account_id'),
        # Unique constraint: user can only have one credential per type per account
        # (handled in migration)
    )
```

### PostgreSQL RLS Policies
```sql
-- Source: PostgreSQL documentation + Supabase best practices

-- Enable RLS on user_accounts table
ALTER TABLE user_accounts ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own account
CREATE POLICY user_accounts_select ON user_accounts
    FOR SELECT
    USING (user_id = current_user_id());

CREATE POLICY user_accounts_insert ON user_accounts
    FOR INSERT
    WITH CHECK (user_id = current_user_id());

CREATE POLICY user_accounts_update ON user_accounts
    FOR UPDATE
    USING (user_id = current_user_id())
    WITH CHECK (user_id = current_user_id());

CREATE POLICY user_accounts_delete ON user_accounts
    FOR DELETE
    USING (user_id = current_user_id());

-- Enable RLS on user_credentials table
ALTER TABLE user_credentials ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own credentials (via denormalized user_id)
CREATE POLICY user_credentials_select ON user_credentials
    FOR SELECT
    USING (user_id = current_user_id());

CREATE POLICY user_credentials_insert ON user_credentials
    FOR INSERT
    WITH CHECK (user_id = current_user_id());

CREATE POLICY user_credentials_update ON user_credentials
    FOR UPDATE
    USING (user_id = current_user_id())
    WITH CHECK (user_id = current_user_id());

CREATE POLICY user_credentials_delete ON user_credentials
    FOR DELETE
    USING (user_id = current_user_id());

-- CRITICAL: Create indexes on policy columns
CREATE INDEX idx_user_accounts_user_id ON user_accounts(user_id);
CREATE INDEX idx_user_credentials_user_id ON user_credentials(user_id);
CREATE INDEX idx_user_credentials_account_id ON user_credentials(user_account_id);
```

### Test Case for RLS Isolation
```python
# Source: Phase 2 success criteria + PostgreSQL RLS testing best practices

import asyncpg
import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_rls_user_isolation():
    """
    Verify RLS prevents users from accessing each other's credentials.
    CRITICAL: Test with non-superuser accounts, not admin.
    """
    # Create test users
    user_1_id = "user_001"
    user_2_id = "user_002"

    # Create test accounts for each user
    async with create_db_connection() as db:
        # Insert user_account for user_1
        account_1_id = await db.fetchval(
            """
            INSERT INTO user_accounts (user_id, account_name)
            VALUES ($1, $2)
            RETURNING id
            """,
            user_1_id, "Account 1"
        )

        # Insert user_account for user_2
        account_2_id = await db.fetchval(
            """
            INSERT INTO user_accounts (user_id, account_name)
            VALUES ($1, $2)
            RETURNING id
            """,
            user_2_id, "Account 2"
        )

        # Insert credentials for user_1
        cred_1_id = await db.fetchval(
            """
            INSERT INTO user_credentials
            (user_account_id, user_id, credential_type, api_key, secret_key)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            account_1_id, user_1_id, "alpaca", "PK123456789ABC", "sp123456789abc"
        )

        # Insert credentials for user_2
        cred_2_id = await db.fetchval(
            """
            INSERT INTO user_credentials
            (user_account_id, user_id, credential_type, api_key, secret_key)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            account_2_id, user_2_id, "alpaca", "PKabcdef123456", "spabcdef123456"
        )

    # Connect as user_1 and verify isolation
    async with create_db_connection_as_user(user_1_id) as db:
        # User_1 should see their own credentials
        results = await db.fetch(
            "SELECT id FROM user_credentials WHERE user_id = $1",
            user_1_id
        )
        assert len(results) == 1
        assert results[0]['id'] == cred_1_id

        # User_1 should NOT see user_2's credentials
        results = await db.fetch(
            "SELECT id FROM user_credentials WHERE user_id = $1",
            user_2_id
        )
        assert len(results) == 0, "RLS violated: user_1 can see user_2's credentials"

    # Connect as user_2 and verify isolation
    async with create_db_connection_as_user(user_2_id) as db:
        # User_2 should see their own credentials
        results = await db.fetch(
            "SELECT id FROM user_credentials WHERE user_id = $1",
            user_2_id
        )
        assert len(results) == 1
        assert results[0]['id'] == cred_2_id

        # User_2 should NOT see user_1's credentials
        results = await db.fetch(
            "SELECT id FROM user_credentials WHERE user_id = $1",
            user_1_id
        )
        assert len(results) == 0, "RLS violated: user_2 can see user_1's credentials"


@pytest.mark.asyncio
async def test_credential_encryption_round_trip():
    """Verify encrypted credentials can be decrypted correctly."""
    from modules.encryption_service import get_encryption_service

    service = get_encryption_service()

    # Test with real Alpaca credential formats
    test_cases = [
        ("PK0123456789ABCDEF", "sp0123456789abcdefghijklmnop"),
        ("PKabcdefghij1234567", "spabcdefghij123456789012345"),
        ("special!@#", "chars$%^&*()"),
        ("", ""),
    ]

    for api_key, secret_key in test_cases:
        encrypted_api = service.encrypt(api_key)
        encrypted_secret = service.encrypt(secret_key)

        decrypted_api = service.decrypt(encrypted_api)
        decrypted_secret = service.decrypt(encrypted_secret)

        assert decrypted_api == api_key, f"API key round-trip failed: {api_key} != {decrypted_api}"
        assert decrypted_secret == secret_key, f"Secret round-trip failed: {secret_key} != {decrypted_secret}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Application-level authorization checks | PostgreSQL RLS policies | 2018+ adoption | Database-enforced security; immune to application bugs |
| Manual permission checks in endpoints | RLS policies at storage layer | Best practice 2020+ | Single source of truth for access control |
| Unencrypted column storage | Application-level Fernet encryption with TypeDecorator | Standard since 2014 | Keys external to database; transparent in ORM |
| SQLAlchemy manual encryption in models | TypeDecorator for transparent encryption | Best practice 2015+ | Encryption centralized; harder to forget |
| Manual cascade delete in application | Database ON DELETE CASCADE constraint | Industry standard | Cleanup guaranteed by database; not dependent on app code |
| Sequential scans on RLS policy checks | Indexed user_id columns in RLS policies | Performance best practice 2015+ | 100x+ improvement on large tables |
| Testing RLS with admin accounts | Testing with non-superuser accounts + FORCE RLS | Best practice 2020+ | Catches bugs hidden by superuser bypass |

**Deprecated/outdated:**
- **Storing user permissions in application code:** Vulnerable to bugs; better to move to database RLS.
- **Unencrypted credential storage:** Unacceptable for any system handling API keys. Must encrypt.
- **Manual encryption in model methods:** Error-prone; use TypeDecorator for transparent encryption.
- **Cascade delete handled by application:** App code can fail; database constraints are more reliable.
- **RLS policies without indexes:** Creates performance bottleneck; always index policy columns.

## Open Questions

Things that couldn't be fully resolved:

1. **NeonDB-Specific RLS Performance at Scale**
   - What we know: Neon supports native PostgreSQL RLS; standard RLS policies work identically to self-hosted PostgreSQL
   - What's unclear: Does Neon provide any special monitoring or optimization tooling for RLS queries? Does the managed service have performance guardrails?
   - Recommendation: Implement standard RLS in Phase 2; if performance issues arise in Phase 3+, contact Neon support for optimization guidance. Load testing Phase 2 will reveal any platform-specific issues.
   - Reference: Phase context noted "PostgreSQL RLS performance unverified at scale - recommend load testing Phase 2"

2. **Current User ID Function Implementation**
   - What we know: RLS policies need to call something like `current_user_id()` to get the authenticated user
   - What's unclear: How does Better Auth integrate with PostgreSQL's authentication? Does the FastAPI session provide a current_user that maps to a database role?
   - Recommendation: Phase 2 planning should include investigation of FastAPI/Better Auth integration to determine how `current_user_id()` function is implemented (likely via auth_middleware.py setting a PostgreSQL role variable)
   - Reference: Better Auth uses TEXT user.id; FastAPI auth_middleware.py exists and likely provides session context

3. **Soft Delete vs. Cascade Delete for Credentials**
   - What we know: CASCADE DELETE is the standard pattern; audit logging can preserve deleted data
   - What's unclear: Should Phase 2 use hard delete (CASCADE) or soft delete (is_deleted flag)?
   - Recommendation: Start with CASCADE DELETE for simplicity; Phase 3 can add audit logging if compliance requirements emerge. Soft deletes add complexity (must filter is_deleted=false in all queries).

4. **Multi-Tenant Isolation Boundary**
   - What we know: Current design is single-user-per-account (user_id from Better Auth)
   - What's unclear: Will Phase 3+ require organization-level isolation (multiple users sharing an account)? The denormalized user_id approach assumes one user per account.
   - Recommendation: Design Phase 2 for single-user isolation; Phase 3 can add organization_id if multi-tenant sharing is needed. The schema can be extended without breaking changes.

## Sources

### Primary (HIGH confidence)

- [PostgreSQL: Documentation: 18: 5.9. Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) — Official CREATE POLICY syntax, USING/WITH CHECK semantics
- [Supabase: Row-Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security) — RLS performance optimization patterns, caching strategies, performance benchmarks
- [Supabase: Troubleshooting - RLS Performance and Best Practices](https://supabase.com/docs/guides/troubleshooting/rls-performance-and-best-practices-Z5Jjwv) — Detailed performance guidelines, indexing strategies, testing with non-superuser accounts
- [Neon: Row-Level Security with Neon](https://neon.com/docs/guides/row-level-security) — Neon-specific RLS guidance
- [Neon: Row-Level Security Tutorial](https://neon.com/docs/guides/rls-tutorial) — Step-by-step RLS implementation
- [SQLAlchemy: Custom Types](https://docs.sqlalchemy.org/en/20/core/custom_types.html) — TypeDecorator pattern for custom column types
- [SQLAlchemy Wiki: DatabaseCrypt](https://github.com/sqlalchemy/sqlalchemy/wiki/DatabaseCrypt) — Hybrid property encryption examples for ORM models
- [Miguel Grinberg: Encryption at Rest with SQLAlchemy](https://blog.miguelgrinberg.com/post/encryption-at-rest-with-sqlalchemy) — Transparent encryption with TypeDecorator
- [PostgreSQL: Documentation: 18: 5.5. Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html) — Foreign key constraints, ON DELETE CASCADE semantics
- [Alembic: Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) — Schema migrations with SQLAlchemy
- [cryptography.io: Fernet](https://cryptography.io/en/latest/fernet/) — Encryption library (Phase 1, inherited)

### Secondary (MEDIUM confidence)

- [Satori Cyber: PostgreSQL Row Level Security](https://satoricyber.com/postgres-security/postgres-row-level-security/) — Best practices overview with examples
- [Permit.io: Postgres RLS Implementation Guide](https://www.permit.io/blog/postgres-rls-implementation-guide) — Best practices for performance and security
- [Scott Pierce: Optimizing Postgres Row Level Security](https://scottpierce.dev/posts/optimizing-postgres-rls/) — In-depth performance optimization guide
- [ByteBase: Postgres RLS Limitations and Alternatives](https://www.bytebase.com/blog/postgres-row-level-security-limitations-and-alternatives/) — Tradeoff analysis
- [ByteBase: Common Postgres RLS Footguns](https://www.bytebase.com/blog/postgres-row-level-security-footguns/) — Common mistakes and prevention
- [AWS Prescriptive Guidance: Row-Level Security Recommendations](https://docs.aws.amazon.com/prescriptive-guidance/latest/saas-multitenant-managed-postgresql/rls.html) — Enterprise best practices
- [EnterpriseDB: Column and Row Level Security](https://www.enterprisedb.com/postgres-tutorials/how-implement-column-and-row-level-security-postgresql) — Implementation patterns
- [PostgreSQL: Documentation: 18: 41.10. Trigger Functions](https://www.postgresql.org/docs/current/plpgsql-trigger.html) — For audit logging with triggers
- [Supabase: Cascade Deletes](https://supabase.com/docs/guides/database/postgres/cascade-deletes) — Best practices for delete cascading

### Tertiary (LOW confidence, marked for validation)

- [WebSearch results on SQLAlchemy EncryptedType](https://github.com/fastapi/sqlmodel/issues/447) — Community implementations and discussions (verified against official patterns)
- [WebSearch on PostgreSQL RLS testing patterns](https://github.com/orgs/supabase/discussions/14576) — Community testing strategies (used for confirmation)

## Metadata

**Confidence breakdown:**
- **Standard Stack (HIGH):** PostgreSQL RLS is mature, documented by official PostgreSQL. SQLAlchemy TypeDecorator is official pattern. Alembic is industry-standard migration tool.
- **Architecture Patterns (HIGH):** RLS patterns verified with PostgreSQL documentation and Supabase (production Postgres service). TypeDecorator pattern from official SQLAlchemy wiki.
- **Performance Considerations (HIGH):** Supabase provides detailed benchmarks (99.94% improvement from indexing, 99.99% from function caching). Research verified with multiple enterprise sources.
- **Testing Strategies (HIGH):** PostgreSQL documentation explicitly warns against superuser testing. Supabase and AWS guidance confirm non-superuser testing required.
- **Pitfalls (HIGH):** All pitfalls documented in official PostgreSQL docs, Supabase best practices, and AWS guidance. Verified against multiple sources.
- **RLS Limitations (MEDIUM):** Research identified valid concerns; Scott Pierce and ByteBase provide detailed analysis. However, for this phase's single-user isolation, RLS is more than sufficient.

**Research date:** 2026-01-29
**Valid until:** 2026-02-28 (stable technologies; PostgreSQL RLS is mature)
**Next validation:** Before Phase 3 if multi-tenant requirements emerge (would require organization_id in schema)

**Key Research Findings Summary:**
1. PostgreSQL RLS is the standard, production-ready approach for user isolation
2. Performance is excellent with proper indexing (100x improvement documented)
3. Testing must use non-superuser accounts to catch bugs
4. SQLAlchemy TypeDecorator provides transparent encryption for ORM models
5. Denormalized schema (storing user_id directly) is more performant than joins in policies
6. NeonDB supports standard PostgreSQL RLS without special configuration

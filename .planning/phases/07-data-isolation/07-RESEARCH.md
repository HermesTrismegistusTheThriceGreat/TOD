# Phase 7: Data Isolation - Research

**Researched:** 2026-02-01
**Domain:** Multi-tenant data isolation with PostgreSQL Row-Level Security (RLS)
**Confidence:** HIGH

## Summary

This phase implements complete tenant isolation — ensuring users cannot see each other's data anywhere in the system. The architecture uses PostgreSQL Row-Level Security (RLS) as the primary defense mechanism, combined with application-level credential validation and filtering. The codebase already has RLS policies in place (migration 15_user_credentials_rls.sql), but the implementation is incomplete without proper browser testing and logging.

The standard approach for multi-tenant data isolation in Python/FastAPI is:
1. **Database-level enforcement** via PostgreSQL RLS with `SET LOCAL app.current_user_id` before queries
2. **Application-level filtering** where endpoints validate credential ownership before fetching external data
3. **Transparent context management** using async context managers that set RLS context
4. **Comprehensive testing** verifying isolation through browser-based testing and integration tests

**Primary recommendation:** Complete the three isolated systems verification (accounts isolation, positions isolation, orders isolation) using database RLS + application filtering, then verify through real browser testing with actual logout/login cycles.

## Standard Stack

The established approach for multi-tenant data isolation in modern SaaS:

### Core
| Library/Pattern | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PostgreSQL RLS | 13+ | Row-level policy enforcement | Database-enforced defense-in-depth, transparent to queries |
| asyncpg | 0.29+ | Async PostgreSQL driver | Allows `SET LOCAL` session variables for RLS context per connection |
| FastAPI Depends | 0.100+ | Dependency injection | Cleanly injects `get_current_user` into route handlers |
| SET LOCAL (SQL) | N/A | Transaction-scoped context | RLS policies check `current_user_id()` function against this |
| app.current_user_id (session var) | N/A | Tenant context storage | Function retrieves this to filter rows in RLS policies |

### Supporting
| Pattern | Purpose | When to Use |
|---------|---------|-------------|
| `get_connection_with_rls(user_id)` context manager | Acquires connection and sets RLS context atomically | Every RLS-protected query (credentials, accounts) |
| `get_decrypted_alpaca_credential()` context manager | Validates credential ownership via RLS + decrypts on-demand | Positions/orders endpoints before external API calls |
| Credential ownership validation (RLS + app logic) | Double-check: database enforces via policy, app validates via query | Critical endpoints like positions, orders |
| User authentication via FastAPI Depends | Extracts current user from Better Auth session cookie | All protected endpoints |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PostgreSQL RLS | Application-level WHERE clauses only | No defense if app bug leaks query, no defense for direct DB access |
| Session variable per connection | PostgreSQL users per tenant | Requires 1 DB user per tenant (doesn't scale past ~100 tenants) |
| FORCE ROW LEVEL SECURITY | Standard RLS (without FORCE) | Superuser can bypass without FORCE; testing requires same enforcement |

## Architecture Patterns

### Core Pattern: RLS Context Management

**What:** Every database operation that touches tenant data:
1. Extracts current user from authentication
2. Acquires database connection
3. Sets `SET LOCAL app.current_user_id = '{user_id}'` (transaction-scoped)
4. Queries automatically filtered by RLS policies

**When to use:** All queries on `user_accounts`, `user_credentials`, and tenant-specific data

**Example:**
```python
# Source: /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/database.py (lines 1991-2013)
@asynccontextmanager
async def get_connection_with_rls(user_id: str):
    """
    Async context manager for database connections with RLS context.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        await set_rls_context(conn, user_id)  # SET LOCAL app.current_user_id
        yield conn
```

### Pattern: Credential-Protected Endpoints

**What:** Endpoints that fetch external data must validate credential ownership twice:
1. Database-level: RLS policy filters credentials table by `user_id = current_user_id()`
2. Application-level: Query succeeds only if credential found and user_id matches

**When to use:** `/api/positions`, `/api/orders` endpoints that call external APIs

**Example:**
```python
# Source: /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/main.py (lines 1243-1306)
@app.get("/api/positions", response_model=GetPositionsResponse)
async def get_positions(
    request: Request,
    credential_id: str = Query(...),  # Required: user must specify which credential
    user: AuthUser = Depends(get_current_user)  # Authentication
):
    # Set RLS context: queries filtered by user_id
    async with get_connection_with_rls(user.id) as conn:
        # Query credential with RLS (returns only user's credentials)
        # If not found: ValueError (isolation successful)
        async with get_decrypted_alpaca_credential(
            conn, credential_id, user.id
        ) as (api_key, secret_key):
            # Safe to use credentials (ownership verified)
            positions = await alpaca_service.get_all_positions_with_credential(
                api_key=api_key,
                secret_key=secret_key
            )
```

### Pattern: RLS Policies Structure

**What:** Each table has four policies (SELECT, INSERT, UPDATE, DELETE) that check `user_id = current_user_id()`

**When to use:** Every tenant-data table (user_accounts, user_credentials)

**Example from migration 15:**
```sql
-- SELECT: Users can only see their own credentials
CREATE POLICY user_credentials_select ON user_credentials
    FOR SELECT
    USING (user_id = current_user_id());

-- INSERT: Users can only create credentials for themselves
CREATE POLICY user_credentials_insert ON user_credentials
    FOR INSERT
    WITH CHECK (user_id = current_user_id());

-- UPDATE: Users can only update their own credentials
CREATE POLICY user_credentials_update ON user_credentials
    FOR UPDATE
    USING (user_id = current_user_id())
    WITH CHECK (user_id = current_user_id());

-- DELETE: Users can only delete their own credentials
CREATE POLICY user_credentials_delete ON user_credentials
    FOR DELETE
    USING (user_id = current_user_id());
```

### Anti-Patterns to Avoid
- **Forgetting to use `get_connection_with_rls()`:** Querying without setting RLS context bypasses policies
- **Relying on RLS alone without application validation:** If RLS context is not set (bug), queries return all rows
- **Not using `FORCE ROW LEVEL SECURITY`:** Without FORCE, superuser connections bypass policies, breaking tests
- **Caching connection objects across requests:** Each request must get fresh connection with new RLS context
- **Trusting client-provided user_id:** Always extract from authenticated session, never from request body/query
- **Missing isolation verification in tests:** Must test with real database and multiple users

## Don't Hand-Roll

Problems that look simple but require careful implementation:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-tenant filtering in queries | WHERE user_id = ? in every query | PostgreSQL RLS policies | One missed WHERE clause = data leak; RLS enforces at database level |
| Credential context switching | Global credential state in app | Decrypt-on-demand context managers | Global state = request concurrency bugs; context manager scopes to single request |
| Tenant context per request | Store tenant_id in global variable | FastAPI Depends + SET LOCAL session var | Async concurrency means global variables cause crosstalk |
| Checking ownership before API calls | IF check in Python | Database RLS + credential query | Can query returns result but policy blocks it; don't add extra Python checks |
| Testing isolation | Unit tests with mocks | Integration tests with real database | Mocks hide RLS, database tests verify actual behavior |

**Key insight:** PostgreSQL RLS is a safety net that catches bugs in application logic. Don't try to replicate it in Python — use it as the enforcement layer, and write tests that verify the policies work.

## Common Pitfalls

### Pitfall 1: Forgetting RLS Context on New Connection
**What goes wrong:** New endpoint acquires connection but never calls `set_rls_context()`, queries return rows for all users
**Why it happens:** Easy to forget one small function call, especially if copy-pasting endpoint code
**How to avoid:** Always use `get_connection_with_rls(user.id)` context manager, never raw `get_connection()`
**Warning signs:** Same data appearing for different users, test failure showing rows from wrong user

### Pitfall 2: Mixing Raw Connections and RLS Context
**What goes wrong:** Some endpoints use RLS, others don't; incomplete coverage leaves gaps
**Why it happens:** Partial migration when adding multi-tenancy to existing code
**How to avoid:** Audit all endpoints touching `user_credentials`, `user_accounts` — every single one needs RLS
**Warning signs:** Data isolation working in some endpoints but not others; browser test shows different results for same page

### Pitfall 3: Relying on Application Logic Alone Without Database Enforcement
**What goes wrong:** Bug in credential ownership check (e.g., missing error handling), unencrypted data leaked
**Why it happens:** Assumption that application code is sufficient; doesn't account for future bugs or direct DB access
**How to avoid:** Treat RLS as mandatory, not optional; add `FORCE ROW LEVEL SECURITY` to all tables
**Warning signs:** Direct database queries return filtered data, but application API returns wrong data (policy not enforced)

### Pitfall 4: Client-Supplied User ID in Queries
**What goes wrong:** Endpoint trusts request body `{"user_id": "attacker"}`, credential accessed across tenants
**Why it happens:** Easy mistake when building filters; looks like POST request to user's account
**How to avoid:** Always extract user_id from authenticated session (`get_current_user`), never from request body
**Warning signs:** User can change query parameter to access other users' data; integration test with different user_id passes

### Pitfall 5: Caching Connections Across Requests
**What goes wrong:** Thread pool caches connection with RLS context from previous user, new request sees old user's data
**Why it happens:** Connection pooling defaults, or re-using connections between requests
**How to avoid:** Each request acquires fresh connection from pool, RLS context scoped to transaction via `SET LOCAL`
**Warning signs:** Race condition test failures; data from different users appearing randomly in responses

### Pitfall 6: Missing Integration Tests for Isolation
**What goes wrong:** Unit tests pass, but real browser testing shows users seeing each other's data
**Why it happens:** Mocks don't trigger RLS policies; only real database enforces them
**How to avoid:** Require browser-based tests that switch users; integration tests with real database
**Warning signs:** Test suite passes but production issues reported, RLS policies look correct but aren't enforced

## Code Examples

### Example 1: RLS Context Setter (Database Module)
```python
# Source: /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/database.py (lines 1972-2013)
async def set_rls_context(conn: asyncpg.Connection, user_id: str) -> None:
    """Set RLS context for the current transaction."""
    await conn.execute(f"SET LOCAL app.current_user_id = '{user_id}'")

@asynccontextmanager
async def get_connection_with_rls(user_id: str):
    """Async context manager for database connections with RLS context."""
    pool = get_pool()
    async with pool.acquire() as conn:
        await set_rls_context(conn, user_id)
        yield conn
```

### Example 2: Credential Isolation Endpoint (Positions)
```python
# Source: /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/main.py (lines 1243-1306)
@app.get("/api/positions", response_model=GetPositionsResponse)
async def get_positions(
    request: Request,
    credential_id: str = Query(...),  # User specifies which credential
    user: AuthUser = Depends(get_current_user)  # Authentication required
):
    """Get positions for a specific credential (RLS-protected)."""
    try:
        user_id = user.id

        # RLS-protected query: only returns user's credentials
        async with get_connection_with_rls(user_id) as conn:
            # Query decrypts credential IF it belongs to user (RLS enforces)
            async with get_decrypted_alpaca_credential(
                conn, credential_id, user_id
            ) as (api_key, secret_key):
                # Safe: only user's credential decrypted
                positions = await alpaca_service.get_all_positions_with_credential(
                    api_key=api_key,
                    secret_key=secret_key
                )
                return GetPositionsResponse(
                    status="success",
                    positions=positions,
                    total_count=len(positions)
                )
    except ValueError as e:
        # Credential not found: RLS policy filtered it out
        # OR: credential_id belongs to different user (isolation working)
        logger.error(f"Credential access denied: {e}")
        return GetPositionsResponse(
            status="error",
            message=f"Credential access denied: {str(e)}"
        )
```

### Example 3: RLS Policy Definition (Database Migration)
```sql
-- Source: /Users/muzz/Desktop/tac/TOD/apps/orchestrator_db/migrations/15_user_credentials_rls.sql
-- Enable RLS with FORCE (critical for testing)
ALTER TABLE user_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_credentials FORCE ROW LEVEL SECURITY;

-- Policy for SELECT: only user's own credentials visible
CREATE POLICY user_credentials_select ON user_credentials
    FOR SELECT
    USING (user_id = current_user_id());

-- Policy for INSERT: can only create credentials for self
CREATE POLICY user_credentials_insert ON user_credentials
    FOR INSERT
    WITH CHECK (user_id = current_user_id());

-- Policy for UPDATE/DELETE: same user check
CREATE POLICY user_credentials_update ON user_credentials
    FOR UPDATE
    USING (user_id = current_user_id())
    WITH CHECK (user_id = current_user_id());

CREATE POLICY user_credentials_delete ON user_credentials
    FOR DELETE
    USING (user_id = current_user_id());
```

### Example 4: Helper Function for Current User (Database)
```sql
-- Source: /Users/muzz/Desktop/tac/TOD/apps/orchestrator_db/migrations/15_user_credentials_rls.sql (lines 69-79)
-- RLS policies check this function; FastAPI sets app.current_user_id via SET LOCAL
CREATE OR REPLACE FUNCTION current_user_id() RETURNS TEXT AS $$
BEGIN
    -- Returns user_id from session variable, NULL if not set (fail-safe)
    RETURN NULLIF(current_setting('app.current_user_id', TRUE), '');
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;  -- Fail-safe: no rows visible if error
END;
$$ LANGUAGE plpgsql STABLE;
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Application-only WHERE filtering | Application + database RLS | PostgreSQL 9.5+ (2016) | Defense-in-depth; database enforces even if app has bugs |
| Global tenant context variable | Per-connection `SET LOCAL` session var | Async adoption (2020+) | Safe for concurrent requests, no crosstalk |
| Testing with mocks | Integration tests with real database + RLS | FastAPI/SQLAlchemy maturity (2023+) | Catches real isolation failures, not just logic |
| Manual credential passing | Decrypt-on-demand context managers | Modern async patterns (2023+) | Scoped credentials, no global state, automatic cleanup |

**Deprecated/outdated:**
- Global tenant ID variables (threading issues with async)
- Per-tenant database users (doesn't scale beyond 100 tenants)
- Unit tests with mocked RLS (doesn't verify policies work)

## Open Questions

1. **Exact logging format for suspicious access attempts**
   - What we know: CONTEXT.md says "Log suspicious access attempts with user/credential details"
   - What's unclear: Format (structured JSON vs plaintext), retention policy, integration with application logging
   - Recommendation: Define structured JSON format with timestamp, user_id, credential_id, action, reason (e.g., "user A tried to access credential of user B") — matches error logging pattern already in codebase

2. **Integration tests vs browser tests for isolation verification**
   - What we know: CONTEXT.md prioritizes browser testing (switch accounts, logout/login), but doesn't mandate integration tests
   - What's unclear: Should integration tests complement browser tests, or are browser tests sufficient?
   - Recommendation: Both complementary: integration tests verify RLS policies work in isolation (faster, deterministic); browser tests verify end-to-end user journey (catches UI bugs)

3. **Positions endpoint fix structure**
   - What we know: `/api/positions` already takes `credential_id` query parameter and uses RLS (implementation verified)
   - What's unclear: Was this already fixed in prior phase? Or is this documentation of existing correct behavior?
   - Recommendation: Verify endpoint is wired correctly in frontend (passing credential_id on position requests), confirm browser test passes

## Sources

### Primary (HIGH confidence)
- **PostgreSQL RLS Migration:** `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_db/migrations/15_user_credentials_rls.sql` — Complete RLS policy definitions with FORCE ROW LEVEL SECURITY and helper functions
- **FastAPI RLS Context Manager:** `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/database.py` (lines 1972-2013) — Async context managers for RLS-protected queries
- **Credential Isolation Endpoints:** `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/main.py` (lines 1243-1423) — Implementation of `/api/positions` and `/api/orders` with credential ownership validation
- **Authentication Middleware:** `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/auth_middleware.py` — User extraction from Better Auth sessions

### Secondary (MEDIUM confidence)
- [Multi-Tenant Data Isolation with PostgreSQL Row Level Security](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/) — AWS Database Blog explaining RLS patterns for multi-tenancy
- [Multi-Tenant Architecture with FastAPI: Design Patterns and Pitfalls](https://medium.com/@koushiksathish3/multi-tenant-architecture-with-fastapi-design-patterns-and-pitfalls-aa3f9e75bf8c) — April 2025 Medium article on FastAPI multi-tenancy patterns
- [Postgres RLS Implementation Guide - Best Practices, and Common Pitfalls](https://www.permit.io/blog/postgres-rls-implementation-guide) — Comprehensive guide on RLS pitfalls (SQL injection in context functions, performance issues, limited column-level control)

### Tertiary (LOW confidence - WebSearch only)
- [Underrated Postgres: Build Multi-Tenancy with Row-Level Security](https://www.simplyblock.io/blog/underated-postgres-multi-tenancy-with-row-level-security/)
- [Multi-Tenancy Testing: What Is It and How Does It Work](https://testgrid.io/blog/multi-tenancy/)
- [fastapi-rowsecurity PyPI Package](https://pypi.org/project/fastapi-rowsecurity/)

## Metadata

**Confidence breakdown:**
- Standard Stack: **HIGH** — All stack components verified in codebase and official PostgreSQL documentation
- Architecture Patterns: **HIGH** — RLS patterns fully implemented in migrations and endpoints; async context managers verified
- Common Pitfalls: **MEDIUM** — Based on mix of codebase patterns and external best practices (Permit.io, AWS)
- Testing Approach: **MEDIUM** — Context mentions browser testing approach; integration test patterns inferred from existing test structure

**Research date:** 2026-02-01
**Valid until:** 2026-02-28 (stable domain; RLS patterns unchanged, but monitoring/logging implementation should be revisited if requirements change)

**Key assumption:** Phase context assumes `/api/positions` endpoint is already fixed with credential_id filtering (verified in codebase). If endpoint was not updated in prior phases, this needs to be confirmed before proceeding.

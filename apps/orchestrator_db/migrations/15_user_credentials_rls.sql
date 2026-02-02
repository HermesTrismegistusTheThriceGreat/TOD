-- ============================================================================
-- ROW-LEVEL SECURITY (RLS) POLICIES FOR USER DATA ISOLATION
-- ============================================================================
-- Implements database-enforced user data isolation using PostgreSQL RLS.
-- Prevents users from accessing each other's accounts and credentials.
--
-- Purpose:
--   Defense-in-depth security - even if application logic fails, database
--   enforces data isolation at the query level.
--
-- How It Works:
--   1. FastAPI middleware sets session variable: SET LOCAL app.current_user_id = '{user_id}'
--   2. RLS policies check current_user_id() against row's user_id column
--   3. Queries automatically filtered to authenticated user's data only
--   4. Works transparently - no changes needed to SELECT/INSERT/UPDATE/DELETE queries
--
-- FastAPI Integration Pattern:
--   ```python
--   # Example middleware pattern for setting user context
--   async def set_user_context(conn, user_id: str):
--       """Set RLS context before queries on this connection"""
--       await conn.execute(f"SET LOCAL app.current_user_id = '{user_id}';")
--
--   # In database operations (after authentication):
--   async with db.acquire() as conn:
--       await set_user_context(conn, current_user.id)
--
--       # All queries on this connection are now RLS-filtered
--       result = await conn.fetch("SELECT * FROM user_credentials")
--       # Returns only current user's credentials automatically
--   ```
--
-- Testing Considerations:
--   - FORCE ROW LEVEL SECURITY ensures policies apply even to table owner/superuser
--   - Test with actual user IDs, not postgres superuser account
--   - Verify isolation: user_1 cannot see user_2's data
--   - Test all CRUD operations: SELECT, INSERT, UPDATE, DELETE
--
-- Performance Notes:
--   - Indexes on user_id columns (created in Migration 14) are CRITICAL for RLS performance
--   - current_user_id() marked STABLE allows query planner to cache result per statement
--   - Denormalized user_id on credentials avoids joins in policy evaluation
--   - SET LOCAL is transaction-scoped (automatically cleared after transaction)
--
-- Security Notes:
--   - RLS policies deny by default (no policy = no access)
--   - USING clause filters SELECT/UPDATE/DELETE (which rows can be seen/modified)
--   - WITH CHECK clause filters INSERT/UPDATE (which rows can be created/modified)
--   - NULL user_id in session = no rows visible (fail-safe behavior)
--
-- Dependencies:
--   - Migration 14: user_accounts and user_credentials tables with user_id columns
--   - Migration 14: Indexes on user_id columns (performance)


-- ═══════════════════════════════════════════════════════════
-- HELPER FUNCTION: current_user_id()
-- ═══════════════════════════════════════════════════════════
-- Retrieves authenticated user ID from PostgreSQL session variable.
-- FastAPI sets this variable before each query via SET LOCAL.
--
-- Returns:
--   - TEXT: user_id if session variable is set
--   - NULL: if not set (fail-safe - NULL won't match any user_id)
--
-- Note: STABLE marking allows PostgreSQL query planner to cache the result
-- for the duration of a single SQL statement, improving performance.

CREATE OR REPLACE FUNCTION current_user_id() RETURNS TEXT AS $$
BEGIN
    -- NULLIF converts empty string to NULL for safety
    -- TRUE parameter makes current_setting return NULL instead of error if not set
    RETURN NULLIF(current_setting('app.current_user_id', TRUE), '');
EXCEPTION
    WHEN OTHERS THEN
        -- If any error occurs, return NULL (fail-safe)
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION current_user_id() IS 'Returns authenticated user ID from session variable (app.current_user_id) or NULL if not set';


-- ═══════════════════════════════════════════════════════════
-- ROW-LEVEL SECURITY: user_accounts
-- ═══════════════════════════════════════════════════════════

-- Enable RLS on table
ALTER TABLE user_accounts ENABLE ROW LEVEL SECURITY;

-- FORCE RLS even for table owner/superuser (critical for testing!)
-- Without this, postgres superuser bypasses RLS policies
ALTER TABLE user_accounts FORCE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (idempotency)
DROP POLICY IF EXISTS user_accounts_select ON user_accounts;
DROP POLICY IF EXISTS user_accounts_insert ON user_accounts;
DROP POLICY IF EXISTS user_accounts_update ON user_accounts;
DROP POLICY IF EXISTS user_accounts_delete ON user_accounts;

-- SELECT: Users can only see their own accounts
CREATE POLICY user_accounts_select ON user_accounts
    FOR SELECT
    USING (user_id = current_user_id());

-- INSERT: Users can only create accounts for themselves
CREATE POLICY user_accounts_insert ON user_accounts
    FOR INSERT
    WITH CHECK (user_id = current_user_id());

-- UPDATE: Users can only update their own accounts
-- USING: Can only target own rows
-- WITH CHECK: Cannot change user_id to another user
CREATE POLICY user_accounts_update ON user_accounts
    FOR UPDATE
    USING (user_id = current_user_id())
    WITH CHECK (user_id = current_user_id());

-- DELETE: Users can only delete their own accounts
CREATE POLICY user_accounts_delete ON user_accounts
    FOR DELETE
    USING (user_id = current_user_id());


-- ═══════════════════════════════════════════════════════════
-- ROW-LEVEL SECURITY: user_credentials
-- ═══════════════════════════════════════════════════════════

-- Enable RLS on table
ALTER TABLE user_credentials ENABLE ROW LEVEL SECURITY;

-- FORCE RLS even for table owner/superuser (critical for testing!)
ALTER TABLE user_credentials FORCE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (idempotency)
DROP POLICY IF EXISTS user_credentials_select ON user_credentials;
DROP POLICY IF EXISTS user_credentials_insert ON user_credentials;
DROP POLICY IF EXISTS user_credentials_update ON user_credentials;
DROP POLICY IF EXISTS user_credentials_delete ON user_credentials;

-- SELECT: Users can only see their own credentials
-- Uses denormalized user_id column (no join needed - fast!)
CREATE POLICY user_credentials_select ON user_credentials
    FOR SELECT
    USING (user_id = current_user_id());

-- INSERT: Users can only create credentials for themselves
-- Ensures user_id matches authenticated user
CREATE POLICY user_credentials_insert ON user_credentials
    FOR INSERT
    WITH CHECK (user_id = current_user_id());

-- UPDATE: Users can only update their own credentials
-- USING: Can only target own rows
-- WITH CHECK: Cannot change user_id to another user
CREATE POLICY user_credentials_update ON user_credentials
    FOR UPDATE
    USING (user_id = current_user_id())
    WITH CHECK (user_id = current_user_id());

-- DELETE: Users can only delete their own credentials
CREATE POLICY user_credentials_delete ON user_credentials
    FOR DELETE
    USING (user_id = current_user_id());


-- ═══════════════════════════════════════════════════════════
-- VERIFICATION QUERIES (for testing)
-- ═══════════════════════════════════════════════════════════
-- Run these to verify RLS is working:
--
-- 1. Check RLS is enabled:
--    SELECT relname, relrowsecurity, relforcerowsecurity
--    FROM pg_class
--    WHERE relname IN ('user_accounts', 'user_credentials');
--
-- 2. Check policies exist:
--    SELECT * FROM pg_policies
--    WHERE tablename IN ('user_accounts', 'user_credentials');
--
-- 3. Test isolation (as superuser):
--    BEGIN;
--    SET LOCAL app.current_user_id = 'user_123';
--    SELECT * FROM user_accounts;  -- Should only see user_123's accounts
--    ROLLBACK;

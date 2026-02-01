# Database User Has BYPASSRLS Privilege - RLS Not Enforced

**Priority:** CRITICAL
**Created:** 2026-02-01
**Phase:** 07-data-isolation
**Status:** BLOCKED

## Problem

The `neondb_owner` database user has the `BYPASSRLS` privilege, which completely bypasses Row-Level Security policies regardless of the `FORCE ROW LEVEL SECURITY` setting.

**Evidence:**
```sql
SELECT current_user, usesuper, usebypassrls
FROM pg_user
WHERE usename = current_user;

 current_user  | usesuper | usebypassrls
---------------+----------+--------------
 neondb_owner  |   False  |    True      ⚠️
```

Even though:
- RLS is enabled (`relrowsecurity = true`)
- FORCE RLS is enabled (`relforcerowsecurity = true`)
- RLS policies are defined correctly
- `current_user_id()` function works correctly

**RLS policies do NOT filter results** because `neondb_owner` has `BYPASSRLS` privilege.

## Security Impact

**CRITICAL:** User data isolation is NOT enforced. Any query from the application can see ALL users' data:
- All credentials from all users visible
- Positions from all accounts accessible
- Orders from all accounts accessible

This violates the core security requirement: "Friends can log in, add their own Alpaca accounts, and trade via chat — each person controls their own money."

## Root Cause

Neon (managed PostgreSQL service) grants `BYPASSRLS` to the database owner role by default. This is a cloud provider configuration.

## Solution Options

### Option 1: Create Application Role Without BYPASSRLS (RECOMMENDED)
```sql
CREATE ROLE app_user LOGIN PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE neondb TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Verify no BYPASSRLS
SELECT usename, usebypassrls FROM pg_user WHERE usename = 'app_user';
```

Update `.env`:
```
DATABASE_URL=postgresql://app_user:secure_password@...
```

### Option 2: Contact Neon Support
Request removal of BYPASSRLS from neondb_owner (may not be possible).

### Option 3: Switch Database Provider
Use a PostgreSQL provider that allows full role configuration.

## Next Steps

1. **IMMEDIATE:** Create `app_user` role without BYPASSRLS in Neon console
2. **UPDATE:** Change DATABASE_URL to use new role
3. **VERIFY:** Run RLS tests - should pass with new role
4. **DOCUMENT:** Update security documentation with role separation

## Testing

After fix, verify with:
```bash
cd apps/orchestrator_3_stream/backend
uv run python tests/test_rls_debug.py
# Should show "Bypass RLS: False"

uv run pytest tests/test_data_isolation.py -v
# All tests should pass
```

## References

- PostgreSQL RLS Documentation: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- Migration 15: `apps/orchestrator_db/migrations/15_user_credentials_rls.sql`
- Debug Script: `apps/orchestrator_3_stream/backend/tests/test_rls_debug.py`

## Related Requirements

- **SEC-01:** User-specific credential storage (BROKEN without RLS)
- **SEC-02:** Encrypted credential storage (Working, but accessible to all users)
- **DAT-01:** User account isolation (BROKEN without RLS)

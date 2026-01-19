# Plan: Fix Auth Service 500 Internal Server Error on Signup

## Task Description
Troubleshoot and fix the auth service returning 500 Internal Server Error when users attempt to sign up via `POST /api/auth/sign-up/email`. The auth service runs on port 9404, uses Better Auth v1.4.6 with Hono framework, and connects to a Neon PostgreSQL database.

## Objective
Restore full signup functionality by diagnosing and fixing the database schema issue preventing Better Auth from creating user records.

## Problem Statement
The auth service at `http://localhost:9404` returns a 500 Internal Server Error on signup requests. The frontend authentication flow works (routing, forms, API calls), but the backend fails to process signup requests. The most likely cause is missing Better Auth database tables in the Neon PostgreSQL database.

## Solution Approach
1. Diagnose the exact error by checking auth service logs
2. Use the **neon-mcp agent** to verify database connectivity and inspect existing tables
3. Use the **neon-mcp agent** to run SQL migrations creating required Better Auth tables (user, session, account, verification)
4. Test signup functionality end-to-end

## Relevant Files
Use these files to complete the task:

**Auth Service Configuration:**
- `apps/orchestrator_3_stream/auth-service/src/index.ts` - Hono server entry point
- `apps/orchestrator_3_stream/auth-service/src/auth.ts` - Better Auth configuration with pg Pool
- `apps/orchestrator_3_stream/auth-service/.env` - Database URL and secrets
- `apps/orchestrator_3_stream/auth-service/package.json` - Dependencies (better-auth v1.4.6)

**Neon MCP Agent:**
- `.claude/agents/neon-mcp.md` - Neon database management specialist agent configuration

**Documentation:**
- `neon_docs/neon-auth-overview.md` - Neon Auth with Better Auth documentation
- `neon_docs/neon-mcp-tools-reference.md` - Neon MCP server tools reference

### New Files
- `apps/orchestrator_3_stream/auth-service/src/migrate.ts` - Database migration script (if needed)

## Implementation Phases

### Phase 1: Diagnosis
Gather detailed error information from the auth service to confirm the root cause.

### Phase 2: Database Setup (via neon-mcp agent)
Use the neon-mcp agent to inspect the database and run Better Auth migrations.

### Phase 3: Verification
Test the complete authentication flow to ensure signup, login, and session management work correctly.

## Step by Step Tasks

### 1. Check Auth Service Logs for Detailed Error
- Start the auth service with verbose logging: `cd apps/orchestrator_3_stream/auth-service && npm run dev`
- Make a test signup request to capture the full error stack trace
- Look for database connection errors, missing table errors, or schema issues

### 2. Use neon-mcp Agent to Inspect Database Tables
Spawn the neon-mcp agent to check if Better Auth tables exist:

```
Use the neon-mcp agent with this prompt:
"Use Neon MCP tools to list all tables in the neondb database. Show me the table names to check if Better Auth tables (user, session, account, verification) exist."
```

The agent will use `get_database_tables` to list existing tables.

### 3. Use neon-mcp Agent to Run Better Auth Migration
If tables are missing, use the neon-mcp agent to create them:

```
Use the neon-mcp agent with this prompt:
"Use Neon MCP tools to run this SQL migration on neondb to create Better Auth tables:

-- Better Auth Core Tables for PostgreSQL
CREATE TABLE IF NOT EXISTS \"user\" (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    \"emailVerified\" BOOLEAN NOT NULL DEFAULT FALSE,
    image TEXT,
    \"createdAt\" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    \"updatedAt\" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS session (
    id TEXT PRIMARY KEY,
    \"expiresAt\" TIMESTAMPTZ NOT NULL,
    token TEXT NOT NULL UNIQUE,
    \"createdAt\" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    \"updatedAt\" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    \"ipAddress\" TEXT,
    \"userAgent\" TEXT,
    \"userId\" TEXT NOT NULL REFERENCES \"user\"(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS account (
    id TEXT PRIMARY KEY,
    \"accountId\" TEXT NOT NULL,
    \"providerId\" TEXT NOT NULL,
    \"userId\" TEXT NOT NULL REFERENCES \"user\"(id) ON DELETE CASCADE,
    \"accessToken\" TEXT,
    \"refreshToken\" TEXT,
    \"idToken\" TEXT,
    \"accessTokenExpiresAt\" TIMESTAMPTZ,
    \"refreshTokenExpiresAt\" TIMESTAMPTZ,
    scope TEXT,
    password TEXT,
    \"createdAt\" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    \"updatedAt\" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS verification (
    id TEXT PRIMARY KEY,
    identifier TEXT NOT NULL,
    value TEXT NOT NULL,
    \"expiresAt\" TIMESTAMPTZ NOT NULL,
    \"createdAt\" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    \"updatedAt\" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS session_userId_idx ON session(\"userId\");
CREATE INDEX IF NOT EXISTS account_userId_idx ON account(\"userId\");
"
```

The agent will use `run_sql_transaction` to execute the migration.

### 4. Alternative: Use Better Auth CLI Migration
If you prefer using the Better Auth CLI instead of raw SQL:
- Navigate to auth-service directory: `cd apps/orchestrator_3_stream/auth-service`
- Generate schema: `npx @better-auth/cli generate`
- Run migration: `npx @better-auth/cli migrate`

### 5. Restart Auth Service and Test Signup
- Restart the auth service: `npm run dev`
- Test signup with the prepared credentials:
  - Email: `test-1768857731@example.com`
  - Password: `TestPassword123!`
- Verify the request returns 200 OK and creates a user record

### 6. Use neon-mcp Agent to Verify User Creation
After signup, verify the user was created:

```
Use the neon-mcp agent with this prompt:
"Use Neon MCP tools to run this SQL on neondb: SELECT id, email, name, \"createdAt\" FROM \"user\" LIMIT 10;"
```

### 7. Validate with Playwright (Optional)
- Use Playwright MCP to test the full signup flow in the browser
- Navigate to `http://localhost:5175/signup`
- Fill in the signup form and submit
- Verify successful registration and redirect

## Testing Strategy
1. **Unit Test**: Direct API call to `POST /api/auth/sign-up/email` with curl
2. **Database Verification**: Use neon-mcp agent to query the `user` table
3. **Integration Test**: Full browser flow using Playwright MCP

## Acceptance Criteria
- [ ] Auth service returns 200 OK on valid signup requests
- [ ] User records are created in the `user` table (verify via neon-mcp)
- [ ] Session tokens are generated and stored in the `session` table
- [ ] Account records are created in the `account` table
- [ ] Login works after signup with the same credentials
- [ ] Logout clears the session properly

## Validation Commands

### Using neon-mcp Agent (Preferred)
```
# 1. Verify tables exist
neon-mcp agent prompt: "Use Neon MCP tools to list all tables in neondb and show which Better Auth tables exist."

# 2. Check user table has records
neon-mcp agent prompt: "Use Neon MCP tools to run: SELECT id, email, name FROM \"user\" LIMIT 5;"

# 3. Check session table
neon-mcp agent prompt: "Use Neon MCP tools to run: SELECT id, \"userId\", \"expiresAt\" FROM session LIMIT 5;"
```

### Using curl for API Testing
```bash
# Test signup endpoint
curl -X POST http://localhost:9404/api/auth/sign-up/email \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123!","name":"Test User"}'

# Test login endpoint
curl -X POST http://localhost:9404/api/auth/sign-in/email \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123!"}'
```

## Notes

### neon-mcp Agent Usage
The neon-mcp agent (`.claude/agents/neon-mcp.md`) is a Neon Postgres database management specialist that:
- Spawns a Claude Code subprocess with Neon MCP tools enabled
- Uses the `.mcp.json.neon` configuration file
- Provides natural language interface to Neon database operations
- Supports `run_sql`, `run_sql_transaction`, `get_database_tables`, `describe_table_schema`

### Better Auth CLI Reference
- Documentation: [Better Auth CLI](https://www.better-auth.com/docs/concepts/cli)
- The CLI automatically detects PostgreSQL and creates tables in the correct schema
- For non-default schemas, it uses the `search_path` configuration

### Neon PostgreSQL Considerations
- Connection string uses pooler endpoint (`-pooler.` in hostname) for connection pooling
- SSL is required (`sslmode=require`)
- Neon supports branch-aware authentication for preview environments

### Environment Variables Required
```
DATABASE_URL=postgresql://...@...neon.tech/neondb?sslmode=require
BETTER_AUTH_SECRET=<random-secret>
AUTH_BASE_URL=http://localhost:9404
```

### Dependencies
- better-auth: ^1.4.6
- pg: ^8.11.0
- hono: ^4.0.0
- @hono/node-server: ^1.8.0

### Sources
- [Better Auth PostgreSQL Adapter](https://www.better-auth.com/docs/adapters/postgresql)
- [Better Auth Database Concepts](https://www.better-auth.com/docs/concepts/database)
- [Better Auth CLI](https://www.better-auth.com/docs/concepts/cli)
- [Better Auth Installation](https://www.better-auth.com/docs/installation)

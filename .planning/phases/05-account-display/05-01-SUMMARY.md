---
phase: 05-account-display
plan: 01
subsystem: backend-api
status: complete
tags: [alpaca, account-data, rest-api, pydantic]
requires:
  - 03-credential-management (decrypt-on-demand pattern, credential service)
provides:
  - AccountDataResponse schema
  - fetch_alpaca_account_data service function
  - GET /api/credentials/{id}/account-data endpoint
affects:
  - 05-02 (Frontend service layer will call this endpoint)
  - 05-03 (UI components will consume account data via this endpoint)
tech-stack:
  added: []
  patterns: [decrypt-on-demand, schema-first-api]
key-files:
  created:
    - apps/orchestrator_3_stream/backend/modules/account_service.py
  modified:
    - apps/orchestrator_3_stream/backend/schemas/account_schemas.py
    - apps/orchestrator_3_stream/backend/routers/credentials.py
decisions:
  - id: use-string-types-for-money
    choice: Use string types for balance/equity/buying_power in AccountDataResponse
    rationale: Alpaca returns decimal strings; preserve precision for frontend
  - id: determine-account-type-from-credential
    choice: Read credential_type from database to determine paper vs live routing
    rationale: Credential type is stored during validation (Phase 3); single source of truth
  - id: wrap-sync-alpaca-in-async
    choice: Wrap synchronous TradingClient.get_account() in async function
    rationale: Consistency with codebase async patterns for future refactoring
metrics:
  duration: 1.8min
  completed: 2026-01-31
---

# Phase 05 Plan 01: Account Data Backend Endpoint Summary

**One-liner:** Backend endpoint fetching real-time Alpaca account metrics via decrypt-on-demand pattern

## What Was Built

Created a complete backend endpoint to fetch real-time account data from Alpaca API using stored credentials.

**Three components:**

1. **AccountDataResponse Schema** - Pydantic model for account metrics with string types for monetary values
2. **fetch_alpaca_account_data Service** - Function to call Alpaca /v2/account API and return formatted data
3. **GET /api/credentials/{id}/account-data Endpoint** - REST endpoint using decrypt-on-demand pattern

**Key flow:**
- Frontend requests account data for a credential_id
- Endpoint queries credential_type from database (paper vs live)
- Decrypts credential using get_decrypted_alpaca_credential context manager
- Calls fetch_alpaca_account_data with decrypted keys
- Returns AccountDataResponse with real-time metrics

## How It Works

**Request Flow:**

```
Frontend → GET /api/credentials/{id}/account-data
         ↓
Endpoint authenticates user (get_current_user)
         ↓
Query credential_type from database (paper/live)
         ↓
Decrypt credential (get_decrypted_alpaca_credential)
         ↓
Call Alpaca API (fetch_alpaca_account_data)
         ↓
Return AccountDataResponse
```

**AccountDataResponse Schema:**
- account_type: "paper" or "live"
- balance, equity, buying_power: String types (preserve precision)
- currency: Default "USD"
- trading_blocked, account_blocked: Boolean flags
- pattern_day_trader: Boolean PDT flag
- daytrade_count: Integer count of recent day trades
- last_updated: ISO 8601 timestamp

**Security:**
- Uses decrypt-on-demand pattern (credentials only decrypted during API call)
- RLS enforcement via get_connection_with_rls
- Never logs credential values
- Validates credential ownership and active status

## Implementation Details

**File: schemas/account_schemas.py**
- Added AccountDataResponse with Field descriptions
- String types for monetary values (balance, equity, buying_power)
- Boolean flags for trading restrictions
- ISO 8601 timestamp for last_updated

**File: modules/account_service.py**
- fetch_alpaca_account_data function (async wrapper)
- TradingClient from alpaca-py library
- paper parameter determines endpoint routing
- getattr with defaults for optional fields

**File: routers/credentials.py**
- GET endpoint at /{credential_id}/account-data
- Queries credential_type from database
- Uses get_decrypted_alpaca_credential context manager
- Error handling for inactive/unauthorized credentials
- Returns 400 for inactive, 403 for unauthorized, 500 for API errors

## Testing Notes

**Manual verification:**
- All imports successful
- Endpoint registered in router (verified via routes list)
- Backend config loads without errors

**Next phase testing:**
- Integration tests with real Alpaca credentials (Phase 5 Plan 3 UAT)
- Frontend consumption tests (Phase 5 Plan 2-3)

## Decisions Made

**1. Use String Types for Monetary Values**
- **Context:** Alpaca API returns decimal strings for precision
- **Decision:** Use str for balance/equity/buying_power in schema
- **Rationale:** Preserve decimal precision; frontend can format as needed
- **Alternative considered:** Decimal type (rejected: complex serialization)

**2. Determine Account Type from Credential Database**
- **Context:** Need to route to paper-api vs api.alpaca.markets
- **Decision:** Query credential_type from user_credentials table
- **Rationale:** Single source of truth; credential type stored during validation
- **Alternative considered:** Detect from API key prefix (rejected: fragile)

**3. Wrap Synchronous Alpaca Client in Async Function**
- **Context:** TradingClient.get_account() is synchronous
- **Decision:** Wrap in async def for consistency
- **Rationale:** Matches codebase patterns; enables future async migration
- **Alternative considered:** Use sync function (rejected: inconsistent)

## Deviations from Plan

None - plan executed exactly as written.

## Key Patterns Established

**1. Decrypt-on-Demand for Account Operations**
- Pattern: Use get_decrypted_alpaca_credential context manager
- Benefit: Credentials only decrypted when needed, auto-cleanup
- Applied to: Account data fetching (extensible to trading operations)

**2. Schema-First API Design**
- Pattern: Define Pydantic schema before endpoint implementation
- Benefit: Type safety, auto-generated OpenAPI docs
- Applied to: AccountDataResponse → endpoint → service

**3. Database-Driven API Routing**
- Pattern: Query credential_type from database to determine endpoint
- Benefit: Single source of truth; supports multiple credential types
- Applied to: Paper vs live Alpaca endpoint selection

## Commits

| Hash    | Message                                          |
|---------|--------------------------------------------------|
| 629ad23 | feat(05-01): add AccountDataResponse schema      |
| 1d4638e | feat(05-01): create account service for Alpaca data |
| 2b9625e | feat(05-01): add account-data endpoint to credentials router |

## Next Phase Readiness

**Ready for Phase 05 Plan 02 (Frontend Service Layer):**
- ✅ Backend endpoint available at /api/credentials/{id}/account-data
- ✅ AccountDataResponse schema matches expected frontend interface
- ✅ Error handling for all credential scenarios (inactive, unauthorized)
- ✅ Decimal precision preserved with string types

**No blockers for next plan.**

**Recommendation:** Create TypeScript interface matching AccountDataResponse in frontend types.d.ts

---
phase: 03-credential-management
plan: 01
subsystem: api
tags: [pydantic, securestr, encryption, credential-management, alpaca]

# Dependency graph
requires:
  - phase: 02-database-schema
    provides: UserCredentialORM with EncryptedString TypeDecorator for transparent encryption
  - phase: 01-security-foundation
    provides: Fernet encryption service with singleton pattern
provides:
  - Pydantic request/response schemas with SecretStr for credential API endpoints
  - Credential service with decrypt-on-demand pattern for secure credential access
  - Alpaca credential validation against live API
affects: [03-02, 03-03, credential-api, alpaca-integration]

# Tech tracking
tech-stack:
  added: [pydantic.SecretStr, httpx]
  patterns: [decrypt-on-demand, async context manager for credential access, response schemas without plaintext]

key-files:
  created:
    - apps/orchestrator_3_stream/backend/schemas/credential_schemas.py
    - apps/orchestrator_3_stream/backend/modules/credential_service.py
  modified: []

key-decisions:
  - "Use SecretStr for api_key and secret_key fields to mask values in logs/errors"
  - "CredentialResponse never includes plaintext credentials (metadata only)"
  - "get_decrypted_alpaca_credential is async context manager for auto-cleanup"
  - "validate_alpaca_credentials supports both paper and live Alpaca API endpoints"
  - "store_credential validates account ownership before inserting"

patterns-established:
  - "Decrypt-on-demand: credentials decrypted only when needed, plaintext discarded after use"
  - "Async context manager pattern for secure resource handling with automatic cleanup"
  - "SecretStr masking pattern for sensitive values in API schemas"

# Metrics
duration: 3min
completed: 2026-01-31
---

# Phase 03 Plan 01: Credential Schemas & Service Summary

**Pydantic schemas with SecretStr masking and credential service with decrypt-on-demand async context manager for secure Alpaca credential management**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-31T14:01:04Z
- **Completed:** 2026-01-31T14:04:05Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Pydantic request/response schemas with SecretStr for automatic credential masking
- CredentialResponse excludes plaintext credentials (metadata only)
- Async context manager for decrypt-on-demand credential access
- Alpaca API credential validation with paper/live endpoint support
- Encrypted credential storage with account ownership validation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Pydantic credential schemas** - `c954885` (feat)
2. **Task 2: Create credential service with decrypt-on-demand** - `13436aa` (feat)

## Files Created/Modified
- `apps/orchestrator_3_stream/backend/schemas/__init__.py` - Schemas package initialization
- `apps/orchestrator_3_stream/backend/schemas/credential_schemas.py` - Pydantic schemas with SecretStr for credential API
- `apps/orchestrator_3_stream/backend/modules/credential_service.py` - Credential service with decrypt-on-demand pattern

## Decisions Made

1. **SecretStr for credential fields**: All api_key and secret_key fields use Pydantic's SecretStr type to ensure credentials are masked in string representations, logs, and error messages.

2. **CredentialResponse excludes credentials**: Response schema only includes metadata (id, account_id, credential_type, is_active, timestamps). Clients must use decrypt-on-demand pattern via dedicated endpoints.

3. **Async context manager pattern**: get_decrypted_alpaca_credential is async context manager that yields plaintext credentials and automatically discards them on exit (try/finally pattern).

4. **Dual API endpoint support**: validate_alpaca_credentials supports both paper (paper-api.alpaca.markets) and live (api.alpaca.markets) endpoints via use_paper parameter.

5. **Account ownership validation**: store_credential validates account exists and belongs to user_id before inserting credential to prevent unauthorized credential storage.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation proceeded smoothly with clear requirements from Phase 1 (encryption service) and Phase 2 (ORM models).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 03 Plan 02 (Credential API Endpoints):**
- Pydantic schemas available for FastAPI endpoint validation
- Credential service ready for use in API route handlers
- SecretStr masking ensures credentials never leak in logs
- Decrypt-on-demand pattern provides secure credential access

**Ready for Phase 03 Plan 03 (Integration Tests):**
- All credential operations testable (store, retrieve, validate)
- Async context manager pattern testable with mock database connections
- Validation against Alpaca API testable with test credentials

**No blockers or concerns.**

---
*Phase: 03-credential-management*
*Completed: 2026-01-31*

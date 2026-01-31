# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-29)

**Core value:** Friends can log in, add their own Alpaca accounts, and trade via chat — each person controls their own money.
**Current focus:** Phase 4 - Account Management UI

## Current Position

Phase: 4 of 8 (Account Management UI)
Plan: 1 of 3 in current phase
Status: In progress
Last activity: 2026-01-31 — Completed 04-01-PLAN.md (Backend Account API)

Progress: [█████████░] 83% (10/12 plans total: Phase 1: 3/3, Phase 2: 3/3, Phase 3: 3/3, Phase 4: 1/3)

## Performance Metrics

**Velocity:**
- Total plans completed: 10
- Average duration: 6.8min
- Total execution time: 1.25 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-security-foundation | 3 | 49.5min | 16.5min |
| 02-database-schema | 3 | 7.3min | 2.4min |
| 03-credential-management | 3 | 11.4min | 3.8min |
| 04-account-management-ui | 1 | 2.0min | 2.0min |

**Recent Trend:**
- Last 5 plans: 03-01 (3min), 03-02 (3min), 03-03 (5.4min), 04-01 (2min)
- Trend: Backend API plans are consistently fast (~2-3min), integration plans slower (~5min)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 8 phases derived from 24 requirements, security-first order
- [Roadmap]: CRED requirements front-loaded in Phases 1-3 (foundation before features)
- [Roadmap]: Mobile polish deferred to Phase 8 (functionality before responsiveness)
- [01-01]: Use Fernet (AES-128-CBC with HMAC-SHA256) for symmetric encryption
- [01-01]: Singleton pattern for encryption service to ensure single key instance
- [01-01]: ENCRYPTION_KEY optional at startup (warning), required for credential operations
- [01-01]: Never log credential values (plaintext or ciphertext) - security pattern established
- [01-02]: Dual-layer security: runtime redaction + pre-commit detection
- [01-02]: Apply redaction filter to ALL handlers (console + file) for complete coverage
- [01-02]: Use detect-secrets v1.4.0 for pre-commit secret scanning
- [01-03]: Test Alpaca-specific key formats (PK..., sp...) explicitly in test suite
- [01-03]: Use monkeypatch fixture for test environment isolation
- [01-03]: Test both positive (functionality) and negative (error conditions) cases for security
- [02-01]: Denormalize user_id in user_credentials table to avoid joins in RLS policies
- [02-01]: Use VARCHAR(255) for account_name to support descriptive names
- [02-01]: Add unique constraint on (user_account_id, credential_type) to prevent duplicate credentials per account
- [02-01]: Include optional expires_at field for future credential expiration support
- [02-02]: Use current_user_id() function to retrieve session variable (app.current_user_id)
- [02-02]: FORCE ROW LEVEL SECURITY on both tables for complete policy enforcement including testing
- [02-02]: Mark current_user_id() as STABLE for query planner caching per statement
- [02-02]: Return NULL from current_user_id() if session variable not set (fail-safe behavior)
- [02-03]: Use SQLAlchemy TypeDecorator for transparent encryption (separates encryption from business logic)
- [02-03]: Set EncryptedString cache_ok = True (encryption service is singleton, safe to cache)
- [02-03]: Use monkeypatch fixture for test encryption keys (test isolation, no shared state)
- [03-01]: Use SecretStr for api_key and secret_key fields to mask values in logs/errors
- [03-01]: CredentialResponse never includes plaintext credentials (metadata only)
- [03-01]: get_decrypted_alpaca_credential is async context manager for auto-cleanup
- [03-01]: validate_alpaca_credentials supports both paper and live Alpaca API endpoints
- [03-01]: store_credential validates account ownership before inserting
- [03-02]: set_rls_context uses SET LOCAL for transaction-scoped RLS (auto-cleanup on transaction end)
- [03-02]: get_connection_with_rls is async context manager for convenient RLS-aware queries
- [03-02]: All credential endpoints use get_current_user dependency for authentication enforcement
- [03-02]: Update endpoint only modifies provided fields (partial update pattern)
- [03-02]: Delete endpoint uses hard delete (not soft delete) per plan specification
- [03-03]: Use invoke_with_stored_credential for credential-aware Alpaca API invocations
- [03-03]: Create three test files: endpoints, lifecycle, real integration (separation of concerns)
- [03-03]: Real Alpaca tests use UNIQUE env var names (ALPACA_PAPER1_*) to avoid duplicate key issue
- [03-03]: Real integration tests use 10-second timeout for API calls to prevent hangs
- [03-03]: RLS isolation test creates temporary user and cleans up after (ephemeral testing)
- [04-01]: Get-or-create endpoint pattern for idempotent account initialization
- [04-01]: One account per user enforced by database unique constraint on user_id
- [04-01]: All account endpoints use get_connection_with_rls for RLS enforcement

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: Alpaca token lifecycle not well documented - may need to contact support
- [Research]: PostgreSQL RLS performance unverified at scale - recommend load testing Phase 2

## Session Continuity

Last session: 2026-01-31 15:27:00 UTC
Stopped at: Completed 04-01-PLAN.md (Backend Account API)
Resume file: None

**Phase 1 Complete:** Security foundation established with encryption service, log redaction, pre-commit hooks, and comprehensive test suite.
**Phase 2 Complete:** Database schema with user accounts and credentials tables, RLS policies for user isolation, and SQLAlchemy ORM models with transparent encryption via TypeDecorator pattern.
**Phase 3 Complete:** Credential management with schemas, service, REST endpoints, Alpaca integration, and comprehensive test suite (32 tests including REAL Alpaca API validation).
**Phase 4 In Progress (1/3 complete):** Backend account API with GET /api/accounts, POST /api/accounts, POST /api/accounts/get-or-create endpoints.

---
*State initialized: 2026-01-29*

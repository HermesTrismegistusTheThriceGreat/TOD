---
phase: 02-database-schema
plan: 03
subsystem: database-encryption
tags: [sqlalchemy, encryption, orm, credentials, fernet]
status: complete

dependencies:
  requires:
    - "01-01-PLAN.md (encryption service)"
    - "02-01-PLAN.md (database schema)"
  provides:
    - "SQLAlchemy ORM models with transparent encryption"
    - "EncryptedString TypeDecorator for automatic encrypt/decrypt"
    - "Comprehensive test suite for encrypted credentials"
  affects:
    - "03-01 (User Authentication) - will use UserAccountORM and UserCredentialORM"
    - "Future database operations - transparent encryption pattern established"

tech-stack:
  added:
    - sqlalchemy==2.0.46
  patterns:
    - "TypeDecorator pattern for transparent encryption"
    - "ORM models with encrypted columns"
    - "Relationship cascades for data integrity"

files:
  created:
    - apps/orchestrator_3_stream/backend/modules/user_models.py
    - apps/orchestrator_3_stream/backend/tests/test_user_credentials.py
  modified:
    - apps/orchestrator_3_stream/backend/pyproject.toml

decisions:
  - id: enc-001
    what: "Use SQLAlchemy TypeDecorator for transparent encryption"
    why: "Separates encryption concerns from business logic; automatic encrypt/decrypt"
    alternative: "Manual encryption in each data access layer"
    trade-offs: "TypeDecorator adds SQLAlchemy dependency but provides cleaner API"

  - id: enc-002
    what: "Set EncryptedString cache_ok = True"
    why: "Encryption service is singleton; safe for SQLAlchemy to cache type metadata"
    alternative: "cache_ok = False (slower, unnecessary recompilation)"
    trade-offs: "Assumes encryption service remains singleton"

  - id: enc-003
    what: "Use monkeypatch fixture for test encryption keys"
    why: "Test isolation - each test has its own key, no shared state"
    alternative: "Shared test key in conftest.py"
    trade-offs: "Slightly more verbose tests, but better isolation"

metrics:
  duration: "3.3min"
  tasks_completed: 2
  tests_added: 14
  test_coverage: "EncryptedString TypeDecorator, ORM models, Alpaca formats, edge cases"
  completed: 2026-01-30
---

# Phase 2 Plan 3: ORM Models with Encryption Summary

**One-liner:** SQLAlchemy ORM models with EncryptedString TypeDecorator for transparent Fernet encryption of Alpaca credentials

## What Was Built

### Core Components

**1. EncryptedString TypeDecorator**
- SQLAlchemy custom type for transparent encryption/decryption
- `process_bind_param()`: Encrypts plaintext on INSERT/UPDATE
- `process_result_value()`: Decrypts ciphertext on SELECT
- Integrates with Phase 1's encryption service via `get_encryption_service()`
- Handles None values, empty strings gracefully

**2. UserAccountORM Model**
- Maps to `user_accounts` table from Plan 01
- Fields: id, user_id, account_name, is_active, timestamps
- One-to-many relationship with UserCredentialORM
- Cascade delete ensures credentials removed with account

**3. UserCredentialORM Model**
- Maps to `user_credentials` table from Plan 01
- Fields: id, user_account_id, user_id, credential_type, api_key, secret_key, is_active, expires_at, timestamps
- **api_key and secret_key columns use EncryptedString** - automatic encryption
- Many-to-one relationship back to UserAccountORM
- Denormalized user_id for RLS performance (from Plan 01 decision)

### Test Coverage

**Test Suite: test_user_credentials.py (14 tests, 1 skipped)**

Coverage includes:
- EncryptedString round-trip encryption (encrypt → decrypt → original)
- None value handling (passes through without encryption)
- Empty string handling (returns empty, no encryption)
- Encrypted value differs from plaintext (security verification)
- Multiple encryptions produce different ciphertext (IV randomization)
- Alpaca API key format (PK...) round-trip
- Alpaca secret key format (sp...) round-trip
- Integration with encryption service singleton
- ORM model column type verification
- ORM relationship verification
- Edge cases: very long credentials, newlines, unicode characters

**Test Results:**
```
14 passed, 1 skipped in 0.14s
```
Skipped test: `test_credential_stored_encrypted_in_db` (database integration placeholder)

## How It Works

### Encryption Flow

**INSERT/UPDATE (process_bind_param):**
```python
user_credential = UserCredentialORM(
    api_key="PKABCDEF1234...",  # Plaintext in code
    secret_key="sp123abc..."     # Plaintext in code
)
session.add(user_credential)
session.commit()
# → EncryptedString.process_bind_param() called
# → get_encryption_service().encrypt() called
# → Ciphertext stored in database: "gAAAAABf..."
```

**SELECT (process_result_value):**
```python
credential = session.query(UserCredentialORM).first()
print(credential.api_key)  # "PKABCDEF1234..." (decrypted)
# → EncryptedString.process_result_value() called
# → get_encryption_service().decrypt() called
# → Plaintext returned to application
```

**Database stores:** `"gAAAAABf..."` (encrypted)
**Application sees:** `"PKABCDEF1234..."` (plaintext)

### Security Properties

1. **Encryption at rest**: Credentials never stored plaintext in database
2. **Transparent to application**: Business logic works with plaintext, encryption automatic
3. **Uses Phase 1 encryption service**: Single encryption key from `ENCRYPTION_KEY` env var
4. **Fernet encryption**: AES-128-CBC with HMAC-SHA256 (authenticated encryption)
5. **IV randomization**: Same plaintext encrypts to different ciphertext each time

## Integration Points

### With Phase 1 (Security Foundation)
- **encryption_service.py**: EncryptedString calls `get_encryption_service()` for encrypt/decrypt
- **Singleton pattern**: Ensures single encryption key instance across all TypeDecorator instances
- **Error handling**: InvalidToken exceptions propagate from encryption service

### With Plan 01 (Database Schema)
- **ORM models match schema**: UserAccountORM and UserCredentialORM map to tables created in Plan 01
- **Indexes preserved**: ORM models include Index() declarations matching Plan 01
- **Denormalization honored**: user_id in UserCredentialORM (from Plan 01 RLS decision)

### With Future Plans
- **Phase 3 (User Authentication)**: Will query UserCredentialORM to fetch Alpaca credentials for authentication
- **Transparent encryption**: Authentication code works with plaintext, no encryption logic needed
- **Pattern established**: Future credential types (Polygon, etc.) can use same EncryptedString pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added SQLAlchemy dependency**
- **Found during:** Task 1 - attempting to import user_models.py
- **Issue:** `ModuleNotFoundError: No module named 'sqlalchemy'` - SQLAlchemy not in dependencies
- **Fix:** Added `sqlalchemy>=2.0.0` to pyproject.toml, ran `uv sync`
- **Files modified:** pyproject.toml, uv.lock
- **Commit:** fb22f46 (included in Task 1 commit)
- **Rationale:** Cannot create ORM models without SQLAlchemy (blocking issue)

**2. [Rule 1 - Bug] Fixed missing sys.path in test file**
- **Found during:** Task 2 - running pytest on test_user_credentials.py
- **Issue:** `ModuleNotFoundError: No module named 'modules'` - tests couldn't import from modules/
- **Fix:** Added sys.path.insert() at top of test file (pattern from existing test_encryption_service.py)
- **Files modified:** test_user_credentials.py
- **Commit:** 8a2388c (included in Task 2 commit)
- **Rationale:** Tests must be able to import modules to run (bug in test setup)

## Key Learnings

### TypeDecorator Benefits
- **Separation of concerns**: Encryption logic isolated from business logic
- **DRY principle**: Single EncryptedString class used for all encrypted columns
- **Testability**: TypeDecorator methods tested independently of database

### Test Isolation
- **monkeypatch fixture**: Each test gets fresh ENCRYPTION_KEY, no shared state
- **No database required**: Most tests verify encryption logic without database connection
- **Alpaca format testing**: Explicit tests for PK... and sp... formats ensure real-world compatibility

### Future Considerations
- **Column length**: EncryptedString(500) chosen to accommodate encrypted output (~1.5x plaintext + signature)
- **Database integration test**: Placeholder exists for future raw SQL verification
- **Performance**: TypeDecorator adds minimal overhead (encryption service cached as singleton)

## Testing Instructions

**Run all tests:**
```bash
cd apps/orchestrator_3_stream/backend
uv run pytest tests/test_user_credentials.py -v
```

**Expected output:**
```
14 passed, 1 skipped in 0.14s
```

**Test with real encryption key:**
```bash
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
uv run pytest tests/test_user_credentials.py -v
```

**Import verification:**
```bash
uv run python -c "from modules.user_models import EncryptedString, UserAccountORM, UserCredentialORM; print('OK')"
```

## Next Phase Readiness

**Phase 3 (User Authentication) can proceed:**
- ✅ ORM models available for credential storage
- ✅ Transparent encryption working and tested
- ✅ Alpaca credential formats verified
- ✅ Relationships between accounts and credentials established

**No blockers or concerns for next phase.**

**Recommendations:**
1. When implementing Phase 3 authentication, use UserCredentialORM directly - no encryption logic needed
2. Consider adding database integration test once database setup is standardized
3. Monitor TypeDecorator performance in production (should be negligible with singleton service)

## Files Modified

### Created
- `apps/orchestrator_3_stream/backend/modules/user_models.py` (260 lines)
  - EncryptedString TypeDecorator
  - UserAccountORM model
  - UserCredentialORM model

- `apps/orchestrator_3_stream/backend/tests/test_user_credentials.py` (346 lines)
  - 14 comprehensive tests
  - 6 test classes
  - Covers TypeDecorator, Alpaca formats, ORM integration, edge cases

### Modified
- `apps/orchestrator_3_stream/backend/pyproject.toml`
  - Added: sqlalchemy>=2.0.0

- `apps/orchestrator_3_stream/backend/uv.lock`
  - Updated: installed sqlalchemy==2.0.46

## Commit History

| Task | Commit  | Message                                           | Files                                         |
| ---- | ------- | ------------------------------------------------- | --------------------------------------------- |
| 1    | fb22f46 | feat(02-03): create SQLAlchemy ORM models         | user_models.py, pyproject.toml, uv.lock       |
| 2    | 8a2388c | test(02-03): add comprehensive tests              | test_user_credentials.py                      |

**Total duration:** 3.3 minutes
**Total tests:** 14 passing, 1 skipped
**Total lines added:** 606 lines (260 production + 346 test)

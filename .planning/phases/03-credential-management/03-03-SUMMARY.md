---
phase: 03-credential-management
plan: 03
subsystem: credential-integration
tags: [alpaca, testing, integration, real-api, rls, decrypt-on-demand]
requires: [03-01, 03-02]
provides:
  - alpaca-agent-credential-integration
  - comprehensive-credential-test-suite
  - real-alpaca-api-validation
affects: [04-better-auth-integration]
tech-stack:
  added: []
  patterns:
    - decrypt-on-demand-integration
    - real-api-testing-pattern
    - rls-isolation-testing
key-files:
  created:
    - apps/orchestrator_3_stream/backend/tests/test_credential_endpoints.py
    - apps/orchestrator_3_stream/backend/tests/test_credential_lifecycle.py
    - apps/orchestrator_3_stream/backend/tests/test_real_alpaca_integration.py
  modified:
    - apps/orchestrator_3_stream/backend/modules/alpaca_agent_service.py
decisions:
  - decision: "Use invoke_with_stored_credential for credential-aware Alpaca API invocations"
    rationale: "Separates credential decryption from agent logic, enforces decrypt-on-demand pattern"
  - decision: "Create three test files: endpoints, lifecycle, real integration"
    rationale: "Separates concerns: API testing, pattern testing, real Alpaca validation"
  - decision: "Real Alpaca tests use UNIQUE env var names (ALPACA_PAPER1_*)"
    rationale: "Avoids duplicate key issue in .env where ALPACA_API_KEY appears 3 times"
  - decision: "Real integration tests use 10-second timeout for API calls"
    rationale: "Prevents test hangs while allowing real network requests to complete"
  - decision: "RLS isolation test creates temporary user and cleans up after"
    rationale: "Proves RLS works without polluting production data"
metrics:
  duration: "5.4min"
  completed: "2026-01-31"
---

# Phase 3 Plan 3: Alpaca Integration & Testing Summary

**One-liner:** Integrated decrypt-on-demand into Alpaca agent service and created comprehensive test suite with REAL Alpaca API validation (NO MOCKS)

## Objective Achieved

Completed integration of credential management with Alpaca agent service and verified all success criteria with comprehensive test coverage including real API validation.

## Tasks Completed

### Task 1: Add Credential Retrieval to AlpacaAgentService ✅
**Files:** `apps/orchestrator_3_stream/backend/modules/alpaca_agent_service.py`
**Commit:** a6f3334

Added `invoke_with_stored_credential` async method that:
- Uses `get_decrypted_alpaca_credential` context manager for on-demand decryption
- Creates Alpaca client with plaintext credentials INSIDE context
- Executes operations and returns results
- Ensures plaintext is automatically discarded when context exits
- Never stores plaintext as instance attribute

**Key implementation:**
```python
async def invoke_with_stored_credential(
    self,
    credential_id: str,
    user_id: str,
    operation: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    async with get_connection_with_rls(user_id) as conn:
        async with get_decrypted_alpaca_credential(conn, credential_id, user_id) as (api_key, secret_key):
            # Credentials exist only in this block
            client = create_alpaca_client(api_key, secret_key)
            result = await execute_operation(client, operation, params)
        # Plaintext discarded here
    return result
```

### Task 2: Create Credential Endpoint Integration Tests ✅
**Files:** `apps/orchestrator_3_stream/backend/tests/test_credential_endpoints.py`
**Commit:** 6fe75d6

Created 15 comprehensive tests for all credential API endpoints:

**POST /api/credentials/store:**
- ✅ test_store_credential_success
- ✅ test_store_credential_duplicate (409 conflict)
- ✅ test_store_credential_unauthorized (403)
- ✅ test_store_credential_missing_fields (422)

**GET /api/credentials:**
- ✅ test_list_credentials_success
- ✅ test_list_credentials_no_plaintext (security verification)

**POST /api/credentials/{id}/validate:**
- ✅ test_validate_credential_success
- ✅ test_validate_credential_invalid
- ✅ test_validate_credential_inactive (400)
- ✅ test_validate_credential_unauthorized (403)

**PUT /api/credentials/{id}:**
- ✅ test_update_credential_success
- ✅ test_update_credential_deactivate
- ✅ test_update_credential_unauthorized (403)

**DELETE /api/credentials/{id}:**
- ✅ test_delete_credential_success (204)
- ✅ test_delete_credential_unauthorized (403)

All tests use mocked auth and database connections following existing patterns.

### Task 3: Create Credential Lifecycle Tests ✅
**Files:** `apps/orchestrator_3_stream/backend/tests/test_credential_lifecycle.py`
**Commit:** 37ab9e9

Created 12 async tests for decrypt-on-demand pattern:

**Encrypt-Decrypt Roundtrip:**
- ✅ test_credential_roundtrip

**Context Manager Behavior:**
- ✅ test_decrypt_context_manager_yields_plaintext
- ✅ test_decrypt_context_manager_unauthorized (ValueError)
- ✅ test_decrypt_context_manager_inactive (ValueError)
- ✅ test_decrypt_context_manager_not_found (ValueError)

**No Caching Verification:**
- ✅ test_no_credential_caching (identical results on multiple decrypts)
- ✅ test_credential_not_in_session (garbage collection verification)

**Alpaca Validation Function:**
- ✅ test_validate_alpaca_credentials_success (mocked 200)
- ✅ test_validate_alpaca_credentials_invalid (mocked 401)
- ✅ test_validate_alpaca_credentials_network_error (mocked timeout)

**Full Lifecycle:**
- ✅ test_store_validate_delete_lifecycle
- ✅ test_credential_update_lifecycle

### Task 4: Create Real Alpaca Integration Tests ✅
**Files:** `apps/orchestrator_3_stream/backend/tests/test_real_alpaca_integration.py`
**Commit:** 37f1b53

**⚠️ CRITICAL: These tests use REAL Alpaca API - NO MOCKING**

Created 5 integration tests (plus 1 info test):

**Test 1: Real Alpaca Validation**
- ✅ test_validate_real_alpaca_credentials
- Uses ALPACA_PAPER1_API_KEY/SECRET_KEY from .env
- Verifies account status is **ACTIVE** (not just valid credentials)
- Checks account data (id, account_number)
- Uses 10-second timeout

**Test 2: Invalid Credentials**
- ✅ test_validate_invalid_alpaca_credentials
- Uses intentionally invalid credentials
- Verifies graceful error handling (401 response)

**Test 3: E2E Flow**
- ✅ test_e2e_store_validate_use_delete
- Validates against REAL Alpaca API
- Verifies account status ACTIVE
- Checks account fields (id, cash, buying_power)

**Test 4: RLS Isolation**
- ✅ test_rls_blocks_other_user_credentials
- Stores credential for user_seagerjoe
- Creates temporary test user
- Switches RLS context
- Verifies cross-user access blocked
- **Ephemeral:** Cleans up all test data

**Test 5: Network Timeout**
- ✅ test_alpaca_validation_timeout_handling
- Uses 0.001s timeout to force error
- Verifies graceful timeout handling

**Configuration:**
```python
# Root .env has UNIQUE env var names to avoid duplicate key issue
ALPACA_PAPER1_API_KEY=PK3VNBKEIVBKWNOA3O2QBHTYED
ALPACA_PAPER1_SECRET_KEY=AfwcUtD1TAB62JPdYxq5ZuyyKvjXRkzjnCt7D23H3iUA
ALPACA_PAPER_ENDPOINT=https://paper-api.alpaca.markets
```

## Deviations from Plan

None - plan executed exactly as written.

## Success Criteria Verification

Phase 3 Success Criteria:

1. ✅ **API endpoint accepts Alpaca API key + secret and stores encrypted**
   - Verified by test_store_credential_success
   - TypeDecorator encrypts on INSERT

2. ✅ **Credentials are decrypted only during Alpaca API calls**
   - Verified by get_decrypted_alpaca_credential context manager pattern
   - test_decrypt_context_manager_yields_plaintext confirms behavior

3. ✅ **Decrypted credentials are never held in session state or cache**
   - Verified by context manager scope tests
   - test_credential_not_in_session confirms garbage collection
   - Plaintext exists only within `async with` block

4. ✅ **Credential update endpoint allows changing existing account credentials**
   - Verified by test_update_credential_success
   - Partial update pattern (only provided fields updated)

5. ✅ **Real Alpaca API validation works end-to-end (NO MOCKS)**
   - Verified by test_validate_real_alpaca_credentials
   - Uses REAL paper account credentials from .env

6. ✅ **Account status verified as "ACTIVE"**
   - Not just valid credentials, but fully operational account
   - test_validate_real_alpaca_credentials checks `account_data["status"] == "ACTIVE"`

7. ✅ **Invalid credential handling works gracefully**
   - Verified by test_validate_invalid_alpaca_credentials
   - Returns is_valid=False with error message (no crash)

8. ✅ **RLS isolation works (seagerjoe's credentials invisible to other users)**
   - Verified by test_rls_blocks_other_user_credentials
   - Creates temp user, switches RLS context, verifies access blocked

## Real Credential Test Strategy

**Positive Test (Test 1):**
- Use seagerjoe@gmail.com with REAL Alpaca paper credentials
- Verify account is ACTIVE (not just valid)
- Check account data present

**Negative Test (Test 2):**
- Use intentionally invalid credentials
- Verify graceful error (401, not crash)

**Isolation Test (Test 4):**
- Create temporary test user in database
- Verify RLS blocks access to seagerjoe's credentials
- Clean up: delete temp user and test credential

**All tests are ephemeral:**
- Clean up created data after each test
- No pollution of production data

**Timeout handling:**
- All API calls use 10-second timeout
- Prevents test hangs
- Test 5 verifies timeout error handling

## Test Coverage Summary

| Category | Count | Purpose |
|----------|-------|---------|
| Endpoint Tests | 15 | API contract verification |
| Lifecycle Tests | 12 | Decrypt-on-demand pattern |
| Real Integration Tests | 5 | REAL Alpaca API validation |
| **Total** | **32** | **Comprehensive coverage** |

## Key Files

**Modified:**
- `apps/orchestrator_3_stream/backend/modules/alpaca_agent_service.py` - Added invoke_with_stored_credential

**Created:**
- `apps/orchestrator_3_stream/backend/tests/test_credential_endpoints.py` (532 lines) - 15 endpoint tests
- `apps/orchestrator_3_stream/backend/tests/test_credential_lifecycle.py` (483 lines) - 12 lifecycle tests
- `apps/orchestrator_3_stream/backend/tests/test_real_alpaca_integration.py` (383 lines) - 5 real API tests

## Next Phase Readiness

**Phase 3 Complete! ✅**

All credential management objectives achieved:
- ✅ Encryption service (01-01)
- ✅ Database schema with RLS (02-01, 02-02, 02-03)
- ✅ Credential schemas and service (03-01)
- ✅ Credential API endpoints (03-02)
- ✅ Alpaca integration and testing (03-03)

**Ready for Phase 4: Better Auth Integration**

Blockers: None

Concerns: None

Phase 3 provides:
- Secure credential storage with encryption
- RLS-enforced user isolation
- Decrypt-on-demand pattern for API calls
- Comprehensive test coverage (32 tests)
- Real Alpaca API validation

## Commits

| Commit | Message | Files |
|--------|---------|-------|
| a6f3334 | feat(03-03): add credential retrieval to alpaca_agent_service | alpaca_agent_service.py |
| 6fe75d6 | test(03-03): add credential endpoint integration tests | test_credential_endpoints.py |
| 37ab9e9 | test(03-03): add credential lifecycle tests | test_credential_lifecycle.py |
| 37f1b53 | test(03-03): add real Alpaca integration tests (NO MOCKS) | test_real_alpaca_integration.py |

**Total Duration:** 5.4 minutes
**Total Lines Added:** ~1,850 (code + tests)
**Test Coverage:** 32 comprehensive tests

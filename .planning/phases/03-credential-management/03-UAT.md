---
status: testing
phase: 03-credential-management
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md]
started: 2026-01-31T14:30:00Z
updated: 2026-01-31T14:30:00Z
---

## Current Test

number: 2
name: List Credentials Returns Metadata Only
expected: |
  GET /api/credentials returns list of credentials with metadata
  (id, account_id, credential_type, is_active, timestamps) but NO
  plaintext API keys or secrets visible in response.
awaiting: user response

## Tests

### 1. Store Alpaca Credentials via API
expected: POST to /api/credentials/store with valid Alpaca API key and secret returns 201 Created. Credentials are stored encrypted in database.
result: skipped

### 2. List Credentials Returns Metadata Only
expected: GET /api/credentials returns list of credentials with metadata (id, account_id, credential_type, is_active, timestamps) but NO plaintext API keys or secrets visible in response.
result: [pending]

### 3. Validate Credentials Against Alpaca API
expected: POST /api/credentials/{id}/validate decrypts credentials, calls real Alpaca API, returns validation result with account status (ACTIVE/INACTIVE).
result: [pending]

### 4. Update Existing Credential
expected: PUT /api/credentials/{id} allows updating API key or secret (partial update). Returns 200 OK with updated metadata.
result: [pending]

### 5. Delete Credential
expected: DELETE /api/credentials/{id} removes credential from database. Returns 204 No Content.
result: [pending]

### 6. RLS Isolation - Cannot Access Other User's Credentials
expected: When authenticated as User A, attempting to list/validate/update/delete User B's credentials returns 403 Forbidden or empty results.
result: [pending]

### 7. Decrypt-on-Demand Pattern Works
expected: Credentials are decrypted only when validate or trade operation is called. Plaintext is never cached or held in session state.
result: [pending]

### 8. Invalid Credentials Handled Gracefully
expected: Storing invalid Alpaca credentials and validating returns is_valid=false with error message (no server crash or exception leak).
result: [pending]

## Summary

total: 8
passed: 0
issues: 0
pending: 7
skipped: 1

## Gaps

[none yet]

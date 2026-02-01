---
phase: 06-trading-context
plan: 01
subsystem: backend-api
tags: [credential-context, rls, chat-endpoint, alpaca-agent]

dependencies:
  requires:
    - 03-credential-management # get_decrypted_alpaca_credential, get_connection_with_rls
    - 05.1-multiple-credentials-support # credential_id support
  provides:
    - credential-aware-chat-endpoint
    - invoke_agent_streaming_with_credential-method
  affects:
    - 06-02 # positions endpoint
    - 06-03 # orders endpoint

tech-stack:
  added: []
  patterns:
    - decrypt-on-demand # credentials decrypted only within scoped context
    - rls-validation # ownership validated via PostgreSQL RLS
    - credential-injection # credentials passed to MCP server configuration

files:
  created: []
  modified:
    - apps/orchestrator_3_stream/backend/modules/alpaca_agent_models.py
    - apps/orchestrator_3_stream/backend/modules/alpaca_agent_service.py
    - apps/orchestrator_3_stream/backend/main.py

decisions:
  - id: credential_id_required
    choice: "credential_id is required field (no default)"
    reason: "Every chat request MUST specify which credential to use - prevents accidental global credential usage"
  - id: temp_auth_header
    choice: "X-User-ID header for temporary auth"
    reason: "Placeholder until proper auth middleware integrated - TODO marked in code"
  - id: paper_trade_default
    choice: "paper_trade defaults to True"
    reason: "Safety first - explicit opt-in required for live trading in future"

metrics:
  duration: 3.7min
  completed: 2026-02-01
---

# Phase 06 Plan 01: Chat Endpoint Credential Context Summary

**One-liner:** Chat endpoint now requires credential_id, validates ownership via RLS, and passes decrypted credentials to agent invocation.

## What Was Built

### Task 1: AlpacaAgentChatRequest credential_id Field
- Added UUID import for validation
- Added required `credential_id` field with description
- Added `@field_validator` to ensure credential_id is valid UUID format
- Updated docstring to document new attribute

### Task 2: invoke_agent_streaming_with_credential Method
- Added new method that accepts `api_key` and `secret_key` directly
- Builds agent options with provided credentials (not from environment)
- Passes credentials to MCP server configuration
- Same SSE streaming logic as existing `invoke_agent_streaming`
- Does NOT call `verify_mcp_config()` since credentials are explicitly provided

### Task 3: Chat Endpoint RLS + Credential Validation
- Added imports for `get_connection_with_rls` and `get_decrypted_alpaca_credential`
- Chat endpoint now accepts `credential_id` from request body
- Validates credential ownership via RLS before any operation
- Decrypts credentials on-demand within scoped context (auto-cleanup)
- Uses `invoke_agent_streaming_with_credential` for agent invocation
- Returns 403 when credential validation fails (not found, not owned, inactive)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 1755da4 | Add credential_id field to AlpacaAgentChatRequest |
| 2 | 53e8699 | Add invoke_agent_streaming_with_credential method |
| 3 | e3061ec | Modify chat endpoint to validate credential and use RLS |

## Key Files Modified

| File | Change |
|------|--------|
| `modules/alpaca_agent_models.py` | Added credential_id field with UUID validation |
| `modules/alpaca_agent_service.py` | Added invoke_agent_streaming_with_credential method |
| `main.py` | Modified chat endpoint to require credential_id and validate via RLS |

## Security Patterns Established

1. **Decrypt-on-Demand:** Credentials exist only within async context manager scope
2. **RLS Validation:** Ownership validated via PostgreSQL RLS before decryption
3. **Credential Injection:** Credentials passed directly to MCP server, not from environment
4. **Automatic Cleanup:** Plaintext discarded when context exits (try/finally pattern)

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Plan 06-02 (Positions Endpoint) can proceed:
- RLS and credential validation patterns established
- `get_connection_with_rls` and `get_decrypted_alpaca_credential` imports available
- Pattern for credential-aware endpoints demonstrated

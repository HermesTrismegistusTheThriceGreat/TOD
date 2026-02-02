# Handoff: Credential Switch Bug - Debug Testing

**Created:** 2026-02-01
**Status:** Ready for testing
**Priority:** HIGH

## Context

When a user switches their active Alpaca account in the UI, the chat agent continues using the **old account's credentials**. The Active Account panel correctly shows the new account's balance, but chat queries return data from the previously selected account.

### Evidence from User Testing
- Before switch: Active Account shows $547,910.40 balance, chat returns Account ID `4c1f9d67-...`
- After switch: Active Account shows $31,056.93 balance, but chat STILL returns old Account ID

### Root Cause Hypothesis
The MCP server subprocess (spawned by Claude SDK) may persist across requests with stale credentials, even though a new `ClaudeSDKClient` is created per request.

## Debug Instrumentation Added

### 1. Backend: `apps/orchestrator_3_stream/backend/modules/alpaca_agent_service.py`

Added logging to `invoke_agent_streaming_with_credential()` method:
- Unique `request_id` per request (8-char UUID)
- `api_key_fingerprint` (last 4 chars of API key - safe to log)
- Client object IDs to verify new instances
- MCP subprocess lifecycle events

### 2. Backend: `apps/orchestrator_3_stream/backend/main.py`

Added `api_key_fingerprint` logging to chat endpoint credential validation.

### 3. Frontend: `apps/orchestrator_3_stream/frontend/src/components/AlpacaAgentChat.vue`

Added console.log for `credential_id` being sent with each request.

### 4. Test Script: `apps/orchestrator_3_stream/backend/tmp_scripts/test_credential_switch.py`

Standalone script to test credential switching without UI.

## Testing Instructions

### Prerequisites

1. Two different Alpaca paper trading accounts with credentials
2. Backend and frontend running locally
3. Access to backend logs (terminal or log files)

### Option A: Manual UI Testing

#### Step 1: Start the Application

```bash
# Terminal 1: Backend
cd apps/orchestrator_3_stream/backend
uv run uvicorn main:app --port 9403 --reload

# Terminal 2: Frontend
cd apps/orchestrator_3_stream/frontend
npm run dev
```

#### Step 2: Set Up Test Accounts

1. Open http://localhost:5175/alpaca-agent
2. Ensure you have **two different Alpaca credentials** added to your account
3. Note the last 4 characters of each API key (for log matching)

#### Step 3: First Request (Credential A)

1. Select first credential from dropdown
2. Send message: "What is my account ID?"
3. Note the Account ID in response
4. Check backend logs for:
   ```
   [ALPACA AGENT SERVICE] [xxxxxxxx] NEW REQUEST - api_key_fingerprint=...AAAA
   [ALPACA AGENT SERVICE] [xxxxxxxx] Client STARTED with api_key_fingerprint=...AAAA
   [ALPACA AGENT SERVICE] [xxxxxxxx] Client CLOSED successfully
   ```

#### Step 4: Second Request (Credential B)

1. **Switch to second credential** in dropdown
2. Wait for Active Account panel to update (shows different balance)
3. Send message: "What is my account ID?"
4. Note the Account ID in response
5. Check backend logs for:
   ```
   [ALPACA AGENT SERVICE] [yyyyyyyy] NEW REQUEST - api_key_fingerprint=...BBBB
   ```

#### Step 5: Compare Results

| Check | Expected | Bug Present |
|-------|----------|-------------|
| Request IDs different | `xxxxxxxx` ≠ `yyyyyyyy` | N/A (always different) |
| API key fingerprints different | `...AAAA` ≠ `...BBBB` | Same fingerprint |
| Account IDs different | Different UUIDs | Same UUID |
| "Client CLOSED" between requests | Present | Missing |

### Option B: Automated Script Testing

#### Step 1: Set Environment Variables

```bash
export ALPACA_PAPER1_API_KEY="PK..."      # First account API key
export ALPACA_PAPER1_SECRET_KEY="..."     # First account secret
export ALPACA_PAPER2_API_KEY="PK..."      # Second account API key
export ALPACA_PAPER2_SECRET_KEY="..."     # Second account secret
export ANTHROPIC_API_KEY="sk-ant-..."     # Claude API key
```

#### Step 2: Run Test Script

```bash
cd apps/orchestrator_3_stream/backend
uv run python tmp_scripts/test_credential_switch.py
```

#### Step 3: Interpret Results

- `✅ TEST PASSED`: Credential switching works correctly
- `❌ TEST FAILED`: Bug confirmed - same Account ID returned for both credentials
- `⚠️ INCONCLUSIVE`: Could not extract Account IDs from responses

### Option C: Browser DevTools Testing

1. Open browser DevTools → Console
2. Switch credentials and send chat
3. Look for: `[AlpacaAgentChat] Sending request with credential_id: <uuid>`
4. Verify the `credential_id` changes when you switch accounts

## Log Patterns to Look For

### Healthy Flow (Bug NOT Present)
```
[ALPACA AGENT] Received chat request with credential_id: abc-123
[ALPACA AGENT] Credential validated, api_key_fingerprint=...WXYZ
[ALPACA AGENT SERVICE] [req1] NEW REQUEST - api_key_fingerprint=...WXYZ
[ALPACA AGENT SERVICE] [req1] Client STARTED
[ALPACA AGENT SERVICE] [req1] Streaming completed
[ALPACA AGENT SERVICE] [req1] Client CLOSED successfully

# User switches account...

[ALPACA AGENT] Received chat request with credential_id: def-456  ← DIFFERENT
[ALPACA AGENT] Credential validated, api_key_fingerprint=...QRST  ← DIFFERENT
[ALPACA AGENT SERVICE] [req2] NEW REQUEST - api_key_fingerprint=...QRST
[ALPACA AGENT SERVICE] [req2] Client STARTED
[ALPACA AGENT SERVICE] [req2] Streaming completed
[ALPACA AGENT SERVICE] [req2] Client CLOSED successfully
```

### Bug Present - Frontend Issue
```
[ALPACA AGENT] Received chat request with credential_id: abc-123
[ALPACA AGENT] Received chat request with credential_id: abc-123  ← SAME (frontend not updating)
```

### Bug Present - Backend/SDK Issue
```
[ALPACA AGENT] Received chat request with credential_id: def-456  ← DIFFERENT (good)
[ALPACA AGENT] Credential validated, api_key_fingerprint=...QRST  ← DIFFERENT (good)
[ALPACA AGENT SERVICE] [req2] NEW REQUEST - api_key_fingerprint=...QRST  ← DIFFERENT (good)
# But response still shows old Account ID (MCP subprocess caching)
```

### Bug Present - Client Not Closing
```
[ALPACA AGENT SERVICE] [req1] Client STARTED
[ALPACA AGENT SERVICE] [req1] Streaming completed
# Missing: "Client CLOSED successfully"
[ALPACA AGENT SERVICE] [req2] Client STARTED
```

## Decision Tree After Testing

### If `credential_id` is the same in both requests:
**Root cause:** Frontend not updating `activeCredentialId`
**Fix location:** `AlpacaAgentChat.vue` or `accountStore.ts`
**Action:** Check Vue reactivity, ensure `accountStore.activeCredentialId` updates

### If `api_key_fingerprint` is the same despite different `credential_id`:
**Root cause:** Credential lookup returning cached/wrong credential
**Fix location:** `credential_service.py` or `main.py`
**Action:** Check database query, verify RLS context

### If fingerprints differ but Account ID in response is same:
**Root cause:** MCP subprocess not being terminated between requests
**Fix location:** `alpaca_agent_service.py`
**Action:** Add explicit subprocess termination, verify `__aexit__` is called

### If "Client CLOSED" is missing:
**Root cause:** Generator not completing, `finally` block not reached
**Fix location:** `alpaca_agent_service.py`
**Action:** Investigate async generator lifecycle, ensure cleanup runs

## Files Modified for Debugging

| File | Changes |
|------|---------|
| `backend/modules/alpaca_agent_service.py` | Added request_id, fingerprint logging, lifecycle logging |
| `backend/main.py` | Added api_key_fingerprint logging to endpoint |
| `frontend/src/components/AlpacaAgentChat.vue` | Added console.log for credential_id |
| `backend/tmp_scripts/test_credential_switch.py` | New test script |

## Reporting Results

After testing, update this document with:

1. **Test Date/Time:**
2. **Test Method Used:** (UI / Script / DevTools)
3. **Findings:**
   - credential_id same or different?
   - api_key_fingerprint same or different?
   - Account ID same or different?
   - "Client CLOSED" present?
4. **Root Cause Identified:**
5. **Recommended Fix:**

---

*Handoff created by: Claude Code session 2026-02-01*

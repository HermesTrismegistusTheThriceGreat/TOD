# TODO: Chat Agent Doesn't Update Credentials on Account Switch

**Created:** 2026-02-01
**Priority:** HIGH (blocks multi-account usability)
**Phase:** 6 - Trading Context (follow-up)

## Problem

When a user switches their active Alpaca account (via the credential selector), the **chat agent continues using the old account's credentials**. The Active Account panel correctly updates to show the new account's data, but chat queries still return data from the previously selected account.

## Evidence

Screenshots show:
1. **Before switch**: Active Account shows $547,910.40 balance, chat returns matching Account ID `4c1f9d67-56b3-4bea-b023-037366b52a3a`
2. **After switch**: Active Account shows $31,056.93 balance (different account), but chat STILL returns Account ID `4c1f9d67-56b3-4bea-b023-037366b52a3a` with $547,910.40

The MCP server tools work correctly (`mcp__alpaca__get_account_info` executes successfully), but they're using stale credentials.

## Root Cause Hypotheses

1. **Frontend not sending updated credential_id** - The chat component may not be reactive to `activeCredentialId` changes
2. **MCP server subprocess caching** - The Claude SDK client's MCP server subprocess may persist across requests
3. **Backend credential lookup issue** - The backend may be caching decrypted credentials

## Architecture Challenge

MCP servers are spawned as **subprocesses** when the Claude SDK client initializes. Credentials are passed via environment variables to that subprocess. To switch accounts mid-session:

1. The old MCP server subprocess must be terminated
2. A new MCP server subprocess must start with new credentials
3. This essentially requires a new Claude SDK client instance per account change

## Potential Solutions

### Option A: Per-Request Fresh Client (Current Intent)
- `invoke_agent_streaming_with_credential` should create fresh client each time
- Verify frontend sends correct `credential_id` on every request
- Ensure no client/session caching in backend

### Option B: Session Reset on Account Switch
- Frontend detects account change and sends "reset session" signal
- Backend terminates any active agent sessions
- Next chat request creates completely fresh client

### Option C: Explicit MCP Server Lifecycle Management
- Track active MCP server subprocess per user
- On account switch, explicitly kill and restart MCP server
- More complex but gives precise control

### Option D: Dynamic MCP Config Files (User Suggested)
- Generate `.mcp.{credential_id}.json` files dynamically
- Load appropriate config when account changes
- Requires file system management per credential

## Files to Investigate

- `apps/orchestrator_3_stream/frontend/src/components/AlpacaAgentChat.vue` - Does it watch `activeCredentialId`?
- `apps/orchestrator_3_stream/frontend/src/stores/accountStore.ts` - How is `activeCredentialId` managed?
- `apps/orchestrator_3_stream/backend/modules/alpaca_agent_service.py` - Is client being cached?
- `apps/orchestrator_3_stream/backend/main.py` - Chat endpoint credential handling

## Success Criteria

- [ ] User switches account in dropdown
- [ ] Next chat message uses NEW account's credentials
- [ ] `mcp__alpaca__get_account_info` returns NEW account's data
- [ ] No stale credential data after account switch

## Related

- Previous todo (DONE): MCP server not connecting (pytz dependency fix)
- Phase 6 TRADE-01, TRADE-02 requirements partially affected
- CRED-05 multiple credentials support

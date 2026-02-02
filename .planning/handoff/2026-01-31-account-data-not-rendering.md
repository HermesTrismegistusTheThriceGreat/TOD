# Handoff: Account Data Not Rendering on Account Switch

**Created:** 2026-01-31
**Issue:** Account data display shows "No account connected" even when credentials exist
**Priority:** High - breaks Phase 5 Account Display feature

## Problem Statement

When a user has valid Alpaca credentials and switches between accounts in the credential selector dropdown, the account data (balance, equity, buying power) does not render. The UI shows "No account connected" despite:
1. Credentials existing in the database
2. Credentials appearing in the dropdown selector
3. User being authenticated

## Screenshot Evidence

The "Active Account" card shows "No account connected" even though the dropdown has two valid credentials:
- "Paper Account 2" (custom nickname)
- "Alpaca - Jan 31, 2026" (fallback display)

## Technical Context

### Relevant Files

**Frontend:**
- `apps/orchestrator_3_stream/frontend/src/components/AccountDataDisplay.vue` - Displays account metrics
- `apps/orchestrator_3_stream/frontend/src/components/AccountSelector.vue` - Credential dropdown
- `apps/orchestrator_3_stream/frontend/src/stores/accountStore.ts` - State management
- `apps/orchestrator_3_stream/frontend/src/services/credentialService.ts` - API calls

**Backend:**
- `apps/orchestrator_3_stream/backend/routers/credentials.py` - `/api/credentials/{id}/account-data` endpoint
- `apps/orchestrator_3_stream/backend/modules/account_service.py` - Alpaca API integration

### Data Flow (Expected)

1. User selects credential from dropdown (`AccountSelector.vue`)
2. `accountStore.setActiveCredential(id)` is called
3. Store should call `fetchAccountData(credentialId)`
4. Service calls `GET /api/credentials/{id}/account-data`
5. Backend decrypts credentials, calls Alpaca API
6. Response populates `accountStore.accountData`
7. `AccountDataDisplay.vue` renders the data

### Likely Root Causes to Investigate

1. **Store not triggering fetch on credential change**
   - Check `setActiveCredential` in `accountStore.ts` line ~250
   - Verify it calls `fetchAccountData` after setting active credential

2. **activeCredentialId not being set**
   - Check if `loadActiveCredential()` runs on mount
   - Verify localStorage persistence working

3. **AccountDataDisplay not reactive to store changes**
   - Check computed properties watching `accountStore.accountData`
   - Verify component is mounted and receiving updates

4. **API endpoint returning errors silently**
   - Check browser Network tab for `/account-data` calls
   - Look for 401/403/500 errors being swallowed

5. **Backend port mismatch**
   - Backend runs on port 9403 (not 8002)
   - Verify frontend API client points to correct port

### Recent Changes (Phase 5.1)

Just completed Phase 5.1 which added:
- Nickname field to credentials
- Multiple credentials per account support
- Fixed `credentialService.storeCredential` to pass nickname
- Fixed `accountStore.addCredential` to include nickname

Bug fix commits made during validation:
- `credentialService.ts` - Added `nickname?: string` parameter
- `accountStore.ts` - Added `nickname: input.nickname || undefined`

These changes may have affected the account data flow.

### Test Credentials

User: seagerjoe@gmail.com / password123
Account ID: f68d10de-b4fc-40a0-8ac9-f34fcec3d125

Credentials in database:
1. ID: 38b17b4e... nickname: "Paper Account 2" (ALPACA_PAPER2 keys)
2. ID: 0117e42d... nickname: "alpaca" (original credential)

### Debugging Steps

1. **Check browser console** for errors when switching accounts
2. **Check Network tab** for `/api/credentials/{id}/account-data` requests
3. **Add console.log** in `setActiveCredential` to trace execution
4. **Verify backend** is receiving requests: `tail -f backend/logs/*.log`
5. **Test API directly**:
   ```bash
   curl http://localhost:9403/api/credentials/38b17b4e-xxxx/account-data \
     -H "Authorization: Bearer <token>"
   ```

### Related Plans

- Phase 5 (Account Display): `.planning/phases/05-account-display/`
  - 05-01-PLAN.md: Backend account-data endpoint
  - 05-02-PLAN.md: Frontend service layer
  - 05-03-PLAN.md: AccountDataDisplay component

### Success Criteria

When fixed:
1. Selecting a credential from dropdown should fetch and display account data
2. Balance, equity, buying power should show real values from Alpaca
3. Paper/Live indicator should display correctly
4. Switching between credentials should update the display

## Commands to Start Environment

```bash
# Start backend (port 9403)
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream && ./start_be.sh &

# Start frontend (port 5175)
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream && ./start_fe.sh &

# Open browser
open http://localhost:5175
```

## Key Decision Context

From STATE.md decisions:
- [05-02]: Auto-trigger fetchAccountData when setActiveCredential called for immediate data availability
- [05-02]: Don't throw errors from fetchAccountData - account data is supplementary, not critical

This suggests the design intent was for account data to auto-fetch, but it may be failing silently.

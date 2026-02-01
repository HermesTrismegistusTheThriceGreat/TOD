---
phase: 06-trading-context
plan: 02
subsystem: trading-api
tags: [alpaca, positions, credentials, rls]
requires:
  - "Phase 03: Credential management with RLS"
  - "06-01: RLS imports in main.py"
provides:
  - "Credential-aware positions endpoint"
  - "get_all_positions_with_credential method"
  - "get_orders_with_credential method"
affects:
  - "06-03: Frontend integration"
  - "Future: Orders endpoint with credential_id"
tech-stack:
  added: []
  patterns:
    - "decrypt-on-demand pattern for credentials"
    - "temporary TradingClient per request"
key-files:
  created: []
  modified:
    - "apps/orchestrator_3_stream/backend/modules/alpaca_service.py"
    - "apps/orchestrator_3_stream/backend/main.py"
decisions:
  - "Use temporary TradingClient per request instead of singleton for credential isolation"
  - "Run sync Alpaca SDK calls in executor to avoid blocking event loop"
metrics:
  duration: "1.9min"
  completed: "2026-02-01"
---

# Phase 06 Plan 02: Credential Context for Positions Summary

**One-liner:** Positions endpoint now requires credential_id, validates ownership via RLS, and fetches positions using user-specific Alpaca credentials.

## What Was Built

### AlpacaService Methods

1. **get_all_positions_with_credential(api_key, secret_key, paper)**
   - Creates temporary TradingClient with provided credentials
   - Fetches all positions via Alpaca REST API
   - Filters for options only (AssetClass.US_OPTION)
   - Groups by ticker using existing _group_by_ticker logic
   - Returns List[OptionsPosition]

2. **get_orders_with_credential(api_key, secret_key, paper, status, limit)**
   - Creates temporary TradingClient with provided credentials
   - Fetches orders with configurable status filter (all/open/closed)
   - Converts Alpaca Order objects to dict format for JSON serialization
   - Prepares for TRADE-04 order history requirement

### Modified Positions Endpoint

```python
@app.get("/api/positions")
async def get_positions(
    request: Request,
    credential_id: str = Query(..., description="UUID of credential to fetch positions for")
):
```

- **credential_id** is now a required query parameter
- Validates credential ownership via RLS (get_connection_with_rls)
- Decrypts credentials on-demand (get_decrypted_alpaca_credential)
- Calls get_all_positions_with_credential with decrypted keys
- Returns credential access denied error if validation fails

## Key Implementation Details

### Security Pattern

The endpoint follows the decrypt-on-demand pattern established in Phase 03:

1. Set RLS context for user isolation
2. Query credential by ID (RLS filters to user's rows only)
3. Validate credential is active and owned by user
4. Decrypt api_key and secret_key
5. Use credentials immediately
6. Credentials automatically discarded on context exit

### Temporary Client Pattern

Instead of using a singleton TradingClient with global credentials, each request creates a temporary client:

```python
temp_client = TradingClient(
    api_key=api_key,
    secret_key=secret_key,
    paper=paper
)
```

This ensures credential isolation between users.

## Files Modified

| File | Changes |
|------|---------|
| `modules/alpaca_service.py` | Added get_all_positions_with_credential and get_orders_with_credential methods |
| `main.py` | Added Query import, modified get_positions endpoint signature |

## Commits

1. `ad2a024` - feat(06-02): add get_all_positions_with_credential method to AlpacaService
2. `60e5f75` - feat(06-02): modify positions endpoint to accept credential_id
3. `60beadb` - feat(06-02): add get_orders_with_credential method to AlpacaService

## Verification

All success criteria met:
- AlpacaService has get_all_positions_with_credential method
- AlpacaService has get_orders_with_credential method
- Positions endpoint requires credential_id query parameter
- Positions endpoint validates credential ownership via RLS
- Positions endpoint uses decrypt-on-demand pattern

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

### For 06-03 (Frontend Integration)
- Positions endpoint ready for frontend to call with credential_id
- Frontend needs to pass credential_id from accountStore.activeCredentialId
- Response format unchanged (GetPositionsResponse)

### For Future Orders Endpoint
- get_orders_with_credential method ready for use
- Same pattern can be applied: credential_id query param + RLS validation

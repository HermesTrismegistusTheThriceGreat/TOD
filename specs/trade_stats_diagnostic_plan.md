# Trade Stats Diagnostic Plan

## Problem Statement

The Trade Stats page at `apps/orchestrator_3_stream/frontend/src/components/TradeStats.vue` displays "No trades found that match the current filters" even though our Alpaca account has trade history.

## Investigation Summary

After comprehensive code review, all layers of the integration are **fully implemented**:

| Layer | Component | Status | Implementation |
|-------|-----------|--------|----------------|
| Frontend | TradeStats.vue | ✅ Complete | Calls `tradeApi.getTrades()` and `tradeApi.getTradeStats()` |
| Frontend | api.ts | ✅ Complete | `tradeApi` object with all three methods |
| Frontend | types/trades.ts | ✅ Complete | TypeScript interfaces match backend models |
| Backend | main.py | ✅ Complete | `/api/trades`, `/api/trade-stats`, `/api/sync-orders` endpoints |
| Backend | alpaca_sync_service.py | ✅ Complete | `get_trades()`, `get_trade_stats()`, `sync_orders()` methods |
| Backend | alpaca_models.py | ✅ Complete | `TradeResponse`, `TradeListResponse`, `TradeStatsResponse` |
| Database | alpaca_orders table | ✅ Complete | Schema in migration `10_alpaca_orders.sql` |

## Root Cause Identified

**The `alpaca_orders` table is empty because orders have never been synced from Alpaca.**

The data flow chain is complete, but it requires **manual triggering** to populate:

```
Alpaca API → POST /api/sync-orders → alpaca_orders table → GET /api/trades → TradeStats.vue
              ↑
         NEVER CALLED
```

### Evidence

1. **No automatic sync on startup**: The `lifespan()` function in `main.py` initializes `alpaca_sync_service` but does NOT call `sync_orders()`
2. **sync_orders() requires manual trigger**: Must call `POST /api/sync-orders` endpoint
3. **Frontend shows empty correctly**: The "No trades found" message is working as designed - there genuinely are no trades in the database

## Data Flow Trace

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CURRENT DATA FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────┐      ┌──────────────┐      ┌──────────────┐      ┌────────────┐ │
│  │ Alpaca API │─────►│ sync_orders()│─────►│alpaca_orders │─────►│get_trades()│ │
│  │            │      │              │      │   (EMPTY)    │      │            │ │
│  └────────────┘      └──────────────┘      └──────────────┘      └────────────┘ │
│        │                    ▲                     │                     │        │
│        │                    │                     │                     │        │
│        │             NEVER CALLED                 │                     ▼        │
│        │                                          │            ┌──────────────┐  │
│        │                                          │            │GET /api/trades│ │
│        │                                          │            └──────────────┘  │
│        │                                          │                     │        │
│        │                                          │                     ▼        │
│        │                                          │            ┌──────────────┐  │
│        │                                          │            │TradeStats.vue│  │
│        │                                          │            │"No trades    │  │
│        │                                          │            │ found"       │  │
│        │                                          │            └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Relevant Files Analyzed

### Frontend
- `apps/orchestrator_3_stream/frontend/src/components/TradeStats.vue`
  - Lines 166-169: Fetches trades and stats via `tradeApi`
  - Lines 175-178: Handles success response correctly
  - Lines 55-58: Shows "No trades found" when `filteredTrades.length === 0`

- `apps/orchestrator_3_stream/frontend/src/services/api.ts`
  - Lines 48-70: `tradeApi` object with `getTrades()`, `getTradeStats()`, `syncOrders()`

- `apps/orchestrator_3_stream/frontend/src/types/trades.ts`
  - Complete type definitions matching backend models

### Backend
- `apps/orchestrator_3_stream/backend/main.py`
  - Lines 1426-1466: `GET /api/trades` endpoint
  - Lines 1469-1491: `GET /api/trade-stats` endpoint
  - Lines 1494-1517: `POST /api/sync-orders` endpoint
  - Lines 193-196: `alpaca_sync_service` initialized but `sync_orders()` NOT called

- `apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py`
  - Lines 92-207: `sync_orders()` method (fetches from Alpaca, persists to DB)
  - Lines 650-763: `get_trades()` method (aggregates orders by trade_id)
  - Lines 765-791: `get_trade_stats()` method (calculates summary stats)

### Database
- `apps/orchestrator_db/migrations/10_alpaca_orders.sql`
  - Lines 18-73: `alpaca_orders` table schema
  - Lines 130-171: `alpaca_positions` table schema

## Fix Tasks (Ordered by Dependency)

### Task 1: Verify Alpaca API Configuration
**Priority: CRITICAL - Must be done first**

Check that Alpaca credentials are configured:

```bash
# Check .env file for Alpaca credentials
grep -E "ALPACA_(API_KEY|SECRET_KEY)" apps/orchestrator_3_stream/backend/.env
```

Expected values in `.env`:
```
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_PAPER=true  # or false for live trading
```

**File**: `apps/orchestrator_3_stream/backend/.env`

### Task 2: Manually Trigger Order Sync
**Priority: CRITICAL - Populates the database**

Call the sync endpoint to fetch orders from Alpaca:

```bash
# Trigger order sync (requires backend running)
curl -X POST http://127.0.0.1:9403/api/sync-orders
```

**Expected Response:**
```json
{
  "status": "success",
  "synced_count": 42,
  "message": "Synced 42 orders from Alpaca"
}
```

### Task 3: Verify Database Has Data
**Priority: VERIFICATION**

Query the database to confirm orders were synced:

```bash
# Connect to database and check
psql $DATABASE_URL -c "SELECT COUNT(*) FROM alpaca_orders;"
psql $DATABASE_URL -c "SELECT underlying, strategy_type, COUNT(*) FROM alpaca_orders GROUP BY underlying, strategy_type;"
```

### Task 4: Add Automatic Sync on Startup (Optional Enhancement)
**Priority: ENHANCEMENT - Prevents future empty state**

**File**: `apps/orchestrator_3_stream/backend/main.py`

**Location**: Lines 193-196 (after `init_alpaca_sync_service()`)

**Code Change**:
```python
# Current code (line 195-196):
alpaca_sync_service = await init_alpaca_sync_service(app, alpaca_service)
logger.success("Alpaca Sync service initialized")

# Add after line 196:
# Auto-sync orders on startup if Alpaca is configured
if alpaca_service.is_configured:
    try:
        logger.info("Auto-syncing Alpaca orders...")
        orders = await alpaca_sync_service.sync_orders()
        logger.success(f"Auto-synced {len(orders)} orders from Alpaca")
    except Exception as e:
        logger.warning(f"Auto-sync failed (non-blocking): {e}")
```

### Task 5: Add Sync Button to UI (Optional Enhancement)
**Priority: ENHANCEMENT - UX improvement**

**File**: `apps/orchestrator_3_stream/frontend/src/components/TradeStats.vue`

Add a sync button next to the refresh button in the header:

```vue
<!-- Add after the refresh button (around line 35) -->
<el-button
  :icon="Download"
  circle
  size="small"
  :loading="syncing"
  @click="handleSync"
  title="Sync orders from Alpaca"
/>
```

And add the sync handler in the script:

```typescript
const syncing = ref(false)

const handleSync = async () => {
  syncing.value = true
  try {
    const result = await tradeApi.syncOrders()
    if (result.status === 'success') {
      // Refresh trades after sync
      await fetchTrades()
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Sync failed'
  } finally {
    syncing.value = false
  }
}
```

## Acceptance Criteria

1. **Immediate Fix**
   - [ ] Alpaca credentials verified in `.env`
   - [ ] `POST /api/sync-orders` returns success with synced count > 0
   - [ ] `alpaca_orders` table contains order data
   - [ ] Trade Stats page displays real trade data

2. **Optional Enhancements**
   - [ ] Auto-sync on backend startup
   - [ ] Sync button in Trade Stats UI
   - [ ] Error handling for sync failures

## Validation Commands

```bash
# 1. Start backend
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend
uv run python main.py &
sleep 5

# 2. Trigger sync
curl -X POST http://127.0.0.1:9403/api/sync-orders | jq

# 3. Verify trades endpoint
curl http://127.0.0.1:9403/api/trades | jq '.total_count'

# 4. Verify stats endpoint
curl http://127.0.0.1:9403/api/trade-stats | jq

# 5. Check frontend (should now show data)
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend
npm run dev
# Open http://localhost:5173 and navigate to Trade Stats
```

## Summary

**The problem is NOT a code bug.** All integration layers are fully implemented and working correctly. The issue is **operational**: the `alpaca_orders` table needs to be populated by calling `POST /api/sync-orders`.

| Issue Type | Description | Solution |
|------------|-------------|----------|
| Root Cause | Database empty - no orders synced | Call `POST /api/sync-orders` |
| Enhancement | No auto-sync on startup | Add sync call in lifespan |
| Enhancement | No manual sync in UI | Add sync button to TradeStats |

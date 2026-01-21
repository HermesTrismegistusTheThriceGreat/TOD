# Diagnostic Logging Implementation Summary

## Objective
Add strategic diagnostic logging to trace option price data flow from Alpaca API → Backend → WebSocket → Frontend to identify where option price updates are failing (while spot prices work correctly).

## Implementation Date
2026-01-20

## Changes Made

### 1. Backend: `alpaca_service.py` - Quote Handler
**File**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/alpaca_service.py`

**Location**: `_handle_quote_update()` method (line ~380)

**Added**:
```python
# DIAGNOSTIC LOG: Option quote received from Alpaca stream
logger.info(f"[OPTION QUOTE RECEIVED] {quote.symbol}: bid={quote.bid_price}, ask={quote.ask_price}")
```

**Purpose**: Logs when Alpaca sends option quotes to the backend, confirming the data stream is active.

---

### 2. Backend: `websocket_manager.py` - Broadcast Function
**File**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/websocket_manager.py`

**Location**: `broadcast_option_price_update()` method (line ~280)

**Added**:
```python
# DIAGNOSTIC LOG: WebSocket broadcast for option price
logger.info(f"[WS BROADCAST OPTION] symbol={update_data.get('symbol')}, mid={update_data.get('mid_price')}")
```

**Purpose**: Logs when the backend broadcasts option price updates via WebSocket, confirming the data is being sent to frontend.

---

### 3. Frontend: `orchestratorStore.ts` - WebSocket Message Handler
**File**: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts`

**Location**: `onOptionPriceUpdate` handler (line ~965)

**Added**:
```typescript
// DIAGNOSTIC LOG: Option price update received via WebSocket
console.log(`[WS MESSAGE] type=option_price_update`, message.update ? message.update : '')
```

**Purpose**: Logs when the frontend receives option price update messages via WebSocket, confirming the data reaches the client.

---

## Verification

### Build Status
✅ **Frontend build successful** - No TypeScript errors
```
npm run build
vite v5.4.21 building for production...
✓ built in 2.96s
```

---

## How to Use Diagnostic Logs

### Expected Log Flow
When option prices are working correctly, you should see logs in this order:

1. **Backend Log (Alpaca → Backend)**:
   ```
   [OPTION QUOTE RECEIVED] SPY260117C00600000: bid=0.50, ask=0.52
   ```

2. **Backend Log (Backend → WebSocket)**:
   ```
   [WS BROADCAST OPTION] symbol=SPY260117C00600000, mid=0.51
   ```

3. **Frontend Log (WebSocket → Frontend)**:
   ```
   [WS MESSAGE] type=option_price_update {symbol: 'SPY260117C00600000', mid_price: 0.51, ...}
   ```

### Debugging Scenarios

#### Scenario A: No logs at all
**Issue**: Alpaca is not sending option quotes
**Action**: Check Alpaca stream subscription and credentials

#### Scenario B: Only log #1 appears
**Issue**: Backend receives quotes but doesn't broadcast them
**Action**: Check rate limiter, WebSocket manager connection

#### Scenario C: Logs #1 and #2 appear, but not #3
**Issue**: WebSocket broadcast works, but frontend doesn't receive
**Action**: Check WebSocket connection status, message routing

#### Scenario D: All logs appear, but UI doesn't update
**Issue**: Data reaches frontend, but Vue reactivity or price update logic fails
**Action**: Check `updateAlpacaPrice()`, `triggerRef()`, and component bindings

---

## Next Steps

1. **Run the backend** and observe logs:
   ```bash
   cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend
   uv run python main.py
   ```

2. **Run the frontend** and open browser console:
   ```bash
   cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend
   npm run dev
   ```

3. **Open Alpaca positions** that have active subscriptions

4. **Monitor logs** to identify where the data flow breaks

5. **Compare with spot prices** (which are working) to identify differences

---

## Related Files

- Backend Quote Handler: `backend/modules/alpaca_service.py` (line ~386)
- Backend WebSocket Broadcast: `backend/modules/websocket_manager.py` (line ~286)
- Frontend WebSocket Handler: `frontend/src/stores/orchestratorStore.ts` (line ~967)

---

## Notes

- These logs are temporary diagnostic additions for debugging
- Use `[OPTION QUOTE RECEIVED]`, `[WS BROADCAST OPTION]`, and `[WS MESSAGE]` prefixes to easily grep logs
- Spot price updates already work, so compare the flow patterns
- Rate limiting in `alpaca_service.py` may throttle some updates (200ms default)

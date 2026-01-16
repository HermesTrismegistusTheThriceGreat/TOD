# PM Tracking: Trade Stats Leg-Level Display

## Implementation Status Dashboard

| Phase | File | Status | Dependencies | Blockers |
|-------|------|--------|--------------|----------|
| **Phase 1: Backend** | | | | |
| 1.1 | `alpaca_models.py` | 🟡 PENDING | None | - |
| 1.2 | `alpaca_sync_service.py` | 🔴 BLOCKED | 1.1 | Needs models |
| 1.3 | `main.py` | 🔴 BLOCKED | 1.1, 1.2 | Needs service method |
| **Phase 2: Frontend Types** | | | | |
| 2.1 | `trades.ts` | 🟡 PENDING | None | - |
| 2.2 | `api.ts` | 🔴 BLOCKED | 2.1 | Needs types |
| **Phase 3: Components** | | | | |
| 3.1a | `LegStatsTable.vue` | 🔴 BLOCKED | 2.1 | Needs types |
| 3.1b | `TradeStatsSummary.vue` | 🔴 BLOCKED | 2.1 | Needs types |
| 3.2 | `TradeStatsCard.vue` | 🔴 BLOCKED | 3.1a, 3.1b | Needs child components |
| 3.3 | `TradeStatsGrid.vue` | 🔴 BLOCKED | 2.2, 3.2 | Needs API + card |

**Legend:** 🟢 COMPLETE | 🔵 IN PROGRESS | 🟡 PENDING | 🔴 BLOCKED

---

## Dependency Graph

```
Phase 1 (Backend) - SEQUENTIAL
================================
alpaca_models.py ──► alpaca_sync_service.py ──► main.py

Phase 2 (Frontend Types) - SEQUENTIAL
======================================
trades.ts ──► api.ts

Phase 3 (Components) - MIXED
=============================
                     ┌─► LegStatsTable.vue ────┐
trades.ts (2.1) ─────┤                         ├──► TradeStatsCard.vue ──► TradeStatsGrid.vue
                     └─► TradeStatsSummary.vue ┘                               │
                                                                               │
api.ts (2.2) ──────────────────────────────────────────────────────────────────┘
```

---

## Parallel Execution Strategy

### Wave 1 - Foundation (No Dependencies)
Can dispatch simultaneously:
- ✅ `alpaca_models.py` (Backend models)
- ✅ `trades.ts` (Frontend types)

### Wave 2 - After Wave 1 Completes
When **alpaca_models.py** completes:
- ✅ `alpaca_sync_service.py`

When **trades.ts** completes:
- ✅ `api.ts`
- ✅ `LegStatsTable.vue` (parallel)
- ✅ `TradeStatsSummary.vue` (parallel)

### Wave 3 - After Wave 2 Completes
When **alpaca_sync_service.py** completes:
- ✅ `main.py`

When **LegStatsTable.vue** AND **TradeStatsSummary.vue** complete:
- ✅ `TradeStatsCard.vue`

### Wave 4 - Final Integration
When **api.ts** AND **TradeStatsCard.vue** complete:
- ✅ `TradeStatsGrid.vue`

---

## File Details for Build Agents

### 1.1 alpaca_models.py
**Path:** `/apps/orchestrator_3_stream/backend/modules/alpaca_models.py`
**Task:** Add 4 new Pydantic models after `TradeResponse` class (~line 443)
- `LegDetail` - Individual leg with open/close matching
- `TradeSummary` - Aggregated summary for all legs
- `DetailedTrade` - Complete trade with legs array
- `DetailedTradeListResponse` - API response wrapper

### 1.2 alpaca_sync_service.py
**Path:** `/apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py`
**Task:** Add `get_detailed_trades()` method after `get_trades()` (~line 789)
- Groups orders by trade_id, then by symbol (leg)
- Matches opening/closing orders per leg
- Calculates per-leg and total P&L
- ~190 lines of new code

### 1.3 main.py
**Path:** `/apps/orchestrator_3_stream/backend/main.py`
**Task:** Add new endpoint `GET /api/trades/detailed` (~line 1476)
- Import `DetailedTradeListResponse` from alpaca_models
- Create endpoint calling `sync_service.get_detailed_trades()`
- Return `DetailedTradeListResponse`

### 2.1 trades.ts
**Path:** `/apps/orchestrator_3_stream/frontend/src/types/trades.ts`
**Task:** Add TypeScript interfaces mirroring backend models
- `LegDetail`, `TradeSummary`, `DetailedTrade`, `DetailedTradeListResponse`

### 2.2 api.ts
**Path:** `/apps/orchestrator_3_stream/frontend/src/services/api.ts`
**Task:** Add `getDetailedTrades()` method to `tradeApi` object
- Import `DetailedTradeListResponse` from types
- Call `/api/trades/detailed` with optional params

### 3.1a LegStatsTable.vue (NEW FILE)
**Path:** `/apps/orchestrator_3_stream/frontend/src/components/LegStatsTable.vue`
**Task:** Create table component showing legs within a trade card
- 7 columns: Leg, Open Action, Open Fill, Close Action, Close Fill, P&L/Share, P&L Total
- Uses Element Plus `el-table`

### 3.1b TradeStatsSummary.vue (NEW FILE)
**Path:** `/apps/orchestrator_3_stream/frontend/src/components/TradeStatsSummary.vue`
**Task:** Create summary footer component
- Shows: ticker, total credit, total debit, net P&L per contract, net P&L total

### 3.2 TradeStatsCard.vue (NEW FILE)
**Path:** `/apps/orchestrator_3_stream/frontend/src/components/TradeStatsCard.vue`
**Task:** Create main card component composing child components
- Header with trade_id, ticker, strategy tag, status tag, expiry
- Body with `<LegStatsTable>`
- Footer with `<TradeStatsSummary>`

### 3.3 TradeStatsGrid.vue (NEW FILE)
**Path:** `/apps/orchestrator_3_stream/frontend/src/components/TradeStatsGrid.vue`
**Task:** Create grid container with API integration
- Header with title, stats pills, status filter, sync button
- Loading/Error/Empty states
- Grid of `<TradeStatsCard>` components
- Calls `tradeApi.getDetailedTrades()`

---

## Validation Checklist

### Backend Validation
```bash
# Python syntax check
uv run python -m py_compile apps/orchestrator_3_stream/backend/modules/alpaca_models.py
uv run python -m py_compile apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py
uv run python -m py_compile apps/orchestrator_3_stream/backend/main.py

# Test endpoint (after backend running)
curl http://localhost:8002/api/trades/detailed | jq
```

### Frontend Validation
```bash
cd apps/orchestrator_3_stream/frontend
npm run build  # TypeScript compilation
```

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Missing import in main.py | Build fails | Ensure `DetailedTradeListResponse` imported |
| Type mismatch frontend/backend | Runtime errors | Verify interfaces match Pydantic models exactly |
| CSS variable undefined | Styling broken | Reference `global.css` for valid variables |
| `tradeApi` not exported | Import errors | Ensure added to existing `tradeApi` object, not new |
| Circular imports in backend | Module load fails | Check import order in alpaca_models.py |

---

## Notes for Coordination

1. **Backend and Frontend can progress in parallel** - Phases 1 and 2 have no cross-dependencies initially

2. **Critical path is 3.3 TradeStatsGrid.vue** - It needs both the API method (2.2) and the card component (3.2)

3. **Watch for import statements** - Every file modification needs proper imports added

4. **Test incrementally** - Run syntax checks after each file completes before moving to dependents

---

*Last Updated: [Timestamp]*
*PM: Claude Project Manager Agent*

# Implementation Report: Fix TradeStatsCard P&L Calculation Display

**Date:** 2026-01-15
**Spec:** `specs/fix-tradestats-pnl-calculation.md`
**Workflow:** 2 Sonnet Build + 2 Haiku Review + 1 Opus Fix

---

## Executive Summary

Successfully implemented the fix for TradeStatsCard P&L calculation display. The implementation restructures P&L tracking from gross totals to semantically correct opening/closing values that match brokerage statements.

### Key Changes Made

1. **Backend P&L Restructure** - Replaced `total_credit`/`total_debit` with `opening_credit`/`closing_debit`
2. **Iron Butterfly Detection** - Added detection for Iron Butterfly strategies (short strikes equal)
3. **Database Migration** - Created migration to add `iron_butterfly` to allowed strategy types
4. **Frontend Updates** - Updated TypeScript types and Vue component labels
5. **Model Fix** - Corrected TradeSummary Pydantic model field names

---

## Agent Workflow Execution

### Phase 1: Build Agents (Sonnet)

| Agent | Focus | Status |
|-------|-------|--------|
| Build Agent 1 | Backend P&L restructure + Database migration | ✅ Complete |
| Build Agent 2 | Strategy detection + Frontend updates | ✅ Complete |

### Phase 2: Review Agents (Haiku)

| Agent | Focus | Findings |
|-------|-------|----------|
| Review Agent 1 | Backend P&L changes | Implementation correct, P&L formula verified |
| Review Agent 2 | Strategy detection + Frontend | Found CRITICAL: TradeSummary model mismatch |

### Phase 3: Fix Agent (Opus)

| Agent | Focus | Status |
|-------|-------|--------|
| Fix Agent | TradeSummary model field names | ✅ Fixed |

---

## Files Modified

### Backend Files

| File | Changes |
|------|---------|
| `apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py` | Restructured `get_detailed_trades()` to track `opening_credit` and `closing_debit` instead of gross totals; Added Iron Butterfly detection in `_detect_strategy()` |
| `apps/orchestrator_3_stream/backend/modules/alpaca_models.py` | Added `is_valid_iron_butterfly()` method; Modified `detect_strategy()` to check Butterfly before Condor; Fixed `TradeSummary` field names |

### Database Files

| File | Changes |
|------|---------|
| `apps/orchestrator_db/migrations/11_add_iron_butterfly_strategy.sql` | **NEW FILE** - Adds `iron_butterfly` to strategy_type CHECK constraint |
| `apps/orchestrator_db/models.py` | Added `iron_butterfly` to `AlpacaOrder.strategy_type` Literal |

### Frontend Files

| File | Changes |
|------|---------|
| `apps/orchestrator_3_stream/frontend/src/types/trades.ts` | Updated `TradeSummary` interface: `total_credit` → `opening_credit`, `total_debit` → `closing_debit` |
| `apps/orchestrator_3_stream/frontend/src/components/TradeStatsSummary.vue` | Updated labels from "credit"/"debit" to "opening"/"closing" |

---

## Implementation Details

### P&L Calculation Logic

```python
# Track opening credit/debit
if open_action == 'SELL':
    opening_credit += open_fill * quantity * 100
else:  # BUY to open
    opening_credit -= open_fill * quantity * 100

# Track closing debit/credit
if is_closed:
    if close_action == 'BUY':
        closing_debit += close_fill * quantity * 100
    else:  # SELL to close
        closing_debit -= close_fill * quantity * 100

# Final P&L
net_pnl_total = opening_credit - closing_debit
```

### Iron Butterfly Detection Logic

```python
def is_valid_iron_butterfly(self) -> bool:
    """Iron Butterfly: 4 legs with short put strike == short call strike (ATM)"""
    return (
        lp.strike < sp.strike and
        sp.strike == sc.strike and  # Same short strikes = Butterfly
        sc.strike < lc.strike
    )
```

### Strategy Detection Order

```python
if len(self.legs) == 4:
    if self.is_valid_iron_butterfly():  # Check Butterfly FIRST (more specific)
        return "Iron Butterfly"
    if self.is_valid_iron_condor():
        return "Iron Condor"
```

---

## Review Findings & Resolutions

### Critical Issue Found

**Issue:** `TradeSummary` Pydantic model in `alpaca_models.py` had outdated field names (`total_credit`/`total_debit`) that didn't match actual usage in `get_detailed_trades()` or frontend types.

**Resolution:** Opus Fix Agent updated the model to use `opening_credit`/`closing_debit` with accurate semantic comments.

### Info-Level Suggestions

1. **Direction Logic Documentation** - Consider adding explicit comments explaining Short = net credit, Long = net debit
2. **Close Validation** - Consider adding validation that close action is opposite to open action
3. **Unit Tests** - No test files were created; recommend adding tests for benchmark validation

---

## Benchmark Validation

The implementation should produce these values:

| Trade | Opening Credit | Closing Debit | Net P&L |
|-------|----------------|---------------|---------|
| Jan 14 GLD Iron Butterfly | $38,000 | $25,500 | +$12,500 |
| Jan 16 GLD Iron Butterfly | $51,600 | $44,200 | +$7,400 |

Formula verification:
- Jan 14: `38000 - 25500 = 12500` ✓
- Jan 16: `51600 - 44200 = 7400` ✓

---

## Deployment Steps

### 1. Run Database Migration
```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_db
uv run python -c "import asyncio; from migrations import run_migrations; asyncio.run(run_migrations())"
```

### 2. Restart Backend
```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend
uv run python main.py
```

### 3. Sync Orders to Detect Iron Butterfly
```bash
curl -X POST http://localhost:8002/api/sync-orders
```

### 4. Verify P&L Calculation
```bash
curl http://localhost:8002/api/trades/detailed | jq '.trades[] | select(.ticker=="GLD") | {strategy, opening_credit: .summary.opening_credit, closing_debit: .summary.closing_debit, net_pnl: .summary.net_pnl_total}'
```

### 5. Verify Frontend Compiles
```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend
npm run type-check
```

---

## Acceptance Criteria Status

| Criteria | Status |
|----------|--------|
| Jan 14 GLD displays correct values | ⏳ Pending validation |
| Jan 16 GLD displays correct values | ⏳ Pending validation |
| Both trades show "Iron Butterfly" tag | ⏳ Pending validation |
| Database allows 'iron_butterfly' | ✅ Migration created |
| No regression in other strategies | ⏳ Pending validation |
| Per-leg P&L values unchanged | ✅ Implementation preserved |

---

## Notes

- **Breaking Change:** Field name changes require simultaneous backend + frontend deployment
- **Backward Compatibility:** Existing data is unaffected; only display semantics change
- **Re-sync Required:** After deployment, trigger order sync to update strategy detection for existing orders

---

## Agent IDs (for resumption if needed)

- Build Agent 1 (Backend P&L): `a0d9861`
- Build Agent 2 (Strategy + Frontend): `abd7cee`
- Review Agent 1 (Backend): `a395c60`
- Review Agent 2 (Strategy + Frontend): `ace7f25`
- Fix Agent (Model): `a313264`

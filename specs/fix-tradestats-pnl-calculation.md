# Plan: Fix TradeStatsCard P&L Calculation Display

## Task Description

Fix the TradeStatsCard component to accurately display profit and loss for Iron Butterfly trades. The current implementation shows gross credit/debit totals which is semantically confusing for multi-leg option strategies. Users expect to see "Opening Credit" and "Closing Debit" as net values that match their brokerage statements.

## Objective

When this plan is complete:
1. P&L display will show semantically correct "Opening Credit" and "Closing Debit" values
2. Iron Butterfly strategies will be properly detected and labeled
3. The net P&L calculation will match the benchmark data exactly:
   - Jan 14 GLD: Opening +$38,000, Closing -$25,500, Net P&L +$12,500
   - Jan 16 GLD: Opening +$51,600, Closing -$44,200, Net P&L +$7,400

## Problem Statement

The TradeStatsCard displays P&L summary with `total_credit` and `total_debit` fields that represent **gross totals** (all premium received and all premium paid across ALL legs and ALL actions). However, users expect to see:

- **Opening Credit**: Net credit received when OPENING the position (SELL premiums - BUY premiums at entry)
- **Closing Debit**: Net debit paid when CLOSING the position (BUY premiums - SELL premiums at exit)

**Example with Jan 14 GLD Iron Butterfly:**

| What Users Expect | What's Currently Shown |
|-------------------|------------------------|
| Opening Credit: $38,000 | Total Credit: $43,200 |
| Closing Debit: $25,500 | Total Debit: $30,700 |
| Net P&L: +$12,500 | Net P&L: +$12,500 ✓ |

The final P&L is mathematically correct, but the intermediate values are confusing because they don't match brokerage statements or user expectations.

Additionally, Iron Butterfly strategies are not being detected - they fall through to generic "options" because the `_detect_strategy()` method only checks for Iron Condor when there are 4 legs.

## Solution Approach

1. **Restructure P&L summary calculation** in `alpaca_sync_service.py` to track opening vs closing separately:
   - `opening_credit`: Net premium received at open (SELL - BUY at entry)
   - `closing_debit`: Net premium paid at close (BUY - SELL at exit)
   - `net_pnl_total`: opening_credit - closing_debit (unchanged formula)

2. **Add Iron Butterfly detection** to strategy detection logic:
   - Iron Butterfly: 4 legs where short put strike == short call strike (same ATM strike)
   - Iron Condor: 4 legs where all 4 strikes are different

3. **Update database schema** to include 'iron_butterfly' in allowed strategy types

4. **Update frontend types** to match new summary structure

## Relevant Files

### Backend Files (Calculation Logic)

- `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py`
  - Lines 856-978: `get_detailed_trades()` method - restructure credit/debit tracking
  - Lines 301-358: `_detect_strategy()` method - add Iron Butterfly detection

- `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend/modules/alpaca_models.py`
  - Lines 220-276: `detect_strategy()` and `is_valid_iron_condor()` methods - add Iron Butterfly detection

### Database Files (Schema)

- `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_db/migrations/10_alpaca_orders.sql`
  - Line 28-31: CHECK constraint for strategy_type - add 'iron_butterfly'

- `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_db/models.py`
  - Line 409: `strategy_type` Literal - add 'iron_butterfly'

### Frontend Files (Display - minimal changes)

- `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/types/trades.ts`
  - Lines 112-120: `TradeSummary` interface - rename fields for clarity

- `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/components/TradeStatsSummary.vue`
  - Lines 10-28: Update labels to match new field names

- `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/components/TradeStatsCard.vue`
  - Line 53: Add 'iron_butterfly' to strategy tag type mapping (already exists!)

### New Files

None required - all changes are modifications to existing files.

## Implementation Phases

### Phase 1: Foundation (Backend P&L Restructure)

1. Modify `get_detailed_trades()` to track opening vs closing separately
2. Calculate `opening_credit` as net of all opening leg values
3. Calculate `closing_debit` as net of all closing leg values
4. Update summary dict structure with new field names

### Phase 2: Core Implementation (Strategy Detection)

1. Add `is_valid_iron_butterfly()` method to `IronCondorPosition` class
2. Modify `detect_strategy()` to check for Iron Butterfly before Iron Condor
3. Mirror changes in `AlpacaSyncService._detect_strategy()`
4. Update database CHECK constraint via new migration

### Phase 3: Integration & Polish (Frontend Updates)

1. Update `TradeSummary` TypeScript interface
2. Update `TradeStatsSummary.vue` labels
3. Verify display matches benchmark data
4. Run Playwright validation

## Step by Step Tasks

### 1. Add Iron Butterfly Detection to Backend Models

- Add `is_valid_iron_butterfly()` method to `IronCondorPosition` class in `alpaca_models.py`:
  ```python
  def is_valid_iron_butterfly(self) -> bool:
      """Verify this is a valid iron butterfly structure.

      Iron Butterfly: 4 legs with short put strike == short call strike (ATM)
      """
      if len(self.legs) != 4:
          return False

      sp = self.short_put
      lp = self.long_put
      sc = self.short_call
      lc = self.long_call

      if not all([sp, lp, sc, lc]):
          return False

      # Iron Butterfly: short put and short call at SAME strike (ATM)
      # Long put below, long call above
      return (
          lp.strike < sp.strike and
          sp.strike == sc.strike and  # KEY DIFFERENCE: same strike
          sc.strike < lc.strike
      )
  ```
- Modify `detect_strategy()` to check for Iron Butterfly first:
  ```python
  if len(self.legs) == 4:
      if self.is_valid_iron_butterfly():
          return "Iron Butterfly"
      if self.is_valid_iron_condor():
          return "Iron Condor"
  ```

### 2. Add Iron Butterfly Detection to Sync Service

- In `alpaca_sync_service.py` `_detect_strategy()` method, add check for Iron Butterfly:
  ```python
  # Check for Iron Butterfly (4 legs: 2 calls + 2 puts, short strikes equal)
  if len(orders) == 4 and len(calls) == 2 and len(puts) == 2:
      short_call = next((c for c in calls if c['side'] == 'sell'), None)
      short_put = next((p for p in puts if p['side'] == 'sell'), None)

      if short_call and short_put:
          if short_call['strike_price'] == short_put['strike_price']:
              return 'iron_butterfly'
          else:
              # Different short strikes = Iron Condor
              call_sides = set(c['side'] for c in calls)
              put_sides = set(p['side'] for p in puts)
              if call_sides == {'buy', 'sell'} and put_sides == {'buy', 'sell'}:
                  return 'iron_condor'
  ```

### 3. Restructure P&L Summary Calculation

- In `get_detailed_trades()`, replace `total_credit`/`total_debit` tracking with:
  ```python
  # Track opening and closing separately
  opening_credit = 0.0  # Net premium from opening legs (SELL - BUY)
  closing_debit = 0.0   # Net premium for closing legs (BUY - SELL)

  for leg:
      if open_action == 'SELL':
          opening_credit += open_fill * quantity * 100
      else:  # BUY to open
          opening_credit -= open_fill * quantity * 100  # Reduces net credit

      if is_closed:
          if close_action == 'BUY':
              closing_debit += close_fill * quantity * 100
          else:  # SELL to close
              closing_debit -= close_fill * quantity * 100  # Reduces net debit

  # Final P&L
  net_pnl_total = opening_credit - closing_debit
  ```

- Update summary dict:
  ```python
  'summary': {
      'opening_credit': round(opening_credit, 2),
      'closing_debit': round(closing_debit, 2),
      'net_pnl_per_contract': round(net_pnl_per_contract, 4),
      'net_pnl_total': round(net_pnl_total, 2),
      'leg_count': len(leg_details),
      'closed_legs': closed_legs,
      'open_legs': open_legs
  }
  ```

### 4. Create Database Migration for Iron Butterfly

- Create new migration file `apps/orchestrator_db/migrations/11_add_iron_butterfly_strategy.sql`:
  ```sql
  -- Migration: Add iron_butterfly to strategy_type enum
  -- Drop existing constraint and recreate with new value

  ALTER TABLE alpaca_orders
  DROP CONSTRAINT IF EXISTS alpaca_orders_strategy_type_check;

  ALTER TABLE alpaca_orders
  ADD CONSTRAINT alpaca_orders_strategy_type_check
  CHECK (strategy_type IN (
      'iron_condor', 'iron_butterfly', 'vertical_spread',
      'strangle', 'straddle', 'single_leg', 'options'
  ));
  ```

### 5. Update Database Model

- In `apps/orchestrator_db/models.py`, update `AlpacaOrder.strategy_type`:
  ```python
  strategy_type: Optional[Literal[
      'iron_condor', 'iron_butterfly', 'vertical_spread',
      'strangle', 'straddle', 'single_leg', 'options'
  ]] = None
  ```

### 6. Update Frontend Types

- In `types/trades.ts`, update `TradeSummary` interface:
  ```typescript
  export interface TradeSummary {
    opening_credit: number    // Net credit received at open
    closing_debit: number     // Net debit paid at close
    net_pnl_per_contract: number
    net_pnl_total: number
    leg_count: number
    closed_legs: number
    open_legs: number
  }
  ```

### 7. Update Frontend Display Labels

- In `TradeStatsSummary.vue`, update labels to match new semantics:
  ```vue
  <div class="summary-cell">
    <span class="value">{{ formatMoney(summary.opening_credit) }}</span>
    <span class="sublabel">opening</span>
  </div>

  <div class="summary-cell">
    <span class="value">{{ formatMoney(summary.closing_debit) }}</span>
    <span class="sublabel">closing</span>
  </div>
  ```

### 8. Validate with Benchmark Data

- Create a test script that verifies P&L calculations match benchmark:
  ```python
  # Test Jan 14 GLD Iron Butterfly
  # Opening: SELL 423C@1.87, SELL 423P@2.43, BUY 431C@0.15, BUY 415P@0.35
  # Closing: BUY 423C@2.12, BUY 423P@0.45, SELL 431C@0.01, SELL 415P@0.01

  opening_credit = (1.87 + 2.43 - 0.15 - 0.35) * 100 * 100  # $38,000
  closing_debit = (2.12 + 0.45 - 0.01 - 0.01) * 100 * 100   # $25,500
  net_pnl = opening_credit - closing_debit                   # $12,500

  assert opening_credit == 38000
  assert closing_debit == 25500
  assert net_pnl == 12500
  ```

## Testing Strategy

### Unit Tests

1. **P&L Calculation Tests** (`test_pnl_calculation.py`):
   - Test Iron Butterfly P&L with Jan 14 GLD benchmark data
   - Test Iron Butterfly P&L with Jan 16 GLD benchmark data
   - Test Iron Condor P&L (ensure no regression)
   - Test partial close scenarios
   - Test open position scenarios (unrealized P&L)

2. **Strategy Detection Tests** (`test_strategy_detection.py`):
   - Test Iron Butterfly detection (4 legs, same short strikes)
   - Test Iron Condor detection (4 legs, different short strikes)
   - Test that Iron Butterfly is detected BEFORE Iron Condor

### Integration Tests

1. **API Endpoint Tests**:
   - `GET /api/trades/detailed` returns correct `opening_credit` and `closing_debit`
   - Strategy type is correctly detected and returned

### UI Validation (Playwright)

1. Navigate to Trade Stats view
2. Verify GLD trades show correct values:
   - Opening: $38,000 / $51,600
   - Closing: $25,500 / $44,200
   - Net P&L: $12,500 / $7,400
3. Verify strategy tag shows "Iron Butterfly" (not "Options")

## Acceptance Criteria

1. [ ] Jan 14 GLD Iron Butterfly displays:
   - Opening Credit: $38,000
   - Closing Debit: $25,500
   - Net P&L: +$12,500

2. [ ] Jan 16 GLD Iron Butterfly displays:
   - Opening Credit: $51,600
   - Closing Debit: $44,200
   - Net P&L: +$7,400

3. [ ] Both trades show strategy tag "Iron Butterfly" (not "Options")

4. [ ] Database allows 'iron_butterfly' as strategy_type

5. [ ] No regression in existing Iron Condor, Vertical Spread, Straddle, Strangle detection

6. [ ] Per-leg P&L values are correct (unchanged from current implementation)

## Validation Commands

Execute these commands to validate the task is complete:

```bash
# 1. Run database migration
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_db
uv run python -c "import asyncio; from migrations import run_migrations; asyncio.run(run_migrations())"

# 2. Sync orders to pick up strategy detection changes
curl -X POST http://localhost:8002/api/sync-orders

# 3. Verify P&L calculation via API
curl http://localhost:8002/api/trades/detailed | jq '.trades[] | select(.ticker=="GLD") | {strategy, opening_credit: .summary.opening_credit, closing_debit: .summary.closing_debit, net_pnl: .summary.net_pnl_total}'

# 4. Run backend tests
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend
uv run pytest tests/test_pnl_calculation.py -v

# 5. Verify frontend compiles
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend
npm run type-check

# 6. Run Playwright validation (if available)
# Use playwright-validator agent to verify UI displays correct values
```

## Notes

### Key Insight: Formula is Correct, Semantics are Wrong

The existing P&L calculation `net_pnl = total_credit - total_debit` produces the mathematically correct result. The issue is that `total_credit` and `total_debit` are GROSS totals (all credits from any leg, all debits from any leg), not the NET opening/closing values users expect to see.

### Backward Compatibility

The change to `TradeSummary` field names (`total_credit` → `opening_credit`, `total_debit` → `closing_debit`) is a breaking change for the frontend. Both must be updated simultaneously.

### Iron Butterfly vs Iron Condor Detection

The key difference:
- **Iron Butterfly**: Short put strike == Short call strike (both at ATM)
- **Iron Condor**: Short put strike < Short call strike (both OTM)

Detection order matters - check Iron Butterfly FIRST since it's a more specific pattern.

### Dependencies

- Requires database migration to run before strategy detection changes take effect for new orders
- Existing orders with incorrect strategy_type can be corrected by re-syncing orders after code deployment

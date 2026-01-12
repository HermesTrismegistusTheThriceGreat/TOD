# Plan: Ticker-Grouped Options Display

## Task Description

Modify the options positions display logic to show every ticker symbol in its own card, regardless of whether the positions form a valid iron condor structure. Currently, the system strictly filters for iron condor patterns (exactly 4 legs with 2C+2P structure and valid strike ordering), which causes many positions to be hidden from the UI.

## Objective

When complete, every ticker (SPY, NFLX, GLD, SLV, QQQ, etc.) with option positions will get its own card displaying all associated options legs, without requiring iron condor structure validation.

## Problem Statement

The current implementation has strict iron condor validation that filters out positions:

1. **Backend filtering** (`alpaca_service.py` lines 256-324):
   - Requires exactly 4 legs per underlying/expiry
   - Requires 2 calls + 2 puts structure
   - Skips groups that don't match this pattern

2. **Model validation** (`alpaca_models.py` lines 218-237):
   - `is_valid_iron_condor()` requires all 4 leg types
   - Validates strike ordering: Long Put < Short Put < Short Call < Long Call

This causes legitimate option positions to be hidden when they don't form perfect iron condor structures.

## Solution Approach

1. **Generalize the data model** - Rename `IronCondorPosition` to `TickerPosition` to reflect that it can hold any option structure
2. **Relax backend grouping** - Modify `_group_into_iron_condors()` to group by ticker only and include all positions
3. **Add optional strategy detection** - Instead of filtering, detect the strategy type and set it as metadata
4. **Update frontend types and components** - Rename and adjust to support variable leg counts

## Relevant Files

### Backend Files
- `apps/orchestrator_3_stream/backend/modules/alpaca_models.py` - Pydantic models for positions and legs
- `apps/orchestrator_3_stream/backend/modules/alpaca_service.py` - Service with `_group_into_iron_condors()` method
- `apps/orchestrator_3_stream/backend/tests/test_alpaca_models.py` - Unit tests for models
- `apps/orchestrator_3_stream/backend/tests/test_alpaca_service.py` - Unit tests for service

### Frontend Files
- `apps/orchestrator_3_stream/frontend/src/types/alpaca.ts` - TypeScript interfaces and transform functions
- `apps/orchestrator_3_stream/frontend/src/components/IronCondorCard.vue` - Card component for displaying positions
- `apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue` - Parent component that renders cards
- `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPositions.ts` - Composable for fetching positions
- `apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts` - Pinia store with position state

## Implementation Phases

### Phase 1: Backend Model Updates
Rename models from iron condor-specific to generic ticker-based naming and relax validation.

### Phase 2: Backend Service Updates
Modify the grouping logic to include all positions per ticker without strict validation.

### Phase 3: Frontend Updates
Update TypeScript types, component names, and display logic to handle variable positions.

### Phase 4: Testing & Validation
Update tests to reflect new behavior and validate the changes work end-to-end.

## Step by Step Tasks

### 1. Update Backend Pydantic Models (`alpaca_models.py`)

- Rename `IronCondorPosition` to `TickerPosition` (keep `IronCondorPosition` as alias for backwards compatibility)
- Modify `strategy` field to default to `"Options"` instead of `"Iron Condor"`
- Change `is_valid_iron_condor()` to a non-filtering check:
  ```python
  def is_valid_iron_condor(self) -> bool:
      """Check if this is a valid iron condor structure (informational only)"""
      # Keep original logic but don't use it for filtering
  ```
- Add a new `detect_strategy()` method that returns strategy type based on legs:
  ```python
  def detect_strategy(self) -> str:
      """Detect the strategy type based on leg structure"""
      if len(self.legs) == 4 and self.is_valid_iron_condor():
          return "Iron Condor"
      elif len(self.legs) == 2:
          # Check for vertical spread, straddle, etc.
          ...
      return "Options"  # Default for unrecognized patterns
  ```
- Update `__all__` exports to include new names

### 2. Update Backend Response Models (`alpaca_models.py`)

- Update `GetPositionsResponse` to use the new model name:
  ```python
  positions: List[TickerPosition] = []  # Or keep as IronCondorPosition alias
  ```
- Keep backwards compatibility with existing API consumers

### 3. Modify Backend Grouping Logic (`alpaca_service.py`)

- Rename method from `_group_into_iron_condors()` to `_group_by_ticker()`:
  ```python
  def _group_by_ticker(self, positions: list) -> List[TickerPosition]:
  ```
- Remove the strict 4-leg requirement:
  ```python
  # OLD: if len(legs) != 4: continue
  # NEW: if len(legs) == 0: continue  # Only skip if no legs
  ```
- Remove the 2C+2P validation:
  ```python
  # OLD: if len(calls) != 2 or len(puts) != 2: continue
  # NEW: Remove this check entirely
  ```
- Group by underlying ticker only (not by expiry):
  ```python
  # OLD: key = (occ.underlying, occ.expiry_date)
  # NEW: key = occ.underlying
  ```
- Remove the `is_valid_iron_condor()` check that skips positions:
  ```python
  # OLD: if ic.is_valid_iron_condor(): iron_condors.append(ic)
  # NEW:
  ic.strategy = ic.detect_strategy()  # Set detected strategy
  ticker_positions.append(ic)  # Always append
  ```
- Update method call in `get_all_positions()`:
  ```python
  # OLD: iron_condors = self._group_into_iron_condors(option_positions)
  # NEW: ticker_positions = self._group_by_ticker(option_positions)
  ```
- Update logging messages

### 4. Handle Multiple Expiry Dates Per Ticker

- When grouping by ticker only, positions may have different expiry dates
- Modify `TickerPosition` to handle this:
  ```python
  expiry_date: Optional[date] = None  # Make optional
  expiry_dates: List[date] = []  # Add list of all expiry dates

  @computed_field
  @property
  def earliest_expiry(self) -> Optional[date]:
      """Get earliest expiry date across all legs"""
      dates = [leg.expiry_date for leg in self.legs]
      return min(dates) if dates else None
  ```
- Or alternatively, create one card per ticker+expiry combination (less change)

### 5. Update Frontend TypeScript Types (`alpaca.ts`)

- Add `TickerPosition` type alongside `IronCondorPosition`:
  ```typescript
  /** Ticker position with option legs (frontend camelCase) */
  export interface TickerPosition {
    id: string
    ticker: string
    strategy: string  // "Iron Condor", "Vertical Spread", "Options", etc.
    expiryDate: string
    legs: OptionLeg[]
    createdAt: string
    totalPnl?: number
    daysToExpiry?: number
  }

  // Backwards compatibility
  export type IronCondorPosition = TickerPosition
  ```
- Update transform functions to work with both names
- Add strategy detection helper if needed on frontend

### 6. Update Frontend Card Component

- Rename `IronCondorCard.vue` to `PositionCard.vue` (or keep name for backwards compatibility)
- Update template to display dynamic strategy name:
  ```vue
  <el-tag type="info" effect="plain">{{ position.strategy }}</el-tag>
  ```
- Update empty state message:
  ```vue
  <!-- OLD: -->
  <span>No iron condor positions found</span>
  <!-- NEW: -->
  <span>No option positions found</span>
  ```
- The card already handles variable leg counts well (uses `position.legs.length`)

### 7. Update Frontend OpenPositions Component

- Update empty state message:
  ```vue
  <!-- OLD: -->
  <span>No open iron condor positions</span>
  <!-- NEW: -->
  <span>No open option positions</span>
  ```
- Component already iterates over all positions, no logic changes needed

### 8. Update Backend Unit Tests (`test_alpaca_models.py`)

- Keep existing iron condor validation tests (method still exists)
- Add new tests for `detect_strategy()`:
  ```python
  def test_detect_strategy_iron_condor(self):
      """Detects iron condor strategy"""
      ic = self.create_valid_iron_condor()
      assert ic.detect_strategy() == "Iron Condor"

  def test_detect_strategy_single_leg(self):
      """Single leg shows as Options"""
      pos = TickerPosition(
          ticker="SPY",
          expiry_date=date(2026, 1, 17),
          legs=[single_leg]
      )
      assert pos.detect_strategy() == "Options"
  ```
- Add tests for positions with variable leg counts

### 9. Update Backend Service Tests (`test_alpaca_service.py`)

- Add tests for `_group_by_ticker()` with various position configurations:
  ```python
  def test_group_by_ticker_single_leg(self):
      """Single option leg creates ticker position"""
      ...

  def test_group_by_ticker_partial_spread(self):
      """2-leg spread creates ticker position"""
      ...

  def test_group_by_ticker_multiple_tickers(self):
      """Multiple tickers create separate positions"""
      ...
  ```

### 10. Validate End-to-End

- Start the backend server
- Verify API returns all option positions grouped by ticker
- Verify frontend displays each ticker in its own card
- Verify strategy is correctly detected and displayed
- Test with various position configurations

## Testing Strategy

### Unit Tests
- Test `detect_strategy()` returns correct strategy for various leg configurations
- Test `_group_by_ticker()` includes all positions without filtering
- Test positions with 1, 2, 3, 4, and 5+ legs are all included
- Test multiple tickers create separate position cards

### Integration Tests
- Test API endpoint returns all option positions
- Test WebSocket price updates still work for all positions
- Test frontend correctly renders variable leg counts

### Edge Cases
- Single option position (1 leg)
- Two-leg vertical spread
- Three-leg position (partial iron condor)
- Five+ leg position (complex strategy)
- Multiple expiry dates for same ticker

## Acceptance Criteria

- [ ] Every ticker with option positions gets its own card in the UI
- [ ] Positions are grouped by underlying ticker symbol
- [ ] No positions are filtered out due to iron condor validation
- [ ] Strategy type is detected and displayed (Iron Condor, Options, etc.)
- [ ] Existing iron condor positions still display correctly
- [ ] P/L calculations work for all position configurations
- [ ] Price streaming works for all option symbols
- [ ] All existing tests pass
- [ ] New tests cover the relaxed grouping logic

## Validation Commands

Execute these commands to validate the task is complete:

```bash
# Backend tests
cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_alpaca_models.py -v

cd apps/orchestrator_3_stream/backend && uv run pytest tests/test_alpaca_service.py -v

# Type check (if mypy is configured)
cd apps/orchestrator_3_stream/backend && uv run python -m py_compile modules/alpaca_models.py modules/alpaca_service.py

# Frontend type check
cd apps/orchestrator_3_stream/frontend && npm run type-check

# Start backend and verify API
cd apps/orchestrator_3_stream/backend && uv run uvicorn main:app --reload

# Test API endpoint (in another terminal)
curl http://localhost:8000/api/positions | jq '.positions | length'
```

## Notes

### Backwards Compatibility
- Keep `IronCondorPosition` as a type alias for `TickerPosition` to avoid breaking existing code
- Keep `is_valid_iron_condor()` method for reference, just don't use it for filtering
- API response structure remains the same

### Strategy Detection Priority
When implementing `detect_strategy()`, check in this order:
1. Iron Condor (4 legs, 2C+2P, correct strike ordering)
2. Iron Butterfly (4 legs, same middle strikes)
3. Vertical Spread (2 legs, same type, different strikes)
4. Straddle (2 legs, same strike, different types)
5. Strangle (2 legs, different strikes, different types)
6. Default to "Options" for unrecognized patterns

### Performance Considerations
- Grouping by ticker instead of ticker+expiry may result in fewer cards but more legs per card
- Consider if this impacts rendering performance with many legs
- The current sorting logic in `sortedLegs` computed property handles this well

### Future Enhancements
- Add expiry date grouping within each ticker card
- Add collapsible sections for different expiry dates
- Add strategy-specific visualizations (payoff diagrams)

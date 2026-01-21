# Plan: Remove Strategy Detection and Simplify Position Grouping

## Task Description
Remove all options strategy identification/detection logic (Iron Condor, Iron Butterfly, Vertical Spread, Straddle, Strangle) from the codebase. Simplify the system so that `OpenPositionCard` groups legs solely by underlying ticker and expiry date without any strategy classification. Rename the `IronCondorPosition` class to a more generic name like `OptionsPosition`.

## Objective
When complete:
1. The `IronCondorPosition` class will be renamed to `OptionsPosition`
2. All `detect_strategy()` methods will be removed
3. The `strategy` field will be kept but always set to `"Options"` (for backwards compatibility)
4. Position grouping will continue to work by underlying + expiry (this already works correctly)
5. Frontend will display "Options" instead of specific strategy names
6. All tests will pass with updated expectations

## Problem Statement
The current strategy detection logic (Iron Condor, Iron Butterfly, etc.) is confusing users and adding unnecessary complexity. The system identifies strategy types based on leg configurations, but this classification:
- Causes confusion when positions don't perfectly match expected patterns
- Adds complexity without providing significant user value
- The class name `IronCondorPosition` is misleading when used for other strategy types

## Solution Approach
1. Rename `IronCondorPosition` → `OptionsPosition` throughout the codebase
2. Remove `detect_strategy()`, `is_valid_iron_condor()`, `is_valid_iron_butterfly()` methods
3. Keep `strategy` field with static default `"Options"` for backward compatibility
4. Simplify frontend formatting functions to just display "Options"
5. Update all tests to reflect the new behavior

## Relevant Files

### Backend - Core Changes
- **`backend/modules/alpaca_models.py`** - Contains `IronCondorPosition` class (rename to `OptionsPosition`), `detect_strategy()` method (remove), validation methods (remove)
- **`backend/modules/alpaca_service.py`** - Imports `IronCondorPosition`, calls `detect_strategy()` at line 318 (remove call)
- **`backend/modules/alpaca_sync_service.py`** - Has duplicate `_detect_strategy()` method at lines 296-341 (remove)

### Backend - Database Models
- **`backend/modules/orch_database_models.py`** - Has `strategy_type` field with literal types at line 409 (simplify)
- **`backend/modules/alpaca_models_db.py`** - Has `strategy_type` field at line 27 (simplify)

### Frontend - Types & Services
- **`frontend/src/types/alpaca.ts`** - `strategy: string` field in types (keep as-is, no change needed)
- **`frontend/src/services/alpacaService.ts`** - May have references to transform (verify)

### Frontend - Components
- **`frontend/src/components/OpenPositionCard.vue`** - Mock data at line 46, confirmation dialog at line 198
- **`frontend/src/components/TradeStats.vue`** - `formatStrategy()` at lines 268-277, `getStrategyTagType()` at lines 280-285
- **`frontend/src/components/TradeStatsCard.vue`** - Similar helper functions at lines 52-60, 72-73
- **`frontend/src/components/CalendarPage.vue`** - Displays `position.strategy` at line 24

### Backend Tests
- **`backend/tests/test_alpaca_models.py`** - `TestIronCondorPosition` class, `TestDetectStrategy` class (remove/update)
- **`backend/tests/test_alpaca_service.py`** - Strategy detection tests at lines 528-630 (update assertions)
- **`backend/tests/test_alpaca_endpoints.py`** - Position creation tests (update)

### Frontend Tests
- **`frontend/src/composables/__tests__/useAlpacaPositions.spec.ts`** - Mock data with strategy values
- **`frontend/src/components/__tests__/OpenPositions.spec.ts`** - Mock data with strategy values
- **`frontend/src/components/__tests__/OpenPositions.integration.spec.ts`** - Mock data with strategy values

### Documentation
- **`.claude/commands/experts/database/expertise.yaml`** - References strategy detection (update docs)

## Implementation Phases

### Phase 1: Backend Model Refactoring
Rename the core class and remove strategy detection methods from `alpaca_models.py`.

### Phase 2: Backend Service Updates
Update imports and remove strategy detection calls in service files.

### Phase 3: Frontend Simplification
Update components to display generic "Options" and simplify formatting functions.

### Phase 4: Test Updates
Update all test files to reflect the new behavior.

## Step by Step Tasks

### 1. Rename IronCondorPosition to OptionsPosition in alpaca_models.py
- Line 155: Rename class `IronCondorPosition` to `OptionsPosition`
- Lines 157-165: Update docstring to remove Iron Condor references, describe as "Options position grouped by underlying and expiry"
- Line 178: Keep `strategy: str = "Options"` as default (no change needed)
- Lines 197-218: **Remove** `get_leg_by_type()` method and helper properties (`short_put`, `long_put`, `short_call`, `long_call`) - only used for validation
- Lines 220-263: **Remove** `is_valid_iron_condor()` and `is_valid_iron_butterfly()` methods entirely
- Lines 265-304: **Remove** entire `detect_strategy()` method
- Line 614: Update alias `TickerPosition = OptionsPosition` (keep for backwards compatibility)
- Lines 616-619: Update `__all__` exports to use `OptionsPosition`

### 2. Update alpaca_service.py imports and strategy detection
- Line 8: Update module docstring to remove "Iron condor position detection"
- Line 40: Change import from `IronCondorPosition` to `OptionsPosition`
- Lines 122-123: Update class docstring to remove iron condor references
- Lines 134, 204, 253, 263: Update type hints from `IronCondorPosition` to `OptionsPosition`
- Lines 267-271: Update comment to remove strategy detection mention
- Lines 310-311: Update comment and class instantiation to `OptionsPosition`
- Line 318: **DELETE** the line `position.strategy = position.detect_strategy()`
- Line 321: Change log message from `{position.strategy}` to just `"Options position"`

### 3. Remove duplicate strategy detection in alpaca_sync_service.py
- Lines 285-341: **Remove** the entire `_detect_strategy()` method
- Line 285: Set strategy directly to `'options'` without calling detect method
- Update any type hints referencing `IronCondorPosition` to `OptionsPosition`

### 4. Simplify database models strategy_type field
- In `orch_database_models.py` line 409: Change `strategy_type: Literal['iron_condor', 'iron_butterfly', ...]` to `strategy_type: str = "options"` or `Literal['options']`
- In `alpaca_models_db.py` line 27: Same change as above

### 5. Update OpenPositionCard.vue mock data and dialog
- Line 46: Change `strategy: "Iron Condor"` to `strategy: "Options"`
- Line 198: Change confirmation message from `"this ${position.value.strategy}"` to `"this options position"` (hardcode generic text)

### 6. Simplify TradeStats.vue formatting functions
- Lines 268-277: Simplify `formatStrategy()` to just return `"Options"` or title-case the input
```typescript
const formatStrategy = (strategy: string): string => {
  return strategy.charAt(0).toUpperCase() + strategy.slice(1).toLowerCase()
}
```
- Lines 280-285: Simplify `getStrategyTagType()` to always return `'info'`:
```typescript
const getStrategyTagType = (_strategy: string) => 'info'
```

### 7. Simplify TradeStatsCard.vue formatting functions
- Lines 52-60: Simplify `getStrategyTagType()` to return `''` or single type
- Lines 72-73: Simplify `formatStrategy()` similar to TradeStats.vue

### 8. Update backend test files
- In `test_alpaca_models.py`:
  - Line 20: Update import from `IronCondorPosition` to `OptionsPosition`
  - Lines 181-388: **Remove** entire `TestDetectStrategy` class
  - Rename `TestIronCondorPosition` to `TestOptionsPosition`
  - Update any remaining tests that reference strategy detection
- In `test_alpaca_service.py`:
  - Line 19: Update import
  - Lines 528-544: Update `test_group_by_ticker_four_legs_iron_condor` - rename and change assertion from `"Iron Condor"` to `"Options"`
  - Lines 604-630: Update strangle/straddle tests - change assertions to expect `"Options"`
- In `test_alpaca_endpoints.py`:
  - Lines 27-30: Update to use `OptionsPosition`

### 9. Update frontend test files
- In `useAlpacaPositions.spec.ts` (lines 40, 89, 125, 152): Change all `strategy: 'Iron Condor'` to `strategy: 'Options'`
- In `OpenPositions.spec.ts` (lines 87, 154, 162, etc.): Change all strategy values to `'Options'`
- In `OpenPositions.integration.spec.ts` (lines 118, 163, 246, 323): Change all strategy values to `'Options'`

### 10. Update documentation files
- In `.claude/commands/experts/database/expertise.yaml` lines 259, 462-464: Update references to remove strategy detection documentation

### 11. Validate all changes
- Run backend tests: `cd backend && uv run pytest`
- Run frontend tests: `cd frontend && npm test`
- Start the application and verify positions display correctly
- Verify the `/api/positions` endpoint returns positions with `strategy: "Options"`

## Testing Strategy

### Backend Tests
- All existing position grouping tests should pass (grouping by underlying+expiry is unchanged)
- Strategy detection tests should be removed or updated to expect "Options"
- Verify `OptionsPosition` model serializes correctly

### Frontend Tests
- Component tests should render positions without strategy-specific logic
- Mock data should use `strategy: 'Options'`
- Verify close confirmation dialog shows generic text

### Integration Tests
- Fetch real positions from Alpaca API
- Verify they display correctly in UI with "Options" label
- Test close strategy and close leg functionality

## Acceptance Criteria
- [ ] `IronCondorPosition` class renamed to `OptionsPosition` in all files
- [ ] `detect_strategy()` method removed from `alpaca_models.py`
- [ ] Duplicate `_detect_strategy()` method removed from `alpaca_sync_service.py`
- [ ] Validation methods (`is_valid_iron_condor`, `is_valid_iron_butterfly`) removed
- [ ] All type hints updated to use `OptionsPosition`
- [ ] Frontend displays "Options" instead of specific strategy names
- [ ] Confirmation dialogs use generic "options position" text
- [ ] All backend tests pass: `uv run pytest`
- [ ] All frontend tests pass: `npm test`
- [ ] `/api/positions` returns positions with `strategy: "Options"`

## Validation Commands
Execute these commands to validate the task is complete:

- `cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend && uv run pytest` - Run all backend tests
- `cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend && npm test` - Run all frontend tests
- `grep -r "IronCondorPosition" apps/orchestrator_3_stream/ --include="*.py" --include="*.ts" --include="*.vue"` - Should return NO matches after completion
- `grep -r "detect_strategy" apps/orchestrator_3_stream/ --include="*.py"` - Should return NO matches (except possibly comments/docs)
- `curl http://localhost:8002/api/positions | jq '.positions[0].strategy'` - Should return `"Options"`

## Notes
- The `TickerPosition` alias should be kept for backwards compatibility but updated to point to `OptionsPosition`
- The `strategy` field is kept in the data model for backwards compatibility with any external systems
- The leg sorting logic in `OpenPositionCard.vue` (`sortedLegs` computed) is INDEPENDENT of strategy and should NOT be changed
- Position grouping by underlying + expiry already works correctly in `_group_by_ticker()` - no changes needed to grouping logic
- Consider keeping helper properties (`short_put`, `long_put`, etc.) if they're useful for P/L calculations, but they can be removed if only used for validation

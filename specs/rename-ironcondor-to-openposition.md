# Plan: Rename IronCondorCard to OpenPositionCard

## Task Description

Refactor the codebase to rename `IronCondorCard` component and `IronCondorPosition` type to `OpenPositionCard` and `OpenPosition` respectively. The current naming is misleading because the card component is used for displaying ANY open position strategy type (Iron Condors, Vertical Spreads, Straddles, Strangles, etc.), not just iron condors.

## Objective

Rename all occurrences of `IronCondorCard` and `IronCondorPosition` (and related types) to use the more generic `OpenPositionCard` and `OpenPosition` naming, ensuring consistent naming throughout the frontend and backend while maintaining backwards compatibility aliases.

## Problem Statement

The current naming (`IronCondorCard`, `IronCondorPosition`) is confusing because:
1. The `IronCondorCard` component displays any options strategy (verified by `detect_strategy()` method)
2. The `IronCondorPosition` type can hold 1-4+ legs, not just 4-leg iron condors
3. This naming confusion can mislead developers about the component's actual purpose

## Solution Approach

1. **Rename the Vue component file** from `IronCondorCard.vue` to `OpenPositionCard.vue`
2. **Rename TypeScript types** in `types/alpaca.ts`
3. **Rename Python Pydantic models** in `alpaca_models.py`
4. **Update all imports and usages** across frontend and backend
5. **Maintain backwards compatibility** with type aliases (existing `TickerPosition` pattern)

## Relevant Files

### Frontend Files to Update

- **`apps/orchestrator_3_stream/frontend/src/components/IronCondorCard.vue`** → Rename to `OpenPositionCard.vue`
- **`apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue`** - Update import statement
- **`apps/orchestrator_3_stream/frontend/src/types/alpaca.ts`** - Rename interfaces and transform functions
- **`apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPositions.ts`** - Update type imports
- **`apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts`** - Update type imports and usages
- **`apps/orchestrator_3_stream/frontend/src/services/chatService.ts`** - Comment reference (minor)
- **`apps/orchestrator_3_stream/frontend/src/components/__tests__/OpenPositions.spec.ts`** - Update mock and type references
- **`apps/orchestrator_3_stream/frontend/src/components/__tests__/OpenPositions.integration.spec.ts`** - Update type references

### Backend Files to Update

- **`apps/orchestrator_3_stream/backend/modules/alpaca_models.py`** - Rename `IronCondorPosition` class
- **`apps/orchestrator_3_stream/backend/modules/alpaca_service.py`** - Update imports and usages
- **`apps/orchestrator_3_stream/backend/tests/test_alpaca_models.py`** - Update test class and imports
- **`apps/orchestrator_3_stream/backend/tests/test_alpaca_service.py`** - Update imports
- **`apps/orchestrator_3_stream/backend/tests/test_alpaca_endpoints.py`** - Update imports and usages

## Implementation Phases

### Phase 1: Backend Model Rename
Rename Python models first since they define the data structure.

### Phase 2: Frontend Type Rename
Rename TypeScript interfaces to match backend changes.

### Phase 3: Component Rename
Rename the Vue component file and update all imports.

### Phase 4: Test Updates
Update all test files to use new names.

## Step by Step Tasks

### 1. Rename Backend Pydantic Model (alpaca_models.py)

- Rename `IronCondorPosition` class to `OpenPosition`
- Add backwards-compatible alias: `IronCondorPosition = OpenPosition`
- Update docstrings to reflect the generic nature
- Update `__all__` exports to include `OpenPosition`
- Update `RawIronCondorPosition` references in comments

```python
# Before:
class IronCondorPosition(BaseModel):
    """Complete iron condor position with 4 legs."""

# After:
class OpenPosition(BaseModel):
    """
    Open position with any number of option legs.
    Supports various strategy types: Iron Condor, Vertical Spread, Straddle, Strangle, etc.
    """

# Backwards compatibility:
IronCondorPosition = OpenPosition
```

### 2. Update Backend Service (alpaca_service.py)

- Update import from `IronCondorPosition` to `OpenPosition`
- Update type hints throughout the file
- Keep using `OpenPosition` class name

```python
# Update imports:
from modules.alpaca_models import (
    ...
    OpenPosition,  # Changed from IronCondorPosition
    ...
)

# Update type hints:
self._positions_cache: Dict[str, OpenPosition] = {}
async def get_all_positions(self) -> List[OpenPosition]:
async def get_position_by_id(self, position_id: str) -> Optional[OpenPosition]:
def _group_by_ticker(self, positions: list) -> List[OpenPosition]:
```

### 3. Update Backend Tests

- **test_alpaca_models.py**:
  - Update import from `IronCondorPosition` to `OpenPosition`
  - Rename `TestIronCondorPosition` class to `TestOpenPosition`
  - Update all `IronCondorPosition(...)` instantiations to `OpenPosition(...)`

- **test_alpaca_service.py**:
  - Update import from `IronCondorPosition` to `OpenPosition`
  - Update type hints and assertions

- **test_alpaca_endpoints.py**:
  - Update import from `IronCondorPosition` to `OpenPosition`
  - Update sample position creation

### 4. Rename Frontend TypeScript Types (types/alpaca.ts)

- Rename `RawIronCondorPosition` → `RawOpenPosition`
- Rename `IronCondorPosition` → `OpenPosition`
- Add backwards-compatible aliases
- Update transform functions

```typescript
// Before:
export interface RawIronCondorPosition { ... }
export interface IronCondorPosition { ... }
export function transformPosition(raw: RawIronCondorPosition): IronCondorPosition

// After:
export interface RawOpenPosition { ... }
export interface OpenPosition { ... }
export function transformPosition(raw: RawOpenPosition): OpenPosition

// Backwards compatibility (keep existing):
export type TickerPosition = OpenPosition
export type IronCondorPosition = OpenPosition  // Add alias
export type RawIronCondorPosition = RawOpenPosition  // Add alias
```

### 5. Update Frontend Composable (useAlpacaPositions.ts)

- Update import from `IronCondorPosition` to `OpenPosition`
- Update type annotations
- Update JSDoc comments

```typescript
// Update import:
import type { OpenPosition } from '../types/alpaca'

// Update computed:
const currentPosition = computed<OpenPosition | null>(() => { ... })
```

### 6. Update Frontend Store (orchestratorStore.ts)

- Update import from `IronCondorPosition` to `OpenPosition`
- Update `alpacaPositions` ref type

```typescript
// Update import:
import type { OpenPosition, OptionPriceUpdate } from '../types/alpaca'

// Update state:
const alpacaPositions = ref<OpenPosition[]>([])
```

### 7. Rename Vue Component File

- Rename file: `IronCondorCard.vue` → `OpenPositionCard.vue`
- Update internal type imports to use `OpenPosition`

```bash
git mv apps/orchestrator_3_stream/frontend/src/components/IronCondorCard.vue \
       apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue
```

### 8. Update OpenPositions.vue Import

- Change import from `IronCondorCard` to `OpenPositionCard`

```typescript
// Before:
import IronCondorCard from './IronCondorCard.vue'

// After:
import OpenPositionCard from './OpenPositionCard.vue'
```

- Update template usage:

```vue
<!-- Before -->
<IronCondorCard v-for="position in positions" ... />

<!-- After -->
<OpenPositionCard v-for="position in positions" ... />
```

### 9. Update Frontend Tests

- **OpenPositions.spec.ts**:
  - Update import from `IronCondorPosition` to `OpenPosition`
  - Update mock for `IronCondorCard.vue` to `OpenPositionCard.vue`
  - Update any text assertions referencing "iron condor"

- **OpenPositions.integration.spec.ts**:
  - Update import from `IronCondorPosition` to `OpenPosition`
  - Update type annotations in test data

### 10. Validate All Changes

- Run TypeScript type checking
- Run frontend tests
- Run backend tests
- Verify application compiles and runs

## Testing Strategy

### Unit Tests
- Verify all existing tests pass after rename
- Ensure backwards-compatible aliases work correctly

### Type Checking
- Run `tsc --noEmit` to verify TypeScript compiles
- Run `uv run python -c "from modules.alpaca_models import OpenPosition, IronCondorPosition"` to verify Python imports

### Integration Tests
- Verify WebSocket price updates still work
- Verify positions display correctly in UI

## Acceptance Criteria

- [ ] `IronCondorCard.vue` renamed to `OpenPositionCard.vue`
- [ ] `IronCondorPosition` type renamed to `OpenPosition` (frontend and backend)
- [ ] `RawIronCondorPosition` type renamed to `RawOpenPosition` (frontend)
- [ ] All imports updated throughout codebase
- [ ] Backwards compatibility aliases exist (`IronCondorPosition = OpenPosition`)
- [ ] All frontend tests pass: `npm run test`
- [ ] All backend tests pass: `uv run pytest`
- [ ] TypeScript compiles without errors
- [ ] Application runs correctly with positions displaying

## Validation Commands

Execute these commands to validate the task is complete:

```bash
# 1. Verify component file renamed
ls -la apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue

# 2. Verify no remaining IronCondorCard.vue
ls apps/orchestrator_3_stream/frontend/src/components/IronCondorCard.vue 2>&1 | grep -q "No such file"

# 3. Run frontend type check
cd apps/orchestrator_3_stream/frontend && npm run type-check

# 4. Run frontend tests
cd apps/orchestrator_3_stream/frontend && npm run test

# 5. Verify Python imports work
cd apps/orchestrator_3_stream/backend && uv run python -c "from modules.alpaca_models import OpenPosition, IronCondorPosition; print('Import OK - OpenPosition:', OpenPosition, 'Alias:', IronCondorPosition)"

# 6. Run backend tests
cd apps/orchestrator_3_stream/backend && uv run pytest -v tests/test_alpaca_models.py tests/test_alpaca_service.py tests/test_alpaca_endpoints.py

# 7. Grep for any remaining "IronCondorCard" references (should only find aliases and comments)
grep -r "IronCondorCard" apps/orchestrator_3_stream --include="*.vue" --include="*.ts" --include="*.py" | grep -v "alias" | grep -v "#" | grep -v "//"
```

## Notes

- **Backwards Compatibility**: We maintain `IronCondorPosition` and `RawIronCondorPosition` as type aliases to avoid breaking any external code or documentation that references the old names.
- **TickerPosition Alias**: The existing `TickerPosition = IronCondorPosition` alias will now point to `OpenPosition` through the chain: `TickerPosition = IronCondorPosition = OpenPosition`
- **Spec Files**: Existing spec files in `specs/` reference `IronCondorPosition` extensively. These are documentation/plans and do NOT need updating - they serve as historical context.
- **Comment Updates**: Consider updating comments/docstrings that mention "iron condor" specifically when the context is about generic positions.

## File Change Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `IronCondorCard.vue` → `OpenPositionCard.vue` | Rename | Component file rename |
| `alpaca_models.py` | Edit | Rename class, add alias |
| `alpaca_service.py` | Edit | Update imports and types |
| `types/alpaca.ts` | Edit | Rename interfaces, add aliases |
| `useAlpacaPositions.ts` | Edit | Update imports and types |
| `orchestratorStore.ts` | Edit | Update imports and types |
| `OpenPositions.vue` | Edit | Update component import |
| `test_alpaca_models.py` | Edit | Update class name and imports |
| `test_alpaca_service.py` | Edit | Update imports |
| `test_alpaca_endpoints.py` | Edit | Update imports |
| `OpenPositions.spec.ts` | Edit | Update mocks and imports |
| `OpenPositions.integration.spec.ts` | Edit | Update types |

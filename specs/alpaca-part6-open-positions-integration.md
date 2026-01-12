# Part 6: OpenPositions.vue Integration

## Overview

**Scope:** Connect OpenPositions.vue to real Alpaca data using existing composables
**Dependencies:** Parts 1-5 (Models, Service, Endpoints, WebSocket, Frontend Integration)
**Estimated Time:** 1-2 hours

## Objectives

1. Replace hardcoded mock data in OpenPositions.vue with `useAlpacaPositions` composable
2. Add loading, error, and empty states following IronCondorCard patterns
3. Add refresh button for manual data reload
4. Ensure WebSocket price updates flow through the entire pipeline
5. Create Vitest test for OpenPositions.vue component

## Problem Statement

`OpenPositions.vue` currently displays **hardcoded mock data** instead of real Alpaca positions:

```vue
<!-- Current: Hardcoded mock data -->
const mockPositions = ref<PositionData[]>([
  {
    ticker: 'SPY',
    strategy: 'Iron Condor',
    expiryDate: '2026-01-17',
    legs: [...]
  },
  // More hardcoded positions...
])
```

The `useAlpacaPositions` composable was created in Part 5 and works correctly - it just isn't being used. This is the final step to complete the Alpaca integration.

## Solution Approach

1. **Replace mock data** - Remove local interfaces and hardcoded data, use composable instead
2. **Add UI states** - Implement loading spinner, error message with retry, and empty state
3. **Wire up IronCondorCard** - Pass `IronCondorPosition` objects from composable to cards
4. **Add refresh action** - Header button to manually reload positions
5. **Verify data flow** - Ensure WebSocket updates propagate through the component tree

### Data Flow (After Implementation)

```
Alpaca API → AlpacaService → REST Endpoint → useAlpacaPositions
                ↓ (WebSocket)
           WebSocketManager → chatService → orchestratorStore
                                                   ↓
                                           useAlpacaPositions
                                                   ↓
                                           OpenPositions.vue
                                                   ↓
                                           IronCondorCard.vue
```

## Relevant Files

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/OpenPositions.vue` | Replace mock data with composable |

### Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/components/__tests__/OpenPositions.spec.ts` | Component tests |

### Reference Files (Read-Only)

| File | Purpose |
|------|---------|
| `frontend/src/components/IronCondorCard.vue` | Example of composable integration |
| `frontend/src/composables/useAlpacaPositions.ts` | Composable to use |
| `frontend/src/types/alpaca.ts` | TypeScript types |
| `frontend/src/stores/orchestratorStore.ts` | State management |

## Implementation Phases

### Phase 1: Component Update

Remove hardcoded mock data and integrate with `useAlpacaPositions` composable. Add all necessary UI states.

### Phase 2: Testing

Create comprehensive Vitest tests covering all component states and user interactions.

### Phase 3: Validation

Verify end-to-end data flow from Alpaca API through WebSocket to UI updates.

## Step by Step Tasks

### 1. Update OpenPositions.vue - Script Section

**File:** `apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue`

Replace the entire `<script setup>` section:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { Loading, Warning, Refresh } from '@element-plus/icons-vue'
import IronCondorCard from './IronCondorCard.vue'
import { useAlpacaPositions } from '../composables/useAlpacaPositions'
import type { IronCondorPosition } from '../types/alpaca'

// Use the Alpaca positions composable
const {
  positions,
  loading,
  error,
  hasPositions,
  positionCount,
  refresh,
} = useAlpacaPositions({
  autoFetch: true,
  autoSubscribe: true,
})

// Computed for display
const displayCount = computed(() => {
  if (loading.value) return '...'
  return `${positionCount.value} position${positionCount.value !== 1 ? 's' : ''}`
})

// Refresh handler with loading feedback
const handleRefresh = async () => {
  await refresh()
}
</script>
```

**Key changes:**
- Remove local `PositionData` and `OptionLeg` interfaces (use `IronCondorPosition` from alpaca.ts)
- Remove `mockPositions` ref
- Import and use `useAlpacaPositions` composable
- Add `handleRefresh` for manual reload
- Add computed `displayCount` for header

### 2. Update OpenPositions.vue - Template Section

Replace the entire `<template>` section:

```vue
<template>
  <div class="open-positions">
    <!-- Header with refresh button -->
    <div class="open-positions-header">
      <h2>Open Positions</h2>
      <div class="header-actions">
        <el-button
          :icon="Refresh"
          circle
          size="small"
          :loading="loading"
          @click="handleRefresh"
          title="Refresh positions"
        />
        <span class="position-count">{{ displayCount }}</span>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && !hasPositions" class="state-container loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <span>Loading positions from Alpaca...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="state-container error-state">
      <el-icon :size="32"><Warning /></el-icon>
      <span class="error-message">{{ error }}</span>
      <el-button type="primary" size="small" @click="handleRefresh">
        Retry
      </el-button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!hasPositions" class="state-container empty-state">
      <span>No open iron condor positions</span>
      <el-button type="primary" size="small" @click="handleRefresh">
        Check Again
      </el-button>
    </div>

    <!-- Positions Grid -->
    <div v-else class="positions-grid">
      <IronCondorCard
        v-for="position in positions"
        :key="position.id"
        :initial-data="position"
      />
    </div>
  </div>
</template>
```

**Key changes:**
- Add refresh button in header with loading state
- Add loading state with spinner and message
- Add error state with retry button
- Add empty state with "Check Again" button
- Use `position.id` as key (instead of array index)
- Pass `initial-data` prop using proper `IronCondorPosition` type

### 3. Update OpenPositions.vue - Style Section

Add new styles for the states (keep existing styles, add these):

```vue
<style scoped>
.open-positions {
  height: 100%;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.open-positions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.open-positions-header h2 {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-primary);
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.position-count {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* State Containers */
.state-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 48px;
  color: var(--text-muted);
}

.loading-state .el-icon {
  color: var(--el-color-primary);
}

.error-state {
  color: var(--el-color-danger);
}

.error-state .error-message {
  max-width: 400px;
  text-align: center;
  line-height: 1.5;
}

.empty-state {
  color: var(--text-muted);
}

/* Positions Grid */
.positions-grid {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(900px, 1fr));
  grid-auto-rows: min-content;
  gap: 24px;
  align-content: start;
}

/* Responsive adjustments */
@media (max-width: 1400px) {
  .positions-grid {
    grid-template-columns: 1fr;
  }
}

/* Scrollbar styling */
.positions-grid::-webkit-scrollbar {
  width: 6px;
}

.positions-grid::-webkit-scrollbar-track {
  background: transparent;
}

.positions-grid::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.positions-grid::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.15);
}
</style>
```

### 4. Create Component Test

**File:** `apps/orchestrator_3_stream/frontend/src/components/__tests__/OpenPositions.spec.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { ref, computed } from 'vue'
import OpenPositions from '../OpenPositions.vue'

// Mock Element Plus components
vi.mock('element-plus', () => ({
  ElButton: {
    name: 'ElButton',
    template: '<button><slot /></button>',
    props: ['icon', 'circle', 'size', 'loading', 'type'],
  },
  ElIcon: {
    name: 'ElIcon',
    template: '<span class="el-icon"><slot /></span>',
    props: ['size'],
  },
}))

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  Loading: { name: 'Loading', template: '<span>Loading</span>' },
  Warning: { name: 'Warning', template: '<span>Warning</span>' },
  Refresh: { name: 'Refresh', template: '<span>Refresh</span>' },
}))

// Mock IronCondorCard
vi.mock('../IronCondorCard.vue', () => ({
  default: {
    name: 'IronCondorCard',
    props: ['initialData', 'positionId', 'useMockData'],
    template: '<div class="mock-iron-condor-card">{{ initialData?.ticker }}</div>',
  },
}))

// Mock useAlpacaPositions composable
const mockPositions = ref([])
const mockLoading = ref(false)
const mockError = ref(null)
const mockHasPositions = computed(() => mockPositions.value.length > 0)
const mockPositionCount = computed(() => mockPositions.value.length)
const mockRefresh = vi.fn()

vi.mock('../../composables/useAlpacaPositions', () => ({
  useAlpacaPositions: () => ({
    positions: mockPositions,
    loading: mockLoading,
    error: mockError,
    hasPositions: mockHasPositions,
    positionCount: mockPositionCount,
    refresh: mockRefresh,
  }),
}))

describe('OpenPositions.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockPositions.value = []
    mockLoading.value = false
    mockError.value = null
  })

  describe('Loading State', () => {
    it('should show loading state when loading and no positions', async () => {
      mockLoading.value = true
      mockPositions.value = []

      const wrapper = mount(OpenPositions)

      expect(wrapper.find('.loading-state').exists()).toBe(true)
      expect(wrapper.text()).toContain('Loading positions from Alpaca')
    })

    it('should show positions grid while refreshing with existing data', async () => {
      mockLoading.value = true
      mockPositions.value = [
        {
          id: 'test-1',
          ticker: 'SPY',
          strategy: 'Iron Condor',
          expiryDate: '2026-01-17',
          legs: [],
          createdAt: new Date().toISOString(),
        },
      ]

      const wrapper = mount(OpenPositions)

      // Should show grid, not loading state (background refresh)
      expect(wrapper.find('.loading-state').exists()).toBe(false)
      expect(wrapper.find('.positions-grid').exists()).toBe(true)
    })
  })

  describe('Error State', () => {
    it('should show error state with message', async () => {
      mockError.value = 'Failed to connect to Alpaca'

      const wrapper = mount(OpenPositions)

      expect(wrapper.find('.error-state').exists()).toBe(true)
      expect(wrapper.text()).toContain('Failed to connect to Alpaca')
    })

    it('should call refresh when retry button clicked', async () => {
      mockError.value = 'Network error'

      const wrapper = mount(OpenPositions)
      await wrapper.find('.error-state button').trigger('click')

      expect(mockRefresh).toHaveBeenCalled()
    })
  })

  describe('Empty State', () => {
    it('should show empty state when no positions', async () => {
      mockLoading.value = false
      mockError.value = null
      mockPositions.value = []

      const wrapper = mount(OpenPositions)

      expect(wrapper.find('.empty-state').exists()).toBe(true)
      expect(wrapper.text()).toContain('No open iron condor positions')
    })

    it('should call refresh when check again clicked', async () => {
      mockPositions.value = []

      const wrapper = mount(OpenPositions)
      await wrapper.find('.empty-state button').trigger('click')

      expect(mockRefresh).toHaveBeenCalled()
    })
  })

  describe('Positions Grid', () => {
    it('should render IronCondorCard for each position', async () => {
      mockPositions.value = [
        {
          id: 'pos-1',
          ticker: 'SPY',
          strategy: 'Iron Condor',
          expiryDate: '2026-01-17',
          legs: [],
          createdAt: new Date().toISOString(),
        },
        {
          id: 'pos-2',
          ticker: 'QQQ',
          strategy: 'Iron Butterfly',
          expiryDate: '2026-01-24',
          legs: [],
          createdAt: new Date().toISOString(),
        },
      ]

      const wrapper = mount(OpenPositions)

      const cards = wrapper.findAll('.mock-iron-condor-card')
      expect(cards).toHaveLength(2)
      expect(cards[0].text()).toBe('SPY')
      expect(cards[1].text()).toBe('QQQ')
    })

    it('should show correct position count in header', async () => {
      mockPositions.value = [
        { id: '1', ticker: 'SPY', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
        { id: '2', ticker: 'QQQ', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
        { id: '3', ticker: 'IWM', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
      ]

      const wrapper = mount(OpenPositions)

      expect(wrapper.find('.position-count').text()).toBe('3 positions')
    })

    it('should use singular "position" for count of 1', async () => {
      mockPositions.value = [
        { id: '1', ticker: 'SPY', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
      ]

      const wrapper = mount(OpenPositions)

      expect(wrapper.find('.position-count').text()).toBe('1 position')
    })
  })

  describe('Refresh Button', () => {
    it('should call refresh when header refresh button clicked', async () => {
      mockPositions.value = [
        { id: '1', ticker: 'SPY', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
      ]

      const wrapper = mount(OpenPositions)
      const refreshBtn = wrapper.find('.header-actions button')
      await refreshBtn.trigger('click')

      expect(mockRefresh).toHaveBeenCalled()
    })

    it('should show loading indicator during refresh', async () => {
      mockLoading.value = true
      mockPositions.value = [
        { id: '1', ticker: 'SPY', strategy: 'IC', expiryDate: '2026-01-17', legs: [], createdAt: '' },
      ]

      const wrapper = mount(OpenPositions)

      // The button should have loading prop
      expect(wrapper.find('.position-count').text()).toBe('...')
    })
  })
})
```

### 5. Verify IronCondorCard Props Compatibility

Ensure `IronCondorCard.vue` accepts the `initial-data` prop correctly:

**Current IronCondorCard props (from Part 5):**
```typescript
const props = defineProps<{
  positionId?: string
  initialData?: IronCondorPosition
  useMockData?: boolean
}>()
```

This is already compatible! The `initial-data` prop accepts `IronCondorPosition` which is exactly what `useAlpacaPositions` returns.

### 6. Verify Data Flow

After implementation, the data flow should work as follows:

1. **Initial Load:**
   ```
   OpenPositions mounts
   → useAlpacaPositions.autoFetch = true
   → fetchPositions() calls alpacaService.getPositions()
   → API returns positions
   → store.setAlpacaPositions(positions)
   → positions computed updates
   → OpenPositions re-renders with data
   → IronCondorCards receive initialData
   ```

2. **WebSocket Price Updates:**
   ```
   Alpaca WebSocket sends quote
   → Backend alpaca_service._handle_quote_update()
   → ws_manager.broadcast_option_price_update()
   → chatService receives message
   → store.updateAlpacaPrice() called
   → Price cache updated + leg.currentPrice updated
   → IronCondorCard's computed values recalculate
   → P/L displays update in real-time
   ```

3. **Manual Refresh:**
   ```
   User clicks refresh button
   → handleRefresh() calls refresh()
   → useAlpacaPositions.refresh() fetches from API
   → Positions array replaced in store
   → All cards re-render with fresh data
   ```

## Testing Strategy

### Unit Tests (Vitest)

1. **Loading state** - Shows spinner when loading, hides when data arrives
2. **Error state** - Shows error message with retry button
3. **Empty state** - Shows message when no positions
4. **Populated state** - Renders correct number of IronCondorCards
5. **Refresh button** - Calls refresh and shows loading indicator
6. **Position count** - Displays correct singular/plural text

### Integration Tests (Manual)

1. Start backend with Alpaca credentials configured
2. Start frontend and navigate to positions view
3. Verify positions load from Alpaca
4. Verify price updates appear in real-time
5. Test refresh button functionality
6. Test error handling (disconnect network, verify retry works)

## Acceptance Criteria

- [ ] OpenPositions.vue uses `useAlpacaPositions` composable (no mock data)
- [ ] Loading state displays while fetching positions
- [ ] Error state displays on API failure with retry button
- [ ] Empty state displays when no positions exist
- [ ] Refresh button triggers data reload with loading indicator
- [ ] Position count displays correctly (singular/plural)
- [ ] IronCondorCards render for each position with correct data
- [ ] WebSocket price updates flow through to IronCondorCards
- [ ] All Vitest tests pass for OpenPositions.vue
- [ ] TypeScript compiles without errors

## Validation Commands

```bash
# Navigate to frontend directory
cd apps/orchestrator_3_stream/frontend

# Type check
npm run build

# Run component tests
npm run test -- OpenPositions

# Run all frontend tests
npm run test

# Run tests with coverage
npm run test:coverage

# Start dev server and verify visually
npm run dev
```

### Manual Validation Checklist

```bash
# Terminal 1: Start backend
cd apps/orchestrator_3_stream/backend
uv run uvicorn main:app --host 127.0.0.1 --port 9403 --reload

# Terminal 2: Start frontend
cd apps/orchestrator_3_stream/frontend
npm run dev

# Open browser to frontend (typically http://localhost:5173)
# 1. Verify loading spinner appears initially
# 2. Verify positions load and display
# 3. Click refresh button - verify it works
# 4. Watch for real-time price updates
# 5. Disconnect network - verify error state appears
# 6. Reconnect and click Retry - verify recovery
```

## Notes

### Removing Mock Data

The original OpenPositions.vue had these local type definitions that should be removed:

```typescript
// REMOVE THESE - use types from alpaca.ts instead
interface OptionLeg {
  id: string
  direction: 'Long' | 'Short'
  // ...
}

interface PositionData {
  ticker: string
  strategy: string
  // ...
}

// REMOVE THIS - use composable instead
const mockPositions = ref<PositionData[]>([...])
```

### IronCondorCard Props

When passing data to IronCondorCard, use `initial-data` (kebab-case in template, camelCase in props):

```vue
<!-- Correct -->
<IronCondorCard :initial-data="position" />

<!-- Also works (explicit) -->
<IronCondorCard :initialData="position" />
```

### Background Refresh UX

The loading state only shows on initial load when there's no data. During refresh with existing data, the spinner appears in the header button but positions remain visible. This provides a better UX than blanking the screen during refresh.

### WebSocket Connection

The `useAlpacaPriceStream` composable handles WebSocket price updates automatically. When OpenPositions renders IronCondorCards, each card will:
1. Receive initial position data via `initial-data` prop
2. Subscribe to price updates via `useAlpacaPriceStream`
3. Update leg prices and P/L in real-time

No additional WebSocket handling is needed in OpenPositions.vue itself.

## Cross-Reference: File Dependencies Across Parts

This diagram shows how files created in each part relate to each other:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (Python/FastAPI)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Part 1: Pydantic Models                                                    │
│  └── modules/alpaca_models.py                                               │
│       ├── OCCSymbol (OCC parser)                                           │
│       ├── OptionLeg                                                        │
│       ├── IronCondorPosition                                               │
│       ├── OptionPriceUpdate                                                │
│       └── API Response Models                                              │
│            │                                                                │
│            ▼                                                                │
│  Part 2: Alpaca Service                                                     │
│  ├── modules/alpaca_service.py ───────────────────┐                        │
│  │    ├── AlpacaService                           │                        │
│  │    ├── TTLCache                                │                        │
│  │    └── init_alpaca_service()                   │                        │
│  └── modules/circuit_breaker.py                   │                        │
│       └── CircuitBreaker                          │                        │
│            │                                       │                        │
│            ▼                                       │                        │
│  Part 3: REST Endpoints                            │                        │
│  └── main.py                                       │                        │
│       ├── GET /api/positions                       │                        │
│       ├── GET /api/positions/{id}                  │                        │
│       ├── POST /api/positions/subscribe-prices     │                        │
│       └── GET /api/positions/circuit-status        │                        │
│            │                                       │                        │
│            │                                       │                        │
│  Part 4: WebSocket                                 │                        │
│  └── modules/ws_manager.py ◄──────────────────────┘                        │
│       └── broadcast_option_price_update()                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ REST API / WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Vue/TypeScript)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Part 5: Frontend Integration                                               │
│  ├── types/alpaca.ts ◄──────────────── (Mirrors Part 1 Pydantic models)    │
│  │    ├── IronCondorPosition                                               │
│  │    ├── OptionLeg                                                        │
│  │    └── OptionPriceUpdate                                                │
│  │         │                                                                │
│  │         ▼                                                                │
│  ├── composables/useAlpacaPositions.ts                                     │
│  │    └── Calls /api/positions (Part 3)                                    │
│  │         │                                                                │
│  ├── composables/useAlpacaPriceStream.ts                                   │
│  │    └── Receives WebSocket updates (Part 4)                              │
│  │         │                                                                │
│  └── stores/orchestratorStore.ts                                           │
│       ├── alpacaPositions state                                            │
│       └── updateAlpacaPrice() action                                       │
│            │                                                                │
│            ▼                                                                │
│  Part 6: OpenPositions.vue Integration (THIS PART)                          │
│  ├── components/OpenPositions.vue                                          │
│  │    └── Uses useAlpacaPositions composable                               │
│  │         │                                                                │
│  │         ▼                                                                │
│  └── components/IronCondorCard.vue                                         │
│       └── Displays position data with real-time prices                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Environment Variables Checklist

Before running the application, ensure the following environment variables are configured:

**Backend** (`apps/orchestrator_3_stream/backend/.env`):
```bash
# Required: Alpaca API Credentials
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here

# Optional: Trading mode (defaults to paper)
ALPACA_PAPER=true

# Optional: Data feed (defaults to 'iex')
ALPACA_DATA_FEED=iex

# Optional: Circuit breaker settings
ALPACA_CB_FAILURE_THRESHOLD=5     # Opens after N failures (default: 5)
ALPACA_CB_RECOVERY_TIMEOUT=60     # Seconds before retry (default: 60)

# Optional: Cache settings
ALPACA_PRICE_CACHE_TTL=300        # Price cache TTL in seconds (default: 300)
```

**Frontend** (`apps/orchestrator_3_stream/frontend/.env`):
```bash
# Optional: Price throttling (reduces re-render frequency)
VITE_ALPACA_PRICE_THROTTLE_MS=200  # Milliseconds between price updates (default: 200)
```

---

## WebSocket Reconnection Behavior

When the WebSocket connection is lost and re-established:

```
┌──────────────────────────────────────────────────────────────────┐
│                    WebSocket Reconnection Flow                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Connection Lost                                               │
│     └── chatService detects disconnect                           │
│         └── orchestratorStore.onAlpacaStatus('disconnected')     │
│             └── UI can show "Reconnecting..." indicator          │
│                                                                   │
│  2. Reconnection Attempt                                          │
│     └── chatService auto-reconnects (exponential backoff)        │
│         └── Connection re-established                             │
│                                                                   │
│  3. Connection Restored                                           │
│     └── chatService.onOpen()                                      │
│         └── orchestratorStore.onAlpacaStatus('connected')         │
│             └── Components can trigger refresh if needed          │
│                                                                   │
│  4. Price Subscriptions                                           │
│     └── Backend maintains subscription list                       │
│     └── Prices resume streaming automatically                     │
│     └── OR: Call useAlpacaPositions.refresh() to resync          │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

**Important:** After reconnection, the backend WebSocket manager maintains its subscription list. However, if positions changed during disconnect, calling `refresh()` ensures the UI has the latest data.

---

## Circuit Breaker Behavior

The AlpacaService uses a circuit breaker pattern (implemented in Part 2) to handle API failures gracefully:

### States

| State | Description | Behavior |
|-------|-------------|----------|
| **CLOSED** | Normal operation | All API calls go through |
| **OPEN** | After 5 consecutive failures | API calls blocked, returns cached data |
| **HALF_OPEN** | After recovery timeout (60s) | Allows one test call to check recovery |

### UI Impact

```typescript
// When circuit is OPEN, the API returns cached positions:
// - Response status: 'cached'
// - Positions may be stale
// - No error thrown (graceful degradation)

// The composable handles this automatically:
const { positions, error } = useAlpacaPositions()
// positions = cached data (may be stale)
// error = null (no error, just using cache)
```

### Testing Circuit Breaker

To manually test circuit breaker behavior:

```bash
# Check circuit status
curl http://localhost:9403/api/positions/circuit-status

# Response when closed:
# { "state": "closed", "failure_count": 0 }

# Response when open:
# { "state": "open", "failure_count": 5, "recovery_in_seconds": 45 }
```

---

## Extended Integration Tests

In addition to the unit tests, add these integration tests to verify the full data flow:

**File:** `apps/orchestrator_3_stream/frontend/src/components/__tests__/OpenPositions.integration.spec.ts`

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { nextTick } from 'vue'
import OpenPositions from '../OpenPositions.vue'
import { useOrchestratorStore } from '../../stores/orchestratorStore'

// NOTE: These tests require actual store implementation, not mocks
// They verify the reactive data flow from store → composable → component

describe('OpenPositions Integration', () => {
  let store: ReturnType<typeof useOrchestratorStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useOrchestratorStore()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Store → Component Data Flow', () => {
    it('should update IronCondorCard when store price changes', async () => {
      // Setup: Mount component with initial position
      const initialPosition = {
        id: 'test-pos-1',
        ticker: 'SPY',
        strategy: 'Iron Condor',
        expiryDate: '2026-01-17',
        legs: [
          {
            id: 'leg-1',
            symbol: 'SPY260117C00600000',
            direction: 'Short' as const,
            strike: 600,
            optionType: 'Call' as const,
            quantity: 1,
            entryPrice: 2.50,
            currentPrice: 2.50,  // Initial price
          },
        ],
        createdAt: new Date().toISOString(),
      }

      // Set initial position in store
      store.setAlpacaPositions([initialPosition])

      // Mount component (will use real composable connected to store)
      const wrapper = mount(OpenPositions)
      await flushPromises()

      // Verify initial render
      expect(wrapper.find('.positions-grid').exists()).toBe(true)

      // Simulate price update via store (as WebSocket would)
      store.updateAlpacaPrice({
        symbol: 'SPY260117C00600000',
        bid_price: 2.80,
        ask_price: 2.90,
        mid_price: 2.85,
        last_price: 2.85,
      })

      await nextTick()

      // Verify the leg's currentPrice was updated
      const updatedPosition = store.alpacaPositions[0]
      const updatedLeg = updatedPosition.legs.find(l => l.symbol === 'SPY260117C00600000')
      expect(updatedLeg?.currentPrice).toBe(2.85)
    })

    it('should handle rapid price updates without excessive re-renders', async () => {
      const position = {
        id: 'test-pos-1',
        ticker: 'SPY',
        strategy: 'Iron Condor',
        expiryDate: '2026-01-17',
        legs: [
          {
            id: 'leg-1',
            symbol: 'SPY260117C00600000',
            direction: 'Short' as const,
            strike: 600,
            optionType: 'Call' as const,
            quantity: 1,
            entryPrice: 2.50,
            currentPrice: 2.50,
          },
        ],
        createdAt: new Date().toISOString(),
      }

      store.setAlpacaPositions([position])
      const wrapper = mount(OpenPositions)
      await flushPromises()

      // Track render count via spy
      const renderSpy = vi.fn()
      wrapper.vm.$watch(() => wrapper.vm, renderSpy, { deep: true })

      // Simulate 10 rapid price updates
      for (let i = 0; i < 10; i++) {
        store.updateAlpacaPrice({
          symbol: 'SPY260117C00600000',
          bid_price: 2.50 + (i * 0.01),
          ask_price: 2.60 + (i * 0.01),
          mid_price: 2.55 + (i * 0.01),
          last_price: 2.55 + (i * 0.01),
        })
      }

      await flushPromises()

      // Final price should be the last update
      const finalLeg = store.alpacaPositions[0].legs[0]
      expect(finalLeg.currentPrice).toBeCloseTo(2.64, 2)
    })
  })

  describe('Circuit Breaker Handling', () => {
    it('should display cached data when circuit is open', async () => {
      // Setup cached position
      const cachedPosition = {
        id: 'cached-1',
        ticker: 'QQQ',
        strategy: 'Iron Condor',
        expiryDate: '2026-02-21',
        legs: [],
        createdAt: new Date().toISOString(),
      }

      store.setAlpacaPositions([cachedPosition])

      // Mock the fetch to simulate circuit open (returns cached data)
      vi.spyOn(global, 'fetch').mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'cached',  // Indicates circuit breaker returned cached data
          positions: [cachedPosition],
          message: 'Using cached data - circuit breaker open',
        }),
      } as Response)

      const wrapper = mount(OpenPositions)
      await flushPromises()

      // Should still show the cached position, not an error
      expect(wrapper.find('.positions-grid').exists()).toBe(true)
      expect(wrapper.find('.error-state').exists()).toBe(false)
    })

    it('should recover and fetch fresh data when circuit closes', async () => {
      const stalePosition = {
        id: 'stale-1',
        ticker: 'SPY',
        strategy: 'Iron Condor',
        expiryDate: '2026-01-17',
        legs: [],
        createdAt: new Date().toISOString(),
      }

      const freshPosition = {
        id: 'fresh-1',
        ticker: 'SPY',
        strategy: 'Iron Condor',
        expiryDate: '2026-01-17',
        legs: [
          {
            id: 'new-leg',
            symbol: 'SPY260117C00605000',
            direction: 'Short' as const,
            strike: 605,
            optionType: 'Call' as const,
            quantity: 1,
            entryPrice: 3.00,
            currentPrice: 3.00,
          },
        ],
        createdAt: new Date().toISOString(),
      }

      // Start with stale cached data
      store.setAlpacaPositions([stalePosition])

      // Mock fetch to return fresh data (circuit recovered)
      vi.spyOn(global, 'fetch').mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'success',
          positions: [freshPosition],
        }),
      } as Response)

      const wrapper = mount(OpenPositions)

      // Trigger refresh
      await wrapper.find('.header-actions button').trigger('click')
      await flushPromises()

      // Should now have fresh position with leg
      expect(store.alpacaPositions[0].legs).toHaveLength(1)
    })
  })
})
```

---

## Summary

This is the **final step** in the Alpaca integration. After completing Part 6:

| Part | Status | Description |
|------|--------|-------------|
| Part 1 | Complete | Pydantic models for positions and prices |
| Part 2 | Complete | AlpacaService with REST and WebSocket |
| Part 3 | Complete | REST API endpoints |
| Part 4 | Complete | WebSocket price streaming |
| Part 5 | Complete | Frontend types, composables, store |
| **Part 6** | **THIS** | **OpenPositions.vue integration** |

After Part 6, the full data flow is complete:
```
Alpaca API → Backend → WebSocket → Frontend Store → Composables → Components
```

Real-time option prices will flow from Alpaca's market data feed directly to the IronCondorCard display.

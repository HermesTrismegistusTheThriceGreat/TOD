# Part 5: Frontend Integration

## Overview

**Scope:** Integrate IronCondorCard with Alpaca data via composables and store
**Dependencies:** Parts 1-4
**Estimated Time:** 3-4 hours

## Objectives

1. Create TypeScript interfaces with Raw* types for snake_case transformation
2. Fix Vue Map reactivity with `shallowRef(new Map())` + `triggerRef`
3. Register WebSocket handlers in orchestrator store
4. Create composables that integrate with WebSocket
5. Add Vitest test framework
6. Add error/loading states to component template

## Review Feedback Addressed

| Issue | Severity | Fix |
|-------|----------|-----|
| TypeScript interfaces use camelCase but backend sends snake_case | BLOCKER | Add Raw* types + transform functions |
| Vue Map reactivity doesn't work with `.set()` | BLOCKER | Use `shallowRef(new Map())` + `triggerRef` |
| WebSocket handlers not registered in store | HIGH | Register in store WebSocket setup |
| Composable doesn't integrate with WebSocket | HIGH | Connect composables to store |
| Frontend has no test framework | HIGH | Add Vitest |
| Missing error/loading states in template | MEDIUM | Add loading/error UI states |

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `frontend/src/types/alpaca.ts` | TypeScript interfaces with Raw* types |
| `frontend/src/services/alpacaService.ts` | REST API client |
| `frontend/src/composables/useAlpacaPositions.ts` | Position management |
| `frontend/src/composables/useAlpacaPriceStream.ts` | Price streaming |
| `frontend/vitest.config.ts` | Vitest configuration |
| `frontend/src/composables/__tests__/useAlpacaPositions.spec.ts` | Tests |

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/stores/orchestratorStore.ts` | Add Alpaca state + WebSocket handlers |
| `frontend/src/components/IronCondorCard.vue` | Integrate with composables |
| `frontend/package.json` | Add Vitest dependency |

## Implementation Steps

### Step 1: Create TypeScript Types with Raw* Pattern

**File:** `apps/orchestrator_3_stream/frontend/src/types/alpaca.ts`

```typescript
/**
 * Alpaca Trading API TypeScript Interfaces
 *
 * Pattern: Raw* types match backend snake_case, then transform to camelCase.
 * This solves the snake_case → camelCase mismatch between Python and TypeScript.
 */

// ═══════════════════════════════════════════════════════════
// RAW TYPES (Backend snake_case)
// ═══════════════════════════════════════════════════════════

/** Raw option leg from backend (snake_case) */
export interface RawOptionLeg {
  id: string
  symbol: string
  direction: 'Long' | 'Short'
  strike: number
  option_type: 'Call' | 'Put'
  quantity: number
  entry_price: number
  current_price: number
  expiry_date: string
  underlying: string
  pnl_dollars?: number
  pnl_percent?: number
}

/** Raw iron condor position from backend (snake_case) */
export interface RawIronCondorPosition {
  id: string
  ticker: string
  strategy: string
  expiry_date: string
  legs: RawOptionLeg[]
  created_at: string
  total_pnl?: number
  days_to_expiry?: number
}

/** Raw price update from backend (snake_case) */
export interface RawOptionPriceUpdate {
  symbol: string
  bid_price: number
  ask_price: number
  mid_price: number
  last_price?: number
  volume: number
  timestamp: string
}

/** Raw API response for positions */
export interface RawGetPositionsResponse {
  status: 'success' | 'error'
  positions: RawIronCondorPosition[]
  total_count: number
  message?: string
}

/** Raw API response for single position */
export interface RawGetPositionResponse {
  status: 'success' | 'error'
  position?: RawIronCondorPosition
  message?: string
}

// ═══════════════════════════════════════════════════════════
// FRONTEND TYPES (camelCase)
// ═══════════════════════════════════════════════════════════

/** Option leg (frontend camelCase) */
export interface OptionLeg {
  id: string
  symbol: string
  direction: 'Long' | 'Short'
  strike: number
  optionType: 'Call' | 'Put'
  quantity: number
  entryPrice: number
  currentPrice: number
  expiryDate: string
  underlying: string
  pnlDollars?: number
  pnlPercent?: number
}

/** Iron condor position (frontend camelCase) */
export interface IronCondorPosition {
  id: string
  ticker: string
  strategy: string
  expiryDate: string
  legs: OptionLeg[]
  createdAt: string
  totalPnl?: number
  daysToExpiry?: number
}

/** Option price update (frontend camelCase) */
export interface OptionPriceUpdate {
  symbol: string
  bidPrice: number
  askPrice: number
  midPrice: number
  lastPrice?: number
  volume: number
  timestamp: string
}

/** API response for positions (frontend) */
export interface GetPositionsResponse {
  status: 'success' | 'error'
  positions: IronCondorPosition[]
  totalCount: number
  message?: string
}

/** API response for single position (frontend) */
export interface GetPositionResponse {
  status: 'success' | 'error'
  position?: IronCondorPosition
  message?: string
}

/** Request for subscribing to prices */
export interface SubscribePricesRequest {
  symbols: string[]
}

// ═══════════════════════════════════════════════════════════
// TRANSFORM FUNCTIONS (snake_case → camelCase)
// ═══════════════════════════════════════════════════════════

/**
 * Transform raw option leg from backend to frontend format.
 */
export function transformOptionLeg(raw: RawOptionLeg): OptionLeg {
  return {
    id: raw.id,
    symbol: raw.symbol,
    direction: raw.direction,
    strike: raw.strike,
    optionType: raw.option_type,
    quantity: raw.quantity,
    entryPrice: raw.entry_price,
    currentPrice: raw.current_price,
    expiryDate: raw.expiry_date,
    underlying: raw.underlying,
    pnlDollars: raw.pnl_dollars,
    pnlPercent: raw.pnl_percent,
  }
}

/**
 * Transform raw position from backend to frontend format.
 */
export function transformPosition(raw: RawIronCondorPosition): IronCondorPosition {
  return {
    id: raw.id,
    ticker: raw.ticker,
    strategy: raw.strategy,
    expiryDate: raw.expiry_date,
    legs: raw.legs.map(transformOptionLeg),
    createdAt: raw.created_at,
    totalPnl: raw.total_pnl,
    daysToExpiry: raw.days_to_expiry,
  }
}

/**
 * Transform raw price update from backend to frontend format.
 */
export function transformPriceUpdate(raw: RawOptionPriceUpdate): OptionPriceUpdate {
  return {
    symbol: raw.symbol,
    bidPrice: raw.bid_price,
    askPrice: raw.ask_price,
    midPrice: raw.mid_price,
    lastPrice: raw.last_price,
    volume: raw.volume,
    timestamp: raw.timestamp,
  }
}

/**
 * Transform raw positions response from backend.
 */
export function transformPositionsResponse(raw: RawGetPositionsResponse): GetPositionsResponse {
  return {
    status: raw.status,
    positions: raw.positions.map(transformPosition),
    totalCount: raw.total_count,
    message: raw.message,
  }
}

/**
 * Transform raw position response from backend.
 */
export function transformPositionResponse(raw: RawGetPositionResponse): GetPositionResponse {
  return {
    status: raw.status,
    position: raw.position ? transformPosition(raw.position) : undefined,
    message: raw.message,
  }
}

// ═══════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════

/**
 * Calculate P/L for a leg (for local recalculation after price updates)
 */
export function calculateLegPnl(leg: OptionLeg): { dollars: number; percent: number } {
  const multiplier = leg.direction === 'Short' ? 1 : -1
  const priceDiff = (leg.entryPrice - leg.currentPrice) * multiplier
  const dollars = priceDiff * leg.quantity * 100

  let percent = 0
  if (leg.entryPrice !== 0) {
    const directionMult = leg.direction === 'Short' ? -1 : 1
    percent = ((leg.currentPrice - leg.entryPrice) / leg.entryPrice) * 100 * directionMult
  }

  return { dollars, percent }
}

/**
 * Extract all option symbols from positions for price subscription.
 */
export function extractSymbolsFromPositions(positions: IronCondorPosition[]): string[] {
  const symbols: string[] = []

  for (const position of positions) {
    for (const leg of position.legs) {
      if (leg.symbol && !symbols.includes(leg.symbol)) {
        symbols.push(leg.symbol)
      }
    }
  }

  return symbols
}
```

### Step 2: Create Alpaca REST Service

**File:** `apps/orchestrator_3_stream/frontend/src/services/alpacaService.ts`

```typescript
/**
 * Alpaca REST API Service
 *
 * Client for Alpaca trading endpoints.
 */

import { apiClient } from './api'
import type {
  RawGetPositionsResponse,
  RawGetPositionResponse,
  GetPositionsResponse,
  GetPositionResponse,
  SubscribePricesRequest,
  IronCondorPosition,
} from '../types/alpaca'
import {
  transformPositionsResponse,
  transformPositionResponse,
} from '../types/alpaca'

/**
 * Fetch all iron condor positions from Alpaca.
 */
export async function getPositions(): Promise<GetPositionsResponse> {
  const response = await apiClient.get<RawGetPositionsResponse>('/api/positions')
  return transformPositionsResponse(response.data)
}

/**
 * Fetch a specific position by ID.
 */
export async function getPositionById(positionId: string): Promise<GetPositionResponse> {
  const response = await apiClient.get<RawGetPositionResponse>(`/api/positions/${positionId}`)
  return transformPositionResponse(response.data)
}

/**
 * Subscribe to real-time price updates for option symbols.
 */
export async function subscribePrices(symbols: string[]): Promise<void> {
  await apiClient.post('/api/positions/subscribe-prices', {
    symbols
  } as SubscribePricesRequest)
}

/**
 * Get circuit breaker status.
 */
export async function getCircuitStatus(): Promise<{
  status: string
  circuit_state: string
  is_configured: boolean
}> {
  const response = await apiClient.get('/api/positions/circuit-status')
  return response.data
}
```

### Step 3: Update Orchestrator Store with Alpaca State

**File:** `apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts`

Add imports at top:

```typescript
import { shallowRef, triggerRef } from 'vue'
import type { IronCondorPosition, OptionPriceUpdate } from '../types/alpaca'
import { transformPosition, transformPriceUpdate } from '../types/alpaca'
```

Add state after existing state declarations (around line 100):

```typescript
  // ═══════════════════════════════════════════════════════════
  // ALPACA POSITION STATE
  // ═══════════════════════════════════════════════════════════

  // Positions list
  const alpacaPositions = ref<IronCondorPosition[]>([])

  // Price cache using shallowRef for proper Map reactivity
  // IMPORTANT: Use shallowRef + triggerRef for Map reactivity
  const alpacaPriceCache = shallowRef<Map<string, OptionPriceUpdate>>(new Map())

  // Loading and error states
  const alpacaPositionsLoading = ref<boolean>(false)
  const alpacaPositionsError = ref<string | null>(null)

  // Alpaca connection status
  const alpacaConnectionStatus = ref<'connected' | 'disconnected' | 'error'>('disconnected')
```

Add computed getters:

```typescript
  // ═══════════════════════════════════════════════════════════
  // ALPACA GETTERS
  // ═══════════════════════════════════════════════════════════

  const hasAlpacaPositions = computed(() => alpacaPositions.value.length > 0)

  const alpacaPositionCount = computed(() => alpacaPositions.value.length)

  // Get a specific position by ID
  const getAlpacaPositionById = computed(() => {
    return (id: string) => alpacaPositions.value.find(p => p.id === id)
  })

  // Get cached price for a symbol
  const getAlpacaPrice = computed(() => {
    return (symbol: string) => alpacaPriceCache.value.get(symbol)
  })
```

Add actions:

```typescript
  // ═══════════════════════════════════════════════════════════
  // ALPACA ACTIONS
  // ═══════════════════════════════════════════════════════════

  /**
   * Set positions from API response.
   */
  function setAlpacaPositions(positions: IronCondorPosition[]) {
    alpacaPositions.value = positions
  }

  /**
   * Update a single option price in the cache.
   * Uses triggerRef for proper Map reactivity.
   */
  function updateAlpacaPrice(symbol: string, update: OptionPriceUpdate) {
    // Set in map
    alpacaPriceCache.value.set(symbol, update)

    // CRITICAL: Trigger reactivity for shallowRef Map
    triggerRef(alpacaPriceCache)

    // Update currentPrice in all matching legs
    for (const position of alpacaPositions.value) {
      for (const leg of position.legs) {
        if (leg.symbol === symbol) {
          leg.currentPrice = update.midPrice

          // Recalculate P/L
          const multiplier = leg.direction === 'Short' ? 1 : -1
          const priceDiff = (leg.entryPrice - leg.currentPrice) * multiplier
          leg.pnlDollars = priceDiff * leg.quantity * 100

          if (leg.entryPrice !== 0) {
            const dirMult = leg.direction === 'Short' ? -1 : 1
            leg.pnlPercent = ((leg.currentPrice - leg.entryPrice) / leg.entryPrice) * 100 * dirMult
          }
        }
      }
    }
  }

  /**
   * Update batch of prices.
   */
  function updateAlpacaPriceBatch(updates: OptionPriceUpdate[]) {
    for (const update of updates) {
      alpacaPriceCache.value.set(update.symbol, update)
    }
    // Single trigger for batch
    triggerRef(alpacaPriceCache)

    // Update legs
    for (const update of updates) {
      for (const position of alpacaPositions.value) {
        for (const leg of position.legs) {
          if (leg.symbol === update.symbol) {
            leg.currentPrice = update.midPrice
          }
        }
      }
    }
  }

  /**
   * Set Alpaca loading state.
   */
  function setAlpacaLoading(loading: boolean) {
    alpacaPositionsLoading.value = loading
  }

  /**
   * Set Alpaca error state.
   */
  function setAlpacaError(error: string | null) {
    alpacaPositionsError.value = error
  }

  /**
   * Clear Alpaca price cache.
   */
  function clearAlpacaPriceCache() {
    alpacaPriceCache.value.clear()
    triggerRef(alpacaPriceCache)
  }

  /**
   * Update Alpaca connection status.
   */
  function setAlpacaConnectionStatus(status: 'connected' | 'disconnected' | 'error') {
    alpacaConnectionStatus.value = status
  }
```

Update `connectWebSocket` to include Alpaca handlers (in the callbacks object):

```typescript
    // In connectWebSocket function, add to callbacks object:

    onOptionPriceUpdate: (message: any) => {
      if (message.update) {
        const update = transformPriceUpdate(message.update)
        updateAlpacaPrice(update.symbol, update)
      }
    },

    onOptionPriceBatch: (message: any) => {
      if (message.updates) {
        const updates = message.updates.map(transformPriceUpdate)
        updateAlpacaPriceBatch(updates)
      }
    },

    onPositionUpdate: (message: any) => {
      if (message.position) {
        const position = transformPosition(message.position)
        const index = alpacaPositions.value.findIndex(p => p.id === position.id)
        if (index >= 0) {
          alpacaPositions.value[index] = position
        } else {
          alpacaPositions.value.push(position)
        }
      }
    },

    onAlpacaStatus: (message: any) => {
      if (message.status) {
        setAlpacaConnectionStatus(message.status)
      }
    },
```

Add to the return statement:

```typescript
  return {
    // ... existing returns ...

    // Alpaca state
    alpacaPositions,
    alpacaPriceCache,
    alpacaPositionsLoading,
    alpacaPositionsError,
    alpacaConnectionStatus,

    // Alpaca getters
    hasAlpacaPositions,
    alpacaPositionCount,
    getAlpacaPositionById,
    getAlpacaPrice,

    // Alpaca actions
    setAlpacaPositions,
    updateAlpacaPrice,
    updateAlpacaPriceBatch,
    setAlpacaLoading,
    setAlpacaError,
    clearAlpacaPriceCache,
    setAlpacaConnectionStatus,
  }
```

### Step 4: Create useAlpacaPositions Composable

**File:** `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPositions.ts`

```typescript
/**
 * useAlpacaPositions Composable
 *
 * Manages fetching and state of iron condor positions.
 * Integrates with orchestrator store for WebSocket updates.
 */

import { ref, computed, onMounted, watch } from 'vue'
import { useOrchestratorStore } from '../stores/orchestratorStore'
import type { IronCondorPosition } from '../types/alpaca'
import { extractSymbolsFromPositions } from '../types/alpaca'
import * as alpacaService from '../services/alpacaService'

export interface UseAlpacaPositionsOptions {
  /** Auto-fetch positions on mount */
  autoFetch?: boolean
  /** Auto-subscribe to price updates after fetching */
  autoSubscribe?: boolean
  /** Specific position ID to fetch (for single position view) */
  positionId?: string
}

export function useAlpacaPositions(options: UseAlpacaPositionsOptions = {}) {
  const {
    autoFetch = true,
    autoSubscribe = true,
    positionId = undefined
  } = options

  const store = useOrchestratorStore()

  // Local state
  const isSubscribed = ref(false)
  const localError = ref<string | null>(null)

  // Computed from store
  const positions = computed(() => store.alpacaPositions)
  const loading = computed(() => store.alpacaPositionsLoading)
  const error = computed(() => store.alpacaPositionsError || localError.value)
  const hasPositions = computed(() => store.hasAlpacaPositions)
  const positionCount = computed(() => store.alpacaPositionCount)

  // Get current position (for single position mode)
  const currentPosition = computed<IronCondorPosition | null>(() => {
    if (positionId) {
      return store.getAlpacaPositionById(positionId) || null
    }
    return positions.value.length > 0 ? positions.value[0] : null
  })

  /**
   * Fetch all positions from Alpaca API.
   */
  async function fetchPositions(): Promise<void> {
    store.setAlpacaLoading(true)
    store.setAlpacaError(null)
    localError.value = null

    try {
      const response = await alpacaService.getPositions()

      if (response.status === 'error') {
        throw new Error(response.message || 'Failed to fetch positions')
      }

      store.setAlpacaPositions(response.positions)

      // Auto-subscribe to price updates
      if (autoSubscribe && response.positions.length > 0) {
        await subscribeToUpdates()
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to fetch positions'
      store.setAlpacaError(message)
      console.error('useAlpacaPositions.fetchPositions error:', e)
    } finally {
      store.setAlpacaLoading(false)
    }
  }

  /**
   * Fetch a specific position by ID.
   */
  async function fetchPosition(id: string): Promise<void> {
    store.setAlpacaLoading(true)
    store.setAlpacaError(null)

    try {
      const response = await alpacaService.getPositionById(id)

      if (response.status === 'error') {
        throw new Error(response.message || 'Failed to fetch position')
      }

      if (response.position) {
        // Add or update in positions array
        const index = store.alpacaPositions.findIndex(p => p.id === id)
        if (index >= 0) {
          store.alpacaPositions[index] = response.position
        } else {
          store.alpacaPositions.push(response.position)
        }

        // Subscribe to price updates for this position
        if (autoSubscribe) {
          const symbols = extractSymbolsFromPositions([response.position])
          await alpacaService.subscribePrices(symbols)
          isSubscribed.value = true
        }
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to fetch position'
      store.setAlpacaError(message)
      console.error('useAlpacaPositions.fetchPosition error:', e)
    } finally {
      store.setAlpacaLoading(false)
    }
  }

  /**
   * Subscribe to price updates for all position symbols.
   */
  async function subscribeToUpdates(): Promise<void> {
    if (isSubscribed.value) return

    try {
      const symbols = extractSymbolsFromPositions(positions.value)

      if (symbols.length > 0) {
        await alpacaService.subscribePrices(symbols)
        isSubscribed.value = true
        console.log(`Subscribed to ${symbols.length} option symbols`)
      }
    } catch (e) {
      console.error('Failed to subscribe to price updates:', e)
      // Non-critical error, don't set error state
    }
  }

  /**
   * Refresh positions (re-fetch from API).
   */
  async function refresh(): Promise<void> {
    if (positionId) {
      await fetchPosition(positionId)
    } else {
      await fetchPositions()
    }
  }

  /**
   * Get cached price for a symbol.
   */
  function getCachedPrice(symbol: string) {
    return store.getAlpacaPrice(symbol)
  }

  // Lifecycle
  onMounted(() => {
    if (autoFetch) {
      if (positionId) {
        fetchPosition(positionId)
      } else {
        fetchPositions()
      }
    }
  })

  return {
    // State
    positions,
    currentPosition,
    loading,
    error,
    isSubscribed,

    // Computed
    hasPositions,
    positionCount,

    // Actions
    fetchPositions,
    fetchPosition,
    subscribeToUpdates,
    refresh,
    getCachedPrice,
  }
}
```

### Step 5: Create useAlpacaPriceStream Composable

**File:** `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPriceStream.ts`

```typescript
/**
 * useAlpacaPriceStream Composable
 *
 * Provides access to real-time price updates from WebSocket.
 * Works with orchestrator store for centralized state.
 */

import { computed, watch, onUnmounted } from 'vue'
import { useOrchestratorStore } from '../stores/orchestratorStore'
import type { OptionPriceUpdate } from '../types/alpaca'

export interface PriceStreamCallbacks {
  onPriceUpdate?: (update: OptionPriceUpdate) => void
}

export function useAlpacaPriceStream(callbacks: PriceStreamCallbacks = {}) {
  const store = useOrchestratorStore()

  // Computed from store
  const priceCache = computed(() => store.alpacaPriceCache)
  const connectionStatus = computed(() => store.alpacaConnectionStatus)

  /**
   * Get the latest price for a symbol.
   */
  function getPrice(symbol: string): OptionPriceUpdate | undefined {
    return store.getAlpacaPrice(symbol)
  }

  /**
   * Get the mid price for a symbol (for display).
   */
  function getMidPrice(symbol: string): number | undefined {
    return store.getAlpacaPrice(symbol)?.midPrice
  }

  /**
   * Watch for price updates and call callback.
   */
  if (callbacks.onPriceUpdate) {
    watch(
      () => store.alpacaPriceCache,
      () => {
        // This is triggered by triggerRef in the store
        // We could track individual updates, but for now
        // the callback can check the cache directly
      },
      { deep: false }
    )
  }

  /**
   * Get all cached prices.
   */
  function getAllPrices(): Map<string, OptionPriceUpdate> {
    return priceCache.value
  }

  /**
   * Check if we have a cached price for a symbol.
   */
  function hasPrice(symbol: string): boolean {
    return priceCache.value.has(symbol)
  }

  return {
    // State
    priceCache,
    connectionStatus,

    // Methods
    getPrice,
    getMidPrice,
    getAllPrices,
    hasPrice,
  }
}
```

### Step 6: Update IronCondorCard Component

**File:** `apps/orchestrator_3_stream/frontend/src/components/IronCondorCard.vue`

Update the `<script setup>` section with loading/error states:

```vue
<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Timer, Loading, Warning } from '@element-plus/icons-vue'
import { useAlpacaPositions } from '../composables/useAlpacaPositions'
import { useAlpacaPriceStream } from '../composables/useAlpacaPriceStream'
import type { OptionLeg, IronCondorPosition } from '../types/alpaca'
import { calculateLegPnl } from '../types/alpaca'

// Props
const props = defineProps<{
  positionId?: string
  initialData?: IronCondorPosition
  /** Use mock data (for development/demo) */
  useMockData?: boolean
}>()

// Composables
const {
  positions,
  currentPosition,
  loading,
  error,
  hasPositions,
  refresh,
  getCachedPrice,
} = useAlpacaPositions({
  autoFetch: !props.useMockData && !props.initialData,
  autoSubscribe: !props.useMockData,
  positionId: props.positionId,
})

const { getMidPrice, connectionStatus } = useAlpacaPriceStream()

// Local state
const position = ref<IronCondorPosition | null>(null)

// Mock data for development
const mockPosition: IronCondorPosition = {
  id: 'mock-1',
  ticker: 'SPY',
  strategy: 'Iron Condor',
  expiryDate: '2026-01-17',
  createdAt: new Date().toISOString(),
  legs: [
    {
      id: '1',
      symbol: 'SPY260117C00695000',
      direction: 'Short',
      strike: 695,
      optionType: 'Call',
      quantity: 10,
      entryPrice: 4.04,
      currentPrice: 3.25,
      expiryDate: '2026-01-17',
      underlying: 'SPY'
    },
    {
      id: '2',
      symbol: 'SPY260117C00700000',
      direction: 'Long',
      strike: 700,
      optionType: 'Call',
      quantity: 10,
      entryPrice: 0.53,
      currentPrice: 0.09,
      expiryDate: '2026-01-17',
      underlying: 'SPY'
    },
    {
      id: '3',
      symbol: 'SPY260117P00680000',
      direction: 'Long',
      strike: 680,
      optionType: 'Put',
      quantity: 10,
      entryPrice: 1.47,
      currentPrice: 0.53,
      expiryDate: '2026-01-17',
      underlying: 'SPY'
    },
    {
      id: '4',
      symbol: 'SPY260117P00685000',
      direction: 'Short',
      strike: 685,
      optionType: 'Put',
      quantity: 10,
      entryPrice: 2.90,
      currentPrice: 1.57,
      expiryDate: '2026-01-17',
      underlying: 'SPY'
    },
  ]
}

// Watch for position changes
watch([currentPosition, positions], () => {
  if (props.initialData) {
    position.value = props.initialData
  } else if (props.useMockData) {
    position.value = mockPosition
  } else if (currentPosition.value) {
    position.value = currentPosition.value
  } else if (positions.value.length > 0) {
    position.value = positions.value[0]
  }
}, { immediate: true })

// Update prices from WebSocket cache
watch(
  () => [position.value, getMidPrice],
  () => {
    if (!position.value) return

    for (const leg of position.value.legs) {
      const price = getMidPrice(leg.symbol)
      if (price !== undefined) {
        leg.currentPrice = price
        const pnl = calculateLegPnl(leg)
        leg.pnlDollars = pnl.dollars
        leg.pnlPercent = pnl.percent
      }
    }
  },
  { deep: true }
)

// Computed values
const daysToExpiry = computed(() => {
  if (!position.value) return 0
  const expiry = new Date(position.value.expiryDate)
  const today = new Date()
  return Math.max(0, Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)))
})

const totalPnL = computed(() => {
  if (!position.value) return 0
  return position.value.legs.reduce((sum, leg) => {
    const pnl = calculateLegPnl(leg)
    return sum + pnl.dollars
  }, 0)
})

const sortedLegs = computed(() => {
  if (!position.value) return []
  const legs = [...position.value.legs]

  const calls = legs.filter(l => l.optionType === 'Call')
  const puts = legs.filter(l => l.optionType === 'Put')

  // Sort Calls: Short then Long (by strike descending)
  calls.sort((a, b) => {
    if (a.direction === 'Short' && b.direction === 'Long') return -1
    if (a.direction === 'Long' && b.direction === 'Short') return 1
    return b.strike - a.strike
  })

  // Sort Puts: Short then Long (by strike descending)
  puts.sort((a, b) => {
    if (a.direction === 'Short' && b.direction === 'Long') return -1
    if (a.direction === 'Long' && b.direction === 'Short') return 1
    return b.strike - a.strike
  })

  return [...calls, ...puts]
})

// Helpers
const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

const formatCurrency = (value: number) => {
  return `${value >= 0 ? '+' : ''}$${Math.abs(value).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  })}`
}

const formatPercent = (value: number) => {
  return `(${value >= 0 ? '+' : ''}${value.toFixed(2)}%)`
}

const formatPrice = (value: number) => {
  return `$${value.toFixed(2)}`
}

// Lifecycle
onMounted(() => {
  if (props.initialData) {
    position.value = props.initialData
  } else if (props.useMockData) {
    position.value = mockPosition
  }
})
</script>
```

Add loading/error states to template:

```vue
<template>
  <div class="iron-condor-card">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <span>Loading positions...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <el-icon :size="24"><Warning /></el-icon>
      <span>{{ error }}</span>
      <el-button size="small" @click="refresh">Retry</el-button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!position" class="empty-state">
      <span>No iron condor positions found</span>
    </div>

    <!-- Position Content -->
    <template v-else>
      <!-- Header -->
      <div class="card-header">
        <div class="ticker-info">
          <span class="ticker">{{ position.ticker }}</span>
          <span class="strategy">{{ position.strategy }}</span>
        </div>
        <div class="expiry-info">
          <el-icon><Timer /></el-icon>
          <span>{{ formatDate(position.expiryDate) }}</span>
          <span class="days-badge">{{ daysToExpiry }}d</span>
        </div>
      </div>

      <!-- Total P/L -->
      <div class="total-pnl" :class="{ profit: totalPnL >= 0, loss: totalPnL < 0 }">
        <span class="label">Total P/L</span>
        <span class="value">{{ formatCurrency(totalPnL) }}</span>
      </div>

      <!-- Connection Status Indicator -->
      <div class="connection-status" :class="connectionStatus">
        <span class="status-dot"></span>
        <span class="status-text">{{ connectionStatus }}</span>
      </div>

      <!-- Legs Table -->
      <div class="legs-table">
        <div class="table-header">
          <span>Type</span>
          <span>Strike</span>
          <span>Entry</span>
          <span>Current</span>
          <span>P/L</span>
        </div>

        <div
          v-for="leg in sortedLegs"
          :key="leg.id"
          class="leg-row"
          :class="[leg.direction.toLowerCase(), leg.optionType.toLowerCase()]"
        >
          <span class="leg-type">
            <span class="direction">{{ leg.direction }}</span>
            <span class="option-type">{{ leg.optionType }}</span>
          </span>
          <span class="strike">{{ formatPrice(leg.strike) }}</span>
          <span class="entry">{{ formatPrice(leg.entryPrice) }}</span>
          <span class="current">{{ formatPrice(leg.currentPrice) }}</span>
          <span class="pnl" :class="{ profit: (leg.pnlDollars || 0) >= 0, loss: (leg.pnlDollars || 0) < 0 }">
            {{ formatCurrency(leg.pnlDollars || 0) }}
            <small>{{ formatPercent(leg.pnlPercent || 0) }}</small>
          </span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.iron-condor-card {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--el-border-color);
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px;
  color: var(--el-text-color-secondary);
}

.error-state {
  color: var(--el-color-danger);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  margin-bottom: 8px;
}

.connection-status .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--el-color-info);
}

.connection-status.connected .status-dot {
  background: var(--el-color-success);
}

.connection-status.disconnected .status-dot {
  background: var(--el-color-warning);
}

.connection-status.error .status-dot {
  background: var(--el-color-danger);
}

/* ... rest of existing styles ... */
</style>
```

### Step 7: Add Vitest Configuration

**File:** `apps/orchestrator_3_stream/frontend/vitest.config.ts`

```typescript
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['src/**/*.{test,spec}.{js,ts,vue}'],
    coverage: {
      reporter: ['text', 'json', 'html'],
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
})
```

Update `package.json` to add Vitest:

```json
{
  "devDependencies": {
    "vitest": "^1.0.0",
    "@vitest/coverage-v8": "^1.0.0",
    "@vue/test-utils": "^2.4.0",
    "jsdom": "^23.0.0"
  },
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage"
  }
}
```

### Step 8: Create Frontend Tests

**File:** `apps/orchestrator_3_stream/frontend/src/composables/__tests__/useAlpacaPositions.spec.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAlpacaPositions } from '../useAlpacaPositions'
import * as alpacaService from '../../services/alpacaService'

// Mock the service
vi.mock('../../services/alpacaService')

describe('useAlpacaPositions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('initialization', () => {
    it('should initialize with default values', () => {
      vi.mocked(alpacaService.getPositions).mockResolvedValue({
        status: 'success',
        positions: [],
        totalCount: 0,
      })

      const { positions, loading, error, hasPositions } = useAlpacaPositions({
        autoFetch: false,
      })

      expect(positions.value).toEqual([])
      expect(loading.value).toBe(false)
      expect(error.value).toBeNull()
      expect(hasPositions.value).toBe(false)
    })
  })

  describe('fetchPositions', () => {
    it('should fetch and set positions', async () => {
      const mockPositions = [
        {
          id: 'test-1',
          ticker: 'SPY',
          strategy: 'Iron Condor',
          expiryDate: '2026-01-17',
          legs: [],
          createdAt: new Date().toISOString(),
        },
      ]

      vi.mocked(alpacaService.getPositions).mockResolvedValue({
        status: 'success',
        positions: mockPositions,
        totalCount: 1,
      })

      vi.mocked(alpacaService.subscribePrices).mockResolvedValue()

      const { positions, fetchPositions, hasPositions } = useAlpacaPositions({
        autoFetch: false,
      })

      await fetchPositions()

      expect(positions.value).toHaveLength(1)
      expect(positions.value[0].ticker).toBe('SPY')
      expect(hasPositions.value).toBe(true)
    })

    it('should handle errors', async () => {
      vi.mocked(alpacaService.getPositions).mockResolvedValue({
        status: 'error',
        positions: [],
        totalCount: 0,
        message: 'API error',
      })

      const { error, fetchPositions } = useAlpacaPositions({
        autoFetch: false,
      })

      await fetchPositions()

      expect(error.value).toBe('API error')
    })
  })

  describe('subscribeToUpdates', () => {
    it('should subscribe to price updates', async () => {
      const mockPositions = [
        {
          id: 'test-1',
          ticker: 'SPY',
          strategy: 'Iron Condor',
          expiryDate: '2026-01-17',
          legs: [
            {
              id: 'leg-1',
              symbol: 'SPY260117C00688000',
              direction: 'Short' as const,
              strike: 688,
              optionType: 'Call' as const,
              quantity: 10,
              entryPrice: 4.0,
              currentPrice: 3.5,
              expiryDate: '2026-01-17',
              underlying: 'SPY',
            },
          ],
          createdAt: new Date().toISOString(),
        },
      ]

      vi.mocked(alpacaService.getPositions).mockResolvedValue({
        status: 'success',
        positions: mockPositions,
        totalCount: 1,
      })

      vi.mocked(alpacaService.subscribePrices).mockResolvedValue()

      const { fetchPositions, isSubscribed } = useAlpacaPositions({
        autoFetch: false,
        autoSubscribe: true,
      })

      await fetchPositions()

      expect(alpacaService.subscribePrices).toHaveBeenCalledWith(['SPY260117C00688000'])
      expect(isSubscribed.value).toBe(true)
    })
  })
})
```

## Validation Commands

```bash
# Navigate to frontend directory
cd apps/orchestrator_3_stream/frontend

# Install Vitest and dependencies
npm install -D vitest @vitest/coverage-v8 @vue/test-utils jsdom

# Run tests
npm run test

# Run tests with coverage
npm run test:coverage

# Type check
npm run build

# Start dev server and verify component
npm run dev
```

## Acceptance Criteria

- [ ] TypeScript Raw* types transform snake_case to camelCase correctly
- [ ] Vue Map reactivity works with `shallowRef` + `triggerRef`
- [ ] WebSocket handlers are registered in orchestrator store
- [ ] Composables integrate with store for WebSocket updates
- [ ] Vitest test framework is configured and working
- [ ] Loading state displays while fetching
- [ ] Error state displays on failure with retry button
- [ ] Empty state displays when no positions
- [ ] Connection status indicator shows WebSocket state
- [ ] All frontend tests pass

## Notes

### Map Reactivity Pattern

```typescript
// WRONG - Vue won't detect changes
const cache = ref<Map<string, any>>(new Map())
cache.value.set('key', value)  // Won't trigger reactivity!

// CORRECT - Use shallowRef + triggerRef
const cache = shallowRef<Map<string, any>>(new Map())
cache.value.set('key', value)
triggerRef(cache)  // Manually trigger reactivity
```

### snake_case → camelCase Pattern

```typescript
// Backend sends:
{ option_type: 'Call', entry_price: 4.00 }

// Transform to:
{ optionType: 'Call', entryPrice: 4.00 }

// Using Raw* types ensures type safety at the boundary
```

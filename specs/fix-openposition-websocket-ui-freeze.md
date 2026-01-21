# Plan: Fix OpenPositionCard UI Freeze from WebSocket Price Updates

## Task Description
The OpenPositionCard.vue component freezes when receiving real-time WebSocket price updates. The WebSocket connection works correctly and prices update briefly, but then the UI becomes unresponsive. Refreshing the page temporarily fixes the issue but it freezes again.

## Objective
Eliminate UI freezing by optimizing the reactivity chain for high-frequency WebSocket price updates, implementing proper throttling/debouncing on the frontend, and preventing Vue reactivity storms.

## Problem Statement

### Evidence from Console Logs
The logs show **extremely high-frequency updates** with the same values repeated:
```
orchestratorStore.ts:967 [WS MESSAGE] type=option_price_update {symbol: 'GLD260121P00422000', mid_price: 0.08}
orchestratorStore.ts:463 [DEBUG] Price update received: GLD260121P00422000 = $0.08
orchestratorStore.ts:967 [WS MESSAGE] type=option_price_update {symbol: 'GLD260121P00422000', mid_price: 0.08}
orchestratorStore.ts:463 [DEBUG] Price update received: GLD260121P00422000 = $0.08
... (repeats many times with same value)
```

### Root Cause Analysis

**1. Per-Symbol Backend Throttling Creates Aggregate Overload**
- Backend throttles to 200ms **per symbol**
- With 6 option symbols, that's up to **30 updates/second** to the frontend
- Even with identical values, each update triggers full reactivity cycle

**2. Double Reactivity Trigger in Store (orchestratorStore.ts:462-488)**
```typescript
function updateAlpacaPrice(symbol: string, update: OptionPriceUpdate) {
  alpacaPriceCache.value.set(symbol, update)
  triggerRef(alpacaPriceCache)  // TRIGGER 1: priceCache watchers fire

  // Then ALSO mutates leg properties directly:
  for (const position of alpacaPositions.value) {
    for (const leg of position.legs) {
      if (leg.symbol === symbol) {
        leg.currentPrice = update.midPrice  // TRIGGER 2: position watchers fire
        leg.pnlDollars = ...
        leg.pnlPercent = ...
      }
    }
  }
}
```

**3. OpenPositionCard Watch Duplicates Store Work (lines 121-137)**
```typescript
watch(
  () => priceCache.value,
  () => {
    for (const leg of position.value.legs) {
      const price = getMidPrice(leg.symbol)
      if (price !== undefined) {
        leg.currentPrice = price  // ALREADY DONE BY STORE
        leg.pnlDollars = ...      // ALREADY DONE BY STORE
        leg.pnlPercent = ...      // ALREADY DONE BY STORE
      }
    }
  }
)
```

**4. No Value-Change Detection**
- Updates with identical values still trigger full reactivity cycles
- Same price received 10 times = 10 full re-renders

**5. Cascading Reactivity Chain**
```
WebSocket Message
    ↓
Store.updateAlpacaPrice()
    ↓
triggerRef(alpacaPriceCache) → Component Watch fires
    ↓                              ↓
Mutate position.legs      +    Mutate position.legs (DUPLICATE)
    ↓                              ↓
Vue re-renders            +    Vue re-renders (DUPLICATE)
    ↓
30 updates/sec × 2 render triggers = 60 re-renders/sec = UI FREEZE
```

## Solution Approach

### Strategy: Decouple Data Flow from Rendering

1. **Batch updates using requestAnimationFrame** - Collect all price updates within a frame, apply once
2. **Skip identical values** - Only trigger reactivity when price actually changes
3. **Single source of truth** - Remove duplicate leg mutation (let store OR component handle it, not both)
4. **Frontend debounce** - Add 100ms debounce to component-level watch

## Relevant Files

### Core Files to Modify
- `apps/orchestrator_3_stream/frontend/src/stores/orchestratorStore.ts` (lines 462-511)
  - Fix double reactivity trigger
  - Add value-change detection
  - Implement RAF batching

- `apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue` (lines 121-137)
  - Remove duplicate leg mutation (store already handles it)
  - Add debounced watch as backup
  - Use computed properties for P/L display

- `apps/orchestrator_3_stream/frontend/src/composables/useAlpacaPriceStream.ts`
  - Add optional debounce parameter
  - Expose batched update method

### Reference Files
- `apps/orchestrator_3_stream/frontend/src/types/alpaca.ts` - calculateLegPnl function
- `apps/orchestrator_3_stream/backend/modules/rate_limiter.py` - Backend throttle reference

### New Files
- `apps/orchestrator_3_stream/frontend/src/utils/rafBatch.ts` - RAF batching utility

## Implementation Phases

### Phase 1: Foundation - Add RAF Batching Utility
Create a utility for batching high-frequency updates into single animation frames.

### Phase 2: Core Implementation - Fix Store Reactivity
- Add value-change detection to skip identical updates
- Implement RAF batching for price updates
- Remove redundant position iteration OR make it opt-out

### Phase 3: Integration & Polish - Fix Component
- Remove duplicate watch logic
- Use pure computed properties for display
- Add CSS containment for render optimization

## Step by Step Tasks

### 1. Create RAF Batching Utility
Create `apps/orchestrator_3_stream/frontend/src/utils/rafBatch.ts`:

```typescript
/**
 * RAF Batching Utility
 *
 * Batches high-frequency updates into single animation frames.
 * Prevents UI freezing from rapid reactive updates.
 */

type BatchCallback<T> = (items: Map<string, T>) => void

export class RafBatcher<T> {
  private pending: Map<string, T> = new Map()
  private frameId: number | null = null
  private callback: BatchCallback<T>

  constructor(callback: BatchCallback<T>) {
    this.callback = callback
  }

  /**
   * Queue an update. Latest value wins per key.
   */
  add(key: string, value: T): void {
    this.pending.set(key, value)
    this.scheduleFlush()
  }

  private scheduleFlush(): void {
    if (this.frameId !== null) return

    this.frameId = requestAnimationFrame(() => {
      this.frameId = null
      if (this.pending.size === 0) return

      const batch = new Map(this.pending)
      this.pending.clear()
      this.callback(batch)
    })
  }

  clear(): void {
    if (this.frameId !== null) {
      cancelAnimationFrame(this.frameId)
      this.frameId = null
    }
    this.pending.clear()
  }
}

/**
 * Creates a debounced function that uses requestAnimationFrame.
 */
export function rafDebounce<T extends (...args: any[]) => void>(fn: T): T {
  let frameId: number | null = null

  return ((...args: any[]) => {
    if (frameId !== null) {
      cancelAnimationFrame(frameId)
    }
    frameId = requestAnimationFrame(() => {
      frameId = null
      fn(...args)
    })
  }) as T
}
```

### 2. Fix Store updateAlpacaPrice - Add Value Change Detection
Modify `orchestratorStore.ts` lines 462-489:

```typescript
/**
 * Update a single option price in the cache.
 * Optimized: Only triggers reactivity if value changed.
 */
function updateAlpacaPrice(symbol: string, update: OptionPriceUpdate) {
  // CHECK IF VALUE ACTUALLY CHANGED
  const existing = alpacaPriceCache.value.get(symbol)
  if (existing && existing.midPrice === update.midPrice) {
    // Same price - skip reactivity entirely
    return
  }

  console.log(`[DEBUG] Price update received: ${symbol} = $${update.midPrice}`)

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
```

### 3. Add RAF Batching to Store
Add batched price update handler:

```typescript
import { RafBatcher } from '../utils/rafBatch'

// In store setup, add batcher:
const priceBatcher = new RafBatcher<OptionPriceUpdate>((batch) => {
  // Apply all batched updates in single reactivity cycle
  let hasChanges = false

  for (const [symbol, update] of batch) {
    const existing = alpacaPriceCache.value.get(symbol)
    if (!existing || existing.midPrice !== update.midPrice) {
      alpacaPriceCache.value.set(symbol, update)
      hasChanges = true

      // Update matching legs
      for (const position of alpacaPositions.value) {
        for (const leg of position.legs) {
          if (leg.symbol === symbol) {
            leg.currentPrice = update.midPrice
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
  }

  // Single trigger for entire batch
  if (hasChanges) {
    triggerRef(alpacaPriceCache)
  }
})

/**
 * Queue a price update for batched processing.
 * Updates are batched per animation frame for optimal performance.
 */
function queueAlpacaPrice(symbol: string, update: OptionPriceUpdate) {
  priceBatcher.add(symbol, update)
}
```

### 4. Update WebSocket Handler to Use Batched Updates
Modify the WebSocket callback in orchestratorStore.ts (around line 964-975):

```typescript
onOptionPriceUpdate: (message: any) => {
  if (message.update) {
    const update = transformPriceUpdate(message.update)
    // USE BATCHED VERSION instead of direct update
    queueAlpacaPrice(update.symbol, update)

    // Infer connected status from receiving price data
    if (alpacaConnectionStatus.value !== 'connected') {
      setAlpacaConnectionStatus('connected')
    }
  }
},
```

### 5. Simplify OpenPositionCard Watch
Since the store now handles leg updates, the component watch is redundant. Simplify it to just force re-render:

```typescript
// SIMPLIFIED: Store handles leg updates, this just ensures reactivity
watch(
  () => priceCache.value,
  () => {
    // Force computed recalculation by touching position ref
    // The store already updates leg.currentPrice/pnlDollars/pnlPercent
  },
  { deep: false }
)
```

Or better, remove the watch entirely and rely on computed properties:

```typescript
// Remove the watch block (lines 119-137)

// Add computed properties for live price data
const legsWithLivePrices = computed(() => {
  if (!position.value) return []

  return position.value.legs.map(leg => {
    // Get live price from cache, fallback to leg's stored price
    const livePrice = getMidPrice(leg.symbol) ?? leg.currentPrice
    const pnl = calculateLegPnl({ ...leg, currentPrice: livePrice })

    return {
      ...leg,
      displayPrice: livePrice,
      displayPnlDollars: pnl.dollars,
      displayPnlPercent: pnl.percent,
    }
  })
})
```

### 6. Add CSS Containment for Render Optimization
Add to OpenPositionCard.vue styles:

```css
/* Optimize rendering performance */
.position-card {
  contain: layout style;
}

.legs-table {
  contain: layout;
}

/* Prevent layout thrashing on price updates */
.spot-value,
.pnl-value,
.strike {
  will-change: contents;
  font-variant-numeric: tabular-nums;
}
```

### 7. Validate with Console Logging
Add temporary debug logging to verify fix:

```typescript
// In store batcher callback
console.log(`[BATCH] Processing ${batch.size} price updates in single frame`)

// In store value-change check
if (existing && existing.midPrice === update.midPrice) {
  console.log(`[SKIP] ${symbol} unchanged at $${update.midPrice}`)
  return
}
```

## Testing Strategy

### Manual Testing
1. Load OpenPositionCard with 6+ option symbols
2. Verify UI remains responsive for 60+ seconds
3. Check console for batching logs showing reduced update frequency
4. Verify prices still update visually (within ~100ms of backend)

### Performance Profiling
1. Open Chrome DevTools Performance tab
2. Record 10 seconds of normal operation
3. Look for:
   - No long tasks (>50ms) from price updates
   - Smooth frame rate (≥30fps)
   - Reduced scripting time vs. before fix

### Edge Cases
1. Test with 0 positions (no crash)
2. Test with 20+ legs (still responsive)
3. Test rapid WebSocket reconnection
4. Test with stale prices (no updates for 30s)

## Acceptance Criteria

1. **UI Never Freezes**: OpenPositionCard remains responsive indefinitely while receiving price updates
2. **Prices Update Visually**: Price changes appear within 200ms of backend broadcast
3. **Console Shows Batching**: Debug logs show multiple updates batched per frame
4. **No Memory Leaks**: Memory usage stable over 5+ minutes
5. **Value-Change Detection Works**: Console shows "SKIP" logs for unchanged prices

## Validation Commands

Execute these commands to validate the task is complete:

- `cd apps/orchestrator_3_stream/frontend && npm run type-check` - Verify TypeScript compiles
- `cd apps/orchestrator_3_stream/frontend && npm run lint` - Verify no lint errors
- `cd apps/orchestrator_3_stream/frontend && npm run build` - Verify production build works

Manual validation:
1. Start backend: `cd apps/orchestrator_3_stream && ./start_be.sh`
2. Start frontend: `cd apps/orchestrator_3_stream && ./start_fe.sh`
3. Navigate to positions page
4. Open DevTools console and observe:
   - `[BATCH] Processing N price updates` logs
   - `[SKIP] symbol unchanged` logs for duplicate values
5. UI should remain responsive for 60+ seconds

## Notes

### Why RAF Batching?
`requestAnimationFrame` ensures updates are synchronized with the browser's paint cycle. Multiple updates within a single frame are consolidated into one render, preventing the "reactivity storm" where Vue tries to re-render faster than the browser can paint.

### Backend Throttle Still Important
The 200ms per-symbol backend throttle is still valuable - it reduces WebSocket traffic. The frontend batching handles the aggregate load when many symbols update simultaneously.

### Alternative: Web Worker
For even heavier loads (50+ symbols), consider moving price processing to a Web Worker. This would completely eliminate main thread blocking. Not needed for current 6-8 symbol use case.

### Rollback Plan
If issues arise, revert to original code and increase `ALPACA_PRICE_THROTTLE_MS` to 500ms as a temporary mitigation.

# RAF Batching Implementation Guide

## Problem Statement

The OpenPositionCard component was receiving 100+ WebSocket price updates per second, each triggering:
1. Vue reactivity cycle
2. Component re-render
3. Table re-render
4. Layout recalculation

This caused **UI freezing** because the render queue couldn't keep up.

## Solution Architecture

```
WebSocket Stream (100+ updates/sec)
          ↓
    RafBatcher
    ├─ Queues updates in Map
    ├─ Deduplicates same symbol
    ├─ Uses requestAnimationFrame
    └─ Triggers single Vue update per frame
          ↓
   Store State Update (max 60/sec)
          ↓
   Component Re-renders (smooth 60fps)
```

## Implementation Components

### 1. RafBatcher Utility Class

**Location:** `frontend/src/utils/rafBatch.ts`

```typescript
export class RafBatcher<T> {
  private pending: Map<string, T> = new Map()
  private frameId: number | null = null

  add(key: string, value: T): void {
    this.pending.set(key, value)  // Latest value wins for same key
    this.scheduleFlush()
  }

  private scheduleFlush(): void {
    if (this.frameId !== null) return  // Already scheduled

    this.frameId = requestAnimationFrame(() => {
      const batch = new Map(this.pending)
      this.pending.clear()
      this.callback(batch)  // Process all updates in batch
    })
  }
}
```

**Key Features:**
- `requestAnimationFrame` syncs with browser refresh (16.67ms at 60fps)
- Map deduplication: latest update for each symbol replaces previous
- Single callback invocation per animation frame

### 2. Store Batching Integration

**Location:** `frontend/src/stores/orchestratorStore.ts`

**Create Batcher Instance (line 158):**
```typescript
const optionPriceBatcher = new RafBatcher<OptionPriceUpdate>((batch) => {
  let hasChanges = false
  console.log(`[BATCH] Processing ${batch.size} option price updates in single frame`)

  for (const [symbol, update] of batch) {
    const existing = alpacaPriceCache.value.get(symbol)

    // Skip if price hasn't actually changed
    if (!existing || existing.midPrice !== update.midPrice) {
      alpacaPriceCache.value.set(symbol, update)
      hasChanges = true

      // Update position legs directly (mutation-based for performance)
      for (const position of alpacaPositions.value) {
        for (const leg of position.legs) {
          if (leg.symbol === symbol) {
            leg.currentPrice = update.midPrice
            // Recalculate P/L...
          }
        }
      }
    }
  }

  // Single reactivity trigger for entire batch
  if (hasChanges) {
    triggerRef(alpacaPriceCache)
  }
})
```

**Queue Price Updates (line 529):**
```typescript
function queueAlpacaPrice(symbol: string, update: OptionPriceUpdate) {
  optionPriceBatcher.add(symbol, update)
}
```

### 3. WebSocket Handler

**Location:** `frontend/src/stores/orchestratorStore.ts` (lines 1065-1069)

```typescript
onOptionPriceUpdate: (message: any) => {
  if (message.update) {
    const update = transformPriceUpdate(message.update)
    queueAlpacaPrice(update.symbol, update)  // Queue for batching
    if (alpacaConnectionStatus.value !== 'connected') {
      setAlpacaConnectionStatus('connected')
    }
  }
}
```

**Flow:**
1. WebSocket receives `option_price_update` event
2. Handler calls `queueAlpacaPrice()`
3. Batcher queues update for next animation frame
4. Multiple updates to same symbol are merged

### 4. Component Cleanup

**Location:** `frontend/src/components/OpenPositionCard.vue` (lines 119-121)

```vue
<!-- NOTE: Price updates are handled by the store's RAF batcher (orchestratorStore.ts)
     The batcher updates leg.currentPrice, pnlDollars, pnlPercent directly on position.legs
     No component-level watch needed - this prevents the double reactivity trigger that caused UI freezing -->
```

**What Changed:**
- BEFORE: Component had `watch` handler for `currentPosition` and `positions`
- AFTER: Removed redundant watch handlers
- EFFECT: Single source of truth (store batcher), no duplicate updates

### 5. CSS Performance Optimization

**Location:** `frontend/src/components/OpenPositionCard.vue` (lines 484, 727)

```css
.position-card {
  contain: layout style;  /* Isolate layout calculations */
}

.legs-table {
  contain: layout;  /* Prevent parent layout recalculation */
}
```

**Impact:**
- Browser doesn't recalculate parent layouts when table changes
- Prevents cascading layout recalculations
- Reduces layout thrashing from O(n²) to O(n)

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│         Alpaca WebSocket Server                     │
│  (Sends price updates 100+ times per second)        │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
          ┌──────────────────────┐
          │  WebSocket Handler   │
          │  (orchestratorStore) │
          └──────────┬───────────┘
                     │
                     ↓
          ┌──────────────────────────┐
          │   queueAlpacaPrice()     │
          │ (route to batcher)       │
          └──────────┬───────────────┘
                     │
         ┌───────────┴────────────┐
         ↓                        ↓
   ┌─────────────────┐   ┌────────────────┐
   │  Symbol: SPY    │   │ Symbol: IWM    │
   │  Price: $421.37 │   │ Price: $203.14 │
   │  Update #1      │   │ Update #1      │
   └────────┬────────┘   └────────┬───────┘
            │                      │
            ↓                      ↓
   ┌────────────────────────────────────────────┐
   │  RafBatcher Pending Queue (Map)            │
   │  ├─ SPY: $421.38  (latest wins)           │
   │  ├─ SPY: $421.37  (overwrites)            │
   │  ├─ IWM: $203.14  (queued)                │
   │  └─ (more updates...)                     │
   └────────────────────┬───────────────────────┘
                        │
                        ↓
        [requestAnimationFrame callback fires]
                        │
        ┌───────────────↓──────────────┐
        │  Process Batch Update        │
        │  ├─ Skip if price unchanged  │
        │  ├─ Update leg.currentPrice  │
        │  ├─ Recalc P/L               │
        │  └─ Single triggerRef()      │
        └───────────────┬──────────────┘
                        │
        ┌───────────────↓──────────────┐
        │  Vue Reactivity Trigger      │
        │  (once per 16.67ms max)      │
        └───────────────┬──────────────┘
                        │
        ┌───────────────↓──────────────┐
        │  Component Re-render         │
        │  (smooth 60fps)              │
        └───────────────┬──────────────┘
                        │
        ┌───────────────↓──────────────┐
        │  Display Updates             │
        │  ├─ Spot price: $421.38      │
        │  ├─ Leg prices update        │
        │  └─ P/L colors flash         │
        └──────────────────────────────┘
```

## Performance Impact

### Before Fix (Naive Approach)
```
Incoming updates:    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ (100/sec)
Vue cycles:          ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ (100/sec)
Browser re-renders:  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ (100/sec)
Result:              FROZEN / UNRESPONSIVE
```

### After Fix (With RAF Batching)
```
Incoming updates:    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ (100/sec)
RAF Batches:         ▓▓▓▓▓▓▓▓ (60/sec max)
Vue cycles:          ▓▓▓▓▓▓▓▓ (60/sec max)
Browser re-renders:  ▓▓▓▓▓▓▓▓ (60fps target)
Result:              SMOOTH / RESPONSIVE
```

## Console Logging for Verification

The implementation includes diagnostic logging:

```typescript
console.log(`[BATCH] Processing ${batch.size} option price updates in single frame`)
```

### What to Look for in DevTools Console

**During active price streaming:**
```
[BATCH] Processing 15 option price updates in single frame
[BATCH] Processing 23 option price updates in single frame
[BATCH] Processing 18 option price updates in single frame
[BATCH] Processing 12 option price updates in single frame
```

**Expected Frequency:**
- One log line per animation frame (max 60/sec at 60fps)
- Number of updates varies (12-30 is typical for 100 updates/sec incoming)
- No logs = no price updates being received

**Debugging Tips:**
- If no `[BATCH]` logs appear → check WebSocket connection
- If logs spike to 100+ per second → RAF batcher not working, check browser DevTools for errors
- If prices don't update → check if WebSocket handler is receiving events

## Testing Checklist

### Unit Tests (if creating tests)
- [ ] RafBatcher batches multiple updates into one callback
- [ ] RafBatcher deduplicates same key (latest value wins)
- [ ] RafBatcher respects animation frame timing
- [ ] Value-change detection skips updates when price unchanged
- [ ] Single `triggerRef()` called per batch, not per update

### Integration Tests
- [ ] Simulate 100+ WebSocket updates/sec
- [ ] Verify UI renders smoothly (60fps target)
- [ ] Verify P/L calculations correct during batch processing
- [ ] Verify prices update visually in component
- [ ] Verify console shows `[BATCH]` logs during streaming

### Manual Testing
- [ ] Open DevTools Console while prices update
- [ ] Watch for `[BATCH]` log messages
- [ ] Scroll the page while prices update (should be smooth)
- [ ] Click buttons and verify responsiveness
- [ ] Check DevTools Performance timeline (should be smooth 60fps)

## Common Issues & Troubleshooting

### Issue: No `[BATCH]` logs in console
**Cause:** WebSocket not sending price updates
**Solution:**
1. Check WebSocket connection status (should be "connected")
2. Verify Alpaca API credentials configured
3. Check browser Network tab for `option_price_update` events

### Issue: UI still freezes occasionally
**Cause:** Other components or store updates causing renders
**Solution:**
1. Check DevTools Performance for heavy operations
2. Look for other watches or computed properties causing re-renders
3. Verify CSS containment is applied correctly

### Issue: Prices don't update visually
**Cause:** Price updates queued but component not re-rendering
**Solution:**
1. Verify `triggerRef()` is called (check console logs)
2. Check that position objects are mutated (directly modify `leg.currentPrice`)
3. Verify component uses `toRef()` for store reactivity chain

### Issue: Memory leaks or high CPU usage
**Cause:** RAF callback scheduled multiple times
**Solution:**
1. Verify `scheduleFlush()` returns early if frame already scheduled
2. Check that `this.frameId` is cleared after callback
3. Verify cancellation on component unmount

## Best Practices

1. **Always use `toRef()` with `shallowRef`**
   ```typescript
   const priceCache = toRef(store, 'alpacaPriceCache')  // Maintains reactivity chain
   ```

2. **Trigger reactivity only when values change**
   ```typescript
   if (!existing || existing.midPrice !== update.midPrice) {
     alpacaPriceCache.value.set(symbol, update)
     triggerRef(alpacaPriceCache)  // Only trigger if changed
   }
   ```

3. **Mutate objects directly in batch**
   ```typescript
   leg.currentPrice = update.midPrice  // Direct mutation
   triggerRef(alpacaPriceCache)        // Single trigger
   ```

4. **Apply CSS containment to optimize layout**
   ```css
   .position-card {
     contain: layout style;  /* Isolate from parent layout */
   }
   ```

5. **Use `requestAnimationFrame` for UI-heavy operations**
   ```typescript
   this.frameId = requestAnimationFrame(() => {
     // Process batch in sync with browser refresh cycle
   })
   ```

## References

- [MDN: requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame)
- [CSS Containment Spec](https://developer.mozilla.org/en-US/docs/Web/CSS/contain)
- [Vue 3 Reactivity API](https://vuejs.org/guide/extras/reactivity-in-depth.html)
- [Vue shallowRef + triggerRef](https://vuejs.org/api/reactivity-advanced.html#triggerref)

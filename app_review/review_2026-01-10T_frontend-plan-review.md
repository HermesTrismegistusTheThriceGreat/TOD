# Code Review Report

**Generated**: 2026-01-10T12:00:00Z
**Reviewed Work**: Frontend aspects of Alpaca IronCondor Integration Plan
**Plan Reference**: `/Users/muzz/Desktop/tac/TOD/specs/alpaca-ironcondor-integration-plan.md`
**Git Diff Summary**: Plan file (untracked) - Implementation not yet started
**Verdict**: ⚠️ FAIL - Must address blockers before implementation

---

## Executive Summary

This is a **plan review** (not a code review) focused on the frontend architecture for the Alpaca IronCondor integration. The plan is generally well-structured with clear composable design and TypeScript interfaces. However, there are **critical blockers** in TypeScript interface inconsistencies (snake_case vs camelCase mismatch), missing reactive state management patterns, and incomplete WebSocket integration that will cause runtime errors if implemented as-is.

---

## Quick Reference

| #   | Description | Risk Level | Recommended Solution |
| --- | --- | --- | --- |
| 1   | TypeScript interface field naming inconsistency | BLOCKER | Use snake_case to match backend Pydantic |
| 2   | Store Map reactivity issue with `alpacaPriceCache` | BLOCKER | Use `shallowRef` or reactive object instead |
| 3   | Missing WebSocket handler registration in store | HIGH | Add `onOptionPriceUpdate` to `connectWebSocket` |
| 4   | Composable doesn't integrate with existing WebSocket | HIGH | Wire `handlePriceUpdate` to store callbacks |
| 5   | Missing error boundary in IronCondorCard | MEDIUM | Add error/loading template slots |
| 6   | Duplicate type definitions | MEDIUM | Extend existing `types.d.ts` |
| 7   | Transform functions should use generics | LOW | Type-safe transform with generics |
| 8   | Missing `onUnmounted` cleanup in composables | LOW | Add cleanup to prevent memory leaks |

---

## Issues by Risk Tier

### 🚨 BLOCKERS (Must Fix Before Implementation)

#### Issue #1: TypeScript Interface Field Naming Inconsistency

**Description**: The plan defines TypeScript interfaces using `camelCase` (e.g., `optionType`, `entryPrice`, `currentPrice`) but the backend Pydantic models use `snake_case` (e.g., `option_type`, `entry_price`, `current_price`). While transform functions are provided, the interfaces should match the **API response format** (snake_case) since that's what the frontend receives. The current design creates confusion and potential type-safety issues.

**Location**:
- File: `Plan Step 7 - TypeScript Interfaces`
- Lines: `1099-1127` (OptionLeg and IronCondorPosition interfaces)

**Offending Code**:
```typescript
export interface OptionLeg {
  id: string
  symbol: string
  direction: 'Long' | 'Short'
  strike: number
  optionType: 'Call' | 'Put'  // Backend sends option_type
  quantity: number
  entryPrice: number          // Backend sends entry_price
  currentPrice: number        // Backend sends current_price
  expiryDate: string          // Backend sends expiry_date
  underlying: string
  pnlDollars?: number         // Backend sends pnl_dollars
  pnlPercent?: number         // Backend sends pnl_percent
}
```

**Recommended Solutions**:
1. **Define Raw API Types + Transformed Types** (Preferred)
   - Create `RawOptionLeg` interface matching exact API response (snake_case)
   - Create `OptionLeg` interface for transformed UI usage (camelCase)
   - Transform functions become type-safe: `transformOptionLeg(raw: RawOptionLeg): OptionLeg`
   - Rationale: This is the pattern used in production Vue/React apps - explicit API boundary

2. **Use snake_case Consistently**
   - Match backend Pydantic models exactly
   - No transform functions needed
   - Trade-off: Violates TypeScript naming conventions, but reduces mapping bugs

---

#### Issue #2: Store Map Reactivity Issue with `alpacaPriceCache`

**Description**: The plan uses `new Map<string, OptionPriceUpdate>()` for `alpacaPriceCache` state. Vue 3's reactivity system does **not** track Map internal changes (`.set()`, `.delete()`). The store's `updateOptionPrice` action will silently fail to trigger reactivity.

**Location**:
- File: `Plan Step 11 - Orchestrator Store`
- Lines: `1647-1648`

**Offending Code**:
```typescript
// In store state
alpacaPriceCache: new Map<string, OptionPriceUpdate>(),

// In action - THIS WON'T TRIGGER REACTIVITY
updateOptionPrice(symbol: string, update: OptionPriceUpdate) {
  this.alpacaPriceCache.set(symbol, update)  // ❌ Vue doesn't track this
}
```

**Recommended Solutions**:
1. **Use `shallowRef` with Manual Triggering** (Preferred)
   ```typescript
   // State
   alpacaPriceCache: shallowRef(new Map<string, OptionPriceUpdate>())

   // Action
   updateOptionPrice(symbol: string, update: OptionPriceUpdate) {
     this.alpacaPriceCache.set(symbol, update)
     triggerRef(this.alpacaPriceCache)  // Force reactivity
   }
   ```
   - Rationale: Maintains Map semantics with explicit reactivity control

2. **Use Reactive Object Instead of Map** (Alternative)
   ```typescript
   // State
   alpacaPriceCache: {} as Record<string, OptionPriceUpdate>

   // Action
   updateOptionPrice(symbol: string, update: OptionPriceUpdate) {
     this.alpacaPriceCache[symbol] = update  // ✅ Vue tracks this
   }
   ```
   - Trade-off: Object instead of Map, but simpler reactivity

---

### ⚠️ HIGH RISK (Should Fix Before Implementation)

#### Issue #3: Missing WebSocket Handler Registration in Store

**Description**: The plan adds `onOptionPriceUpdate` and `onPositionUpdate` to the `WebSocketCallbacks` interface (Step 6), but the store's `connectWebSocket` method (lines 707-792 in existing code) is never updated to register these handlers. Without this, price updates from the backend will be silently ignored.

**Location**:
- File: `Plan Step 11 - Orchestrator Store`
- Lines: `1689-1703` (shows handlers but not registration)

**Offending Code**:
```typescript
// Plan shows handlers to ADD:
onOptionPriceUpdate: (message: any) => {
  const update = transformPriceUpdate(message.update)
  this.updateOptionPrice(update.symbol, update)
},

// BUT the plan doesn't show WHERE to add them in connectWebSocket
// The existing connectWebSocket method needs modification
```

**Recommended Solutions**:
1. **Explicitly Add to `connectWebSocket` Call** (Required)
   ```typescript
   // In connectWebSocket method, add to callbacks object:
   wsConnection = chatService.connectWebSocket(wsUrl, {
     // ... existing handlers ...
     onOptionPriceUpdate: (message: any) => {
       const update = transformPriceUpdate(message.update)
       this.updateOptionPrice(update.symbol, update)
     },
     onPositionUpdate: (message: any) => {
       const position = transformPosition(message.position)
       // ... handle position update
     },
   })
   ```
   - Rationale: Without this, the WebSocket events are defined but never wired

---

#### Issue #4: Composable Doesn't Integrate with Existing WebSocket

**Description**: The `useAlpacaPriceStream` composable (Step 10) has a `handlePriceUpdate` method, but it's never wired to the store's WebSocket. The composable imports `useOrchestratorStore` but doesn't actually use it to subscribe to updates. The `watch` in IronCondorCard (Step 12, line 1792) watches `store.alpacaPriceCache` but that cache is never populated because the WebSocket handler isn't wired.

**Location**:
- File: `Plan Step 10 - useAlpacaPriceStream`
- Lines: `1565-1627`

**Offending Code**:
```typescript
export function useAlpacaPriceStream(callbacks: PriceStreamCallbacks = {}) {
  const store = useOrchestratorStore()  // ❌ Not used

  // This is never called from anywhere:
  function handlePriceUpdate(message: any): void {
    // ...
  }

  // Missing: No subscription to store's WebSocket events
}
```

**Recommended Solutions**:
1. **Use Store's Price Cache Directly** (Preferred)
   ```typescript
   export function useAlpacaPriceStream(callbacks: PriceStreamCallbacks = {}) {
     const store = useOrchestratorStore()

     // Watch store's price cache for changes
     watch(
       () => store.alpacaPriceCache,
       (cache) => {
         // Notify callbacks when cache changes
         for (const [symbol, update] of cache.entries()) {
           callbacks.onPriceUpdate?.(update)
         }
       },
       { deep: true }
     )

     // Expose store's cache directly
     const getPrice = (symbol: string) => store.alpacaPriceCache.get(symbol)
     // ...
   }
   ```
   - Rationale: Single source of truth - store handles WebSocket, composable provides reactive access

2. **Remove Composable, Use Store Directly** (Alternative)
   - The composable adds little value if store already manages price state
   - IronCondorCard can watch `store.alpacaPriceCache` directly
   - Trade-off: Less separation, but simpler architecture

---

### ⚡ MEDIUM RISK (Fix Soon)

#### Issue #5: Missing Error Boundary in IronCondorCard

**Description**: The updated IronCondorCard (Step 12) has `loading` and `error` refs from the composable, but the template only shows `v-loading="loading"`. There's no error state display or empty state handling in the template.

**Location**:
- File: `Plan Step 12 - IronCondorCard`
- Lines: `1730-1872` (script has error handling, template missing)

**Offending Code**:
```vue
<template>
  <el-card v-loading="loading" class="position-card">
    <template v-if="position">
      <!-- Only shows when position exists -->
    </template>
    <!-- ❌ No v-else for error/empty state -->
  </el-card>
</template>
```

**Recommended Solutions**:
1. **Add Error and Empty State Templates** (Preferred)
   ```vue
   <template>
     <el-card v-loading="loading" class="position-card">
       <!-- Error state -->
       <template v-if="error">
         <el-result icon="error" :title="error">
           <template #extra>
             <el-button @click="refresh">Retry</el-button>
           </template>
         </el-result>
       </template>

       <!-- Empty state -->
       <template v-else-if="!position && !loading">
         <el-empty description="No position data" />
       </template>

       <!-- Position data -->
       <template v-else-if="position">
         <!-- existing template -->
       </template>
     </el-card>
   </template>
   ```

---

#### Issue #6: Duplicate Type Definitions

**Description**: The plan creates a new `types/alpaca.ts` file, but the project already has `types.d.ts` with comprehensive type definitions. Creating a separate file fragments the type system and creates maintenance burden.

**Location**:
- File: `Plan Step 7 - New types/alpaca.ts file`
- Existing: `src/types.d.ts`

**Recommended Solutions**:
1. **Extend Existing types.d.ts** (Preferred)
   ```typescript
   // In existing types.d.ts, add new section:

   // ═══════════════════════════════════════════════════════════
   // ALPACA TRADING TYPES
   // ═══════════════════════════════════════════════════════════

   export interface OptionLeg { /* ... */ }
   export interface IronCondorPosition { /* ... */ }
   // etc.
   ```
   - Rationale: Single source of truth for all types, consistent with project patterns

---

### 💡 LOW RISK (Nice to Have)

#### Issue #7: Transform Functions Should Use Generics

**Description**: The transform functions use `any` type for input, losing type safety benefits.

**Location**:
- File: `Plan Step 7 - Transform functions`
- Lines: `1199-1239`

**Offending Code**:
```typescript
export function transformOptionLeg(leg: any): OptionLeg {
  // 'leg' is any - no compile-time checking
}
```

**Recommended Solutions**:
1. **Define Raw Types and Use Generics**
   ```typescript
   interface RawOptionLeg {
     id: string
     symbol: string
     direction: 'Long' | 'Short'
     strike: number
     option_type: 'Call' | 'Put'  // snake_case
     // etc.
   }

   export function transformOptionLeg(leg: RawOptionLeg): OptionLeg {
     return {
       optionType: leg.option_type,  // Type-safe mapping
       // etc.
     }
   }
   ```

---

#### Issue #8: Missing `onUnmounted` Cleanup in Composables

**Description**: The `useAlpacaPositions` composable has `onMounted` but no `onUnmounted` cleanup. If the component unmounts while a fetch is in progress, it could cause "setting state on unmounted component" warnings.

**Location**:
- File: `Plan Step 9 - useAlpacaPositions`
- Lines: `1501-1508`

**Recommended Solutions**:
1. **Add Cleanup with AbortController**
   ```typescript
   export function useAlpacaPositions(options = {}) {
     const abortController = ref<AbortController | null>(null)

     async function fetchPositions(): Promise<void> {
       abortController.value = new AbortController()
       try {
         positions.value = await getPositions({
           signal: abortController.value.signal
         })
       } catch (e) {
         if (e.name !== 'AbortError') {
           error.value = e.message
         }
       }
     }

     onUnmounted(() => {
       abortController.value?.abort()
     })
   }
   ```

---

## Plan Compliance Check

### Acceptance Criteria Validation

- [ ] **TypeScript Interfaces**: Defined but naming mismatch with backend (BLOCKER)
- [ ] **Store Integration**: Pattern defined but Map reactivity issue (BLOCKER)
- [ ] **WebSocket Handling**: Callbacks defined but not registered (HIGH)
- [ ] **Composables Design**: Good patterns but not wired correctly (HIGH)
- [ ] **IronCondorCard Updates**: Script complete, template incomplete (MEDIUM)

### Validation Commands (Not Yet Runnable)
The plan's validation commands are for post-implementation. For plan review:

```bash
# Type checking will fail due to snake_case/camelCase mismatch
# Store reactivity tests would fail silently
# WebSocket integration tests would show no price updates
```

---

## Verification Checklist

- [ ] TypeScript interfaces use consistent naming (snake_case for API, camelCase for UI)
- [ ] Store uses `shallowRef` or reactive object for Map-like price cache
- [ ] WebSocket handlers registered in `connectWebSocket` method
- [ ] Composables properly subscribe to store events
- [ ] Error and loading states handled in template
- [ ] Types added to existing `types.d.ts` instead of new file
- [ ] Transform functions are type-safe with generics
- [ ] Cleanup handlers prevent memory leaks

---

## Final Verdict

**Status**: ⚠️ FAIL

**Reasoning**: The plan has 2 BLOCKER issues (TypeScript naming inconsistency, Map reactivity) and 2 HIGH risk issues (WebSocket registration, composable wiring) that will cause runtime failures or silent data loss if implemented as-is. The architectural approach is sound, but the implementation details need correction before development begins.

**Next Steps**:
1. **BLOCKER**: Define `Raw*` types matching API response + transform to `camelCase` types
2. **BLOCKER**: Replace `Map` with `shallowRef(new Map())` + `triggerRef` pattern
3. **HIGH**: Add explicit WebSocket handler registration code to plan
4. **HIGH**: Wire composable to store's price cache with `watch`
5. Update IronCondorCard template with error/empty states
6. Consolidate types into existing `types.d.ts`

---

**Report File**: `app_review/review_2026-01-10T_frontend-plan-review.md`

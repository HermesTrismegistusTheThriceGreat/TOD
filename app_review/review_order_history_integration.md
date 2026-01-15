# Code Review Report: Order History Integration

**Generated**: 2026-01-14T00:00:00Z
**Reviewed Work**: Order History Integration implementation with Trade API, TypeScript types, and Vue components
**Reviewed Files**: 6 files (3 backend, 3 frontend)
**Verdict**: ⚠️ **FAIL** - Critical blockers must be fixed before merge

---

## Executive Summary

The Order History Integration implementation demonstrates good architectural patterns and comprehensive coverage of backend-to-frontend data flow. However, there are **critical issues** that prevent merging: a SQL injection vulnerability in dynamic query building, incorrect P&L calculation logic, missing null validation that causes runtime errors, and a mismatch in API response contracts. Additionally, the implementation lacks comprehensive error handling in frontend components and introduces simplified P&L calculations that don't match real trading outcomes. These issues must be resolved before the feature can be deployed to production.

---

## Quick Reference

| #   | Issue                                  | Risk Level | Component        | File                                    |
| --- | -------------------------------------- | ---------- | ---------------- | --------------------------------------- |
| 1   | SQL Injection in dynamic query         | BLOCKER    | Backend          | alpaca_sync_service.py                  |
| 2   | Incorrect P&L calculation logic        | BLOCKER    | Backend          | alpaca_sync_service.py                  |
| 3   | Missing optional field in TS types     | BLOCKER    | Frontend          | types/trades.ts                         |
| 4   | API response contract mismatch         | BLOCKER    | Frontend/Backend  | api.ts vs alpaca_models.py              |
| 5   | Null reference in frontend fetch       | HIGH       | Frontend          | TradeStats.vue                          |
| 6   | Missing validation on NULL database values | HIGH   | Backend          | alpaca_sync_service.py (line 695-718)   |
| 7   | Inconsistent P&L calculation methods  | HIGH       | Backend          | alpaca_sync_service.py vs alpaca_models.py |
| 8   | No error boundary in Vue component     | HIGH       | Frontend          | TradeStats.vue                          |
| 9   | Missing orders array in TradeResponse | MEDIUM     | Backend/Frontend  | alpaca_models.py vs types/trades.ts     |
| 10  | No timeout handling for concurrent requests | MEDIUM | Frontend          | TradeStats.vue (line 157-160)            |
| 11  | Incomplete win_rate calculation       | MEDIUM     | Backend          | alpaca_sync_service.py (line 758)       |
| 12  | Status filtering logic is fragile      | MEDIUM     | Backend          | alpaca_sync_service.py (line 700-711)   |

---

## Issues by Risk Tier

### 🚨 BLOCKERS (Must Fix Before Merge)

#### Issue #1: SQL Injection Vulnerability in Dynamic Query Building

**Description**: The `get_orders()` method in alpaca_sync_service.py constructs SQL queries by dynamically building the WHERE clause with string concatenation. Although parameterized placeholders are used for values, the overall query construction pattern is dangerous because future modifications could introduce injection vulnerabilities. More critically, the LIMIT and OFFSET parameters are incorrectly applied.

**Location**:
- File: `apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py`
- Lines: `616-621`

**Offending Code**:
```python
async with pool.acquire() as conn:
    rows = await conn.fetch(f"""
        SELECT * FROM alpaca_orders
        WHERE {where_clause}
        ORDER BY submitted_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params)
```

**Issues**:
- The LIMIT parameter references `${param_idx}` but should be `${param_idx}` and OFFSET should be `${param_idx + 1}` - HOWEVER the params list has already appended limit and offset, so the indexing is off by 1
- The query uses f-string to insert `where_clause` which could be dangerous despite current safeguards

**Recommended Solutions**:

1. **Use query builder pattern (Preferred)**
   - Build the complete query with all parameters properly indexed
   - Use raw SQL with explicit parameter indices
   ```python
   async with pool.acquire() as conn:
       conditions = []
       params = []

       if underlying:
           conditions.append("underlying = $1")
           params.append(underlying)
       # ... more conditions ...

       where_clause = " AND ".join(conditions) if conditions else "1=1"
       limit_idx = len(params) + 1
       offset_idx = len(params) + 2

       rows = await conn.fetch(f"""
           SELECT * FROM alpaca_orders
           WHERE {where_clause}
           ORDER BY submitted_at DESC
           LIMIT ${limit_idx} OFFSET ${offset_idx}
       """, *params, limit, offset)
   ```
   - Rationale: Fixes the parameter indexing and maintains proper SQL parameterization

2. **Use asyncpg's execute with proper parameter binding**
   - Build query string completely with placeholders
   - Pass all parameters in order without indexing
   - Rationale: Cleaner and more maintainable

---

#### Issue #2: Incorrect and Oversimplified P&L Calculation Logic

**Description**: The P&L calculation in `get_trades()` is fundamentally flawed. It calculates total_premium as the sum of sell transactions minus buy transactions, but then uses this as both `entry_price` and `pnl`. This conflates entry price with actual profit/loss and doesn't account for position matching, exit prices, or the true cost basis of the trade.

**Location**:
- File: `apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py`
- Lines: `683-734`

**Offending Code**:
```python
SUM(CASE WHEN side = 'sell' THEN filled_avg_price * filled_qty * 100
         ELSE -filled_avg_price * filled_qty * 100 END) as total_premium,
# ...
# Calculate P&L percent (simplified - premium selling strategies)
total_premium = float(row['total_premium'] or 0)
pnl_percent = 0.0
if total_premium != 0:
    pnl_percent = (total_premium / abs(total_premium)) * 100 if total_premium else 0.0

trades.append({
    'entry_price': total_premium,
    'exit_price': None,
    'pnl': total_premium,  # Simplified - needs position matching
    'pnl_percent': pnl_percent,  # This calculation is wrong!
})
```

**Problems**:
1. Line 718: `pnl_percent = (total_premium / abs(total_premium)) * 100` returns only -100 or +100, never the actual percentage
2. `entry_price` should be the average entry price, not total premium
3. `pnl` should be calculated from entry vs exit prices, not just total premium
4. The calculation assumes all premium-selling strategies and doesn't handle long positions correctly
5. Comments admit the calculation is "simplified" - this is production code that needs to be correct

**Recommended Solutions**:

1. **Implement proper position matching (Preferred)**
   - For each trade_id, match closing orders to opening orders
   - Calculate entry_price as weighted average of opening orders
   - Calculate exit_price from closing orders
   - Calculate pnl = (exit_price - entry_price) * quantity * 100 * direction_multiplier
   ```python
   # For each trade_id:
   opening_qty = sum(o.qty for o in orders if o.side == 'sell')
   opening_value = sum(o.filled_qty * o.filled_avg_price for o in orders if o.side == 'sell')
   entry_price = opening_value / opening_qty if opening_qty else 0

   closing_qty = sum(o.qty for o in orders if o.side == 'buy')
   closing_value = sum(o.filled_qty * o.filled_avg_price for o in orders if o.side == 'buy')
   exit_price = closing_value / closing_qty if closing_qty else None

   if exit_price:
       pnl = (exit_price - entry_price) * opening_qty * 100
   else:
       pnl = (current_price - entry_price) * opening_qty * 100
   ```
   - Rationale: Most accurate and industry-standard approach

2. **Implement simplified but correct calculation for now**
   - Document the limitation that pnl is unreliable until positions are closed
   - Only calculate pnl for fully-closed trades
   - Return None/0 for open trades
   - Rationale: Prevents incorrect data from being displayed

3. **Mark fields as estimated/unreliable**
   - Add `pnl_source: 'estimated' | 'calculated'` to TradeResponse
   - Return estimated values with clear UI labeling
   - Rationale: Manages expectations until proper implementation available

---

#### Issue #3: Missing Required Field in TradeResponse Type Definition

**Description**: The TradeResponse Pydantic model in the backend includes an `orders: List[dict] = []` field (line 443 in alpaca_models.py), but the TypeScript interface Trade in types/trades.ts does not include this field. This causes a contract mismatch that will lead to runtime errors when frontend code expects this field.

**Location**:
- Backend: `apps/orchestrator_3_stream/backend/modules/alpaca_models.py` - Line 443
- Frontend: `apps/orchestrator_3_stream/frontend/src/types/trades.ts` - Lines 8-22

**Offending Code**:

Backend (alpaca_models.py:426-443):
```python
class TradeResponse(BaseModel):
    """Single trade (aggregated from orders with same trade_id)"""
    # ... other fields ...
    leg_count: int  # number of legs in this trade
    orders: List[dict] = []  # individual order details
```

Frontend (types/trades.ts:8-22):
```typescript
export interface Trade {
  trade_id: string
  ticker: string
  strategy: string
  direction: 'Long' | 'Short'
  entry_date: string
  exit_date: string | null
  entry_price: number
  exit_price: number | null
  quantity: number
  pnl: number
  pnl_percent: number
  status: 'open' | 'closed' | 'expired'
  leg_count: number
  // NOTE: Missing 'orders' field!
}
```

**Recommended Solutions**:

1. **Add orders field to TypeScript interface (Preferred)**
   - Add proper typing for the orders list
   ```typescript
   export interface OrderDetail {
     id: string
     symbol: string
     side: string
     qty: number
     filled_avg_price: number
     status: string
   }

   export interface Trade {
     // ... existing fields ...
     leg_count: number
     orders: OrderDetail[]
   }
   ```
   - Rationale: Maintains contract consistency and allows frontend to display order details

2. **Remove orders field from backend if not used**
   - If frontend doesn't need individual order details, remove from TradeResponse
   - Update documentation to explain trade aggregation
   - Rationale: Reduces payload size and simplifies data model

3. **Make orders optional in both**
   - Mark as `orders?: Order[]` in TypeScript
   - Mark as `orders: List[dict] = []` in Pydantic (already done)
   - Document when orders are populated vs empty
   - Rationale: Provides flexibility for gradual rollout

---

#### Issue #4: API Response Contract Mismatch Between Backend and Frontend

**Description**: The TradeStatsResponse in the backend includes a `message: Optional[str]` field, but the TypeScript interface TradeStatsResponse also includes message but doesn't properly handle the case where other fields are optional. This creates confusion about which fields are guaranteed to be present in success vs error responses.

**Location**:
- Backend: `apps/orchestrator_3_stream/backend/modules/alpaca_models.py` - Lines 456-468
- Frontend: `apps/orchestrator_3_stream/frontend/src/types/trades.ts` - Lines 41-51

**Offending Code**:

Backend (alpaca_models.py:456-468):
```python
class TradeStatsResponse(BaseModel):
    status: Literal['success', 'error']
    total_pnl: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    open_trades: int = 0
    closed_trades: int = 0
    message: Optional[str] = None
```

Frontend (types/trades.ts:41-51):
```typescript
export interface TradeStatsResponse {
  status: 'success' | 'error'
  total_pnl?: number          // Optional!
  win_rate?: number           // Optional!
  total_trades?: number       // Optional!
  winning_trades?: number     // Optional!
  losing_trades?: number      // Optional!
  open_trades?: number        // Optional!
  closed_trades?: number      // Optional!
  message?: string
}
```

**Problem**: The backend returns all fields with defaults (0.0, 0), but the frontend marks them all as optional. When status='error', the frontend code might assume these fields are missing, but they're always present in the API response.

**Recommended Solutions**:

1. **Create discriminated union types (Preferred)**
   ```typescript
   export interface TradeStatsSuccess {
     status: 'success'
     total_pnl: number
     win_rate: number
     total_trades: number
     winning_trades: number
     losing_trades: number
     open_trades: number
     closed_trades: number
   }

   export interface TradeStatsError {
     status: 'error'
     message: string
   }

   export type TradeStatsResponse = TradeStatsSuccess | TradeStatsError
   ```
   - Usage in Vue: `if (statsRes.status === 'success') { statsRes.total_pnl ... }`
   - Rationale: TypeScript will enforce proper field access based on status

2. **Make all fields required in TypeScript**
   - Remove the `?` from all numeric fields
   - Frontend code expects all fields for status='success'
   - Rationale: Matches backend contract exactly

3. **Update backend to only return fields on success**
   - Use Pydantic's `exclude_unset` or conditional serialization
   - Return only `{status: 'error', message}` on error
   - Rationale: More RESTful, smaller payloads

---

### ⚠️ HIGH RISK (Should Fix Before Merge)

#### Issue #5: Null Reference Error in Frontend Promise Handling

**Description**: In TradeStats.vue, the component makes concurrent API calls without null checking. If either API call fails partially or returns unexpected data, accessing properties on the response object could throw null reference errors. The error handling catches top-level exceptions but not field access errors.

**Location**:
- File: `apps/orchestrator_3_stream/frontend/src/components/TradeStats.vue`
- Lines: `157-180`

**Offending Code**:
```typescript
try {
  const [tradesRes, statsRes] = await Promise.all([
    tradeApi.getTrades({ status: statusFilter.value === 'all' ? undefined : statusFilter.value }),
    tradeApi.getTradeStats(statusFilter.value === 'all' ? undefined : statusFilter.value)
  ])

  if (tradesRes.status === 'success') {
    trades.value = tradesRes.trades  // What if trades is undefined?
  } else {
    error.value = tradesRes.message || 'Failed to fetch trades'
  }

  if (statsRes.status === 'success') {
    stats.value = {
      total_pnl: statsRes.total_pnl || 0,      // Fallback is good
      win_rate: statsRes.win_rate || 0,        // But what if response is null?
      total_trades: statsRes.total_trades || 0
    }
  }
} catch (e) {
  error.value = e instanceof Error ? e.message : 'An error occurred'
}
```

**Issues**:
1. If API returns 500 error, apiClient interceptor throws and catches it, but status might be 'error' with no message
2. `tradesRes.trades` could be undefined even when status='success' (no null check)
3. `statsRes` object could be null if Promise.all rejects

**Recommended Solutions**:

1. **Add defensive null checks (Preferred)**
   ```typescript
   try {
     const [tradesRes, statsRes] = await Promise.all([
       tradeApi.getTrades({ ... }),
       tradeApi.getTradeStats(...)
     ])

     if (!tradesRes || typeof tradesRes !== 'object') {
       error.value = 'Invalid trades response'
       return
     }

     if (tradesRes.status === 'success' && Array.isArray(tradesRes.trades)) {
       trades.value = tradesRes.trades
     } else {
       error.value = tradesRes?.message || 'Failed to fetch trades'
     }

     if (statsRes?.status === 'success') {
       stats.value = {
         total_pnl: statsRes.total_pnl ?? 0,
         win_rate: statsRes.win_rate ?? 0,
         total_trades: statsRes.total_trades ?? 0
       }
     } else {
       error.value = statsRes?.message || 'Failed to fetch statistics'
     }
   } catch (e) {
     error.value = e instanceof Error ? e.message : 'Network error'
   }
   ```
   - Rationale: Prevents null reference errors and provides better error messages

2. **Use Zod or Valibot for response validation**
   - Parse responses against expected schema
   - Throws on schema mismatch
   - Rationale: Catches contract violations early

3. **Separate API calls with individual error handling**
   ```typescript
   await fetchTrades()
   await fetchStats()
   ```
   - Rationale: Allows one call to fail without crashing the other

---

#### Issue #6: Missing Null Validation in Backend P&L Aggregation

**Description**: The SQL query in `get_trades()` uses aggregate functions without handling potential NULL values from the database. The `exit_date` field uses `COALESCE(filled_at, canceled_at, expired_at)` but these could all be NULL for open positions. The code converts to float without validation.

**Location**:
- File: `apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py`
- Lines: `682-694`, `714-718`

**Offending Code**:
```python
query = """
    SELECT
        trade_id,
        underlying,
        strategy_type,
        MIN(submitted_at) as entry_date,
        MAX(COALESCE(filled_at, canceled_at, expired_at)) as exit_date,
        SUM(CASE WHEN side = 'sell' THEN filled_avg_price * filled_qty * 100
                 ELSE -filled_avg_price * filled_qty * 100 END) as total_premium,
        ...
"""
# ...
total_premium = float(row['total_premium'] or 0)  # What if this is NULL from DB?
pnl_percent = 0.0
if total_premium != 0:
    pnl_percent = (total_premium / abs(total_premium)) * 100 if total_premium else 0.0
```

**Issues**:
1. `row['total_premium']` could be NULL from database (SUM returns NULL if no rows match condition)
2. `float(None)` raises TypeError - the `or 0` catches it but is fragile
3. `row['exit_date']` could be NULL for open positions, needs explicit handling
4. `row['quantity']` could be NULL, converted to int without check

**Recommended Solutions**:

1. **Use COALESCE in SQL (Preferred)**
   ```python
   query = """
       SELECT
           trade_id,
           underlying,
           strategy_type,
           MIN(submitted_at) as entry_date,
           MAX(COALESCE(filled_at, canceled_at, expired_at)) as exit_date,
           COALESCE(
               SUM(CASE WHEN side = 'sell' THEN filled_avg_price * filled_qty * 100
                        ELSE -filled_avg_price * filled_qty * 100 END),
               0
           ) as total_premium,
           MAX(filled_qty) as quantity,
           COUNT(*) as leg_count,
           array_agg(DISTINCT status) as statuses
       FROM alpaca_orders
       WHERE ($1::TEXT IS NULL OR underlying = $1)
       GROUP BY trade_id, underlying, strategy_type
       ORDER BY entry_date DESC
       LIMIT $2 OFFSET $3
   """
   ```
   - Rationale: Handles NULLs at the database level

2. **Add explicit type conversion helper**
   ```python
   def safe_float(val, default=0.0):
       if val is None:
           return default
       return float(val)

   total_premium = safe_float(row['total_premium'])
   quantity = safe_float(row['quantity'], 0)
   ```
   - Rationale: Makes NULL handling explicit and reusable

3. **Add logging for unexpected NULLs**
   ```python
   if row['total_premium'] is None:
       logger.warning(f"Total premium is NULL for trade {row['trade_id']}")
   ```
   - Rationale: Helps debug data quality issues

---

#### Issue #7: Inconsistent P&L Calculation Methods Between Models

**Description**: The OptionLeg model in alpaca_models.py calculates P&L using one method (lines 130-148), but the get_trades() method uses a completely different calculation. This creates confusion and inconsistent results.

**Location**:
- File: `apps/orchestrator_3_stream/backend/modules/alpaca_models.py` - Lines 130-148 (OptionLeg)
- File: `apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py` - Lines 714-734 (get_trades)

**Offending Code**:

OptionLeg calculation (alpaca_models.py:130-139):
```python
@computed_field
@property
def pnl_dollars(self) -> float:
    """Short positions profit when price decreases."""
    multiplier = 1 if self.direction == 'Short' else -1
    price_diff = (self.entry_price - self.current_price) * multiplier
    return price_diff * self.quantity * 100
```

get_trades calculation (alpaca_sync_service.py:714-734):
```python
total_premium = float(row['total_premium'] or 0)
pnl_percent = 0.0
if total_premium != 0:
    pnl_percent = (total_premium / abs(total_premium)) * 100 if total_premium else 0.0

trades.append({
    'entry_price': total_premium,
    'pnl': total_premium,
    'pnl_percent': pnl_percent,
})
```

**Problems**:
1. OptionLeg uses (entry - current) * multiplier * quantity * 100
2. get_trades() uses total premium only and returns ±100% or 0%
3. The two methods will give completely different P&L values for the same position
4. This will cause confusion in the UI where trades show different P&L than positions

**Recommended Solutions**:

1. **Use OptionLeg's calculation as the standard (Preferred)**
   - Reuse the pnl_dollars logic in get_trades()
   - Match current price from latest position data
   - Rationale: Consistent methodology across the codebase

2. **Document the difference clearly**
   - Add comment explaining why aggregated trade P&L differs from leg P&L
   - Create separate methods: `pnl_per_leg()` vs `pnl_aggregated()`
   - Rationale: If both approaches are valid, document the use cases

3. **Create a unified P&L calculator**
   ```python
   class PnLCalculator:
       @staticmethod
       def calculate_leg_pnl(
           entry_price: float,
           current_price: float,
           quantity: int,
           direction: str
       ) -> float:
           multiplier = 1 if direction == 'Short' else -1
           price_diff = (entry_price - current_price) * multiplier
           return price_diff * quantity * 100
   ```
   - Use in both OptionLeg and get_trades()
   - Rationale: Single source of truth for calculation

---

#### Issue #8: No Error Boundary or Recovery in Vue Component

**Description**: The TradeStats Vue component lacks an error boundary or recovery mechanism. If the API returns invalid data after being parsed, there's no graceful degradation. Additionally, if the component unmounts while an API call is pending, it can cause memory leaks.

**Location**:
- File: `apps/orchestrator_3_stream/frontend/src/components/TradeStats.vue`
- Lines: `152-189`

**Offending Code**:
```typescript
const fetchTrades = async () => {
  loading.value = true
  error.value = null

  try {
    const [tradesRes, statsRes] = await Promise.all([
      tradeApi.getTrades({ status: statusFilter.value === 'all' ? undefined : statusFilter.value }),
      tradeApi.getTradeStats(statusFilter.value === 'all' ? undefined : statusFilter.value)
    ])
    // ... no cancellation token, no cleanup on unmount
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'An error occurred'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchTrades()
})
```

**Issues**:
1. No AbortController - if component unmounts, pending requests continue and try to update state
2. No retry mechanism for transient failures
3. No timeout handling (apiClient has 30s timeout, but no frontend timeout)
4. If JSON.parse fails in apiClient interceptor, error isn't caught properly
5. No tracking of which request failed if Promise.all rejects

**Recommended Solutions**:

1. **Add AbortController for cleanup (Preferred)**
   ```typescript
   import { ref, onMounted, onUnmounted } from 'vue'

   const abortController = ref<AbortController | null>(null)

   const fetchTrades = async () => {
     loading.value = true
     error.value = null

     // Cancel previous request if still pending
     abortController.value?.abort()
     abortController.value = new AbortController()

     try {
       const [tradesRes, statsRes] = await Promise.all([
         tradeApi.getTrades({
           signal: abortController.value.signal,
           status: statusFilter.value === 'all' ? undefined : statusFilter.value
         }),
         tradeApi.getTradeStats({
           signal: abortController.value.signal,
           status: statusFilter.value === 'all' ? undefined : statusFilter.value
         })
       ])
       // ...
     } catch (e) {
       if (e.name !== 'AbortError') {
         error.value = e instanceof Error ? e.message : 'An error occurred'
       }
     } finally {
       loading.value = false
     }
   }

   onUnmounted(() => {
     abortController.value?.abort()
   })
   ```
   - Rationale: Prevents memory leaks from stale API calls

2. **Add retry with exponential backoff**
   ```typescript
   const fetchTrades = async (retries = 3) => {
     for (let i = 0; i < retries; i++) {
       try {
         // ... fetch logic ...
         return
       } catch (e) {
         if (i === retries - 1) throw e
         await new Promise(r => setTimeout(r, 1000 * Math.pow(2, i)))
       }
     }
   }
   ```
   - Rationale: Handles transient network failures gracefully

3. **Validate response schema before using**
   ```typescript
   import { z } from 'zod'

   const TradeStatsSchema = z.object({
     status: z.enum(['success', 'error']),
     total_pnl: z.number().optional().default(0),
     // ...
   })

   const validated = TradeStatsSchema.parse(statsRes)
   ```
   - Rationale: Catches API contract violations at parse time

---

### ⚡ MEDIUM RISK (Fix Soon)

#### Issue #9: Missing orders Field in Trade Type Causes Data Loss

**Description**: The TradeResponse Pydantic model includes an `orders: List[dict] = []` field that provides individual order details for each aggregated trade. However, the frontend TypeScript interface doesn't include this field, so this data is silently dropped. Frontend users cannot see the individual orders that make up a trade.

**Location**:
- Backend: `apps/orchestrator_3_stream/backend/modules/alpaca_models.py` - Line 443
- Frontend: `apps/orchestrator_3_stream/frontend/src/types/trades.ts` - Missing field

**Offending Code**:
```python
class TradeResponse(BaseModel):
    # ... fields ...
    orders: List[dict] = []  # This field is sent to frontend but...
```

```typescript
export interface Trade {
    // ... fields ...
    leg_count: number
    // ... orders field is NOT defined here!
}
```

**Recommended Solutions**:

1. **Add orders array to Trade interface (Preferred)**
   ```typescript
   export interface TradeOrder {
     id: string
     symbol: string
     side: 'buy' | 'sell'
     qty: number
     filled_avg_price: number
     status: string
     filled_at?: string
   }

   export interface Trade {
     // ... existing fields ...
     orders: TradeOrder[]  // Add this
   }
   ```
   - Rationale: Preserves data integrity and allows expanded UI features

2. **Remove orders from backend response**
   - If frontend doesn't need individual orders, remove from TradeResponse
   - Reduces API payload size
   - Rationale: If data isn't used, don't send it

3. **Make orders optional in both**
   - Backend: keep `orders: List[dict] = []`
   - Frontend: add `orders?: Order[]`
   - Load orders only on demand when user clicks on trade
   - Rationale: Lazy loading optimization

---

#### Issue #10: No Timeout or Concurrency Handling for Concurrent Requests

**Description**: The Vue component uses Promise.all for concurrent API requests (line 157-160) without handling the case where one request succeeds but the other fails, or where requests take longer than expected. The apiClient has a 30s timeout, but this isn't exposed to the component for UX purposes.

**Location**:
- File: `apps/orchestrator_3_stream/frontend/src/components/TradeStats.vue`
- Lines: `157-160`

**Offending Code**:
```typescript
const [tradesRes, statsRes] = await Promise.all([
  tradeApi.getTrades({ status: statusFilter.value === 'all' ? undefined : statusFilter.value }),
  tradeApi.getTradeStats(statusFilter.value === 'all' ? undefined : statusFilter.value)
])
```

**Issues**:
1. If trades request succeeds but stats request fails, Promise.all rejects everything
2. UI shows error for both even though trades data is available
3. No timeout specific to this component's needs (30s is backend timeout)
4. User can't tell which request failed or why

**Recommended Solutions**:

1. **Use Promise.allSettled for partial success (Preferred)**
   ```typescript
   const [tradesResult, statsResult] = await Promise.allSettled([
     tradeApi.getTrades({ status: ... }),
     tradeApi.getTradeStats(status: ...)
   ])

   if (tradesResult.status === 'fulfilled') {
     const tradesRes = tradesResult.value
     if (tradesRes.status === 'success') {
       trades.value = tradesRes.trades
     } else {
       logger.warn('Trades fetch failed but stats may still work')
     }
   } else {
     logger.error('Trades request failed:', tradesResult.reason)
   }

   if (statsResult.status === 'fulfilled') {
     const statsRes = statsResult.value
     if (statsRes.status === 'success') {
       stats.value = { ... }
     }
   }
   ```
   - Rationale: Allows UI to show partial data if one request fails

2. **Sequential requests with timeouts**
   ```typescript
   const controller = new AbortController()
   const timeoutId = setTimeout(() => controller.abort(), 15000) // 15s timeout

   try {
     const tradesRes = await tradeApi.getTrades({ signal: controller.signal })
     const statsRes = await tradeApi.getTradeStats({ signal: controller.signal })
     // ...
   } finally {
     clearTimeout(timeoutId)
   }
   ```
   - Rationale: Gives feedback if requests are taking too long

3. **Separate loading states per request**
   ```typescript
   const loadingTrades = ref(false)
   const loadingStats = ref(false)
   const errorTrades = ref<string | null>(null)
   const errorStats = ref<string | null>(null)

   // Load independently
   await Promise.all([
     (async () => {
       try {
         loadingTrades.value = true
         const res = await tradeApi.getTrades(...)
         // ...
       } catch (e) {
         errorTrades.value = ...
       } finally {
         loadingTrades.value = false
       }
     })(),
     // similar for stats
   ])
   ```
   - Rationale: Clear status per data type

---

#### Issue #11: Incomplete Win Rate Calculation with Division by Zero Risk

**Description**: The `get_trade_stats()` method calculates win_rate by dividing winning trades by total trades without proper null checking. If there are no trades, this causes a division by zero.

**Location**:
- File: `apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py`
- Lines: `750-764`

**Offending Code**:
```python
async def get_trade_stats(self, status: Optional[str] = None) -> dict:
    trades = await self.get_trades(status=status, limit=1000)

    total_pnl = sum(t['pnl'] for t in trades)
    winning = [t for t in trades if t['pnl'] > 0]
    losing = [t for t in trades if t['pnl'] < 0]
    open_trades = [t for t in trades if t['status'] == 'open']
    closed_trades = [t for t in trades if t['status'] in ('closed', 'expired')]

    return {
        'total_pnl': total_pnl,
        'win_rate': (len(winning) / len(trades) * 100) if trades else 0,  # Good!
        'total_trades': len(trades),
        'winning_trades': len(winning),
        'losing_trades': len(losing),
        'open_trades': len(open_trades),
        'closed_trades': len(closed_trades),
    }
```

**Issues**:
1. Line 758 handles the zero case: `if trades else 0` - actually GOOD
2. BUT: The win_rate calculation has a logical issue:
   - If there are trades with pnl=0 (break-even), they're counted in denominator but not in winning/losing
   - win_rate should only count closed trades (open trades shouldn't affect win rate)
   - Real win rate should exclude break-even trades or explicitly count them

**Recommended Solutions**:

1. **Calculate win rate on closed trades only (Preferred)**
   ```python
   closed_trades_list = [t for t in trades if t['status'] in ('closed', 'expired')]
   profitable_trades = [t for t in closed_trades_list if t['pnl'] > 0]

   win_rate = (len(profitable_trades) / len(closed_trades_list) * 100) if closed_trades_list else 0
   ```
   - Rationale: Industry standard - win rate excludes open/pending trades

2. **Document the calculation method**
   ```python
   # Win rate = (# profitable closed trades) / (# total closed trades)
   # Open trades are not included in win rate calculation
   # Break-even trades count as losses
   ```
   - Rationale: Clear specification prevents future confusion

3. **Return additional metrics**
   ```python
   return {
       'total_pnl': total_pnl,
       'win_rate': win_rate,
       'total_trades': len(trades),
       'winning_trades': len(winning),
       'losing_trades': len(losing),
       'breakeven_trades': len([t for t in trades if t['pnl'] == 0]),
       'open_trades': len(open_trades),
       'closed_trades': len(closed_trades),
       'win_rate_basis': 'closed_trades'  # Clarify what win_rate is based on
   }
   ```
   - Rationale: Frontend can use correct denominator for display

---

#### Issue #12: Fragile Status Filtering Logic

**Description**: The status filtering in `get_trades()` method has fragile logic that filters after the query completes. This means if a user requests only "open" trades, the database still returns all trades which are then filtered in Python, wasting database resources.

**Location**:
- File: `apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py`
- Lines: `700-711`

**Offending Code**:
```python
for row in rows:
    # Determine status from order statuses
    statuses = set(row['statuses'])
    if 'filled' in statuses and len(statuses) == 1:
        trade_status = 'closed'
    elif 'expired' in statuses:
        trade_status = 'expired'
    elif statuses & {'new', 'accepted', 'partially_filled'}:
        trade_status = 'open'
    else:
        trade_status = 'closed'

    # Filter by status if requested
    if status and status != 'all' and trade_status != status:
        continue  # Skip this trade!
```

**Issues**:
1. Status filtering happens in Python AFTER fetching from database
2. If user requests 100 trades but only 10 are "open", database fetches all 100 then Python discards 90
3. Query doesn't pass status filter to SQL WHERE clause
4. Status determination logic is complex and error-prone - relies on order statuses

**Recommended Solutions**:

1. **Filter by status in SQL query (Preferred)**
   ```python
   async def get_trades(
       self,
       underlying: Optional[str] = None,
       status: Optional[str] = None,  # open, closed, all
       limit: int = 100,
       offset: int = 0
   ) -> List[dict]:
       # Translate status to order status filter
       status_filter = None
       if status == 'open':
           status_filter = ['new', 'accepted', 'partially_filled']
       elif status == 'closed':
           status_filter = ['filled']
       elif status == 'expired':
           status_filter = ['expired']

       query = """
           SELECT
               trade_id,
               ...
           FROM alpaca_orders
           WHERE ($1::TEXT IS NULL OR underlying = $1)
       """

       if status_filter:
           query += f" AND status = ANY($4)"
           # Need to modify query building...

       query += """
           GROUP BY trade_id, underlying, strategy_type
           ORDER BY entry_date DESC
           LIMIT $2 OFFSET $3
       """
   ```
   - Rationale: Database applies filter before returning data

2. **Simplify status determination**
   ```python
   # Status is determined from the MAX(status) of all orders in the trade
   # Get the "final" status from the latest order
   # Instead of complex status determination logic
   ```
   - Rationale: Easier to test and maintain

3. **Document status determination logic**
   ```python
   def determine_trade_status(order_statuses: List[str]) -> str:
       """
       Determine trade status from order statuses.

       Logic:
       - If any order is 'expired', trade is 'expired'
       - If all orders are 'filled', trade is 'closed'
       - If any order is 'new'/'accepted'/'partially_filled', trade is 'open'
       - Otherwise, trade is 'closed'

       This assumes orders in a trade move from open → closed together.
       """
       statuses = set(order_statuses)
       # ... implementation ...
   ```
   - Rationale: Makes logic explicit and testable

---

### 💡 LOW RISK (Nice to Have)

#### Issue #13: Missing JSDoc Comments on API Methods

**Description**: The tradeApi object in api.ts has public methods with no JSDoc comments explaining parameters, return types, or usage examples. This makes the API less discoverable for frontend developers.

**Location**:
- File: `apps/orchestrator_3_stream/frontend/src/services/api.ts`
- Lines: `48-70`

**Offending Code**:
```typescript
export const tradeApi = {
  async getTrades(params?: {
    underlying?: string
    status?: 'open' | 'closed' | 'all'
    limit?: number
    offset?: number
  }): Promise<TradeListResponse> {
    // No JSDoc!
    const response = await apiClient.get('/api/trades', { params })
    return response.data
  },
  // ...
}
```

**Suggested Solution**:
```typescript
export const tradeApi = {
  /**
   * Fetch aggregated trade history.
   *
   * @param params - Query parameters
   * @param params.underlying - Filter by underlying symbol (e.g., "SPY")
   * @param params.status - Filter by trade status: 'open', 'closed', or 'all' (default)
   * @param params.limit - Maximum number of trades to return (default: 100)
   * @param params.offset - Pagination offset (default: 0)
   * @returns TradeListResponse with trades array or error message
   * @example
   *   const res = await tradeApi.getTrades({ underlying: 'SPY', status: 'closed' })
   */
  async getTrades(params?: {
    underlying?: string
    status?: 'open' | 'closed' | 'all'
    limit?: number
    offset?: number
  }): Promise<TradeListResponse> {
    const response = await apiClient.get('/api/trades', { params })
    return response.data
  },
  // ...
}
```

---

## Plan Compliance Check

No plan file was provided, so this review is based on the review focus areas specified in the command.

**Review Focus Areas Completed**:
- ✅ Check API contracts match between backend and frontend
- ✅ Verify SQL query correctness and NULL handling
- ✅ Check error handling comprehensiveness
- ✅ Verify P&L calculation logic
- ✅ Check for missing null checks and edge cases
- ✅ Verify status filtering
- ✅ Check TypeScript types match API responses
- ✅ Verify Vue component handles loading, error, and empty states

---

## Verification Checklist

- [ ] **BLOCKER #1**: SQL injection vulnerability fixed and query parameter indexing corrected
- [ ] **BLOCKER #2**: P&L calculation logic properly implements position matching
- [ ] **BLOCKER #3**: orders field added to TypeScript Trade interface
- [ ] **BLOCKER #4**: API response contracts use discriminated union types or are explicitly documented
- [ ] **HIGH RISK #5**: Frontend null checks added for API responses
- [ ] **HIGH RISK #6**: NULL value handling added to backend SQL aggregation
- [ ] **HIGH RISK #7**: P&L calculation methods unified across OptionLeg and get_trades()
- [ ] **HIGH RISK #8**: AbortController and error boundary added to Vue component
- [ ] **MEDIUM #9**: orders field properly typed and handled in frontend
- [ ] **MEDIUM #10**: Promise.allSettled or sequential requests with proper error handling
- [ ] **MEDIUM #11**: Win rate calculation uses closed trades only
- [ ] **MEDIUM #12**: Status filtering moved to SQL query layer
- [ ] TypeScript strict mode enabled to catch more errors
- [ ] Integration tests created for all trade aggregation logic
- [ ] API contract testing (e.g., Supertest for backend endpoints)

---

## Final Verdict

**Status**: ⚠️ **FAIL** - Multiple blockers prevent merge

**Reasoning**:

This implementation demonstrates good architectural patterns and covers the complete data flow from backend to frontend. However, there are **4 critical blockers** that must be fixed before this can be merged to production:

1. **SQL Injection Risk** (Issue #1): The dynamic query building pattern is dangerous and the parameter indexing is incorrect
2. **Incorrect P&L Calculation** (Issue #2): The P&L logic returns ±100% instead of actual percentages and conflates premium with profit
3. **Missing Type Contract** (Issue #3): The orders field is missing from TypeScript interface, causing type mismatches
4. **Response Contract Confusion** (Issue #4): TradeStatsResponse has ambiguous optional fields depending on status

Additionally, there are **4 high-risk issues** that make the code fragile:
- Frontend doesn't validate API responses, leading to potential runtime errors
- Backend doesn't handle NULL values from aggregation queries
- P&L calculation methods are inconsistent between models
- Vue component lacks error boundaries and can cause memory leaks

The implementation is **60-70% complete** with good structure but requires significant fixes to the core P&L calculation logic and type contracts before production deployment.

**Next Steps**:

1. **Immediate (Blockers)**:
   - Fix SQL injection vulnerability and parameter indexing
   - Rewrite P&L calculation to properly match positions and calculate accurate percentages
   - Add orders field to TypeScript interface
   - Create discriminated union types for TradeStatsResponse

2. **Before Merge (High Risk)**:
   - Add defensive null checks throughout frontend
   - Add COALESCE to SQL aggregation queries
   - Unify P&L calculation into single method
   - Add AbortController and error handling to Vue component

3. **Follow-up (Medium/Low Risk)**:
   - Move status filtering to SQL layer
   - Fix win rate calculation to use closed trades only
   - Add JSDoc comments to API methods
   - Create comprehensive test suite for trade aggregation

---

**Report Generated**: 2026-01-14T00:00:00Z
**Reviewer**: Code Review Agent
**Review Type**: Full Implementation Review

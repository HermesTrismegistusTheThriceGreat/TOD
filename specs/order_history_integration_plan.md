# Plan: Order History Integration - Backend to Frontend

## Task Description

Connect the backend Alpaca order history table (`alpaca_orders`) with the frontend Trade Stats page (`TradeStats.vue`) to display real trading data instead of mock data. This involves creating API endpoints, data transformation logic, and updating the frontend to consume the real data.

## Objective

When this plan is complete:
1. The Trade Stats page will display real order history from the Alpaca API stored in the database
2. Orders will be grouped by `trade_id` to show aggregated trades (multi-leg strategies)
3. Summary statistics (Total P&L, Win Rate, Total Trades) will be calculated from real data
4. Filtering by status (All/Open/Closed) will work with real data
5. The UI will handle loading, error, and empty states gracefully

## Problem Statement

The frontend Trade Stats page (`TradeStats.vue`) currently uses hardcoded mock data and has no connection to the backend. Meanwhile, the backend has:
- A complete database schema for `alpaca_orders` with trade grouping
- An `AlpacaSyncService` that fetches and persists order history from Alpaca
- Pydantic models (`AlpacaOrder`) for data validation

However, there are no API endpoints to expose this data to the frontend, and no data transformation layer to convert the backend order format to the frontend's Trade interface.

## Solution Approach

1. **Create Backend API Endpoints**: Expose order history and trade statistics via RESTful endpoints
2. **Implement Data Aggregation**: Group orders by `trade_id` and calculate P&L per strategy
3. **Add Response Models**: Create Pydantic models for API responses
4. **Update Frontend Service**: Add API client methods to fetch trade data
5. **Connect TradeStats Component**: Replace mock data with real API calls
6. **Implement Error Handling**: Add robust loading, error, and empty states

## Relevant Files

### Backend - Existing Files to Modify
- `apps/orchestrator_3_stream/backend/main.py` - Add new API endpoints for order history
- `apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py` - Add trade aggregation methods
- `apps/orchestrator_3_stream/backend/modules/alpaca_models.py` - Add response models for trade history

### Backend - Reference Files
- `apps/orchestrator_db/models.py` - Contains `AlpacaOrder` and `AlpacaPosition` models
- `apps/orchestrator_db/migrations/10_alpaca_orders.sql` - Database schema with trade_id grouping

### Frontend - Existing Files to Modify
- `apps/orchestrator_3_stream/frontend/src/components/TradeStats.vue` - Replace mock data with API calls
- `apps/orchestrator_3_stream/frontend/src/services/api.ts` - Add trade history API methods

### New Files
- `apps/orchestrator_3_stream/frontend/src/types/trades.ts` - TypeScript interfaces for trade data

## Implementation Phases

### Phase 1: Foundation - Backend API Contract

Define the API contract and create response models that will be used by both backend and frontend.

**Key Decisions:**
- Use `trade_id` as the primary grouping mechanism for multi-leg orders
- Aggregate P&L across all legs in a trade
- Map Alpaca order statuses to simplified frontend statuses (open/closed/expired)

### Phase 2: Core Implementation - Backend Endpoints

Create the API endpoints and data transformation logic:
1. `/api/orders` - List order history with filtering
2. `/api/trades` - Aggregated trades (grouped by trade_id)
3. `/api/trade-stats` - Summary statistics

### Phase 3: Integration & Polish - Frontend Connection

Update the frontend to consume real data:
1. Add API service methods
2. Replace mock data in TradeStats component
3. Implement proper error handling
4. Add loading states

## Step by Step Tasks

### 1. Create Trade Response Models (Backend)

Add new Pydantic models to `alpaca_models.py` for API responses:

```python
# Add to apps/orchestrator_3_stream/backend/modules/alpaca_models.py

from typing import List, Optional, Literal
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict

class TradeResponse(BaseModel):
    """Single trade (aggregated from orders with same trade_id)"""
    model_config = ConfigDict(from_attributes=True)

    trade_id: str
    ticker: str  # underlying symbol
    strategy: str  # iron_condor, vertical_spread, etc.
    direction: Literal['Long', 'Short']  # dominant direction
    entry_date: str  # ISO format date
    exit_date: Optional[str] = None
    entry_price: float  # total premium received/paid
    exit_price: Optional[float] = None
    quantity: int  # number of contracts (max across legs)
    pnl: float  # total P&L in dollars
    pnl_percent: float  # P&L as percentage
    status: Literal['open', 'closed', 'expired']
    leg_count: int  # number of legs in this trade
    orders: List[dict] = []  # individual order details

class TradeListResponse(BaseModel):
    """Response for GET /api/trades"""
    model_config = ConfigDict(from_attributes=True)

    status: Literal['success', 'error']
    trades: List[TradeResponse] = []
    total_count: int = 0
    message: Optional[str] = None

class TradeStatsResponse(BaseModel):
    """Response for GET /api/trade-stats"""
    model_config = ConfigDict(from_attributes=True)

    status: Literal['success', 'error']
    total_pnl: float = 0.0
    win_rate: float = 0.0  # percentage
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    open_trades: int = 0
    closed_trades: int = 0
    message: Optional[str] = None
```

- Add `TradeResponse` model mapping to frontend `Trade` interface
- Add `TradeListResponse` for paginated list
- Add `TradeStatsResponse` for summary statistics

### 2. Add Trade Aggregation Methods (Backend)

Add methods to `AlpacaSyncService` for aggregating orders into trades:

```python
# Add to apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py

async def get_trades(
    self,
    underlying: Optional[str] = None,
    status: Optional[str] = None,  # open, closed, all
    limit: int = 100,
    offset: int = 0
) -> List[dict]:
    """
    Get aggregated trades (orders grouped by trade_id).

    Logic:
    1. Query orders grouped by trade_id
    2. Aggregate P&L across all legs
    3. Determine overall trade status
    4. Calculate direction (net position)
    """
    pool = await self._get_pool()

    async with pool.acquire() as conn:
        # Query with aggregation
        query = """
            SELECT
                trade_id,
                underlying,
                strategy_type,
                MIN(submitted_at) as entry_date,
                MAX(COALESCE(filled_at, canceled_at, expired_at)) as exit_date,
                SUM(CASE WHEN side = 'sell' THEN filled_avg_price * filled_qty * 100
                         ELSE -filled_avg_price * filled_qty * 100 END) as total_premium,
                MAX(filled_qty) as quantity,
                COUNT(*) as leg_count,
                array_agg(DISTINCT status) as statuses
            FROM alpaca_orders
            WHERE ($1::TEXT IS NULL OR underlying = $1)
            GROUP BY trade_id, underlying, strategy_type
            ORDER BY entry_date DESC
            LIMIT $2 OFFSET $3
        """
        rows = await conn.fetch(query, underlying, limit, offset)

        trades = []
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

            trades.append({
                'trade_id': str(row['trade_id']),
                'ticker': row['underlying'],
                'strategy': row['strategy_type'] or 'options',
                'direction': 'Short',  # Default for premium-selling strategies
                'entry_date': row['entry_date'].isoformat() if row['entry_date'] else None,
                'exit_date': row['exit_date'].isoformat() if row['exit_date'] else None,
                'entry_price': float(row['total_premium'] or 0),
                'quantity': int(row['quantity'] or 0),
                'pnl': float(row['total_premium'] or 0),  # Simplified - needs position matching
                'pnl_percent': 0.0,  # Calculate based on cost basis
                'status': trade_status,
                'leg_count': row['leg_count'],
            })

        return trades

async def get_trade_stats(self, status: Optional[str] = None) -> dict:
    """Get aggregated trade statistics."""
    trades = await self.get_trades(status=status, limit=1000)

    total_pnl = sum(t['pnl'] for t in trades)
    winning = [t for t in trades if t['pnl'] > 0]
    losing = [t for t in trades if t['pnl'] < 0]
    open_trades = [t for t in trades if t['status'] == 'open']
    closed_trades = [t for t in trades if t['status'] in ('closed', 'expired')]

    return {
        'total_pnl': total_pnl,
        'win_rate': (len(winning) / len(trades) * 100) if trades else 0,
        'total_trades': len(trades),
        'winning_trades': len(winning),
        'losing_trades': len(losing),
        'open_trades': len(open_trades),
        'closed_trades': len(closed_trades),
    }
```

- Add `get_trades()` method to aggregate orders by trade_id
- Add `get_trade_stats()` method for summary calculations
- Implement P&L calculation logic (entry premium vs exit premium)
- Handle status aggregation across multiple legs

### 3. Create API Endpoints (Backend)

Add new endpoints to `main.py`:

```python
# Add to apps/orchestrator_3_stream/backend/main.py

from modules.alpaca_sync_service import init_alpaca_sync_service, get_alpaca_sync_service
from modules.alpaca_models import TradeListResponse, TradeStatsResponse

# In lifespan, after alpaca_service initialization:
alpaca_sync_service = await init_alpaca_sync_service(app, alpaca_service)

@app.get("/api/trades", response_model=TradeListResponse, tags=["Trades"])
async def get_trades(
    request: Request,
    underlying: Optional[str] = None,
    status: Optional[str] = None,  # open, closed, all
    limit: int = 100,
    offset: int = 0
):
    """Get aggregated trade history."""
    try:
        sync_service = get_alpaca_sync_service(request.app)
        trades = await sync_service.get_trades(
            underlying=underlying,
            status=status,
            limit=limit,
            offset=offset
        )
        return TradeListResponse(
            status="success",
            trades=trades,
            total_count=len(trades)
        )
    except Exception as e:
        return TradeListResponse(status="error", message=str(e))

@app.get("/api/trade-stats", response_model=TradeStatsResponse, tags=["Trades"])
async def get_trade_stats(request: Request, status: Optional[str] = None):
    """Get trade summary statistics."""
    try:
        sync_service = get_alpaca_sync_service(request.app)
        stats = await sync_service.get_trade_stats(status=status)
        return TradeStatsResponse(status="success", **stats)
    except Exception as e:
        return TradeStatsResponse(status="error", message=str(e))

@app.post("/api/sync-orders", tags=["Trades"])
async def sync_orders(request: Request):
    """Trigger manual sync of orders from Alpaca."""
    try:
        sync_service = get_alpaca_sync_service(request.app)
        orders = await sync_service.sync_orders()
        return {
            "status": "success",
            "synced_count": len(orders),
            "message": f"Synced {len(orders)} orders from Alpaca"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

- Add `GET /api/trades` endpoint with filtering
- Add `GET /api/trade-stats` endpoint for summary stats
- Add `POST /api/sync-orders` to trigger manual sync
- Initialize `AlpacaSyncService` in lifespan

### 4. Create TypeScript Types (Frontend)

Create type definitions for trade data:

```typescript
// apps/orchestrator_3_stream/frontend/src/types/trades.ts

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
}

export interface TradeListResponse {
  status: 'success' | 'error'
  trades: Trade[]
  total_count: number
  message?: string
}

export interface TradeStats {
  total_pnl: number
  win_rate: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  open_trades: number
  closed_trades: number
}

export interface TradeStatsResponse {
  status: 'success' | 'error'
  total_pnl?: number
  win_rate?: number
  total_trades?: number
  winning_trades?: number
  losing_trades?: number
  open_trades?: number
  closed_trades?: number
  message?: string
}
```

- Create `Trade` interface matching backend `TradeResponse`
- Create `TradeListResponse` and `TradeStatsResponse` types
- Export for use in components

### 5. Add API Methods (Frontend)

Add trade-related API methods to the service layer:

```typescript
// Add to apps/orchestrator_3_stream/frontend/src/services/api.ts

import type { TradeListResponse, TradeStatsResponse } from '@/types/trades'

// Trade History API
export const tradeApi = {
  async getTrades(params?: {
    underlying?: string
    status?: 'open' | 'closed' | 'all'
    limit?: number
    offset?: number
  }): Promise<TradeListResponse> {
    const response = await apiClient.get('/api/trades', { params })
    return response.data
  },

  async getTradeStats(status?: string): Promise<TradeStatsResponse> {
    const response = await apiClient.get('/api/trade-stats', {
      params: { status }
    })
    return response.data
  },

  async syncOrders(): Promise<{ status: string; synced_count?: number; message?: string }> {
    const response = await apiClient.post('/api/sync-orders')
    return response.data
  }
}
```

- Add `tradeApi.getTrades()` method with filtering support
- Add `tradeApi.getTradeStats()` for summary statistics
- Add `tradeApi.syncOrders()` to trigger manual sync

### 6. Update TradeStats Component (Frontend)

Replace mock data with real API calls:

```vue
<!-- Key changes for apps/orchestrator_3_stream/frontend/src/components/TradeStats.vue -->

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { tradeApi } from '@/services/api'
import type { Trade } from '@/types/trades'

const loading = ref(false)
const error = ref<string | null>(null)
const statusFilter = ref<'all' | 'open' | 'closed'>('all')
const trades = ref<Trade[]>([])
const stats = ref({
  total_pnl: 0,
  win_rate: 0,
  total_trades: 0
})

const filteredTrades = computed(() => {
  if (statusFilter.value === 'all') return trades.value
  return trades.value.filter(t => t.status === statusFilter.value)
})

const fetchTrades = async () => {
  loading.value = true
  error.value = null

  try {
    const [tradesRes, statsRes] = await Promise.all([
      tradeApi.getTrades({ status: statusFilter.value === 'all' ? undefined : statusFilter.value }),
      tradeApi.getTradeStats(statusFilter.value === 'all' ? undefined : statusFilter.value)
    ])

    if (tradesRes.status === 'success') {
      trades.value = tradesRes.trades
    } else {
      error.value = tradesRes.message || 'Failed to fetch trades'
    }

    if (statsRes.status === 'success') {
      stats.value = {
        total_pnl: statsRes.total_pnl || 0,
        win_rate: statsRes.win_rate || 0,
        total_trades: statsRes.total_trades || 0
      }
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'An error occurred'
  } finally {
    loading.value = false
  }
}

// Watch for filter changes
watch(statusFilter, () => {
  fetchTrades()
})

onMounted(() => {
  fetchTrades()
})

const handleRefresh = () => {
  fetchTrades()
}
</script>
```

- Import `tradeApi` and type definitions
- Replace mock data with reactive state
- Implement `fetchTrades()` async function
- Add error state handling
- Watch filter changes to refetch data
- Update computed properties to use real stats

### 7. Add Error State UI (Frontend)

Add error state to the component template:

```vue
<!-- Add error state to template -->
<div v-if="error" class="state-container error-state">
  <el-icon :size="32"><WarningFilled /></el-icon>
  <span>{{ error }}</span>
  <el-button type="primary" size="small" @click="handleRefresh">
    Retry
  </el-button>
</div>
```

- Add error state between loading and empty states
- Show error message with retry button
- Add appropriate styling for error state

### 8. Update Summary Pills (Frontend)

Update summary pills to use real stats:

```vue
<!-- Update summary pills to use stats ref -->
<div class="summary-pill">
  <span class="label">Total P&L:</span>
  <span class="value" :class="getPnlClass(stats.total_pnl)">
    {{ formatMoney(stats.total_pnl) }}
  </span>
</div>
<div class="summary-pill">
  <span class="label">Win Rate:</span>
  <span class="value">{{ stats.win_rate.toFixed(1) }}%</span>
</div>
<div class="summary-pill">
  <span class="label">Trades:</span>
  <span class="value">{{ stats.total_trades }}</span>
</div>
```

- Bind to `stats` reactive object instead of computed from trades
- Format win rate with decimal place

### 9. Map Strategy Display Names (Frontend)

Add strategy display name mapping:

```typescript
const formatStrategy = (strategy: string): string => {
  const strategyMap: Record<string, string> = {
    'iron_condor': 'Iron Condor',
    'vertical_spread': 'Vertical Spread',
    'strangle': 'Strangle',
    'straddle': 'Straddle',
    'single_leg': 'Single Leg',
    'options': 'Options'
  }
  return strategyMap[strategy] || strategy
}
```

- Map snake_case backend values to Title Case display
- Use in table column template

### 10. Validate Integration

Run end-to-end tests to verify:

- Backend starts without errors
- API endpoints respond correctly
- Frontend fetches and displays data
- Filtering works as expected
- Error states are handled gracefully

## Testing Strategy

### Backend Tests

1. **Unit Tests for Trade Aggregation**
   - Test `get_trades()` returns correct grouping by trade_id
   - Test P&L calculation across multiple legs
   - Test status determination from mixed order statuses
   - Test filtering by underlying and status

2. **API Endpoint Tests**
   - Test `GET /api/trades` returns valid response
   - Test `GET /api/trade-stats` calculation accuracy
   - Test error handling for database failures
   - Test pagination (limit/offset)

3. **Integration Tests**
   - Test full flow: sync orders -> query trades
   - Test with real Alpaca sandbox data
   - Test circuit breaker behavior

### Frontend Tests

1. **Component Tests**
   - Test loading state renders correctly
   - Test error state with retry button
   - Test empty state when no trades
   - Test filter switching updates data

2. **API Integration Tests**
   - Mock API responses and verify component updates
   - Test error handling from API failures
   - Test concurrent request handling

## Acceptance Criteria

1. **API Endpoints Work**
   - [ ] `GET /api/trades` returns list of aggregated trades
   - [ ] `GET /api/trade-stats` returns correct summary statistics
   - [ ] `POST /api/sync-orders` triggers Alpaca sync
   - [ ] Filtering by status works correctly

2. **Frontend Displays Real Data**
   - [ ] Trade history table shows real orders from database
   - [ ] Summary pills (Total P&L, Win Rate, Trades) use real stats
   - [ ] Status filter (All/Open/Closed) filters correctly
   - [ ] Refresh button triggers new data fetch

3. **Error Handling**
   - [ ] Loading spinner shows during data fetch
   - [ ] Error message displays on API failure
   - [ ] Retry button triggers new fetch after error
   - [ ] Empty state shows when no trades match filter

4. **Data Mapping**
   - [ ] Backend AlpacaOrder maps to frontend Trade interface
   - [ ] Strategy types display with proper formatting
   - [ ] P&L values show with correct sign and color
   - [ ] Dates format correctly

## Validation Commands

Execute these commands to validate the task is complete:

```bash
# 1. Verify backend code compiles
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/backend
uv run python -m py_compile main.py modules/alpaca_sync_service.py modules/alpaca_models.py

# 2. Start backend and test endpoints
uv run python main.py &
sleep 3
curl http://127.0.0.1:9403/api/trades
curl http://127.0.0.1:9403/api/trade-stats

# 3. Verify frontend builds
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend
npm run build

# 4. Run frontend type check
npm run type-check

# 5. Start frontend and verify in browser
npm run dev
# Open http://localhost:5173 and navigate to Trade Stats page
```

## Notes

### Dependencies

- No new Python packages needed - uses existing `asyncpg`, `pydantic`, `fastapi`
- No new npm packages needed - uses existing `axios`, `element-plus`

### Database Initialization

Before testing, ensure Alpaca orders are synced:
1. Configure Alpaca API credentials in `.env`
2. Call `POST /api/sync-orders` to populate database
3. Alternatively, orders sync automatically when positions are fetched

### Future Enhancements

1. **WebSocket Updates**: Push trade updates via WebSocket for real-time UI
2. **Trade Details Modal**: Click on trade to see individual leg details
3. **P&L Chart**: Add visualization of P&L over time
4. **Export to CSV**: Add button to export trade history
5. **Date Range Filter**: Filter trades by entry/exit date range

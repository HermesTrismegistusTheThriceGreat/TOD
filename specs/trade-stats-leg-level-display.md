# Plan: Trade Stats Leg-Level Display with Open/Close Matching

## Task Description
Implement a comprehensive trade stats display feature that shows leg-level data with proper open/close order matching. Each trade (strategy) should be displayed as a card containing all its legs with entry/exit details, per-leg P&L, and an aggregated summary row. The feature requires backend changes to return properly structured leg-level data and new frontend components to display this data.

## Objective
When this plan is complete, users will be able to view their trade history as cards where each card represents a complete strategy (e.g., iron butterfly GLD0001) with:
- All legs displayed in a table (423 Call, 423 Put, 431 Call, 415 Put)
- Entry (open) and exit (close) details per leg
- Per-leg P&L calculations
- An aggregated summary row showing total credit, total debit, and net P&L

## Problem Statement
The current `get_trades()` method in `alpaca_sync_service.py` aggregates orders too aggressively - it returns trade-level summaries but doesn't include individual leg records. The frontend expects leg-level data (the `orders` field in `Trade` interface is always empty). This makes it impossible to display the detailed view shown in the target design.

The database already stores all required leg-level data in `alpaca_orders` table (symbol, side, strike, expiry, filled_avg_price, etc.). The gap is purely in the query/aggregation logic.

## Solution Approach
1. **Backend**: Create a new `get_detailed_trades()` method that:
   - Groups orders by trade_id
   - Within each trade, groups by leg (symbol)
   - Matches opening orders with closing orders per leg
   - Computes per-leg and total P&L
   - Returns structured data with legs array and summary object

2. **API**: Create new endpoint `GET /api/trades/detailed` returning `DetailedTradeListResponse`

3. **Frontend**: Create new Vue components following the specified naming convention:
   - `TradeStatsCard.vue` - Single trade/strategy card
   - `LegStatsTable.vue` - Table of legs within a card
   - `TradeStatsSummary.vue` - Footer row with totals
   - `TradeStatsGrid.vue` - Grid layout of multiple trade cards

## Relevant Files

### Backend Files (Modify)
- `/apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py` - Add `get_detailed_trades()` method (lines 676-789 for reference)
- `/apps/orchestrator_3_stream/backend/modules/alpaca_models.py` - Add new Pydantic response models
- `/apps/orchestrator_3_stream/backend/main.py` - Add new `/api/trades/detailed` endpoint (around line 1476)

### Frontend Files (Modify)
- `/apps/orchestrator_3_stream/frontend/src/types/trades.ts` - Add new TypeScript interfaces for detailed trades
- `/apps/orchestrator_3_stream/frontend/src/services/api.ts` - Add new API method `getDetailedTrades()`

### Frontend Files (Create)
- `/apps/orchestrator_3_stream/frontend/src/components/TradeStatsCard.vue` - New component
- `/apps/orchestrator_3_stream/frontend/src/components/LegStatsTable.vue` - New component
- `/apps/orchestrator_3_stream/frontend/src/components/TradeStatsSummary.vue` - New component
- `/apps/orchestrator_3_stream/frontend/src/components/TradeStatsGrid.vue` - New component

### Reference Files (Read Only)
- `/apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue` - Card pattern reference (lines 268-698)
- `/apps/orchestrator_3_stream/frontend/src/components/TradeStats.vue` - Existing trade display, formatting functions
- `/apps/orchestrator_3_stream/frontend/src/styles/global.css` - CSS variables and patterns
- `/apps/orchestrator_db/models.py` - Database models (AlpacaOrder lines 397-482)
- `/apps/orchestrator_db/migrations/10_alpaca_orders.sql` - Database schema reference

## Implementation Phases

### Phase 1: Foundation - Backend Data Layer
Define new Pydantic models and implement the core data aggregation logic.

### Phase 2: Core Implementation - API & Frontend Types
Create API endpoint and TypeScript interfaces for the new data structure.

### Phase 3: Integration & Polish - Frontend Components
Build Vue components following established patterns, integrate with API.

## Step by Step Tasks

### 1. Add Pydantic Models for Detailed Trade Response
**File:** `/apps/orchestrator_3_stream/backend/modules/alpaca_models.py`

Add these new models after the existing `TradeResponse` class (around line 443):

```python
class LegDetail(BaseModel):
    """Individual leg within a trade with open/close matching."""
    leg_number: int
    description: str  # e.g., "423 Call"
    symbol: str  # OCC symbol
    strike: float
    option_type: Literal['call', 'put']

    # Open (entry) details
    open_action: Literal['BUY', 'SELL']
    open_fill: float  # filled_avg_price for opening order
    open_date: Optional[str] = None

    # Close (exit) details - None if position still open
    close_action: Optional[Literal['BUY', 'SELL']] = None
    close_fill: Optional[float] = None
    close_date: Optional[str] = None

    # Computed P&L
    quantity: int
    pnl_per_contract: float  # P&L per single contract
    pnl_total: float  # P&L for all contracts (quantity * 100 * pnl_per_contract)
    is_closed: bool = False


class TradeSummary(BaseModel):
    """Aggregated summary for all legs in a trade."""
    total_credit: float  # Total premium received from selling
    total_debit: float  # Total cost from buying
    net_pnl_per_contract: float
    net_pnl_total: float
    leg_count: int
    closed_legs: int
    open_legs: int


class DetailedTrade(BaseModel):
    """Complete trade with leg-level detail."""
    trade_id: str
    ticker: str
    strategy: str  # iron_butterfly, vertical_spread, etc.
    direction: Literal['Long', 'Short']  # Net direction based on premium
    status: Literal['open', 'closed', 'partial']  # partial = some legs closed
    entry_date: str
    exit_date: Optional[str] = None
    expiry_date: Optional[str] = None

    legs: List[LegDetail]
    summary: TradeSummary


class DetailedTradeListResponse(BaseModel):
    """Response for detailed trades endpoint."""
    status: Literal['success', 'error']
    trades: List[DetailedTrade] = []
    total_count: int = 0
    message: Optional[str] = None
```

### 2. Implement get_detailed_trades() Method
**File:** `/apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py`

Add this new method after `get_trades()` (around line 789):

```python
async def get_detailed_trades(
    self,
    underlying: Optional[str] = None,
    status: Optional[str] = None,  # open, closed, partial, all
    limit: int = 50,
    offset: int = 0
) -> List[dict]:
    """
    Get trades with full leg-level detail and open/close matching.

    For each trade:
    1. Fetch all orders grouped by trade_id
    2. Group orders by leg (symbol)
    3. Match opening order with closing order per leg
    4. Calculate per-leg P&L
    5. Aggregate into summary

    Returns:
        List of DetailedTrade dictionaries
    """
    pool = await self._get_pool()

    async with pool.acquire() as conn:
        # Step 1: Get all trade_ids with basic info
        trade_query = """
            SELECT DISTINCT
                trade_id,
                underlying,
                strategy_type,
                MIN(expiry_date) as expiry_date,
                MIN(submitted_at) as entry_date
            FROM alpaca_orders
            WHERE ($1::TEXT IS NULL OR underlying = $1)
            GROUP BY trade_id, underlying, strategy_type
            ORDER BY entry_date DESC
            LIMIT $2 OFFSET $3
        """
        trade_rows = await conn.fetch(trade_query, underlying, limit, offset)

        if not trade_rows:
            return []

        detailed_trades = []

        for trade_row in trade_rows:
            trade_id = trade_row['trade_id']

            # Step 2: Fetch all orders for this trade
            orders_query = """
                SELECT
                    alpaca_order_id, symbol, underlying, side,
                    qty, filled_qty, filled_avg_price, status,
                    option_type, strike_price, expiry_date,
                    leg_number, submitted_at, filled_at
                FROM alpaca_orders
                WHERE trade_id = $1
                ORDER BY leg_number, submitted_at
            """
            orders = await conn.fetch(orders_query, trade_id)

            # Step 3: Group orders by symbol (leg)
            legs_by_symbol: Dict[str, List[dict]] = defaultdict(list)
            for order in orders:
                legs_by_symbol[order['symbol']].append(dict(order))

            # Step 4: Build leg details with open/close matching
            leg_details = []
            total_credit = 0.0
            total_debit = 0.0
            closed_legs = 0

            for leg_num, (symbol, leg_orders) in enumerate(legs_by_symbol.items(), 1):
                # Sort by time to identify open vs close
                leg_orders.sort(key=lambda x: x['submitted_at'] or datetime.min)

                # First order is the opening order
                open_order = leg_orders[0]
                close_order = leg_orders[1] if len(leg_orders) > 1 else None

                # Determine open action
                open_action = 'SELL' if open_order['side'] == 'sell' else 'BUY'
                open_fill = float(open_order['filled_avg_price'] or 0)

                # Determine close action (opposite of open)
                close_action = None
                close_fill = None
                close_date = None
                is_closed = False

                if close_order:
                    close_action = 'BUY' if close_order['side'] == 'buy' else 'SELL'
                    close_fill = float(close_order['filled_avg_price'] or 0)
                    close_date = close_order['filled_at'].isoformat() if close_order['filled_at'] else None
                    is_closed = True
                    closed_legs += 1

                # Calculate P&L per leg
                quantity = int(open_order['filled_qty'] or open_order['qty'] or 1)

                if open_action == 'SELL':
                    # Sold to open: credit received
                    total_credit += open_fill * quantity * 100
                    if is_closed:
                        # Bought to close: debit paid
                        total_debit += close_fill * quantity * 100
                        pnl_per_contract = open_fill - close_fill
                    else:
                        pnl_per_contract = open_fill  # Unrealized
                else:
                    # Bought to open: debit paid
                    total_debit += open_fill * quantity * 100
                    if is_closed:
                        # Sold to close: credit received
                        total_credit += close_fill * quantity * 100
                        pnl_per_contract = close_fill - open_fill
                    else:
                        pnl_per_contract = -open_fill  # Unrealized (cost)

                pnl_total = pnl_per_contract * quantity * 100

                # Build description (e.g., "423 Call")
                strike = open_order['strike_price']
                opt_type = (open_order['option_type'] or 'option').capitalize()
                description = f"{int(strike)} {opt_type}" if strike else symbol

                leg_details.append({
                    'leg_number': leg_num,
                    'description': description,
                    'symbol': symbol,
                    'strike': float(strike) if strike else 0,
                    'option_type': (open_order['option_type'] or 'call').lower(),
                    'open_action': open_action,
                    'open_fill': open_fill,
                    'open_date': open_order['submitted_at'].isoformat() if open_order['submitted_at'] else None,
                    'close_action': close_action,
                    'close_fill': close_fill,
                    'close_date': close_date,
                    'quantity': quantity,
                    'pnl_per_contract': round(pnl_per_contract, 4),
                    'pnl_total': round(pnl_total, 2),
                    'is_closed': is_closed
                })

            # Step 5: Build summary
            net_pnl_total = total_credit - total_debit
            avg_quantity = sum(leg['quantity'] for leg in leg_details) / len(leg_details) if leg_details else 1
            net_pnl_per_contract = net_pnl_total / (avg_quantity * 100) if avg_quantity else 0

            # Determine trade status
            open_legs = len(leg_details) - closed_legs
            if closed_legs == 0:
                trade_status = 'open'
            elif open_legs == 0:
                trade_status = 'closed'
            else:
                trade_status = 'partial'

            # Filter by status if requested
            if status and status != 'all' and trade_status != status:
                continue

            # Determine direction (net credit = Short, net debit = Long)
            direction = 'Short' if total_credit > total_debit else 'Long'

            # Find exit date (latest close date)
            exit_dates = [leg['close_date'] for leg in leg_details if leg['close_date']]
            exit_date = max(exit_dates) if exit_dates else None

            detailed_trades.append({
                'trade_id': str(trade_id),
                'ticker': trade_row['underlying'] or 'UNKNOWN',
                'strategy': trade_row['strategy_type'] or 'options',
                'direction': direction,
                'status': trade_status,
                'entry_date': trade_row['entry_date'].isoformat() if trade_row['entry_date'] else None,
                'exit_date': exit_date,
                'expiry_date': trade_row['expiry_date'].isoformat() if trade_row['expiry_date'] else None,
                'legs': leg_details,
                'summary': {
                    'total_credit': round(total_credit, 2),
                    'total_debit': round(total_debit, 2),
                    'net_pnl_per_contract': round(net_pnl_per_contract, 4),
                    'net_pnl_total': round(net_pnl_total, 2),
                    'leg_count': len(leg_details),
                    'closed_legs': closed_legs,
                    'open_legs': open_legs
                }
            })

        return detailed_trades
```

### 3. Add API Endpoint for Detailed Trades
**File:** `/apps/orchestrator_3_stream/backend/main.py`

Add new endpoint after the existing `/api/trades` endpoint (around line 1476):

```python
@app.get("/api/trades/detailed", response_model=DetailedTradeListResponse, tags=["Trades"])
async def get_detailed_trades(
    request: Request,
    underlying: Optional[str] = None,
    status: Optional[str] = None,  # open, closed, partial, all
    limit: int = 50,
    offset: int = 0
):
    """
    Get detailed trade history with leg-level data.

    Returns trades with full leg breakdown including:
    - Open/close action and fill prices per leg
    - Per-leg P&L calculations
    - Aggregated summary per trade

    Args:
        underlying: Filter by underlying symbol (e.g., "SPY")
        status: Filter by status ("open", "closed", "partial", or "all")
        limit: Maximum number of trades to return (default 50)
        offset: Offset for pagination

    Returns:
        DetailedTradeListResponse with list of detailed trades
    """
    try:
        logger.http_request("GET", "/api/trades/detailed")
        sync_service = get_alpaca_sync_service(request.app)
        trades = await sync_service.get_detailed_trades(
            underlying=underlying,
            status=status,
            limit=limit,
            offset=offset
        )
        logger.http_request("GET", "/api/trades/detailed", 200)
        return DetailedTradeListResponse(
            status="success",
            trades=trades,
            total_count=len(trades)
        )
    except Exception as e:
        logger.error(f"Failed to get detailed trades: {e}")
        return DetailedTradeListResponse(status="error", message=str(e))
```

Add imports at top of main.py:
```python
from .modules.alpaca_models import DetailedTradeListResponse
```

### 4. Add TypeScript Types for Detailed Trades
**File:** `/apps/orchestrator_3_stream/frontend/src/types/trades.ts`

Add these new interfaces after the existing types:

```typescript
/**
 * Individual leg with open/close matching
 */
export interface LegDetail {
  leg_number: number
  description: string  // e.g., "423 Call"
  symbol: string
  strike: number
  option_type: 'call' | 'put'

  // Open (entry) details
  open_action: 'BUY' | 'SELL'
  open_fill: number
  open_date: string | null

  // Close (exit) details
  close_action: 'BUY' | 'SELL' | null
  close_fill: number | null
  close_date: string | null

  // P&L
  quantity: number
  pnl_per_contract: number
  pnl_total: number
  is_closed: boolean
}

/**
 * Aggregated summary for all legs in a trade
 */
export interface TradeSummary {
  total_credit: number
  total_debit: number
  net_pnl_per_contract: number
  net_pnl_total: number
  leg_count: number
  closed_legs: number
  open_legs: number
}

/**
 * Complete trade with leg-level detail
 */
export interface DetailedTrade {
  trade_id: string
  ticker: string
  strategy: string
  direction: 'Long' | 'Short'
  status: 'open' | 'closed' | 'partial'
  entry_date: string
  exit_date: string | null
  expiry_date: string | null
  legs: LegDetail[]
  summary: TradeSummary
}

export interface DetailedTradeListResponse {
  status: 'success' | 'error'
  trades: DetailedTrade[]
  total_count: number
  message?: string
}
```

### 5. Add API Method for Detailed Trades
**File:** `/apps/orchestrator_3_stream/frontend/src/services/api.ts`

Add new method to the `tradeApi` object:

```typescript
async getDetailedTrades(params?: {
  underlying?: string
  status?: 'open' | 'closed' | 'partial' | 'all'
  limit?: number
  offset?: number
}): Promise<DetailedTradeListResponse> {
  const response = await apiClient.get('/api/trades/detailed', { params })
  return response.data
}
```

Add import at top:
```typescript
import type { DetailedTradeListResponse } from '@/types/trades'
```

### 6. Create LegStatsTable.vue Component
**File:** `/apps/orchestrator_3_stream/frontend/src/components/LegStatsTable.vue`

Create table component displaying legs within a trade card:

```vue
<template>
  <div class="leg-stats-table">
    <el-table
      :data="legs"
      class="legs-table"
      :header-cell-style="headerStyle"
      :cell-style="cellStyle"
    >
      <el-table-column label="Leg" width="120" align="center">
        <template #default="{ row }">
          <span class="leg-description">{{ row.description }}</span>
        </template>
      </el-table-column>

      <el-table-column label="Open Action" width="120" align="center">
        <template #default="{ row }">
          <span :class="getActionClass(row.open_action)">
            {{ row.open_action }} to open
          </span>
        </template>
      </el-table-column>

      <el-table-column label="Open Fill" width="100" align="right">
        <template #default="{ row }">
          <span class="fill-price">{{ formatPrice(row.open_fill) }}</span>
        </template>
      </el-table-column>

      <el-table-column label="Close Action" width="120" align="center">
        <template #default="{ row }">
          <span v-if="row.close_action" :class="getActionClass(row.close_action)">
            {{ row.close_action }} to close
          </span>
          <span v-else class="text-muted">—</span>
        </template>
      </el-table-column>

      <el-table-column label="Close Fill" width="100" align="right">
        <template #default="{ row }">
          <span v-if="row.close_fill !== null" class="fill-price">
            {{ formatPrice(row.close_fill) }}
          </span>
          <span v-else class="text-muted">—</span>
        </template>
      </el-table-column>

      <el-table-column label="P&L/Share" width="110" align="right">
        <template #default="{ row }">
          <span :class="getPnlClass(row.pnl_per_contract)">
            {{ formatPnlPerShare(row.pnl_per_contract) }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="P&L Total" width="130" align="right">
        <template #default="{ row }">
          <span :class="getPnlClass(row.pnl_total)" class="pnl-total">
            {{ formatMoney(row.pnl_total) }}
          </span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import type { LegDetail } from '@/types/trades'

defineProps<{
  legs: LegDetail[]
}>()

const headerStyle = {
  background: 'var(--bg-tertiary)',
  borderBottom: '1px solid var(--border-color)',
  color: 'var(--text-muted)',
  fontWeight: '600',
  fontSize: '0.75rem',
  textTransform: 'uppercase'
}

const cellStyle = {
  background: 'var(--bg-secondary)',
  borderBottom: '1px solid var(--border-light)'
}

const getActionClass = (action: string) => {
  return action === 'SELL' ? 'action-sell' : 'action-buy'
}

const getPnlClass = (value: number) => {
  if (value > 0) return 'positive'
  if (value < 0) return 'negative'
  return 'neutral'
}

const formatPrice = (value: number) => {
  return `$${value.toFixed(2)}`
}

const formatPnlPerShare = (value: number) => {
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${value.toFixed(2)}`
}

const formatMoney = (value: number) => {
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${Math.abs(value).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  })}`
}
</script>

<style scoped>
.leg-stats-table {
  width: 100%;
}

.legs-table {
  --el-table-border-color: var(--border-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.leg-description {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--text-primary);
}

.action-sell {
  color: var(--status-warning);
  font-weight: 500;
}

.action-buy {
  color: var(--status-info);
  font-weight: 500;
}

.fill-price {
  font-family: var(--font-mono);
  color: var(--text-primary);
}

.positive {
  color: var(--status-success);
}

.negative {
  color: var(--status-error);
}

.neutral {
  color: var(--text-muted);
}

.text-muted {
  color: var(--text-muted);
}

.pnl-total {
  font-family: var(--font-mono);
  font-weight: 600;
}
</style>
```

### 7. Create TradeStatsSummary.vue Component
**File:** `/apps/orchestrator_3_stream/frontend/src/components/TradeStatsSummary.vue`

Create summary row component:

```vue
<template>
  <div class="trade-stats-summary">
    <div class="summary-row">
      <div class="summary-cell label">
        <span class="ticker">{{ ticker }}</span>
        <span class="total-label">TOTAL</span>
      </div>

      <div class="summary-cell">
        <span class="value">{{ formatMoney(summary.total_credit) }}</span>
        <span class="sublabel">credit</span>
      </div>

      <div class="summary-cell">
        <span class="value">{{ formatMoney(summary.total_debit) }}</span>
        <span class="sublabel">debit</span>
      </div>

      <div class="summary-cell">
        <span class="value" :class="getPnlClass(summary.net_pnl_per_contract)">
          {{ formatPnlPerShare(summary.net_pnl_per_contract) }}
        </span>
      </div>

      <div class="summary-cell pnl-cell">
        <span class="value pnl-total" :class="getPnlClass(summary.net_pnl_total)">
          {{ formatMoney(summary.net_pnl_total) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TradeSummary } from '@/types/trades'

defineProps<{
  ticker: string
  summary: TradeSummary
}>()

const getPnlClass = (value: number) => {
  if (value > 0) return 'positive'
  if (value < 0) return 'negative'
  return 'neutral'
}

const formatMoney = (value: number) => {
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${Math.abs(value).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  })}`
}

const formatPnlPerShare = (value: number) => {
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${value.toFixed(2)}`
}
</script>

<style scoped>
.trade-stats-summary {
  background: var(--bg-tertiary);
  border-top: 2px solid var(--border-color);
  padding: var(--spacing-md);
}

.summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-lg);
}

.summary-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.summary-cell.label {
  flex-direction: row;
  gap: var(--spacing-sm);
  flex: 1;
}

.ticker {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--accent-primary);
}

.total-label {
  font-weight: 700;
  color: var(--text-primary);
  text-transform: uppercase;
}

.value {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 1rem;
  color: var(--text-primary);
}

.sublabel {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: lowercase;
}

.pnl-cell {
  min-width: 120px;
  text-align: right;
}

.pnl-total {
  font-size: 1.1rem;
}

.positive {
  color: var(--status-success);
}

.negative {
  color: var(--status-error);
}

.neutral {
  color: var(--text-muted);
}
</style>
```

### 8. Create TradeStatsCard.vue Component
**File:** `/apps/orchestrator_3_stream/frontend/src/components/TradeStatsCard.vue`

Create main card component:

```vue
<template>
  <el-card class="trade-stats-card">
    <!-- Card Header -->
    <div class="card-header">
      <div class="header-left">
        <span class="trade-id">{{ trade.trade_id.slice(0, 8) }}</span>
        <span class="ticker">{{ trade.ticker }}</span>
        <el-tag
          :type="getStrategyTagType(trade.strategy)"
          size="small"
          effect="dark"
        >
          {{ formatStrategy(trade.strategy) }}
        </el-tag>
      </div>
      <div class="header-right">
        <el-tag
          :type="getStatusTagType(trade.status)"
          size="small"
          effect="plain"
        >
          {{ trade.status.toUpperCase() }}
        </el-tag>
        <span class="expiry" v-if="trade.expiry_date">
          Exp: {{ formatDate(trade.expiry_date) }}
        </span>
      </div>
    </div>

    <!-- Legs Table -->
    <div class="card-content">
      <LegStatsTable :legs="trade.legs" />
    </div>

    <!-- Summary Footer -->
    <TradeStatsSummary
      :ticker="trade.trade_id.slice(0, 8)"
      :summary="trade.summary"
    />
  </el-card>
</template>

<script setup lang="ts">
import type { DetailedTrade } from '@/types/trades'
import LegStatsTable from './LegStatsTable.vue'
import TradeStatsSummary from './TradeStatsSummary.vue'

defineProps<{
  trade: DetailedTrade
}>()

const getStrategyTagType = (strategy: string) => {
  const types: Record<string, string> = {
    iron_butterfly: 'warning',
    vertical_spread: 'primary',
    strangle: 'success',
    straddle: 'info',
    single_leg: '',
  }
  return types[strategy] || ''
}

const getStatusTagType = (status: string) => {
  const types: Record<string, string> = {
    open: 'info',
    closed: 'success',
    partial: 'warning',
  }
  return types[status] || ''
}

const formatStrategy = (strategy: string) => {
  return strategy.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric'
  })
}
</script>

<style scoped>
.trade-stats-card {
  --card-bg: var(--bg-secondary);
  --card-border: var(--border-color);

  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  overflow: hidden;
}

.trade-stats-card :deep(.el-card__body) {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-tertiary);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.trade-id {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--text-muted);
}

.ticker {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--accent-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.expiry {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.card-content {
  padding: var(--spacing-lg);
}
</style>
```

### 9. Create TradeStatsGrid.vue Component
**File:** `/apps/orchestrator_3_stream/frontend/src/components/TradeStatsGrid.vue`

Create grid container component:

```vue
<template>
  <div class="trade-stats-grid">
    <!-- Header -->
    <div class="grid-header">
      <div class="header-left">
        <h2>Trade History</h2>
        <div class="header-stats" v-if="!loading && trades.length > 0">
          <div class="stat-pill">
            <span class="label">Trades:</span>
            <span class="value">{{ trades.length }}</span>
          </div>
          <div class="stat-pill">
            <span class="label">Total P&L:</span>
            <span class="value" :class="getTotalPnlClass">
              {{ formatMoney(totalPnl) }}
            </span>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <el-radio-group v-model="statusFilter" size="small">
          <el-radio-button label="all">ALL</el-radio-button>
          <el-radio-button label="open">OPEN</el-radio-button>
          <el-radio-button label="closed">CLOSED</el-radio-button>
        </el-radio-group>
        <el-button
          type="primary"
          size="small"
          :loading="syncing"
          @click="handleSync"
        >
          Sync Orders
        </el-button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <span>Loading trades...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <el-icon :size="32"><WarningFilled /></el-icon>
      <span>{{ error }}</span>
      <el-button type="primary" size="small" @click="fetchTrades">
        Retry
      </el-button>
    </div>

    <!-- Empty State -->
    <div v-else-if="trades.length === 0" class="empty-state">
      <el-icon :size="48"><Document /></el-icon>
      <span>No trades found</span>
      <el-button type="primary" size="small" @click="handleSync">
        Sync from Alpaca
      </el-button>
    </div>

    <!-- Trade Cards Grid -->
    <div v-else class="cards-grid">
      <TradeStatsCard
        v-for="trade in trades"
        :key="trade.trade_id"
        :trade="trade"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Loading, WarningFilled, Document } from '@element-plus/icons-vue'
import { tradeApi } from '@/services/api'
import type { DetailedTrade } from '@/types/trades'
import TradeStatsCard from './TradeStatsCard.vue'

const loading = ref(false)
const syncing = ref(false)
const error = ref<string | null>(null)
const trades = ref<DetailedTrade[]>([])
const statusFilter = ref<'all' | 'open' | 'closed'>('all')

const totalPnl = computed(() => {
  return trades.value.reduce((sum, t) => sum + t.summary.net_pnl_total, 0)
})

const getTotalPnlClass = computed(() => {
  if (totalPnl.value > 0) return 'positive'
  if (totalPnl.value < 0) return 'negative'
  return 'neutral'
})

const formatMoney = (value: number) => {
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${Math.abs(value).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  })}`
}

const fetchTrades = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await tradeApi.getDetailedTrades({
      status: statusFilter.value === 'all' ? undefined : statusFilter.value,
      limit: 50
    })

    if (response.status === 'success') {
      trades.value = response.trades
    } else {
      error.value = response.message || 'Failed to load trades'
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error'
  } finally {
    loading.value = false
  }
}

const handleSync = async () => {
  syncing.value = true
  try {
    await tradeApi.syncOrders()
    await fetchTrades()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Sync failed'
  } finally {
    syncing.value = false
  }
}

watch(statusFilter, () => {
  fetchTrades()
})

onMounted(() => {
  fetchTrades()
})
</script>

<style scoped>
.trade-stats-grid {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  overflow: hidden;
}

.grid-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.header-left h2 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--text-primary);
}

.header-stats {
  display: flex;
  gap: var(--spacing-sm);
}

.stat-pill {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  background: var(--bg-tertiary);
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid var(--border-light);
  font-size: 0.75rem;
}

.stat-pill .label {
  color: var(--text-muted);
}

.stat-pill .value {
  font-weight: 600;
  font-family: var(--font-mono);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.loading-state,
.error-state,
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  color: var(--text-muted);
}

.cards-grid {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.positive {
  color: var(--status-success);
}

.negative {
  color: var(--status-error);
}

.neutral {
  color: var(--text-muted);
}
</style>
```

### 10. Validate Implementation
- Run backend tests to verify new endpoint
- Run frontend build to check for TypeScript errors
- Test component rendering with mock data
- Verify API integration end-to-end

## Testing Strategy

### Backend Tests
1. **Unit test `get_detailed_trades()`**: Verify leg grouping and P&L calculation logic
2. **Test open/close matching**: Verify correct matching of opening and closing orders
3. **Test edge cases**: Single leg trades, partial closes, no closes

### Frontend Tests
1. **Component tests**: Verify each component renders correctly with mock data
2. **Integration test**: Verify API call and data binding
3. **Visual regression**: Check P&L colors, formatting, layout

### Test Commands
```bash
# Backend
cd apps/orchestrator_3_stream/backend
uv run pytest tests/ -v

# Frontend
cd apps/orchestrator_3_stream/frontend
npm run build  # Check for TypeScript errors
npm run test   # If tests exist
```

## Acceptance Criteria
- [ ] New `/api/trades/detailed` endpoint returns leg-level data
- [ ] Each trade shows all legs with entry (open) and exit (close) details
- [ ] P&L is calculated correctly per leg and aggregated in summary
- [ ] TradeStatsCard displays trade_id, ticker, strategy, and status
- [ ] LegStatsTable shows all columns: Leg, Open Action, Open Fill, Close Action, Close Fill, P&L/Share, P&L Total
- [ ] TradeStatsSummary shows total credit, total debit, and net P&L
- [ ] TradeStatsGrid displays multiple cards with filtering by status
- [ ] Colors correctly indicate profit (green) vs loss (red)
- [ ] Empty, loading, and error states are handled gracefully

## Validation Commands

```bash
# Start backend and verify endpoint
cd apps/orchestrator_3_stream
./start_be.sh &
curl http://localhost:8002/api/trades/detailed | jq

# Build frontend and check for errors
cd apps/orchestrator_3_stream/frontend
npm run build

# Run Python syntax check
uv run python -m py_compile apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py
uv run python -m py_compile apps/orchestrator_3_stream/backend/modules/alpaca_models.py
```

## Notes

### Import Updates Required
**Backend `main.py`:**
```python
from .modules.alpaca_models import (
    # ... existing imports ...
    DetailedTradeListResponse,
    LegDetail,
    TradeSummary,
    DetailedTrade
)
```

**Backend `alpaca_sync_service.py`:**
```python
from collections import defaultdict  # Already imported
from datetime import datetime  # Already imported
```

### CSS Variables Reference
All new components should use these global CSS variables:
- `--bg-primary`, `--bg-secondary`, `--bg-tertiary` - backgrounds
- `--text-primary`, `--text-secondary`, `--text-muted` - text colors
- `--status-success` (#10b981) - profit/positive
- `--status-error` (#ef4444) - loss/negative
- `--status-warning` (#f59e0b) - sell actions
- `--status-info` (#3b82f6) - buy actions
- `--accent-primary` (#06b6d4) - ticker highlight
- `--font-mono` - monospace for prices/numbers
- `--spacing-xs` through `--spacing-xl` - consistent spacing

### Database Schema Note
No database migrations required. The existing `alpaca_orders` table already stores all leg-level data needed:
- `trade_id` - groups related orders
- `leg_number` - orders legs within trade
- `symbol` - OCC symbol for leg identification
- `side` - buy/sell
- `filled_avg_price` - fill price
- `strike_price`, `option_type` - option details
- `submitted_at`, `filled_at` - timestamps for ordering

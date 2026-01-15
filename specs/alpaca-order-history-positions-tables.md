# Plan: Alpaca Order History and Open Positions Backend Tables

## Task Description
Create database tables to store Alpaca order history and open positions data, with a critical `trade_id` field that links related orders together for multi-leg strategies (iron condors, spreads, strangles). This enables grouping all legs of a strategy as a single logical trade for display and analysis.

## Objective
When this plan is complete, the system will have:
1. Two new PostgreSQL tables (`alpaca_orders` and `alpaca_positions`)
2. Corresponding Pydantic models in `models.py`
3. A sync service to fetch and persist Alpaca data with intelligent `trade_id` assignment
4. Database schema optimized for filtering, sorting, and grouping trades by strategy

## Problem Statement
Currently, Alpaca position data is fetched in real-time but not persisted. This means:
- No historical order data is available
- Multi-leg strategies cannot be grouped together for analysis
- No ability to filter/sort orders by date, symbol, or strategy type
- Frontend cannot display order history page

## Solution Approach
1. Create database schema following existing migration patterns (CREATE IF NOT EXISTS, indexes, comments)
2. Add Pydantic models following `models.py` conventions (field_validator, ConfigDict)
3. Create a sync service that:
   - Fetches orders/positions from Alpaca API
   - Assigns `trade_id` to link related orders (same underlying, expiry, time window)
   - Uses existing AlpacaService patterns (circuit breaker, rate limiter)
4. Design schema to support future frontend order history page

## Relevant Files
Use these files to complete the task:

- `apps/orchestrator_db/migrations/9_ai_developer_workflows.sql` - Latest migration pattern to follow
- `apps/orchestrator_db/migrations/8_orchestrator_chat.sql` - Example of comprehensive table structure with CHECK constraints
- `apps/orchestrator_db/models.py` - Pydantic model patterns (field_validator, ConfigDict)
- `apps/orchestrator_db/run_migrations.py` - Add new migration to MIGRATIONS list
- `apps/orchestrator_3_stream/backend/modules/alpaca_models.py` - Existing Alpaca models (OCCSymbol, IronCondorPosition)
- `apps/orchestrator_3_stream/backend/modules/alpaca_service.py` - Service patterns (circuit breaker, rate limiter)

### New Files
- `apps/orchestrator_db/migrations/10_alpaca_orders.sql` - New migration with both tables
- `apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py` - Service for syncing Alpaca data to database

## Implementation Phases

### Phase 1: Foundation
Create database schema with tables, indexes, and constraints. Update Pydantic models.

### Phase 2: Core Implementation
Implement sync service with trade_id assignment logic and Alpaca API integration.

### Phase 3: Integration & Polish
Test migrations, validate data integrity, and ensure proper error handling.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Create Migration File (10_alpaca_orders.sql)
Create `apps/orchestrator_db/migrations/10_alpaca_orders.sql` with both tables:

**alpaca_orders table:**
```sql
CREATE TABLE IF NOT EXISTS alpaca_orders (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Alpaca identifiers
    alpaca_order_id TEXT NOT NULL UNIQUE,  -- Alpaca's UUID
    client_order_id TEXT,

    -- Trade grouping (CRITICAL)
    trade_id UUID NOT NULL,  -- Links related orders together
    strategy_type TEXT CHECK (strategy_type IN (
        'iron_condor', 'vertical_spread', 'strangle',
        'straddle', 'single_leg', 'options'
    )),
    leg_number INTEGER,  -- 1-4 for iron condors

    -- Order details
    symbol TEXT NOT NULL,  -- OCC option symbol
    underlying TEXT NOT NULL,  -- Underlying ticker (SPY, QQQ)
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    qty DECIMAL(12, 4) NOT NULL,
    filled_qty DECIMAL(12, 4) DEFAULT 0,
    order_type TEXT CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit')),
    time_in_force TEXT CHECK (time_in_force IN ('day', 'gtc', 'opg', 'cls', 'ioc', 'fok')),

    -- Pricing
    limit_price DECIMAL(12, 4),
    stop_price DECIMAL(12, 4),
    filled_avg_price DECIMAL(12, 4),

    -- Status
    status TEXT NOT NULL CHECK (status IN (
        'new', 'partially_filled', 'filled', 'done_for_day',
        'canceled', 'expired', 'replaced', 'pending_cancel',
        'pending_replace', 'accepted', 'pending_new', 'accepted_for_bidding',
        'stopped', 'rejected', 'suspended', 'calculated'
    )),

    -- Option details
    expiry_date DATE,
    strike_price DECIMAL(12, 4),
    option_type TEXT CHECK (option_type IN ('call', 'put')),

    -- Timestamps from Alpaca
    submitted_at TIMESTAMPTZ,
    filled_at TIMESTAMPTZ,
    expired_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ,

    -- Metadata
    raw_data JSONB DEFAULT '{}'::jsonb,

    -- Our timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**alpaca_positions table:**
```sql
CREATE TABLE IF NOT EXISTS alpaca_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Trade grouping
    trade_id UUID,  -- Links to orders

    -- Position identifiers
    symbol TEXT NOT NULL,  -- OCC option symbol
    underlying TEXT NOT NULL,  -- Underlying ticker

    -- Position details
    qty DECIMAL(12, 4) NOT NULL,
    side TEXT CHECK (side IN ('long', 'short')),
    avg_entry_price DECIMAL(12, 4),
    current_price DECIMAL(12, 4),
    market_value DECIMAL(12, 4),
    cost_basis DECIMAL(12, 4),

    -- P/L
    unrealized_pl DECIMAL(12, 4),
    unrealized_plpc DECIMAL(12, 6),  -- Percentage
    unrealized_intraday_pl DECIMAL(12, 4),
    unrealized_intraday_plpc DECIMAL(12, 6),

    -- Option details
    expiry_date DATE,
    strike_price DECIMAL(12, 4),
    option_type TEXT CHECK (option_type IN ('call', 'put')),

    -- Status
    is_open BOOLEAN DEFAULT TRUE,

    -- Metadata
    raw_data JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint on symbol (only one position per symbol at a time)
    CONSTRAINT unique_open_position UNIQUE (symbol, is_open)
);
```

**Add indexes for performance:**
```sql
-- alpaca_orders indexes
CREATE INDEX IF NOT EXISTS idx_alpaca_orders_trade_id ON alpaca_orders(trade_id);
CREATE INDEX IF NOT EXISTS idx_alpaca_orders_symbol ON alpaca_orders(symbol);
CREATE INDEX IF NOT EXISTS idx_alpaca_orders_underlying ON alpaca_orders(underlying);
CREATE INDEX IF NOT EXISTS idx_alpaca_orders_status ON alpaca_orders(status);
CREATE INDEX IF NOT EXISTS idx_alpaca_orders_strategy ON alpaca_orders(strategy_type);
CREATE INDEX IF NOT EXISTS idx_alpaca_orders_submitted ON alpaca_orders(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_alpaca_orders_filled ON alpaca_orders(filled_at DESC);
CREATE INDEX IF NOT EXISTS idx_alpaca_orders_created ON alpaca_orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alpaca_orders_expiry ON alpaca_orders(expiry_date);
CREATE INDEX IF NOT EXISTS idx_alpaca_orders_trade_underlying ON alpaca_orders(trade_id, underlying);

-- alpaca_positions indexes
CREATE INDEX IF NOT EXISTS idx_alpaca_positions_trade_id ON alpaca_positions(trade_id);
CREATE INDEX IF NOT EXISTS idx_alpaca_positions_symbol ON alpaca_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_alpaca_positions_underlying ON alpaca_positions(underlying);
CREATE INDEX IF NOT EXISTS idx_alpaca_positions_is_open ON alpaca_positions(is_open);
CREATE INDEX IF NOT EXISTS idx_alpaca_positions_expiry ON alpaca_positions(expiry_date);
```

**Add table and column comments (follow existing pattern)**

### 2. Update models.py with Pydantic Models
Add to `apps/orchestrator_db/models.py`:

**AlpacaOrder model:**
```python
class AlpacaOrder(BaseModel):
    """
    Alpaca order history record with trade grouping.

    Maps to: alpaca_orders table
    """
    id: UUID
    alpaca_order_id: str
    client_order_id: Optional[str] = None

    # Trade grouping
    trade_id: UUID
    strategy_type: Optional[Literal['iron_condor', 'vertical_spread', 'strangle', 'straddle', 'single_leg', 'options']] = None
    leg_number: Optional[int] = None

    # Order details
    symbol: str
    underlying: str
    side: Literal['buy', 'sell']
    qty: float
    filled_qty: float = 0.0
    order_type: Optional[Literal['market', 'limit', 'stop', 'stop_limit']] = None
    time_in_force: Optional[Literal['day', 'gtc', 'opg', 'cls', 'ioc', 'fok']] = None

    # Pricing
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_avg_price: Optional[float] = None

    # Status
    status: str

    # Option details
    expiry_date: Optional[date] = None
    strike_price: Optional[float] = None
    option_type: Optional[Literal['call', 'put']] = None

    # Timestamps
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None

    # Metadata
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime

    # Add field_validators for UUID and Decimal conversion (follow existing pattern)
```

**AlpacaPosition model:**
```python
class AlpacaPosition(BaseModel):
    """
    Current open position from Alpaca.

    Maps to: alpaca_positions table
    """
    id: UUID
    trade_id: Optional[UUID] = None

    symbol: str
    underlying: str
    qty: float
    side: Optional[Literal['long', 'short']] = None

    # Pricing
    avg_entry_price: Optional[float] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    cost_basis: Optional[float] = None

    # P/L
    unrealized_pl: Optional[float] = None
    unrealized_plpc: Optional[float] = None
    unrealized_intraday_pl: Optional[float] = None
    unrealized_intraday_plpc: Optional[float] = None

    # Option details
    expiry_date: Optional[date] = None
    strike_price: Optional[float] = None
    option_type: Optional[Literal['call', 'put']] = None

    is_open: bool = True
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime

    # Add field_validators for UUID and Decimal conversion (follow existing pattern)
```

- Add both models to `__all__` exports

### 3. Update run_migrations.py
Add "10_alpaca_orders.sql" to the MIGRATIONS list:

```python
MIGRATIONS = [
    "0_orchestrator_agents.sql",
    "1_agents.sql",
    "2_prompts.sql",
    "3_agent_logs.sql",
    "4_system_logs.sql",
    "5_indexes.sql",
    "6_functions.sql",
    "7_triggers.sql",
    "8_orchestrator_chat.sql",
    "9_ai_developer_workflows.sql",
    "10_alpaca_orders.sql",  # NEW
]
```

- Also update the summary table in the `else` block to include the new tables

### 4. Create Alpaca Sync Service
Create `apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py`:

**Key components:**

```python
class AlpacaSyncService:
    """
    Service for syncing Alpaca data to database.

    Responsibilities:
    - Fetch and persist order history
    - Fetch and persist open positions
    - Assign trade_ids to link related orders
    - Detect strategy types from order patterns
    """

    def __init__(self, alpaca_service: AlpacaService, db_pool: Any):
        self._alpaca_service = alpaca_service
        self._db_pool = db_pool

    async def sync_orders(self, since: datetime = None) -> List[AlpacaOrder]:
        """Fetch and sync order history from Alpaca"""
        pass

    async def sync_positions(self) -> List[AlpacaPosition]:
        """Fetch and sync open positions from Alpaca"""
        pass

    def _assign_trade_id(self, orders: List[dict]) -> Dict[str, UUID]:
        """
        Assign trade_ids to group related orders.

        Logic:
        1. Group by underlying + expiry + time window (5 min)
        2. Detect strategy pattern (iron_condor, vertical_spread, etc.)
        3. Assign same UUID to all orders in group
        """
        pass

    def _detect_strategy(self, orders: List[dict]) -> str:
        """
        Detect strategy type from order leg patterns.

        Uses same logic as alpaca_models.py IronCondorPosition.detect_strategy()
        """
        pass
```

**Trade ID Assignment Logic:**
```python
def _assign_trade_id(self, orders: List[dict]) -> Dict[str, UUID]:
    """
    Group orders by:
    1. Same underlying symbol
    2. Same expiry date
    3. Submitted within 5-minute time window
    4. Strategy pattern detection

    Returns: mapping of alpaca_order_id -> trade_id
    """
    from collections import defaultdict
    from datetime import timedelta

    TIME_WINDOW = timedelta(minutes=5)

    # Group by underlying + expiry
    groups = defaultdict(list)
    for order in orders:
        occ = OCCSymbol.parse(order['symbol'])
        key = (occ.underlying, occ.expiry_date)
        groups[key].append(order)

    trade_id_map = {}

    for key, group_orders in groups.items():
        # Sort by submitted_at
        group_orders.sort(key=lambda x: x['submitted_at'])

        # Find clusters within time window
        clusters = []
        current_cluster = [group_orders[0]]

        for order in group_orders[1:]:
            prev_time = current_cluster[-1]['submitted_at']
            curr_time = order['submitted_at']

            if curr_time - prev_time <= TIME_WINDOW:
                current_cluster.append(order)
            else:
                clusters.append(current_cluster)
                current_cluster = [order]

        clusters.append(current_cluster)

        # Assign trade_id to each cluster
        for cluster in clusters:
            trade_id = uuid4()
            strategy = self._detect_strategy(cluster)

            for i, order in enumerate(cluster):
                trade_id_map[order['id']] = {
                    'trade_id': trade_id,
                    'strategy_type': strategy,
                    'leg_number': i + 1
                }

    return trade_id_map
```

### 5. Add Database Connection to Sync Service
- Use existing database pool pattern from orchestrator_db
- Use python-dotenv for DATABASE_URL
- Follow async patterns from existing services

### 6. Add Sync Endpoints (Optional - Future Enhancement)
Create REST endpoints in `alpaca_routes.py`:
- `POST /api/alpaca/sync/orders` - Trigger order sync
- `POST /api/alpaca/sync/positions` - Trigger position sync
- `GET /api/alpaca/orders` - Get order history with filters
- `GET /api/alpaca/orders/{trade_id}` - Get all orders for a trade group

### 7. Validate Implementation
- Run migration: `uv run apps/orchestrator_db/run_migrations.py`
- Test Pydantic models parse correctly
- Test sync service connects and fetches data
- Verify trade_id assignment groups orders correctly

## Testing Strategy

### Unit Tests
- Test OCCSymbol parsing for various option symbols
- Test trade_id assignment logic with mock orders
- Test strategy detection for iron condors, vertical spreads, straddles, strangles

### Integration Tests
- Test migration runs without errors
- Test sync service fetches real Alpaca data (use paper trading account)
- Test database CRUD operations for both tables
- Test unique constraints and CHECK constraints work

### Edge Cases
- Orders with missing timestamps
- Single-leg orders (should get unique trade_id)
- Orders placed exactly at time window boundary
- Positions with NULL trade_id (historical positions without order match)

## Acceptance Criteria

1. Migration `10_alpaca_orders.sql` runs successfully with no errors
2. Both `alpaca_orders` and `alpaca_positions` tables created with all indexes
3. `AlpacaOrder` and `AlpacaPosition` Pydantic models added to `models.py`
4. Models handle UUID/Decimal conversion correctly (follow existing patterns)
5. `run_migrations.py` updated with new migration file
6. Sync service can fetch orders from Alpaca API
7. Trade_id assignment correctly groups multi-leg strategies
8. Strategy detection matches existing `detect_strategy()` logic
9. All CHECK constraints validated (status, side, order_type, etc.)
10. Indexes support efficient filtering by date, symbol, strategy_type

## Validation Commands
Execute these commands to validate the task is complete:

- `uv run apps/orchestrator_db/run_migrations.py` - Run migrations to create tables
- `uv run python -m py_compile apps/orchestrator_db/models.py` - Verify models.py compiles
- `uv run python -c "from apps.orchestrator_db.models import AlpacaOrder, AlpacaPosition; print('Models import OK')"` - Test model imports
- `psql $DATABASE_URL -c "SELECT COUNT(*) FROM alpaca_orders;"` - Verify table exists
- `psql $DATABASE_URL -c "\d alpaca_orders"` - Check table structure
- `psql $DATABASE_URL -c "\di idx_alpaca_orders_*"` - Verify indexes created

## Notes

### Database Considerations
- Use DECIMAL(12, 4) for price fields to avoid floating point issues in financial calculations
- raw_data JSONB stores complete Alpaca API response for debugging/auditing
- trade_id is NOT NULL on orders (every order belongs to a trade group)
- trade_id is nullable on positions (may not always be linked)

### Trade ID Linking Strategy
- For new orders placed via our system: generate trade_id upfront before submitting
- For historical/imported orders: use time-window clustering algorithm
- Consider adding manual trade grouping UI in future

### Future Enhancements
- Add `alpaca_trades` table for higher-level trade tracking (open/closed status, total P/L)
- Add webhook handler for real-time order status updates
- Add scheduled job for periodic position/order sync
- Add database triggers for automatic updated_at timestamps (use existing pattern from 6_functions.sql)

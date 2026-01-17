# Plan: GLD Options Greeks Snapshots

## Task Description

Implement a system to capture and persist GLD option Greeks data from the Alpaca API into our Neon PostgreSQL database. The system will fetch snapshots 3 times daily (London session, US session, Asian session) containing delta, gamma, theta, vega, rho, implied volatility, and pricing data for all GLD option contracts.

## Objective

When complete, the system will:
1. Have a new `option_greeks_snapshots` table storing historical Greeks data
2. Have a Pydantic model for type-safe data handling
3. Have a service that fetches Greeks from Alpaca's options snapshot API
4. Run scheduled snapshots at 8:00 AM ET (London session), 2:00 PM ET (US session), and 9:30 PM ET (Asian session) every day of the week
5. Provide queryable historical Greeks data for analysis

## Problem Statement

We need to track option Greeks over time to analyze volatility patterns, delta exposure, and time decay characteristics for GLD options. Currently, we have no historical Greeks storage - only real-time data from websocket streams.

## Solution Approach

Leverage existing patterns from `alpaca_orders` and `alpaca_positions` tables, using:
- Alpaca's `OptionHistoricalDataClient.get_option_snapshot()` for data fetching
- `APScheduler` for scheduled execution (3x daily: London, US, and Asian sessions)
- Existing `asyncpg` connection pool and service patterns from `alpaca_sync_service.py`
- Pydantic models matching `apps/orchestrator_db/models.py` conventions

## Relevant Files

### Existing Files to Reference

- `apps/orchestrator_db/migrations/10_alpaca_orders.sql` - Template for SQL migration structure
- `apps/orchestrator_db/models.py` - Pydantic model patterns (AlpacaOrder, AlpacaPosition)
- `apps/orchestrator_db/sync_models.py` - Model sync mechanism
- `apps/orchestrator_3_stream/backend/modules/alpaca_service.py` - Alpaca client initialization
- `apps/orchestrator_3_stream/backend/modules/alpaca_sync_service.py` - Database persistence patterns
- `apps/orchestrator_3_stream/backend/modules/alpaca_models.py` - OCCSymbol parser
- `apps/orchestrator_3_stream/backend/modules/config.py` - Configuration patterns
- `apps/orchestrator_3_stream/backend/modules/database.py` - Connection pool management
- `apps/orchestrator_3_stream/backend/main.py` - FastAPI lifespan for service initialization

### New Files to Create

- `apps/orchestrator_db/migrations/12_option_greeks_snapshots.sql` - Database migration
- `apps/orchestrator_3_stream/backend/modules/greeks_snapshot_service.py` - Snapshot fetching and persistence
- `apps/orchestrator_3_stream/backend/modules/greeks_scheduler.py` - APScheduler configuration

## Implementation Phases

### Phase 1: Foundation (Database Layer)
- Create SQL migration for `option_greeks_snapshots` table
- Add Pydantic model `OptionGreeksSnapshot` to `models.py`
- Run `sync_models.py` to propagate changes

### Phase 2: Core Implementation (Service Layer)
- Create `GreeksSnapshotService` class following `AlpacaSyncService` patterns
- Implement Alpaca API integration using `OptionHistoricalDataClient`
- Implement batch insert with upsert logic (ON CONFLICT)
- Add pagination handling for large option chains

### Phase 3: Integration & Polish (Scheduler + Endpoints)
- Set up APScheduler with 3 daily jobs (8:00 AM, 2:00 PM, 9:30 PM ET)
- Integrate into FastAPI lifespan
- Add REST endpoints for manual trigger and query

## Step by Step Tasks

### 1. Create Database Migration

Create `apps/orchestrator_db/migrations/12_option_greeks_snapshots.sql`:

```sql
-- ============================================================================
-- OPTION GREEKS SNAPSHOTS TABLE
-- ============================================================================
-- Stores historical option Greeks snapshots from Alpaca API.
-- Captures delta, gamma, theta, vega, rho, IV, and pricing data.
--
-- Key Features:
-- - 3x daily snapshots (market open, mid-day, close)
-- - Full option chain for GLD (initially)
-- - JSONB raw_data for complete API response preservation
--
-- Dependencies: 6_functions.sql (update_updated_at_column trigger function)

CREATE TABLE IF NOT EXISTS option_greeks_snapshots (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Snapshot timing
    snapshot_at TIMESTAMPTZ NOT NULL,           -- Timestamp of the snapshot
    snapshot_type TEXT CHECK (snapshot_type IN ('london_session', 'us_session', 'asian_session', 'manual')),

    -- Option identifiers
    symbol TEXT NOT NULL,                       -- OCC option symbol (e.g., GLD260117C00175000)
    underlying TEXT NOT NULL,                   -- Underlying ticker (GLD)
    expiry_date DATE NOT NULL,                  -- Option expiration date
    strike_price DECIMAL(12, 4) NOT NULL,       -- Strike price
    option_type TEXT NOT NULL CHECK (option_type IN ('call', 'put')),

    -- Greeks (all nullable - may not always be available)
    delta DECIMAL(10, 6),
    gamma DECIMAL(10, 6),
    theta DECIMAL(12, 6),                       -- Can be larger magnitude
    vega DECIMAL(10, 6),
    rho DECIMAL(10, 6),
    implied_volatility DECIMAL(10, 6),

    -- Pricing data
    underlying_price DECIMAL(12, 4),            -- Underlying spot price at snapshot
    bid_price DECIMAL(12, 4),
    ask_price DECIMAL(12, 4),
    mid_price DECIMAL(12, 4),
    last_trade_price DECIMAL(12, 4),

    -- Volume/interest
    volume INTEGER DEFAULT 0,
    open_interest INTEGER DEFAULT 0,

    -- Metadata
    raw_data JSONB DEFAULT '{}'::jsonb,         -- Complete API response

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint: one snapshot per symbol per timestamp
    CONSTRAINT unique_greeks_snapshot UNIQUE (symbol, snapshot_at)
);

-- Table and column comments
COMMENT ON TABLE option_greeks_snapshots IS 'Historical option Greeks snapshots from Alpaca API (3x daily)';
COMMENT ON COLUMN option_greeks_snapshots.id IS 'Internal unique identifier';
COMMENT ON COLUMN option_greeks_snapshots.snapshot_at IS 'Timestamp when snapshot was taken';
COMMENT ON COLUMN option_greeks_snapshots.snapshot_type IS 'Type: london_session (8:00 AM ET), us_session (2:00 PM ET), asian_session (9:30 PM ET), manual';
COMMENT ON COLUMN option_greeks_snapshots.symbol IS 'OCC option symbol (e.g., GLD260117C00175000)';
COMMENT ON COLUMN option_greeks_snapshots.underlying IS 'Underlying ticker symbol (e.g., GLD)';
COMMENT ON COLUMN option_greeks_snapshots.expiry_date IS 'Option expiration date';
COMMENT ON COLUMN option_greeks_snapshots.strike_price IS 'Option strike price';
COMMENT ON COLUMN option_greeks_snapshots.option_type IS 'Option type: call or put';
COMMENT ON COLUMN option_greeks_snapshots.delta IS 'Delta (-1.0 to 1.0)';
COMMENT ON COLUMN option_greeks_snapshots.gamma IS 'Gamma (rate of delta change)';
COMMENT ON COLUMN option_greeks_snapshots.theta IS 'Theta (time decay per day)';
COMMENT ON COLUMN option_greeks_snapshots.vega IS 'Vega (sensitivity to volatility)';
COMMENT ON COLUMN option_greeks_snapshots.rho IS 'Rho (sensitivity to interest rates)';
COMMENT ON COLUMN option_greeks_snapshots.implied_volatility IS 'Implied volatility as decimal';
COMMENT ON COLUMN option_greeks_snapshots.underlying_price IS 'Underlying spot price at snapshot time';
COMMENT ON COLUMN option_greeks_snapshots.bid_price IS 'Best bid price';
COMMENT ON COLUMN option_greeks_snapshots.ask_price IS 'Best ask price';
COMMENT ON COLUMN option_greeks_snapshots.mid_price IS 'Mid price ((bid + ask) / 2)';
COMMENT ON COLUMN option_greeks_snapshots.last_trade_price IS 'Last trade price';
COMMENT ON COLUMN option_greeks_snapshots.volume IS 'Daily trading volume';
COMMENT ON COLUMN option_greeks_snapshots.open_interest IS 'Open interest (contracts outstanding)';
COMMENT ON COLUMN option_greeks_snapshots.raw_data IS 'Complete Alpaca API response (JSONB)';
COMMENT ON COLUMN option_greeks_snapshots.created_at IS 'Record creation timestamp';

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_greeks_snapshot_at ON option_greeks_snapshots(snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_greeks_underlying ON option_greeks_snapshots(underlying);
CREATE INDEX IF NOT EXISTS idx_greeks_symbol ON option_greeks_snapshots(symbol);
CREATE INDEX IF NOT EXISTS idx_greeks_expiry ON option_greeks_snapshots(expiry_date);
CREATE INDEX IF NOT EXISTS idx_greeks_type ON option_greeks_snapshots(snapshot_type);
CREATE INDEX IF NOT EXISTS idx_greeks_underlying_expiry ON option_greeks_snapshots(underlying, expiry_date);
CREATE INDEX IF NOT EXISTS idx_greeks_symbol_snapshot ON option_greeks_snapshots(symbol, snapshot_at DESC);

-- Composite index for time-series queries
CREATE INDEX IF NOT EXISTS idx_greeks_underlying_snapshot_type
    ON option_greeks_snapshots(underlying, snapshot_type, snapshot_at DESC);
```

- Follow exact format from `10_alpaca_orders.sql`
- Use `DECIMAL(10, 6)` for Greeks (6 decimal precision)
- Use `DECIMAL(12, 4)` for prices (4 decimal precision)
- Add comprehensive indexes for time-series queries
- Include `snapshot_type` to distinguish timing

### 2. Add Pydantic Model to models.py

Add to `apps/orchestrator_db/models.py` before the `__all__` export:

```python
# ═══════════════════════════════════════════════════════════
# OPTION_GREEKS_SNAPSHOT MODEL
# ═══════════════════════════════════════════════════════════


class OptionGreeksSnapshot(BaseModel):
    """
    Option Greeks snapshot record from Alpaca API.

    Maps to: option_greeks_snapshots table
    """
    id: UUID
    snapshot_at: datetime
    snapshot_type: Optional[Literal['london_session', 'us_session', 'asian_session', 'manual']] = None

    # Option identifiers
    symbol: str
    underlying: str
    expiry_date: date
    strike_price: float
    option_type: Literal['call', 'put']

    # Greeks
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    implied_volatility: Optional[float] = None

    # Pricing
    underlying_price: Optional[float] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    mid_price: Optional[float] = None
    last_trade_price: Optional[float] = None

    # Volume
    volume: int = 0
    open_interest: int = 0

    # Metadata
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert asyncpg UUID to Python UUID"""
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        return UUID(str(v))

    @field_validator('strike_price', 'delta', 'gamma', 'theta', 'vega', 'rho',
                     'implied_volatility', 'underlying_price', 'bid_price',
                     'ask_price', 'mid_price', 'last_trade_price', mode='before')
    @classmethod
    def convert_decimal(cls, v):
        """Convert Decimal to float"""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        return v

    @field_validator('raw_data', mode='before')
    @classmethod
    def parse_raw_data(cls, v):
        """Parse JSON string to dict"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
```

- Add `OptionGreeksSnapshot` to the `__all__` list
- Follow same validator patterns as `AlpacaOrder` and `AlpacaPosition`

### 3. Sync Models to Backend

- Run `uv run python apps/orchestrator_db/sync_models.py`
- Verify `orch_database_models.py` is updated in backend modules

### 4. Create Greeks Snapshot Service

Create `apps/orchestrator_3_stream/backend/modules/greeks_snapshot_service.py`:

```python
#!/usr/bin/env python3
"""
Greeks Snapshot Service

Fetches and persists option Greeks snapshots from Alpaca API.

Key Features:
- Uses OptionHistoricalDataClient for snapshot data
- Handles pagination for large option chains
- Persists to option_greeks_snapshots table
- Supports manual and scheduled triggers

IMPORTANT: Use app.state pattern, not global singleton.
Initialize via init_greeks_snapshot_service(app) in lifespan.
"""

import asyncio
import json
from datetime import datetime, date, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID

import asyncpg
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionSnapshotRequest

from .alpaca_models import OCCSymbol
from .config import ALPACA_API_KEY, ALPACA_SECRET_KEY, DATABASE_URL
from .logger import get_logger

# Import model for type hints
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "orchestrator_db"))
from models import OptionGreeksSnapshot

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger()


class GreeksSnapshotService:
    """
    Service for fetching and persisting option Greeks snapshots.

    Responsibilities:
    - Fetch option chain snapshots from Alpaca
    - Parse Greeks and pricing data
    - Persist to PostgreSQL with upsert logic
    - Support multiple underlyings (initially GLD)
    """

    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        """
        Initialize the service.

        Args:
            db_pool: Optional asyncpg connection pool (created if not provided)
        """
        self._db_pool = db_pool
        self._option_client: Optional[OptionHistoricalDataClient] = None
        self._is_configured = bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)

    @property
    def is_configured(self) -> bool:
        """Check if Alpaca credentials are configured."""
        return self._is_configured

    def _get_option_client(self) -> OptionHistoricalDataClient:
        """Get or create OptionHistoricalDataClient."""
        if self._option_client is None:
            self._option_client = OptionHistoricalDataClient(
                api_key=ALPACA_API_KEY,
                secret_key=ALPACA_SECRET_KEY
            )
        return self._option_client

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create database connection pool."""
        if self._db_pool is None:
            self._db_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10
            )
            logger.info("GreeksSnapshotService: Database pool created")
        return self._db_pool

    async def close(self) -> None:
        """Close database connections."""
        if self._db_pool:
            await self._db_pool.close()
            self._db_pool = None
            logger.info("GreeksSnapshotService: Database pool closed")

    # ═══════════════════════════════════════════════════════════
    # SNAPSHOT FETCHING
    # ═══════════════════════════════════════════════════════════

    async def fetch_and_persist_snapshots(
        self,
        underlying: str = "GLD",
        snapshot_type: str = "manual"
    ) -> int:
        """
        Fetch option chain snapshots and persist to database.

        Args:
            underlying: Underlying symbol (default: GLD)
            snapshot_type: Type of snapshot (london_session, us_session, asian_session, manual)

        Returns:
            Number of snapshots persisted
        """
        if not self._is_configured:
            logger.warning("GreeksSnapshotService: Alpaca not configured - skipping snapshot")
            return 0

        try:
            snapshot_at = datetime.now(timezone.utc)
            logger.info(f"Fetching {underlying} options snapshots ({snapshot_type})...")

            # Fetch snapshots with pagination
            all_snapshots = await self._fetch_all_snapshots(underlying)

            if not all_snapshots:
                logger.warning(f"No snapshots returned for {underlying}")
                return 0

            logger.info(f"Fetched {len(all_snapshots)} option contracts for {underlying}")

            # Persist to database
            persisted_count = await self._persist_snapshots(
                snapshots=all_snapshots,
                underlying=underlying,
                snapshot_at=snapshot_at,
                snapshot_type=snapshot_type
            )

            logger.success(f"Persisted {persisted_count} Greeks snapshots for {underlying}")
            return persisted_count

        except Exception as e:
            logger.error(f"Failed to fetch/persist snapshots for {underlying}: {e}")
            raise

    async def _fetch_all_snapshots(self, underlying: str) -> Dict[str, Any]:
        """
        Fetch all option snapshots with pagination.

        Args:
            underlying: Underlying symbol

        Returns:
            Dictionary of symbol -> snapshot data
        """
        client = self._get_option_client()
        loop = asyncio.get_running_loop()

        all_snapshots = {}
        page_token = None

        while True:
            # Build request
            request = OptionSnapshotRequest(
                symbol_or_symbols=underlying,
                feed="opra"  # Use OPRA feed (Elite subscription)
            )

            # Fetch snapshots (sync call in executor)
            response = await loop.run_in_executor(
                None,
                lambda: client.get_option_snapshot(request)
            )

            # Response is Dict[str, OptionSnapshot]
            if response:
                all_snapshots.update(response)

            # Check for pagination (handle if API returns next_page_token)
            # Note: SDK may handle pagination internally
            if hasattr(response, 'next_page_token') and response.next_page_token:
                page_token = response.next_page_token
            else:
                break

        return all_snapshots

    async def _persist_snapshots(
        self,
        snapshots: Dict[str, Any],
        underlying: str,
        snapshot_at: datetime,
        snapshot_type: str
    ) -> int:
        """
        Persist snapshots to database.

        Args:
            snapshots: Dictionary of symbol -> snapshot data
            underlying: Underlying symbol
            snapshot_at: Timestamp of snapshot
            snapshot_type: Type of snapshot

        Returns:
            Number of records persisted
        """
        pool = await self._get_pool()
        persisted = 0

        async with pool.acquire() as conn:
            # Use a transaction for batch insert
            async with conn.transaction():
                for symbol, snapshot in snapshots.items():
                    try:
                        # Parse OCC symbol
                        occ = OCCSymbol.parse(symbol)

                        # Extract Greeks (handle both dict and object access)
                        greeks = snapshot.greeks if hasattr(snapshot, 'greeks') else snapshot.get('greeks', {})
                        quote = snapshot.latest_quote if hasattr(snapshot, 'latest_quote') else snapshot.get('latestQuote', {})
                        trade = snapshot.latest_trade if hasattr(snapshot, 'latest_trade') else snapshot.get('latestTrade', {})

                        # Handle attribute vs dict access for greeks
                        if hasattr(greeks, 'delta'):
                            delta = greeks.delta
                            gamma = greeks.gamma
                            theta = greeks.theta
                            vega = greeks.vega
                            rho = greeks.rho
                            iv = greeks.implied_volatility
                        else:
                            delta = greeks.get('delta') if greeks else None
                            gamma = greeks.get('gamma') if greeks else None
                            theta = greeks.get('theta') if greeks else None
                            vega = greeks.get('vega') if greeks else None
                            rho = greeks.get('rho') if greeks else None
                            iv = greeks.get('implied_volatility') if greeks else None

                        # Extract pricing
                        if hasattr(quote, 'bid_price'):
                            bid = quote.bid_price
                            ask = quote.ask_price
                        else:
                            bid = quote.get('bp') if quote else None  # API uses 'bp' for bid_price
                            ask = quote.get('ap') if quote else None  # API uses 'ap' for ask_price

                        mid = (float(bid) + float(ask)) / 2 if bid and ask else None

                        if hasattr(trade, 'price'):
                            last_price = trade.price
                        else:
                            last_price = trade.get('p') if trade else None  # API uses 'p' for price

                        # Build raw_data
                        raw_data = {
                            'greeks': greeks if isinstance(greeks, dict) else (
                                {'delta': delta, 'gamma': gamma, 'theta': theta, 'vega': vega, 'rho': rho, 'iv': iv}
                            ),
                            'quote': quote if isinstance(quote, dict) else {'bid': bid, 'ask': ask},
                            'trade': trade if isinstance(trade, dict) else {'price': last_price}
                        }

                        # Upsert to database
                        await conn.execute("""
                            INSERT INTO option_greeks_snapshots (
                                snapshot_at, snapshot_type,
                                symbol, underlying, expiry_date, strike_price, option_type,
                                delta, gamma, theta, vega, rho, implied_volatility,
                                underlying_price, bid_price, ask_price, mid_price, last_trade_price,
                                volume, open_interest, raw_data
                            ) VALUES (
                                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                                $14, $15, $16, $17, $18, $19, $20, $21
                            )
                            ON CONFLICT (symbol, snapshot_at)
                            DO UPDATE SET
                                delta = EXCLUDED.delta,
                                gamma = EXCLUDED.gamma,
                                theta = EXCLUDED.theta,
                                vega = EXCLUDED.vega,
                                rho = EXCLUDED.rho,
                                implied_volatility = EXCLUDED.implied_volatility,
                                bid_price = EXCLUDED.bid_price,
                                ask_price = EXCLUDED.ask_price,
                                mid_price = EXCLUDED.mid_price,
                                last_trade_price = EXCLUDED.last_trade_price,
                                raw_data = EXCLUDED.raw_data
                        """,
                            snapshot_at,
                            snapshot_type,
                            symbol,
                            underlying,
                            occ.expiry_date,
                            occ.strike_price,
                            occ.option_type.lower(),
                            delta,
                            gamma,
                            theta,
                            vega,
                            rho,
                            iv,
                            None,  # underlying_price - would need separate fetch
                            bid,
                            ask,
                            mid,
                            last_price,
                            0,  # volume - not in snapshot response
                            0,  # open_interest - not in snapshot response
                            json.dumps(raw_data)
                        )

                        persisted += 1

                    except Exception as e:
                        logger.warning(f"Failed to persist snapshot for {symbol}: {e}")
                        continue

        return persisted

    # ═══════════════════════════════════════════════════════════
    # QUERY METHODS
    # ═══════════════════════════════════════════════════════════

    async def get_latest_snapshots(
        self,
        underlying: str = "GLD",
        limit: int = 100
    ) -> List[OptionGreeksSnapshot]:
        """
        Get latest Greeks snapshots for an underlying.

        Args:
            underlying: Underlying symbol
            limit: Maximum records to return

        Returns:
            List of OptionGreeksSnapshot records
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM option_greeks_snapshots
                WHERE underlying = $1
                ORDER BY snapshot_at DESC, symbol
                LIMIT $2
            """, underlying, limit)

            return [OptionGreeksSnapshot(**dict(row)) for row in rows]

    async def get_greeks_history(
        self,
        symbol: str,
        days: int = 30,
        limit: int = 1000
    ) -> List[OptionGreeksSnapshot]:
        """
        Get Greeks history for a specific option symbol.

        Args:
            symbol: OCC option symbol
            days: Number of days of history
            limit: Maximum records to return

        Returns:
            List of OptionGreeksSnapshot records ordered by snapshot_at ASC
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM option_greeks_snapshots
                WHERE symbol = $1
                  AND snapshot_at >= NOW() - INTERVAL '%s days'
                ORDER BY snapshot_at ASC
                LIMIT $2
            """ % days, symbol, limit)

            return [OptionGreeksSnapshot(**dict(row)) for row in rows]


# ═══════════════════════════════════════════════════════════
# APP.STATE INITIALIZATION
# ═══════════════════════════════════════════════════════════

async def init_greeks_snapshot_service(app: "FastAPI") -> GreeksSnapshotService:
    """
    Initialize GreeksSnapshotService and store in app.state.

    IMPORTANT: Call this in FastAPI lifespan startup.

    Args:
        app: FastAPI application instance

    Returns:
        Initialized GreeksSnapshotService
    """
    service = GreeksSnapshotService()
    app.state.greeks_snapshot_service = service

    if service.is_configured:
        logger.success("GreeksSnapshotService initialized and ready")
    else:
        logger.warning("GreeksSnapshotService: Alpaca not configured - snapshots disabled")

    return service


def get_greeks_snapshot_service(app: "FastAPI") -> GreeksSnapshotService:
    """
    Get GreeksSnapshotService from app.state.

    Args:
        app: FastAPI application instance

    Returns:
        GreeksSnapshotService instance

    Raises:
        RuntimeError: If service not initialized
    """
    if not hasattr(app.state, 'greeks_snapshot_service'):
        raise RuntimeError("GreeksSnapshotService not initialized. Call init_greeks_snapshot_service() in lifespan.")
    return app.state.greeks_snapshot_service
```

- Follow `AlpacaSyncService` patterns exactly
- Use `OptionHistoricalDataClient` from `alpaca-py`
- Handle both object and dict access patterns from API response
- Use transaction for batch inserts

### 5. Create Scheduler Module

Create `apps/orchestrator_3_stream/backend/modules/greeks_scheduler.py`:

```python
#!/usr/bin/env python3
"""
Greeks Snapshot Scheduler

Schedules automatic Greeks snapshots 3x daily using APScheduler.

Schedule (Eastern Time):
- 8:00 AM - London Session (London is in full swing, captures overnight moves)
- 2:00 PM - US Session (Peak COMEX activity, good liquidity)
- 9:30 PM - Asian Session (Tokyo/Shanghai handoff from US)

Runs every day (gold trades nearly 24 hours).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import pytz

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .greeks_snapshot_service import get_greeks_snapshot_service
from .logger import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger()

# US Eastern timezone
ET = pytz.timezone('America/New_York')

# Scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def is_trading_day() -> bool:
    """
    Check if today is a trading day.

    Returns True for Mon-Fri, excluding major US market holidays.
    Note: For production, integrate with a market calendar API.
    """
    now = datetime.now(ET)

    # Skip weekends
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    # Major US market holidays (simplified - add more as needed)
    # For production, use pandas_market_calendars or similar
    holidays = [
        (1, 1),   # New Year's Day
        (7, 4),   # Independence Day
        (12, 25), # Christmas Day
    ]

    if (now.month, now.day) in holidays:
        return False

    return True


async def run_london_session_snapshot(app: "FastAPI") -> None:
    """Run London session snapshot (8:00 AM ET). London is the world's largest gold trading hub."""
    logger.info("Greeks scheduler: Running London session snapshot...")
    try:
        service = get_greeks_snapshot_service(app)
        count = await service.fetch_and_persist_snapshots(
            underlying="GLD",
            snapshot_type="london_session"
        )
        logger.success(f"Greeks scheduler: London session snapshot complete ({count} records)")
    except Exception as e:
        logger.error(f"Greeks scheduler: London session snapshot failed: {e}")


async def run_us_session_snapshot(app: "FastAPI") -> None:
    """Run US session snapshot (2:00 PM ET). Peak COMEX activity with good liquidity."""
    logger.info("Greeks scheduler: Running US session snapshot...")
    try:
        service = get_greeks_snapshot_service(app)
        count = await service.fetch_and_persist_snapshots(
            underlying="GLD",
            snapshot_type="us_session"
        )
        logger.success(f"Greeks scheduler: US session snapshot complete ({count} records)")
    except Exception as e:
        logger.error(f"Greeks scheduler: US session snapshot failed: {e}")


async def run_asian_session_snapshot(app: "FastAPI") -> None:
    """Run Asian session snapshot (9:30 PM ET). Catches Tokyo/Shanghai handoff from US."""
    logger.info("Greeks scheduler: Running Asian session snapshot...")
    try:
        service = get_greeks_snapshot_service(app)
        count = await service.fetch_and_persist_snapshots(
            underlying="GLD",
            snapshot_type="asian_session"
        )
        logger.success(f"Greeks scheduler: Asian session snapshot complete ({count} records)")
    except Exception as e:
        logger.error(f"Greeks scheduler: Asian session snapshot failed: {e}")


def init_greeks_scheduler(app: "FastAPI") -> AsyncIOScheduler:
    """
    Initialize and start the Greeks snapshot scheduler.

    Args:
        app: FastAPI application instance

    Returns:
        Configured AsyncIOScheduler
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Greeks scheduler already initialized")
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone=ET)

    # London Session: 8:00 AM ET (London in full swing, captures overnight moves)
    _scheduler.add_job(
        run_london_session_snapshot,
        CronTrigger(hour=8, minute=0, timezone=ET),
        args=[app],
        id='greeks_london_session',
        name='Greeks London Session Snapshot',
        replace_existing=True
    )

    # US Session: 2:00 PM ET (Peak COMEX activity, good liquidity)
    _scheduler.add_job(
        run_us_session_snapshot,
        CronTrigger(hour=14, minute=0, timezone=ET),
        args=[app],
        id='greeks_us_session',
        name='Greeks US Session Snapshot',
        replace_existing=True
    )

    # Asian Session: 9:30 PM ET (Tokyo/Shanghai handoff from US)
    _scheduler.add_job(
        run_asian_session_snapshot,
        CronTrigger(hour=21, minute=30, timezone=ET),
        args=[app],
        id='greeks_asian_session',
        name='Greeks Asian Session Snapshot',
        replace_existing=True
    )

    _scheduler.start()
    logger.success("Greeks scheduler started (3 daily jobs scheduled)")

    return _scheduler


def shutdown_greeks_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    global _scheduler

    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Greeks scheduler shutdown")
```

- Use APScheduler with `AsyncIOScheduler`
- Schedule for 8:00 AM (London), 2:00 PM (US), 9:30 PM (Asian) Eastern
- Runs daily (gold trades nearly 24 hours)
- Integrate with app.state pattern

### 6. Add APScheduler Dependency

Add `apscheduler` to the backend's dependencies:

```bash
cd apps/orchestrator_3_stream/backend
uv add apscheduler pytz
```

### 7. Integrate into FastAPI Lifespan

Update `apps/orchestrator_3_stream/backend/main.py` lifespan:

```python
# Add imports
from modules.greeks_snapshot_service import init_greeks_snapshot_service
from modules.greeks_scheduler import init_greeks_scheduler, shutdown_greeks_scheduler

# In lifespan startup (after alpaca_service init):
greeks_service = await init_greeks_snapshot_service(app)
greeks_scheduler = init_greeks_scheduler(app)

# In lifespan shutdown:
shutdown_greeks_scheduler()
if hasattr(app.state, 'greeks_snapshot_service'):
    await app.state.greeks_snapshot_service.close()
```

### 8. Add REST Endpoints

Add endpoints to `main.py` or create a new router:

```python
from fastapi import APIRouter
from modules.greeks_snapshot_service import get_greeks_snapshot_service

greeks_router = APIRouter(prefix="/api/greeks", tags=["greeks"])

@greeks_router.post("/snapshot")
async def trigger_snapshot(underlying: str = "GLD"):
    """Manually trigger a Greeks snapshot."""
    service = get_greeks_snapshot_service(request.app)
    count = await service.fetch_and_persist_snapshots(
        underlying=underlying,
        snapshot_type="manual"
    )
    return {"status": "success", "records": count}

@greeks_router.get("/latest")
async def get_latest_greeks(underlying: str = "GLD", limit: int = 100):
    """Get latest Greeks snapshots."""
    service = get_greeks_snapshot_service(request.app)
    snapshots = await service.get_latest_snapshots(underlying, limit)
    return {"status": "success", "snapshots": [s.model_dump() for s in snapshots]}

@greeks_router.get("/history/{symbol}")
async def get_greeks_history(symbol: str, days: int = 30):
    """Get Greeks history for a specific option."""
    service = get_greeks_snapshot_service(request.app)
    history = await service.get_greeks_history(symbol, days)
    return {"status": "success", "history": [h.model_dump() for h in history]}

# Register router
app.include_router(greeks_router)
```

### 9. Run Database Migration

```bash
# Connect to Neon DB and run migration
cd apps/orchestrator_db
uv run python -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def run_migration():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    with open('migrations/12_option_greeks_snapshots.sql', 'r') as f:
        await conn.execute(f.read())
    await conn.close()
    print('Migration complete!')

asyncio.run(run_migration())
"
```

### 10. Validate Implementation

- Test manual snapshot trigger
- Verify database records
- Check scheduler is running
- Confirm Greeks data is populated

## Testing Strategy

### Unit Tests

1. **OCC Symbol parsing** - Verify Greeks service correctly parses option symbols
2. **Snapshot data mapping** - Verify API response maps to database schema

### Integration Tests

1. **API fetch and persist** - Fetch real GLD snapshots, verify database records
2. **Scheduler timing** - Mock time, verify jobs trigger at correct times
3. **Upsert logic** - Verify duplicate snapshots update rather than error

### Test Pattern (following existing tests)

```python
# tests/test_greeks_snapshot_service.py
import pytest
from datetime import datetime
from modules.greeks_snapshot_service import GreeksSnapshotService

@pytest.mark.asyncio
async def test_fetch_and_persist_snapshots():
    """Test fetching and persisting Greeks snapshots."""
    service = GreeksSnapshotService()

    # Fetch real data (use test database)
    count = await service.fetch_and_persist_snapshots(
        underlying="GLD",
        snapshot_type="manual"
    )

    assert count > 0, "Should persist at least one snapshot"

    # Verify records exist
    snapshots = await service.get_latest_snapshots("GLD", limit=10)
    assert len(snapshots) > 0

    # Verify Greeks fields
    snapshot = snapshots[0]
    assert snapshot.underlying == "GLD"
    assert snapshot.delta is not None or snapshot.gamma is not None

    await service.close()
```

## Acceptance Criteria

1. **Database table exists** - `option_greeks_snapshots` table created with all columns
2. **Pydantic model works** - `OptionGreeksSnapshot` can serialize/deserialize records
3. **Manual trigger works** - POST `/api/greeks/snapshot` fetches and persists data
4. **Scheduler runs** - Jobs execute at 8:00 AM (London), 2:00 PM (US), 9:30 PM (Asian) ET daily
5. **Greeks populated** - Delta, gamma, theta, vega, rho, IV have values
6. **Query endpoints work** - GET `/api/greeks/latest` and `/api/greeks/history/{symbol}` return data

## Validation Commands

Execute these commands to validate the task is complete:

```bash
# 1. Verify migration file exists and compiles
uv run python -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_table():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    result = await conn.fetchval('''
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'option_greeks_snapshots'
        )
    ''')
    print(f'Table exists: {result}')
    await conn.close()

asyncio.run(check_table())
"

# 2. Verify models sync
uv run python apps/orchestrator_db/sync_models.py

# 3. Verify imports work
cd apps/orchestrator_3_stream/backend
uv run python -c "from modules.greeks_snapshot_service import GreeksSnapshotService; print('Import OK')"
uv run python -c "from modules.greeks_scheduler import init_greeks_scheduler; print('Import OK')"

# 4. Test manual snapshot (requires running backend)
curl -X POST http://localhost:8000/api/greeks/snapshot?underlying=GLD

# 5. Verify data persisted
curl http://localhost:8000/api/greeks/latest?underlying=GLD&limit=5
```

## Notes

### Dependencies to Add

```bash
cd apps/orchestrator_3_stream/backend
uv add apscheduler pytz
```

### Volume and Open Interest

The Alpaca options snapshot endpoint does not return volume or open_interest directly. These fields are set to 0 in the schema but could be populated from:
- A separate `/v2/options/contracts` API call
- Aggregating from trade data

### Underlying Price

The snapshot response doesn't include underlying spot price. To add this:
- Make a separate stock quote request
- Or use the existing alpaca_service price cache

### Holiday Calendar

The `is_trading_day()` function uses a simplified holiday list. For production:
- Integrate `pandas_market_calendars` library
- Or use Alpaca's market calendar API

### Rate Limits

With Alpaca Elite subscription (1000 calls/minute):
- Each snapshot request returns up to 1000 contracts
- GLD typically has ~500-800 option contracts
- 3 daily calls is well under limit
- Manual triggers should implement basic rate limiting

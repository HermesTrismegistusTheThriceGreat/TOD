-- ============================================================================
-- ALPACA ORDERS AND POSITIONS TABLES
-- ============================================================================
-- Stores Alpaca order history and open positions with trade grouping.
--
-- Key Features:
-- - trade_id links related orders together for multi-leg strategies
-- - Strategy type detection (iron_condor, vertical_spread, etc.)
-- - Comprehensive indexing for filtering and sorting
--
-- Dependencies: None (standalone tables)

-- ============================================================================
-- ALPACA_ORDERS TABLE
-- ============================================================================
-- Stores order history from Alpaca with trade grouping for multi-leg strategies

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

-- Table and column comments
COMMENT ON TABLE alpaca_orders IS 'Alpaca order history with trade grouping for multi-leg strategies';
COMMENT ON COLUMN alpaca_orders.id IS 'Internal unique identifier';
COMMENT ON COLUMN alpaca_orders.alpaca_order_id IS 'Alpaca order UUID (unique)';
COMMENT ON COLUMN alpaca_orders.client_order_id IS 'Optional client-specified order ID';
COMMENT ON COLUMN alpaca_orders.trade_id IS 'UUID linking related orders together (same trade group)';
COMMENT ON COLUMN alpaca_orders.strategy_type IS 'Detected strategy: iron_condor, vertical_spread, strangle, straddle, single_leg, options';
COMMENT ON COLUMN alpaca_orders.leg_number IS 'Leg number within strategy (1-4 for iron condors)';
COMMENT ON COLUMN alpaca_orders.symbol IS 'OCC option symbol (e.g., SPY260117C00688000)';
COMMENT ON COLUMN alpaca_orders.underlying IS 'Underlying ticker symbol (e.g., SPY, QQQ)';
COMMENT ON COLUMN alpaca_orders.side IS 'Order side: buy or sell';
COMMENT ON COLUMN alpaca_orders.qty IS 'Order quantity';
COMMENT ON COLUMN alpaca_orders.filled_qty IS 'Filled quantity';
COMMENT ON COLUMN alpaca_orders.order_type IS 'Order type: market, limit, stop, stop_limit';
COMMENT ON COLUMN alpaca_orders.time_in_force IS 'Time in force: day, gtc, opg, cls, ioc, fok';
COMMENT ON COLUMN alpaca_orders.limit_price IS 'Limit price for limit orders';
COMMENT ON COLUMN alpaca_orders.stop_price IS 'Stop price for stop orders';
COMMENT ON COLUMN alpaca_orders.filled_avg_price IS 'Average fill price';
COMMENT ON COLUMN alpaca_orders.status IS 'Order status from Alpaca';
COMMENT ON COLUMN alpaca_orders.expiry_date IS 'Option expiration date';
COMMENT ON COLUMN alpaca_orders.strike_price IS 'Option strike price';
COMMENT ON COLUMN alpaca_orders.option_type IS 'Option type: call or put';
COMMENT ON COLUMN alpaca_orders.submitted_at IS 'Timestamp when order was submitted to Alpaca';
COMMENT ON COLUMN alpaca_orders.filled_at IS 'Timestamp when order was filled';
COMMENT ON COLUMN alpaca_orders.expired_at IS 'Timestamp when order expired';
COMMENT ON COLUMN alpaca_orders.canceled_at IS 'Timestamp when order was canceled';
COMMENT ON COLUMN alpaca_orders.raw_data IS 'Complete Alpaca API response (JSONB)';
COMMENT ON COLUMN alpaca_orders.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN alpaca_orders.updated_at IS 'Record last update timestamp';

-- Indexes for alpaca_orders
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

-- Trigger for updated_at (uses existing function from 6_functions.sql)
DROP TRIGGER IF EXISTS update_alpaca_orders_updated_at ON alpaca_orders;
CREATE TRIGGER update_alpaca_orders_updated_at
    BEFORE UPDATE ON alpaca_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- ALPACA_POSITIONS TABLE
-- ============================================================================
-- Stores current open positions from Alpaca with trade linking

CREATE TABLE IF NOT EXISTS alpaca_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Trade grouping
    trade_id UUID,  -- Links to orders (nullable for historical positions)

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

-- Table and column comments
COMMENT ON TABLE alpaca_positions IS 'Current open positions from Alpaca with trade linking';
COMMENT ON COLUMN alpaca_positions.id IS 'Internal unique identifier';
COMMENT ON COLUMN alpaca_positions.trade_id IS 'UUID linking to related orders (nullable)';
COMMENT ON COLUMN alpaca_positions.symbol IS 'OCC option symbol';
COMMENT ON COLUMN alpaca_positions.underlying IS 'Underlying ticker symbol';
COMMENT ON COLUMN alpaca_positions.qty IS 'Position quantity (negative for short)';
COMMENT ON COLUMN alpaca_positions.side IS 'Position side: long or short';
COMMENT ON COLUMN alpaca_positions.avg_entry_price IS 'Average entry price';
COMMENT ON COLUMN alpaca_positions.current_price IS 'Current market price';
COMMENT ON COLUMN alpaca_positions.market_value IS 'Current market value';
COMMENT ON COLUMN alpaca_positions.cost_basis IS 'Total cost basis';
COMMENT ON COLUMN alpaca_positions.unrealized_pl IS 'Unrealized P/L in dollars';
COMMENT ON COLUMN alpaca_positions.unrealized_plpc IS 'Unrealized P/L percentage';
COMMENT ON COLUMN alpaca_positions.unrealized_intraday_pl IS 'Intraday unrealized P/L in dollars';
COMMENT ON COLUMN alpaca_positions.unrealized_intraday_plpc IS 'Intraday unrealized P/L percentage';
COMMENT ON COLUMN alpaca_positions.expiry_date IS 'Option expiration date';
COMMENT ON COLUMN alpaca_positions.strike_price IS 'Option strike price';
COMMENT ON COLUMN alpaca_positions.option_type IS 'Option type: call or put';
COMMENT ON COLUMN alpaca_positions.is_open IS 'Whether position is currently open';
COMMENT ON COLUMN alpaca_positions.raw_data IS 'Complete Alpaca API response (JSONB)';
COMMENT ON COLUMN alpaca_positions.created_at IS 'Record creation timestamp';
COMMENT ON COLUMN alpaca_positions.updated_at IS 'Record last update timestamp';

-- Indexes for alpaca_positions
CREATE INDEX IF NOT EXISTS idx_alpaca_positions_trade_id ON alpaca_positions(trade_id);
CREATE INDEX IF NOT EXISTS idx_alpaca_positions_symbol ON alpaca_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_alpaca_positions_underlying ON alpaca_positions(underlying);
CREATE INDEX IF NOT EXISTS idx_alpaca_positions_is_open ON alpaca_positions(is_open);
CREATE INDEX IF NOT EXISTS idx_alpaca_positions_expiry ON alpaca_positions(expiry_date);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_alpaca_positions_updated_at ON alpaca_positions;
CREATE TRIGGER update_alpaca_positions_updated_at
    BEFORE UPDATE ON alpaca_positions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

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

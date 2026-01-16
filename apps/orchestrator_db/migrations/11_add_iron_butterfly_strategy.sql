-- Migration: Add iron_butterfly to strategy_type enum
-- Drop existing constraint and recreate with new value

ALTER TABLE alpaca_orders
DROP CONSTRAINT IF EXISTS alpaca_orders_strategy_type_check;

ALTER TABLE alpaca_orders
ADD CONSTRAINT alpaca_orders_strategy_type_check
CHECK (strategy_type IN (
    'iron_condor', 'iron_butterfly', 'vertical_spread',
    'strangle', 'straddle', 'single_leg', 'options'
));

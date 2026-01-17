# Options Trading Overview

## Initial Options Offering

### Supported Features
- US-listed equities options (American style)
- Level 1-3 options trading
- Fully disclosed partner relationships
- Automatic account approval via API with SSE events
- Partner ability to downgrade/disable options trading
- API-based options exercise capability
- DNE (do not exercise) requests by email
- Options-specific activity tracking
- Access to options market data (paid) or vendor referrals

### Not Supported
- Local currency trading (LCT)
- Fractional options
- Extended hours trading

## Options Enablement

### New Account Setup
Per FINRA Rule 2360, accounts must be approved for options before trading. New accounts require these identity fields:
- Annual income and net worth figures
- Liquid net worth and liquidity needs
- Investment experience (stocks/options)
- Risk tolerance and investment objectives
- Time horizon, marital status, dependent count

The account request must include an `options_agreement` with signature details.

### Existing Account Approval
Use the approval endpoint to request options levels. Response statuses include:
- **APPROVED**: User qualified for requested level
- **LOWER_LEVEL_APPROVED**: User approved for lower tier
- **PENDING**: Manual review required
- **REJECTED**: Application denied

### Sandbox Testing
Approval fixtures enable scenario testing without live approvals, allowing you to simulate all approval outcomes.

### Downgrading Options
Customers can reduce or disable options via the trading account configuration endpoint using `max_options_trading_level`. The actual trading level never exceeds the approved level.

## Trading

### Overview
Supported order features include options symbols, day time-in-force, market/limit orders, cancellations, and replacements. Level 1+2 strategies are permitted. Extended hours and fractional orders are not supported.

### Trading Levels

| Level | Supported Trades | Requirements |
|-------|------------------|--------------|
| 0 | Disabled | N/A |
| 1 | Covered calls; cash-secured puts | Sufficient shares; adequate buying power |
| 2 | Level 1 activities plus calls/puts | Sufficient options buying power |

### Asset Master
The options contract endpoint returns available contracts per underlying symbol, including expiration date, strike price, and trading status.

### Order Examples
- **Call purchase**: Symbol, qty, buy side, market type, day TIF
- **Put purchase**: Same structure
- **Covered call sale**: Requires underlying share collateral
- **Cash-secured put**: Requires buying power for full obligation minus premium

### Buying Power Checks
- **Call/put purchases**: Premium cost must not exceed `options_buying_power`
- **Covered calls**: Account must hold 100 shares per contract
- **Cash-secured puts**: Required buying power = (strike × 100) - premium received

## Positions

Options positions appear in the positions endpoint with `asset_class: us_option`, displaying quantity, entry price, market value, and profit/loss calculations.

## Post-Trade Activities

### Exercising
Buyers may exercise calls or puts via the exercise endpoint during market hours. Two activities generate:
- **OPEXC**: Removes the option position
- **OPTRD**: Records the resulting stock transaction

Exercising a call buys stock at strike; exercising a put sells at strike.

### Assignment
When sellers are assigned (call or put), two activities record:
- **OPASN**: Removes the short position
- **OPTRD**: Documents the obligation fulfillment

Call assignment obligates stock sale; put assignment obligates stock purchase.

### Expiration
Starting at 3:30 PM EST on expiration:
- Alpaca halts new position orders
- In-the-money (ITM) long options auto-exercise if account has resources
- Underfunded positions liquidate while ITM
- Covered calls/cash-secured puts auto-assign if ITM
- At/out-of-the-money positions may expire worthless

## Market Data

Alpaca provides options market data through these endpoints:
- Latest quotes and trades (multi-symbol)
- Historical trades and bars
- Snapshots (combined quotes/trades)
- Option chain queries by underlying symbol

**Disclaimer**: Options trading carries significant risk. Review the OCC's "Characteristics and Risks of Standardized Options" before investing.

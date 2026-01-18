---
name: selecting-options-strategies
description: Selects optimal options trading strategies based on greek profiles and market regime analysis. Use when analyzing options greeks, choosing between strategies like iron condors, straddles, or calendar spreads, or when the user asks about volatility plays, theta generation, or greek-based strategy selection.
---

# Options Strategy Selector

Analyzes greek data and market conditions to recommend optimal options strategies using a systematic theme-to-strategy mapping.

## Prerequisites

- Options chain data with greeks (delta, gamma, theta, vega)
- Implied volatility (IV) and historical volatility (HV) data
- Python with numpy, pandas, and pydantic

## Data Integration with Alpaca

This skill integrates with Alpaca's Elite API to fetch real-time options data with greeks and historical volatility.

### Setup Requirements

**Alpaca Elite Subscription Required**
- Options data requires Alpaca Elite subscription with OPRA feed access
- Sign up at [alpaca.markets](https://alpaca.markets)
- Enable options data in your account settings

**Environment Variables**
```bash
# Add to your .env file
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
```

### Complete Pipeline Usage

**CLI - Fetch and Analyze**
```bash
# Basic usage - fetch GLD data with auto spot price
uv run scripts/fetch_and_select.py --symbol GLD

# Explicit spot price
uv run scripts/fetch_and_select.py --symbol SLV --spot 28.50

# Filter by days to expiration (30-60 days out)
uv run scripts/fetch_and_select.py --symbol GLD --min-dte 30 --max-dte 60

# Save fetched data for later analysis
uv run scripts/fetch_and_select.py --symbol SLV --save-data slv_data.json

# Override IV rank for regime detection
uv run scripts/fetch_and_select.py --symbol SLV --iv-rank 85

# Save strategy recommendation
uv run scripts/fetch_and_select.py --symbol SLV --output recommendation.json
```

**Programmatic Usage**
```python
from alpaca_fetcher import AlpacaFetcher
from strategy_selector import select_strategy

# Fetch data
fetcher = AlpacaFetcher()
profiles = fetcher.fetch_all("SLV")

# Get recommendation
recommendation = select_strategy(profiles, spot=28.50)

print(f"Strategy: {recommendation.strategy.name}")
print(f"Theme: {recommendation.theme}")
```

### What Data Gets Fetched

The Alpaca integration fetches:

| Data Type | API Endpoint | Description |
|-----------|--------------|-------------|
| **Historical Volatility** | `/v2/stocks/{symbol}/bars` | 20-day realized vol from stock bars |
| **Options Chain** | `/v1beta1/options/snapshots/{symbol}` | Full chain with greeks and quotes |
| **Greeks** | Included in snapshots | Delta, gamma, theta, vega, IV |
| **Pricing** | Included in snapshots | Bid, ask, last price, volume |

**OCC Symbol Format**
- Alpaca uses OCC standard: `SLV250221C00025000`
- Format: `SYMBOL` + `YYMMDD` + `C/P` + `STRIKE*1000` (8 digits)
- Example: SLV Feb 21 2025 $25 Call

### Rate Limits

Alpaca API rate limits:
- **Free tier**: 200 requests/minute
- **Elite tier**: Higher limits (check documentation)
- Fetching full chain + historical vol = ~2 API calls
- Use `--min-dte` and `--max-dte` to reduce data volume

**Best Practices**
- Cache fetched data with `--save-data` for repeated analysis
- Filter by DTE range to reduce API calls
- Use programmatic API for batch processing
- Monitor your rate limit usage in Alpaca dashboard

## Quick Reference: Theme to Strategy Mapping

| Theme | Strategy | Code | Primary Greeks |
|-------|----------|------|----------------|
| Volatility Mean Reversion | Long Straddle | STRAT_A1 | +Vega, +Gamma, -Theta |
| Range-Bound Stability | Iron Condor | STRAT_A2 | -Vega, -Gamma, +Theta |
| Volatility Skew | Ratio Spread | STRAT_A3 | Variable Delta, -Vega |
| Term Structure Arb | Calendar Spread | STRAT_A4 | Neutral Delta, +Vega |
| Precision Pinning | Butterfly Spread | STRAT_A5 | Neutral Vega, -Gamma |
| Arbitrage | Synthetic/Parity | STRAT_A6 | Pure Delta |

## Workflow

### Step 1: Gather Greek Data

Collect options chain data in this format:

```python
from pydantic import BaseModel
from datetime import date
from typing import Literal, Optional

class GreekProfile(BaseModel):
    symbol: str
    strike: float
    expiry: date
    option_type: Literal["call", "put"]
    dte: int  # Days to expiration

    # Core Greeks
    delta: float          # -1 to 1
    gamma: float          # Rate of delta change
    theta: float          # Time decay (negative for longs)
    vega: float           # IV sensitivity

    # Volatility Metrics
    implied_vol: float    # Current IV (decimal, e.g., 0.25 = 25%)
    hist_vol_20d: float   # 20-day realized vol
    iv_rank: Optional[float] = None  # 0-100 percentile

    # Computed
    @property
    def vol_edge(self) -> float:
        return self.implied_vol - self.hist_vol_20d
```

### Step 2: Detect Market Regime

Analyze the data to identify the current market theme:

| Theme | Detection Criteria |
|-------|-------------------|
| **Volatility Mean Reversion** | IV < 80% of HV, DTE > 45 |
| **Range-Bound Stability** | IV Rank > 70, Delta 0.1-0.3 available |
| **Term Structure Arb** | Near-term IV < Far-term IV, ATM options available |
| **Volatility Skew** | \|Put IV - Call IV\| > 5% at same strike |
| **Regime Shift** | High realized vol, trending market |

Run the detector script:

```bash
uv run scripts/detect_regime.py --symbol SLV --data greeks.json
```

### Step 3: Select Strategy

Based on the detected theme, select the appropriate strategy:

```python
def select_strategy(theme: str) -> dict:
    strategies = {
        "volatility_mean_reversion": {
            "code": "STRAT_A1",
            "name": "Long Straddle",
            "greeks": "+Vega, +Gamma, -Theta",
            "sentiment": "Buying the dip in vol - high risk, high reward"
        },
        "range_bound_stability": {
            "code": "STRAT_A2",
            "name": "Iron Condor",
            "greeks": "-Vega, -Gamma, +Theta",
            "sentiment": "Bread and butter theta harvesting"
        },
        "volatility_skew": {
            "code": "STRAT_A3",
            "name": "Ratio Spread",
            "greeks": "Variable Delta, -Vega",
            "sentiment": "Complex skew exploitation"
        },
        "term_structure_arb": {
            "code": "STRAT_A4",
            "name": "Calendar Spread",
            "greeks": "Neutral Delta, +Vega",
            "sentiment": "Low-risk time decay play"
        },
        "precision_pinning": {
            "code": "STRAT_A5",
            "name": "Butterfly Spread",
            "greeks": "Neutral Vega, -Gamma",
            "sentiment": "Precision price targeting"
        },
        "arbitrage": {
            "code": "STRAT_A6",
            "name": "Synthetic/Parity",
            "greeks": "Pure Delta",
            "sentiment": "Institutional edge only"
        }
    }
    return strategies.get(theme, strategies["range_bound_stability"])
```

### Step 4: Calculate Strategy Parameters

Run the full selector to get specific strikes and expiries:

```bash
uv run scripts/strategy_selector.py \
  --symbol SLV \
  --data greeks.json \
  --output recommendation.json
```

Output format:

```json
{
  "symbol": "SLV",
  "theme": "range_bound_stability",
  "strategy": {
    "code": "STRAT_A2",
    "name": "Iron Condor",
    "greeks": "-Vega, -Gamma, +Theta"
  },
  "parameters": {
    "short_put": 22,
    "long_put": 20,
    "short_call": 28,
    "long_call": 30,
    "expiry": "2025-02-21",
    "net_credit": 0.85
  },
  "risk_metrics": {
    "max_profit": 85,
    "max_loss": 115,
    "breakeven_low": 21.15,
    "breakeven_high": 28.85
  }
}
```

## Decision Matrix Details

For detailed strategy implementations and P&L calculations, see [strategies.md](strategies.md).

## Greek Data Requirements

### Minimum Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Underlying ticker |
| `strike` | float | Option strike price |
| `expiry` | date | Expiration date |
| `option_type` | "call" \| "put" | Option type |
| `delta` | float | Delta value (-1 to 1) |
| `gamma` | float | Gamma value |
| `theta` | float | Theta value |
| `vega` | float | Vega value |
| `implied_vol` | float | IV as decimal |
| `hist_vol_20d` | float | 20-day HV as decimal |

### Optional Fields for Enhanced Analysis

| Field | Type | Description |
|-------|------|-------------|
| `iv_rank` | float | IV percentile (0-100) |
| `volume` | int | Contract volume |
| `open_interest` | int | Open interest |
| `bid` | float | Bid price |
| `ask` | float | Ask price |

## Examples

### Example 1: High IV Rank Environment (SLV)

User request:
```
Analyze SLV options and recommend a strategy. IV rank is at 85%.
```

You would:
1. Recognize high IV rank (>70) suggests range-bound stability theme
2. Run the strategy selector:
   ```bash
   uv run scripts/strategy_selector.py --symbol SLV --iv-rank 85
   ```
3. Return Iron Condor (STRAT_A2) recommendation with specific strikes
4. Calculate risk metrics and breakevens

### Example 2: IV Below Historical Vol (GLD)

User request:
```
GLD IV is at 15% but realized vol is 22%. What strategy?
```

You would:
1. Calculate vol edge: 0.15 - 0.22 = -0.07 (negative = IV underpriced)
2. Detect volatility mean reversion theme
3. Recommend Long Straddle (STRAT_A1)
4. Specify ATM strike and expiry > 45 DTE

### Example 3: Term Structure Opportunity

User request:
```
Near-term SLV IV is 18% but 60-day IV is 24%. Strategy?
```

You would:
1. Detect term structure arbitrage opportunity
2. Recommend Calendar Spread (STRAT_A4)
3. Select ATM strike, sell near-term, buy far-term
4. Calculate theta differential edge

### Example 4: Skew Analysis

User request:
```
SLV put IV at 25 strike is 28%, call IV is 21%. How to trade this?
```

You would:
1. Calculate skew: 28% - 21% = 7% (significant)
2. Detect volatility skew theme
3. Recommend Ratio Spread (STRAT_A3)
4. Structure as 1x2 put ratio or call ratio depending on directional view

# Strategy Implementations

Detailed P&L calculations and implementation guidance for each strategy.

## Table of Contents

1. [STRAT_A1: Long Straddle](#strat_a1-long-straddle)
2. [STRAT_A2: Iron Condor](#strat_a2-iron-condor)
3. [STRAT_A3: Ratio Spread](#strat_a3-ratio-spread)
4. [STRAT_A4: Calendar Spread](#strat_a4-calendar-spread)
5. [STRAT_A5: Butterfly Spread](#strat_a5-butterfly-spread)
6. [STRAT_A6: Synthetics](#strat_a6-synthetics)
7. [Black-Scholes Engine](#black-scholes-engine)
8. [Data Query Patterns](#data-query-patterns)

---

## STRAT_A1: Long Straddle

**Theme**: Volatility Mean Reversion
**Greeks**: +Vega, +Gamma, -Theta
**Sentiment**: Buying the dip in vol - high risk, high reward

### When to Use

- IV < 80% of historical volatility
- DTE > 45 days (time for vol expansion)
- Expecting significant price movement in either direction

### Entry Criteria

```sql
SELECT strike, iv, delta FROM options
WHERE iv < hist_vol * 0.8
  AND dte > 45
  AND delta BETWEEN 0.45 AND 0.55
```

### P&L Calculation

```python
import numpy as np

def straddle_pnl(S_range: np.ndarray, K: float, premium_paid: float) -> np.ndarray:
    """
    Long Straddle P&L at expiration.

    Args:
        S_range: Array of underlying prices at expiration
        K: Strike price (ATM)
        premium_paid: Total premium paid (call + put)

    Returns:
        P&L array for each price in S_range

    Reference: Natenberg, Option Volatility & Pricing, p. 150
    """
    return np.abs(S_range - K) - premium_paid
```

### Risk Profile

| Metric | Value |
|--------|-------|
| Max Profit | Unlimited |
| Max Loss | Premium paid |
| Breakeven Up | K + Premium |
| Breakeven Down | K - Premium |
| Theta | Negative (time decay hurts) |
| Vega | Positive (benefits from IV increase) |

---

## STRAT_A2: Iron Condor

**Theme**: Range-Bound Stability
**Greeks**: -Vega, -Gamma, +Theta
**Sentiment**: Bread and butter strategy for income

### When to Use

- IV Rank > 70 (sell high IV)
- Range-bound market expectation
- Delta 0.1-0.3 for wing strikes

### Entry Criteria

```python
# Find optimal wing strikes
df_filtered = df[
    (df['delta'].between(0.1, 0.3)) &
    (df['iv_rank'] > 70)
]
```

### P&L Calculation

```python
import numpy as np

def iron_condor_pnl(
    S_range: np.ndarray,
    put_wing: float,
    short_put: float,
    short_call: float,
    call_wing: float,
    net_credit: float
) -> np.ndarray:
    """
    Iron Condor P&L at expiration.

    Args:
        S_range: Array of underlying prices
        put_wing: Long put strike (lowest)
        short_put: Short put strike
        short_call: Short call strike
        call_wing: Long call strike (highest)
        net_credit: Net credit received

    Returns:
        P&L array for each price
    """
    pnl = np.where(
        S_range <= put_wing,
        (put_wing - short_put) + net_credit,
        np.where(
            S_range <= short_put,
            (S_range - short_put) + net_credit,
            np.where(
                S_range <= short_call,
                net_credit,
                np.where(
                    S_range <= call_wing,
                    (short_call - S_range) + net_credit,
                    (short_call - call_wing) + net_credit
                )
            )
        )
    )
    return pnl
```

### Risk Profile

| Metric | Calculation |
|--------|-------------|
| Max Profit | Net Credit |
| Max Loss | Wing Width - Net Credit |
| Breakeven Up | Short Call + Net Credit |
| Breakeven Down | Short Put - Net Credit |
| Theta | Positive |
| Vega | Negative |

---

## STRAT_A3: Ratio Spread

**Theme**: Volatility Skew
**Greeks**: Variable Delta, -Vega
**Sentiment**: Complex skew exploitation, hedging black swan events

### When to Use

- Significant put/call IV skew (>5% difference)
- Directional bias with limited risk
- Hedging tail risk

### Entry Criteria

```python
# Calculate skew
df['skew'] = df['put_iv'] - df['call_iv']
skew_opportunities = df.sort_values('skew', ascending=False)
```

### P&L Calculation (1x2 Call Ratio)

```python
import numpy as np

def call_ratio_pnl(
    S_range: np.ndarray,
    K1: float,
    K2: float,
    p1: float,
    p2: float
) -> np.ndarray:
    """
    1x2 Call Ratio Spread P&L.
    Buy 1 call at K1, Sell 2 calls at K2 (K2 > K1).

    Args:
        S_range: Array of underlying prices
        K1: Long call strike (lower)
        K2: Short call strike (higher)
        p1: Premium paid for long call
        p2: Premium received per short call

    Returns:
        P&L array
    """
    cost = p1 - (2 * p2)  # Can be credit or debit
    long_call = np.maximum(S_range - K1, 0)
    short_calls = 2 * np.maximum(S_range - K2, 0)
    return long_call - short_calls - cost
```

### Risk Profile

| Metric | Value |
|--------|-------|
| Max Profit | K2 - K1 - Net Debit (at K2) |
| Max Loss | Unlimited above K2 |
| Breakeven | Depends on structure |

---

## STRAT_A4: Calendar Spread

**Theme**: Term Structure Arbitrage
**Greeks**: Neutral Delta, +Vega
**Sentiment**: Low-risk volatility skew play, favored by professionals

### When to Use

- Near-term IV < Far-term IV (contango)
- ATM options available (delta 0.45-0.55)
- Expect IV to normalize

### Entry Criteria

```sql
SELECT * FROM chains
WHERE near_iv < far_iv
  AND delta BETWEEN 0.45 AND 0.55
```

### Theta Edge Calculation

```python
def calendar_theta_edge(near_theta: float, far_theta: float) -> float:
    """
    Calculate theta differential advantage.
    Near-term theta decays faster than far-term.

    Args:
        near_theta: Short leg theta (more negative)
        far_theta: Long leg theta (less negative)

    Returns:
        Daily theta edge (positive = profitable decay)
    """
    return abs(near_theta) - abs(far_theta)
```

### Full Valuation

```python
def calendar_value(
    S: float,
    K: float,
    T1: float,  # Near-term time to expiry
    T2: float,  # Far-term time to expiry
    r: float,
    iv1: float,  # Near-term IV
    iv2: float   # Far-term IV
) -> float:
    """
    Calendar spread value using Black-Scholes.
    Short near-term, long far-term at same strike.
    """
    near_value = black_scholes(S, K, T1, r, iv1, "C")
    far_value = black_scholes(S, K, T2, r, iv2, "C")
    return far_value - near_value
```

---

## STRAT_A5: Butterfly Spread

**Theme**: Precision Pinning
**Greeks**: Neutral Vega, -Gamma
**Sentiment**: Precision price targeting with defined risk

### When to Use

- Strong conviction on price target at expiration
- Low vega risk desired
- Limited capital for directional bet

### P&L Calculation

```python
import numpy as np

def butterfly_pnl(
    S_range: np.ndarray,
    K_low: float,
    K_mid: float,
    K_high: float,
    cost: float
) -> np.ndarray:
    """
    Long Butterfly P&L: Buy 1 low, Sell 2 mid, Buy 1 high.

    Args:
        S_range: Array of underlying prices
        K_low: Lower wing strike
        K_mid: Body strike (ATM target)
        K_high: Upper wing strike
        cost: Net debit paid

    Returns:
        P&L array
    """
    return (
        np.maximum(S_range - K_low, 0)
        - 2 * np.maximum(S_range - K_mid, 0)
        + np.maximum(S_range - K_high, 0)
        - cost
    )
```

### Risk Profile

| Metric | Calculation |
|--------|-------------|
| Max Profit | K_mid - K_low - Cost |
| Max Loss | Cost (debit paid) |
| Breakeven Low | K_low + Cost |
| Breakeven High | K_high - Cost |

---

## STRAT_A6: Synthetics

**Theme**: Arbitrage
**Greeks**: Pure Delta
**Sentiment**: Institutional edge only, put-call parity exploitation

### Put-Call Parity

```
S = C - P + K * e^(-rT)
```

### Arbitrage Detection

```python
import numpy as np

def check_parity_arbitrage(
    S: float,    # Spot price
    C: float,    # Call price
    P: float,    # Put price
    K: float,    # Strike
    r: float,    # Risk-free rate
    T: float     # Time to expiry (years)
) -> float:
    """
    Check for put-call parity violation.
    Non-zero return indicates arbitrage opportunity.

    Returns:
        Mispricing amount (positive = buy synthetic, sell actual)
    """
    synthetic_stock = C - P + (K * np.exp(-r * T))
    return S - synthetic_stock
```

---

## Black-Scholes Engine

Reference implementation for option pricing:

```python
import numpy as np
import scipy.stats as si

class BlackScholesEngine:
    @staticmethod
    def price(
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: str = "C"
    ) -> float:
        """
        Black-Scholes option pricing.

        Args:
            S: Spot price
            K: Strike price
            T: Time to expiration (years)
            r: Risk-free rate
            sigma: Implied volatility
            option_type: "C" for call, "P" for put

        Returns:
            Option price
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if option_type == "C":
            return S * si.norm.cdf(d1) - K * np.exp(-r * T) * si.norm.cdf(d2)
        return K * np.exp(-r * T) * si.norm.cdf(-d2) - S * si.norm.cdf(-d1)

    @staticmethod
    def greeks(
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: str = "C"
    ) -> dict:
        """Calculate all Greeks."""
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        # Common terms
        pdf_d1 = si.norm.pdf(d1)
        cdf_d1 = si.norm.cdf(d1)
        cdf_d2 = si.norm.cdf(d2)

        if option_type == "C":
            delta = cdf_d1
            theta = (
                -S * pdf_d1 * sigma / (2 * np.sqrt(T))
                - r * K * np.exp(-r * T) * cdf_d2
            ) / 365
        else:
            delta = cdf_d1 - 1
            theta = (
                -S * pdf_d1 * sigma / (2 * np.sqrt(T))
                + r * K * np.exp(-r * T) * si.norm.cdf(-d2)
            ) / 365

        gamma = pdf_d1 / (S * sigma * np.sqrt(T))
        vega = S * pdf_d1 * np.sqrt(T) / 100

        return {
            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "vega": vega
        }
```

---

## Data Query Patterns

### SQL: Identify Underpriced Vega

```sql
SELECT
    symbol,
    strike,
    expiry,
    (implied_vol - hist_vol_20d) AS vol_edge,
    vega,
    gamma,
    theta
FROM option_chains
WHERE symbol IN ('SLV', 'GLD')
  AND dte BETWEEN 30 AND 60
  AND delta BETWEEN 0.40 AND 0.60
ORDER BY vol_edge ASC;
```

### Python: Opportunity Scanner

```python
import yfinance as yf

def fetch_greeks_table(ticker_symbol: str) -> None:
    """Fetch and display greek data for ATM options."""
    ticker = yf.Ticker(ticker_symbol)
    expiry = ticker.options[0]  # Near term
    chain = ticker.option_chain(expiry)
    calls = chain.calls

    # Delta-Neutral Strike Identification
    spot = ticker.info.get('regularMarketPrice', 0)
    atm_call = calls.iloc[
        (calls['strike'] - spot).abs().argsort()[:1]
    ]

    print(f"--- {ticker_symbol} Strategic Greek Scan ---")
    print(atm_call[['strike', 'lastPrice', 'impliedVolatility', 'volume']])
```

### Regime Detection Query

```python
def detect_regime(greeks: list, spot: float, iv_rank: float) -> str:
    """
    Detect market regime from greek data.

    Returns one of:
    - volatility_mean_reversion
    - range_bound_stability
    - term_structure_arb
    - volatility_skew
    - regime_shift
    """
    # Calculate vol edge
    avg_iv = sum(g.implied_vol for g in greeks) / len(greeks)
    avg_hv = sum(g.hist_vol_20d for g in greeks) / len(greeks)
    vol_edge = avg_iv - avg_hv

    # Check conditions in priority order
    if vol_edge < -0.05:  # IV significantly below HV
        return "volatility_mean_reversion"

    if iv_rank > 70:  # High IV rank
        return "range_bound_stability"

    # Check term structure if multi-expiry data available
    # Check skew if put/call IV data available

    return "range_bound_stability"  # Default
```

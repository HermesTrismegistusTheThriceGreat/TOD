# Options Strategy Selection Guide

A systematic approach to selecting options strategies based on market conditions and themes.

---

## Strategy Selection Matrix

### Macro/Micro Themes → Strategy Mapping

| Theme | Strategy | Primary Greeks | Data Pull Snippet | Sentiment |
|-------|----------|----------------|-------------------|-----------|
| **Macro: Volatility Mean Reversion** | Long Straddle / Strangle | +Vega, +Gamma, -Theta | `SELECT strike, iv FROM options WHERE iv < hist_vol * 0.8 AND dte > 45` | The IV Crush killer, High risk, high reward |
| **Macro: Range-Bound Stability** | Iron Condor / Butterfly | -Vega, -Gamma, +Theta | `df[df['delta'].between(0.1, 0.3)].query('iv_rank > 70')` | The "Bread and Butter" strategy for income |
| **Micro: Term Structure Arb** | Calendar (Time) Spreads | +Vega, Neutral Delta | `SELECT * FROM chains WHERE near_iv < far_iv AND delta BETWEEN 0.45 AND 0.55` | Favored by pros for "low-risk volatility skew" plays |
| **Micro: Volatility Skew** | Ratio Spreads | -Vega, Variable Delta | `df['skew'] = df['put_iv'] - df['call_iv']; df.sort_values('skew')` | Complex; often used to hedge "Black Swan" events |
| **Macro: Regime Shift** | Dynamic Hedging | Δ-Neutral, Γ-Scalp | `while abs(net_delta) > threshold: execute_trade(-net_delta)` | The secret way Market Makers never lose |

---

## Strategy Quick Reference

| Theme | Strategy | Greeks | Sentiment | Code |
|-------|----------|--------|-----------|------|
| High Realized Vol | Long Straddle | +Γ, +V, −Θ | Buying the dip in vol | STRAT_A1 |
| Range Stability | Iron Condor | −Γ, −V, +Θ | Yield harvesting GLD | STRAT_A2 |
| Skew Exploitation | Ratio Spread | Δ Var, −V | Hedging the SLV squeeze | STRAT_A3 |
| Term Structure | Calendar Spread | Neut Δ, +V | Low-cost time decay | STRAT_A4 |
| Pinning/Targets | Butterfly Spread | Neut V, −Γ | Precision price targets | STRAT_A5 |
| Arbitrage | Synthetic/Parity | Pure Δ | Institutional edge only | STRAT_A6 |

---

## Strategy Implementations

### STRAT_A1: Long Straddle (Buying Realized Vol)

Bet on realized volatility exceeding implied volatility.

```python
import numpy as np

def long_straddle_pnl(S, K, premium, vol_realized):
    """Theoretical P&L at expiration"""
    return np.abs(S - K) - premium
```

---

### STRAT_A2: Iron Condor (Theta Generation)

Selling the wings for premium collection in range-bound markets.

```python
def iron_condor_risk_profile(S_range, wings, shorts, credit):
    """
    Args:
        wings: [put_wing, call_wing] e.g., [20, 30]
        shorts: [short_put, short_call] e.g., [22, 28]
        credit: Net credit received
    """
    pnl = np.where(S_range < wings[0], wings[0] - shorts[0] + credit,
          np.where(S_range < shorts[0], S_range - shorts[0] + credit,
          np.where(S_range < shorts[1], credit,
          np.where(S_range < wings[1], shorts[1] - S_range + credit,
          shorts[1] - wings[1] + credit))))
    return pnl
```

---

### STRAT_A3: Ratio Spreads (The Skew Play)

1x2 ratio spread for volatility skew exploitation.

```python
def ratio_spread_pnl(S_range, K1, K2, p1, p2):
    """Buy 1, Sell 2 (Net credit or debit)"""
    return (np.maximum(S_range - K1, 0)) - (2 * np.maximum(S_range - K2, 0)) - (p1 - 2*p2)
```

---

### STRAT_A4: Calendar Spread (Time Arbitrage)

Long far-dated, short near-dated for theta edge.

```python
def calendar_spread_theta_edge(near_theta, far_theta):
    """Calculate theta differential"""
    return abs(near_theta) - abs(far_theta)
```

---

### STRAT_A5: Butterfly Spread (Precision Placement)

Low vega risk, precision price targeting.

```python
def butterfly_pnl(S_range, K_low, K_mid, K_high, cost):
    """Buy 1 Low, Sell 2 Mid, Buy 1 High"""
    return (np.maximum(S_range - K_low, 0)
            - 2 * np.maximum(S_range - K_mid, 0)
            + np.maximum(S_range - K_high, 0)) - cost
```

---

### STRAT_A6: Synthetics (Put-Call Parity)

Arbitrage via synthetic positions: `S = C - P + K/(1+rt)`

```python
def check_parity_arb(S, C, P, K, r, T):
    """Non-zero return indicates arbitrage opportunity"""
    synthetic_s = C - P + (K * np.exp(-r * T))
    return S - synthetic_s
```

---

## Data Queries

### SQL: Identify Underpriced Vega in SLV/GLD

```sql
SELECT
    symbol, strike, expiry,
    (implied_vol - hist_vol_20d) AS vol_edge,
    vega, gamma, theta
FROM option_chains
WHERE symbol IN ('SLV', 'GLD')
  AND dte BETWEEN 30 AND 60
  AND delta BETWEEN 0.40 AND 0.60
ORDER BY vol_edge ASC;
```

---

### Python: Greek Data Pull (SLV/GLD Opportunity Scanner)

```python
import yfinance as yf

def fetch_greeks_table(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    expiry = ticker.options[0]  # Near term
    chain = ticker.option_chain(expiry)

    # Professional Filtering: Find High Gamma/Low Theta for Scalping
    calls = chain.calls

    # Delta-Neutral Strike Identification
    atm_call = calls.iloc[(calls['strike'] - ticker.info['regularMarketPrice']).abs().argsort()[:1]]

    print(f"--- {ticker_symbol} Strategic Greek Scan ---")
    print(atm_call[['strike', 'lastPrice', 'impliedVolatility', 'volume']])

# Usage
fetch_greeks_table("SLV")
```

---

## Black-Scholes Pricing Engine

```python
import numpy as np
import scipy.stats as si

class Engine:
    @staticmethod
    def black_scholes(S, K, T, r, sigma, option_type="C"):
        """
        Black-Scholes option pricing

        Args:
            S: Spot price
            K: Strike price
            T: Time to expiration (years)
            r: Risk-free rate
            sigma: Implied volatility
            option_type: "C" for call, "P" for put
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if option_type == "C":
            return S * si.norm.cdf(d1) - K * np.exp(-r * T) * si.norm.cdf(d2)
        return K * np.exp(-r * T) * si.norm.cdf(-d2) - S * si.norm.cdf(-d1)
```

---

## Full P&L Calculation Functions

### A1: Long Straddle (Buying Volatility)

```python
def straddle_pnl(S_range, K, premium_paid):
    """P&L = |S - K| - Cost (Natenberg p. 150)"""
    return np.abs(S_range - K) - premium_paid
```

### A2: Iron Condor (Neutral)

```python
def iron_condor_pnl(S_range, put_wing, short_put, short_call, call_wing, net_credit):
    pnl = np.where(S_range <= put_wing, (put_wing - short_put) + net_credit,
          np.where(S_range <= short_put, (S_range - short_put) + net_credit,
          np.where(S_range <= short_call, net_credit,
          np.where(S_range <= call_wing, (short_call - S_range) + net_credit,
          (short_call - call_wing) + net_credit))))
    return pnl
```

### A3: Ratio Spread (1x2 Call Ratio)

```python
def call_ratio_pnl(S_range, K1, K2, p1, p2):
    """Buy 1 K1, Sell 2 K2 (Credit or Debit)"""
    cost = p1 - (2 * p2)
    pnl = (np.maximum(S_range - K1, 0)) - (2 * np.maximum(S_range - K2, 0)) - cost
    return pnl
```

### A4: Calendar Spread (Time Arb)

```python
def calendar_val(S, K, T1, T2, r, iv1, iv2):
    """Short Near-Term IV, Long Far-Term IV"""
    near_month = Engine.black_scholes(S, K, T1, r, iv1)
    far_month = Engine.black_scholes(S, K, T2, r, iv2)
    return far_month - near_month
```

### A5: Butterfly Spread (Precision)

```python
def butterfly_pnl(S_range, K_low, K_mid, K_high, cost):
    """Buy 1 Low, Sell 2 Mid, Buy 1 High"""
    return (np.maximum(S_range - K_low, 0)
            - 2 * np.maximum(S_range - K_mid, 0)
            + np.maximum(S_range - K_high, 0)) - cost
```

---
allowed-tools: mcp__mgmt__create_agent, mcp__mgmt__command_agent, mcp__mgmt__check_agent_status, mcp__mgmt__delete_agent, Bash(sleep:*)
description: Calculate probabilistic price ranges for 1, 2, and 3-week horizons using exponentially weighted historical volatility
argument-hint: [ticker]
model: opus
---

# Purpose

Calculate probabilistic price ranges for 1, 2, and 3-week horizons using exponentially weighted historical movement data. Applies statistical scaling (drift grows linearly, volatility grows with square root of time) to generate 68% and 95% confidence bands around expected prices. Output helps traders visualize realistic upside targets and downside risks for position sizing, strike selection, and risk management without making directional predictions.

## Variables

TICKER: $1
ANALYSIS_TIMESTAMP: Current date/time when prompt is executed (auto-captured)
CURRENT_PRICE: Fetched automatically via yfinance (no user input required)
HISTORICAL_PERIOD: 2 years (500 trading days for EWM calculation)
EWM_SPAN: 63 trading days (quarterly weighting)
CONFIDENCE_LEVELS: 68% (1 std dev) and 95% (2 std dev)
SLEEP_INTERVAL: 10 seconds

## Instructions

- **IMPORTANT: If no TICKER is provided, ask the user to provide a ticker symbol**
- This workflow uses a **team of specialized agents** to keep each agent's context minimal and optimize performance
- **Agent Architecture**:
  1. **Data Agent** (haiku/fast): Fetches historical data using yfinance - minimal context, single purpose
  2. **Calculator Agent** (opus): Performs statistical calculations and generates the forecast report
- **Statistical Methodology**:
  - Use exponentially weighted volatility (EWM) to weight recent price movements more heavily
  - Drift (expected return) scales linearly with time: `drift_t = daily_drift × t`
  - Volatility scales with square root of time: `vol_t = daily_vol × sqrt(t)`
  - 68% confidence = ±1 standard deviation (normal distribution)
  - 95% confidence = ±2 standard deviations (normal distribution)
- Do NOT make directional predictions - this is purely probabilistic range estimation
- The data agent writes results to a temp file; the calculator agent reads from it
- Clean up agents after completion to keep the system tidy

## Workflow

### Phase 1: Create Specialized Agents

1. **(Create Data Agent)** Run `create_agent` with:
   - `name`: "data-{TICKER}"
   - `model`: "haiku" (fast, low context)
   - `system_prompt`: Specialized data fetcher prompt (see below)

2. **(Create Calculator Agent)** Run `create_agent` with:
   - `name`: "calc-{TICKER}"
   - `model`: "opus" (latest and smartest Claude model)
   - `system_prompt`: Statistical calculator prompt (see below)

### Phase 2: Fetch Historical Data

3. **(Command Data Agent)** Run `command_agent` with the data fetch instructions:
   ```
   Fetch 2 years of daily OHLC data for {TICKER} using yfinance.

   Use this Python code:

   import yfinance as yf
   import pandas as pd
   from datetime import datetime, timedelta

   ticker = "{TICKER}"
   end_date = datetime.now()
   start_date = end_date - timedelta(days=730)  # 2 years

   data = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))

   # Calculate daily returns
   data['Return'] = data['Adj Close'].pct_change()

   # Calculate EWM statistics (63-day span = quarterly)
   span = 63
   data['EWM_Vol'] = data['Return'].ewm(span=span).std()
   data['EWM_Drift'] = data['Return'].ewm(span=span).mean()

   # Get latest values
   latest_vol = data['EWM_Vol'].iloc[-1]
   latest_drift = data['EWM_Drift'].iloc[-1]
   latest_price = data['Adj Close'].iloc[-1]

   # Annualized volatility for context
   annualized_vol = latest_vol * (252 ** 0.5)

   # Output the results
   print(f"TICKER: {ticker}")
   print(f"LATEST_PRICE: {latest_price:.2f}")
   print(f"DAILY_VOLATILITY: {latest_vol:.6f}")
   print(f"DAILY_DRIFT: {latest_drift:.6f}")
   print(f"ANNUALIZED_VOL: {annualized_vol:.4f}")
   print(f"DATA_POINTS: {len(data)}")

   Run this with: uv run --with yfinance --with pandas python -c "..."

   Report the output values clearly.
   ```

4. **(Monitor Data Agent)** Sleep for SLEEP_INTERVAL and check status until completion
   - Look for `response` event_category followed by `hook` with `Stop` event_type

5. **(Extract Data)** Parse the data agent's output to get:
   - LATEST_PRICE (current price from yfinance)
   - DAILY_VOLATILITY
   - DAILY_DRIFT
   - DATA_POINTS count

### Phase 3: Calculate Price Ranges

6. **(Command Calculator Agent)** Run `command_agent` with the calculation instructions:
   ```
   Calculate probabilistic price ranges for {TICKER} at current price ${LATEST_PRICE}.

   Use these statistics from the data agent:
   - Daily Volatility (EWM): {DAILY_VOLATILITY}
   - Daily Drift (EWM): {DAILY_DRIFT}

   Apply the statistical methodology:

   For each horizon (5, 10, 15 trading days = 1, 2, 3 weeks):

   1. Calculate expected price:
      expected_price = current_price × (1 + daily_drift × days)

   2. Calculate volatility at horizon:
      vol_at_horizon = daily_vol × sqrt(days)

   3. Calculate price ranges:
      68% confidence (1σ):
        lower_68 = expected_price × (1 - vol_at_horizon)
        upper_68 = expected_price × (1 + vol_at_horizon)

      95% confidence (2σ):
        lower_95 = expected_price × (1 - 2 × vol_at_horizon)
        upper_95 = expected_price × (1 + 2 × vol_at_horizon)

   Generate a report with:
   - Current price and volatility metrics
   - Table showing ranges for each horizon
   - Maximum drawdown and rally estimates
   - Risk management context (what 1σ and 2σ moves mean in dollar terms)
   ```

7. **(Monitor Calculator Agent)** Sleep for SLEEP_INTERVAL and check status until completion

8. **(Extract Results)** Capture the calculator agent's full report

### Phase 4: Cleanup and Report

9. **(Delete Agents)** Run `delete_agent` for both agents to clean up

10. **(Present Report)** Format and present the final forecast to the user

## Agent System Prompts

### Data Agent System Prompt
```
You are a minimal data fetching agent. Your ONLY job is to:
1. Run the provided Python code using yfinance
2. Report the numerical results
Do NOT perform analysis. Just fetch and report data.
Use Bash to run Python with: uv run --with yfinance --with pandas python -c "..."
```

### Calculator Agent System Prompt
```
You are a statistical calculation agent. Your job is to:
1. Apply statistical formulas to calculate price probability ranges
2. Generate clean, formatted reports
3. Explain the methodology clearly
Do NOT fetch data. Work only with the numbers provided.
Present results in a trader-friendly format with clear risk context.
```

## Report

Present the forecast in this format:

---

## Probabilistic Price Forecast: {TICKER}

**Current Price:** ${LATEST_PRICE}
**Analysis Date:** {ANALYSIS_TIMESTAMP}
**Methodology:** Exponentially Weighted Moving Average (63-day span)

### Volatility Metrics

| Metric | Value |
|--------|-------|
| Daily EWM Volatility | {daily_vol}% |
| Annualized Volatility | {annual_vol}% |
| Daily EWM Drift | {daily_drift}% |

### Price Range Forecast

| Horizon | Expected Price | 68% Range (1σ) | 95% Range (2σ) |
|---------|---------------|----------------|----------------|
| **1 Week (5d)** | ${expected_1w} | ${lower_68_1w} - ${upper_68_1w} | ${lower_95_1w} - ${upper_95_1w} |
| **2 Weeks (10d)** | ${expected_2w} | ${lower_68_2w} - ${upper_68_2w} | ${lower_95_2w} - ${upper_95_2w} |
|**3 Weeks (15d)** | ${expected_3w} | ${lower_68_3w} - ${upper_68_3w} | ${lower_95_3w} - ${upper_95_3w} |

### Risk Context (per $1,000 position)

| Horizon | 1σ Move ($) | 2σ Move ($) |
|---------|------------|------------|
| 1 Week | ±${1sigma_1w} | ±${2sigma_1w} |
| 2 Weeks | ±${1sigma_2w} | ±${2sigma_2w} |
| 3 Weeks | ±${1sigma_3w} | ±${2sigma_3w} |

### Interpretation

- **68% probability**: Price stays within the 1σ range
- **95% probability**: Price stays within the 2σ range
- **~16% probability**: Price exceeds upper 1σ band (upside breakout)
- **~16% probability**: Price falls below lower 1σ band (downside break)
- **~2.5% probability**: Price moves beyond 2σ in either direction

### Use Cases

- **Position Sizing**: Size positions so 2σ moves are within risk tolerance
- **Strike Selection**: Consider 1σ ranges for ATM options, 2σ for OTM
- **Stop Loss Placement**: 1σ for tight stops, 2σ for swing trades
- **Profit Targets**: 1σ moves are high-probability, 2σ moves are stretch goals

---

*This analysis is purely statistical and does not predict direction. Past volatility may not predict future volatility. Use in conjunction with other analysis methods.*

# Options Theta Collection Analysis Agent

  ## Objective
  Analyze options for optimal theta collection strategies with defined risk parameters.

  ## Inputs
  - `UNDERLYING`: Stock/ETF symbol (e.g., GLD, SPY)
  - `EXPIRATION`: Target expiration date or description (e.g., "2026-01-21", "next Friday", "upcoming weekly")
  - `WING_WIDTHS`: Array of wing widths to analyze (e.g., [6, 8, 10])
  - `CONTRACTS`: Number of contracts per leg (e.g., 100)

  ## Execution Steps

  ### Step 1: Get Current Spot Price
  get_stock_snapshot(UNDERLYING)
  Extract: latest trade price → SPOT_PRICE

  ### Step 2: Determine ATM Strike
  ATM_STRIKE = round(SPOT_PRICE) to nearest available strike

  ### Step 3: Pull Option Chain with Greeks
  get_option_chain(
    underlying_symbol=UNDERLYING,
    expiration_date=EXPIRATION,
    strike_price_gte=ATM_STRIKE - max(WING_WIDTHS),
    strike_price_lte=ATM_STRIKE + max(WING_WIDTHS)
  )

  ### Step 4: Extract ATM Straddle Data
  From option chain, find:
  - ATM_CALL: bid, ask, theta, delta for strike = ATM_STRIKE
  - ATM_PUT: bid, ask, theta, delta for strike = ATM_STRIKE

  Calculate:
  - STRADDLE_CREDIT = (ATM_CALL.mid + ATM_PUT.mid)
  - STRADDLE_THETA = |ATM_CALL.theta| + |ATM_PUT.theta|

  ### Step 5: For Each Wing Width, Calculate Iron Butterfly Metrics
  for WIDTH in WING_WIDTHS:
      CALL_WING_STRIKE = ATM_STRIKE + WIDTH
      PUT_WING_STRIKE = ATM_STRIKE - WIDTH

  # Extract wing option data
  LONG_CALL = option at CALL_WING_STRIKE (call)
  LONG_PUT = option at PUT_WING_STRIKE (put)

  # Calculate metrics
  WING_COST = LONG_CALL.ask + LONG_PUT.ask
  NET_CREDIT = STRADDLE_CREDIT - WING_COST
  MAX_LOSS = WIDTH - NET_CREDIT
  NET_THETA = STRADDLE_THETA - |LONG_CALL.theta| - |LONG_PUT.theta|

  # Ratios
  THETA_RISK_RATIO = NET_THETA / MAX_LOSS
  CREDIT_PCT = (NET_CREDIT / WIDTH) * 100
  REWARD_RISK = NET_CREDIT / MAX_LOSS

  ### Step 6: Output Format

  {UNDERLYING} Theta Analysis - {EXPIRATION} ({DTE} DTE)

  Spot Price: ${SPOT_PRICE}
  ATM Strike: {ATM_STRIKE}

  ATM Straddle
  ┌───────────┬──────────────────┬─────────────────┬───────────────────────┐
  │  Metric   │       Call       │       Put       │       Combined        │
  ├───────────┼──────────────────┼─────────────────┼───────────────────────┤
  │ Mid Price │ ${ATM_CALL.mid}  │ ${ATM_PUT.mid}  │ ${STRADDLE_CREDIT}    │
  ├───────────┼──────────────────┼─────────────────┼───────────────────────┤
  │ Theta     │ {ATM_CALL.theta} │ {ATM_PUT.theta} │ +{STRADDLE_THETA}/day │
  └───────────┴──────────────────┴─────────────────┴───────────────────────┘
  Iron Butterfly Comparison
  ┌───────────┬───────────────┬─────────────┬──────────────┬─────────────────────┬───────────────┬─────────────────┐
  │   Width   │  Net Credit   │  Max Loss   │  Theta/Day   │     Theta/Risk      │   Credit %    │       R:R       │
  ├───────────┼───────────────┼─────────────┼──────────────┼─────────────────────┼───────────────┼─────────────────┤
  │ {WIDTH}pt │ ${NET_CREDIT} │ ${MAX_LOSS} │ ${NET_THETA} │ {THETA_RISK_RATIO}% │ {CREDIT_PCT}% │ {REWARD_RISK}:1 │
  └───────────┴───────────────┴─────────────┴──────────────┴─────────────────────┴───────────────┴─────────────────┘
  Ranked Recommendations

  1. #{RANK} - {WIDTH}pt Iron Fly - Best theta efficiency at {THETA_RISK_RATIO}%/day
    - Structure: {PUT_WING}/{ATM}/{CALL_WING}
    - Credit ({CONTRACTS} contracts): ${NET_CREDIT * CONTRACTS * 100}
    - Max Loss: ${MAX_LOSS * CONTRACTS * 100}

  ## Ranking Criteria (weighted)
  1. **Theta/Max Risk Ratio** (primary) - Higher is better
  2. **Credit % of Width** (secondary) - Higher means more premium capture
  3. **Reward:Risk Ratio** (tertiary) - Higher provides better risk-adjusted return

  ## Edge Cases
  - If no options for requested expiration: check adjacent dates, list available expirations
  - If ATM strike doesn't exist: use closest strike, note delta skew
  - If markets closed (holiday): identify next trading day
  - If Greeks unavailable: estimate theta from time decay or skip contract
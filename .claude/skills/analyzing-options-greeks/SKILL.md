---
name: analyzing-options-greeks
description: Analyzes options Greeks (delta, gamma, theta, vega, rho) for trade exit signals, strategy selection, position risk evaluation, and theta decay optimization. Use when user asks about Greeks interpretation, IV analysis, open interest patterns, volatility surfaces, or options strategy selection based on Greek profiles.
---

# Options Greeks Analysis

Expert guidance on options Greeks analysis and trading applications for informed decision-making.

## Instructions

### Prerequisites

Read the comprehensive training documentation for detailed context:
- [options-greeks-expert-training.md](options-greeks-expert-training.md) - Full research with 144 citation-ready facts

### Core Capabilities

This skill enables analysis in four key domains:

1. **Interpreting Greeks for Trade Exit Signals**
2. **Selecting Optimal Strategies Based on Greek Profiles**
3. **Evaluating Position Risk Through Greek Analysis**
4. **Optimizing Theta Decay Collection**

### Workflow

#### 1. Greeks-Based Trade Exit Signals

**Theta-Based Exits**:
- Primary exit target: **21 DTE** (captures 60-80% of profit)
- Compare daily theta rates to assess acceleration
- Exit at favorable times to prevent excessive holding

**DTE Action Framework**:

| DTE Window | Action | Reasoning |
|------------|--------|-----------|
| 45-30 DTE | HOLD | Entry zone, manageable decay |
| 30-14 DTE | MONITOR | Accelerating but controlled |
| 14-7 DTE | DECIDE | Rapid acceleration zone |
| 0-7 DTE | EXIT/AVOID | Extreme decay + gamma risk |

**IV-Based Exits**:
- IV >> HV: Signals overpriced options - exit long positions
- Vega expansion hurts iron condors - consider exit
- IV contraction benefits short premium - continue holding

#### 2. Strategy Selection Based on Greek Profiles

**High-Delta Strategies** (Directional):
- Target: Delta 0.7-1.0 (calls) or -0.7 to -1.0 (puts)
- Examples: Deep ITM options, synthetic stock
- Risk: Limited time decay protection

**High-Gamma Strategies** (Scalping):
- Target: ATM options with high gamma
- Benefit: Delta changes rapidly with price
- Risk: Transaction costs from constant adjustments

**High-Theta Strategies** (Income):
- Target: Positive theta (short options)
- Strategies: Covered calls, cash-secured puts, iron condors
- Optimal entry: 30-45 DTE | Optimal exit: 21 DTE

**High-Vega Strategies** (Volatility Plays):
- Target: Positive vega (long options)
- Strategies: Long straddles, strangles
- Entry: Low IV rank/percentile (<30%)

#### 3. Position Risk Evaluation

**Multi-Leg Greeks Aggregation**:
- Calculate cumulative delta, theta, gamma, vega across all legs
- Gamma-Theta correlation: Increasing gamma = accelerated theta decay

**Delta-Neutral Construction**:
- Stock delta 1.0 offset by put -0.5 + call -0.5
- Continuous rebalancing required

**High-Gamma Risk Management**:
1. Limit position sizes
2. Use stop-loss orders
3. Diversify gamma across uncorrelated positions
4. Automate adjustments

#### 4. Theta Decay Optimization

**DTE-Based Protocol**:
1. **Enter at 30-45 DTE**: Optimal theta/gamma ratio
2. **Monitor at 21 DTE**: Decision point
3. **Exit by 14 DTE**: Unless specific thesis
4. **Avoid final 7 days**: Theta/gamma tradeoff unfavorable

**Theta Decay Schedule**:

| DTE Window | Daily Decay | Cumulative | Risk Level |
|------------|-------------|------------|------------|
| 45-30 | $0.08-0.12 | 20-30% | Low |
| 30-14 | $0.15-0.25 | 30-60% | Medium |
| 14-7 | $0.25-0.40 | 60-85% | High |
| 0-7 | >$0.40 | 85-100% | Extreme |

### Reference Tables

**Greek Ranges**:

| Greek | Calls | Puts | Peak Location |
|-------|-------|------|---------------|
| Delta | 0 to 1.0 | -1.0 to 0 | Deep ITM |
| Gamma | Positive | Positive | ATM |
| Theta | Negative (long) | Negative (long) | ATM near expiration |
| Vega | Positive (long) | Positive (long) | ATM |

**Put/Call Ratio Thresholds**:

| Metric | Bullish | Bearish |
|--------|---------|---------|
| Daily Extreme | ≤0.70 | ≥1.20 |
| 10-Day SMA | 0.80 | 0.95 |

**IV Environment Guidelines**:

| IV Rank | Strategy Bias |
|---------|---------------|
| 0-30% | Buy premium (long vega) |
| 30-50% | Neutral; strategy-dependent |
| 50-80% | Sell premium (short vega) |
| 80-100% | Aggressively sell premium |

**Term Structure Patterns**:

| Pattern | Frequency | Signal |
|---------|-----------|--------|
| Contango | >80% | Normal market |
| Backwardation | <20% | Stressed/uncertain |

## Examples

### Example 1: Trade Exit Timing Analysis

User request:
```
I have an iron condor at 18 DTE with 65% profit. Should I close?
```

You would:
1. Reference the DTE Action Framework - 18 DTE is in the 14-30 DTE "MONITOR" zone
2. Note that 65% profit exceeds the 60-80% target for 21 DTE exit
3. Consider gamma acceleration risk approaching 14 DTE
4. Recommend closing the position to lock in profits and avoid gamma explosion

Response: "At 18 DTE with 65% profit, you've already captured strong returns. The 21 DTE exit rule suggests closing now - you've achieved the target profit range (60-80%) while avoiding the gamma acceleration zone below 14 DTE. Close the position."

### Example 2: Strategy Selection Based on IV

User request:
```
IV Rank is 85% on SPY. What strategy should I use?
```

You would:
1. Reference IV Environment Guidelines - 80-100% range = "Aggressively sell premium"
2. Recommend short vega strategies
3. Suggest specific structures

Response: "With IV Rank at 85%, premium selling is optimal. Consider: iron condors (benefit from high IV + theta decay), credit spreads, or short strangles if you can handle the risk. Enter at 30-45 DTE for optimal theta/gamma ratio."

### Example 3: Greeks Interpretation for Position Risk

User request:
```
My position has: Delta +50, Gamma +15, Theta -25, Vega +30. What's my risk?
```

You would:
1. Analyze each Greek exposure
2. Identify the gamma-theta relationship
3. Assess directional and volatility risk

Response: "Your position is:
- **Directionally bullish** (Delta +50 = long ~50 shares equivalent)
- **Long gamma** (+15) = benefits from large moves but pays theta
- **Negative theta** (-25/day) = losing $25 daily to time decay
- **Long vega** (+30) = benefits from IV expansion

Risk profile: You need either a significant directional move or IV expansion to overcome theta decay. High gamma means rapid delta changes - good for volatile markets but costly in sideways action."

### Example 4: Open Interest Support/Resistance

User request:
```
SPY has highest put OI at 550 and highest call OI at 580. Current price is 565.
```

You would:
1. Reference OI patterns for support/resistance
2. Identify structural levels

Response: "Based on open interest:
- **Support at 550**: Heavy put OI creates structural support - put sellers hedge by buying stock as price approaches, creating a natural bid
- **Resistance at 580**: Heavy call OI creates resistance - call sellers hedge by shorting stock, creating selling pressure

Expected range: 550-580 through this expiration, with 565 as midpoint. Note: OI levels are guides, not guarantees - major catalysts can override."

# GLD Iron Butterfly Theta Collection Analysis

**Spot Price:** $421.29
**ATM Strike:** 421
**Analysis Date:** 2026-01-17

---

## 2026-01-21 Expiry - 4 DTE

**ATM Straddle:**
- 421 Call: Bid $3.40, θ = -0.4232
- 421 Put: Bid $2.99, θ = -0.3908
- **Straddle Credit:** $6.39 | **Net θ:** 0.814/day

| Wing Width | Strikes | Credit | Max Loss | θ/Risk | θ/Credit | Credit % | Risk:Reward | Flag |
|------------|---------|--------|----------|--------|----------|----------|-------------|------|
| 6 pts | 415/427 | $4.05 | $1.95 | 9.06% | 4.36% | 67.5% | 0.48:1 | - |
| 8 pts | 413/429 | $4.79 | $3.21 | 8.86% | 5.94% | 59.9% | 0.67:1 | - |
| 10 pts | 411/431 | $5.34 | $4.66 | 8.35% | 7.29% | 53.4% | 0.87:1 | - |

**Wing Details:**
- 6pt: Short 415P/427C @ $2.34, Net θ = 0.177/day
- 8pt: Short 413P/429C @ $1.60, Net θ = 0.285/day
- 10pt: Short 411P/431C @ $1.05, Net θ = 0.389/day

---

## 2026-01-23 Expiry - 6 DTE

**ATM Straddle:**
- 421 Call: Bid $4.60, θ = -0.3899
- 421 Put: Bid $4.00, θ = -0.3450
- **Straddle Credit:** $8.60 | **Net θ:** 0.735/day

| Wing Width | Strikes | Credit | Max Loss | θ/Risk | θ/Credit | Credit % | Risk:Reward | Flag |
|------------|---------|--------|----------|--------|----------|----------|-------------|------|
| 6 pts | 415/427 | $4.36 | $1.64 | 5.63% | 2.12% | 72.7% | 0.38:1 | - |
| 8 pts | 413/429 | $5.38 | $2.62 | 6.04% | 2.94% | 67.3% | 0.49:1 | - |
| 10 pts | 411/431 | $6.18 | $3.82 | 5.95% | 3.68% | 61.8% | 0.62:1 | - |

**Wing Details:**
- 6pt: Short 415P/427C @ $4.24, Net θ = 0.092/day
- 8pt: Short 413P/429C @ $3.22, Net θ = 0.158/day
- 10pt: Short 411P/431C @ $2.42, Net θ = 0.227/day

---

## 2026-01-30 Expiry - 13 DTE

**ATM Straddle:**
- 421 Call: Bid $7.15, θ = -0.2837
- 421 Put: Bid $6.25, θ = -0.2391
- **Straddle Credit:** $13.40 | **Net θ:** 0.523/day

| Wing Width | Strikes | Credit | Max Loss | θ/Risk | θ/Credit | Credit % | Risk:Reward | Flag |
|------------|---------|--------|----------|--------|----------|----------|-------------|------|
| 6 pts | 415/427 | $4.80 | $1.20 | 2.54% | 0.64% | 80.0% | 0.25:1 | - |
| 8 pts | 413/429 | $6.10 | $1.90 | 2.79% | 0.87% | 76.3% | 0.31:1 | - |
| 10 pts | 411/431 | $7.32 | $2.68 | 2.94% | 1.08% | 73.2% | 0.37:1 | - |

**Wing Details:**
- 6pt: Short 415P/427C @ $8.60, Net θ = 0.031/day
- 8pt: Short 413P/429C @ $7.30, Net θ = 0.053/day
- 10pt: Short 411P/431C @ $6.08, Net θ = 0.079/day

---

## Rankings

### By Theta Efficiency (θ/Risk) - Best Decay Rate

This metric shows daily theta decay as a percentage of maximum loss. Higher is better for rapid premium collection.

| Rank | Expiry | Wings | DTE | θ/Risk | θ/Credit | Max Loss | Credit | Flag |
|------|--------|-------|-----|--------|----------|----------|--------|------|
| 1 | 2026-01-21 | 6 pt | 4 | 9.06% | 4.36% | $1.95 | $4.05 | - |
| 2 | 2026-01-21 | 8 pt | 4 | 8.86% | 5.94% | $3.21 | $4.79 | - |
| 3 | 2026-01-21 | 10 pt | 4 | 8.35% | 7.29% | $4.66 | $5.34 | - |
| 4 | 2026-01-23 | 8 pt | 6 | 6.04% | 2.94% | $2.62 | $5.38 | - |
| 5 | 2026-01-23 | 10 pt | 6 | 5.95% | 3.68% | $3.82 | $6.18 | - |
| 6 | 2026-01-23 | 6 pt | 6 | 5.63% | 2.12% | $1.64 | $4.36 | - |
| 7 | 2026-01-30 | 10 pt | 13 | 2.94% | 1.08% | $2.68 | $7.32 | - |
| 8 | 2026-01-30 | 8 pt | 13 | 2.79% | 0.87% | $1.90 | $6.10 | - |
| 9 | 2026-01-30 | 6 pt | 13 | 2.54% | 0.64% | $1.20 | $4.80 | - |

### By Theta Efficiency (θ/Credit) - Stable Metric

This metric shows theta as a percentage of credit received. Less sensitive to small max loss values.

| Rank | Expiry | Wings | DTE | θ/Credit | θ/Risk | Net Credit | Flag |
|------|--------|-------|-----|----------|--------|------------|------|
| 1 | 2026-01-21 | 10 pt | 4 | 7.29% | 8.35% | $5.34 | - |
| 2 | 2026-01-21 | 8 pt | 4 | 5.94% | 8.86% | $4.79 | - |
| 3 | 2026-01-21 | 6 pt | 4 | 4.36% | 9.06% | $4.05 | - |
| 4 | 2026-01-23 | 10 pt | 6 | 3.68% | 5.95% | $6.18 | - |
| 5 | 2026-01-23 | 8 pt | 6 | 2.94% | 6.04% | $5.38 | - |
| 6 | 2026-01-23 | 6 pt | 6 | 2.12% | 5.63% | $4.36 | - |
| 7 | 2026-01-30 | 10 pt | 13 | 1.08% | 2.94% | $7.32 | - |
| 8 | 2026-01-30 | 8 pt | 13 | 0.87% | 2.79% | $6.10 | - |
| 9 | 2026-01-30 | 6 pt | 13 | 0.64% | 2.54% | $4.80 | - |

### By Risk-Reward (Credit %) - Best Probability

Higher credit percentage means better margin of error before assignment. Lower risk:reward ratio is better.

| Rank | Expiry | Wings | DTE | Credit % | Risk:Reward | Max Loss | Credit | Flag |
|------|--------|-------|-----|----------|-------------|----------|--------|------|
| 1 | 2026-01-30 | 6 pt | 13 | 80.0% | 0.25:1 | $1.20 | $4.80 | - |
| 2 | 2026-01-30 | 8 pt | 13 | 76.3% | 0.31:1 | $1.90 | $6.10 | - |
| 3 | 2026-01-30 | 10 pt | 13 | 73.2% | 0.37:1 | $2.68 | $7.32 | - |
| 4 | 2026-01-23 | 6 pt | 6 | 72.7% | 0.38:1 | $1.64 | $4.36 | - |
| 5 | 2026-01-21 | 6 pt | 4 | 67.5% | 0.48:1 | $1.95 | $4.05 | - |
| 6 | 2026-01-23 | 8 pt | 6 | 67.3% | 0.49:1 | $2.62 | $5.38 | - |
| 7 | 2026-01-23 | 10 pt | 6 | 61.8% | 0.62:1 | $3.82 | $6.18 | - |
| 8 | 2026-01-21 | 8 pt | 4 | 59.9% | 0.67:1 | $3.21 | $4.79 | - |
| 9 | 2026-01-21 | 10 pt | 4 | 53.4% | 0.87:1 | $4.66 | $5.34 | - |

---

## Data Quality Assessment

**Data Confidence: HIGH**

All 9 strategy combinations passed validation checks:
- No max loss values below $0.10
- No credit percentages exceeding 95%
- All wing costs above $0.50 threshold
- All data appears to be live market quotes

---

## Key Insights

**Best for Theta Decay:**
- **2026-01-21 6pt Iron Butterfly (415/421/421/427)** - 9.06% θ/Risk
  - Collects $4.05 credit with only $1.95 max loss
  - Generates 0.177 theta/day (21.7% of straddle theta)
  - Extremely tight breakevens provide rapid decay in range

**Best Risk-Reward:**
- **2026-01-30 6pt Iron Butterfly (415/421/421/427)** - 80% Credit, 0.25:1 Risk
  - Collects $4.80 credit with only $1.20 max loss
  - Wide margin of safety - can absorb $4.80 move before max loss
  - However, lower theta efficiency at 2.54% θ/Risk

**Balanced Pick:**
- **2026-01-23 8pt Iron Butterfly (413/421/421/429)** - 6.04% θ/Risk, 67.3% Credit
  - Collects $5.38 credit with $2.62 max loss
  - 6 DTE provides good balance between decay and safety
  - Net theta of 0.158/day is 21.5% of straddle theta
  - Moderate breakevens at 413/429 (±$8 from spot of $421.29)

**Strategy Comparison:**
- **4 DTE (Jan 21):** Highest theta efficiency but tighter management window
- **6 DTE (Jan 23):** Good balance of decay and time for adjustment
- **13 DTE (Jan 30):** Best probability/credit ratio but lowest theta decay

**Wing Width Analysis:**
- **6pt Wings:** Highest θ/Risk, tightest breakevens, lowest capital at risk
- **8pt Wings:** Balanced theta and probability metrics
- **10pt Wings:** Most credit collected, widest safety margin, highest capital at risk

---

## Trade Execution Notes

1. **Entry Timing:** Best filled during market hours with tight bid-ask spreads
2. **Greeks Watch:** Monitor delta to ensure position stays delta-neutral
3. **Adjustment Triggers:** Consider rolling if underlying moves beyond breakevens
4. **Exit Strategy:** Many traders close at 50% max profit or at 21 DTE whichever comes first
5. **Position Sizing:** Max loss represents actual capital at risk per contract

**Analysis saved to:** /Users/muzz/Desktop/tac/TOD/specs/GLD-theta-analysis.md

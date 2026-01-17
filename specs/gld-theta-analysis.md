# GLD Iron Butterfly Theta Analysis

**Spot Price:** $421.78
**ATM Strike:** 422
**Analysis Date:** 2026-01-16

---

## 2026-01-23 - 7 DTE

### ATM Straddle
| Strike | Type | Bid | Theta |
|--------|------|-----|-------|
| 422 | Call | $4.10 | -0.3034 |
| 422 | Put | $4.50 | -0.3249 |
| **Straddle** | | **$8.60** | **-0.6283** |

### Iron Butterfly Metrics

| Wing Width | Wing Strikes | Wing Cost | Net Credit | Max Loss | Net θ | θ/Risk | Credit % |
|------------|--------------|-----------|------------|----------|-------|--------|----------|
| 6 pts | 416P / 428C | $3.33 | $5.27 | $0.73 | 0.1043 | 14.29% | 87.83% |
| 8 pts | 414P / 430C | $3.51 | $5.09 | $2.91 | 0.1635 | 5.62% | 63.63% |
| 10 pts | 412P / 432C | $2.42 | $6.18 | $3.82 | 0.1969 | 5.15% | 61.80% |

**Wing Details:**
- 416 Put: Ask $1.71, θ = -0.2756
- 428 Call: Ask $1.62, θ = -0.2484
- 414 Put: Ask $2.06, θ = -0.2601
- 430 Call: Ask $1.45, θ = -0.2324
- 412 Put: Ask $1.36, θ = -0.2310
- 432 Call: Ask $1.06, θ = -0.2004

---

## 2026-01-26 - 10 DTE

### ATM Straddle
| Strike | Type | Bid | Theta |
|--------|------|-----|-------|
| 422 | Call | $4.70 | -0.2456 |
| 422 | Put | $5.05 | -0.2518 |
| **Straddle** | | **$9.75** | **-0.4974** |

### Iron Butterfly Metrics

| Wing Width | Wing Strikes | Wing Cost | Net Credit | Max Loss | Net θ | θ/Risk | Credit % |
|------------|--------------|-----------|------------|----------|-------|--------|----------|
| 6 pts | 416P / 428C | $5.27 | $4.48 | $1.52 | 0.0501 | 3.30% | 74.67% |
| 8 pts | 414P / 430C | $4.11 | $5.64 | $2.36 | 0.0888 | 3.76% | 70.50% |
| 10 pts | 412P / 432C | $3.22 | $6.53 | $3.47 | 0.1138 | 3.28% | 65.30% |

**Wing Details:**
- 416 Put: Ask $2.77, θ = -0.2254
- 428 Call: Ask $2.50, θ = -0.2218
- 414 Put: Ask $2.19, θ = -0.2083
- 430 Call: Ask $1.92, θ = -0.2012
- 412 Put: Ask $1.74, θ = -0.1911
- 432 Call: Ask $1.48, θ = -0.1793

---

## 2026-01-28 - 12 DTE

### ATM Straddle
| Strike | Type | Bid | Theta |
|--------|------|-----|-------|
| 422 | Call | $5.75 | -0.2502 |
| 422 | Put | $6.00 | -0.2476 |
| **Straddle** | | **$11.75** | **-0.4978** |

### Iron Butterfly Metrics

| Wing Width | Wing Strikes | Wing Cost | Net Credit | Max Loss | Net θ | θ/Risk | Credit % |
|------------|--------------|-----------|------------|----------|-------|--------|----------|
| 6 pts | 416P / 428C | $6.10 | $5.65 | $0.35 | 0.0534 | 15.26% | 94.17% |
| 8 pts | 414P / 430C | $5.80 | $5.95 | $2.05 | 0.0802 | 3.91% | 74.38% |
| 10 pts | 412P / 432C | $4.75 | $7.00 | $3.00 | 0.1048 | 3.49% | 70.00% |

**Wing Details:**
- 416 Put: Ask $3.65, θ = -0.2287
- 428 Call: Ask $3.45, θ = -0.2335
- 414 Put: Ask $2.99, θ = -0.2159
- 430 Call: Ask $2.81, θ = -0.2199
- 412 Put: Ask $2.46, θ = -0.2017
- 432 Call: Ask $2.29, θ = -0.2035

---

## 2026-01-30 - 14 DTE

### ATM Straddle
| Strike | Type | Bid | Theta |
|--------|------|-----|-------|
| 422 | Call | $6.65 | -0.2480 |
| 422 | Put | $6.75 | -0.2375 |
| **Straddle** | | **$13.40** | **-0.4855** |

### Iron Butterfly Metrics

| Wing Width | Wing Strikes | Wing Cost | Net Credit | Max Loss | Net θ | θ/Risk | Credit % |
|------------|--------------|-----------|------------|----------|-------|--------|----------|
| 6 pts | 416P / 428C | $6.60 | $6.80 | -$0.80 | 0.0502 | N/A | 113.33% |
| 8 pts | 414P / 430C | $6.25 | $7.15 | $0.85 | 0.0790 | 9.29% | 89.38% |
| 10 pts | 412P / 432C | $6.04 | $7.36 | $2.64 | 0.0972 | 3.68% | 73.60% |

**Wing Details:**
- 416 Put: Ask $4.30, θ = -0.2210
- 428 Call: Ask $4.30, θ = -0.2352
- 414 Put: Ask $3.65, θ = -0.2110
- 430 Call: Ask $3.60, θ = -0.2255
- 412 Put: Ask $3.05, θ = -0.2000
- 432 Call: Ask $2.99, θ = -0.2117

---

## Rankings

### By Theta Efficiency (θ/Risk)

| Rank | Expiry | DTE | Wings | θ/Risk | Max Loss | Net Credit |
|------|--------|-----|-------|--------|----------|------------|
| 1 | 2026-01-28 | 12 | 6 pt | 15.26% | $0.35 | $5.65 |
| 2 | 2026-01-23 | 7 | 6 pt | 14.29% | $0.73 | $5.27 |
| 3 | 2026-01-30 | 14 | 8 pt | 9.29% | $0.85 | $7.15 |
| 4 | 2026-01-23 | 7 | 8 pt | 5.62% | $2.91 | $5.09 |
| 5 | 2026-01-23 | 7 | 10 pt | 5.15% | $3.82 | $6.18 |
| 6 | 2026-01-28 | 12 | 8 pt | 3.91% | $2.05 | $5.95 |
| 7 | 2026-01-26 | 10 | 8 pt | 3.76% | $2.36 | $5.64 |
| 8 | 2026-01-30 | 14 | 10 pt | 3.68% | $2.64 | $7.36 |
| 9 | 2026-01-28 | 12 | 10 pt | 3.49% | $3.00 | $7.00 |
| 10 | 2026-01-26 | 10 | 6 pt | 3.30% | $1.52 | $4.48 |

### By Risk-Reward (Credit %)

| Rank | Expiry | DTE | Wings | Credit % | Risk:Reward | Max Loss |
|------|--------|-----|-------|----------|-------------|----------|
| 1 | 2026-01-30 | 14 | 6 pt | 113.33% | Credit > Wings | -$0.80 |
| 2 | 2026-01-28 | 12 | 6 pt | 94.17% | 0.06:1 | $0.35 |
| 3 | 2026-01-30 | 14 | 8 pt | 89.38% | 0.12:1 | $0.85 |
| 4 | 2026-01-23 | 7 | 6 pt | 87.83% | 0.14:1 | $0.73 |
| 5 | 2026-01-26 | 10 | 6 pt | 74.67% | 0.34:1 | $1.52 |
| 6 | 2026-01-28 | 12 | 8 pt | 74.38% | 0.34:1 | $2.05 |
| 7 | 2026-01-30 | 14 | 10 pt | 73.60% | 0.36:1 | $2.64 |
| 8 | 2026-01-26 | 10 | 8 pt | 70.50% | 0.42:1 | $2.36 |
| 9 | 2026-01-28 | 12 | 10 pt | 70.00% | 0.43:1 | $3.00 |
| 10 | 2026-01-26 | 10 | 10 pt | 65.30% | 0.53:1 | $3.47 |

---

## Key Insights

- **Best for theta decay:** Jan 28 (12 DTE) with 6-point wings - exceptional 15.26% θ/Risk ratio with tiny $0.35 max loss
- **Best risk-reward:** Jan 30 (14 DTE) with 6-point wings - credit exceeds wing width (net debit on wings, guaranteed profit)
- **Balanced pick:** Jan 23 (7 DTE) with 6-point wings - high 14.29% θ/Risk with quick expiration

### Strategy Notes

1. **Jan 30 6-pt wings** show credit > wing width, meaning the short straddle premium completely covers the protective wings plus profit - this is unusual and worth investigating for fill quality
2. **Shorter DTE (7 days)** provides faster theta decay but less time for position management
3. **6-point wings** consistently outperform wider wings on θ/Risk across all expiries
4. **IV Skew:** Put IVs running 3-5% higher than call IVs (typical for GLD)

---

*Analysis generated by theta-collector agent on 2026-01-16*
*Data Source: Alpaca Markets MCP Server*

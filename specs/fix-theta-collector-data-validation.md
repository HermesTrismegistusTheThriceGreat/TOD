# Plan: Fix Theta-Collector θ/Risk Metric Distortion

## Task Description

The theta-collector agent produces accurate formulas for iron butterfly analysis, but the θ/Risk metric becomes unreliable when Max Loss values approach zero. This creates artificially inflated rankings (e.g., 15.26% θ/Risk with only $0.35 max loss) and impossible results (113% Credit implying guaranteed profit). The fix requires adding data validation checks, implementing a more stable alternative metric, and flagging suspicious data quality issues.

## Objective

When this plan is complete, the theta-collector agent will:
1. Detect and flag suspicious Max Loss values (≤ $0.10) that indicate data quality issues
2. Detect and flag impossible Credit percentages (> 95%) that indicate stale quotes or wide spreads
3. Provide an alternative "θ/Credit" metric that doesn't explode with small denominators
4. Include clear warning flags in output when data anomalies are detected
5. Maintain backward compatibility with existing calculation logic

## Problem Statement

### The Division-by-Small-Number Problem

The current θ/Risk formula is:
```
θ/Risk = (Net Theta / Max Loss) × 100
```

When Max Loss approaches zero:
- **Example 1**: Jan 28 / 6pt wings: θ/Risk = 15.26% with Max Loss = $0.35
  - Net Theta was only $0.0534 - LOWER than Jan 23's $0.1043
  - But $0.35 denominator inflated the ratio vs Jan 23's $0.73 max loss

- **Example 2**: Jan 30 / 6pt wings: Credit % = 113.33%
  - Net Credit = $6.80 on 6-point wings
  - This implies Max Loss = -$0.80 (guaranteed profit regardless of outcome)
  - This is mathematically impossible in real markets

### Root Cause

Small denominators amplify any data errors into spectacular-looking but misleading results. Stale quotes, wide bid-ask spreads, or indicative feed data can create scenarios where:
- Wings appear cheaper than they actually are
- Straddles appear more expensive than they actually are
- Combined effect: Max Loss approaches zero or goes negative

## Solution Approach

### 1. Add Validation Layer

Add checks after calculating Max Loss and Credit %:
```python
# Suspicious Max Loss threshold
MIN_VALID_MAX_LOSS = 0.10  # $0.10

# Suspicious Credit % threshold
MAX_VALID_CREDIT_PCT = 95.0  # 95%

# After calculating metrics
if max_loss <= MIN_VALID_MAX_LOSS:
    data_quality_flag = "VERIFY_QUOTES"

if credit_pct > MAX_VALID_CREDIT_PCT:
    data_quality_flag = "CHECK_FILL_QUALITY"
```

### 2. Add Alternative Metric

Introduce θ/Credit that doesn't explode with small denominators:
```python
# Current metric (prone to explosion)
theta_risk_pct = (net_theta / max_loss) * 100

# New stable metric
theta_per_dollar_credit = net_theta / net_credit  # theta collected per dollar of credit received
```

This metric:
- Uses Net Credit as denominator (always positive for valid iron butterflies)
- Represents "how much theta decay per dollar you've committed"
- More intuitive: higher = better theta efficiency per dollar

### 3. Add Warning Flags to Output

Modify the output tables to include warning indicators:
```
| Expiry | Wings | θ/Risk | θ/Credit | Max Loss | Flag |
|--------|-------|--------|----------|----------|------|
| Jan 28 | 6 pt  | 15.26% | 0.94%    | $0.35    | ⚠️ VERIFY |
| Jan 30 | 6 pt  | N/A    | 0.74%    | -$0.80   | ⚠️ DATA ERROR |
```

## Relevant Files

Use these files to complete the task:

- **`.claude/agents/theta-collector.md`** - Main agent prompt file containing calculation logic, formulas, and output format. This is the primary file to modify.
- **`specs/gld-theta-analysis.md`** - Example output showing the problematic metrics (Jan 28 at 15.26% θ/Risk, Jan 30 at 113% Credit). Use as reference for understanding current output format.
- **`specs/gld-theta-analysis-multi-expiry.md`** - Another example output showing similar issues (957% θ/Risk with $0.76 max loss). Reference for edge cases.
- **`app_fix_reports/fix_2026-01-16_theta-collector-wings.md`** - Previous fix report for wing option types. Reference for fix documentation format.

### New Files

- **`app_fix_reports/fix_2026-01-17_theta-collector-validation.md`** - Fix report documenting the validation changes (to be created at completion)

## Implementation Phases

### Phase 1: Foundation

Add validation constants and data quality flag definitions to the agent prompt. Define thresholds for suspicious data detection.

### Phase 2: Core Implementation

Modify the calculation logic to:
1. Add validation checks after Max Loss and Credit % calculations
2. Implement the new θ/Credit metric
3. Add flag assignment logic

### Phase 3: Integration & Polish

Update output format to include:
1. New θ/Credit column in tables
2. Warning flag column
3. Data quality notes section
4. Modified rankings that de-prioritize flagged entries

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Read Current Agent Implementation

- Read the full `.claude/agents/theta-collector.md` file to understand current structure
- Identify the exact location of calculation formulas (around line 109-120)
- Identify the Report section format (around line 160-189)
- Note the rankings tables format (around line 171-179)

### 2. Add Validation Constants and Thresholds

- Add a new `## Data Validation` section after the `## Variables` section
- Define validation constants:
  ```markdown
  ## Data Validation

  ### Thresholds
  - `MIN_VALID_MAX_LOSS`: $0.10 - Max loss below this suggests data quality issues
  - `MAX_VALID_CREDIT_PCT`: 95% - Credit exceeding this percentage of width is suspicious
  - `MIN_VALID_WING_COST`: $0.50 - Wing cost below this suggests stale or indicative quotes

  ### Warning Flags
  - `⚠️ VERIFY QUOTES` - Max loss near zero, verify bid/ask quotes are live
  - `⚠️ DATA ERROR` - Impossible values (negative max loss, credit > width)
  - `⚠️ CHECK SPREADS` - Wing costs suspiciously low, check bid-ask spreads
  ```

### 3. Modify Calculation Logic

- Locate the calculation table in Section 4 (around line 109-120)
- Add new metrics to the calculation table:
  ```markdown
  | Metric | Formula |
  |--------|---------|
  | Straddle Credit | ATM_CALL.bid + ATM_PUT.bid |
  | Wing Cost | lower_put.ask + upper_call.ask |
  | Net Credit | Straddle Credit - Wing Cost |
  | Max Loss | Wing Width - Net Credit |
  | Straddle Theta | |ATM_CALL.theta| + |ATM_PUT.theta| |
  | Net Theta | Straddle Theta - |wing_put.theta| - |wing_call.theta| |
  | Theta/Risk | (Net Theta / Max Loss) × 100 |
  | Credit % | (Net Credit / Wing Width) × 100 |
  | **θ/Credit (NEW)** | **(Net Theta / Net Credit) × 100** |
  | **Data Quality Flag** | **See validation rules below** |
  ```

### 4. Add Validation Rules Section

- Add validation rules after the calculation table:
  ```markdown
  **Data Validation Rules (apply after calculations):**

  1. **Check Max Loss validity:**
     - If Max Loss ≤ $0.10: Set flag = "⚠️ VERIFY QUOTES"
     - If Max Loss ≤ $0: Set flag = "⚠️ DATA ERROR" and θ/Risk = "N/A"

  2. **Check Credit % validity:**
     - If Credit % > 95%: Set flag = "⚠️ CHECK SPREADS"
     - If Credit % > 100%: Set flag = "⚠️ DATA ERROR"

  3. **Check Wing Cost validity:**
     - If Wing Cost < $0.50: Set flag = "⚠️ VERIFY QUOTES"

  4. **Ranking adjustments:**
     - Entries with "⚠️ DATA ERROR" should be excluded from rankings
     - Entries with "⚠️ VERIFY QUOTES" should be shown but de-prioritized with note
  ```

### 5. Update Iron Butterfly Metrics Table Format

- Modify the Iron Butterfly Metrics table in the Report section to include new columns:
  ```markdown
  | Wing Width | Credit | Max Loss | θ/Risk | θ/Credit | Credit % | Flag |
  |------------|--------|----------|--------|----------|----------|------|
  | 6 pts      | $X.XX  | $X.XX    | X.XX%  | X.XX%    | XX.X%    | -    |
  ```

### 6. Update Rankings Tables

- Modify the "By Theta Efficiency" ranking table to include θ/Credit as secondary metric:
  ```markdown
  ### By Theta Efficiency (θ/Risk)

  **Note:** Entries marked with ⚠️ have data quality concerns. Verify quotes before trading.

  | Rank | Expiry | Wings | θ/Risk | θ/Credit | Max Loss | Credit | Flag |
  |------|--------|-------|--------|----------|----------|--------|------|
  ```

- Add new ranking section for θ/Credit:
  ```markdown
  ### By Theta Efficiency (θ/Credit) - Stable Metric

  This ranking uses θ/Credit which doesn't inflate with small max loss values.

  | Rank | Expiry | Wings | θ/Credit | θ/Risk | Net Credit | Flag |
  |------|--------|-------|----------|--------|------------|------|
  ```

### 7. Add Data Quality Notes Section

- Add a new section before Key Insights in the Report template:
  ```markdown
  ---
  ## Data Quality Notes

  {IF ANY FLAGS PRESENT}
  ⚠️ **Data Quality Warnings Detected**

  The following entries have potential data quality issues:

  | Expiry | Wings | Issue | Recommendation |
  |--------|-------|-------|----------------|
  | {DATE} | X pt  | {FLAG} | {ACTION} |

  **Common Causes:**
  - Stale quotes from after-hours or low-volume options
  - Wide bid-ask spreads creating artificial pricing
  - Indicative (non-tradeable) quotes from data feed

  **Recommended Actions:**
  - Verify live quotes during market hours before placing orders
  - Check bid-ask spreads (>$0.10 spread may indicate illiquidity)
  - Consider using mid-price estimates rather than bid/ask extremes
  {END IF}
  ```

### 8. Update Key Insights Section

- Modify the Key Insights template to include data quality awareness:
  ```markdown
  ## Key Insights

  - Best for theta: {recommendation}
    {IF FLAGGED: Note: Verify quotes - Max loss value is unusually low}
  - Best risk-reward: {recommendation}
  - Balanced pick: {recommendation}
  - **Data confidence:** {HIGH|MEDIUM|LOW based on flag count}
  ```

### 9. Create Fix Report Documentation

- Create `app_fix_reports/fix_2026-01-17_theta-collector-validation.md` documenting:
  - Problem description
  - Solution applied
  - Files changed
  - Validation results

### 10. Validate the Changes

- Review the updated agent prompt for consistency
- Verify all markdown tables are properly formatted
- Ensure validation logic is clear and unambiguous
- Test mentally with the problematic examples:
  - Jan 28 / 6pt: Max Loss = $0.35 → Should trigger "⚠️ VERIFY QUOTES"
  - Jan 30 / 6pt: Max Loss = -$0.80 → Should trigger "⚠️ DATA ERROR", θ/Risk = "N/A"

## Testing Strategy

### Manual Validation Tests

1. **Test Case: Normal Data**
   - Max Loss = $2.50, Credit % = 65%
   - Expected: No flags, both θ/Risk and θ/Credit calculated normally

2. **Test Case: Suspicious Max Loss**
   - Max Loss = $0.08, Credit % = 87%
   - Expected: Flag = "⚠️ VERIFY QUOTES", θ/Risk still calculated but flagged

3. **Test Case: Impossible Credit**
   - Max Loss = -$0.80, Credit % = 113%
   - Expected: Flag = "⚠️ DATA ERROR", θ/Risk = "N/A", excluded from rankings

4. **Test Case: Low Wing Cost**
   - Wing Cost = $0.25 (suspiciously cheap)
   - Expected: Flag = "⚠️ VERIFY QUOTES"

### Integration Validation

After modifying the agent, run a test analysis on a ticker and verify:
1. All columns appear in output tables
2. Flags are correctly assigned based on thresholds
3. Rankings properly handle flagged entries
4. Data Quality Notes section appears when flags are present

## Acceptance Criteria

- [ ] Validation constants defined in agent prompt with clear thresholds
- [ ] New θ/Credit metric added to calculation table and output
- [ ] Data validation rules clearly documented in agent prompt
- [ ] Iron Butterfly Metrics table includes Flag column
- [ ] Both ranking tables include θ/Credit and Flag columns
- [ ] New "θ/Credit Ranking" section added for stable metric comparison
- [ ] Data Quality Notes section template added to report format
- [ ] Key Insights template includes data confidence indicator
- [ ] Fix report documentation created
- [ ] Agent prompt maintains valid markdown formatting
- [ ] Example scenarios (Jan 28, Jan 30 from GLD analysis) would be correctly flagged

## Validation Commands

Execute these commands to validate the task is complete:

- `wc -l .claude/agents/theta-collector.md` - Verify file has grown (should be ~230+ lines, up from ~190)
- `grep -c "VERIFY QUOTES" .claude/agents/theta-collector.md` - Should return ≥2 (validation rules + output format)
- `grep -c "θ/Credit" .claude/agents/theta-collector.md` - Should return ≥4 (formula, tables, rankings)
- `grep -c "Data Quality" .claude/agents/theta-collector.md` - Should return ≥2 (section header + notes)
- `cat .claude/agents/theta-collector.md | head -50` - Verify Data Validation section exists near top
- `ls app_fix_reports/fix_2026-01-17_theta-collector-validation.md` - Verify fix report exists

## Notes

### Design Decisions

1. **Keep θ/Risk metric** - Don't remove it entirely, as it's still useful for comparing strategies with similar max loss values. Just add warnings and an alternative.

2. **Use $0.10 threshold** - This is roughly 1.5-2% of a typical wing width. Below this, the max loss is likely a data artifact rather than real market pricing.

3. **95% Credit threshold** - Iron butterflies rarely collect more than 80-85% of wing width in practice. Above 95% strongly suggests data issues.

4. **θ/Credit vs θ/Risk** - The new metric measures "theta decay per dollar of premium received" which is more intuitive for traders thinking about capital efficiency.

### Dependencies

- No new libraries required
- No code changes needed - this is purely a prompt engineering task
- Changes are backward compatible with existing workflow

### Future Considerations

- Could add bid-ask spread validation if that data becomes available
- Could integrate with a quote freshness check if timestamp data is available
- Could add configurable thresholds for different underlying types (ETFs vs individual stocks)

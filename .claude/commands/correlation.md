---
allowed-tools: WebSearch, WebFetch, Read, Write, Glob, Grep, Bash(wc:*)
description: Analyze 10-year exponentially weighted correlations and basis point movements between financial tickers
argument-hint: [tickers (comma-separated, e.g. SPY,GLD,SLV)]
model: opus
---

# Purpose

Perform comprehensive financial correlation analysis between user-specified tickers using exponentially weighted calculations. This prompt analyzes 10 years of historical equity data to determine correlation relationships (inverse, positive, or no correlation), calculate basis point movements across multiple timeframes, and compute drift metrics from OHLC data. Follow the `Instructions` and execute the `Workflow` to generate a detailed analysis report and summary table saved to `ai_docs`.

## Variables

TICKERS: $1
ANALYSIS_PERIOD: 10 years
EWM_SPAN: 252 trading days (1 year) for exponential weighting
OUTPUT_DIRECTORY: ai_docs

## Instructions

- **IMPORTANT: If no `TICKERS` are provided, stop and ask the user to provide a comma-separated list of tickers (e.g., SPY,GLD,SLV)**
- Parse the `TICKERS` variable to extract individual ticker symbols (comma or space separated)
- Use WebSearch to gather historical price data, correlation statistics, and volatility metrics for each ticker
- Focus on **exponentially weighted** correlations which give more weight to recent data points
- Calculate or research basis point movements for daily, weekly, bi-weekly, and monthly timeframes
- Research OHLC (Open, High, Low, Close) drift patterns using exponentially weighted averages
- Classify each correlation pair as: INVERSE (< -0.3), LOW (-0.3 to 0.3), MODERATE (0.3 to 0.6), HIGH (> 0.6)
- Include data source citations with URLs for all statistics
- Document any data limitations and recommend tools/APIs for improved future analysis
- Save the final report to `OUTPUT_DIRECTORY/<ticker1>-<ticker2>-...-correlation-analysis.md`

## Workflow

1. **Parse Tickers** - Extract individual ticker symbols from the `TICKERS` variable
2. **Research Historical Data** - Use WebSearch to find 10-year historical price data and performance metrics for each ticker
3. **Gather Correlation Data** - Search for exponentially weighted correlation coefficients between each ticker pair from financial data sources (PortfoliosLab, Macroaxis, Yahoo Finance, etc.)
4. **Collect Volatility Metrics** - Research annualized volatility, standard deviation, and risk metrics for each ticker
5. **Calculate Basis Point Movements** - Research or derive average basis point movements for:
   - Daily (1 trading day)
   - Weekly (5 trading days)
   - Bi-weekly (10 trading days)
   - Monthly (21 trading days)
6. **Analyze OHLC Drift** - Research exponentially weighted average drift patterns:
   - Open-to-Close drift (intraday direction)
   - High-to-Low drift (daily range)
   - Close-to-Open drift (overnight gap)
7. **Classify Relationships** - Categorize each correlation pair as inverse, positive, or no correlation
8. **Identify Data Gaps** - Document missing data and limitations encountered during research
9. **Recommend Improvements** - Suggest tools, APIs, and data sources for enhanced future analysis
10. **Generate Report** - Create comprehensive markdown report following the `Report Format`
11. **Save Output** - Write report to `OUTPUT_DIRECTORY/<tickers-joined>-correlation-analysis.md`

## Report Format

```md
# <TICKER1>, <TICKER2>, ... Exponentially Weighted Correlation Analysis

## 10-Year Historical Analysis

**Report Date:** <current date>
**Analysis Period:** <10 years ending current date>
**Assets Analyzed:** <list each ticker with full name>
**Methodology:** Exponentially Weighted Moving Average (EWM) with span of 1252 trading days

---

## Executive Summary

<3-5 key findings about the correlation relationships, volatility differences, and portfolio implications>

### Key Findings at a Glance

| Metric | <TICKER1> | <TICKER2> | ... |
|--------|-----------|-----------|-----|
| 10-Year Annualized Return | | | |
| EWM Volatility | | | |
| Maximum Drawdown | | | |
| Sharpe Ratio | | | |

---

## Data Sources & Methodology

### Primary Data Sources
<table of sources with URLs>

### Exponentially Weighted Methodology
- EWM gives more weight to recent observations, with decay factor based on span
- Formula: EWM_t = alpha * X_t + (1 - alpha) * EWM_{t-1}, where alpha = 2 / (span + 1)
- Advantages over simple correlation: More responsive to recent market regimes

---

## Exponentially Weighted Correlation Analysis

### Correlation Matrix (EWM)

|        | <TICKER1> | <TICKER2> | ... |
|--------|-----------|-----------|-----|
| <TICKER1> | 1.00 | | |
| <TICKER2> | | 1.00 | |

### Correlation Interpretation

<For each ticker pair, provide:>
#### <TICKER1> vs <TICKER2> (EWM Correlation: X.XX) - <INVERSE/LOW/MODERATE/HIGH>
- **Relationship**: <description of correlation type>
- **Diversification Value**: <Excellent/Good/Limited/None>
- **Historical Context**: <how correlation has changed over time>

---

## Basis Point Movement Analysis (EWM)

### Understanding Basis Points
- 1 basis point (bp) = 0.01% price change
- 100 basis points = 1.00% price change

### Average Basis Point Movements by Timeframe

#### Daily Movements (EWM)
| Asset | Avg Daily Move (bps) | Daily Std Dev (bps) | Up Days % |
|-------|---------------------|--------------------:|----------:|

#### Weekly Movements (EWM)
| Asset | Avg Weekly Move (bps) | Weekly Std Dev (bps) |
|-------|----------------------|---------------------:|

#### Bi-Weekly Movements (EWM)
| Asset | Avg Bi-Weekly Move (bps) | Bi-Weekly Std Dev (bps) |
|-------|-------------------------|------------------------:|

#### Monthly Movements (EWM)
| Asset | Avg Monthly Move (bps) | Monthly Std Dev (bps) |
|-------|------------------------|----------------------:|

---

## OHLC Drift Analysis (EWM)

### Exponentially Weighted Drift Metrics

| Asset | Open-to-Close Drift (bps) | High-to-Low Range (bps) | Close-to-Open Gap (bps) |
|-------|--------------------------|------------------------|------------------------|

### Drift Interpretation
<explain what the drift patterns indicate about each asset's trading behavior>

---

## Risk-Adjusted Performance

### Sharpe Ratios (EWM)
| Asset | EWM Sharpe Ratio | Long-Term Sharpe |
|-------|------------------|------------------|

### Maximum Drawdown Analysis
| Asset | Max Drawdown | Date | Recovery Time |
|-------|-------------|------|---------------|

---

## Key Investment Insights

<numbered list of actionable insights based on the analysis>

---

## Limitations & Data Gaps

### Limitations of This Analysis
<numbered list of limitations>

### Missing Data Points
| Data Needed | Impact on Analysis |
|-------------|-------------------|

---

## Recommendations for Future Analysis

### Data Source Improvements
| Tool/Source | Purpose | Access Method |
|-------------|---------|---------------|
| Bloomberg Terminal | Professional-grade tick data | Subscription |
| yfinance | Free historical OHLCV data | Python library |
| Alpha Vantage | Free API for historical data | API key |
| Polygon.io | Real-time and historical data | API subscription |

### Recommended Python Implementation
<code block showing how to calculate EWM correlations and basis points>

---

## Appendix: Data Source References

<numbered list of all sources with URLs>

---

*Report generated: <date>*
*Analysis by: Claude AI Quantitative Analysis Agent*
*Methodology: Exponentially Weighted Moving Average (EWM)*
```

## Report

After completing the analysis and saving the report, provide a summary:

```
Exponentially Weighted Correlation Analysis Complete

Report saved to: ai_docs/<tickers>-correlation-analysis.md

Tickers Analyzed: <list of tickers>
Analysis Period: 10 years

Key Correlations (EWM):
- <TICKER1> vs <TICKER2>: X.XX (<CLASSIFICATION>)
- <TICKER2> vs <TICKER3>: X.XX (<CLASSIFICATION>)
...

Basis Point Summary (Daily EWM):
- <TICKER1>: +/- X bps avg, Y bps std dev
- <TICKER2>: +/- X bps avg, Y bps std dev
...

OHLC Drift Highlights:
- <key insight about drift patterns>

Data Gaps Identified: <count>
Recommendations: <count> tools/sources suggested for improvement
```

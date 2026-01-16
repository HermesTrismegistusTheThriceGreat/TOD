# Trade Stats Validation - Running the Tests

## Option 1: Run the Python Script (Recommended)

This will automatically navigate, screenshot, and analyze the Trade Stats page.

### Prerequisites
Make sure you have the application running at http://localhost:5175

### Step 1: Install Playwright (if not already installed)
```bash
cd /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend
pip install playwright
```

### Step 2: Run the Validation Script
```bash
python /Users/muzz/Desktop/tac/TOD/app_review/validate_trade_stats.py
```

This will:
1. Navigate to http://localhost:5175
2. Find and click the Trade Stats navigation
3. Capture screenshots at each step
4. Analyze the page structure
5. Generate a detailed report
6. Save the final screenshot to `/Users/muzz/Desktop/tac/TOD/app_review/trade-stats-screenshot-2026-01-15.png`

### Step 3: Review Results
The script will create a directory with:
- `validation-report.md` - Detailed validation report
- `01-initial-page.png` - Initial app load
- `02-navigation-to-trade-stats.png` - After clicking Trade Stats
- `03-trade-stats-loaded.png` - Page loading
- `04-final-trade-stats-view.png` - Final state with all content loaded

## Option 2: Manual Validation (Browser)

If you prefer to validate manually:

1. Open http://localhost:5175 in your browser
2. Look for a navigation element to switch to "Trade Stats" view
3. Click it to navigate to Trade Stats
4. Once loaded, take a screenshot and save it
5. Compare the layout with the "What to Verify" section below

## What to Verify in the Screenshot

### Expected NEW Layout (Success)
The page should show:
- Card-based layout with multiple trade cards
- Each card displays:
  - Trade ID and ticker (e.g., "SPY Iron Condor")
  - Strategy tags (e.g., "Iron Condor", colored badges)
  - A table inside each card showing:
    - Column headers: Open Action, Open Fill, Close Action, Close Fill, P&L
    - One row per leg of the trade
    - Specific fill prices and P&L values
  - Summary footer showing:
    - Total Credit, Total Debit, Net P&L

### Example Card Structure
```
┌─────────────────────────────────────┐
│ SPY Iron Condor (Trade #12345)      │
│ [Iron Condor] [2026-01-15]         │
├─────────────────────────────────────┤
│ Open    │ Open │ Close   │ Close │ │
│ Action  │ Fill │ Action  │ Fill  │P&L
├─────────────────────────────────────┤
│ BUY     │ 100  │ SELL    │ 95    │ $50
│ SELL    │ 105  │ BUY     │ 110   │ -$25
│ SELL    │ 110  │ BUY     │ 108   │ $40
│ BUY     │ 95   │ SELL    │ 100   │ -$30
├─────────────────────────────────────┤
│ Credit: $215  Debit: $205  P&L: $10 │
└─────────────────────────────────────┘
```

### OLD Layout (Failure - Do NOT Want)
If the page still shows this, the fix didn't work:
```
TICKER | STRATEGY      | DIR | ENTRY DATE | EXIT DATE  | P&L
SPY    | Iron Condor   | NET | 2026-01-10 | 2026-01-15 | $10
XYZ    | Call Spread   | NET | 2026-01-08 | 2026-01-14 | $25
```

## Troubleshooting

### Script Won't Run
- Ensure Python 3.7+ is installed
- Check that playwright is installed: `pip install playwright`
- Verify the application is running at http://localhost:5175

### Application Not Loading
- Check that your app is running: `npm run dev` or `pnpm run dev` in the frontend directory
- Verify http://localhost:5175 loads in your browser
- Check for any console errors (F12 -> Console tab)

### Screenshots Are Blank
- The application may not be fully loaded
- Check if there are errors in the browser console
- Try increasing the timeout in the script (change `wait_until="networkidle"` parameters)

### Can't Find Trade Stats Navigation
- The app may already be on the Trade Stats view
- Look at the URL or page title to confirm the current view
- The navigation might be in a different location than expected

## Files Generated

After running the validation, you'll have:

```
/Users/muzz/Desktop/tac/TOD/app_review/
├── validate_trade_stats.py              (validation script)
├── trade-stats-validation-plan.md       (this plan)
├── trade-stats-screenshot-2026-01-15.png (final screenshot - requested location)
└── validation_YYYY-MM-DD_HH-MM-SS/      (detailed results)
    ├── validation-report.md
    ├── 01-initial-page.png
    ├── 02-navigation-to-trade-stats.png
    ├── 03-trade-stats-loaded.png
    └── 04-final-trade-stats-view.png
```

## Interpreting Results

### SUCCESS
- Script reports "PASS - New card-based leg-level display is visible"
- Screenshots show card-based layout with leg details
- Each trade has its own card with structured leg information

### FAILURE
- Script reports "FAIL - Old simple table format still visible"
- Screenshots show simple table rows without card structure
- No leg-level details visible

## Next Steps

After validation, report the findings:
- Share the screenshot at `/Users/muzz/Desktop/tac/TOD/app_review/trade-stats-screenshot-2026-01-15.png`
- Review the validation report in the timestamped directory
- If FAIL: Check the implementation for issues
- If PASS: Confirm the feature is working as expected

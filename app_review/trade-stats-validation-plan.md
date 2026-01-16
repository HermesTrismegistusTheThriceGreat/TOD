# Trade Stats Leg-Level Display Validation Plan
**Date:** 2026-01-15
**Target URL:** http://localhost:5175
**Expected Screenshot Location:** `/Users/muzz/Desktop/tac/TOD/app_review/trade-stats-screenshot-2026-01-15.png`

## Validation Objective
Verify that the Trade Stats page is displaying the new leg-level display with card-based layout instead of the old simple table format.

## Steps to Execute

### Step 1: Navigate to Application
- Open browser to http://localhost:5175
- Wait for the Orchestrator 3 Stream interface to load completely
- Screenshot: `01-initial-page.png`

### Step 2: Locate and Navigate to Trade Stats View
- Look for navigation element to switch to "Trade Stats" view (view mode 'trade-stats')
- This could be in:
  - Header navigation
  - Sidebar menu
  - Tab navigation
- Click to activate Trade Stats view
- Screenshot: `02-navigation-to-trade-stats.png`

### Step 3: Wait for Trade Stats Page to Load
- Wait for page content to fully render (reasonable timeout: 5-10 seconds)
- Screenshot: `03-trade-stats-loaded.png`

### Step 4: Capture Final Trade Stats View
- Take final screenshot showing the complete Trade Stats page
- Save to: `/Users/muzz/Desktop/tac/TOD/app_review/trade-stats-screenshot-2026-01-15.png`
- Screenshot: `04-final-trade-stats-view.png`

## Verification Checklist

### NEW Layout (Expected - Card-Based Display)
- [ ] Cards visible for each trade
- [ ] Each card shows:
  - [ ] Trade ID and ticker
  - [ ] Strategy tags (e.g., "Iron Condor", "Call Spread")
  - [ ] Leg details table with columns:
    - [ ] Open Action
    - [ ] Open Fill
    - [ ] Close Action
    - [ ] Close Fill
    - [ ] P&L
  - [ ] Summary footer showing:
    - [ ] Total Credit
    - [ ] Total Debit
    - [ ] Net P&L

### OLD Layout (Undesired - Simple Table Format)
- [ ] Simple rows with only: TICKER, STRATEGY, DIR, ENTRY DATE, EXIT DATE, P&L
- **If this format is visible, the fix did NOT work**

## Expected Outcome
SUCCESS: Card-based layout with leg-level details is visible
FAILURE: Old table format is still showing OR page doesn't load

## Notes
- Check browser console for any errors
- Verify page loads without 404 or connection errors
- Note any missing data or rendering issues

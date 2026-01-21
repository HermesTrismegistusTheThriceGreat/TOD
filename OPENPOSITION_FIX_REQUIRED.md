# OpenPositionCard Fix Required - 4 Legs Not Visible

## Executive Summary

**Status:** VALIDATION FAILURE
**Issue:** Only 2 out of 4 legs visible in multi-leg option positions
**Root Cause:** OpenPositionCard component has `overflow: hidden` preventing internal table scrolling
**Impact:** Users cannot see complete position data (breaks 4-leg strategies: iron condors, etc.)
**Fix Difficulty:** Easy (2 CSS rules to add/modify)
**Estimated Time:** 5 minutes

## What's Broken

The OpenPositionCard component truncates positions with more than 2 legs:

```
Position: GLD Jan 21, 2026 (4 LEGS POSITION)
├── Leg 1: Short Call $422.00        ✓ VISIBLE
├── Leg 2: Long Call $428.00         ✓ VISIBLE
├── Leg 3: Short Put $422.00         ✗ PARTIALLY CUT OFF
└── Leg 4: Long Put $416.00          ✗ COMPLETELY HIDDEN
```

## Evidence

Screenshot: `/Users/muzz/Desktop/tac/TOD/.playwright-mcp/openposition-card-gld-4legs.png`

Shows white/blank space where legs 3 and 4 should be.

## Root Cause

File: `apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue`

The `.legs-table` CSS rule has `overflow: hidden` which clips content:

```css
/* Line 714-728: CURRENT (BROKEN) */
.legs-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent; /* Cleaner look */
  --el-table-header-bg-color: rgba(255, 255, 255, 0.02);
  --el-table-border-color: var(--border);
  --el-table-text-color: var(--text);
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.04);

  border-radius: 8px;
  overflow: hidden;  /* <-- THIS IS THE PROBLEM */
  border: 1px solid var(--border);
  contain: layout;
}
```

When the table has 4 rows, they don't all fit in the visible space, and `overflow: hidden` clips the overflow instead of allowing scroll.

## The Fix

### Step 1: Update .legs-table CSS (Lines 714-728)

Change from:
```css
.legs-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.02);
  --el-table-border-color: var(--border);
  --el-table-text-color: var(--text);
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.04);

  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);

  /* Performance: CSS containment for table layout */
  contain: layout;
}
```

To:
```css
.legs-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.02);
  --el-table-border-color: var(--border);
  --el-table-text-color: var(--text);
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.04);

  border-radius: 8px;
  overflow: auto;                    /* CHANGED: allow scrolling */
  max-height: 400px;                 /* ADDED: limit height */
  border: 1px solid var(--border);

  /* Performance: CSS containment for table layout */
  contain: layout;
}
```

### Step 2: Add new rule for table body scrolling (after line 733)

Add this new CSS rule after the existing `.legs-table :deep(.el-table__inner-wrapper::before)` rule:

```css
/* NEW: Enable scrolling for table body when content exceeds height */
.legs-table :deep(.el-table__body-wrapper) {
  overflow-y: auto !important;
  max-height: 380px; /* Slightly less than container */
}
```

## Complete Fixed CSS Block

Here's the complete section with changes (lines 714-735):

```css
.legs-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.02);
  --el-table-border-color: var(--border);
  --el-table-text-color: var(--text);
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.04);

  border-radius: 8px;
  overflow: auto;              /* ← CHANGED from: overflow: hidden; */
  max-height: 400px;           /* ← ADDED */
  border: 1px solid var(--border);

  /* Performance: CSS containment for table layout */
  contain: layout;
}

/* Remove bottom border of the last row for cleaner look */
.legs-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

/* NEW: Enable scrolling for table body when content exceeds height */
.legs-table :deep(.el-table__body-wrapper) {
  overflow-y: auto !important;
  max-height: 380px;
}
```

## How to Apply

### Option 1: Manual Edit
1. Open: `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue`
2. Find line 714 (`.legs-table {`)
3. Change `overflow: hidden;` to `overflow: auto;`
4. Add `max-height: 400px;` after `overflow: auto;`
5. After line 733, add the `.legs-table :deep(.el-table__body-wrapper)` rule
6. Save and test

### Option 2: Using sed (one-liner)

```bash
# Change overflow: hidden to overflow: auto and add max-height
sed -i '723s/overflow: hidden;/overflow: auto;\n  max-height: 400px;/' \
  /Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue
```

## Expected Result After Fix

✅ All 4 legs will be visible in the table
✅ Table will scroll if content exceeds 400px
✅ Scrollbar will appear on the right side of the table
✅ Header stays fixed while body scrolls
✅ Maintains all styling and functionality

## Testing

After applying the fix:

1. Navigate to http://localhost:5175
2. Find any "4 LEGS POSITION" card
3. Verify all 4 legs are visible (may need to scroll if > 400px)
4. Click on legs to verify "Close Leg" button works
5. Test scrolling works smoothly

## Files Involved

- **Primary:** `apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue` (lines 714-735)
- **Secondary:** (Already correctly configured)
  - `apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue` (has `.positions-grid { overflow-y: auto }`)
  - `apps/orchestrator_3_stream/frontend/src/App.vue` (has `.app-content { overflow: auto }`)

## Notes

- This fix only enables scrolling within the card
- Position cards themselves will still scroll within the OpenPositions container
- The fix maintains all original styling and performance optimizations
- CSS containment (`contain: layout`) is preserved
- No JavaScript changes needed

## Validation Command

After applying the fix, run this validation:

```bash
claude --mcp-config .mcp.json.playwright --model haiku --dangerously-skip-permissions \
  -p "Navigate to http://localhost:5175, find a 4-leg position, take screenshot of the complete table showing all 4 legs with scroll bar if needed. Report: visible legs count (should be 4)."
```

---

**Status:** Ready to implement
**Priority:** High - Blocks viewing complete position data
**Blocker:** No
**Dependencies:** None

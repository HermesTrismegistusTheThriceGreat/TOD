# OpenPositionCard Multi-Leg Validation Report

**Date:** January 20, 2026
**Status:** FAILURE - Partial Fix Only
**Test URL:** http://localhost:5175
**Viewport:** 1920x1080

## Test Scenario

Validate that the OpenPositionCard component displays all 4 legs of multi-leg positions without visual cutoff. The fix applied involved:
1. Changing `.app-content { overflow: auto; }` in App.vue
2. Changing `.open-positions { overflow-y: auto; }` in OpenPositions.vue
3. Adding `.positions-grid { min-height: 0; overflow-y: auto; }` in OpenPositions.vue

## Results

### What Works:
✅ Page loads successfully at http://localhost:5175
✅ OpenPositions component displays position cards
✅ Multiple 4-leg positions are rendered (GLD Jan 21 and GLD Jan 23)
✅ "4 LEGS POSITION" badge correctly displays
✅ Position card header, P/L circle, and DTE box all render properly
✅ First 2 legs are fully visible in the table

### What Doesn't Work:
❌ **Only 2 legs are fully visible in the card**
❌ **3rd leg is partially cut off**
❌ **4th leg is completely hidden**
❌ The position card table doesn't scroll vertically
❌ Text is overlapping/blending with white bars at the table edge (see screenshot)

## Screenshots

**Evidence of Issue:** `/Users/muzz/Desktop/tac/TOD/.playwright-mcp/openposition-card-gld-4legs.png`

The screenshot clearly shows:
1. **GLD (Jan 21, 2026)** position card with "4 LEGS POSITION" badge
2. **Row 1:** Short Call $422.00 - FULLY VISIBLE ✓
3. **Row 2:** Long Call $428.00 - FULLY VISIBLE ✓
4. **Row 3:** (Short Put) - PARTIALLY VISIBLE, bottom is cut off
5. **Row 4:** (Long Put) - COMPLETELY HIDDEN

## Root Cause Analysis

The CSS fixes applied work for scroll ability at the parent container level (`.open-positions` and `.positions-grid`), but the **OpenPositionCard itself doesn't allow its table to scroll independently**.

### Current CSS Issues in OpenPositionCard.vue:

```css
.position-card {
  overflow: hidden;    /* Line 480 - Prevents card scrolling */
  height: fit-content; /* Line 481 - Expands with content */
}

.legs-table {
  overflow: hidden;    /* Line 723 - Prevents table scrolling */
  border-radius: 8px;
}

.legs-content {
  flex-grow: 1;
  min-width: 0;
  /* NO max-height constraint - unbounded */
}
```

### The Problem:

1. `.position-card` with `overflow: hidden` clips content that exceeds its boundaries
2. `.legs-table` with `overflow: hidden` prevents the table from scrolling
3. The parent flex layout expands the table, but since both card and table have `overflow: hidden`, rows beyond visible space get clipped
4. When 4 legs are rendered, only ~2 fit in the visible space before being cut off

## Recommendations for Fix

### Recommended Solution: Add internal scrolling to legs table

Modify `.legs-table` in `OpenPositionCard.vue` (line 714-728):

```css
.legs-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.02);
  --el-table-border-color: var(--border);
  --el-table-text-color: var(--text);
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.04);

  border-radius: 8px;
  border: 1px solid var(--border);
  
  /* CHANGE: Allow table body wrapper to scroll */
  overflow: auto;  /* Changed from: overflow: hidden; */
  
  /* CHANGE: Add max-height to enable scrolling */
  max-height: 400px; /* Limit table height */
  
  /* Performance: CSS containment for table layout */
  contain: layout;
}

/* CHANGE: Add this rule to make table body scrollable */
.legs-table :deep(.el-table__body-wrapper) {
  overflow-y: auto !important;
  max-height: 380px; /* Slightly less than container */
}
```

### Alternative: Constrain card height

If scrolling inside card is undesirable, consider:
1. Limiting the position card height and scrolling between cards
2. Implementing an expandable/collapsible leg list
3. Using an "View All Legs" button that opens a modal

## Affected Files

- `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue`
  - `.position-card` CSS: line 459-485
  - `.legs-table` CSS: line 714-728
  
- `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue`
  - Already correctly configured with scroll support
  
- `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/App.vue`
  - Already correctly configured with scroll support

## Screenshots Captured

1. `/Users/muzz/Desktop/tac/TOD/.playwright-mcp/openposition-card-gld-4legs.png` - Zoomed view showing truncation
2. `/Users/muzz/Desktop/tac/TOD/.playwright-mcp/openposition-card-full.png` - Full page view
3. `/Users/muzz/Desktop/tac/TOD/.playwright-mcp/openposition-card-first-position.png` - Initial load state

## Conclusion

**The current fix is incomplete.** While the parent containers now support scrolling through multiple position cards, **individual cards with 4-leg positions do not display all legs due to overflow:hidden on both the card and table elements.**

Visible Legs: **2 out of 4** (50% complete)
- Leg 1 (Short Call $422.00) - ✓ Visible
- Leg 2 (Long Call $428.00) - ✓ Visible  
- Leg 3 (Short Put $422.00) - ✗ Partially cut off
- Leg 4 (Long Put $416.00) - ✗ Hidden

**Status: NEEDS ADDITIONAL FIX**

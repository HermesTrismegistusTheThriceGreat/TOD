# Plan: Fix OpenPositionCard Desktop Cutoff

## Task Description
Fix the OpenPositionCard component that is being cut off on desktop, preventing users from seeing all 4 legs of an options position. Currently only 2 of 4 legs are visible because the card content is being clipped by parent container constraints. The fix must maintain mobile responsiveness.

## Objective
Ensure the OpenPositionCard displays all option legs on desktop while preserving existing mobile optimization. Users should see the complete position data including all 4 legs of an iron condor or similar multi-leg strategy.

## Problem Statement
On desktop viewports, the OpenPositionCard component is being cut off, showing only 2 of 4 position legs. The issue stems from:
1. Parent container `.open-positions` has `height: 100%; overflow: hidden;` (OpenPositions.vue:79-85)
2. The card uses `height: fit-content` but parent constraints prevent natural expansion
3. The `.positions-grid` container has `flex: 1; overflow-y: auto;` which should scroll, but the parent's `overflow: hidden` clips content prematurely

## Solution Approach
Modify the CSS hierarchy to allow cards to display their full content on desktop:
1. Change `.open-positions` container to allow overflow on desktop (keep mobile behavior)
2. Ensure `.positions-grid` can properly scroll to show all card content
3. Add a desktop-specific media query to relax height constraints above 768px
4. Keep existing mobile responsive behavior intact (< 768px already has `overflow: visible !important`)

## Relevant Files
Use these files to complete the task:

- `apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue` - Parent container with overflow constraints causing cutoff (lines 79-85, 146-154, 174-185)
- `apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue` - The card component itself; may need minor adjustments (lines 459-485, 714-728)
- `apps/orchestrator_3_stream/frontend/src/App.vue` - Top-level layout with grid and overflow settings (lines 166-204, 200-204)
- `apps/orchestrator_3_stream/frontend/src/styles/global.css` - Global styles with responsive breakpoints (lines 70-75, 605-720)

## Implementation Phases

### Phase 1: Foundation
Analyze and understand the current overflow hierarchy:
- App.vue: `.app-content` has `height: 100%; overflow: hidden;`
- OpenPositions.vue: `.open-positions` has `height: 100%; overflow: hidden;`
- OpenPositions.vue: `.positions-grid` has `flex: 1; overflow-y: auto;`

### Phase 2: Core Implementation
Modify CSS to allow proper card expansion on desktop:
1. In OpenPositions.vue, change `.open-positions` to use `overflow-y: auto` instead of `overflow: hidden` on desktop
2. Ensure `.positions-grid` maintains proper scrolling behavior
3. Consider removing unnecessary height constraints that prevent card expansion

### Phase 3: Integration & Polish
Test across viewport sizes and ensure mobile behavior is preserved.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Update OpenPositions.vue Container Styles
- Change `.open-positions` from `overflow: hidden` to `overflow-y: auto` for desktop
- This allows the container to scroll when cards exceed viewport height
- The existing mobile media query at `@media (max-width: 768px)` already handles mobile with `overflow: visible !important`

**File:** `apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue`
**Lines:** 79-85

**Current:**
```css
.open-positions {
  height: 100%;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
```

**Change to:**
```css
.open-positions {
  height: 100%;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  overflow-x: hidden;
}
```

### 2. Update Positions Grid to Remove Height Restriction
- The `.positions-grid` already has `overflow-y: auto` which is correct
- Ensure the grid can expand to fit content without being clipped
- Add `min-height: 0` to allow flex children to shrink properly in nested flex containers

**File:** `apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue`
**Lines:** 146-154

**Current:**
```css
.positions-grid {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}
```

**Change to:**
```css
.positions-grid {
  flex: 1;
  min-height: 0; /* Critical: allows flex child to shrink below content size */
  overflow-y: auto;
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}
```

### 3. Add Desktop Media Query for Explicit Overflow Handling
- Add a media query for desktop (min-width: 769px) to ensure proper scrolling behavior
- This provides explicit control over desktop behavior separate from mobile

**File:** `apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue`
**After line 185 (after the existing mobile media query)**

**Add:**
```css
/* Desktop: Ensure proper scrolling and card visibility */
@media (min-width: 769px) {
  .open-positions {
    overflow-y: auto;
    overflow-x: hidden;
  }

  .positions-grid {
    min-height: min-content; /* Ensure grid is at least as tall as its content */
  }
}
```

### 4. Verify OpenPositionCard Has Proper Height Settings
- The card already has `height: fit-content` which is correct
- Verify the table inside isn't being clipped by its own overflow settings
- The `.legs-table` has `overflow: hidden` and `contain: layout` - these are for performance and shouldn't cause vertical clipping since the table auto-sizes to content

**File:** `apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue`
**Lines:** 714-728 - No changes needed, but verify this doesn't need adjustment after testing

The Element Plus `<el-table>` component auto-sizes based on `:data` rows, so all rows should render. The issue is the parent container clipping, not the table itself.

### 5. Validate the Changes
- Start the frontend development server
- Navigate to Open Positions page
- Verify that all 4 legs are visible on desktop
- Verify mobile responsive behavior still works (< 768px)
- Test with multiple position cards to ensure scrolling works

## Testing Strategy
1. **Visual Testing**: Use Playwright or manual browser testing to verify:
   - All 4 legs visible on desktop viewport (1200px+)
   - Card scrolls properly when multiple positions exist
   - Mobile view (< 768px) still stacks properly with `overflow: visible`

2. **Viewport Testing**: Test at key breakpoints:
   - 1920px (large desktop)
   - 1200px (standard desktop)
   - 900px (OpenPositionCard breakpoint - sidebar hides)
   - 768px (mobile breakpoint)
   - 375px (mobile phone)

3. **Content Testing**: Test with different position types:
   - 4-leg iron condor (current failing case)
   - 2-leg vertical spread
   - Single leg position

## Acceptance Criteria
- [ ] All 4 legs of a position are visible on desktop without scrolling within the card
- [ ] The positions container scrolls when multiple position cards exceed viewport height
- [ ] Mobile responsive behavior is preserved (cards stack vertically, overflow visible)
- [ ] No horizontal overflow or layout shift on any viewport size
- [ ] Element Plus table renders all rows without internal clipping
- [ ] Existing mobile media query behavior at 768px is unchanged

## Validation Commands
Execute these commands to validate the task is complete:

- `cd apps/orchestrator_3_stream/frontend && npm run build` - Ensure CSS compiles without errors
- `cd apps/orchestrator_3_stream/frontend && npm run type-check` - Verify no TypeScript errors
- `cd apps/orchestrator_3_stream/frontend && npm run dev` - Start dev server for visual testing
- Use Playwright MCP or browser DevTools to test at different viewport sizes

## Notes
- The fix focuses on CSS changes only - no JavaScript/TypeScript modifications needed
- The Element Plus `<el-table>` component handles row rendering automatically based on data
- CSS containment (`contain: layout`) on the card is a performance optimization and should be preserved
- The `min-height: 0` trick is essential for nested flexbox layouts where children need to shrink below their content minimum
- Consider future enhancement: Adding a "Show All / Collapse" feature for positions with many legs (6+ legs)

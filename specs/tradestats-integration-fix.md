# Plan: TradeStats Integration Fix

## Problem
The Trade Stats page is NOT rendering the new leg-level display components because `App.vue` was never updated to use `TradeStatsGrid.vue`.

## Root Cause
The original implementation created all new components but forgot to update the main App.vue to actually USE them. App.vue still imports and renders the old `TradeStats.vue` component.

## Fix Required

### File: `/apps/orchestrator_3_stream/frontend/src/App.vue`

#### Change 1: Update Import (around line 73)
```diff
- import TradeStats from './components/TradeStats.vue'
+ import TradeStatsGrid from './components/TradeStatsGrid.vue'
```

#### Change 2: Update Template (around lines 42-45)
```diff
- <TradeStats
+ <TradeStatsGrid
    v-else-if="store.viewMode === 'trade-stats'"
    class="app-content center"
  />
```

## Verification
1. Run `npm run build` to verify no TypeScript errors
2. Start frontend and navigate to Trade Stats view
3. Verify card-based display with leg details appears

## Status
- Created: 2026-01-15
- Phase: Ready for build agent implementation

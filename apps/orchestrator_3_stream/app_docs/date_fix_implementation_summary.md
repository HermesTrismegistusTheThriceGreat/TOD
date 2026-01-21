# Date Display Bug Fix - Implementation Summary

## Overview
Fixed the timezone offset bug where expiration dates displayed one day behind (e.g., GLD260121... showing "Jan 20, 2026" instead of "Jan 21, 2026").

## Root Cause
When JavaScript's `new Date()` parses an ISO date string like `"2026-01-21"`, it interprets it as UTC midnight. When displayed using `toLocaleDateString()` in US timezones (which are behind UTC), the date shifts backwards by one day.

## Solution
Created a centralized date utility module that parses ISO date strings as local dates instead of UTC, preventing timezone-related date shifts.

## Files Created

### 1. `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/utils/dateUtils.ts`
New utility module with three functions:

- **`parseLocalDate(dateStr: string): Date`**
  - Parses YYYY-MM-DD as a local date (not UTC)
  - Prevents timezone offset issues
  - Example: `parseLocalDate("2026-01-21")` → Jan 21, 2026 in local time

- **`formatDateString(dateStr: string, options?: Intl.DateTimeFormatOptions): string`**
  - Formats YYYY-MM-DD date strings for display
  - Uses local timezone interpretation
  - Default format: "Jan 21, 2026"
  - Handles empty strings gracefully

- **`daysUntil(dateStr: string): number`**
  - Calculates days between a date and today
  - Uses local timezone for both dates
  - Returns positive for future dates, negative for past

### 2. `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/utils/dateUtils.test.ts`
Comprehensive test suite with 9 tests covering:
- Local date parsing without timezone shift
- Date formatting with custom options
- Days until calculation for future/past dates
- Edge cases (empty strings, GLD symbol dates)

## Files Modified

### 1. `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/components/OpenPositionCard.vue`
**Changes:**
- Added import: `import { formatDateString, daysUntil } from "../utils/dateUtils"`
- Updated `formatDate()` function to use `formatDateString()`
- Simplified `daysToExpiry` computed property to use `daysUntil()`

**Before:**
```typescript
const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const daysToExpiry = computed(() => {
  if (!position.value) return 0;
  const expiry = new Date(position.value.expiryDate);
  const today = new Date();
  return Math.max(
    0,
    Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)),
  );
});
```

**After:**
```typescript
const formatDate = (dateStr: string) => {
  return formatDateString(dateStr, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const daysToExpiry = computed(() => {
  if (!position.value) return 0;
  return Math.max(0, daysUntil(position.value.expiryDate));
});
```

### 2. `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/components/TradeStatsCard.vue`
**Changes:**
- Added import: `import { formatDateString } from '@/utils/dateUtils'`
- Updated `formatDate()` function to use `formatDateString()`

**Before:**
```typescript
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric'
  })
}
```

**After:**
```typescript
const formatDate = (dateStr: string) => {
  return formatDateString(dateStr, {
    month: 'short',
    day: 'numeric'
  })
}
```

### 3. `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/frontend/src/components/TradeStats.vue`
**Changes:**
- Added import: `import { formatDateString } from '@/utils/dateUtils'`
- Updated inline date formatting in table columns (lines 101 and 107)

**Before:**
```vue
<template #default="{ row }">
  {{ row.entry_date ? new Date(row.entry_date).toLocaleDateString() : '—' }}
</template>
```

**After:**
```vue
<template #default="{ row }">
  {{ row.entry_date ? formatDateString(row.entry_date) : '—' }}
</template>
```

## Verification

### Build Verification
```bash
npm run build
# ✓ built successfully with no errors
```

### Test Results
```bash
npm run test:run -- src/utils/dateUtils.test.ts
# ✓ 9 tests passed
```

All tests pass, confirming:
- Dates parse correctly as local time
- No timezone shifting occurs
- GLD260121... displays as "Jan 21, 2026" (not "Jan 20")
- Days until calculation is accurate

## Impact

### Before Fix
- "2026-01-21" → displayed as "Jan 20, 2026" in US timezones ❌
- Days to expiry could be off by 1 day ❌
- Inconsistent date display across components ❌

### After Fix
- "2026-01-21" → displays as "Jan 21, 2026" consistently ✅
- Days to expiry calculates accurately ✅
- Centralized date handling for consistency ✅

## Benefits

1. **Correctness**: Expiration dates now display accurately
2. **Consistency**: All components use the same date utilities
3. **Maintainability**: Centralized date logic in one module
4. **Testability**: Comprehensive test coverage for date operations
5. **Documentation**: Well-documented functions with JSDoc comments

## Future Considerations

If additional date-related functionality is needed, add it to the `dateUtils.ts` module to maintain consistency across the application.

## Related Files

For a visual demonstration of the fix, see:
- `/Users/muzz/Desktop/tac/TOD/apps/orchestrator_3_stream/tmp_scripts/test_date_fix.html`

This HTML file demonstrates the before/after behavior and can be opened in a browser to see the difference.

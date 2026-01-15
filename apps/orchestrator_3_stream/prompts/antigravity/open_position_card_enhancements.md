# OpenPositionCard.vue Enhancement - Frontend Rough-In

**Date**: 2026-01-14
**Component**: `frontend/src/components/OpenPositionCard.vue`
**Scope**: Frontend UI only (mock data for new fields)
**Backend Integration**: Will be handled separately by Claude agents

---

## Overview

Enhance the OpenPositionCard.vue component to display additional options market data columns and add new action buttons for position management. This is a **frontend rough-in only** - use placeholder/mock data for all new fields in preparation for backend integration.

---

## Requirements

### 1. New Table Columns (Add After "Current" Column, Before "P/L")

Add the following columns to the `el-table` that displays the legs:

#### A. Greeks Column
Display the option Greeks for each leg. Show as a compact multi-line cell:
```
Delta: 0.45
Gamma: 0.02
Theta: -0.15
Vega: 0.08
```

**Mock data structure** - add to `OptionLeg` type:
```typescript
greeks?: {
  delta: number   // Range: -1 to 1
  gamma: number   // Small positive values (0.001 - 0.1)
  theta: number   // Usually negative (time decay)
  vega: number    // Positive values
}
```

**Mock values example:**
- Short Call: `{ delta: -0.35, gamma: 0.02, theta: 0.12, vega: -0.08 }`
- Long Call: `{ delta: 0.15, gamma: 0.01, theta: -0.05, vega: 0.03 }`
- Short Put: `{ delta: 0.25, gamma: 0.02, theta: 0.10, vega: -0.06 }`
- Long Put: `{ delta: -0.18, gamma: 0.01, theta: -0.04, vega: 0.04 }`

#### B. Implied Volatility (IV) Column
Display the implied volatility as a percentage.

**Mock data structure** - add to `OptionLeg` type:
```typescript
impliedVolatility?: number  // e.g., 0.25 = 25%
```

**Display format**: `25.3%` (one decimal place)

**Mock values**: Range typically 15-60% for equity options

#### C. Open Interest Column
Display the open interest (number of outstanding contracts).

**Mock data structure** - add to `OptionLeg` type:
```typescript
openInterest?: number  // Integer, typically 100-50000
```

**Display format**: Comma-separated integer (e.g., `12,450`)

---

### 2. New Action Buttons

#### A. Per-Leg Actions (In the "Actions" Column)

Current button layout: `[Close Leg]`

**New layout**: `[Close Leg] [Roll Leg] [Limit Order]`

Add two new buttons next to the existing "Close Leg" button:

**Roll Leg Button:**
- Position: Immediately after "Close Leg"
- Style: `type="warning"` with `plain` attribute
- Text: "Roll Leg"
- Handler: `handleRollLeg(row)` - stub function that shows a placeholder message

**Limit Order Button:**
- Position: After "Roll Leg"
- Style: `type="primary"` with `plain` attribute
- Text: "Limit Order"
- Handler: `handleLimitOrder(row)` - stub function that shows a placeholder message

#### B. Strategy-Level Actions (In the Card Header)

Current button layout: `[Close Strategy]`

**New layout**: `[Close Strategy] [Roll Strategy]`

Add a new button next to the existing "Close Strategy" button:

**Roll Strategy Button:**
- Position: Before "Close Strategy" button
- Style: `type="warning"` (solid, not plain)
- Size: `small`
- Text: "Roll Strategy"
- Handler: `handleRollStrategy()` - stub function that shows a placeholder message

---

### 3. Mock Data Updates

Update the `mockPosition` object to include all new fields for testing:

```typescript
const mockPosition: OpenPosition = {
  // ... existing fields ...
  legs: [
    {
      id: '1',
      symbol: 'SPY260117C00695000',
      direction: 'Short',
      strike: 695,
      optionType: 'Call',
      quantity: 10,
      entryPrice: 4.04,
      currentPrice: 3.25,
      expiryDate: '2026-01-17',
      underlying: 'SPY',
      // NEW FIELDS:
      greeks: { delta: -0.35, gamma: 0.02, theta: 0.12, vega: -0.08 },
      impliedVolatility: 0.232,
      openInterest: 15420
    },
    // ... update all other legs similarly
  ]
}
```

---

### 4. Stub Handler Functions

Add these placeholder handlers in the `<script setup>` section:

```typescript
function handleRollLeg(leg: OptionLeg) {
  ElMessage.info(`Roll Leg: ${leg.direction} ${leg.optionType} $${leg.strike} - Feature coming soon`)
}

function handleRollStrategy() {
  if (!position.value) return
  ElMessage.info(`Roll Strategy: ${position.value.strategy} - Feature coming soon`)
}

function handleLimitOrder(leg: OptionLeg) {
  ElMessage.info(`Limit Order: ${leg.direction} ${leg.optionType} $${leg.strike} - Feature coming soon`)
}
```

---

### 5. Styling Guidelines

Follow the existing component's styling patterns:

**Colors (use existing CSS variables):**
- `--text`: #e2e8f0 (primary text)
- `--text-muted`: #94a3b8 (secondary/label text)
- `--profit`: #22c55e (positive values)
- `--loss`: #ef4444 (negative values)
- `--border`: #2d3548 (borders)

**Greeks Column Styling:**
- Use `font-size: 0.75rem` for compact display
- Use monospace font (`font-family: 'Roboto Mono', monospace`)
- Display as 2x2 grid or stacked vertically
- Labels in `--text-muted`, values in `--text`

**Button Spacing:**
- Use `gap: 4px` or `margin-left: 4px` between action buttons
- Keep buttons compact with `size="small"`

**IV Column:**
- Right-align the percentage
- Green text if IV < 30%, neutral if 30-50%, amber/orange if > 50%

**Open Interest Column:**
- Right-align the number
- Use `--text` color
- Format with comma separators

---

### 6. Type Updates

Update the `OptionLeg` interface in `types/alpaca.ts`:

```typescript
export interface OptionLeg {
  // ... existing fields ...

  // New fields for Greeks, IV, and OI
  greeks?: {
    delta: number
    gamma: number
    theta: number
    vega: number
  }
  impliedVolatility?: number
  openInterest?: number
}
```

---

### 7. Column Order (Final)

The table columns should be in this order:
1. Position (Direction/Type badges + Strike)
2. Actions (Close Leg, Roll Leg, Limit Order)
3. Qty
4. Entry
5. Current
6. Greeks (NEW)
7. IV (NEW)
8. Open Interest (NEW)
9. P/L

---

## Important Notes

- **Mock Data Only**: All new fields should use hardcoded mock values. Backend will provide real data later.
- **Optional Fields**: All new fields are optional (`?`) since they won't be present in real API responses initially.
- **Null Handling**: Display "--" or empty string when data is unavailable.
- **Responsive**: The card already has `min-width: 800px`. May need to increase to accommodate new columns.
- **Backend Integration**: Claude agents will handle the backend API integration in a separate task. The frontend should be ready with proper type definitions and placeholder displays.

---

## Testing Checklist

After implementation:
- [ ] New columns display correctly with mock data
- [ ] Greeks show 4 values in compact format
- [ ] IV shows as percentage with correct formatting
- [ ] Open Interest shows comma-separated integer
- [ ] Roll Leg button visible and shows info message on click
- [ ] Limit Order button visible and shows info message on click
- [ ] Roll Strategy button visible and shows info message on click
- [ ] All existing functionality still works (close leg, close strategy)
- [ ] Card layout doesn't overflow or break with new columns

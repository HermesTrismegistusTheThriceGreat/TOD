# Implementation Plan: Stage IronCondorCard on Open Positions Page

## Objective

Render multiple `IronCondorCard` components on the existing `OpenPositions.vue` page with hardcoded mock data for UI testing. This is frontend-only work to validate the card component's appearance and behavior before backend integration.

---

## Files to Modify

| File | Action | Purpose |
|------|--------|---------|
| `IronCondorCard.vue` | **Move** | Relocate from project root to components directory |
| `OpenPositions.vue` | **Modify** | Import card, add mock data, render grid of cards |

### File Paths

- **Source**: `/Users/muzz/Desktop/tac/orchestrator-agent-with-adws/IronCondorCard.vue`
- **Destination**: `/Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend/src/components/IronCondorCard.vue`
- **Target**: `/Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend/src/components/OpenPositions.vue`

---

## IronCondorCard Component Analysis

### Props Interface
```typescript
const props = defineProps<{
  positionId?: string
}>()
```

### Internal Data Interfaces
```typescript
interface OptionLeg {
  id: string
  direction: 'Long' | 'Short'
  strike: number
  optionType: 'Call' | 'Put'
  quantity: number
  entryPrice: number
  currentPrice: number
}

interface PositionData {
  ticker: string
  strategy: string
  expiryDate: string  // Format: 'YYYY-MM-DD'
  legs: OptionLeg[]
}
```

### Component Dependencies
- **Vue**: `ref`, `computed`, `onMounted`
- **Element Plus**: `el-card`, `el-tag`, `el-table`, `el-table-column`, `el-icon`, `v-loading`
- **Element Plus Icons**: `Timer` from `@element-plus/icons-vue`

### Key Behavior
- If `positionId` prop is provided, component fetches data (API not implemented yet)
- If `positionId` is NOT provided, component uses internal `placeholderData`
- **For staging**: We will NOT pass `positionId` - cards will use their own placeholder data

---

## Mock Data Structure

Since IronCondorCard uses its own internal placeholder data when no `positionId` is passed, we only need an array to control how many cards render. However, for better staging variety, we should modify the approach to allow passing position data directly.

### Option A: Simple Staging (Use Component's Internal Data)
Just render multiple cards without props - they all show the same SPY Iron Condor data:

```typescript
// Simple staging - all cards show same data
const positionCount = ref(3)
```

### Option B: Better Staging (Pass Data as Props) - RECOMMENDED
Modify IronCondorCard to accept `positionData` prop OR `positionId`:

```typescript
// Mock positions array with variety
const mockPositions: PositionData[] = [
  {
    ticker: 'SPY',
    strategy: 'Iron Condor',
    expiryDate: '2026-01-17',
    legs: [
      { id: '1', direction: 'Short', strike: 588, optionType: 'Call', quantity: 10, entryPrice: 4.04, currentPrice: 3.25 },
      { id: '2', direction: 'Long', strike: 597, optionType: 'Call', quantity: 10, entryPrice: 0.53, currentPrice: 0.09 },
      { id: '3', direction: 'Long', strike: 573, optionType: 'Put', quantity: 10, entryPrice: 1.47, currentPrice: 0.53 },
      { id: '4', direction: 'Short', strike: 578, optionType: 'Put', quantity: 10, entryPrice: 2.90, currentPrice: 1.57 },
    ]
  },
  {
    ticker: 'QQQ',
    strategy: 'Iron Butterfly',
    expiryDate: '2026-01-24',
    legs: [
      { id: '5', direction: 'Long', strike: 510, optionType: 'Call', quantity: 5, entryPrice: 1.20, currentPrice: 0.85 },
      { id: '6', direction: 'Short', strike: 520, optionType: 'Call', quantity: 5, entryPrice: 8.50, currentPrice: 6.20 },
      { id: '7', direction: 'Short', strike: 520, optionType: 'Put', quantity: 5, entryPrice: 7.80, currentPrice: 5.90 },
      { id: '8', direction: 'Long', strike: 530, optionType: 'Put', quantity: 5, entryPrice: 1.35, currentPrice: 0.95 },
    ]
  },
  {
    ticker: 'IWM',
    strategy: 'Iron Condor',
    expiryDate: '2026-01-10',  // Expiring tomorrow!
    legs: [
      { id: '9', direction: 'Short', strike: 225, optionType: 'Call', quantity: 15, entryPrice: 2.10, currentPrice: 0.15 },
      { id: '10', direction: 'Long', strike: 230, optionType: 'Call', quantity: 15, entryPrice: 0.45, currentPrice: 0.02 },
      { id: '11', direction: 'Long', strike: 210, optionType: 'Put', quantity: 15, entryPrice: 0.38, currentPrice: 0.05 },
      { id: '12', direction: 'Short', strike: 215, optionType: 'Put', quantity: 15, entryPrice: 1.85, currentPrice: 0.08 },
    ]
  }
]
```

---

## Implementation Tasks

### Task 1: Move IronCondorCard Component

```bash
# Move from root to components directory
mv /Users/muzz/Desktop/tac/orchestrator-agent-with-adws/IronCondorCard.vue \
   /Users/muzz/Desktop/tac/orchestrator-agent-with-adws/apps/orchestrator_3_stream/frontend/src/components/IronCondorCard.vue
```

### Task 2: Modify IronCondorCard to Accept Position Data (Optional but Recommended)

Add an alternative prop to pass data directly instead of fetching:

```typescript
// Updated props
const props = defineProps<{
  positionId?: string
  initialData?: PositionData  // NEW: Direct data injection
}>()

// Updated onMounted
onMounted(() => {
  if (props.initialData) {
    position.value = props.initialData
  } else if (props.positionId) {
    fetchPosition(props.positionId)
  } else {
    position.value = placeholderData
  }
})
```

### Task 3: Update OpenPositions.vue

Replace the current placeholder with the grid of IronCondorCards:

```vue
<template>
  <div class="open-positions">
    <div class="open-positions-header">
      <h2>Open Positions</h2>
      <span class="position-count">{{ mockPositions.length }} positions</span>
    </div>

    <div class="positions-grid">
      <IronCondorCard
        v-for="(position, index) in mockPositions"
        :key="index"
        :initial-data="position"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import IronCondorCard from './IronCondorCard.vue'

// Type definitions (matching IronCondorCard's internal types)
interface OptionLeg {
  id: string
  direction: 'Long' | 'Short'
  strike: number
  optionType: 'Call' | 'Put'
  quantity: number
  entryPrice: number
  currentPrice: number
}

interface PositionData {
  ticker: string
  strategy: string
  expiryDate: string
  legs: OptionLeg[]
}

// Mock data for staging
const mockPositions = ref<PositionData[]>([
  {
    ticker: 'SPY',
    strategy: 'Iron Condor',
    expiryDate: '2026-01-17',
    legs: [
      { id: '1', direction: 'Short', strike: 588, optionType: 'Call', quantity: 10, entryPrice: 4.04, currentPrice: 3.25 },
      { id: '2', direction: 'Long', strike: 597, optionType: 'Call', quantity: 10, entryPrice: 0.53, currentPrice: 0.09 },
      { id: '3', direction: 'Long', strike: 573, optionType: 'Put', quantity: 10, entryPrice: 1.47, currentPrice: 0.53 },
      { id: '4', direction: 'Short', strike: 578, optionType: 'Put', quantity: 10, entryPrice: 2.90, currentPrice: 1.57 },
    ]
  },
  {
    ticker: 'QQQ',
    strategy: 'Iron Butterfly',
    expiryDate: '2026-01-24',
    legs: [
      { id: '5', direction: 'Long', strike: 510, optionType: 'Call', quantity: 5, entryPrice: 1.20, currentPrice: 0.85 },
      { id: '6', direction: 'Short', strike: 520, optionType: 'Call', quantity: 5, entryPrice: 8.50, currentPrice: 6.20 },
      { id: '7', direction: 'Short', strike: 520, optionType: 'Put', quantity: 5, entryPrice: 7.80, currentPrice: 5.90 },
      { id: '8', direction: 'Long', strike: 530, optionType: 'Put', quantity: 5, entryPrice: 1.35, currentPrice: 0.95 },
    ]
  },
  {
    ticker: 'IWM',
    strategy: 'Iron Condor',
    expiryDate: '2026-01-10',
    legs: [
      { id: '9', direction: 'Short', strike: 225, optionType: 'Call', quantity: 15, entryPrice: 2.10, currentPrice: 0.15 },
      { id: '10', direction: 'Long', strike: 230, optionType: 'Call', quantity: 15, entryPrice: 0.45, currentPrice: 0.02 },
      { id: '11', direction: 'Long', strike: 210, optionType: 'Put', quantity: 15, entryPrice: 0.38, currentPrice: 0.05 },
      { id: '12', direction: 'Short', strike: 215, optionType: 'Put', quantity: 15, entryPrice: 1.85, currentPrice: 0.08 },
    ]
  }
])
</script>

<style scoped>
.open-positions {
  height: 100%;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.open-positions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.open-positions-header h2 {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-primary);
  font-weight: 600;
}

.position-count {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.positions-grid {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(680px, 1fr));
  gap: var(--spacing-lg);
  align-content: start;
}

/* Responsive adjustments */
@media (max-width: 1400px) {
  .positions-grid {
    grid-template-columns: 1fr;
  }
}

/* Scrollbar styling (matching existing patterns) */
.positions-grid::-webkit-scrollbar {
  width: 6px;
}

.positions-grid::-webkit-scrollbar-track {
  background: transparent;
}

.positions-grid::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.positions-grid::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.15);
}
</style>
```

---

## Implementation Checklist

- [ ] **Step 1**: Move `IronCondorCard.vue` from root to `frontend/src/components/`
- [ ] **Step 2**: Modify `IronCondorCard.vue` to add `initialData` prop
- [ ] **Step 3**: Update `onMounted` lifecycle hook in IronCondorCard to handle `initialData`
- [ ] **Step 4**: Replace `OpenPositions.vue` content with new template, script, and styles
- [ ] **Step 5**: Test by navigating to Open Positions view in the UI
- [ ] **Step 6**: Verify all 3 cards render with different data
- [ ] **Step 7**: Verify IWM card shows "Expires Tomorrow" warning (expiry: 2026-01-10)

---

## Acceptance Criteria

1. **Cards Render**: Three IronCondorCard components visible on Open Positions page
2. **Data Variety**: Each card shows different ticker (SPY, QQQ, IWM) and strategy info
3. **Expiry Warning**: IWM card displays "Expires Tomorrow" indicator (urgent styling)
4. **P/L Display**: Each card shows calculated P/L based on entry vs current prices
5. **Responsive Layout**: Cards stack vertically on narrower screens
6. **No Console Errors**: Clean browser console, no Vue/Element Plus warnings
7. **Dark Theme**: Cards integrate seamlessly with existing dark theme

---

## Mock Data Rationale

| Ticker | Strategy | DTE | Purpose |
|--------|----------|-----|---------|
| SPY | Iron Condor | 8 days | Standard profitable position |
| QQQ | Iron Butterfly | 15 days | Different strategy type |
| IWM | Iron Condor | 1 day | Tests "Expires Tomorrow" warning |

---

## Out of Scope (DO NOT Implement)

- Backend API integration
- Pinia state management for positions
- Loading/error states for API calls
- Real-time price updates
- Position CRUD operations

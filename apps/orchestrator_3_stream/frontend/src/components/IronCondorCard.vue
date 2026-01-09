<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Timer } from '@element-plus/icons-vue'

// Types for API response
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

// Props - pass position ID to fetch from API OR initialData for direct injection
const props = defineProps<{
  positionId?: string
  initialData?: PositionData
}>()

// State
const loading = ref(false)
const position = ref<PositionData | null>(null)

// Placeholder data - replace with API call
const placeholderData: PositionData = {
  ticker: 'SPY',
  strategy: 'Iron Condor',
  expiryDate: '2026-01-10',
  legs: [
    { id: '1', direction: 'Short', strike: 688, optionType: 'Call', quantity: 10, entryPrice: 4.04, currentPrice: 3.25 },
    { id: '2', direction: 'Long', strike: 697, optionType: 'Call', quantity: 10, entryPrice: 0.53, currentPrice: 0.09 },
    { id: '3', direction: 'Long', strike: 683, optionType: 'Put', quantity: 10, entryPrice: 1.47, currentPrice: 0.53 },
    { id: '4', direction: 'Short', strike: 688, optionType: 'Put', quantity: 10, entryPrice: 2.90, currentPrice: 1.57 },
  ]
}

// API fetch function - implement your endpoint here
const fetchPosition = async (id: string) => {
  loading.value = true
  try {
    // TODO: Replace with actual API call
    // const response = await fetch(`/api/positions/${id}`)
    // position.value = await response.json()

    // Using placeholder for now
    await new Promise(resolve => setTimeout(resolve, 300)) // Simulate network delay
    position.value = placeholderData
  } catch (error) {
    console.error('Failed to fetch position:', error)
  } finally {
    loading.value = false
  }
}

// Computed values
const daysToExpiry = computed(() => {
  if (!position.value) return 0
  const expiry = new Date(position.value.expiryDate)
  const today = new Date()
  return Math.max(0, Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)))
})

const totalPnL = computed(() => {
  if (!position.value) return 0
  return position.value.legs.reduce((sum, leg) => {
    return sum + calculateLegPnL(leg).dollars
  }, 0)
})

const sortedLegs = computed(() => {
  if (!position.value) return []
  const legs = [...position.value.legs]
  
  const calls = legs.filter(l => l.optionType === 'Call')
  const puts = legs.filter(l => l.optionType === 'Put')

  // Sort Calls: Long then Short (High Strike -> Low Strike often correlates, but sticking to Direction)
  calls.sort((a, b) => {
    if (a.direction === 'Long' && b.direction === 'Short') return -1
    if (a.direction === 'Short' && b.direction === 'Long') return 1
    return b.strike - a.strike // Secondary sort by strike descending
  })

  // Sort Puts: Short then Long
  puts.sort((a, b) => {
    if (a.direction === 'Short' && b.direction === 'Long') return -1
    if (a.direction === 'Long' && b.direction === 'Short') return 1
    return b.strike - a.strike // Secondary sort by strike descending
  })

  return [...calls, ...puts]
})

// Helpers
const calculateLegPnL = (leg: OptionLeg) => {
  const multiplier = leg.direction === 'Short' ? 1 : -1
  const priceDiff = (leg.entryPrice - leg.currentPrice) * multiplier
  const dollars = priceDiff * leg.quantity * 100
  const percent = ((leg.currentPrice - leg.entryPrice) / leg.entryPrice) * 100 * (leg.direction === 'Short' ? -1 : 1)
  return { dollars, percent }
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const formatCurrency = (value: number) => `${value >= 0 ? '+' : ''}$${Math.abs(value).toLocaleString()}`
const formatPercent = (value: number) => `(${value >= 0 ? '+' : ''}${value.toFixed(2)}%)`

// Lifecycle
onMounted(() => {
  if (props.initialData) {
    position.value = props.initialData
  } else if (props.positionId) {
    fetchPosition(props.positionId)
  } else {
    position.value = placeholderData
  }
})
</script>

<template>
  <el-card v-loading="loading" class="position-card">
    <template v-if="position">
      <!-- Header -->
      <div class="card-header">
        <div class="header-title">
          <span class="ticker">{{ position.ticker }}</span>
          <el-tag type="info" effect="plain">{{ position.strategy }}</el-tag>
          <span class="expiry-text">({{ formatDate(position.expiryDate) }})</span>
        </div>
        <div class="header-actions">
          <!-- TODO: Backend Dev - Connect this button to the close strategy endpoint -->
          <el-button type="danger" size="small">Close Strategy</el-button>
        </div>
      </div>

      <!-- Main Content Flex Wrapper -->
      <div class="content-wrapper">
        
        <!-- Left Sidebar: Stats -->
        <div class="stats-sidebar">
          <!-- P/L Circle -->
          <div class="pnl-ring" :class="totalPnL >= 0 ? 'profit' : 'loss'">
            <span class="pnl-label">TOTAL P/L</span>
            <span class="pnl-value">{{ formatCurrency(totalPnL) }}</span>
          </div>

          <!-- DTE Box -->
          <div class="dte-box">
            <span class="dte-value">{{ daysToExpiry }}</span>
            <span class="dte-label">{{ daysToExpiry === 1 ? 'day' : 'days' }}</span>
          </div>
        </div>

        <!-- Right Content: Legs Table -->
        <div class="legs-content">
          <div class="legs-header">
            <span class="summary-badge">{{ position.legs.length }} legs position</span>
          </div>

          <el-table :data="sortedLegs" class="legs-table" style="width: 100%">
            <el-table-column label="Position" min-width="240" align="center" header-align="center">
              <template #default="{ row }">
                <div class="position-cell">
                  <div class="badges">
                    <span class="custom-tag" :class="row.direction.toLowerCase()">
                      {{ row.direction }}
                    </span>
                    <span class="custom-tag" :class="row.optionType.toLowerCase()">
                      {{ row.optionType }}
                    </span>
                  </div>
                  <span class="strike">${{ row.strike }}</span>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="Actions" min-width="120" align="center">
              <template #default>
                <!-- Note: Backend API connection pending -->
                <el-button class="close-leg-btn" size="small" type="danger" plain>Close Leg</el-button>
              </template>
            </el-table-column>

            <el-table-column label="Qty" align="center" min-width="80">
              <template #default="{ row }">
                {{ row.direction === 'Short' ? '-' : '' }}{{ row.quantity }}
              </template>
            </el-table-column>

            <el-table-column label="Entry" align="center" min-width="90">
              <template #default="{ row }">${{ row.entryPrice.toFixed(2) }}</template>
            </el-table-column>

            <el-table-column label="Current" align="center" min-width="90">
              <template #default="{ row }">${{ row.currentPrice.toFixed(2) }}</template>
            </el-table-column>

            <el-table-column label="P/L" align="center" min-width="140" header-align="center">
              <template #default="{ row }">
                <span :class="calculateLegPnL(row).dollars >= 0 ? 'text-profit' : 'text-loss'">
                  {{ formatCurrency(calculateLegPnL(row).dollars) }}
                  <span class="pnl-pct">{{ formatPercent(calculateLegPnL(row).percent) }}</span>
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>

      </div>
    </template>
  </el-card>
</template>

<style scoped>
.position-card {
  --bg-dark: #1e2433;
  --bg-darker: #171c28;
  --border: #2d3548;
  --profit: #22c55e;
  --loss: #ef4444;
  --text: #e2e8f0;
  --text-muted: #94a3b8;
  
  /* Custom Badge Colors */
  --color-short: #f59e0b;  /* Amber */
  --color-long: #10b981;   /* Emerald */
  --color-call: #3b82f6;   /* Blue */
  --color-put: #f43f5e;    /* Rose/Red */

  background: var(--bg-dark);
  border: 1px solid var(--border);
  border-radius: 12px;
  color: var(--text);
  /* Adjusted for side-by-side layout: wider min-width */
  min-width: 800px; 
  overflow: hidden;
  height: fit-content;
}

/* Override Element Plus card body padding */
.position-card :deep(.el-card__body) {
  padding: 20px;
  overflow: visible;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ticker {
  font-size: 1.4rem;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.expiry-text {
  color: var(--text-muted);
  font-size: 0.9rem;
}

/* Main Layout Wrapper */
.content-wrapper {
  display: flex;
  gap: 32px;
  align-items: flex-start;
}

/* Sidebar Styling */
.stats-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex-shrink: 0; /* Don't shrink the sidebar */
  width: 140px; /* Fixed width matching the ring */
}

/* P/L Ring */
.pnl-ring {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  border: 4px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--bg-darker);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.pnl-ring.profit { border-color: var(--profit); }
.pnl-ring.loss { border-color: var(--loss); }

.pnl-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  letter-spacing: 1px;
  margin-bottom: 4px;
}

.pnl-value {
  font-size: 1.5rem;
  font-weight: 700;
}

.pnl-ring.profit .pnl-value { color: var(--profit); }
.pnl-ring.loss .pnl-value { color: var(--loss); }

/* DTE Box */
.dte-box {
  text-align: center;
  padding: 12px;
  background: var(--bg-darker);
  border-radius: 8px;
  border: 1px solid var(--border);
}

.dte-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.1;
  color: var(--text);
}

.dte-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Right Content Styling */
.legs-content {
  flex-grow: 1; /* Take up remaining space */
  min-width: 0; /* Critical for table scrolling/sizing inside flex */
}

.legs-header {
  display: flex;
  margin-bottom: 12px;
}

.summary-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border: 1px solid var(--border);
}

.legs-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent; /* Cleaner look */
  --el-table-header-bg-color: rgba(255,255,255,0.02);
  --el-table-border-color: var(--border);
  --el-table-text-color: var(--text);
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.04);
  
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
}

/* Remove bottom border of the last row for cleaner look */
.legs-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.position-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.badges {
  display: flex;
  gap: 4px;
}

.custom-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border: 1px solid transparent;
}

/* Color Styles */
.custom-tag.short {
  background: rgba(245, 158, 11, 0.15);
  color: var(--color-short);
  border-color: rgba(245, 158, 11, 0.3);
}

.custom-tag.long {
  background: rgba(16, 185, 129, 0.15);
  color: var(--color-long);
  border-color: rgba(16, 185, 129, 0.3);
}

.custom-tag.call {
  background: rgba(59, 130, 246, 0.15);
  color: var(--color-call);
  border-color: rgba(59, 130, 246, 0.3);
}

.custom-tag.put {
  background: rgba(244, 63, 94, 0.15);
  color: var(--color-put);
  border-color: rgba(244, 63, 94, 0.3);
}

.strike {
  font-weight: 600;
  font-family: 'Roboto Mono', monospace;
  font-size: 1.1em;
}

.text-profit { color: var(--profit); }
.text-loss { color: var(--loss); }

.pnl-pct {
  font-size: 0.8em;
  opacity: 0.7;
  margin-left: 4px;
}

.header-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.dev-note {
  font-size: 0.65rem;
  color: var(--text-muted);
  font-style: italic;
  opacity: 0.6;
}

.close-leg-btn {
  /* Always visible now */
  /* opacity: 0; */ 
  transition: opacity 0.2s ease;
}

/* 
.legs-table :deep(.el-table__row:hover) .close-leg-btn {
  opacity: 1;
} 
*/
</style>

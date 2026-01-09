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
        <el-tag
          :type="daysToExpiry <= 1 ? 'danger' : 'warning'"
          effect="dark"
        >
          <el-icon><Timer /></el-icon>
          {{ daysToExpiry <= 1 ? 'Expires Tomorrow' : `${daysToExpiry} DTE` }}
        </el-tag>
      </div>

      <!-- Body -->
      <div class="card-body">
        <!-- P/L Circle -->
        <div class="pnl-ring" :class="totalPnL >= 0 ? 'profit' : 'loss'">
          <span class="pnl-label">TOTAL P/L</span>
          <span class="pnl-value">{{ formatCurrency(totalPnL) }}</span>
          <span class="pnl-sub">sum of {{ position.legs.length }} legs</span>
        </div>

        <!-- DTE Box -->
        <div class="dte-box">
          <span class="dte-value">{{ daysToExpiry }}</span>
          <span class="dte-label">{{ daysToExpiry === 1 ? 'day' : 'days' }}</span>
        </div>
      </div>

      <!-- Legs Table -->
      <el-table :data="position.legs" class="legs-table">
        <el-table-column label="Position" min-width="160">
          <template #default="{ row }">
            <div class="position-cell">
              <el-tag :type="row.direction === 'Short' ? 'warning' : 'success'" size="small">
                {{ row.direction }}
              </el-tag>
              <span class="strike">${{ row.strike }}</span>
              <el-tag :type="row.optionType === 'Call' ? 'primary' : 'danger'" size="small" effect="dark">
                {{ row.optionType }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="Qty" align="center" width="70">
          <template #default="{ row }">
            {{ row.direction === 'Short' ? '-' : '' }}{{ row.quantity }}
          </template>
        </el-table-column>

        <el-table-column label="Entry" align="center" width="80">
          <template #default="{ row }">${{ row.entryPrice.toFixed(2) }}</template>
        </el-table-column>

        <el-table-column label="Current" align="center" width="80">
          <template #default="{ row }">${{ row.currentPrice.toFixed(2) }}</template>
        </el-table-column>

        <el-table-column label="P/L" align="right" width="140">
          <template #default="{ row }">
            <span :class="calculateLegPnL(row).dollars >= 0 ? 'text-profit' : 'text-loss'">
              {{ formatCurrency(calculateLegPnL(row).dollars) }}
              <span class="pnl-pct">{{ formatPercent(calculateLegPnL(row).percent) }}</span>
            </span>
          </template>
        </el-table-column>
      </el-table>
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

  background: var(--bg-dark);
  border: 1px solid var(--border);
  border-radius: 12px;
  color: var(--text);
  max-width: 720px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ticker {
  font-size: 1.25rem;
  font-weight: 700;
}

.expiry-text {
  color: var(--text-muted);
}

.card-body {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 0 20px;
}

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
}

.pnl-ring.profit { border-color: var(--profit); }
.pnl-ring.loss { border-color: var(--loss); }

.pnl-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  letter-spacing: 1px;
}

.pnl-value {
  font-size: 1.75rem;
  font-weight: 700;
}

.pnl-ring.profit .pnl-value { color: var(--profit); }
.pnl-ring.loss .pnl-value { color: var(--loss); }

.pnl-sub {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.dte-box {
  text-align: center;
  padding: 16px 28px;
  background: var(--bg-darker);
  border-radius: 8px;
  border: 1px solid var(--border);
}

.dte-value {
  display: block;
  font-size: 3rem;
  font-weight: 700;
  line-height: 1;
}

.dte-label {
  font-size: 0.9rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.legs-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: var(--bg-darker);
  --el-table-header-bg-color: var(--bg-darker);
  --el-table-border-color: var(--border);
  --el-table-text-color: var(--text);
}

.position-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strike {
  font-weight: 600;
}

.text-profit { color: var(--profit); }
.text-loss { color: var(--loss); }

.pnl-pct {
  font-size: 0.85em;
  opacity: 0.8;
}
</style>

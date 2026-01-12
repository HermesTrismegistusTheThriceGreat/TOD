<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Timer, Loading, Warning } from '@element-plus/icons-vue'
import { useAlpacaPositions } from '../composables/useAlpacaPositions'
import { useAlpacaPriceStream } from '../composables/useAlpacaPriceStream'
import type { OptionLeg, IronCondorPosition } from '../types/alpaca'
import { calculateLegPnl } from '../types/alpaca'

// Props
const props = defineProps<{
  positionId?: string
  initialData?: IronCondorPosition
  /** Use mock data (for development/demo) */
  useMockData?: boolean
}>()

// Composables
const {
  positions,
  currentPosition,
  loading,
  error,
  hasPositions,
  refresh,
  getCachedPrice,
} = useAlpacaPositions({
  autoFetch: !props.useMockData && !props.initialData,
  autoSubscribe: !props.useMockData,
  positionId: props.positionId,
})

const { getMidPrice, connectionStatus } = useAlpacaPriceStream()

// Local state
const position = ref<IronCondorPosition | null>(null)

// Mock data for development
const mockPosition: IronCondorPosition = {
  id: 'mock-1',
  ticker: 'SPY',
  strategy: 'Iron Condor',
  expiryDate: '2026-01-17',
  createdAt: new Date().toISOString(),
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
      underlying: 'SPY'
    },
    {
      id: '2',
      symbol: 'SPY260117C00700000',
      direction: 'Long',
      strike: 700,
      optionType: 'Call',
      quantity: 10,
      entryPrice: 0.53,
      currentPrice: 0.09,
      expiryDate: '2026-01-17',
      underlying: 'SPY'
    },
    {
      id: '3',
      symbol: 'SPY260117P00680000',
      direction: 'Long',
      strike: 680,
      optionType: 'Put',
      quantity: 10,
      entryPrice: 1.47,
      currentPrice: 0.53,
      expiryDate: '2026-01-17',
      underlying: 'SPY'
    },
    {
      id: '4',
      symbol: 'SPY260117P00685000',
      direction: 'Short',
      strike: 685,
      optionType: 'Put',
      quantity: 10,
      entryPrice: 2.90,
      currentPrice: 1.57,
      expiryDate: '2026-01-17',
      underlying: 'SPY'
    },
  ]
}

// Watch for position changes
watch([currentPosition, positions], () => {
  if (props.initialData) {
    position.value = props.initialData
  } else if (props.useMockData) {
    position.value = mockPosition
  } else if (currentPosition.value) {
    position.value = currentPosition.value
  } else if (positions.value.length > 0) {
    position.value = positions.value[0]
  }
}, { immediate: true })

// Update prices from WebSocket cache
watch(
  () => [position.value, getMidPrice],
  () => {
    if (!position.value) return

    for (const leg of position.value.legs) {
      const price = getMidPrice(leg.symbol)
      if (price !== undefined) {
        leg.currentPrice = price
        const pnl = calculateLegPnl(leg)
        leg.pnlDollars = pnl.dollars
        leg.pnlPercent = pnl.percent
      }
    }
  },
  { deep: true }
)

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
    const pnl = calculateLegPnl(leg)
    return sum + pnl.dollars
  }, 0)
})

const sortedLegs = computed(() => {
  if (!position.value) return []
  const legs = [...position.value.legs]

  const calls = legs.filter(l => l.optionType === 'Call')
  const puts = legs.filter(l => l.optionType === 'Put')

  // Sort Calls: Short then Long (by strike descending)
  calls.sort((a, b) => {
    if (a.direction === 'Short' && b.direction === 'Long') return -1
    if (a.direction === 'Long' && b.direction === 'Short') return 1
    return b.strike - a.strike
  })

  // Sort Puts: Short then Long (by strike descending)
  puts.sort((a, b) => {
    if (a.direction === 'Short' && b.direction === 'Long') return -1
    if (a.direction === 'Long' && b.direction === 'Short') return 1
    return b.strike - a.strike
  })

  return [...calls, ...puts]
})

// Helpers
const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

const formatCurrency = (value: number) => {
  return `${value >= 0 ? '+' : ''}$${Math.abs(value).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  })}`
}

const formatPercent = (value: number) => {
  return `(${value >= 0 ? '+' : ''}${value.toFixed(2)}%)`
}

const formatPrice = (value: number) => {
  return `$${value.toFixed(2)}`
}

// Lifecycle
onMounted(() => {
  if (props.initialData) {
    position.value = props.initialData
  } else if (props.useMockData) {
    position.value = mockPosition
  }
})
</script>

<template>
  <el-card class="position-card">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <span>Loading positions...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <el-icon :size="24"><Warning /></el-icon>
      <span>{{ error }}</span>
      <el-button size="small" @click="refresh">Retry</el-button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!position" class="empty-state">
      <span>No option positions found</span>
    </div>

    <!-- Position Content -->
    <template v-else>
      <!-- Header -->
      <div class="card-header">
        <div class="header-title">
          <span class="ticker">{{ position.ticker }}</span>
          <el-tag type="info" effect="plain">{{ position.strategy }}</el-tag>
          <span class="expiry-text">({{ formatDate(position.expiryDate) }})</span>
        </div>
        <div class="header-actions">
          <!-- Connection Status Indicator -->
          <div class="connection-status" :class="connectionStatus">
            <span class="status-dot"></span>
            <span class="status-text">{{ connectionStatus }}</span>
          </div>
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
                  <span class="strike">{{ formatPrice(row.strike) }}</span>
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
              <template #default="{ row }">{{ formatPrice(row.entryPrice) }}</template>
            </el-table-column>

            <el-table-column label="Current" align="center" min-width="90">
              <template #default="{ row }">{{ formatPrice(row.currentPrice) }}</template>
            </el-table-column>

            <el-table-column label="P/L" align="center" min-width="140" header-align="center">
              <template #default="{ row }">
                <span :class="(row.pnlDollars || calculateLegPnl(row).dollars) >= 0 ? 'text-profit' : 'text-loss'">
                  {{ formatCurrency(row.pnlDollars || calculateLegPnl(row).dollars) }}
                  <span class="pnl-pct">{{ formatPercent(row.pnlPercent || calculateLegPnl(row).percent) }}</span>
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

/* Loading, Error, Empty States */
.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px;
  color: var(--text-muted);
}

.error-state {
  color: var(--loss);
}

.error-state .el-button {
  margin-top: 8px;
}

/* Connection Status */
.connection-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  margin-right: 12px;
}

.connection-status .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.connection-status.connected .status-dot {
  background: var(--profit);
}

.connection-status.disconnected .status-dot {
  background: #f59e0b;
}

.connection-status.error .status-dot {
  background: var(--loss);
}

.connection-status .status-text {
  text-transform: capitalize;
  color: var(--text-muted);
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

.header-actions {
  display: flex;
  align-items: center;
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

.close-leg-btn {
  transition: opacity 0.2s ease;
}
</style>

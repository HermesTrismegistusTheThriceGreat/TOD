<template>
  <div class="trade-stats">
    <!-- Header with refresh button -->
    <div class="trade-stats-header">
      <div class="header-left">
        <h2>Trade History</h2>
        <div class="header-stats-summary" v-if="!loading && !error">
          <div class="summary-pill">
            <span class="label">Total P&L:</span>
            <span class="value" :class="getPnlClass(stats.total_pnl)">{{ formatMoney(stats.total_pnl) }}</span>
          </div>
          <div class="summary-pill">
            <span class="label">Win Rate:</span>
            <span class="value">{{ stats.win_rate.toFixed(1) }}%</span>
          </div>
          <div class="summary-pill">
            <span class="label">Trades:</span>
            <span class="value">{{ stats.total_trades }}</span>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <el-radio-group v-model="statusFilter" size="small" class="status-filter">
          <el-radio-button label="all">ALL</el-radio-button>
          <el-radio-button label="open">OPEN</el-radio-button>
          <el-radio-button label="closed">CLOSED</el-radio-button>
        </el-radio-group>
        <el-button
          :icon="Download"
          circle
          size="small"
          :loading="syncing"
          @click="handleSync"
          title="Sync orders from Alpaca"
        />
        <el-button
          :icon="Refresh"
          circle
          size="small"
          :loading="loading"
          @click="handleRefresh"
          title="Refresh statistics"
        />
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="state-container loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <span>Loading trade statistics...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="state-container error-state">
      <el-icon :size="32"><WarningFilled /></el-icon>
      <span>{{ error }}</span>
      <el-button type="primary" size="small" @click="handleRefresh">
        Retry
      </el-button>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredTrades.length === 0" class="state-container empty-state">
      <el-icon :size="32"><Search /></el-icon>
      <span>No trades found matching the current filters</span>
    </div>

    <!-- Trade History Table -->
    <div v-else class="stats-content">
      <el-table 
        :data="filteredTrades" 
        style="width: 100%" 
        class="trade-table"
        :header-cell-style="{ background: 'var(--bg-tertiary)', borderBottom: '1px solid var(--border-color)' }"
        :cell-style="{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-light)' }"
      >
        <el-table-column prop="ticker" label="TICKER" width="100">
          <template #default="{ row }">
            <span class="ticker-symbol">{{ row.ticker }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="strategy" label="STRATEGY" min-width="150">
          <template #default="{ row }">
            <el-tag size="small" effect="dark" :type="getStrategyTagType(row.strategy)">
              {{ formatStrategy(row.strategy) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="direction" label="DIR" width="80">
          <template #default="{ row }">
            <span :class="row.direction === 'Long' ? 'text-long' : 'text-short'">
              {{ row.direction.toUpperCase() }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column prop="entry_date" label="ENTRY DATE" width="120" sortable>
          <template #default="{ row }">
            {{ row.entry_date ? new Date(row.entry_date).toLocaleDateString() : '—' }}
          </template>
        </el-table-column>

        <el-table-column prop="exit_date" label="EXIT DATE" width="120">
          <template #default="{ row }">
            {{ row.exit_date ? new Date(row.exit_date).toLocaleDateString() : '—' }}
          </template>
        </el-table-column>
        
        <el-table-column prop="pnl" label="P&L" width="120" sortable align="right">
          <template #default="{ row }">
            <span :class="getPnlClass(row.pnl)" class="pnl-value">
              {{ formatMoney(row.pnl) }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column prop="pnl_percent" label="P&L %" width="100" align="right">
          <template #default="{ row }">
            <span :class="getPnlClass(row.pnl_percent)" class="pnl-percent">
              {{ row.pnl_percent > 0 ? '+' : '' }}{{ row.pnl_percent.toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        
        <el-table-column prop="status" label="STATUS" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small" effect="light" class="status-tag">
              {{ row.status.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Loading, Refresh, Search, WarningFilled, Download } from '@element-plus/icons-vue'
import { tradeApi } from '@/services/api'
import type { Trade } from '@/types/trades'

const loading = ref(false)
const syncing = ref(false)
const error = ref<string | null>(null)
const statusFilter = ref<'all' | 'open' | 'closed'>('all')
const trades = ref<Trade[]>([])
const stats = ref({
  total_pnl: 0,
  win_rate: 0,
  total_trades: 0
})

// AbortController for request cancellation
let abortController: AbortController | null = null

const filteredTrades = computed(() => {
  if (statusFilter.value === 'all') return trades.value
  return trades.value.filter(t => t.status === statusFilter.value)
})

const fetchTrades = async () => {
  // Cancel any previous pending request
  if (abortController) {
    abortController.abort()
  }
  abortController = new AbortController()
  const signal = abortController.signal

  loading.value = true
  error.value = null

  try {
    const [tradesRes, statsRes] = await Promise.all([
      tradeApi.getTrades({ status: statusFilter.value === 'all' ? undefined : statusFilter.value }),
      tradeApi.getTradeStats(statusFilter.value === 'all' ? undefined : statusFilter.value)
    ])

    // Check if request was aborted before processing response
    if (signal.aborted) return

    if (tradesRes.status === 'success') {
      // Defensive null check: ensure trades is an array before assignment
      trades.value = Array.isArray(tradesRes.trades) ? tradesRes.trades : []
    } else {
      error.value = tradesRes.message || 'Failed to fetch trades'
    }

    if (statsRes.status === 'success') {
      // Use optional chaining and nullish coalescing for safe access
      stats.value = {
        total_pnl: statsRes.total_pnl ?? 0,
        win_rate: statsRes.win_rate ?? 0,
        total_trades: statsRes.total_trades ?? 0
      }
    }
  } catch (e) {
    // Handle AbortError separately - don't show as user-facing error
    if (e instanceof Error && e.name === 'AbortError') {
      // Request was cancelled, no need to update state
      return
    }
    error.value = e instanceof Error ? e.message : 'An error occurred'
  } finally {
    // Only update loading state if request wasn't aborted
    if (!signal.aborted) {
      loading.value = false
    }
  }
}

// Watch for filter changes
watch(statusFilter, () => {
  fetchTrades()
})

onMounted(() => {
  fetchTrades()
})

// Cleanup on unmount
onUnmounted(() => {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
})

const handleRefresh = () => {
  fetchTrades()
}

const handleSync = async () => {
  syncing.value = true
  error.value = null
  try {
    const result = await tradeApi.syncOrders()
    if (result.status === 'success') {
      // Refresh trades after sync
      await fetchTrades()
    } else {
      error.value = result.message || 'Sync failed'
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Sync failed'
  } finally {
    syncing.value = false
  }
}

const getPnlClass = (val: number) => {
  if (val > 0) return 'positive'
  if (val < 0) return 'negative'
  return 'neutral'
}

const formatMoney = (val: number) => {
  const sign = val >= 0 ? '' : '-'
  return sign + '$' + Math.abs(val).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

const formatStrategy = (strategy: string): string => {
  const strategyMap: Record<string, string> = {
    'iron_condor': 'Iron Condor',
    'vertical_spread': 'Vertical Spread',
    'strangle': 'Strangle',
    'straddle': 'Straddle',
    'single_leg': 'Single Leg',
    'options': 'Options'
  }
  return strategyMap[strategy] || strategy
}

const getStrategyTagType = (strategy: string) => {
  if (strategy.includes('condor') || strategy.includes('Condor')) return ''
  if (strategy.includes('spread') || strategy.includes('Spread')) return 'success'
  if (strategy.includes('strangle') || strategy.includes('Strangle')) return 'warning'
  return 'info'
}

const getStatusTagType = (status: string) => {
  switch (status) {
    case 'open': return 'primary'
    case 'closed': return 'success'
    case 'expired': return 'warning'
    default: return 'info'
  }
}
</script>

<style scoped>
.trade-stats {
  height: 100%;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.trade-stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.trade-stats-header h2 {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-primary);
  font-weight: 600;
}

.header-stats-summary {
  display: flex;
  gap: var(--spacing-md);
}

.summary-pill {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  background: var(--bg-tertiary);
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid var(--border-light);
  font-size: 0.75rem;
}

.summary-pill .label {
  color: var(--text-muted);
  font-weight: 500;
}

.summary-pill .value {
  font-weight: 700;
  font-family: var(--font-mono);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-filter :deep(.el-radio-button__inner) {
  background: var(--bg-tertiary);
  border-color: var(--border-color);
  color: var(--text-muted);
  font-size: 0.65rem;
  font-weight: 600;
}

.status-filter :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: white;
  box-shadow: none;
}

/* State Containers */
.state-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 48px;
  color: var(--text-muted);
}

.loading-state .el-icon {
  color: var(--accent-primary);
}

.error-state {
  color: var(--status-error);
}

.error-state .el-icon {
  color: var(--status-error);
}

.stats-content {
  flex: 1;
  overflow: hidden;
  padding: var(--spacing-lg);
}

.trade-table {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  --el-table-border-color: var(--border-color);
  --el-table-header-text-color: var(--text-muted);
  --el-table-text-color: var(--text-primary);
}

.ticker-symbol {
  font-weight: 700;
  color: var(--accent-primary);
  font-family: var(--font-mono);
}

.text-long {
  color: var(--status-success);
  font-weight: 600;
}

.text-short {
  color: var(--status-error);
  font-weight: 600;
}

.pnl-value {
  font-weight: 700;
  font-family: var(--font-mono);
}

.pnl-percent {
  font-size: 0.75rem;
  font-weight: 600;
}

.positive {
  color: var(--status-success);
}

.negative {
  color: var(--status-error);
}

.neutral {
  color: var(--text-muted);
}

.status-tag {
  font-weight: 700;
  font-size: 0.65rem;
  letter-spacing: 0.025em;
}

/* Scrollbar styling for Element Plus Table */
:deep(.el-table__body-wrapper::-webkit-scrollbar) {
  width: 6px;
}

:deep(.el-table__body-wrapper::-webkit-scrollbar-track) {
  background: transparent;
}

:deep(.el-table__body-wrapper::-webkit-scrollbar-thumb) {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

:deep(.el-table__body-wrapper::-webkit-scrollbar-thumb:hover) {
  background: rgba(255, 255, 255, 0.15);
}
</style>

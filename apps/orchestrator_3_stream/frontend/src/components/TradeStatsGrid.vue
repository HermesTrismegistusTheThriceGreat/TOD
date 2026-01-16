<template>
  <div class="trade-stats-grid">
    <!-- Header -->
    <div class="grid-header">
      <div class="header-left">
        <h2>Trade History</h2>
        <div class="header-stats" v-if="!loading && trades.length > 0">
          <div class="stat-pill">
            <span class="label">Trades:</span>
            <span class="value">{{ trades.length }}</span>
          </div>
          <div class="stat-pill">
            <span class="label">Total P&L:</span>
            <span class="value" :class="getTotalPnlClass">
              {{ formatMoney(totalPnl) }}
            </span>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <el-radio-group v-model="statusFilter" size="small">
          <el-radio-button label="all">ALL</el-radio-button>
          <el-radio-button label="open">OPEN</el-radio-button>
          <el-radio-button label="closed">CLOSED</el-radio-button>
        </el-radio-group>
        <el-button
          type="primary"
          size="small"
          :loading="syncing"
          @click="handleSync"
        >
          Sync Orders
        </el-button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <span>Loading trades...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <el-icon :size="32"><WarningFilled /></el-icon>
      <span>{{ error }}</span>
      <el-button type="primary" size="small" @click="fetchTrades">
        Retry
      </el-button>
    </div>

    <!-- Empty State -->
    <div v-else-if="trades.length === 0" class="empty-state">
      <el-icon :size="48"><Document /></el-icon>
      <span>No trades found</span>
      <el-button type="primary" size="small" @click="handleSync">
        Sync from Alpaca
      </el-button>
    </div>

    <!-- Trade Cards Grid -->
    <div v-else class="cards-grid">
      <TradeStatsCard
        v-for="trade in trades"
        :key="trade.trade_id"
        :trade="trade"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Loading, WarningFilled, Document } from '@element-plus/icons-vue'
import { tradeApi } from '@/services/api'
import type { DetailedTrade } from '@/types/trades'
import TradeStatsCard from './TradeStatsCard.vue'

const loading = ref(false)
const syncing = ref(false)
const error = ref<string | null>(null)
const trades = ref<DetailedTrade[]>([])
const statusFilter = ref<'all' | 'open' | 'closed'>('all')

const totalPnl = computed(() => {
  return trades.value.reduce((sum, t) => sum + t.summary.net_pnl_total, 0)
})

const getTotalPnlClass = computed(() => {
  if (totalPnl.value > 0) return 'positive'
  if (totalPnl.value < 0) return 'negative'
  return 'neutral'
})

const formatMoney = (value: number) => {
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${Math.abs(value).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  })}`
}

const fetchTrades = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await tradeApi.getDetailedTrades({
      status: statusFilter.value,  // Pass status directly; 'all' is a valid value handled by backend
      limit: 50
    })

    if (response.status === 'success') {
      trades.value = response.trades
    } else {
      error.value = response.message || 'Failed to load trades'
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error'
  } finally {
    loading.value = false
  }
}

const handleSync = async () => {
  syncing.value = true
  try {
    await tradeApi.syncOrders()
    await fetchTrades()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Sync failed'
  } finally {
    syncing.value = false
  }
}

watch(statusFilter, () => {
  fetchTrades()
})

onMounted(() => {
  fetchTrades()
})
</script>

<style scoped>
.trade-stats-grid {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  overflow: hidden;
}

.grid-header {
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

.header-left h2 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--text-primary);
}

.header-stats {
  display: flex;
  gap: var(--spacing-sm);
}

.stat-pill {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  background: var(--bg-tertiary);
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid var(--border-light);
  font-size: 0.75rem;
}

.stat-pill .label {
  color: var(--text-muted);
}

.stat-pill .value {
  font-weight: 600;
  font-family: var(--font-mono);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.loading-state,
.error-state,
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  color: var(--text-muted);
}

.cards-grid {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
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
</style>

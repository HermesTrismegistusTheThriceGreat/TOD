<template>
  <el-card class="trade-stats-card">
    <!-- Card Header -->
    <div class="card-header">
      <div class="header-left">
        <span class="ticker">{{ trade.ticker }}</span>
        <el-tag
          :type="getStrategyTagType(trade.strategy)"
          size="small"
          effect="dark"
        >
          {{ formatStrategy(trade.strategy) }}
        </el-tag>
      </div>
      <div class="header-right">
        <el-tag
          :type="getStatusTagType(trade.status)"
          size="small"
          effect="plain"
        >
          {{ trade.status.toUpperCase() }}
        </el-tag>
        <span class="expiry" v-if="trade.expiry_date">
          Exp: {{ formatDate(trade.expiry_date) }}
        </span>
      </div>
    </div>

    <!-- Legs Table -->
    <div class="card-content">
      <LegStatsTable :legs="trade.legs" />
    </div>

    <!-- Summary Footer -->
    <TradeStatsSummary
      :ticker="trade.ticker"
      :summary="trade.summary"
    />
  </el-card>
</template>

<script setup lang="ts">
import type { DetailedTrade } from '@/types/trades'
import LegStatsTable from './LegStatsTable.vue'
import TradeStatsSummary from './TradeStatsSummary.vue'
import { formatDateString } from '@/utils/dateUtils'

defineProps<{
  trade: DetailedTrade
}>()

const getStrategyTagType = (_strategy: string) => ''

const getStatusTagType = (status: string) => {
  const types: Record<string, string> = {
    open: 'info',
    closed: 'success',
    partial: 'warning',
  }
  return types[status] || ''
}

const formatStrategy = (strategy: string) => {
  return strategy.charAt(0).toUpperCase() + strategy.slice(1).toLowerCase()
}

const formatDate = (dateStr: string) => {
  return formatDateString(dateStr, {
    month: 'short',
    day: 'numeric'
  })
}
</script>

<style scoped>
.trade-stats-card {
  --card-bg: var(--bg-secondary);
  --card-border: var(--border-color);

  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  overflow: visible;
  min-height: 200px;
  display: flex;
  flex-direction: column;
}

.trade-stats-card :deep(.el-card__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
  min-height: 100px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-tertiary);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.trade-id {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--text-muted);
}

.ticker {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--accent-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.expiry {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.card-content {
  padding: var(--spacing-lg);
}
</style>

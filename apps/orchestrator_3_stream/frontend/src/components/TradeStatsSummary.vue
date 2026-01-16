<template>
  <div class="trade-stats-summary">
    <div class="summary-row">
      <div class="summary-cell label">
        <span class="ticker">{{ ticker }}</span>
        <span class="total-label">TOTAL</span>
      </div>

      <div class="summary-cell">
        <span class="value">{{ formatMoney(summary.opening_credit) }}</span>
        <span class="sublabel">opening</span>
      </div>

      <div class="summary-cell">
        <span class="value">{{ formatMoney(summary.closing_debit) }}</span>
        <span class="sublabel">closing</span>
      </div>

      <div class="summary-cell">
        <span class="value" :class="getPnlClass(summary.net_pnl_per_contract)">
          {{ formatPnlPerShare(summary.net_pnl_per_contract) }}
        </span>
      </div>

      <div class="summary-cell pnl-cell">
        <span class="value pnl-total" :class="getPnlClass(summary.net_pnl_total)">
          {{ formatMoney(summary.net_pnl_total) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TradeSummary } from '@/types/trades'

defineProps<{
  ticker: string
  summary: TradeSummary
}>()

const getPnlClass = (value: number) => {
  if (value > 0) return 'positive'
  if (value < 0) return 'negative'
  return 'neutral'
}

const formatMoney = (value: number) => {
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${Math.abs(value).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  })}`
}

const formatPnlPerShare = (value: number) => {
  if (value === 0) return '$0.00'
  const sign = value > 0 ? '+' : ''
  return `${sign}$${value.toFixed(2)}`
}
</script>

<style scoped>
.trade-stats-summary {
  background: var(--bg-tertiary);
  border-top: 1px solid var(--border-color);
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom-left-radius: 12px;
  border-bottom-right-radius: 12px;
}

.summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-lg);
}

.summary-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.summary-cell.label {
  flex-direction: row;
  gap: var(--spacing-sm);
  flex: 1;
}

.ticker {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--accent-primary);
}

.total-label {
  font-weight: 700;
  color: var(--text-primary);
  text-transform: uppercase;
}

.value {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.sublabel {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: lowercase;
}

.pnl-cell {
  min-width: 120px;
  text-align: right;
}

.pnl-total {
  font-size: 1.1rem;
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

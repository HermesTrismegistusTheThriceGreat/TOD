<template>
  <div class="leg-stats-table">
    <el-table
      :data="legs"
      class="legs-table"
      :header-cell-style="headerStyle"
      :cell-style="cellStyle"
    >
      <el-table-column label="Leg" width="120" align="center">
        <template #default="{ row }">
          <span class="leg-description">{{ row.description }}</span>
        </template>
      </el-table-column>

      <el-table-column label="Open Action" width="120" align="center">
        <template #default="{ row }">
          <span :class="getActionClass(row.open_action)">
            {{ row.open_action }} to open
          </span>
        </template>
      </el-table-column>

      <el-table-column label="Open Fill" width="100" align="right">
        <template #default="{ row }">
          <span class="fill-price">{{ formatPrice(row.open_fill) }}</span>
        </template>
      </el-table-column>

      <el-table-column label="Close Action" width="120" align="center">
        <template #default="{ row }">
          <span v-if="row.close_action" :class="getActionClass(row.close_action)">
            {{ row.close_action }} to close
          </span>
          <span v-else class="text-muted">—</span>
        </template>
      </el-table-column>

      <el-table-column label="Close Fill" width="100" align="right">
        <template #default="{ row }">
          <span v-if="row.close_fill !== null" class="fill-price">
            {{ formatPrice(row.close_fill) }}
          </span>
          <span v-else class="text-muted">—</span>
        </template>
      </el-table-column>

      <el-table-column label="P&L/Share" width="110" align="right">
        <template #default="{ row }">
          <span :class="getPnlClass(row.pnl_per_contract)">
            {{ formatPnlPerShare(row.pnl_per_contract) }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="P&L Total" width="130" align="right">
        <template #default="{ row }">
          <span :class="getPnlClass(row.pnl_total)" class="pnl-total">
            {{ formatMoney(row.pnl_total) }}
          </span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import type { LegDetail } from '@/types/trades'

defineProps<{
  legs: LegDetail[]
}>()

const headerStyle = {
  background: 'var(--bg-tertiary)',
  borderBottom: '1px solid var(--border-color)',
  color: 'var(--text-muted)',
  fontWeight: '600',
  fontSize: '0.75rem',
  textTransform: 'uppercase'
}

const cellStyle = {
  background: 'var(--bg-secondary)',
  borderBottom: '1px solid var(--border-light)'
}

const getActionClass = (action: string) => {
  return action === 'SELL' ? 'action-sell' : 'action-buy'
}

const getPnlClass = (value: number) => {
  if (value > 0) return 'positive'
  if (value < 0) return 'negative'
  return 'neutral'
}

const formatPrice = (value: number) => {
  return `$${value.toFixed(2)}`
}

const formatPnlPerShare = (value: number) => {
  if (value === 0) return '$0.00'
  const sign = value > 0 ? '+' : ''
  return `${sign}$${value.toFixed(2)}`
}

const formatMoney = (value: number) => {
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${Math.abs(value).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  })}`
}
</script>

<style scoped>
.leg-stats-table {
  width: 100%;
  margin-bottom: var(--spacing-sm);
}
 
.legs-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: var(--bg-tertiary);
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.03);
  --el-table-border-color: var(--border-light);
  
  border: 1px solid var(--border-light);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.1);
}

.leg-description {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.9rem;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.action-sell {
  color: #ff9f43; /* More vibrant orange */
  font-weight: 600;
  font-size: 0.8rem;
  letter-spacing: 0.02em;
}

.action-buy {
  color: #4834d4; /* More vibrant blue-purple */
  font-weight: 600;
  font-size: 0.8rem;
  letter-spacing: 0.02em;
}

.fill-price {
  font-family: var(--font-mono);
  color: var(--text-primary);
  font-weight: 500;
}

.positive {
  color: var(--status-success);
  font-weight: 600;
}

.negative {
  color: var(--status-error);
  font-weight: 600;
}

.neutral {
  color: var(--text-muted);
}

.text-muted {
  color: var(--text-muted);
  font-style: italic;
}

.pnl-total {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1rem;
}
</style>

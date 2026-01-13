<template>
  <div class="calendar-page">
    <el-calendar ref="calendar">
      <template #header="{ date }">
        <div class="custom-header">
          <span>{{ date }}</span>
          <div class="header-actions">
            <!-- Add any custom header actions here if needed -->
          </div>
        </div>
      </template>
      <template #date-cell="{ data }">
        <div class="calendar-cell" :class="{ 'has-events': getPositionsForDate(data.day).length > 0 }">
          <div class="day-number">{{ data.day.split('-').slice(2).join('') }}</div>
          <div class="events-container">
            <div
              v-for="position in getPositionsForDate(data.day)"
              :key="position.id"
              class="calendar-event"
              @click.stop="handlePositionClick(position)"
            >
              <div class="event-content">
                <span class="ticker">{{ position.ticker }}</span>
                <span class="strategy">{{ position.strategy }}</span>
              </div>
              <div class="event-pnl" :class="getPnlClass(position.totalPnl)">
                {{ formatMoney(position.totalPnl) }}
              </div>
            </div>
          </div>
        </div>
      </template>
    </el-calendar>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useOrchestratorStore } from '../stores/orchestratorStore'
import type { OpenPosition } from '../types/alpaca'

const store = useOrchestratorStore()

// Group positions by expiry date
const positionsByDate = computed(() => {
  const map = new Map<string, OpenPosition[]>()
  
  for (const position of store.alpacaPositions) {
    // Assuming expiryDate is in YYYY-MM-DD format
    if (!position.expiryDate) continue
    
    if (!map.has(position.expiryDate)) {
      map.set(position.expiryDate, [])
    }
    map.get(position.expiryDate)?.push(position)
  }
  
  return map
})

const getPositionsForDate = (date: string) => {
  return positionsByDate.value.get(date) || []
}

const getPnlClass = (pnl?: number) => {
  if (!pnl) return 'neutral'
  return pnl >= 0 ? 'positive' : 'negative'
}

const formatMoney = (val?: number) => {
  if (val === undefined) return '$0.00'
  return val.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
  })
}

const handlePositionClick = (position: OpenPosition) => {
  // Could navigate to detailed view or show a modal
  console.log('Clicked position:', position)
}

</script>

<style scoped>
.calendar-page {
  height: 100%;
  overflow: auto;
  padding: var(--spacing-md);
  background-color: var(--bg-primary);
}

:deep(.el-calendar) {
  background-color: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
  --el-calendar-border: var(--border-color);
  --el-calendar-cell-width: 100%;
}

:deep(.el-calendar__header) {
  border-bottom: 1px solid var(--border-color);
  padding: var(--spacing-md);
}

:deep(.el-calendar__title) {
  color: var(--text-primary);
  font-weight: 600;
}

:deep(.el-calendar__body) {
  padding: 0;
}

:deep(.el-calendar-table) {
  border-spacing: 0;
}

:deep(.el-calendar-table td) {
  border: 1px solid var(--border-color);
  transition: background-color 0.2s;
}

:deep(.el-calendar-table td:hover) {
  background-color: var(--bg-tertiary);
}

:deep(.el-calendar-table td.is-selected) {
  background-color: var(--bg-tertiary);
}

:deep(.el-calendar-table .el-calendar-day) {
  height: 120px;
  padding: 4px;
}

/* Custom cell styling */
.calendar-cell {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.day-number {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: 4px;
  text-align: right;
  padding-right: 4px;
}

.events-container {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.calendar-event {
  background-color: var(--bg-quaternary);
  border-radius: 4px;
  padding: 2px 4px;
  cursor: pointer;
  border-left: 2px solid var(--accent-primary);
  font-size: 0.7rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: transform 0.1s;
}

.calendar-event:hover {
  transform: translateX(1px);
  background-color: var(--bg-hover);
}

.event-content {
  display: flex;
  gap: 4px;
  color: var(--text-primary);
  font-weight: 500;
}

.ticker {
  font-weight: 700;
}

.event-pnl {
  font-size: 0.65rem;
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
</style>

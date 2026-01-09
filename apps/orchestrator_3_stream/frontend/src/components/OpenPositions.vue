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

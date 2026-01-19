<template>
  <div class="open-positions">
    <!-- Header with refresh button -->
    <div class="open-positions-header">
      <h2>Open Positions</h2>
      <div class="header-actions">
        <el-button
          :icon="Refresh"
          circle
          size="small"
          :loading="loading"
          @click="handleRefresh"
          title="Refresh positions"
        />
        <span class="position-count">{{ displayCount }}</span>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && !hasPositions" class="state-container loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <span>Loading positions from Alpaca...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="state-container error-state">
      <el-icon :size="32"><Warning /></el-icon>
      <span class="error-message">{{ error }}</span>
      <el-button type="primary" size="small" @click="handleRefresh">
        Retry
      </el-button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!hasPositions" class="state-container empty-state">
      <span>No open option positions</span>
      <el-button type="primary" size="small" @click="handleRefresh">
        Check Again
      </el-button>
    </div>

    <!-- Positions Grid -->
    <div v-else class="positions-grid">
      <OpenPositionCard
        v-for="position in positions"
        :key="position.id"
        :initial-data="position"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Loading, Warning, Refresh } from "@element-plus/icons-vue";
import OpenPositionCard from "./OpenPositionCard.vue";
import { useAlpacaPositions } from "../composables/useAlpacaPositions";

// Use the Alpaca positions composable
const { positions, loading, error, hasPositions, positionCount, refresh } =
  useAlpacaPositions({
    autoFetch: true,
    autoSubscribe: true,
  });

// Computed for display
const displayCount = computed(() => {
  if (loading.value) return "...";
  return `${positionCount.value} position${positionCount.value !== 1 ? "s" : ""}`;
});

// Refresh handler with loading feedback
const handleRefresh = async () => {
  await refresh();
};
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.position-count {
  font-size: 0.75rem;
  color: var(--text-muted);
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
  color: var(--el-color-primary);
}

.error-state {
  color: var(--el-color-danger);
}

.error-state .error-message {
  max-width: 400px;
  text-align: center;
  line-height: 1.5;
}

.empty-state {
  color: var(--text-muted);
}

/* Positions Stack */
.positions-grid {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

/* Scrollbar styling */
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

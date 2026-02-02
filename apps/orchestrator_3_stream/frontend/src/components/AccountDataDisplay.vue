<template>
  <el-card class="account-data-display" shadow="hover" :body-style="{ padding: '12px 16px' }">
    <!-- Header with account type badge -->
    <template #header>
      <div class="card-header">
        <span class="header-title">Active Account</span>
        <el-badge
          v-if="accountData && !accountDataLoading"
          :value="accountData.account_type.toUpperCase()"
          :type="accountTypeBadgeType"
          class="account-type-badge"
        />
      </div>
    </template>

    <!-- Loading skeleton -->
    <el-skeleton v-if="accountDataLoading" :rows="2" animated />

    <!-- Account metrics -->
    <div v-else-if="accountData" class="account-metrics">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-statistic title="Balance" :value="formattedBalance" :precision="2">
            <template #prefix>$</template>
          </el-statistic>
        </el-col>
        <el-col :span="8">
          <el-statistic title="Equity" :value="formattedEquity" :precision="2">
            <template #prefix>$</template>
          </el-statistic>
        </el-col>
        <el-col :span="8">
          <el-statistic title="Buying Power" :value="formattedBuyingPower" :precision="2">
            <template #prefix>$</template>
          </el-statistic>
        </el-col>
      </el-row>

      <!-- Account status alerts -->
      <div v-if="accountData.trading_blocked || accountData.account_blocked || accountData.pattern_day_trader" class="account-alerts">
        <el-alert
          v-if="accountData.trading_blocked"
          title="Trading Blocked"
          type="error"
          :closable="false"
          show-icon
          class="status-alert"
        />
        <el-alert
          v-if="accountData.account_blocked"
          title="Account Blocked"
          type="error"
          :closable="false"
          show-icon
          class="status-alert"
        />
        <el-alert
          v-if="accountData.pattern_day_trader"
          :title="`Pattern Day Trader (${accountData.daytrade_count}/4 day trades)`"
          type="warning"
          :closable="false"
          show-icon
          class="status-alert"
        />
      </div>
    </div>

    <!-- Empty state - no credential selected -->
    <div v-else class="empty-state">
      <el-text type="info">No account connected</el-text>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAccountStore } from '@/stores/accountStore'

const store = useAccountStore()

// Reactive state from store
const accountData = computed(() => store.accountData)
const accountDataLoading = computed(() => store.accountDataLoading)

// Badge type: warning for paper, danger for live
const accountTypeBadgeType = computed(() => {
  if (!accountData.value) return 'info'
  return accountData.value.account_type === 'paper' ? 'warning' : 'danger'
})

// Format currency values (convert string to number)
const formattedBalance = computed(() => {
  if (!accountData.value) return 0
  return parseFloat(accountData.value.balance)
})

const formattedEquity = computed(() => {
  if (!accountData.value) return 0
  return parseFloat(accountData.value.equity)
})

const formattedBuyingPower = computed(() => {
  if (!accountData.value) return 0
  return parseFloat(accountData.value.buying_power)
})
</script>

<style scoped>
.account-data-display {
  width: 100%;
  min-width: 320px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0;
}

.header-title {
  font-weight: 600;
  font-size: 14px;
}

.account-type-badge {
  margin-left: auto;
}

.account-metrics {
  padding: 8px 0;
}

.account-alerts {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-alert {
  margin: 0;
}

.empty-state {
  text-align: center;
  padding: 16px;
}

/* Override Element Plus statistic styling for compact display */
:deep(.el-statistic__head) {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

:deep(.el-statistic__content) {
  font-size: 18px;
}

/* Mobile responsive styles */
@media (max-width: 650px) {
  .account-data-display {
    min-width: auto;
  }

  .card-header {
    font-size: 0.7rem;
  }

  .header-title {
    font-size: 0.7rem;
  }

  .account-type-badge {
    font-size: 0.65rem;
  }

  .account-metrics {
    padding: 4px 0;
  }

  :deep(.el-statistic__head) {
    font-size: 0.65rem;
  }

  :deep(.el-statistic__content) {
    font-size: 0.875rem;
  }

  .account-alerts {
    margin-top: 8px;
  }

  :deep(.el-alert) {
    padding: 6px 8px;
    font-size: 0.65rem;
  }

  :deep(.el-alert__title) {
    font-size: 0.65rem;
  }
}
</style>

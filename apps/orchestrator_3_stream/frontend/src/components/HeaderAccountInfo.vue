<template>
  <div class="header-account-info" v-if="store.hasCredentials">
    <!-- Account Selector (compact) -->
    <div class="account-selector-compact">
      <el-select
        v-model="selectedId"
        :loading="store.isLoading"
        placeholder="Account"
        size="small"
        class="compact-select"
        @change="handleChange"
      >
        <el-option
          v-for="cred in store.alpacaCredentials"
          :key="cred.id"
          :label="formatLabel(cred)"
          :value="cred.id"
        >
          <div class="option-content">
            <span class="option-name">{{ formatLabel(cred) }}</span>
          </div>
        </el-option>
      </el-select>
    </div>

    <!-- Separator -->
    <div class="info-separator"></div>

    <!-- Buying Power Metric (inline badge style) -->
    <div class="metric-display" v-if="store.accountData && !store.accountDataLoading">
      <span class="metric-label">BP</span>
      <span class="metric-value">{{ formattedBuyingPower }}</span>
    </div>

    <!-- Loading indicator for account data -->
    <div class="metric-display metric-loading" v-else-if="store.accountDataLoading">
      <span class="metric-label">BP</span>
      <span class="metric-value">...</span>
    </div>

    <!-- Account Type Badge -->
    <span
      v-if="store.accountData && !store.accountDataLoading"
      class="account-badge"
      :class="accountType"
    >
      {{ accountType.toUpperCase() }}
    </span>
  </div>

  <!-- Empty state when no credentials -->
  <div class="header-account-info empty" v-else-if="!store.hasCredentials && !store.isLoading">
    <span class="empty-text">No account</span>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useAccountStore } from '@/stores/accountStore'
import type { CredentialResponse } from '@/types/account'

// Store
const store = useAccountStore()

// Selected ID with getter/setter
const selectedId = computed({
  get: () => store.activeCredentialId || '',
  set: (value: string) => {
    if (value) {
      store.setActiveCredential(value)
    }
  }
})

// Account type from account data
const accountType = computed(() => {
  if (!store.accountData) return 'paper'
  return store.accountData.account_type || 'paper'
})

// Format buying power with currency
const formattedBuyingPower = computed(() => {
  if (!store.accountData) return '$0'
  const value = parseFloat(store.accountData.buying_power)
  return formatCurrency(value)
})

// Format currency value
function formatCurrency(value: number): string {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(2)}M`
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`
  }
  return `$${value.toFixed(2)}`
}

// Format label for dropdown - use nickname or fallback
function formatLabel(cred: CredentialResponse): string {
  if (cred.nickname && cred.nickname !== cred.credential_type) {
    return cred.nickname
  }
  const type = cred.credential_type.charAt(0).toUpperCase() + cred.credential_type.slice(1)
  return type
}

// Handle change
function handleChange() {
  console.log('[HeaderAccountInfo] Active credential changed to:', selectedId.value)
}

// Load active credential from localStorage on mount
onMounted(() => {
  store.loadActiveCredential()
})
</script>

<style scoped>
.header-account-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm, 8px);
  padding: 0.375rem 0.75rem;
  background: var(--bg-tertiary, #2a2a2a);
  border: 1px solid var(--border-color, #333);
  border-radius: 8px;
  transition: all 0.2s ease;
}

.header-account-info:hover {
  border-color: var(--border-light, #444);
}

.header-account-info.empty {
  padding: 0.375rem 0.75rem;
}

.empty-text {
  font-size: 0.75rem;
  color: var(--text-muted, #666);
  font-weight: 500;
}

/* Compact Account Selector */
.account-selector-compact {
  display: inline-block;
  min-width: 80px;
  max-width: 140px;
}

.compact-select {
  width: 100%;
}

/* Element Plus Select Overrides for compact display */
:deep(.el-select .el-input__wrapper) {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 0;
  min-height: auto;
}

:deep(.el-select .el-input__wrapper:hover) {
  background: transparent;
}

:deep(.el-select .el-input__wrapper.is-focus) {
  box-shadow: none;
}

:deep(.el-select .el-input__inner) {
  color: var(--text-primary, #e5e5e5);
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0;
  height: auto;
  line-height: 1.4;
}

:deep(.el-select .el-input__inner::placeholder) {
  color: var(--text-muted, #666);
}

:deep(.el-select__caret) {
  color: var(--text-muted, #666);
  font-size: 12px;
}

:deep(.el-select .el-input__suffix) {
  right: 0;
}

/* Dropdown menu styling */
:deep(.el-select-dropdown) {
  background: var(--bg-secondary, #1a1a1a);
  border: 1px solid var(--border-color, #333);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

:deep(.el-select-dropdown__item) {
  background: var(--bg-secondary, #1a1a1a);
  color: var(--text-secondary, #a1a1a1);
  font-size: 0.75rem;
  padding: 8px 12px;
  transition: all 0.2s ease;
}

:deep(.el-select-dropdown__item:hover) {
  background: var(--bg-tertiary, #2a2a2a);
  color: var(--text-primary, #e5e5e5);
}

:deep(.el-select-dropdown__item.is-selected) {
  background: var(--accent-primary, #06b6d4);
  color: white;
  font-weight: 600;
}

/* Option content */
.option-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.option-name {
  font-weight: 500;
}

/* Info Separator */
.info-separator {
  width: 1px;
  height: 20px;
  background: var(--border-color, #333);
  flex-shrink: 0;
}

/* Metric Display - Badge Style */
.metric-display {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  padding: 0 var(--spacing-xs, 4px);
  min-width: 60px;
}

.metric-display.metric-loading {
  opacity: 0.5;
}

.metric-label {
  font-size: 0.6rem;
  color: var(--text-muted, #666);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  line-height: 1;
}

.metric-value {
  font-size: 0.8rem;
  font-weight: 700;
  font-family: var(--font-mono, 'SF Mono', 'Monaco', monospace);
  color: var(--status-success, #10b981);
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

/* Account Type Badge */
.account-badge {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}

.account-badge.paper {
  background: rgba(245, 158, 11, 0.15);
  color: var(--status-warning, #f59e0b);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.account-badge.live {
  background: rgba(239, 68, 68, 0.15);
  color: var(--status-error, #ef4444);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

/* Responsive - hide on mobile (will be in mobile menu) */
@media (max-width: 768px) {
  .header-account-info {
    display: none;
  }
}
</style>

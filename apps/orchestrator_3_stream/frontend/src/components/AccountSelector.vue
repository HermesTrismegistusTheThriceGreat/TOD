<template>
  <div class="account-selector">
    <el-select
      v-model="selectedId"
      :loading="store.isLoading"
      placeholder="Select account"
      size="small"
      @change="handleChange"
      class="account-select"
    >
      <el-option
        v-for="cred in store.alpacaCredentials"
        :key="cred.id"
        :label="formatLabel(cred)"
        :value="cred.id"
      />

      <!-- Show message if no credentials -->
      <template v-if="store.alpacaCredentials.length === 0" #empty>
        <div class="empty-state">
          <span>No accounts connected</span>
        </div>
      </template>
    </el-select>
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

// Format label for dropdown
function formatLabel(cred: CredentialResponse): string {
  const type = cred.credential_type.charAt(0).toUpperCase() + cred.credential_type.slice(1)
  const date = new Date(cred.created_at)
  const formattedDate = date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
  return `${type} - ${formattedDate}`
}

// Handle change (optional - store already handles persistence)
function handleChange() {
  console.log('[AccountSelector] Active credential changed to:', selectedId.value)
}

// Load active credential from localStorage on mount
onMounted(() => {
  store.loadActiveCredential()
})
</script>

<style scoped>
.account-selector {
  display: inline-block;
  max-width: 200px;
}

.account-select {
  width: 100%;
}

/* Element Plus Select Overrides */
:deep(.el-select .el-input__wrapper) {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  box-shadow: none;
  transition: all 0.2s ease;
}

:deep(.el-select .el-input__wrapper:hover) {
  border-color: var(--accent-primary);
}

:deep(.el-select .el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(6, 182, 212, 0.1);
}

:deep(.el-select .el-input__inner) {
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 500;
}

:deep(.el-select .el-input__inner::placeholder) {
  color: var(--text-muted);
  opacity: 0.7;
}

:deep(.el-select__caret) {
  color: var(--text-muted);
}

:deep(.el-select .el-input__suffix) {
  color: var(--text-muted);
}

/* Dropdown menu styling */
:deep(.el-select-dropdown) {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

:deep(.el-select-dropdown__item) {
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 0.75rem;
  padding: 8px 12px;
  transition: all 0.2s ease;
}

:deep(.el-select-dropdown__item:hover) {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

:deep(.el-select-dropdown__item.is-selected) {
  background: var(--accent-primary);
  color: white;
  font-weight: 600;
}

/* Empty state */
.empty-state {
  padding: 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.75rem;
}

/* Loading state */
:deep(.el-select .el-icon.is-reverse) {
  color: var(--accent-primary);
}
</style>

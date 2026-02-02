<template>
  <div class="account-list-page">
    <!-- App Header for Navigation -->
    <AppHeader />

    <div class="account-list-view">
      <!-- Page Header -->
      <div class="account-list-header">
        <div class="header-left">
          <h2>Connected Accounts</h2>
        </div>
        <div class="header-actions">
          <el-button type="primary" @click="showAddDialog">
            Add Account
          </el-button>
        </div>
      </div>

      <!-- Error State -->
      <el-alert
        v-if="store.error"
        type="error"
        :closable="false"
        class="error-alert"
        show-icon
      >
        <template #default>
          <div class="error-content">
            <span>{{ store.error }}</span>
            <el-button size="small" @click="handleRetry">Retry</el-button>
          </div>
        </template>
      </el-alert>

      <!-- Loading State -->
      <div v-if="store.isLoading && store.credentials.length === 0" class="state-container">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <span>Loading accounts...</span>
      </div>

      <!-- Empty State -->
      <div v-else-if="!store.isLoading && store.credentials.length === 0" class="state-container">
        <el-empty description="No accounts connected yet">
          <el-button type="primary" @click="showAddDialog">
            Add Your First Account
          </el-button>
        </el-empty>
      </div>

      <!-- Credentials Table -->
      <div v-else class="table-container">
        <el-table
          :data="store.credentials"
          :loading="store.isLoading"
          style="width: 100%"
          class="credentials-table"
          :header-cell-style="{ background: 'var(--bg-tertiary)', borderBottom: '1px solid var(--border-color)' }"
          :cell-style="{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-light)' }"
        >
          <el-table-column prop="nickname" label="NICKNAME" min-width="140">
            <template #default="{ row }">
              <span class="credential-nickname">
                {{ getDisplayName(row) }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="credential_type" label="TYPE" width="100">
            <template #default="{ row }">
              <span class="credential-type">
                {{ formatCredentialType(row.credential_type) }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="BALANCE" min-width="140">
            <template #default="{ row }">
              <span v-if="loadingAccountData.has(row.id)" class="balance-loading">
                <el-icon class="is-loading" :size="14"><Loading /></el-icon>
              </span>
              <span v-else class="balance-value">
                {{ formatBalance(getAccountData(row.id)?.equity) }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="STATUS" width="100">
            <template #default="{ row }">
              <el-tag
                :type="row.is_active ? 'success' : 'info'"
                size="small"
                effect="light"
              >
                {{ row.is_active ? 'Active' : 'Inactive' }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="created_at" label="ADDED" width="130">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>

          <el-table-column label="ACTIONS" width="220" align="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button
                  size="small"
                  @click="handleEdit(row)"
                >
                  Edit
                </el-button>
                <el-button
                  size="small"
                  :loading="validatingId === row.id"
                  @click="handleValidate(row)"
                >
                  Test
                </el-button>
                <el-button
                  size="small"
                  type="danger"
                  @click="handleDelete(row)"
                >
                  Remove
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Account Manager Dialog -->
      <AccountManagerDialog
        v-model:visible="dialogVisible"
        :credentialId="editingCredentialId"
        @success="handleDialogSuccess"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { useAccountStore } from '@/stores/accountStore'
import credentialService from '@/services/credentialService'
import AccountManagerDialog from './AccountManagerDialog.vue'
import AppHeader from './AppHeader.vue'
import type { CredentialResponse, AccountDataResponse } from '@/types/account'

// Store
const store = useAccountStore()

// State
const dialogVisible = ref(false)
const editingCredentialId = ref<string | null>(null)
const validatingId = ref<string | null>(null)

// Account data cache (credential_id -> account data)
const accountDataCache = reactive<Map<string, AccountDataResponse>>(new Map())
const loadingAccountData = reactive<Set<string>>(new Set())

// Format credential type for display
function formatCredentialType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1)
}

// Format date
function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

// Format currency for balance display
function formatBalance(balance: string | undefined): string {
  if (!balance) return '-'
  const num = parseFloat(balance)
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num)
}

// Get display name for credential (nickname or fallback)
function getDisplayName(credential: CredentialResponse): string {
  return credential.nickname || formatCredentialType(credential.credential_type)
}

// Fetch account data for a credential
async function fetchAccountData(credentialId: string): Promise<void> {
  if (accountDataCache.has(credentialId) || loadingAccountData.has(credentialId)) {
    return
  }

  loadingAccountData.add(credentialId)
  try {
    const data = await credentialService.getAccountData(credentialId)
    accountDataCache.set(credentialId, data)
  } catch (error) {
    console.error(`[AccountListView] Failed to fetch account data for ${credentialId}:`, error)
  } finally {
    loadingAccountData.delete(credentialId)
  }
}

// Get cached account data for a credential
function getAccountData(credentialId: string): AccountDataResponse | undefined {
  return accountDataCache.get(credentialId)
}

// Show add dialog
function showAddDialog() {
  editingCredentialId.value = null
  dialogVisible.value = true
}

// Handle edit
function handleEdit(credential: CredentialResponse) {
  editingCredentialId.value = credential.id
  dialogVisible.value = true
}

// Handle validate
async function handleValidate(credential: CredentialResponse) {
  validatingId.value = credential.id
  try {
    const result = await credentialService.validateCredential(credential.id)

    if (result.is_valid) {
      ElMessage.success({
        message: `${formatCredentialType(credential.credential_type)} credentials are valid`,
        duration: 3000
      })

      // Show account type if available
      if (result.account_type) {
        ElMessage.info({
          message: `Account type: ${result.account_type}`,
          duration: 3000
        })
      }
    } else {
      ElMessage.warning({
        message: `Invalid credentials: ${result.error || 'Unknown error'}`,
        duration: 5000
      })
    }
  } catch (error) {
    ElMessage.error({
      message: error instanceof Error ? error.message : 'Validation failed',
      duration: 5000
    })
  } finally {
    validatingId.value = null
  }
}

// Handle delete
async function handleDelete(credential: CredentialResponse) {
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to remove this ${formatCredentialType(credential.credential_type)} account? This action cannot be undone.`,
      'Delete Account',
      {
        type: 'warning',
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel'
      }
    )

    // User confirmed, proceed with deletion
    await store.removeCredential(credential.id)
    ElMessage.success('Account removed successfully')
  } catch (error) {
    // User cancelled or error occurred
    if (error === 'cancel') {
      // User cancelled, do nothing
      return
    }

    ElMessage.error(
      error instanceof Error ? error.message : 'Failed to remove account'
    )
  }
}

// Handle dialog success
function handleDialogSuccess() {
  // Credentials are already updated in store by the dialog
  // Just log for debugging
  console.log('[AccountListView] Dialog operation successful')
}

// Handle retry
async function handleRetry() {
  if (!store.userAccount?.id) {
    await store.initialize()
  } else {
    await store.fetchCredentials()
  }
}

// Initialize on mount
onMounted(async () => {
  // Only initialize if not already initialized
  if (!store.isInitialized) {
    try {
      await store.initialize()
    } catch (error) {
      console.error('[AccountListView] Failed to initialize store:', error)
    }
  }

  // Fetch account data for all credentials
  for (const credential of store.credentials) {
    fetchAccountData(credential.id)
  }
})
</script>

<style scoped>
/* Page wrapper - full screen with header */
.account-list-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  overflow: hidden;
}

/* Content area below header */
.account-list-view {
  flex: 1;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Page Header */
.account-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.header-left h2 {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-primary);
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: var(--spacing-sm);
}

/* Error Alert */
.error-alert {
  margin: var(--spacing-md) var(--spacing-lg);
  flex-shrink: 0;
}

.error-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: var(--spacing-md);
}

:deep(.el-alert) {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--status-error);
}

:deep(.el-alert__content) {
  flex: 1;
}

/* State Container */
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

.state-container .el-icon {
  color: var(--accent-primary);
}

/* Table Container */
.table-container {
  flex: 1;
  overflow: hidden;
  padding: var(--spacing-lg);
}

.credentials-table {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  --el-table-border-color: var(--border-color);
  --el-table-header-text-color: var(--text-muted);
  --el-table-text-color: var(--text-primary);
}

.credential-type {
  font-weight: 600;
  color: var(--accent-primary);
  text-transform: capitalize;
}

.credential-nickname {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 0.875rem;
}

.balance-value {
  font-weight: 600;
  color: var(--status-success);
  font-family: var(--font-mono);
  font-size: 0.875rem;
}

.balance-loading {
  display: inline-flex;
  align-items: center;
  color: var(--text-muted);
}

/* Action Buttons */
.action-buttons {
  display: flex;
  gap: var(--spacing-xs);
  justify-content: flex-end;
}

/* Element Plus Overrides */
:deep(.el-button) {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 0.75rem;
}

:deep(.el-button:hover) {
  background: var(--bg-quaternary);
  border-color: var(--accent-primary);
  color: var(--text-primary);
}

:deep(.el-button--primary) {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: white;
}

:deep(.el-button--primary:hover) {
  background: #0891b2;
  border-color: #0891b2;
  color: white;
}

:deep(.el-button--danger) {
  background: transparent;
  border-color: var(--status-error);
  color: var(--status-error);
}

:deep(.el-button--danger:hover) {
  background: var(--status-error);
  border-color: var(--status-error);
  color: white;
}

:deep(.el-button--small) {
  padding: 4px 10px;
  font-size: 0.7rem;
}

:deep(.el-tag) {
  font-weight: 600;
  font-size: 0.7rem;
  letter-spacing: 0.025em;
  border: none;
}

:deep(.el-tag--success) {
  background: rgba(16, 185, 129, 0.15);
  color: var(--status-success);
}

:deep(.el-tag--info) {
  background: rgba(107, 114, 128, 0.15);
  color: var(--text-muted);
}

/* Empty state styling */
:deep(.el-empty) {
  padding: 0;
}

:deep(.el-empty__description) {
  color: var(--text-muted);
  margin-top: var(--spacing-md);
}

/* Scrollbar styling */
:deep(.el-table__body-wrapper::-webkit-scrollbar) {
  width: 6px;
}

:deep(.el-table__body-wrapper::-webkit-scrollbar-track) {
  background: transparent;
}

:deep(.el-table__body-wrapper::-webkit-scrollbar-thumb) {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

:deep(.el-table__body-wrapper::-webkit-scrollbar-thumb:hover) {
  background: rgba(255, 255, 255, 0.15);
}

/* Message Box overrides */
:deep(.el-message-box) {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
}

:deep(.el-message-box__title) {
  color: var(--text-primary);
}

:deep(.el-message-box__content) {
  color: var(--text-secondary);
}
</style>

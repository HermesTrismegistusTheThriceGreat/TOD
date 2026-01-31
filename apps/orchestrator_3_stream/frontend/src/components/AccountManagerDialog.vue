<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEditMode ? 'Edit Account' : 'Add New Account'"
    width="500px"
    @close="handleClose"
  >
    <!-- Error Alert -->
    <el-alert
      v-if="store.error"
      type="error"
      :closable="false"
      class="error-alert"
      :title="store.error"
      show-icon
    />

    <!-- Form -->
    <el-form
      ref="formRef"
      :model="formData"
      :rules="validationRules"
      label-width="120px"
      class="account-form"
    >
      <el-form-item label="Account Type" prop="credential_type">
        <el-select
          v-model="formData.credential_type"
          placeholder="Select account type"
          style="width: 100%"
        >
          <el-option label="Alpaca Trading" value="alpaca" />
        </el-select>
      </el-form-item>

      <el-form-item label="Nickname" prop="nickname">
        <el-input
          v-model="formData.nickname"
          placeholder="Paper Account 1"
          maxlength="100"
        />
        <template #extra>
          <span class="input-hint">Optional. Helps identify this account.</span>
        </template>
      </el-form-item>

      <el-form-item label="API Key" prop="api_key">
        <el-input
          v-model="formData.api_key"
          type="password"
          placeholder="PK..."
          show-password
        />
      </el-form-item>

      <el-form-item label="Secret Key" prop="secret_key">
        <el-input
          v-model="formData.secret_key"
          type="password"
          placeholder="sp..."
          show-password
        />
      </el-form-item>
    </el-form>

    <!-- Footer -->
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">Cancel</el-button>
        <el-button
          type="primary"
          :loading="store.isLoading"
          @click="handleSubmit"
        >
          {{ isEditMode ? 'Update' : 'Add' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAccountStore } from '@/stores/accountStore'
import type { CredentialInput, CredentialUpdate } from '@/types/account'

// Props
const props = defineProps<{
  visible: boolean
  credentialId?: string
}>()

// Emits
const emit = defineEmits<{
  'update:visible': [value: boolean]
  'success': []
}>()

// Store
const store = useAccountStore()

// Form ref
const formRef = ref<FormInstance>()

// Form data
const formData = ref<CredentialInput>({
  credential_type: 'alpaca',
  api_key: '',
  secret_key: '',
  nickname: ''
})

// Computed
const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const isEditMode = computed(() => !!props.credentialId)

// Validation rules
const validationRules: FormRules = {
  credential_type: [
    { required: true, message: 'Account type is required', trigger: 'change' }
  ],
  api_key: [
    { required: true, message: 'API key is required', trigger: 'blur' }
  ],
  secret_key: [
    { required: true, message: 'Secret key is required', trigger: 'blur' }
  ]
}

// Watch for dialog open/close
watch(() => props.visible, (visible) => {
  if (visible) {
    // Clear error when opening
    store.error = null

    // Load credential data if editing
    if (props.credentialId) {
      const credential = store.credentials.find(c => c.id === props.credentialId)
      if (credential) {
        formData.value = {
          credential_type: credential.credential_type,
          api_key: '', // Don't show existing API key
          secret_key: '' // Don't show existing secret
        }
      }
    } else {
      // Reset form for add mode
      resetForm()
    }
  }
})

// Reset form
function resetForm() {
  formData.value = {
    credential_type: 'alpaca',
    api_key: '',
    secret_key: '',
    nickname: ''
  }
  formRef.value?.clearValidate()
}

// Handle close
function handleClose() {
  resetForm()
  store.error = null
  emit('update:visible', false)
}

// Handle submit
async function handleSubmit() {
  if (!formRef.value) return

  try {
    // Validate form
    await formRef.value.validate()

    if (isEditMode.value && props.credentialId) {
      // Update existing credential
      const updateData: CredentialUpdate = {}
      if (formData.value.api_key) {
        updateData.api_key = formData.value.api_key
      }
      if (formData.value.secret_key) {
        updateData.secret_key = formData.value.secret_key
      }

      await store.updateCredential(props.credentialId, updateData)
      ElMessage.success('Account updated successfully')
    } else {
      // Add new credential
      await store.addCredential(formData.value)
      ElMessage.success('Account added successfully')
    }

    emit('success')
    handleClose()
  } catch (error) {
    // Error is already set in store, just show message
    ElMessage.error(
      error instanceof Error ? error.message : 'Operation failed'
    )
  }
}
</script>

<style scoped>
/* Dialog styling */
:deep(.el-dialog) {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

:deep(.el-dialog__header) {
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
  padding: var(--spacing-md) var(--spacing-lg);
}

:deep(.el-dialog__title) {
  color: var(--text-primary);
  font-size: 1rem;
  font-weight: 600;
}

:deep(.el-dialog__body) {
  background: var(--bg-secondary);
  padding: var(--spacing-lg);
}

:deep(.el-dialog__footer) {
  background: var(--bg-tertiary);
  border-top: 1px solid var(--border-color);
  padding: var(--spacing-md) var(--spacing-lg);
}

/* Error alert */
.error-alert {
  margin-bottom: var(--spacing-md);
}

:deep(.el-alert) {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--status-error);
}

:deep(.el-alert__title) {
  color: var(--status-error);
}

/* Form styling */
.account-form {
  margin-top: var(--spacing-md);
}

:deep(.el-form-item__label) {
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 0.875rem;
}

:deep(.el-input__wrapper) {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  box-shadow: none;
}

:deep(.el-input__wrapper:hover) {
  border-color: var(--accent-primary);
}

:deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(6, 182, 212, 0.1);
}

:deep(.el-input__inner) {
  color: var(--text-primary);
}

:deep(.el-input__inner::placeholder) {
  color: var(--text-muted);
}

:deep(.el-select .el-input__wrapper) {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
}

/* Footer buttons */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
}

:deep(.el-button) {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-weight: 500;
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

:deep(.el-button.is-loading) {
  opacity: 0.7;
}

/* Validation error styling */
:deep(.el-form-item.is-error .el-input__wrapper) {
  border-color: var(--status-error);
}

:deep(.el-form-item__error) {
  color: var(--status-error);
}

/* Input hint */
.input-hint {
  color: var(--text-muted);
  font-size: 0.75rem;
  margin-top: 4px;
}
</style>

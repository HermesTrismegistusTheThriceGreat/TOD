# Phase 4: Account Management UI - Research

**Researched:** 2026-01-31
**Domain:** Vue 3 Frontend UI Components & CRUD Operations (TypeScript + Axios + Element Plus)
**Confidence:** HIGH

## Summary

Phase 4 implements the frontend for account credential management built on the API endpoints completed in Phase 3. This phase bridges the gap between the secured backend credential API and user-facing UI components for adding, viewing, switching, updating, and removing Alpaca accounts.

The phase is straightforward technically because:
1. Backend endpoints are complete and tested (Phase 3 complete)
2. Existing project has established patterns for Vue 3 + Composition API + Pinia
3. Element Plus is the confirmed UI library (already in package.json as v2.13.1)
4. Axios is already configured with error interceptors
5. Project uses TypeScript throughout

The core architectural patterns are well-established in the codebase:
- Pinia stores for state management (composition API style, no modules)
- Composables for shared logic
- Services for API calls using Axios
- Element Plus components for UI (Dialog, Form, Table, Select, Button)
- Async/await with try-catch for error handling

**Key implementation insight:** This phase requires no custom form validation or complex modals—Element Plus's built-in validation and Dialog component handle all necessary flows. The focus is component composition and state management, not custom implementations.

**Primary recommendation:** Implement a dedicated credentials service in `src/services/credentialService.ts` with methods for all CRUD operations, a Pinia store in `src/stores/accountStore.ts` for managing credentials and active account state, and three UI components: `AccountManagerDialog.vue` (modal for add/edit), `AccountListView.vue` (main list), and `AccountSelector.vue` (dropdown for switching active account). Use Element Plus Form for validation, Dialog for modals, Table for list display, and Select for account switching.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vue | ^3.4.0 | Reactive UI framework | Already in use; project standard |
| Vue Router | ^4.4.0 | Client-side routing | Already in use; enables dedicated account management view |
| Pinia | ^2.1.7 | State management | Official Vue 3 store; composition API style; no modules needed |
| TypeScript | ^5.0.0 | Type safety | Already in use project-wide; required for production safety |
| Axios | ^1.6.0 | HTTP client | Already configured with error interceptors; used throughout codebase |
| Element Plus | ^2.13.1 | UI components | Already in use (confirmed in package.json); provides Dialog, Form, Table, Select, Button |

### Supporting (Element Plus Sub-components)
| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| el-dialog | 2.13.1 | Modal for add/edit forms | Add new credential, edit existing credential |
| el-form | 2.13.1 | Form validation & layout | Credential input forms with client-side validation |
| el-input | 2.13.1 | Text input with type=password | API key and secret key inputs |
| el-button | 2.13.1 | Action buttons | Save, cancel, delete, switch account actions |
| el-table | 2.13.1 | Tabular data display | List of connected Alpaca accounts with actions |
| el-select | 2.13.1 | Dropdown selector | Switch active account via dropdown |
| el-message-box | 2.13.1 | Confirmation dialog | Delete account confirmation |
| el-message | 2.13.1 | Toast notifications | Success/error feedback on CRUD operations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Element Plus | PrimeVue | PrimeVue not in package.json; requires new dependency; Element Plus already in use |
| Element Plus | Headless UI / ShadCN | Less built-in validation support; more custom code required |
| Pinia | Vuex | Pinia simpler API; Vuex adds unnecessary ceremony for this use case |
| Element Plus Dialog | Vue Final Modal | Element Plus Dialog sufficient for this phase; no need for advanced modal manager |
| Native HTML inputs | Vue Input Mask | Element Plus inputs with type=password sufficient; masking handled by browser |

**Installation:**
```bash
# Already installed in project
# If needed to reinstall dependencies:
npm install
```

## Architecture Patterns

### Recommended Project Structure

```
src/
├── services/
│   ├── credentialService.ts        # API calls for credential CRUD
│   └── api.ts                       # Already exists; Axios configured
├── stores/
│   ├── accountStore.ts              # Pinia store for credentials state
│   └── orchestratorStore.ts         # Already exists
├── components/
│   ├── AccountManagerDialog.vue     # Modal for add/edit credential
│   ├── AccountListView.vue          # Main list of accounts
│   ├── AccountSelector.vue          # Dropdown for active account selection
│   └── AppHeader.vue                # Already exists; integrate account selector
├── types/
│   ├── index.ts                     # Already exists
│   └── account.ts                   # NEW: Credential/account types (mirrors backend CredentialResponse)
├── composables/
│   ├── useAccountManager.ts         # Optional: Composable for account form state
│   └── (other existing composables)
└── views/
    └── AccountManagementView.vue    # Optional: Dedicated page for account management
```

### Pattern 1: Credential Service Layer

**What:** Dedicated service module that handles all API communication with the backend credential endpoints, keeping HTTP logic separate from UI components.

**When to use:** All credential CRUD operations (list, add, update, delete, validate) should go through this service to ensure consistent error handling and request formatting.

**Example:**
```typescript
// src/services/credentialService.ts
// Source: Existing pattern from chatService.ts and alpacaService.ts in codebase

import { apiClient } from './api'
import type { CredentialResponse, ListCredentialsResponse } from '@/types/account'

export const credentialService = {
  /**
   * List all credentials for a user account
   */
  async listCredentials(accountId: string): Promise<CredentialResponse[]> {
    const response = await apiClient.get<ListCredentialsResponse>(
      '/api/credentials',
      { params: { account_id: accountId } }
    )
    return response.data.credentials
  },

  /**
   * Store new credential with encrypted keys
   */
  async storeCredential(data: {
    account_id: string
    credential_type: string
    api_key: string
    secret_key: string
  }): Promise<CredentialResponse> {
    const response = await apiClient.post<CredentialResponse>(
      '/api/credentials/store',
      data
    )
    return response.data
  },

  /**
   * Update existing credential
   */
  async updateCredential(
    credentialId: string,
    data: {
      api_key?: string
      secret_key?: string
      is_active?: boolean
    }
  ): Promise<CredentialResponse> {
    const response = await apiClient.put<CredentialResponse>(
      `/api/credentials/${credentialId}`,
      data
    )
    return response.data
  },

  /**
   * Delete credential
   */
  async deleteCredential(credentialId: string): Promise<void> {
    await apiClient.delete(`/api/credentials/${credentialId}`)
  },

  /**
   * Validate credential against Alpaca API
   */
  async validateCredential(credentialId: string): Promise<{
    is_valid: boolean
    account_type?: string
  }> {
    const response = await apiClient.post(
      `/api/credentials/${credentialId}/validate`,
      {}
    )
    return response.data
  }
}
```

### Pattern 2: Pinia Store for Account State

**What:** Composition API-style Pinia store that manages the list of credentials, selected/active credential, and loading states. Follows existing orchestratorStore pattern in codebase.

**When to use:** Whenever any component needs access to credentials list or active account, dispatch store actions to fetch/update state.

**Example:**
```typescript
// src/stores/accountStore.ts
// Source: Pattern from existing orchestratorStore.ts (composition API style)

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { CredentialResponse } from '@/types/account'
import { credentialService } from '@/services/credentialService'

export const useAccountStore = defineStore('account', () => {
  // ═══════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════

  const credentials = ref<CredentialResponse[]>([])
  const activeCredentialId = ref<string | null>(null)
  const selectedAccountId = ref<string | null>(null) // Current user account
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // ═══════════════════════════════════════════════════════════
  // GETTERS
  // ═══════════════════════════════════════════════════════════

  const activeCredential = computed(() => {
    if (!activeCredentialId.value) return null
    return credentials.value.find(c => c.id === activeCredentialId.value) || null
  })

  // ═══════════════════════════════════════════════════════════
  // ACTIONS
  // ═══════════════════════════════════════════════════════════

  async function fetchCredentials(accountId: string) {
    isLoading.value = true
    error.value = null
    try {
      credentials.value = await credentialService.listCredentials(accountId)
      // Auto-select first active credential if any exist
      const active = credentials.value.find(c => c.is_active)
      if (active) {
        activeCredentialId.value = active.id
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load credentials'
    } finally {
      isLoading.value = false
    }
  }

  async function addCredential(data: Parameters<typeof credentialService.storeCredential>[0]) {
    isLoading.value = true
    error.value = null
    try {
      const newCredential = await credentialService.storeCredential(data)
      credentials.value.push(newCredential)
      return newCredential
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to add credential'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function updateCredential(credentialId: string, data: Parameters<typeof credentialService.updateCredential>[1]) {
    isLoading.value = true
    error.value = null
    try {
      const updated = await credentialService.updateCredential(credentialId, data)
      const index = credentials.value.findIndex(c => c.id === credentialId)
      if (index !== -1) {
        credentials.value[index] = updated
      }
      return updated
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update credential'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function deleteCredential(credentialId: string) {
    isLoading.value = true
    error.value = null
    try {
      await credentialService.deleteCredential(credentialId)
      credentials.value = credentials.value.filter(c => c.id !== credentialId)
      // Clear active if deleted
      if (activeCredentialId.value === credentialId) {
        activeCredentialId.value = credentials.value[0]?.id || null
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete credential'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function setActiveCredential(credentialId: string) {
    activeCredentialId.value = credentialId
  }

  return {
    credentials,
    activeCredentialId,
    activeCredential,
    selectedAccountId,
    isLoading,
    error,
    fetchCredentials,
    addCredential,
    updateCredential,
    deleteCredential,
    setActiveCredential
  }
})
```

### Pattern 3: Dialog Component for Add/Edit

**What:** Reusable modal dialog for adding or editing credentials. Uses Element Plus Form for client-side validation and SecretStr input handling.

**When to use:** When user clicks "Add Credential" button or clicks edit on an existing credential.

**Example:**
```typescript
// src/components/AccountManagerDialog.vue
// Source: Pattern from Element Plus Dialog docs + existing component patterns

<template>
  <el-dialog
    v-model="isVisible"
    :title="isEditing ? 'Edit Account' : 'Add New Account'"
    width="500px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="validationRules"
      label-width="120px"
      @submit.prevent
    >
      <el-form-item label="Account Type" prop="credential_type">
        <el-select v-model="formData.credential_type" placeholder="Select type">
          <el-option label="Alpaca Trading" value="alpaca" />
        </el-select>
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

    <template #footer>
      <el-button @click="handleClose">Cancel</el-button>
      <el-button
        type="primary"
        :loading="store.isLoading"
        @click="handleSubmit"
      >
        {{ isEditing ? 'Update' : 'Add' }} Account
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { useAccountStore } from '@/stores/accountStore'

interface Props {
  visible: boolean
  credentialId?: string // If provided, edit mode
}

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'success'): void
}

const props = withDefaults(defineProps<Props>(), {
  credentialId: undefined
})

const emit = defineEmits<Emits>()

const store = useAccountStore()
const formRef = ref<FormInstance>()
const isVisible = ref(props.visible)
const isEditing = ref(!!props.credentialId)

const formData = reactive({
  credential_type: 'alpaca',
  api_key: '',
  secret_key: ''
})

const validationRules = {
  api_key: [{ required: true, message: 'API key is required', trigger: 'blur' }],
  secret_key: [{ required: true, message: 'Secret key is required', trigger: 'blur' }],
  credential_type: [{ required: true, message: 'Account type is required', trigger: 'change' }]
}

// Watch visible prop and sync with local state
watch(() => props.visible, (newVal) => {
  isVisible.value = newVal
})

// Watch local visible and emit to parent
watch(isVisible, (newVal) => {
  emit('update:visible', newVal)
})

const handleClose = () => {
  isVisible.value = false
  formData.api_key = ''
  formData.secret_key = ''
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()

    if (isEditing.value && props.credentialId) {
      // Update existing
      await store.updateCredential(props.credentialId, {
        api_key: formData.api_key || undefined,
        secret_key: formData.secret_key || undefined
      })
      ElMessage.success('Account updated successfully')
    } else {
      // Add new
      if (!store.selectedAccountId) {
        ElMessage.error('Account ID not set')
        return
      }
      await store.addCredential({
        account_id: store.selectedAccountId,
        credential_type: formData.credential_type,
        api_key: formData.api_key,
        secret_key: formData.secret_key
      })
      ElMessage.success('Account added successfully')
    }

    emit('success')
    handleClose()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'Operation failed')
  }
}
</script>
```

### Anti-Patterns to Avoid

- **Direct Axios calls in components:** Always use credentialService to keep HTTP logic centralized
- **Storing credentials in component local state:** Use Pinia store exclusively; components should derive state from store
- **Multiple dialogs for add/edit:** Use single AccountManagerDialog with conditional rendering for add vs edit modes
- **Hardcoded validation rules:** Define rules as constants or in store; keeps them maintainable
- **Not using SecretStr equivalent:** Always use type="password" on credential inputs to prevent accidental visibility
- **Skipping list refresh after CRUD:** Always refetch list or update store state immediately after operations

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form validation | Custom validators, if-checks | Element Plus Form validation rules with async-validator | Built-in supports required, email, custom validators, error messages, visual feedback |
| Modal dialogs | Custom div with CSS overlay | Element Plus Dialog with Teleport | Handles z-index, focus trap, Esc key, animation, accessibility |
| Dropdown selector | Custom select with filter | Element Plus Select with filterable and remote-search | Built-in filtering, grouping, remote data loading, tags for multiple |
| Confirmation dialogs | Custom modal | Element Plus MessageBox | Simpler API for confirmation flows, built-in promise support |
| Password input masking | Custom show/hide button | Element Plus Input with show-password attribute | Native browser password field + built-in toggle button |
| Error notifications | Custom alert divs | Element Plus Message | Auto-dismiss, queue support, multiple positioning options |
| Table with actions | Custom div-based list | Element Plus Table with custom column | Built-in sorting, selection, expandable rows, responsive |

**Key insight:** Element Plus is a comprehensive UI library designed specifically for these use cases. Each component handles edge cases, accessibility, and animation automatically. Building custom modals, forms, or dialogs introduces maintenance burden and accessibility risk. This project is committed to Element Plus (v2.13.1 confirmed in package.json), so use it fully.

## Common Pitfalls

### Pitfall 1: Forgetting to Mask API Keys in UI

**What goes wrong:** Developers display credential data in plaintext, accidentally exposing API keys in the UI, browser history, or screenshots.

**Why it happens:** CredentialResponse from backend never includes plaintext (good!), but frontend form inputs might display data unsafely during edit operations.

**How to avoid:**
- Always use `type="password"` on credential input fields
- Never console.log credential objects
- Always use SecretStr-equivalent masking in error messages
- In edit flows, only allow updating (not displaying old values)

**Warning signs:**
- Credential values appearing in browser DevTools console
- API keys visible in component v-model values
- Credentials appearing in error messages

### Pitfall 2: State Desynchronization Between Store and Credentials List

**What goes wrong:** After add/update/delete operations, the UI still shows stale data because store wasn't updated properly, or requests succeeded but UI wasn't refreshed.

**Why it happens:** Forgetting to call `fetchCredentials()` after operations, or updating wrong part of store state.

**How to avoid:**
- Always refetch list after modify operations, or manually update store array
- Use mutation approach: after successful POST/PUT, immediately update store.credentials array
- Call store actions from components, never direct API calls
- Don't assume backend response equals stored state—verify after commit

**Warning signs:**
- Added credential doesn't appear in list
- Deleted credential still visible
- Updated values don't reflect in UI
- Multiple requests triggered for single user action

### Pitfall 3: Not Handling API Errors Consistently

**What goes wrong:** Different error flows for different CRUD operations lead to inconsistent UX—sometimes toast, sometimes nothing, sometimes generic errors.

**Why it happens:** Copy-pasting code without consistent error handling, or forgetting to add try-catch to all API calls.

**How to avoid:**
- All credentialService methods should throw on error (don't swallow errors)
- All store actions should set `error` state on catch
- All components should display error with ElMessage.error()
- Follow axios interceptor pattern already established in codebase
- Add specific error handling for 403 (permission), 409 (conflict/duplicate), 400 (validation)

**Warning signs:**
- Errors appearing in console but not to user
- HTTP 400/403 errors with no UI feedback
- "undefined" errors displayed to user
- Successful operations showing error messages

### Pitfall 4: Validation Only on Backend

**What goes wrong:** Form submits invalid data, backend rejects it, but user doesn't know why the form "hung" because there's no client-side validation.

**Why it happens:** Skipping client-side validation to "rely on backend" (which is correct, but both are needed).

**How to avoid:**
- Use Element Plus Form rules for all credential inputs (required, min length)
- Call `formRef.validate()` before submit
- Match backend validation logic in frontend rules
- Provide immediate feedback on what's wrong with input

**Warning signs:**
- Form submit button appears stuck/loading indefinitely
- No error messages shown when required fields are empty
- HTTP errors due to obvious validation issues (empty strings, wrong format)

### Pitfall 5: Not Setting Active Account State

**What goes wrong:** UI shows "no active account" or switches account in one tab but not reflected in another component.

**Why it happens:** Forgetting to persist active credential ID, or not syncing across components when multiple credential lists exist.

**How to avoid:**
- Pinia store should track `activeCredentialId` as source of truth
- Update store on select/switch operations
- Components should read activeCredential from store computed, not local state
- Consider persisting to localStorage for across-session memory

**Warning signs:**
- Active account doesn't persist across page refresh
- Dropdown shows different selection than header badge
- Operations fail with "no credential selected"

## Code Examples

Verified patterns from official and existing sources:

### API Response Type Mapping

```typescript
// src/types/account.ts
// Source: Backend credential_schemas.py (CredentialResponse structure)

export interface CredentialResponse {
  id: string
  account_id: string
  credential_type: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ListCredentialsResponse {
  status: string
  credentials: CredentialResponse[]
  count: number
}

// Form input types (for add/edit)
export interface CredentialInput {
  credential_type: string
  api_key: string
  secret_key: string
}

export interface CredentialUpdate {
  api_key?: string
  secret_key?: string
  is_active?: boolean
}
```

### Error Handling Pattern

```typescript
// Source: Existing pattern from codebase (chatService.ts, alpacaService.ts)
// Applied to credential operations

async function updateCredential(credentialId: string, data: CredentialUpdate) {
  try {
    const response = await apiClient.put(`/api/credentials/${credentialId}`, data)
    return response.data
  } catch (error) {
    if (error.response) {
      // Server responded with error
      const status = error.response.status
      const detail = error.response.data?.detail

      if (status === 403) {
        throw new Error('You do not have permission to modify this credential')
      } else if (status === 404) {
        throw new Error('Credential not found')
      } else if (status === 400) {
        throw new Error(`Validation error: ${detail}`)
      } else {
        throw new Error(detail || 'Failed to update credential')
      }
    } else if (error.request) {
      throw new Error('No response from server—check your connection')
    } else {
      throw new Error('Request setup error: ' + error.message)
    }
  }
}
```

### Element Plus Select for Account Switching

```typescript
// src/components/AccountSelector.vue
// Source: Element Plus Select documentation

<template>
  <div class="account-selector">
    <label>Active Account:</label>
    <el-select
      v-model="selectedId"
      :loading="store.isLoading"
      placeholder="Select account"
      @change="handleChange"
    >
      <el-option
        v-for="cred in store.credentials"
        :key="cred.id"
        :label="`${cred.credential_type} - ${cred.created_at.split('T')[0]}`"
        :value="cred.id"
      />
    </el-select>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAccountStore } from '@/stores/accountStore'

const store = useAccountStore()

const selectedId = computed({
  get: () => store.activeCredentialId || '',
  set: (value) => {
    store.setActiveCredential(value)
  }
})

const handleChange = () => {
  // Store handles persistence and state update
}
</script>
```

### Async Validation with Credential Testing

```typescript
// src/components/AccountManagerDialog.vue (extended)
// Source: Element Plus Form validation + credentialService.validateCredential

// In validationRules:
const validateCredentials = async (rule, value, callback) => {
  if (!formData.api_key || !formData.secret_key) {
    callback(new Error('Both API key and secret key required'))
    return
  }

  try {
    // For new credentials, create temp ID for validation
    // For existing, use credentialId
    const testId = props.credentialId || 'temp-test'
    const result = await credentialService.validateCredential(testId)

    if (result.is_valid) {
      callback()
    } else {
      callback(new Error('Invalid credentials—check with Alpaca'))
    }
  } catch (error) {
    callback(new Error('Validation failed: ' + error.message))
  }
}

const validationRules = {
  // ... other rules ...
  secret_key: [
    { required: true, message: 'Secret key required', trigger: 'blur' },
    { asyncValidator: validateCredentials, trigger: 'change' }
  ]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Vuex stores with modules | Pinia composition API | Vue 3 adoption (2022) | Simpler code, better TypeScript, no modules ceremony |
| Class-based components | Composition API with setup | Vue 3 release (2020) | Reactive refs, composables, better code reuse |
| Fetch API | Axios with interceptors | Standardization (2021+) | Centralized error handling, request/response transforms |
| Custom form libraries | Element Plus built-in validation | Enterprise adoption (2023+) | Async-validator backend, comprehensive components |
| Manual modal z-index | Teleport + Dialog component | Vue 3 Teleport (2020) | Automatic stacking, no CSS conflicts |

**Deprecated/outdated:**
- Manual div-based modals: Replaced by native `<dialog>` and Teleport-based components
- Form refs with jQuery-style DOM manipulation: Replaced by Vue's template refs + reactive data binding
- Global event bus for component communication: Replaced by Pinia for shared state, props/events for local

## Open Questions

1. **Backend account_id vs credential_id relationship**
   - What we know: Credentials are associated with user_accounts, each credential has unique id
   - What's unclear: Should UI support multiple Alpaca credentials per account, or one-credential-per-account model?
   - Recommendation: Assume one-active credential model (like radio select). Backend structure supports multiple but one should be marked `is_active`. Phase 3 API supports this. If multi-credential needed later, Table display instead of Select will suffice.

2. **Credential validation flow timing**
   - What we know: Backend validates against Alpaca API on POST /credentials/{id}/validate
   - What's unclear: Should validation run automatically on add, or only on user request? Should we block form submission on validation failure?
   - Recommendation: Make validation optional in form submission. Provide separate "Test Credentials" button. Don't block add if validation fails (credentials might work later). Allow update even if validation fails to permit fixing bad credentials.

3. **Displaying credential metadata safely**
   - What we know: CredentialResponse only includes metadata (id, type, is_active, timestamps), no plaintext keys
   - What's unclear: Should edit flow allow viewing/changing api_key and secret_key, or just mark inactive?
   - Recommendation: Allow full updates (both keys), but don't display old values. Input fields should remain empty on edit—only allow new values to be entered. This prevents accidental exposure of old keys in the form.

4. **Account switching scope**
   - What we know: Multiple credentials can be stored per user_account
   - What's unclear: When user switches active account, should this affect all of Alpaca Agent Chat or just the next execution?
   - Recommendation: Store activeCredentialId in Pinia persistently. Alpaca Agent Chat should read from store before each execution. Switching account immediately updates store and takes effect on next agent request.

5. **Error recovery for deleted-in-flight credentials**
   - What we know: DELETE endpoint exists and RLS ensures user owns credential
   - What's unclear: If user deletes credential while another component is using it, should there be graceful fallback?
   - Recommendation: Phase 4 scope is just UI CRUD. Error handling for "credential deleted while in use" belongs to Phase 5+ when Alpaca Agent Chat integrates. For Phase 4, assume single-user, single-session usage patterns.

## Sources

### Primary (HIGH confidence)
- **Element Plus v2.13.1** - Form, Dialog, Table, Select, Button, Message components (confirmed in package.json; docs: https://element-plus.org)
- **Vue 3 v3.4.0** - Composition API with ref, computed, watch (confirmed in package.json)
- **Pinia v2.1.7** - Composition API store definition pattern (confirmed in package.json; docs: https://pinia.vuejs.org)
- **Axios v1.6.0** - HTTP client configured in existing codebase at src/services/api.ts
- **Phase 3 Backend** - Verified credential endpoints at apps/orchestrator_3_stream/backend/routers/credentials.py
- **Phase 3 Schemas** - Verified CredentialResponse structure at apps/orchestrator_3_stream/backend/schemas/credential_schemas.py

### Secondary (MEDIUM confidence)
- [Element Plus Dialog Documentation](https://element-plus.org/en-US/component/dialog) - Dialog patterns, Teleport, before-close hooks
- [Element Plus Form Validation](https://element-plus.org/en-US/component/form) - Async validator, validation rules, validation triggers
- [Element Plus Select](https://element-plus.org/en-US/component/select) - Filterable, remote data, multiple selection
- [Pinia Documentation](https://pinia.vuejs.org/introduction.html) - Composition API stores, composition syntax
- [Vue 3 Composition API](https://vuejs.org/guide/extras/composition-api-faq.html) - Reactivity with ref/computed, watchers
- [Vue 3 Form Management Best Practices 2026](https://www.vuescript.com/best-modal-popup-dialog/) - Modal dialog patterns for Vue 3

### Tertiary (LOW confidence - WebSearch, marked for validation)
- [Vue 3 CRUD Patterns](https://github.com/bezkoder/vue-3-crud) - Community CRUD example structure
- [Axios Error Handling Patterns](https://blog.logrocket.com/error-handling-debugging-and-tracing-in-vue-js/) - Error handling with Axios interceptors
- [Vue Input Masking Libraries](https://blog.logrocket.com/creating-vue-masked-input-fields/) - Input mask patterns (context note: Element Plus type=password sufficient for this phase)

## Metadata

**Confidence breakdown:**
- **Standard Stack: HIGH** - All libraries confirmed in package.json or existing codebase
- **Architecture: HIGH** - Patterns derived from existing project code (orchestratorStore, chatService, existing composables)
- **Pitfalls: HIGH** - Based on common Vue 3 CRUD mistakes documented in official Element Plus and Vue documentation
- **Code Examples: HIGH** - All examples follow patterns already established in codebase (credentialService mirrors chatService pattern)

**Research date:** 2026-01-31
**Valid until:** 2026-02-14 (2 weeks—Element Plus stable, Vue 3 stable; fast-moving: consider Axios/Pinia updates sooner)

## Notes for Planner

- **No new dependencies needed.** All libraries are installed and at stable versions.
- **Zero blocked by backend.** Phase 3 endpoints are complete and tested. Frontend can start immediately.
- **TypeScript throughout.** All code examples use full type safety. Verify components export proper type definitions.
- **Pinia store is state source of truth.** All components must read from store, never maintain local credential copies.
- **SecretStr pattern note:** Backend uses Pydantic's SecretStr to mask credentials. Frontend equivalent is `type="password"` on inputs. No custom masking library needed.
- **Element Plus components are sufficient.** Dialog, Form, Table, Select all have features needed. Don't reach for external modal/form libraries.

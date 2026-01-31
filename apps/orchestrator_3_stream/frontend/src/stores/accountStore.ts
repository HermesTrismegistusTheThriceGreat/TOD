/**
 * Account Store
 *
 * Pinia store for managing user accounts and credentials state.
 * Handles CRUD operations, active credential selection, and localStorage persistence.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  UserAccountResponse,
  CredentialResponse,
  CredentialInput,
  CredentialUpdate
} from '@/types/account'
import credentialService from '@/services/credentialService'

export const useAccountStore = defineStore('account', () => {
  // ═══════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════

  /** Current user's account */
  const userAccount = ref<UserAccountResponse | null>(null)

  /** List of credentials for current account */
  const credentials = ref<CredentialResponse[]>([])

  /** Selected credential ID for trading */
  const activeCredentialId = ref<string | null>(null)

  /** Loading indicator */
  const isLoading = ref<boolean>(false)

  /** Error message */
  const error = ref<string | null>(null)

  /** Prevents duplicate initialization */
  const isInitialized = ref<boolean>(false)

  // ═══════════════════════════════════════════════════════════
  // GETTERS
  // ═══════════════════════════════════════════════════════════

  /** Active credential object */
  const activeCredential = computed(() => {
    if (!activeCredentialId.value) return null
    return credentials.value.find(c => c.id === activeCredentialId.value) || null
  })

  /** Whether user has any credentials */
  const hasCredentials = computed(() => credentials.value.length > 0)

  /** Filter credentials by type: alpaca */
  const alpacaCredentials = computed(() =>
    credentials.value.filter(c => c.credential_type === 'alpaca')
  )

  // ═══════════════════════════════════════════════════════════
  // ACTIONS
  // ═══════════════════════════════════════════════════════════

  /**
   * Initialize store: get or create account, fetch credentials.
   * GUARD: Prevents duplicate initialization calls.
   */
  async function initialize(): Promise<void> {
    // GUARD: If already initialized, return early
    if (isInitialized.value) {
      console.log('[AccountStore] Already initialized, skipping')
      return
    }

    try {
      console.log('[AccountStore] Initializing...')
      isInitialized.value = true
      error.value = null

      // Get or create account for current user
      const response = await credentialService.getOrCreateAccount()
      userAccount.value = response.account

      if (response.created) {
        console.log('[AccountStore] New account created:', response.account.id)
      } else {
        console.log('[AccountStore] Existing account loaded:', response.account.id)
      }

      // Fetch credentials for this account
      await fetchCredentials(response.account.id)

      // Auto-select first active credential if none selected
      if (!activeCredentialId.value && credentials.value.length > 0) {
        const firstActive = credentials.value.find(c => c.is_active)
        if (firstActive) {
          setActiveCredential(firstActive.id)
          console.log('[AccountStore] Auto-selected first active credential:', firstActive.id)
        }
      }

      console.log('[AccountStore] Initialization complete')
    } catch (err) {
      console.error('[AccountStore] Initialization failed:', err)
      error.value = err instanceof Error ? err.message : 'Failed to initialize account store'
      // On error, reset initialization flag to allow retry
      isInitialized.value = false
      throw err
    }
  }

  /**
   * Reset store state.
   * Use this when user logs out.
   */
  function reset(): void {
    console.log('[AccountStore] Resetting state')
    userAccount.value = null
    credentials.value = []
    activeCredentialId.value = null
    error.value = null
    isInitialized.value = false

    // Clear from localStorage
    try {
      localStorage.removeItem('activeCredentialId')
    } catch (err) {
      console.warn('[AccountStore] Failed to clear localStorage:', err)
    }
  }

  /**
   * Fetch credentials for an account.
   *
   * @param accountId - Account ID (optional, uses userAccount.id if not provided)
   */
  async function fetchCredentials(accountId?: string): Promise<void> {
    try {
      error.value = null
      const targetAccountId = accountId || userAccount.value?.id

      if (!targetAccountId) {
        throw new Error('No account ID available')
      }

      console.log('[AccountStore] Fetching credentials for account:', targetAccountId)
      credentials.value = await credentialService.listCredentials(targetAccountId)
      console.log('[AccountStore] Fetched', credentials.value.length, 'credentials')

      // Auto-select first active if none selected
      if (!activeCredentialId.value && credentials.value.length > 0) {
        const firstActive = credentials.value.find(c => c.is_active)
        if (firstActive) {
          setActiveCredential(firstActive.id)
        }
      }
    } catch (err) {
      console.error('[AccountStore] Failed to fetch credentials:', err)
      error.value = err instanceof Error ? err.message : 'Failed to fetch credentials'
      throw err
    }
  }

  /**
   * Add a new credential.
   *
   * @param input - Credential input data
   * @returns Newly created credential
   */
  async function addCredential(input: CredentialInput): Promise<CredentialResponse> {
    try {
      isLoading.value = true
      error.value = null

      if (!userAccount.value) {
        throw new Error('No user account available')
      }

      console.log('[AccountStore] Adding credential:', input.credential_type)
      const newCredential = await credentialService.storeCredential({
        account_id: userAccount.value.id,
        credential_type: input.credential_type,
        api_key: input.api_key,
        secret_key: input.secret_key
      })

      // Add to credentials array
      credentials.value.push(newCredential)
      console.log('[AccountStore] Credential added:', newCredential.id)

      return newCredential
    } catch (err) {
      console.error('[AccountStore] Failed to add credential:', err)
      error.value = err instanceof Error ? err.message : 'Failed to add credential'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update an existing credential.
   *
   * @param credentialId - Credential ID to update
   * @param data - Fields to update
   * @returns Updated credential
   */
  async function updateCredential(
    credentialId: string,
    data: CredentialUpdate
  ): Promise<CredentialResponse> {
    try {
      isLoading.value = true
      error.value = null

      console.log('[AccountStore] Updating credential:', credentialId)
      const updated = await credentialService.updateCredential(credentialId, data)

      // Update in credentials array
      const index = credentials.value.findIndex(c => c.id === credentialId)
      if (index !== -1) {
        credentials.value[index] = updated
        console.log('[AccountStore] Credential updated in store')
      }

      return updated
    } catch (err) {
      console.error('[AccountStore] Failed to update credential:', err)
      error.value = err instanceof Error ? err.message : 'Failed to update credential'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Remove a credential.
   *
   * @param credentialId - Credential ID to delete
   */
  async function removeCredential(credentialId: string): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      console.log('[AccountStore] Deleting credential:', credentialId)
      await credentialService.deleteCredential(credentialId)

      // Remove from credentials array
      credentials.value = credentials.value.filter(c => c.id !== credentialId)
      console.log('[AccountStore] Credential removed from store')

      // Clear active credential if it was deleted
      if (activeCredentialId.value === credentialId) {
        activeCredentialId.value = null
        try {
          localStorage.removeItem('activeCredentialId')
        } catch (err) {
          console.warn('[AccountStore] Failed to clear activeCredentialId from localStorage:', err)
        }
        console.log('[AccountStore] Cleared active credential (was deleted)')
      }
    } catch (err) {
      console.error('[AccountStore] Failed to remove credential:', err)
      error.value = err instanceof Error ? err.message : 'Failed to remove credential'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Set active credential for trading.
   * Persists to localStorage.
   *
   * @param credentialId - Credential ID to set as active
   */
  function setActiveCredential(credentialId: string): void {
    console.log('[AccountStore] Setting active credential:', credentialId)
    activeCredentialId.value = credentialId

    // Persist to localStorage
    try {
      localStorage.setItem('activeCredentialId', credentialId)
    } catch (err) {
      console.warn('[AccountStore] Failed to save activeCredentialId to localStorage:', err)
    }
  }

  /**
   * Load active credential from localStorage.
   * Validates it exists in credentials array.
   */
  function loadActiveCredential(): void {
    try {
      const saved = localStorage.getItem('activeCredentialId')
      if (saved) {
        // Validate it exists in credentials array
        const exists = credentials.value.find(c => c.id === saved)
        if (exists) {
          activeCredentialId.value = saved
          console.log('[AccountStore] Loaded active credential from localStorage:', saved)
        } else {
          console.warn('[AccountStore] Saved credential ID not found in credentials array:', saved)
          localStorage.removeItem('activeCredentialId')
        }
      }
    } catch (err) {
      console.warn('[AccountStore] Failed to load activeCredentialId from localStorage:', err)
    }
  }

  // ═══════════════════════════════════════════════════════════
  // RETURN PUBLIC API
  // ═══════════════════════════════════════════════════════════

  return {
    // State
    userAccount,
    credentials,
    activeCredentialId,
    isLoading,
    error,
    isInitialized,

    // Getters
    activeCredential,
    hasCredentials,
    alpacaCredentials,

    // Actions
    initialize,
    reset,
    fetchCredentials,
    addCredential,
    updateCredential,
    removeCredential,
    setActiveCredential,
    loadActiveCredential
  }
})

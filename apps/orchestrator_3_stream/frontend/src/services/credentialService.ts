/**
 * Credential and Account Service
 *
 * HTTP service for managing user accounts and credentials.
 * Provides all CRUD operations for credentials and account management.
 */

import { apiClient } from './api'
import type {
  CredentialResponse,
  ListCredentialsResponse,
  CredentialUpdate,
  ValidateCredentialResponse,
  UserAccountResponse,
  ListAccountsResponse,
  GetOrCreateAccountResponse,
  AccountDataResponse
} from '@/types/account'

/**
 * Credential and Account Service
 *
 * All methods use async/await and let axios error interceptors handle errors.
 */
const credentialService = {
  /**
   * Get or create account for current user.
   * Idempotent operation - returns existing account or creates new one.
   *
   * @returns Account object and created flag
   */
  async getOrCreateAccount(): Promise<GetOrCreateAccountResponse> {
    const response = await apiClient.post<GetOrCreateAccountResponse>('/api/accounts/get-or-create')
    return response.data
  },

  /**
   * List all accounts for current user.
   *
   * @returns Array of user accounts
   */
  async listAccounts(): Promise<UserAccountResponse[]> {
    const response = await apiClient.get<ListAccountsResponse>('/api/accounts')
    return response.data.accounts
  },

  /**
   * List all credentials for a specific account.
   *
   * @param accountId - UUID of the user account
   * @returns Array of credential metadata (no plaintext credentials)
   */
  async listCredentials(accountId: string): Promise<CredentialResponse[]> {
    const response = await apiClient.get<ListCredentialsResponse>('/api/credentials', {
      params: { account_id: accountId }
    })
    return response.data.credentials
  },

  /**
   * Store a new credential for an account.
   *
   * @param data - Credential data including account_id, credential_type, api_key, secret_key
   * @returns Newly created credential metadata
   */
  async storeCredential(data: {
    account_id: string
    credential_type: string
    api_key: string
    secret_key: string
  }): Promise<CredentialResponse> {
    const response = await apiClient.post<CredentialResponse>('/api/credentials/store', data)
    return response.data
  },

  /**
   * Update an existing credential.
   * Only provided fields will be updated (partial update).
   *
   * @param credentialId - UUID of the credential to update
   * @param data - Fields to update (api_key, secret_key, is_active)
   * @returns Updated credential metadata
   */
  async updateCredential(credentialId: string, data: CredentialUpdate): Promise<CredentialResponse> {
    const response = await apiClient.put<CredentialResponse>(`/api/credentials/${credentialId}`, data)
    return response.data
  },

  /**
   * Delete a credential.
   * Hard delete - credential will be removed from database.
   *
   * @param credentialId - UUID of the credential to delete
   */
  async deleteCredential(credentialId: string): Promise<void> {
    await apiClient.delete(`/api/credentials/${credentialId}`)
    // No return value - 204 No Content
  },

  /**
   * Validate a credential against external API.
   * Tests if the credential is valid with the provider (Alpaca/Polygon).
   *
   * @param credentialId - UUID of the credential to validate
   * @returns Validation result with is_valid flag and account_type
   */
  async validateCredential(credentialId: string): Promise<ValidateCredentialResponse> {
    const response = await apiClient.post<ValidateCredentialResponse>(
      `/api/credentials/${credentialId}/validate`
    )
    return response.data
  },

  /**
   * Fetch real-time account data for a credential.
   * Returns balance, equity, buying power, and account type from Alpaca API.
   *
   * @param credentialId - UUID of the credential
   * @returns Account data response with metrics
   */
  async getAccountData(credentialId: string): Promise<AccountDataResponse> {
    const response = await apiClient.get<AccountDataResponse>(
      `/api/credentials/${credentialId}/account-data`
    )
    return response.data
  }
}

// Export as default and named export
export default credentialService
export { credentialService }

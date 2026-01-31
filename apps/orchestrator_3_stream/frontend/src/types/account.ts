/**
 * TypeScript types for Account and Credential management.
 *
 * These interfaces mirror the backend Pydantic schemas to ensure type safety
 * across the frontend-backend boundary.
 */

/**
 * Credential metadata response (no plaintext credentials).
 * Mirrors backend CredentialResponse schema.
 */
export interface CredentialResponse {
  /** Credential ID (UUID) */
  id: string
  /** User account ID (UUID) */
  account_id: string
  /** Credential type (alpaca/polygon) */
  credential_type: string
  /** Whether credential is active */
  is_active: boolean
  /** Creation timestamp (ISO 8601) */
  created_at: string
  /** Last update timestamp (ISO 8601) */
  updated_at: string
}

/**
 * Response from list credentials endpoint.
 * Mirrors backend ListCredentialsResponse schema.
 */
export interface ListCredentialsResponse {
  /** Response status */
  status: string
  /** List of credential metadata */
  credentials: CredentialResponse[]
  /** Number of credentials returned */
  count: number
}

/**
 * Response from credential validation endpoint.
 * Mirrors backend ValidateCredentialResponse schema.
 */
export interface ValidateCredentialResponse {
  /** Whether credentials are valid */
  is_valid: boolean
  /** Validation message */
  message: string
  /** Account type if valid: 'paper' or 'live' */
  account_type: string | null
}

/**
 * Input for storing a new credential.
 * Used in add credential form.
 */
export interface CredentialInput {
  /** Type of credential: 'alpaca' or 'polygon' */
  credential_type: string
  /** API key (will be encrypted server-side) */
  api_key: string
  /** Secret key (will be encrypted server-side) */
  secret_key: string
}

/**
 * Input for updating an existing credential.
 * All fields are optional - only provided fields will be updated.
 */
export interface CredentialUpdate {
  /** New API key (optional) */
  api_key?: string
  /** New secret key (optional) */
  secret_key?: string
  /** Whether credential is active (optional) */
  is_active?: boolean
}

/**
 * User account metadata response.
 * Mirrors backend UserAccountResponse schema.
 */
export interface UserAccountResponse {
  /** Account ID (UUID) */
  id: string
  /** User ID (from Better Auth) */
  user_id: string
  /** Display name for the account */
  account_name: string
  /** Whether account is active */
  is_active: boolean
  /** Creation timestamp (ISO 8601) */
  created_at: string
  /** Last update timestamp (ISO 8601) */
  updated_at: string
}

/**
 * Response from list accounts endpoint.
 * Mirrors backend ListAccountsResponse schema.
 */
export interface ListAccountsResponse {
  /** Response status */
  status: string
  /** List of user accounts */
  accounts: UserAccountResponse[]
  /** Number of accounts returned */
  count: number
}

/**
 * Response from get-or-create account endpoint.
 * Mirrors backend GetOrCreateAccountResponse schema.
 */
export interface GetOrCreateAccountResponse {
  /** The user account (existing or newly created) */
  account: UserAccountResponse
  /** True if account was just created, False if it already existed */
  created: boolean
}

/**
 * Real-time account data response from Alpaca API.
 * Mirrors backend AccountDataResponse schema.
 */
export interface AccountDataResponse {
  /** Account type: "paper" or "live" */
  account_type: string
  /** Cash balance as string (e.g., "100000.25") */
  balance: string
  /** Total equity (cash + positions) as string */
  equity: string
  /** Available buying power as string */
  buying_power: string
  /** Account currency (default: USD) */
  currency: string
  /** Whether trading is blocked */
  trading_blocked: boolean
  /** Whether account activity is prohibited */
  account_blocked: boolean
  /** Whether flagged as pattern day trader */
  pattern_day_trader: boolean
  /** Day trades in last 5 trading days */
  daytrade_count: number
  /** ISO 8601 timestamp of last update */
  last_updated: string
}

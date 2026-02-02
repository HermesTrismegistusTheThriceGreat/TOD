-- ============================================================================
-- USER ACCOUNTS AND CREDENTIALS TABLES
-- ============================================================================
-- Multi-user credential management for Alpaca trading accounts.
-- Links Better Auth users to their trading accounts and encrypted API credentials.
--
-- Key Features:
-- - One user can have multiple trading accounts (e.g., live, paper)
-- - Each account can have multiple credential sets (Alpaca, Polygon, etc.)
-- - Denormalized user_id in user_credentials for RLS performance
-- - Cascade deletes ensure cleanup when users/accounts are removed
--
-- Dependencies:
-- - Migration 13: Better Auth "user" table must exist
-- - Phase 1: Encryption service for securing api_key/secret_key fields

-- ═══════════════════════════════════════════════════════════
-- USER_ACCOUNTS TABLE
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE,
    account_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_accounts_user_id ON user_accounts(user_id);

COMMENT ON TABLE user_accounts IS 'User trading accounts linked to Better Auth users';
COMMENT ON COLUMN user_accounts.id IS 'Account unique identifier';
COMMENT ON COLUMN user_accounts.user_id IS 'Better Auth user ID (references user.id)';
COMMENT ON COLUMN user_accounts.account_name IS 'Display name for account (e.g., "Trading Account 1", "Paper Account")';
COMMENT ON COLUMN user_accounts.is_active IS 'Whether account is active and can be used';
COMMENT ON COLUMN user_accounts.created_at IS 'Account creation timestamp';
COMMENT ON COLUMN user_accounts.updated_at IS 'Account last update timestamp';


-- ═══════════════════════════════════════════════════════════
-- USER_CREDENTIALS TABLE
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_account_id UUID NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    credential_type VARCHAR(50) NOT NULL,
    api_key TEXT NOT NULL,
    secret_key TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_credentials_user_id ON user_credentials(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credentials_account_id ON user_credentials(user_account_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_credentials_unique ON user_credentials(user_account_id, credential_type);

COMMENT ON TABLE user_credentials IS 'Encrypted API credentials for user trading accounts';
COMMENT ON COLUMN user_credentials.id IS 'Credential unique identifier';
COMMENT ON COLUMN user_credentials.user_account_id IS 'User account this credential belongs to';
COMMENT ON COLUMN user_credentials.user_id IS 'Denormalized user_id for RLS performance (avoids join in policy)';
COMMENT ON COLUMN user_credentials.credential_type IS 'Credential type (alpaca, polygon, etc.)';
COMMENT ON COLUMN user_credentials.api_key IS 'API key (encrypted via SQLAlchemy TypeDecorator)';
COMMENT ON COLUMN user_credentials.secret_key IS 'Secret key (encrypted via SQLAlchemy TypeDecorator)';
COMMENT ON COLUMN user_credentials.is_active IS 'Whether credential is active and can be used';
COMMENT ON COLUMN user_credentials.expires_at IS 'Optional credential expiration timestamp';
COMMENT ON COLUMN user_credentials.created_at IS 'Credential creation timestamp';
COMMENT ON COLUMN user_credentials.updated_at IS 'Credential last update timestamp';

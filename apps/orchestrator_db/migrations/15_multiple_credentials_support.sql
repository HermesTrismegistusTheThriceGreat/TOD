-- ============================================================================
-- MULTIPLE CREDENTIALS SUPPORT
-- ============================================================================
-- Enables users to have multiple credentials of the same type per account.
-- This allows users to add multiple Alpaca paper accounts or multiple live accounts.
--
-- Changes:
-- - DROP unique constraint on (user_account_id, credential_type)
-- - ADD nickname column for user-friendly credential identification
-- - BACKFILL existing credentials with credential_type as nickname
-- - ADD index on (user_account_id, nickname) for efficient lookups
--
-- Dependencies:
-- - Migration 14: user_credentials table must exist
-- ============================================================================

-- ═══════════════════════════════════════════════════════════
-- DROP UNIQUE CONSTRAINT
-- ═══════════════════════════════════════════════════════════
-- This allows multiple credentials of the same type per account
-- (e.g., multiple "alpaca_paper" credentials)

DROP INDEX IF EXISTS idx_user_credentials_unique;


-- ═══════════════════════════════════════════════════════════
-- ADD NICKNAME COLUMN
-- ═══════════════════════════════════════════════════════════
-- User-friendly label to distinguish between multiple credentials

ALTER TABLE user_credentials
ADD COLUMN IF NOT EXISTS nickname VARCHAR(255);

COMMENT ON COLUMN user_credentials.nickname IS 'User-friendly label for credential (e.g., "Main Trading", "Paper Testing")';


-- ═══════════════════════════════════════════════════════════
-- BACKFILL EXISTING CREDENTIALS
-- ═══════════════════════════════════════════════════════════
-- Set nickname to credential_type for existing rows without a nickname

UPDATE user_credentials
SET nickname = credential_type
WHERE nickname IS NULL;


-- ═══════════════════════════════════════════════════════════
-- ADD INDEX FOR NICKNAME LOOKUPS
-- ═══════════════════════════════════════════════════════════
-- Enables efficient queries filtering by account and nickname

CREATE INDEX IF NOT EXISTS idx_user_credentials_nickname
ON user_credentials(user_account_id, nickname);

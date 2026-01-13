-- ============================================================================
-- Fix Features and Twilio Accounts ULID Foreign Keys
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migrating features and twilio_accounts FKs to ULID...';
END $$;

-- 1. Alter features table to support ULID owner_id
-- Since we are in a dev environment/resetting DB, we can just alter the type.
-- In prod, we would need a more complex migration (add column, fill, swap).
-- But here, data is likely empty or can be truncated.

-- Drop constraints if they exist
ALTER TABLE features DROP CONSTRAINT IF EXISTS features_owner_id_fkey;
ALTER TABLE twilio_accounts DROP CONSTRAINT IF EXISTS twilio_accounts_owner_id_fkey;

-- Change column type to TEXT for ULID
ALTER TABLE features ALTER COLUMN owner_id TYPE TEXT USING owner_id::TEXT;
ALTER TABLE twilio_accounts ALTER COLUMN owner_id TYPE TEXT USING owner_id::TEXT;

-- Re-add Foreign Key constraints
ALTER TABLE features 
    ADD CONSTRAINT fk_features_owner 
    FOREIGN KEY (owner_id) 
    REFERENCES owners(owner_id) 
    ON DELETE CASCADE;

ALTER TABLE twilio_accounts 
    ADD CONSTRAINT fk_twilio_accounts_owner 
    FOREIGN KEY (owner_id) 
    REFERENCES owners(owner_id) 
    ON DELETE CASCADE;

-- Update indexes
DROP INDEX IF EXISTS idx_features_owner;
DROP INDEX IF EXISTS idx_twilio_accounts_owner;

CREATE INDEX IF NOT EXISTS idx_features_owner_id ON features(owner_id);
CREATE INDEX IF NOT EXISTS idx_twilio_accounts_owner_id ON twilio_accounts(owner_id);

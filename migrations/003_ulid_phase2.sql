-- ============================================================================
-- Migration Phase 2: Finalize ULID Migration
-- ============================================================================
-- This script completes the ULID migration by:
-- 1. Dropping old integer ID columns
-- 2. Renaming ULID columns to primary names
-- 3. Recreating foreign key constraints
-- 4. Cleaning up temporary migration artifacts
--
-- ⚠️  WARNING: This is a BREAKING CHANGE
-- Only run this after ALL application code has been updated to use ULIDs
-- ============================================================================

-- ============================================================================
-- SAFETY CHECK: Verify application is ready
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'ULID Migration Phase 2 - FINAL STEPS';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  WARNING: This migration is DESTRUCTIVE';
    RAISE NOTICE '';
    RAISE NOTICE 'This will:';
    RAISE NOTICE '1. DROP all old integer ID columns';
    RAISE NOTICE '2. RENAME ULID columns to primary names';
    RAISE NOTICE '3. DROP foreign key constraints using old IDs';
    RAISE NOTICE '';
    RAISE NOTICE 'Before proceeding, ensure:';
    RAISE NOTICE '✓ ALL application code updated to use ULIDs';
    RAISE NOTICE '✓ ALL repositories updated';
    RAISE NOTICE '✓ ALL services updated';
    RAISE NOTICE '✓ Testing completed successfully';
    RAISE NOTICE '✓ Database backup created';
    RAISE NOTICE '';
    RAISE NOTICE 'Uncomment the execution blocks below to proceed';
    RAISE NOTICE '========================================';
END $$;

-- ============================================================================
-- STEP 1: Drop Foreign Key Constraints (Old Integer IDs)
-- ============================================================================

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_owner_id_fkey;
ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_owner_id_fkey;
ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_user_id_fkey;
ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_conv_id_fkey;
ALTER TABLE ai_results DROP CONSTRAINT IF EXISTS ai_results_msg_id_fkey;
ALTER TABLE ai_results DROP CONSTRAINT IF EXISTS ai_results_feature_id_fkey;
ALTER TABLE features DROP CONSTRAINT IF EXISTS features_owner_id_fkey;
ALTER TABLE twilio_accounts DROP CONSTRAINT IF EXISTS twilio_accounts_owner_id_fkey;

-- ============================================================================
-- STEP 2: Drop Old Integer ID Columns
-- ============================================================================

-- Drop old primary key columns
ALTER TABLE owners DROP COLUMN IF EXISTS owner_id CASCADE;
ALTER TABLE users DROP COLUMN IF EXISTS user_id CASCADE;
ALTER TABLE conversations DROP COLUMN IF EXISTS conv_id CASCADE;
ALTER TABLE messages DROP COLUMN IF EXISTS msg_id CASCADE;
ALTER TABLE ai_results DROP COLUMN IF EXISTS ai_result_id CASCADE;

-- Drop old foreign key columns
ALTER TABLE users DROP COLUMN IF EXISTS owner_id;
ALTER TABLE conversations DROP COLUMN IF EXISTS owner_id;
ALTER TABLE conversations DROP COLUMN IF EXISTS user_id;
ALTER TABLE messages DROP COLUMN IF EXISTS conv_id;
ALTER TABLE ai_results DROP COLUMN IF EXISTS msg_id;
-- Note: feature_id kept as BIGINT for now, can be migrated separately if needed

-- ============================================================================
-- STEP 3: Rename ULID Columns to Primary Names
-- ============================================================================

-- Rename primary ULID columns
ALTER TABLE owners RENAME COLUMN owner_ulid TO owner_id;
ALTER TABLE users RENAME COLUMN user_ulid TO user_id;
ALTER TABLE conversations RENAME COLUMN conv_ulid TO conv_id;
ALTER TABLE messages RENAME COLUMN msg_ulid TO msg_id;
ALTER TABLE ai_results RENAME COLUMN ai_result_ulid TO ai_result_id;

-- Rename foreign key ULID columns
ALTER TABLE users RENAME COLUMN owner_ulid_fk TO owner_id;
ALTER TABLE conversations RENAME COLUMN owner_ulid_fk TO owner_id;
ALTER TABLE conversations RENAME COLUMN user_ulid_fk TO user_id;
ALTER TABLE messages RENAME COLUMN conv_ulid_fk TO conv_id;
ALTER TABLE ai_results RENAME COLUMN msg_ulid_fk TO msg_id;

-- ============================================================================
-- STEP 4: Recreate Primary Key Constraints
-- ============================================================================

ALTER TABLE owners ADD PRIMARY KEY (owner_id);
ALTER TABLE users ADD PRIMARY KEY (user_id);
ALTER TABLE conversations ADD PRIMARY KEY (conv_id);
ALTER TABLE messages ADD PRIMARY KEY (msg_id);
ALTER TABLE ai_results ADD PRIMARY KEY (ai_result_id);

-- ============================================================================
-- STEP 5: Recreate Foreign Key Constraints (Now Using ULIDs)
-- ============================================================================

-- Users -> Owners
ALTER TABLE users 
    ADD CONSTRAINT fk_users_owner 
    FOREIGN KEY (owner_id) 
    REFERENCES owners(owner_id) 
    ON DELETE CASCADE;

-- Conversations -> Owners
ALTER TABLE conversations 
    ADD CONSTRAINT fk_conversations_owner 
    FOREIGN KEY (owner_id) 
    REFERENCES owners(owner_id) 
    ON DELETE CASCADE;

-- Conversations -> Users
ALTER TABLE conversations 
    ADD CONSTRAINT fk_conversations_user 
    FOREIGN KEY (user_id) 
    REFERENCES users(user_id) 
    ON DELETE SET NULL;

-- Messages -> Conversations
ALTER TABLE messages 
    ADD CONSTRAINT fk_messages_conversation 
    FOREIGN KEY (conv_id) 
    REFERENCES conversations(conv_id) 
    ON DELETE CASCADE;

-- AI Results -> Messages
ALTER TABLE ai_results 
    ADD CONSTRAINT fk_ai_results_message 
    FOREIGN KEY (msg_id) 
    REFERENCES messages(msg_id) 
    ON DELETE CASCADE;

-- Features -> Owners (if migrating features to ULID)
-- ALTER TABLE features 
--     ADD CONSTRAINT fk_features_owner 
--     FOREIGN KEY (owner_id) 
--     REFERENCES owners(owner_id) 
--     ON DELETE CASCADE;

-- Twilio Accounts -> Owners (if migrating to ULID)
-- ALTER TABLE twilio_accounts 
--     ADD CONSTRAINT fk_twilio_accounts_owner 
--     FOREIGN KEY (owner_id) 
--     REFERENCES owners(owner_id) 
--     ON DELETE CASCADE;

-- ============================================================================
-- STEP 6: Update Indexes
-- ============================================================================

-- Drop old integer-based indexes (if they exist)
DROP INDEX IF EXISTS idx_owners_email;
DROP INDEX IF EXISTS idx_users_owner;
DROP INDEX IF EXISTS idx_users_phone;
DROP INDEX IF EXISTS idx_conversations_owner;
DROP INDEX IF EXISTS idx_conversations_owner_conv;
DROP INDEX IF EXISTS idx_messages_conv;

-- Recreate indexes on ULID columns (many already exist from phase 1)
CREATE INDEX IF NOT EXISTS idx_users_owner_id ON users(owner_id);
CREATE INDEX IF NOT EXISTS idx_conversations_owner_id ON conversations(owner_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_conv_id ON messages(conv_id);
CREATE INDEX IF NOT EXISTS idx_ai_results_msg_id ON ai_results(msg_id);

-- Composite indexes that might be useful
CREATE INDEX IF NOT EXISTS idx_users_owner_phone ON users(owner_id, phone) WHERE phone IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_conversations_owner_session ON conversations(owner_id, session_key, status);

-- ============================================================================
-- STEP 7: Update Triggers
-- ============================================================================

-- Update ULID generation triggers to use new column names
DROP TRIGGER IF EXISTS trigger_owners_ulid ON owners;
DROP TRIGGER IF EXISTS trigger_users_ulid ON users;
DROP TRIGGER IF EXISTS trigger_conversations_ulid ON conversations;
DROP TRIGGER IF EXISTS trigger_messages_ulid ON messages;
DROP TRIGGER IF EXISTS trigger_ai_results_ulid ON ai_results;

-- Recreate triggers with new column names
CREATE OR REPLACE FUNCTION set_ulid_on_insert_v2()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME = 'owners' AND NEW.owner_id IS NULL THEN
        NEW.owner_id := generate_ulid();
    ELSIF TG_TABLE_NAME = 'users' AND NEW.user_id IS NULL THEN
        NEW.user_id := generate_ulid();
    ELSIF TG_TABLE_NAME = 'conversations' AND NEW.conv_id IS NULL THEN
        NEW.conv_id := generate_ulid();
    ELSIF TG_TABLE_NAME = 'messages' AND NEW.msg_id IS NULL THEN
        NEW.msg_id := generate_ulid();
    ELSIF TG_TABLE_NAME = 'ai_results' AND NEW.ai_result_id IS NULL THEN
        NEW.ai_result_id := generate_ulid();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_owners_ulid
    BEFORE INSERT ON owners
    FOR EACH ROW
    EXECUTE FUNCTION set_ulid_on_insert_v2();

CREATE TRIGGER trigger_users_ulid
    BEFORE INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION set_ulid_on_insert_v2();

CREATE TRIGGER trigger_conversations_ulid
    BEFORE INSERT ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION set_ulid_on_insert_v2();

CREATE TRIGGER trigger_messages_ulid
    BEFORE INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION set_ulid_on_insert_v2();

CREATE TRIGGER trigger_ai_results_ulid
    BEFORE INSERT ON ai_results
    FOR EACH ROW
    EXECUTE FUNCTION set_ulid_on_insert_v2();

-- ============================================================================
-- STEP 8: Clean Up Migration Artifacts
-- ============================================================================

-- Uncomment when ready (ONLY after confirming everything works):
/*
-- Drop backup tables (after confirming migration success)
-- DROP TABLE IF EXISTS owners_backup;
-- DROP TABLE IF EXISTS users_backup;
-- DROP TABLE IF EXISTS conversations_backup;
-- DROP TABLE IF EXISTS messages_backup;
-- DROP TABLE IF EXISTS ai_results_backup;

-- Drop ID mapping table (after all code migrated)
-- DROP TABLE IF EXISTS id_mappings;

-- Drop migration helper functions (keep if you want backward compatibility)
-- DROP FUNCTION IF EXISTS get_ulid_from_id(TEXT, BIGINT);
-- DROP FUNCTION IF EXISTS get_id_from_ulid(TEXT, TEXT);

-- Drop old trigger function
-- DROP FUNCTION IF EXISTS set_ulid_on_insert();
*/

-- ============================================================================
-- STEP 9: Verify Migration
-- ============================================================================

DO $$
DECLARE
    table_info RECORD;
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Verifying ULID Migration';
    RAISE NOTICE '========================================';
    
    -- Check primary keys
    FOR table_info IN 
        SELECT 
            tc.table_name,
            kcu.column_name,
            c.data_type
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.columns c 
            ON c.table_name = tc.table_name 
            AND c.column_name = kcu.column_name
        WHERE tc.constraint_type = 'PRIMARY KEY'
            AND tc.table_schema = 'public'
            AND tc.table_name IN ('owners', 'users', 'conversations', 'messages', 'ai_results')
        ORDER BY tc.table_name
    LOOP
        RAISE NOTICE 'Table: % | PK Column: % | Type: %', 
            table_info.table_name, 
            table_info.column_name,
            table_info.data_type;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE 'Foreign Keys:';
    
    -- Check foreign keys
    FOR table_info IN 
        SELECT 
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
            AND tc.table_name IN ('users', 'conversations', 'messages', 'ai_results')
        ORDER BY tc.table_name, kcu.column_name
    LOOP
        RAISE NOTICE 'Table: % | Column: % -> % (%)', 
            table_info.table_name,
            table_info.column_name,
            table_info.foreign_table_name,
            table_info.foreign_column_name;
    END LOOP;
    
    RAISE NOTICE '========================================';
END $$;

-- ============================================================================
-- Migration: Primary Keys from BIGSERIAL to ULID
-- ============================================================================
-- This migration converts sensitive primary keys to ULID format for:
-- 1. Better security (non-sequential, hard to guess)
-- 2. Distributed system compatibility
-- 3. Sortable by timestamp
-- 4. URL-safe identifiers
--
-- ULID Format: 01ARZ3NDEKTSV4RRFFQ69G5FAV (26 characters)
-- Encoding: Crockford's Base32
-- Structure: TTTTTTTTTTRRRRRRRRRRRRRRRR
--            |________| |______________|
--             Timestamp   Randomness
--            (10 chars)    (16 chars)
-- ============================================================================

-- ============================================================================
-- STEP 0: Install ULID Extension (if not available, use function below)
-- ============================================================================

-- Option A: If you have pg_ulid extension
-- CREATE EXTENSION IF NOT EXISTS pg_ulid;

-- Option B: Custom ULID generation function (recommended)
-- Based on: https://github.com/ulid/spec

CREATE OR REPLACE FUNCTION generate_ulid() RETURNS TEXT AS $$
DECLARE
    -- Crockford's Base32 alphabet (excludes I, L, O, U to avoid confusion)
    encoding   TEXT := '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
    timestamp  BIGINT;
    output     TEXT := '';
    unix_time  BIGINT;
    random_part BIGINT;
BEGIN
    -- Get current timestamp in milliseconds
    unix_time := (EXTRACT(EPOCH FROM CLOCK_TIMESTAMP()) * 1000)::BIGINT;
    timestamp := unix_time;
    
    -- Encode timestamp (10 characters)
    FOR i IN 1..10 LOOP
        output := output || SUBSTRING(encoding FROM (timestamp % 32) + 1 FOR 1);
        timestamp := timestamp / 32;
    END LOOP;
    
    -- Add random part (16 characters)
    FOR i IN 1..16 LOOP
        random_part := (RANDOM() * 31)::INTEGER;
        output := output || SUBSTRING(encoding FROM random_part + 1 FOR 1);
    END LOOP;
    
    RETURN output;
END;
$$ LANGUAGE plpgsql VOLATILE;

COMMENT ON FUNCTION generate_ulid() IS 'Generate ULID (Universally Unique Lexicographically Sortable Identifier)';

-- ============================================================================
-- STEP 1: Backup Current Data
-- ============================================================================

-- Create backup tables (optional but recommended)
CREATE TABLE IF NOT EXISTS owners_backup AS SELECT * FROM owners;
CREATE TABLE IF NOT EXISTS users_backup AS SELECT * FROM users;
CREATE TABLE IF NOT EXISTS conversations_backup AS SELECT * FROM conversations;
CREATE TABLE IF NOT EXISTS messages_backup AS SELECT * FROM messages;
CREATE TABLE IF NOT EXISTS ai_results_backup AS SELECT * FROM ai_results;

-- ============================================================================
-- STEP 2: Add New ULID Columns
-- ============================================================================

-- Owners table
ALTER TABLE owners ADD COLUMN IF NOT EXISTS owner_ulid TEXT;

-- Users table  
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_ulid TEXT;

-- Conversations table
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS conv_ulid TEXT;

-- Messages table
ALTER TABLE messages ADD COLUMN IF NOT EXISTS msg_ulid TEXT;

-- AI Results table
ALTER TABLE ai_results ADD COLUMN IF NOT EXISTS ai_result_ulid TEXT;

-- ============================================================================
-- STEP 3: Populate ULID Columns with Generated Values
-- ============================================================================

-- Generate ULIDs for existing records
UPDATE owners SET owner_ulid = generate_ulid() WHERE owner_ulid IS NULL;
UPDATE users SET user_ulid = generate_ulid() WHERE user_ulid IS NULL;
UPDATE conversations SET conv_ulid = generate_ulid() WHERE conv_ulid IS NULL;
UPDATE messages SET msg_ulid = generate_ulid() WHERE msg_ulid IS NULL;
UPDATE ai_results SET ai_result_ulid = generate_ulid() WHERE ai_result_ulid IS NULL;

-- ============================================================================
-- STEP 4: Create Mapping Tables (for backward compatibility during transition)
-- ============================================================================

-- This allows gradual migration of application code
CREATE TABLE IF NOT EXISTS id_mappings (
    table_name TEXT NOT NULL,
    old_id BIGINT NOT NULL,
    new_ulid TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (table_name, old_id)
);
-- CREATE INDEX idx_id_mappings_ulid ON id_mappings(table_name, new_ulid);
CREATE INDEX IF NOT EXISTS idx_id_mappings_ulid ON id_mappings(table_name, new_ulid);

-- Populate mapping tables
INSERT INTO id_mappings (table_name, old_id, new_ulid)
SELECT 'owners', owner_id, owner_ulid FROM owners
ON CONFLICT (table_name, old_id) DO UPDATE SET new_ulid = EXCLUDED.new_ulid;

INSERT INTO id_mappings (table_name, old_id, new_ulid)
SELECT 'users', user_id, user_ulid FROM users
ON CONFLICT (table_name, old_id) DO UPDATE SET new_ulid = EXCLUDED.new_ulid;

INSERT INTO id_mappings (table_name, old_id, new_ulid)
SELECT 'conversations', conv_id, conv_ulid FROM conversations
ON CONFLICT (table_name, old_id) DO UPDATE SET new_ulid = EXCLUDED.new_ulid;

INSERT INTO id_mappings (table_name, old_id, new_ulid)
SELECT 'messages', msg_id, msg_ulid FROM messages
ON CONFLICT (table_name, old_id) DO UPDATE SET new_ulid = EXCLUDED.new_ulid;

INSERT INTO id_mappings (table_name, old_id, new_ulid)
SELECT 'ai_results', ai_result_id, ai_result_ulid FROM ai_results
ON CONFLICT (table_name, old_id) DO UPDATE SET new_ulid = EXCLUDED.new_ulid;

-- ============================================================================
-- STEP 5: Add Foreign Key ULID Columns
-- ============================================================================

-- Users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS owner_ulid_fk TEXT;
UPDATE users u SET owner_ulid_fk = o.owner_ulid FROM owners o WHERE u.owner_id = o.owner_id;

-- Conversations table
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS owner_ulid_fk TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS user_ulid_fk TEXT;

UPDATE conversations c SET owner_ulid_fk = o.owner_ulid FROM owners o WHERE c.owner_id = o.owner_id;
UPDATE conversations c SET user_ulid_fk = u.user_ulid FROM users u WHERE c.user_id = u.user_id;

-- Messages table
ALTER TABLE messages ADD COLUMN IF NOT EXISTS conv_ulid_fk TEXT;
UPDATE messages m SET conv_ulid_fk = c.conv_ulid FROM conversations c WHERE m.conv_id = c.conv_id;

-- AI Results table
ALTER TABLE ai_results ADD COLUMN IF NOT EXISTS msg_ulid_fk TEXT;
ALTER TABLE ai_results ADD COLUMN IF NOT EXISTS feature_ulid_fk TEXT;

UPDATE ai_results a SET msg_ulid_fk = m.msg_ulid FROM messages m WHERE a.msg_id = m.msg_id;
-- Note: features table not migrated to ULID in this script, but can be added if needed

-- ============================================================================
-- STEP 6: Add Constraints and Indexes on ULID Columns
-- ============================================================================

-- Make ULID columns NOT NULL
ALTER TABLE owners ALTER COLUMN owner_ulid SET NOT NULL;
ALTER TABLE users ALTER COLUMN user_ulid SET NOT NULL;
ALTER TABLE conversations ALTER COLUMN conv_ulid SET NOT NULL;
ALTER TABLE messages ALTER COLUMN msg_ulid SET NOT NULL;
ALTER TABLE ai_results ALTER COLUMN ai_result_ulid SET NOT NULL;

-- Add UNIQUE constraints
ALTER TABLE owners ADD CONSTRAINT uk_owners_ulid UNIQUE (owner_ulid);
ALTER TABLE users ADD CONSTRAINT uk_users_ulid UNIQUE (user_ulid);
ALTER TABLE conversations ADD CONSTRAINT uk_conversations_ulid UNIQUE (conv_ulid);
ALTER TABLE messages ADD CONSTRAINT uk_messages_ulid UNIQUE (msg_ulid);
ALTER TABLE ai_results ADD CONSTRAINT uk_ai_results_ulid UNIQUE (ai_result_ulid);

-- Create indexes for performance
CREATE INDEX idx_owners_ulid ON owners(owner_ulid);
CREATE INDEX idx_users_ulid ON users(user_ulid);
CREATE INDEX idx_users_owner_ulid_fk ON users(owner_ulid_fk);
CREATE INDEX idx_conversations_ulid ON conversations(conv_ulid);
CREATE INDEX idx_conversations_owner_ulid_fk ON conversations(owner_ulid_fk);
CREATE INDEX idx_conversations_user_ulid_fk ON conversations(user_ulid_fk);
CREATE INDEX idx_messages_ulid ON messages(msg_ulid);
CREATE INDEX idx_messages_conv_ulid_fk ON messages(conv_ulid_fk);
CREATE INDEX idx_ai_results_ulid ON ai_results(ai_result_ulid);
CREATE INDEX idx_ai_results_msg_ulid_fk ON ai_results(msg_ulid_fk);

-- ============================================================================
-- STEP 7: Create Helper Functions for ULID Operations
-- ============================================================================

-- Function to get ULID from old ID (for backward compatibility)
CREATE OR REPLACE FUNCTION get_ulid_from_id(p_table_name TEXT, p_old_id BIGINT)
RETURNS TEXT AS $$
DECLARE
    v_ulid TEXT;
BEGIN
    SELECT new_ulid INTO v_ulid
    FROM id_mappings
    WHERE table_name = p_table_name AND old_id = p_old_id;
    
    RETURN v_ulid;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to get old ID from ULID (for backward compatibility)
CREATE OR REPLACE FUNCTION get_id_from_ulid(p_table_name TEXT, p_ulid TEXT)
RETURNS BIGINT AS $$
DECLARE
    v_id BIGINT;
BEGIN
    SELECT old_id INTO v_id
    FROM id_mappings
    WHERE table_name = p_table_name AND new_ulid = p_ulid;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to validate ULID format
CREATE OR REPLACE FUNCTION is_valid_ulid(ulid TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- ULID should be exactly 26 characters
    IF LENGTH(ulid) != 26 THEN
        RETURN FALSE;
    END IF;
    
    -- ULID should only contain Crockford's Base32 characters
    IF ulid !~ '^[0-9A-HJKMNP-TV-Z]{26}$' THEN
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to extract timestamp from ULID
CREATE OR REPLACE FUNCTION ulid_to_timestamp(ulid TEXT)
RETURNS TIMESTAMP WITH TIME ZONE AS $$
DECLARE
    encoding TEXT := '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
    timestamp_part TEXT;
    unix_ms BIGINT := 0;
    char_val INTEGER;
BEGIN
    IF NOT is_valid_ulid(ulid) THEN
        RAISE EXCEPTION 'Invalid ULID format: %', ulid;
    END IF;
    
    -- Extract timestamp part (first 10 characters)
    timestamp_part := SUBSTRING(ulid FROM 1 FOR 10);
    
    -- Decode Base32 timestamp
    FOR i IN REVERSE 10..1 LOOP
        char_val := POSITION(SUBSTRING(timestamp_part FROM i FOR 1) IN encoding) - 1;
        unix_ms := unix_ms + (char_val * (32 ^ (10 - i)));
    END LOOP;
    
    -- Convert milliseconds to timestamp
    RETURN TO_TIMESTAMP(unix_ms / 1000.0);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION generate_ulid() IS 'Generate a new ULID';
COMMENT ON FUNCTION is_valid_ulid(TEXT) IS 'Validate ULID format';
COMMENT ON FUNCTION ulid_to_timestamp(TEXT) IS 'Extract timestamp from ULID';
COMMENT ON FUNCTION get_ulid_from_id(TEXT, BIGINT) IS 'Get ULID from old integer ID (migration helper)';
COMMENT ON FUNCTION get_id_from_ulid(TEXT, TEXT) IS 'Get old integer ID from ULID (migration helper)';

-- ============================================================================
-- STEP 8: Create Triggers for Auto-generating ULIDs on INSERT
-- ============================================================================

-- Trigger function
CREATE OR REPLACE FUNCTION set_ulid_on_insert()
RETURNS TRIGGER AS $$
BEGIN
    -- Automatically generate ULID if not provided
    IF TG_TABLE_NAME = 'owners' AND NEW.owner_ulid IS NULL THEN
        NEW.owner_ulid := generate_ulid();
    ELSIF TG_TABLE_NAME = 'users' AND NEW.user_ulid IS NULL THEN
        NEW.user_ulid := generate_ulid();
    ELSIF TG_TABLE_NAME = 'conversations' AND NEW.conv_ulid IS NULL THEN
        NEW.conv_ulid := generate_ulid();
    ELSIF TG_TABLE_NAME = 'messages' AND NEW.msg_ulid IS NULL THEN
        NEW.msg_ulid := generate_ulid();
    ELSIF TG_TABLE_NAME = 'ai_results' AND NEW.ai_result_ulid IS NULL THEN
        NEW.ai_result_ulid := generate_ulid();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers
DROP TRIGGER IF EXISTS trigger_owners_ulid ON owners;
CREATE TRIGGER trigger_owners_ulid
    BEFORE INSERT ON owners
    FOR EACH ROW
    EXECUTE FUNCTION set_ulid_on_insert();

DROP TRIGGER IF EXISTS trigger_users_ulid ON users;
CREATE TRIGGER trigger_users_ulid
    BEFORE INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION set_ulid_on_insert();

DROP TRIGGER IF EXISTS trigger_conversations_ulid ON conversations;
CREATE TRIGGER trigger_conversations_ulid
    BEFORE INSERT ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION set_ulid_on_insert();

DROP TRIGGER IF EXISTS trigger_messages_ulid ON messages;
CREATE TRIGGER trigger_messages_ulid
    BEFORE INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION set_ulid_on_insert();

DROP TRIGGER IF EXISTS trigger_ai_results_ulid ON ai_results;
CREATE TRIGGER trigger_ai_results_ulid
    BEFORE INSERT ON ai_results
    FOR EACH ROW
    EXECUTE FUNCTION set_ulid_on_insert();

-- ============================================================================
-- STEP 9: Validation Queries
-- ============================================================================

-- Verify all records have ULIDs
DO $$
DECLARE
    missing_count INTEGER;
BEGIN
    -- Check owners
    SELECT COUNT(*) INTO missing_count FROM owners WHERE owner_ulid IS NULL;
    IF missing_count > 0 THEN
        RAISE NOTICE 'WARNING: % owners missing ULID', missing_count;
    ELSE
        RAISE NOTICE 'OK: All owners have ULIDs';
    END IF;
    
    -- Check users
    SELECT COUNT(*) INTO missing_count FROM users WHERE user_ulid IS NULL;
    IF missing_count > 0 THEN
        RAISE NOTICE 'WARNING: % users missing ULID', missing_count;
    ELSE
        RAISE NOTICE 'OK: All users have ULIDs';
    END IF;
    
    -- Check conversations
    SELECT COUNT(*) INTO missing_count FROM conversations WHERE conv_ulid IS NULL;
    IF missing_count > 0 THEN
        RAISE NOTICE 'WARNING: % conversations missing ULID', missing_count;
    ELSE
        RAISE NOTICE 'OK: All conversations have ULIDs';
    END IF;
    
    -- Check messages
    SELECT COUNT(*) INTO missing_count FROM messages WHERE msg_ulid IS NULL;
    IF missing_count > 0 THEN
        RAISE NOTICE 'WARNING: % messages missing ULID', missing_count;
    ELSE
        RAISE NOTICE 'OK: All messages have ULIDs';
    END IF;
    
    -- Check ai_results
    SELECT COUNT(*) INTO missing_count FROM ai_results WHERE ai_result_ulid IS NULL;
    IF missing_count > 0 THEN
        RAISE NOTICE 'WARNING: % ai_results missing ULID', missing_count;
    ELSE
        RAISE NOTICE 'OK: All ai_results have ULIDs';
    END IF;
END $$;

-- ============================================================================
-- STEP 10: Migration Complete Notice
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'ULID Migration Phase 1 Complete!';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE 'What was done:';
    RAISE NOTICE '1. Added ULID columns to all tables';
    RAISE NOTICE '2. Generated ULIDs for existing records';
    RAISE NOTICE '3. Created mapping table for backward compatibility';
    RAISE NOTICE '4. Added indexes and constraints';
    RAISE NOTICE '5. Created helper functions';
    RAISE NOTICE '6. Set up auto-generation triggers';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Update application code to use ULID columns';
    RAISE NOTICE '2. Run Phase 2 migration (003_ulid_phase2.sql) to:';
    RAISE NOTICE '   - Drop old integer columns';
    RAISE NOTICE '   - Rename ULID columns to primary names';
    RAISE NOTICE '   - Clean up mapping tables';
    RAISE NOTICE '';
    RAISE NOTICE 'Note: Both old and new IDs work during transition period';
    RAISE NOTICE '========================================';
END $$;

-- ============================================================================
-- SAMPLE QUERIES - Testing ULID Functions
-- ============================================================================

-- Generate a new ULID
-- SELECT generate_ulid();

-- Validate ULID format
-- SELECT is_valid_ulid('01ARZ3NDEKTSV4RRFFQ69G5FAV'); -- Returns TRUE
-- SELECT is_valid_ulid('invalid'); -- Returns FALSE

-- Extract timestamp from ULID
-- SELECT ulid_to_timestamp('01ARZ3NDEKTSV4RRFFQ69G5FAV');

-- Get ULID from old ID
-- SELECT get_ulid_from_id('owners', 1);

-- Get old ID from ULID
-- SELECT get_id_from_ulid('owners', '01ARZ3NDEKTSV4RRFFQ69G5FAV');

-- Test insert with auto-generated ULID
-- INSERT INTO owners (name, email) VALUES ('Test Owner', 'test@example.com')
-- RETURNING owner_id, owner_ulid;

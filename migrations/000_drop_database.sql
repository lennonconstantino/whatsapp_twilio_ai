-- ============================================================================
-- DROP DATABASE - Remove all objects in correct dependency order
-- ============================================================================
-- WARNING: This script will permanently delete all data and objects!
-- Execute with caution.
-- ============================================================================

-- Disable foreign key checks temporarily
SET session_replication_role = 'replica';

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Starting database cleanup...';
    RAISE NOTICE '==============================================';
END $$;

-- ============================================================================
-- 1. DROP VIEWS
-- ============================================================================


-- ============================================================================
-- 2. DROP TABLES (in reverse dependency order)
-- ============================================================================

-- Drop child tables first (tables with foreign keys)
DROP TABLE IF EXISTS conversation_state_history CASCADE;
DROP TABLE IF EXISTS ai_results CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS message_embeddings CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS plan_features CASCADE;
DROP TABLE IF EXISTS plans CASCADE;
DROP TABLE IF EXISTS twilio_accounts CASCADE;
DROP TABLE IF EXISTS features CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop parent tables last
DROP TABLE IF EXISTS owners CASCADE;

-- ============================================================================
-- 3. DROP FUNCTIONS
-- ============================================================================
DROP FUNCTION IF EXISTS search_message_embeddings_hybrid_rrf(text, extensions.vector, int, double precision, jsonb, double precision, double precision, int, text) CASCADE;
DROP FUNCTION IF EXISTS search_message_embeddings_text(text, int, jsonb, text) CASCADE;
DROP FUNCTION IF EXISTS match_message_embeddings(extensions.vector, float, int, jsonb) CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS generate_ulid() CASCADE;
DROP FUNCTION IF EXISTS is_valid_ulid(TEXT) CASCADE;
DROP FUNCTION IF EXISTS ulid_to_timestamp(TEXT) CASCADE;
DROP FUNCTION IF EXISTS set_history_id_on_insert() CASCADE;
DROP FUNCTION IF EXISTS set_ulid_on_insert() CASCADE;
DROP FUNCTION IF EXISTS set_ulid_on_insert_v2() CASCADE;
DROP FUNCTION IF EXISTS set_owners_id_on_insert() CASCADE;
DROP FUNCTION IF EXISTS set_users_id_on_insert() CASCADE;
DROP FUNCTION IF EXISTS set_conv_id_on_insert() CASCADE;
DROP FUNCTION IF EXISTS set_msg_id_on_insert() CASCADE;
DROP FUNCTION IF EXISTS get_ulid_from_id(BIGINT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_id_from_ulid(TEXT, TEXT) CASCADE;

-- ============================================================================
-- 4. DROP INDEXES (if any standalone indexes remain)
-- ============================================================================
-- Most indexes are dropped with their tables via CASCADE
-- This section is for any orphaned indexes

-- ============================================================================
-- 5. DROP TYPES (if any custom types exist)
-- ============================================================================
-- Add custom types here if needed

-- ============================================================================
-- 6. DROP EXTENSIONS (optional - be careful with shared extensions)
-- ============================================================================
-- Uncomment if you want to remove extensions
DROP EXTENSION IF EXISTS vector CASCADE;
DROP EXTENSION IF EXISTS "uuid-ossp" CASCADE;
DROP EXTENSION IF EXISTS pg_trgm CASCADE;

-- ============================================================================
-- 7. DROP SCHEMAS (optional - only if you created custom schemas)
-- ============================================================================
DROP SCHEMA IF EXISTS extensions CASCADE;

-- Re-enable foreign key checks
SET session_replication_role = 'origin';

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Database cleanup completed!';
    RAISE NOTICE 'All tables, functions, and views removed.';
    RAISE NOTICE '==============================================';
END $$;

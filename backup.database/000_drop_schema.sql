-- ============================================================================
-- Owner Project - Database Cleanup Script
-- Removes all database objects in correct dependency order
-- ============================================================================

-- Disable foreign key checks temporarily
SET session_replication_role = 'replica';

-- ============================================================================
-- 1. DROP TABLES (in reverse dependency order)
-- ============================================================================
-- Drop child tables first
DROP TABLE IF EXISTS reminder CASCADE;
DROP TABLE IF EXISTS interaction CASCADE;
DROP TABLE IF EXISTS person CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS plan_features CASCADE;
DROP TABLE IF EXISTS plans CASCADE;
DROP TABLE IF EXISTS conversation_state_history CASCADE;
DROP TABLE IF EXISTS ai_results CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS twilio_accounts CASCADE;
DROP TABLE IF EXISTS features CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS owners CASCADE;

DROP TABLE IF EXISTS message_embeddings CASCADE;

-- ============================================================================
-- 2. DROP TABLEs Features
-- ============================================================================
-- relationships
DROP TABLE IF EXISTS person CASCADE;
DROP TABLE IF EXISTS interaction CASCADE;
DROP TABLE IF EXISTS reminder CASCADE;

-- Finance
DROP TABLE IF EXISTS revenue CASCADE;
DROP TABLE IF EXISTS expense CASCADE;
DROP TABLE IF EXISTS customer CASCADE;
DROP TABLE IF EXISTS invoice CASCADE;

-- ============================================================================
-- 2. DROP FUNCTIONS
-- ============================================================================
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS generate_ulid() CASCADE;
DROP FUNCTION IF EXISTS is_valid_ulid(TEXT) CASCADE;
DROP FUNCTION IF EXISTS ulid_to_timestamp(TEXT) CASCADE;
DROP FUNCTION IF EXISTS set_ulid_on_insert() CASCADE;
DROP FUNCTION IF EXISTS set_ulid_on_insert_v2() CASCADE;
DROP FUNCTION IF EXISTS set_owners_id_on_insert() CASCADE;
DROP FUNCTION IF EXISTS set_users_id_on_insert() CASCADE;
DROP FUNCTION IF EXISTS set_conversations_id_on_insert() CASCADE;
DROP FUNCTION IF EXISTS set_messages_id_on_insert() CASCADE;
DROP FUNCTION IF EXISTS set_ai_results_id_on_insert() CASCADE;

-- ============================================================================
-- 3. DROP EXTENSIONS (optional - only if needed)
-- ============================================================================
-- Uncomment if you want to remove the extension completely
-- DROP EXTENSION IF EXISTS "uuid-ossp" CASCADE;

-- Re-enable foreign key checks
SET session_replication_role = 'origin';

-- ============================================================================
-- Completion Message
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Database cleanup completed successfully!';
    RAISE NOTICE 'All tables and functions removed.';
    RAISE NOTICE '==============================================';
END $$;

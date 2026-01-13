-- ============================================================================
-- Owner Project - Database Cleanup Script
-- Removes all database objects in correct dependency order
-- ============================================================================

-- Disable foreign key checks temporarily
SET session_replication_role = 'replica';

-- ============================================================================
-- 1. DROP POLICIES (Row Level Security)
-- ============================================================================
DROP POLICY IF EXISTS "Enable read access for all users" ON owners;
DROP POLICY IF EXISTS "Users can view own owner's users" ON users;
DROP POLICY IF EXISTS "Features viewable by owner" ON features;
DROP POLICY IF EXISTS "Conversations viewable by owner" ON conversations;
DROP POLICY IF EXISTS "Messages viewable via conversation" ON messages;

-- ============================================================================
-- 2. DISABLE ROW LEVEL SECURITY
-- ============================================================================
ALTER TABLE IF EXISTS owners DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS users DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS features DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS twilio_accounts DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS conversations DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ai_results DISABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 3. DROP TRIGGERS
-- ============================================================================
-- Update timestamp triggers
DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
DROP TRIGGER IF EXISTS update_features_updated_at ON features;

-- ULID generation triggers
DROP TRIGGER IF EXISTS trigger_owners_ulid ON owners;
DROP TRIGGER IF EXISTS trigger_users_ulid ON users;
DROP TRIGGER IF EXISTS trigger_conversations_ulid ON conversations;
DROP TRIGGER IF EXISTS trigger_messages_ulid ON messages;
DROP TRIGGER IF EXISTS trigger_ai_results_ulid ON ai_results;
DROP TRIGGER IF EXISTS set_ulid_on_insert ON messages;
DROP TRIGGER IF EXISTS trigger_set_ulid_on_insert ON messages;

-- ============================================================================
-- 4. DROP FUNCTIONS
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
-- 5. DROP JSONB INDEXES
-- ============================================================================
-- Features table JSONB indexes
DROP INDEX IF EXISTS idx_features_config_gin;
DROP INDEX IF EXISTS idx_features_config_enabled;

-- Twilio accounts table JSONB indexes
DROP INDEX IF EXISTS idx_twilio_phone_numbers_gin;

-- Conversations table JSONB indexes
DROP INDEX IF EXISTS idx_conversations_context_gin;
DROP INDEX IF EXISTS idx_conversations_metadata_gin;
DROP INDEX IF EXISTS idx_conversations_context_status;
DROP INDEX IF EXISTS idx_conversations_metadata_priority;

-- Messages table JSONB indexes
DROP INDEX IF EXISTS idx_messages_metadata_gin;
DROP INDEX IF EXISTS idx_messages_metadata_delivery_status;

-- AI results table JSONB indexes
DROP INDEX IF EXISTS idx_ai_results_json_gin;
DROP INDEX IF EXISTS idx_ai_results_json_confidence;
DROP INDEX IF EXISTS idx_ai_results_json_category;

-- ============================================================================
-- 6. DROP STANDARD INDEXES
-- ============================================================================
-- Session key indexes
DROP INDEX IF EXISTS idx_conversations_session_key_active;
DROP INDEX IF EXISTS idx_conversations_session_key;

-- ULID indexes
DROP INDEX IF EXISTS idx_owners_ulid;
DROP INDEX IF EXISTS idx_users_ulid;
DROP INDEX IF EXISTS idx_users_owner_ulid_fk;
DROP INDEX IF EXISTS idx_conversations_ulid;
DROP INDEX IF EXISTS idx_conversations_owner_ulid_fk;
DROP INDEX IF EXISTS idx_conversations_user_ulid_fk;
DROP INDEX IF EXISTS idx_messages_ulid;
DROP INDEX IF EXISTS idx_messages_conv_ulid_fk;
DROP INDEX IF EXISTS idx_ai_results_ulid;
DROP INDEX IF EXISTS idx_ai_results_msg_ulid_fk;

-- Additional indexes
DROP INDEX IF EXISTS idx_users_owner_id;
DROP INDEX IF EXISTS idx_conversations_owner_id;
DROP INDEX IF EXISTS idx_conversations_user_id;
DROP INDEX IF EXISTS idx_messages_conv_id;
DROP INDEX IF EXISTS idx_messages_owner_id;
DROP INDEX IF EXISTS idx_ai_results_msg_id;
DROP INDEX IF EXISTS idx_users_owner_phone;
DROP INDEX IF EXISTS idx_conversations_owner_session;
DROP INDEX IF EXISTS idx_features_owner_id;
DROP INDEX IF EXISTS idx_twilio_accounts_owner_id;

-- ============================================================================
-- 7. DROP TABLES (in reverse dependency order)
-- ============================================================================
-- Drop child tables first
DROP TABLE IF EXISTS ai_results CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS twilio_accounts CASCADE;
DROP TABLE IF EXISTS features CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS owners CASCADE;

-- ============================================================================
-- 8. DROP EXTENSIONS (optional - only if needed)
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
    RAISE NOTICE 'All tables, triggers, policies and indexes removed.';
    RAISE NOTICE '==============================================';
END $$;

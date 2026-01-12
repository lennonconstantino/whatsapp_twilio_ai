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
DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
DROP TRIGGER IF EXISTS update_features_updated_at ON features;

-- ============================================================================
-- 4. DROP FUNCTIONS
-- ============================================================================
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

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
DROP INDEX IF EXISTS idx_conversations_session_key_active;
DROP INDEX IF EXISTS idx_conversations_session_key;

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

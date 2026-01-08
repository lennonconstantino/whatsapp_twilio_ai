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
-- 5. DROP TABLES (in reverse dependency order)
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
-- 6. DROP EXTENSIONS (optional - only if needed)
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
    RAISE NOTICE 'All tables, triggers, and policies removed.';
    RAISE NOTICE '==============================================';
END $$;

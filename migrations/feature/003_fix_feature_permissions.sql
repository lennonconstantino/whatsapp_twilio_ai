-- ============================================================================
-- MIGRATION: FIX FEATURE TABLES PERMISSIONS
-- ============================================================================
-- Explicitly grant permissions to feature tables (finance, relationships)
-- and CORE tables (conversations, messages) to fix permission denied errors
-- ============================================================================

-- Set search path
SET search_path = app, extensions, public;

-- ============================================================================
-- 1. Grant USAGE on SCHEMA
-- ============================================================================

GRANT USAGE ON SCHEMA app TO service_role;
GRANT USAGE ON SCHEMA app TO authenticated;
GRANT USAGE ON SCHEMA app TO anon;

-- ============================================================================
-- 2. Grant Permissions on CORE Tables (Fixing 42501 Error)
-- ============================================================================

-- Grant ALL privileges to service_role (Admin/Worker)
GRANT ALL ON ALL TABLES IN SCHEMA app TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA app TO service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA app TO service_role;

-- Grant ALL privileges to authenticated users (RLS will restrict data access)
GRANT ALL ON ALL TABLES IN SCHEMA app TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA app TO authenticated;
GRANT ALL ON ALL ROUTINES IN SCHEMA app TO authenticated;

-- ============================================================================
-- 3. Explicit Grants for Critical Tables (Safety Net)
-- ============================================================================

GRANT ALL ON TABLE app.conversations TO service_role;
GRANT ALL ON TABLE app.conversations TO authenticated;

GRANT ALL ON TABLE app.messages TO service_role;
GRANT ALL ON TABLE app.messages TO authenticated;

GRANT ALL ON TABLE app.ai_results TO service_role;
GRANT ALL ON TABLE app.ai_results TO authenticated;

GRANT ALL ON TABLE app.conversation_state_history TO service_role;
GRANT ALL ON TABLE app.conversation_state_history TO authenticated;

-- ============================================================================
-- 4. Future Tables Default Permissions
-- ============================================================================

ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON TABLES TO authenticated;

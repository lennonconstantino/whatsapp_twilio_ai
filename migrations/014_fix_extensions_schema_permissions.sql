-- ============================================================================
-- FIX EXTENSIONS SCHEMA PERMISSIONS
-- ============================================================================
-- Grants USAGE on extensions schema to service_role and other roles
-- This is required for accessing types like 'vector' and functions in extensions schema
-- ============================================================================

-- Set search path for this session
SET search_path = app, extensions, public;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Fixing extensions schema permissions...';
    RAISE NOTICE '==============================================';
END $$;

-- 1. Grant USAGE on schema extensions
-- Service Role (Admin/Backend)
GRANT USAGE ON SCHEMA extensions TO service_role;
-- Authenticated Users (if they need to insert vectors directly via RLS)
GRANT USAGE ON SCHEMA extensions TO authenticated;
-- Anonymous Users (usually not needed, but good for public search functions if any)
GRANT USAGE ON SCHEMA extensions TO anon;

-- 2. Grant ALL on functions in schema extensions
-- This covers vector similarity operators and other extension functions
GRANT ALL ON ALL FUNCTIONS IN SCHEMA extensions TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA extensions TO authenticated;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA extensions TO anon;

-- 3. Ensure privileges on existing tables in extensions (if any)
GRANT ALL ON ALL TABLES IN SCHEMA extensions TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA extensions TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA extensions TO anon;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Permissions granted on extensions schema!';
    RAISE NOTICE '✓ USAGE granted to service_role, authenticated, anon';
    RAISE NOTICE '✓ EXECUTE on functions granted';
    RAISE NOTICE '==============================================';
END $$;

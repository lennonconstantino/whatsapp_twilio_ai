-- ============================================================================
-- SET SEARCH PATH
-- ============================================================================
-- Ensure the application uses the correct schemas by default
-- ============================================================================

-- Set search path for the current database user
ALTER ROLE CURRENT_USER SET search_path TO app, extensions, public;

-- Also try to set it for the database itself (might require superuser)
DO $$
BEGIN
    EXECUTE 'ALTER DATABASE ' || current_database() || ' SET search_path TO app, extensions, public';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Could not set search_path on database level (requires superuser?). Skipping.';
END $$;

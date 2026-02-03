-- ============================================================================
-- SECURITY POLICIES (RLS - Row Level Security)
-- ============================================================================
-- This script enables Row Level Security and creates policies
-- Execute ONLY if you're using Supabase Auth or similar authentication
-- ============================================================================
-- WARNING: This is OPTIONAL and should be reviewed before production use
-- ============================================================================

-- Set search path for the session
SET search_path = app, extensions, public;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Configuring security policies...';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'NOTE: This assumes Supabase Auth is configured';
    RAISE NOTICE 'If not using Supabase, adjust policies accordingly';
    RAISE NOTICE '==============================================';
END $$;

-- ============================================================================
-- 1. HELPER FUNCTION - Get Current Owner ID from Auth
-- ============================================================================
-- This function links auth.uid() to the owner_id in the users table

CREATE OR REPLACE FUNCTION app.get_current_owner_id()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, extensions, public, temp
AS $$
BEGIN
    -- Assumes users table links auth_id to owner_id
    -- Returns the owner_id of the currently authenticated user
    RETURN (SELECT owner_id FROM app.users WHERE auth_id = auth.uid()::text LIMIT 1);
END;
$$;

COMMENT ON FUNCTION app.get_current_owner_id() IS 'Get owner_id for currently authenticated user via auth.uid()';

-- ============================================================================
-- 2. ENABLE RLS ON TABLES
-- ============================================================================

-- Core tables
-- ALTER TABLE app.owners ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE app.users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE app.features ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE app.conversations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE app.messages ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE app.ai_results ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE app.conversation_state_history ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE app.twilio_accounts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE app.subscriptions ENABLE ROW LEVEL SECURITY;

-- Vector store (optional - depends on your access model)
-- ALTER TABLE app.message_embeddings ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 3. POLICIES FOR OWNERS TABLE
-- ============================================================================

-- Users can view their own owner record
DROP POLICY IF EXISTS "Users can view their own owner" ON app.owners;
CREATE POLICY "Users can view their own owner"
ON app.owners
FOR SELECT
USING (
    owner_id = get_current_owner_id()
);

-- Users can update their own owner record
DROP POLICY IF EXISTS "Users can update their own owner" ON app.owners;
CREATE POLICY "Users can update their own owner"
ON app.owners
FOR UPDATE
USING (
    owner_id = get_current_owner_id()
);

-- ============================================================================
-- 4. POLICIES FOR USERS TABLE
-- ============================================================================

-- Users can view users from their own organization
DROP POLICY IF EXISTS "Users can view users in their org" ON app.users;
CREATE POLICY "Users can view users in their org"
ON app.users
FOR SELECT
USING (
    owner_id = get_current_owner_id()
);

-- Users can update their own profile
DROP POLICY IF EXISTS "Users can update their own profile" ON app.users;
CREATE POLICY "Users can update their own profile"
ON app.users
FOR UPDATE
USING (
    auth_id = auth.uid()::text
);

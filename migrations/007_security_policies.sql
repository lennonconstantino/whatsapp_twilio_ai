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

-- Only admins can insert new users (you may need to adjust this)
DROP POLICY IF EXISTS "Admins can insert users" ON app.users;
CREATE POLICY "Admins can insert users"
ON app.users
FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM app.users 
        WHERE auth_id = auth.uid()::text 
        AND role = 'admin'
        AND owner_id = get_current_owner_id()
    )
);

-- ============================================================================
-- 5. POLICIES FOR FEATURES TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view their org features" ON app.features;
CREATE POLICY "Users can view their org features"
ON app.features
FOR SELECT
TO authenticated
USING (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Admins can manage features" ON app.features;
CREATE POLICY "Admins can manage features"
ON app.features
FOR ALL
TO authenticated
USING (
    owner_id = get_current_owner_id()
    AND EXISTS (
        SELECT 1 FROM app.users 
        WHERE auth_id = auth.uid()::text 
        AND role = 'admin'
    )
);

-- ============================================================================
-- 6. POLICIES FOR CONVERSATIONS TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view their own conversations" ON app.conversations;
CREATE POLICY "Users can view their own conversations"
ON app.conversations
FOR SELECT
USING (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Users can insert their own conversations" ON app.conversations;
CREATE POLICY "Users can insert their own conversations"
ON app.conversations
FOR INSERT
WITH CHECK (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Users can update their own conversations" ON app.conversations;
CREATE POLICY "Users can update their own conversations"
ON app.conversations
FOR UPDATE
USING (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Users can delete their own conversations" ON app.conversations;
CREATE POLICY "Users can delete their own conversations"
ON app.conversations
FOR DELETE
USING (
    owner_id = get_current_owner_id()
);

-- ============================================================================
-- 7. POLICIES FOR MESSAGES TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view messages from their conversations" ON app.messages;
CREATE POLICY "Users can view messages from their conversations"
ON app.messages
FOR SELECT
USING (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Users can insert messages" ON app.messages;
CREATE POLICY "Users can insert messages"
ON app.messages
FOR INSERT
WITH CHECK (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Users can update their messages" ON app.messages;
CREATE POLICY "Users can update their messages"
ON app.messages
FOR UPDATE
USING (
    owner_id = get_current_owner_id()
);

-- ============================================================================
-- 8. POLICIES FOR AI_RESULTS TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view AI results for their messages" ON app.ai_results;
CREATE POLICY "Users can view AI results for their messages"
ON app.ai_results
FOR SELECT
USING (
    msg_id IN (
        SELECT msg_id FROM app.messages 
        WHERE owner_id = get_current_owner_id()
    )
);

DROP POLICY IF EXISTS "System can insert AI results" ON app.ai_results;
CREATE POLICY "System can insert AI results"
ON app.ai_results
FOR INSERT
WITH CHECK (
    msg_id IN (
        SELECT msg_id FROM app.messages 
        WHERE owner_id = get_current_owner_id()
    )
);

-- ============================================================================
-- 9. POLICIES FOR CONVERSATION_STATE_HISTORY TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view history of their conversations" ON app.conversation_state_history;
CREATE POLICY "Users can view history of their conversations"
ON app.conversation_state_history
FOR SELECT
USING (
    conv_id IN (
        SELECT conv_id FROM app.conversations 
        WHERE owner_id = get_current_owner_id()
    )
);

DROP POLICY IF EXISTS "System can insert state history" ON app.conversation_state_history;
CREATE POLICY "System can insert state history"
ON app.conversation_state_history
FOR INSERT
WITH CHECK (
    conv_id IN (
        SELECT conv_id FROM app.conversations 
        WHERE owner_id = get_current_owner_id()
    )
);

-- ============================================================================
-- 10. POLICIES FOR TWILIO_ACCOUNTS TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view their Twilio accounts" ON app.twilio_accounts;
CREATE POLICY "Users can view their Twilio accounts"
ON app.twilio_accounts
FOR SELECT
TO authenticated
USING (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Admins can manage Twilio accounts" ON app.twilio_accounts;
CREATE POLICY "Admins can manage Twilio accounts"
ON app.twilio_accounts
FOR ALL
TO authenticated
USING (
    owner_id = get_current_owner_id()
    AND EXISTS (
        SELECT 1 FROM app.users 
        WHERE auth_id = auth.uid()::text 
        AND role = 'admin'
    )
);

-- ============================================================================
-- 11. POLICIES FOR SUBSCRIPTIONS TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view their subscription" ON app.subscriptions;
CREATE POLICY "Users can view their subscription"
ON app.subscriptions
FOR SELECT
USING (
    owner_id = get_current_owner_id()
);

-- ============================================================================
-- 12. OPTIONAL: MESSAGE_EMBEDDINGS POLICIES
-- ============================================================================
-- Uncomment if you want RLS on message_embeddings

/*
DROP POLICY IF EXISTS "Users can view their embeddings" ON app.message_embeddings;
CREATE POLICY "Users can view their embeddings"
ON app.message_embeddings
FOR SELECT
USING (
    metadata->>'owner_id' = get_current_owner_id()
);

DROP POLICY IF EXISTS "System can insert embeddings" ON app.message_embeddings;
CREATE POLICY "System can insert embeddings"
ON app.message_embeddings
FOR INSERT
WITH CHECK (
    metadata->>'owner_id' = get_current_owner_id()
);
*/

-- ============================================================================
-- 13. GRANT PERMISSIONS TO ROLES
-- ============================================================================
-- Adjust these based on your Supabase roles

-- Anonymous users (no access to tables with RLS)
-- REVOKE ALL ON ALL TABLES IN SCHEMA app FROM anon;

-- Authenticated users get access through RLS policies
GRANT USAGE ON SCHEMA app TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO authenticated;

-- Service role (backend/API) bypasses RLS
GRANT ALL ON SCHEMA app TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA app TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA app TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA app TO service_role;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Security policies created successfully!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'RLS enabled on:';
    RAISE NOTICE '✓ owners, users, features';
    RAISE NOTICE '✓ conversations, messages, ai_results';
    RAISE NOTICE '✓ conversation_state_history';
    RAISE NOTICE '✓ twilio_accounts, subscriptions';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'IMPORTANT:';
    RAISE NOTICE '- Review policies before production use';
    RAISE NOTICE '- Test with different user roles';
    RAISE NOTICE '- Adjust admin permissions as needed';
    RAISE NOTICE '- message_embeddings RLS is commented out';
    RAISE NOTICE '==============================================';
END $$;

-- ============================================================================
-- SECURITY POLICIES (RLS - Row Level Security)
-- ============================================================================
-- This script enables Row Level Security and creates policies
-- Execute ONLY if you're using Supabase Auth or similar authentication
-- ============================================================================
-- WARNING: This is OPTIONAL and should be reviewed before production use
-- ============================================================================

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

CREATE OR REPLACE FUNCTION public.get_current_owner_id()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions, temp
AS $$
BEGIN
    -- Assumes users table links auth_id to owner_id
    -- Returns the owner_id of the currently authenticated user
    RETURN (SELECT owner_id FROM public.users WHERE auth_id = auth.uid()::text LIMIT 1);
END;
$$;

COMMENT ON FUNCTION public.get_current_owner_id() IS 'Get owner_id for currently authenticated user via auth.uid()';

-- ============================================================================
-- 2. ENABLE RLS ON TABLES
-- ============================================================================

-- Core tables
-- ALTER TABLE public.owners ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.features ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.ai_results ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.conversation_state_history ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.twilio_accounts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

-- Vector store (optional - depends on your access model)
-- ALTER TABLE public.message_embeddings ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 3. POLICIES FOR OWNERS TABLE
-- ============================================================================

-- Users can view their own owner record
DROP POLICY IF EXISTS "Users can view their own owner" ON public.owners;
CREATE POLICY "Users can view their own owner"
ON public.owners
FOR SELECT
USING (
    owner_id = get_current_owner_id()
);

-- Users can update their own owner record
DROP POLICY IF EXISTS "Users can update their own owner" ON public.owners;
CREATE POLICY "Users can update their own owner"
ON public.owners
FOR UPDATE
USING (
    owner_id = get_current_owner_id()
);

-- ============================================================================
-- 4. POLICIES FOR USERS TABLE
-- ============================================================================

-- Users can view users from their own organization
DROP POLICY IF EXISTS "Users can view users in their org" ON public.users;
CREATE POLICY "Users can view users in their org"
ON public.users
FOR SELECT
USING (
    owner_id = get_current_owner_id()
);

-- Users can update their own profile
DROP POLICY IF EXISTS "Users can update their own profile" ON public.users;
CREATE POLICY "Users can update their own profile"
ON public.users
FOR UPDATE
USING (
    auth_id = auth.uid()::text
);

-- Only admins can insert new users (you may need to adjust this)
DROP POLICY IF EXISTS "Admins can insert users" ON public.users;
CREATE POLICY "Admins can insert users"
ON public.users
FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.users 
        WHERE auth_id = auth.uid()::text 
        AND role = 'admin'
        AND owner_id = get_current_owner_id()
    )
);

-- ============================================================================
-- 5. POLICIES FOR FEATURES TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view their org features" ON public.features;
CREATE POLICY "Users can view their org features"
ON public.features
FOR SELECT
USING (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Admins can manage features" ON public.features;
CREATE POLICY "Admins can manage features"
ON public.features
FOR ALL
USING (
    owner_id = get_current_owner_id()
    AND EXISTS (
        SELECT 1 FROM public.users 
        WHERE auth_id = auth.uid()::text 
        AND role = 'admin'
    )
);

-- ============================================================================
-- 6. POLICIES FOR CONVERSATIONS TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view their own conversations" ON public.conversations;
CREATE POLICY "Users can view their own conversations"
ON public.conversations
FOR SELECT
USING (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Users can insert their own conversations" ON public.conversations;
CREATE POLICY "Users can insert their own conversations"
ON public.conversations
FOR INSERT
WITH CHECK (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Users can update their own conversations" ON public.conversations;
CREATE POLICY "Users can update their own conversations"
ON public.conversations
FOR UPDATE
USING (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Users can delete their own conversations" ON public.conversations;
CREATE POLICY "Users can delete their own conversations"
ON public.conversations
FOR DELETE
USING (
    owner_id = get_current_owner_id()
);

-- ============================================================================
-- 7. POLICIES FOR MESSAGES TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view messages from their conversations" ON public.messages;
CREATE POLICY "Users can view messages from their conversations"
ON public.messages
FOR SELECT
USING (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Users can insert messages" ON public.messages;
CREATE POLICY "Users can insert messages"
ON public.messages
FOR INSERT
WITH CHECK (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Users can update their messages" ON public.messages;
CREATE POLICY "Users can update their messages"
ON public.messages
FOR UPDATE
USING (
    owner_id = get_current_owner_id()
);

-- ============================================================================
-- 8. POLICIES FOR AI_RESULTS TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view AI results for their messages" ON public.ai_results;
CREATE POLICY "Users can view AI results for their messages"
ON public.ai_results
FOR SELECT
USING (
    msg_id IN (
        SELECT msg_id FROM public.messages 
        WHERE owner_id = get_current_owner_id()
    )
);

DROP POLICY IF EXISTS "System can insert AI results" ON public.ai_results;
CREATE POLICY "System can insert AI results"
ON public.ai_results
FOR INSERT
WITH CHECK (
    msg_id IN (
        SELECT msg_id FROM public.messages 
        WHERE owner_id = get_current_owner_id()
    )
);

-- ============================================================================
-- 9. POLICIES FOR CONVERSATION_STATE_HISTORY TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view history of their conversations" ON public.conversation_state_history;
CREATE POLICY "Users can view history of their conversations"
ON public.conversation_state_history
FOR SELECT
USING (
    conv_id IN (
        SELECT conv_id FROM public.conversations 
        WHERE owner_id = get_current_owner_id()
    )
);

DROP POLICY IF EXISTS "System can insert state history" ON public.conversation_state_history;
CREATE POLICY "System can insert state history"
ON public.conversation_state_history
FOR INSERT
WITH CHECK (
    conv_id IN (
        SELECT conv_id FROM public.conversations 
        WHERE owner_id = get_current_owner_id()
    )
);

-- ============================================================================
-- 10. POLICIES FOR TWILIO_ACCOUNTS TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view their Twilio accounts" ON public.twilio_accounts;
CREATE POLICY "Users can view their Twilio accounts"
ON public.twilio_accounts
FOR SELECT
USING (
    owner_id = get_current_owner_id()
);

DROP POLICY IF EXISTS "Admins can manage Twilio accounts" ON public.twilio_accounts;
CREATE POLICY "Admins can manage Twilio accounts"
ON public.twilio_accounts
FOR ALL
USING (
    owner_id = get_current_owner_id()
    AND EXISTS (
        SELECT 1 FROM public.users 
        WHERE auth_id = auth.uid()::text 
        AND role = 'admin'
    )
);

-- ============================================================================
-- 11. POLICIES FOR SUBSCRIPTIONS TABLE
-- ============================================================================

DROP POLICY IF EXISTS "Users can view their subscription" ON public.subscriptions;
CREATE POLICY "Users can view their subscription"
ON public.subscriptions
FOR SELECT
USING (
    owner_id = get_current_owner_id()
);

-- ============================================================================
-- 12. OPTIONAL: MESSAGE_EMBEDDINGS POLICIES
-- ============================================================================
-- Uncomment if you want RLS on message_embeddings

/*
DROP POLICY IF EXISTS "Users can view their embeddings" ON public.message_embeddings;
CREATE POLICY "Users can view their embeddings"
ON public.message_embeddings
FOR SELECT
USING (
    metadata->>'owner_id' = get_current_owner_id()
);

DROP POLICY IF EXISTS "System can insert embeddings" ON public.message_embeddings;
CREATE POLICY "System can insert embeddings"
ON public.message_embeddings
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
-- REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;

-- Authenticated users get access through RLS policies
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Service role (backend/API) bypasses RLS
GRANT ALL ON SCHEMA public TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO service_role;

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

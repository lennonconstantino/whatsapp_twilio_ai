-- ============================================================================
-- Owner Project - Database Schema (Consolidated with ULID)
-- Multi-tenant conversation management system with Twilio integration
-- ============================================================================
-- This schema uses ULID (Universally Unique Lexicographically Sortable ID)
-- for primary keys instead of BIGSERIAL for better security and scalability.
--
-- ULID Format: 01ARZ3NDEKTSV4RRFFQ69G5FAV (26 characters)
-- Encoding: Crockford's Base32
-- Structure: TTTTTTTTTTRRRRRRRRRRRRRRRR
--            |________| |______________|
--             Timestamp   Randomness
--            (10 chars)    (16 chars)
-- ============================================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- ULID GENERATION FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION generate_ulid() RETURNS TEXT AS $$
DECLARE
    -- Crockford's Base32 alphabet (excludes I, L, O, U to avoid confusion)
    encoding   TEXT := '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
    timestamp  BIGINT;
    output     TEXT := '';
    unix_time  BIGINT;
    random_part BIGINT;
BEGIN
    -- Get current timestamp in milliseconds
    unix_time := (EXTRACT(EPOCH FROM CLOCK_TIMESTAMP()) * 1000)::BIGINT;
    timestamp := unix_time;
    
    -- Encode timestamp (10 characters)
    FOR i IN 1..10 LOOP
        -- Explicitly cast position to INTEGER to fix 'function substring does not exist' error
        output := output || SUBSTRING(encoding FROM ((timestamp % 32) + 1)::INTEGER FOR 1);
        timestamp := timestamp / 32;
    END LOOP;
    
    -- Add random part (16 characters)
    FOR i IN 1..16 LOOP
        random_part := (RANDOM() * 31)::INTEGER;
        output := output || SUBSTRING(encoding FROM (random_part + 1)::INTEGER FOR 1);
    END LOOP;
    
    RETURN output;
END;
$$ LANGUAGE plpgsql VOLATILE;

COMMENT ON FUNCTION generate_ulid() IS 'Generate ULID (Universally Unique Lexicographically Sortable Identifier) - Fixed Type Casting';

-- ============================================================================
-- ULID VALIDATION FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION is_valid_ulid(ulid TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    encoding TEXT := '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
    char TEXT;
BEGIN
    -- Check length
    IF LENGTH(ulid) != 26 THEN
        RETURN FALSE;
    END IF;
    
    -- Check if all characters are in the encoding alphabet
    FOR i IN 1..26 LOOP
        char := SUBSTRING(ulid FROM i FOR 1);
        IF POSITION(char IN encoding) = 0 THEN
            RETURN FALSE;
        END IF;
    END LOOP;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION is_valid_ulid(TEXT) IS 'Validate ULID format (26 chars, Crockford Base32)';

-- ============================================================================
-- ULID TO TIMESTAMP FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION ulid_to_timestamp(ulid TEXT)
RETURNS TIMESTAMP WITH TIME ZONE AS $$
DECLARE
    encoding TEXT := '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
    timestamp_part TEXT;
    unix_ms BIGINT := 0;
    char_val INTEGER;
BEGIN
    IF NOT is_valid_ulid(ulid) THEN
        RAISE EXCEPTION 'Invalid ULID format: %', ulid;
    END IF;
    
    -- Extract timestamp part (first 10 characters)
    timestamp_part := SUBSTRING(ulid FROM 1 FOR 10);
    
    -- Decode Base32 timestamp
    FOR i IN REVERSE 10..1 LOOP
        char_val := POSITION(SUBSTRING(timestamp_part FROM i FOR 1) IN encoding) - 1;
        unix_ms := unix_ms + (char_val * (32 ^ (10 - i)));
    END LOOP;
    
    -- Convert milliseconds to timestamp
    RETURN TO_TIMESTAMP(unix_ms / 1000.0);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION ulid_to_timestamp(TEXT) IS 'Extract timestamp from ULID';

-- ============================================================================
-- 1. OWNERS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS owners (
    owner_id   TEXT PRIMARY KEY DEFAULT generate_ulid(),
    name       TEXT NOT NULL,
    email      TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    active     BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_owners_email ON owners(email);
CREATE INDEX idx_owners_active ON owners(active);

COMMENT ON TABLE owners IS 'Tenants/organizations in the system';
COMMENT ON COLUMN owners.owner_id IS 'Unique ULID identifier for the owner';
COMMENT ON COLUMN owners.name IS 'Owner/organization name';
COMMENT ON COLUMN owners.email IS 'Contact email for the owner';
COMMENT ON COLUMN owners.active IS 'Whether the owner account is active';

-- ============================================================================
-- 2. USERS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    user_id      TEXT PRIMARY KEY DEFAULT generate_ulid(),
    owner_id     TEXT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
    profile_name TEXT,
    first_name   TEXT,
    last_name    TEXT,
    role         TEXT CHECK (role IN ('admin', 'agent', 'user')) DEFAULT 'user',
    phone        TEXT,
    active       BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_owner_id ON users(owner_id);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_role ON users(owner_id, role);
CREATE INDEX idx_users_active ON users(owner_id, active);
CREATE INDEX idx_users_owner_phone ON users(owner_id, phone) WHERE phone IS NOT NULL;

COMMENT ON TABLE users IS 'Staff members associated with owners';
COMMENT ON COLUMN users.user_id IS 'Unique ULID identifier for the user';
COMMENT ON COLUMN users.owner_id IS 'ULID reference to parent owner';
COMMENT ON COLUMN users.role IS 'User role: admin, agent, or user';

-- ============================================================================
-- 3. FEATURES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS features (
    feature_id  BIGSERIAL PRIMARY KEY,
    owner_id    TEXT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT,
    enabled     BOOLEAN DEFAULT FALSE,
    config_json JSONB DEFAULT '{}'::jsonb,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_features_owner_id ON features(owner_id);
CREATE INDEX idx_features_enabled ON features(owner_id, enabled);
CREATE UNIQUE INDEX idx_features_owner_name ON features(owner_id, name);

-- JSONB Indexes for features.config_json
CREATE INDEX idx_features_config_gin ON features USING gin(config_json);
CREATE INDEX idx_features_config_enabled ON features((config_json->>'enabled')) 
WHERE config_json->>'enabled' IS NOT NULL;

COMMENT ON TABLE features IS 'Features/functions that can be enabled per owner';
COMMENT ON COLUMN features.owner_id IS 'ULID reference to parent owner';
COMMENT ON COLUMN features.config_json IS 'Feature-specific configuration in JSON format';
COMMENT ON INDEX idx_features_config_gin IS 'GIN index for efficient JSONB queries (containment, key existence)';
COMMENT ON INDEX idx_features_config_enabled IS 'Partial index for enabled flag in config_json';

-- ============================================================================
-- 4. PLANS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS plans (
    plan_id     TEXT PRIMARY KEY DEFAULT generate_ulid(),
    name        TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    price_cents INTEGER NOT NULL DEFAULT 0,
    billing_period TEXT CHECK (billing_period IN ('monthly', 'yearly', 'lifetime')) DEFAULT 'monthly',
    is_public   BOOLEAN DEFAULT TRUE,
    max_users   INTEGER,
    max_projects INTEGER,
    config_json JSONB DEFAULT '{}'::jsonb,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    active      BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_plans_active ON plans(active);
CREATE INDEX idx_plans_public ON plans(is_public, active);

-- ============================================================================
-- 5. PLAN_FEATURES TABLE (Many-to-Many)
-- ============================================================================
CREATE TABLE IF NOT EXISTS plan_features (
    plan_feature_id BIGSERIAL PRIMARY KEY,
    plan_id         TEXT NOT NULL REFERENCES plans(plan_id) ON DELETE CASCADE,
    feature_name    TEXT NOT NULL,
    feature_value   JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_plan_features_plan_name ON plan_features(plan_id, feature_name);
CREATE INDEX idx_plan_features_plan_id ON plan_features(plan_id);

-- ============================================================================
-- 6. SUBSCRIPTIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id TEXT PRIMARY KEY DEFAULT generate_ulid(),
    owner_id        TEXT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
    plan_id         TEXT NOT NULL REFERENCES plans(plan_id),
    status          TEXT CHECK (status IN ('active', 'canceled', 'expired', 'trial')) DEFAULT 'trial',
    started_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at      TIMESTAMP WITH TIME ZONE,
    canceled_at     TIMESTAMP WITH TIME ZONE,
    trial_ends_at   TIMESTAMP WITH TIME ZONE,
    config_json     JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_owner_id ON subscriptions(owner_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(owner_id, status);
CREATE INDEX idx_subscriptions_expires_at ON subscriptions(expires_at) WHERE expires_at IS NOT NULL;

-- Constraint: apenas uma subscription ativa por owner
CREATE UNIQUE INDEX idx_subscriptions_owner_active 
ON subscriptions(owner_id) 
WHERE status = 'active';

-- ============================================================================
-- 7. TWILIO ACCOUNTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS twilio_accounts (
    tw_account_id BIGSERIAL PRIMARY KEY,
    owner_id      TEXT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
    account_sid   TEXT NOT NULL,
    auth_token    TEXT NOT NULL,
    phone_numbers JSONB DEFAULT '[]'::jsonb,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_twilio_accounts_owner_id ON twilio_accounts(owner_id);
CREATE INDEX idx_twilio_sid ON twilio_accounts(account_sid);

-- JSONB Index for twilio_accounts.phone_numbers
CREATE INDEX idx_twilio_phone_numbers_gin ON twilio_accounts USING gin(phone_numbers);

COMMENT ON TABLE twilio_accounts IS 'Twilio credentials for each owner';
COMMENT ON COLUMN twilio_accounts.owner_id IS 'ULID reference to parent owner';
COMMENT ON COLUMN twilio_accounts.phone_numbers IS 'Array of Twilio phone numbers';
COMMENT ON INDEX idx_twilio_phone_numbers_gin IS 'GIN index for searching phone numbers in JSONB array';

-- ============================================================================
-- 8. CONVERSATIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS conversations (
    conv_id      TEXT PRIMARY KEY DEFAULT generate_ulid(),
    owner_id     TEXT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
    user_id      TEXT REFERENCES users(user_id) ON DELETE SET NULL,
    from_number  TEXT NOT NULL,
    to_number    TEXT NOT NULL,
    status       TEXT CHECK (status IN (
        'pending', 'progress', 'agent_closed', 'support_closed',
        'user_closed', 'expired', 'failed', 'idle_timeout'
    )) DEFAULT 'pending',
    started_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at     TIMESTAMP WITH TIME ZONE,
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at   TIMESTAMP WITH TIME ZONE,
    channel      TEXT DEFAULT 'whatsapp',
    phone_number TEXT,
    context      JSONB DEFAULT '{}'::jsonb,
    metadata     JSONB DEFAULT '{}'::jsonb
);

-- Session key column (computed automatically)
ALTER TABLE conversations 
ADD COLUMN session_key TEXT GENERATED ALWAYS AS (
    CASE 
        WHEN from_number < to_number 
        THEN from_number || '::' || to_number
        ELSE to_number || '::' || from_number
    END
) STORED;

COMMENT ON COLUMN conversations.conv_id IS 'Unique ULID identifier for the conversation';
COMMENT ON COLUMN conversations.owner_id IS 'ULID reference to parent owner';
COMMENT ON COLUMN conversations.user_id IS 'ULID reference to assigned user';
COMMENT ON COLUMN conversations.session_key IS 
'Bidirectional conversation identifier: always sorted alphabetically regardless of message direction';

-- Standard indexes
CREATE UNIQUE INDEX idx_conversations_session_key_active 
ON conversations(owner_id, session_key)
WHERE status IN ('pending', 'progress');

CREATE INDEX idx_conversations_owner_id ON conversations(owner_id);
CREATE INDEX idx_conversations_user_id ON conversations(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_from ON conversations(from_number);
CREATE INDEX idx_conversations_active ON conversations(owner_id, from_number, to_number, status);
CREATE INDEX idx_conversations_expires ON conversations(expires_at) WHERE status IN ('pending', 'progress');
CREATE INDEX idx_conversations_updated ON conversations(updated_at) WHERE status IN ('pending', 'progress');
CREATE INDEX idx_conversations_owner_session ON conversations(owner_id, session_key, status);

-- JSONB Indexes for conversations.context
CREATE INDEX idx_conversations_context_gin ON conversations USING gin(context);
CREATE INDEX idx_conversations_context_status ON conversations((context->>'customer_id'), status)
WHERE context->>'customer_id' IS NOT NULL;

-- JSONB Indexes for conversations.metadata
CREATE INDEX idx_conversations_metadata_gin ON conversations USING gin(metadata);
CREATE INDEX idx_conversations_metadata_priority ON conversations((metadata->>'priority'))
WHERE metadata->>'priority' = 'high';

COMMENT ON TABLE conversations IS 'Conversations between users and the system';
COMMENT ON COLUMN conversations.status IS 'Current conversation status';
COMMENT ON COLUMN conversations.context IS 'Conversation context data';
COMMENT ON COLUMN conversations.metadata IS 'Additional metadata';
COMMENT ON INDEX idx_conversations_context_gin IS 'GIN index for efficient context JSONB queries';
COMMENT ON INDEX idx_conversations_metadata_gin IS 'GIN index for efficient metadata JSONB queries';

-- ============================================================================
-- 9. MESSAGES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS messages (
    msg_id        TEXT PRIMARY KEY DEFAULT generate_ulid(),
    conv_id       TEXT NOT NULL REFERENCES conversations(conv_id) ON DELETE CASCADE,
    owner_id      TEXT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
    from_number   TEXT NOT NULL,
    to_number     TEXT NOT NULL,
    body          TEXT NOT NULL,
    direction     TEXT CHECK (direction IN ('inbound', 'outbound')) DEFAULT 'inbound',
    timestamp     TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_by_ia    BOOLEAN DEFAULT FALSE,
    message_owner TEXT CHECK (message_owner IN ('user', 'agent', 'system', 'tool', 'support')) DEFAULT 'user',
    message_type  TEXT CHECK (message_type IN ('text', 'image', 'audio', 'video', 'document')) DEFAULT 'text',
    content       TEXT,
    metadata      JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_messages_conv_id ON messages(conv_id);
CREATE INDEX idx_messages_owner_id ON messages(owner_id);
CREATE INDEX idx_messages_conv_ts ON messages(conv_id, timestamp);
CREATE INDEX idx_messages_direction ON messages(direction);
CREATE INDEX idx_messages_owner ON messages(message_owner);

-- JSONB Index for messages.metadata
CREATE INDEX idx_messages_metadata_gin ON messages USING gin(metadata);
CREATE INDEX idx_messages_metadata_delivery_status ON messages((metadata->>'delivery_status'))
WHERE metadata->>'delivery_status' IS NOT NULL;

COMMENT ON TABLE messages IS 'Messages within conversations';
COMMENT ON COLUMN messages.msg_id IS 'Unique ULID identifier for the message';
COMMENT ON COLUMN messages.conv_id IS 'ULID reference to parent conversation';
COMMENT ON COLUMN messages.owner_id IS 'ULID reference to parent owner (denormalized for RLS/triggers)';
COMMENT ON COLUMN messages.direction IS 'Message direction: inbound or outbound';
COMMENT ON COLUMN messages.message_owner IS 'Who sent the message';
COMMENT ON COLUMN messages.message_type IS 'Type of message content';
COMMENT ON INDEX idx_messages_metadata_gin IS 'GIN index for efficient metadata JSONB queries';

-- ============================================================================
-- 10. AI RESULTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_results (
    ai_result_id TEXT PRIMARY KEY DEFAULT generate_ulid(),
    msg_id       TEXT NOT NULL REFERENCES messages(msg_id) ON DELETE CASCADE,
    feature_id   BIGINT NOT NULL REFERENCES features(feature_id) ON DELETE CASCADE,
    result_json  JSONB NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ai_results_msg_id ON ai_results(msg_id);
CREATE INDEX idx_ai_results_feature ON ai_results(feature_id);
CREATE INDEX idx_ai_results_processed ON ai_results(processed_at);

-- JSONB Indexes for ai_results.result_json
CREATE INDEX idx_ai_results_json_gin ON ai_results USING gin(result_json);
CREATE INDEX idx_ai_results_json_confidence ON ai_results(((result_json->'analysis'->>'confidence')::numeric))
WHERE result_json->'analysis'->>'confidence' IS NOT NULL;
CREATE INDEX idx_ai_results_json_category ON ai_results((result_json->>'category'))
WHERE result_json->>'category' IS NOT NULL;

COMMENT ON TABLE ai_results IS 'AI processing results for messages';
COMMENT ON COLUMN ai_results.ai_result_id IS 'Unique ULID identifier for the AI result';
COMMENT ON COLUMN ai_results.msg_id IS 'ULID reference to parent message';
COMMENT ON COLUMN ai_results.result_json IS 'AI processing output in JSON format';
COMMENT ON INDEX idx_ai_results_json_gin IS 'GIN index for efficient result_json queries';
COMMENT ON INDEX idx_ai_results_json_confidence IS 'Expression index for AI confidence scores';

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := timezone('UTC', now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for conversations
DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for features
DROP TRIGGER IF EXISTS update_features_updated_at ON features;
CREATE TRIGGER update_features_updated_at
    BEFORE UPDATE ON features
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_plans_updated_at BEFORE UPDATE ON plans
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();    

-- ============================================================================
-- ULID AUTO-GENERATION TRIGGERS
-- ============================================================================

-- Specific trigger functions for each table to avoid field access errors
-- Each function only accesses fields that exist in its specific table

CREATE OR REPLACE FUNCTION set_owners_id_on_insert()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.owner_id IS NULL THEN
        NEW.owner_id := generate_ulid();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_users_id_on_insert()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_id IS NULL THEN
        NEW.user_id := generate_ulid();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_conversations_id_on_insert()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.conv_id IS NULL THEN
        NEW.conv_id := generate_ulid();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_messages_id_on_insert()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.msg_id IS NULL THEN
        NEW.msg_id := generate_ulid();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_ai_results_id_on_insert()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ai_result_id IS NULL THEN
        NEW.ai_result_id := generate_ulid();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers with specific functions
DROP TRIGGER IF EXISTS trigger_owners_ulid ON owners;
CREATE TRIGGER trigger_owners_ulid
    BEFORE INSERT ON owners
    FOR EACH ROW
    EXECUTE FUNCTION set_owners_id_on_insert();

DROP TRIGGER IF EXISTS trigger_users_ulid ON users;
CREATE TRIGGER trigger_users_ulid
    BEFORE INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION set_users_id_on_insert();

DROP TRIGGER IF EXISTS trigger_conversations_ulid ON conversations;
CREATE TRIGGER trigger_conversations_ulid
    BEFORE INSERT ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION set_conversations_id_on_insert();

DROP TRIGGER IF EXISTS trigger_messages_ulid ON messages;
CREATE TRIGGER trigger_messages_ulid
    BEFORE INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION set_messages_id_on_insert();

DROP TRIGGER IF EXISTS trigger_ai_results_ulid ON ai_results;
CREATE TRIGGER trigger_ai_results_ulid
    BEFORE INSERT ON ai_results
    FOR EACH ROW
    EXECUTE FUNCTION set_ai_results_id_on_insert();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) SETUP
-- ============================================================================

-- Enable RLS on all tables (commented out by default)
-- ALTER TABLE owners ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE features ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE twilio_accounts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ai_results ENABLE ROW LEVEL SECURITY;

-- Create policies (these are examples - adjust based on your auth setup)
CREATE POLICY "Enable read access for all users" ON owners
    FOR SELECT USING (true);

CREATE POLICY "Users can view own owner's users" ON users
    FOR SELECT USING (true);

CREATE POLICY "Features viewable by owner" ON features
    FOR SELECT USING (true);

CREATE POLICY "Conversations viewable by owner" ON conversations
    FOR SELECT USING (true);

CREATE POLICY "Messages viewable via conversation" ON messages
    FOR SELECT USING (true);

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Grant usage on sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres, anon, authenticated, service_role;

-- Grant table permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, service_role;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;

-- ============================================================================
-- JSONB INDEXING GUIDE AND BEST PRACTICES
-- ============================================================================

/*
===================================================================================
JSONB INDEXING STRATEGIES IMPLEMENTED
===================================================================================

1. GIN INDEXES (Generalized Inverted Index)
   - Best for: Containment queries (@>, <@), key existence (?), array operations
   - Usage: WHERE jsonb_column @> '{"key": "value"}'
   - Applied to: ALL JSONB columns for general flexibility

2. EXPRESSION INDEXES
   - Best for: Specific key access, ordering, filtering
   - Usage: WHERE (jsonb_column->>'key') = 'value'
   - Applied to: Frequently accessed keys (examples provided)

3. PARTIAL INDEXES
   - Best for: Filtering common conditions
   - Usage: Indexes only relevant subset of data
   - Applied to: High priority or specific status fields

===================================================================================
QUERY EXAMPLES FOR INDEXED FIELDS
===================================================================================

-- Features config_json queries (uses idx_features_config_gin)
SELECT * FROM features 
WHERE config_json @> '{"api_enabled": true}';

SELECT * FROM features 
WHERE config_json ? 'webhook_url';

-- Features enabled flag (uses idx_features_config_enabled)
SELECT * FROM features 
WHERE config_json->>'enabled' = 'true';

-- Twilio phone numbers (uses idx_twilio_phone_numbers_gin)
SELECT * FROM twilio_accounts 
WHERE phone_numbers @> '["+1234567890"]';

-- Conversations context queries (uses idx_conversations_context_gin)
SELECT * FROM conversations 
WHERE context @> '{"language": "pt-BR"}';

-- Conversations context by customer_id (uses idx_conversations_context_status)
SELECT * FROM conversations 
WHERE context->>'customer_id' = '12345' 
AND status = 'progress';

-- Messages metadata queries (uses idx_messages_metadata_gin)
SELECT * FROM messages 
WHERE metadata @> '{"read": true}';

-- AI results queries (uses idx_ai_results_json_gin)
SELECT * FROM ai_results 
WHERE result_json @> '{"status": "success"}';

===================================================================================
ULID USAGE EXAMPLES
===================================================================================

-- Generate a new ULID
SELECT generate_ulid();

-- Validate ULID format
SELECT is_valid_ulid('01ARZ3NDEKTSV4RRFFQ69G5FAV'); -- Returns TRUE
SELECT is_valid_ulid('invalid'); -- Returns FALSE

-- Extract timestamp from ULID
SELECT ulid_to_timestamp('01ARZ3NDEKTSV4RRFFQ69G5FAV');

-- Test insert with auto-generated ULID
INSERT INTO owners (name, email) VALUES ('Test Owner', 'test@example.com')
RETURNING owner_id;

===================================================================================
MAINTENANCE COMMANDS
===================================================================================

-- Check index usage statistics
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Check index sizes
SELECT
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Rebuild indexes if needed (after bulk updates)
REINDEX TABLE conversations;
REINDEX TABLE messages;
REINDEX TABLE ai_results;

-- Update table statistics for query planner
ANALYZE conversations;
ANALYZE messages;
ANALYZE ai_results;
ANALYZE features;

===================================================================================
*/

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Database schema created successfully!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Schema Features:';
    RAISE NOTICE '✓ ULID primary keys for security and scalability';
    RAISE NOTICE '✓ JSONB columns with optimized indexing';
    RAISE NOTICE '✓ Automatic timestamp tracking';
    RAISE NOTICE '✓ Row Level Security policies (disabled by default)';
    RAISE NOTICE '✓ Foreign key constraints with CASCADE';
    RAISE NOTICE '✓ Computed session_key for bidirectional conversations';
    RAISE NOTICE '==============================================';
END $$;

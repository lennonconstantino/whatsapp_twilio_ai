-- ============================================================================
-- Owner Project - Database Schema (Optimized with JSONB Indexing)
-- Multi-tenant conversation management system with Twilio integration
-- ============================================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. OWNERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS owners (
    owner_id   BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    active     BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_owners_email ON owners(email);
CREATE INDEX idx_owners_active ON owners(active);

COMMENT ON TABLE owners IS 'Tenants/organizations in the system';
COMMENT ON COLUMN owners.owner_id IS 'Unique identifier for the owner';
COMMENT ON COLUMN owners.name IS 'Owner/organization name';
COMMENT ON COLUMN owners.email IS 'Contact email for the owner';
COMMENT ON COLUMN owners.active IS 'Whether the owner account is active';

-- ============================================================================
-- 2. USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id      BIGSERIAL PRIMARY KEY,
    owner_id     BIGINT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
    profile_name TEXT,
    first_name   TEXT,
    last_name    TEXT,
    role         TEXT CHECK (role IN ('admin', 'agent', 'user')) DEFAULT 'user',
    phone        TEXT,
    active       BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_owner ON users(owner_id);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_role ON users(owner_id, role);
CREATE INDEX idx_users_active ON users(owner_id, active);

COMMENT ON TABLE users IS 'Staff members associated with owners';
COMMENT ON COLUMN users.role IS 'User role: admin, agent, or user';

-- ============================================================================
-- 3. FEATURES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS features (
    feature_id  BIGSERIAL PRIMARY KEY,
    owner_id    BIGINT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT,
    enabled     BOOLEAN DEFAULT FALSE,
    config_json JSONB DEFAULT '{}'::jsonb,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_features_owner ON features(owner_id);
CREATE INDEX idx_features_enabled ON features(owner_id, enabled);
CREATE UNIQUE INDEX idx_features_owner_name ON features(owner_id, name);

-- JSONB Indexes for features.config_json
-- Strategy 1: GIN index for general queries (containment, key existence)
CREATE INDEX idx_features_config_gin ON features USING gin(config_json);

-- Strategy 2: Expression index for frequently accessed keys
-- Example: If you frequently query config_json->>'enabled' or similar
CREATE INDEX idx_features_config_enabled ON features((config_json->>'enabled')) 
WHERE config_json->>'enabled' IS NOT NULL;

COMMENT ON TABLE features IS 'Features/functions that can be enabled per owner';
COMMENT ON COLUMN features.config_json IS 'Feature-specific configuration in JSON format';
COMMENT ON INDEX idx_features_config_gin IS 'GIN index for efficient JSONB queries (containment, key existence)';
COMMENT ON INDEX idx_features_config_enabled IS 'Partial index for enabled flag in config_json';

-- ============================================================================
-- 4. TWILIO ACCOUNTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS twilio_accounts (
    tw_account_id BIGSERIAL PRIMARY KEY,
    owner_id      BIGINT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
    account_sid   TEXT NOT NULL,
    auth_token    TEXT NOT NULL,
    phone_numbers JSONB DEFAULT '[]'::jsonb,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_twilio_owner ON twilio_accounts(owner_id);
CREATE INDEX idx_twilio_sid ON twilio_accounts(account_sid);

-- JSONB Index for twilio_accounts.phone_numbers
-- GIN index for array containment queries
CREATE INDEX idx_twilio_phone_numbers_gin ON twilio_accounts USING gin(phone_numbers);

COMMENT ON TABLE twilio_accounts IS 'Twilio credentials for each owner';
COMMENT ON COLUMN twilio_accounts.phone_numbers IS 'Array of Twilio phone numbers';
COMMENT ON INDEX idx_twilio_phone_numbers_gin IS 'GIN index for searching phone numbers in JSONB array';

-- ============================================================================
-- 5. CONVERSATIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    conv_id      BIGSERIAL PRIMARY KEY,
    owner_id     BIGINT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
    user_id      BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
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

COMMENT ON COLUMN conversations.session_key IS 
'Bidirectional conversation identifier: always sorted alphabetically regardless of message direction';

-- Standard indexes
CREATE UNIQUE INDEX idx_conversations_session_key_active 
ON conversations(owner_id, session_key)
WHERE status IN ('pending', 'progress');

CREATE INDEX idx_conversations_session_key 
ON conversations(owner_id, session_key, status);

CREATE INDEX idx_conversations_owner ON conversations(owner_id);
CREATE INDEX idx_conversations_owner_conv ON conversations(owner_id, conv_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_from ON conversations(from_number);
CREATE INDEX idx_conversations_active ON conversations(owner_id, from_number, to_number, status);
CREATE INDEX idx_conversations_expires ON conversations(expires_at) WHERE status IN ('pending', 'progress');
CREATE INDEX idx_conversations_updated ON conversations(updated_at) WHERE status IN ('pending', 'progress');

-- JSONB Indexes for conversations.context
-- Strategy 1: GIN index for general context queries
CREATE INDEX idx_conversations_context_gin ON conversations USING gin(context);

-- Strategy 2: Expression indexes for specific context keys
-- Example: If you frequently query context->>'customer_id'
CREATE INDEX idx_conversations_context_status ON conversations((context->>'customer_id'), status)
WHERE context->>'customer_id' IS NOT NULL;

-- JSONB Indexes for conversations.metadata
-- GIN index for metadata queries
CREATE INDEX idx_conversations_metadata_gin ON conversations USING gin(metadata);

-- Example: Partial index for high priority conversations
CREATE INDEX idx_conversations_metadata_priority ON conversations((metadata->>'priority'))
WHERE metadata->>'priority' = 'high';

COMMENT ON TABLE conversations IS 'Conversations between users and the system';
COMMENT ON COLUMN conversations.status IS 'Current conversation status';
COMMENT ON COLUMN conversations.context IS 'Conversation context data';
COMMENT ON COLUMN conversations.metadata IS 'Additional metadata';
COMMENT ON INDEX idx_conversations_context_gin IS 'GIN index for efficient context JSONB queries';
COMMENT ON INDEX idx_conversations_metadata_gin IS 'GIN index for efficient metadata JSONB queries';

-- ============================================================================
-- 6. MESSAGES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS messages (
    msg_id        BIGSERIAL PRIMARY KEY,
    conv_id       BIGINT NOT NULL REFERENCES conversations(conv_id) ON DELETE CASCADE,
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

CREATE INDEX idx_messages_conv ON messages(conv_id);
CREATE INDEX idx_messages_conv_ts ON messages(conv_id, timestamp);
CREATE INDEX idx_messages_direction ON messages(direction);
CREATE INDEX idx_messages_owner ON messages(message_owner);

-- JSONB Index for messages.metadata
-- GIN index for general metadata queries
CREATE INDEX idx_messages_metadata_gin ON messages USING gin(metadata);

-- Example: Expression index for delivery status tracking
CREATE INDEX idx_messages_metadata_delivery_status ON messages((metadata->>'delivery_status'))
WHERE metadata->>'delivery_status' IS NOT NULL;

COMMENT ON TABLE messages IS 'Messages within conversations';
COMMENT ON COLUMN messages.direction IS 'Message direction: inbound or outbound';
COMMENT ON COLUMN messages.message_owner IS 'Who sent the message';
COMMENT ON COLUMN messages.message_type IS 'Type of message content';
COMMENT ON INDEX idx_messages_metadata_gin IS 'GIN index for efficient metadata JSONB queries';

-- ============================================================================
-- 7. AI RESULTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS ai_results (
    ai_result_id BIGSERIAL PRIMARY KEY,
    msg_id       BIGINT NOT NULL REFERENCES messages(msg_id) ON DELETE CASCADE,
    feature_id   BIGINT NOT NULL REFERENCES features(feature_id) ON DELETE CASCADE,
    result_json  JSONB NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ai_results_msg ON ai_results(msg_id);
CREATE INDEX idx_ai_results_feature ON ai_results(feature_id);
CREATE INDEX idx_ai_results_processed ON ai_results(processed_at);

-- JSONB Indexes for ai_results.result_json
-- Strategy 1: GIN index for general AI result queries
CREATE INDEX idx_ai_results_json_gin ON ai_results USING gin(result_json);

-- Strategy 2: Expression indexes for specific AI result fields
-- Example: If you frequently query by confidence score
CREATE INDEX idx_ai_results_json_confidence ON ai_results(((result_json->'analysis'->>'confidence')::numeric))
WHERE result_json->'analysis'->>'confidence' IS NOT NULL;

-- Example: If you frequently filter by AI category or classification
CREATE INDEX idx_ai_results_json_category ON ai_results((result_json->>'category'))
WHERE result_json->>'category' IS NOT NULL;

COMMENT ON TABLE ai_results IS 'AI processing results for messages';
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

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) SETUP
-- ============================================================================

-- Enable RLS on all tables
-- ALTER TABLE owners ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE features ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE twilio_accounts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ai_results ENABLE ROW LEVEL SECURITY;

-- Create policies (these are examples - adjust based on your auth setup)
-- For now, allow all operations for service role

-- Owners policies
CREATE POLICY "Enable read access for all users" ON owners
    FOR SELECT USING (true);

-- Users policies
CREATE POLICY "Users can view own owner's users" ON users
    FOR SELECT USING (true);

-- Features policies
CREATE POLICY "Features viewable by owner" ON features
    FOR SELECT USING (true);

-- Conversations policies
CREATE POLICY "Conversations viewable by owner" ON conversations
    FOR SELECT USING (true);

-- Messages policies
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

SELECT * FROM twilio_accounts 
WHERE phone_numbers ? '+1234567890';

-- Conversations context queries (uses idx_conversations_context_gin)
SELECT * FROM conversations 
WHERE context @> '{"language": "pt-BR"}';

SELECT * FROM conversations 
WHERE context ? 'customer_id';

-- Conversations context by customer_id (uses idx_conversations_context_status)
SELECT * FROM conversations 
WHERE context->>'customer_id' = '12345' 
AND status = 'progress';

-- Conversations metadata priority (uses idx_conversations_metadata_priority)
SELECT * FROM conversations 
WHERE metadata->>'priority' = 'high';

-- Messages metadata queries (uses idx_messages_metadata_gin)
SELECT * FROM messages 
WHERE metadata @> '{"read": true}';

-- Messages delivery status (uses idx_messages_metadata_delivery_status)
SELECT * FROM messages 
WHERE metadata->>'delivery_status' = 'delivered';

-- AI results queries (uses idx_ai_results_json_gin)
SELECT * FROM ai_results 
WHERE result_json @> '{"status": "success"}';

-- AI results confidence filter (uses idx_ai_results_json_confidence)
SELECT * FROM ai_results 
WHERE (result_json->'analysis'->>'confidence')::numeric > 0.8;

-- AI results category filter (uses idx_ai_results_json_category)
SELECT * FROM ai_results 
WHERE result_json->>'category' = 'sentiment_positive';

===================================================================================
PERFORMANCE TIPS
===================================================================================

1. Use GIN indexes for:
   - Queries with @>, <@, ?, ?&, ?| operators
   - Full text search within JSONB
   - When you don't know which keys will be queried

2. Use Expression indexes for:
   - Specific, frequently accessed keys
   - When you need to sort by JSONB values
   - When you filter by specific JSONB values repeatedly

3. Use Partial indexes for:
   - Queries that always include certain WHERE conditions
   - To save storage space
   - To improve write performance on irrelevant data

4. Monitor and adjust:
   - Use EXPLAIN ANALYZE to verify index usage
   - Drop unused indexes to improve write performance
   - Add new expression indexes based on query patterns

5. JSONB vs JSON:
   - Always use JSONB (not JSON) for indexed fields
   - JSONB supports indexing, JSON does not
   - JSONB is more efficient for queries

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

-- ============================================================================
-- CREATE TABLES
-- ============================================================================
-- Main database tables in correct dependency order
-- ============================================================================

-- Set search path for the session
SET search_path = app, extensions, public;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Creating tables...';
    RAISE NOTICE '==============================================';
END $$;

-- ============================================================================
-- 1. OWNERS TABLE (Parent table - no dependencies)
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
-- 2. USERS TABLE (Depends on: owners)
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
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    auth_id      TEXT UNIQUE,
    preferences  JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_users_owner_id ON users(owner_id);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_role ON users(owner_id, role);
CREATE INDEX idx_users_active ON users(owner_id, active);
CREATE INDEX idx_users_owner_phone ON users(owner_id, phone) WHERE phone IS NOT NULL;
CREATE INDEX idx_users_auth_id ON users(auth_id);
CREATE INDEX idx_users_preferences ON users USING gin (preferences);

COMMENT ON TABLE users IS 'Staff members associated with owners';
COMMENT ON COLUMN users.user_id IS 'Unique ULID identifier for the user';
COMMENT ON COLUMN users.owner_id IS 'ULID reference to parent owner';
COMMENT ON COLUMN users.role IS 'User role: admin, agent, or user';
COMMENT ON COLUMN users.auth_id IS 'External authentication ID (e.g. from Supabase Auth)';
COMMENT ON COLUMN users.preferences IS 'User preferences stored as JSONB';

-- ============================================================================
-- 3. FEATURES TABLE (Depends on: owners)
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
CREATE INDEX idx_features_config_gin ON features USING gin(config_json);
CREATE INDEX idx_features_config_enabled ON features((config_json->>'enabled')) 
WHERE config_json->>'enabled' IS NOT NULL;

-- Trigger for auto-updating updated_at
CREATE TRIGGER update_features_updated_at
    BEFORE UPDATE ON features
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE features IS 'Features/functions that can be enabled per owner';
COMMENT ON COLUMN features.owner_id IS 'ULID reference to parent owner';
COMMENT ON COLUMN features.config_json IS 'Feature-specific configuration in JSON format';
COMMENT ON INDEX idx_features_config_gin IS 'GIN index for efficient JSONB queries (containment, key existence)';
COMMENT ON INDEX idx_features_config_enabled IS 'Partial index for enabled flag in config_json';

-- ============================================================================
-- 4. PLANS TABLE (Depends on: nothing - standalone)
-- ============================================================================

CREATE TABLE IF NOT EXISTS plans (
    plan_id      TEXT PRIMARY KEY DEFAULT generate_ulid(),
    name         TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    description  TEXT,
    price_cents  INTEGER NOT NULL DEFAULT 0,
    billing_period TEXT CHECK (billing_period IN ('monthly', 'yearly', 'lifetime')) DEFAULT 'monthly',
    is_public    BOOLEAN DEFAULT TRUE,
    max_users    INTEGER,
    max_projects INTEGER,
    config_json  JSONB DEFAULT '{}'::jsonb,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    active       BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_plans_active ON plans(active);
CREATE INDEX idx_plans_public ON plans(is_public, active);

-- Trigger for auto-updating updated_at
CREATE TRIGGER update_plans_updated_at
    BEFORE UPDATE ON plans
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE plans IS 'Subscription plans available in the system';
COMMENT ON COLUMN plans.plan_id IS 'Unique ULID identifier for the plan';
COMMENT ON COLUMN plans.price_cents IS 'Price in cents (e.g., 1999 = $19.99)';
COMMENT ON COLUMN plans.billing_period IS 'Billing frequency: monthly, yearly, or lifetime';

-- ============================================================================
-- 5. PLAN_FEATURES TABLE (Depends on: plans)
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

COMMENT ON TABLE plan_features IS 'Many-to-many relationship between plans and features';
COMMENT ON COLUMN plan_features.plan_id IS 'ULID reference to parent plan';
COMMENT ON COLUMN plan_features.feature_name IS 'Name of the feature included in this plan';

-- ============================================================================
-- 6. SUBSCRIPTIONS TABLE (Depends on: owners, plans)
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

-- Trigger for auto-updating updated_at
CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE subscriptions IS 'Subscriptions linking owners to plans';
COMMENT ON COLUMN subscriptions.subscription_id IS 'Unique ULID identifier for the subscription';
COMMENT ON COLUMN subscriptions.owner_id IS 'ULID reference to parent owner';
COMMENT ON COLUMN subscriptions.plan_id IS 'ULID reference to subscribed plan';

-- ============================================================================
-- 7. TWILIO ACCOUNTS TABLE (Depends on: owners)
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
CREATE INDEX idx_twilio_phone_numbers_gin ON twilio_accounts USING gin(phone_numbers);

COMMENT ON TABLE twilio_accounts IS 'Twilio credentials for each owner';
COMMENT ON COLUMN twilio_accounts.owner_id IS 'ULID reference to parent owner';
COMMENT ON COLUMN twilio_accounts.phone_numbers IS 'Array of Twilio phone numbers';
COMMENT ON INDEX idx_twilio_phone_numbers_gin IS 'GIN index for searching phone numbers in JSONB array';

-- ============================================================================
-- 8. CONVERSATIONS TABLE (Depends on: owners, users)
-- ============================================================================

CREATE TABLE IF NOT EXISTS conversations (
    conv_id      TEXT PRIMARY KEY DEFAULT generate_ulid(),
    owner_id     TEXT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
    user_id      TEXT REFERENCES users(user_id) ON DELETE SET NULL,
    from_number  TEXT NOT NULL,
    to_number    TEXT NOT NULL,
    status       TEXT CHECK (status IN (
        'pending', 'progress', 'agent_closed', 'support_closed',
        'user_closed', 'expired', 'failed', 'idle_timeout', 'human_handoff'
    )) DEFAULT 'pending',
    started_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at     TIMESTAMP WITH TIME ZONE,
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at   TIMESTAMP WITH TIME ZONE,
    channel      TEXT DEFAULT 'whatsapp',
    phone_number TEXT,
    context      JSONB DEFAULT '{}'::jsonb,
    metadata     JSONB DEFAULT '{}'::jsonb,
    version      INTEGER DEFAULT 1 NOT NULL,
    agent_id     TEXT,
    handoff_at   TIMESTAMP WITH TIME ZONE
);

-- Session key column (computed automatically for bidirectional conversations)
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
COMMENT ON COLUMN conversations.version IS 'Version number for optimistic locking';
COMMENT ON COLUMN conversations.agent_id IS 'ID of the agent assigned for human handoff';
COMMENT ON COLUMN conversations.handoff_at IS 'Timestamp when conversation was handed off to human agent';

-- Standard indexes
CREATE UNIQUE INDEX idx_conversations_session_key_active 
ON conversations(owner_id, session_key)
WHERE status IN ('pending', 'progress', 'human_handoff');

CREATE INDEX idx_conversations_owner_id ON conversations(owner_id);
CREATE INDEX idx_conversations_user_id ON conversations(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_from ON conversations(from_number);
CREATE INDEX idx_conversations_active ON conversations(owner_id, from_number, to_number, status);
CREATE INDEX idx_conversations_expires ON conversations(expires_at) 
WHERE status IN ('pending', 'progress', 'human_handoff');
CREATE INDEX idx_conversations_updated ON conversations(updated_at) 
WHERE status IN ('pending', 'progress', 'human_handoff');
CREATE INDEX idx_conversations_owner_session ON conversations(owner_id, session_key, status);
CREATE INDEX idx_conversations_agent_id ON conversations(agent_id);
CREATE INDEX idx_conversations_status_handoff ON conversations(status) WHERE status = 'human_handoff';

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
-- 9. MESSAGES TABLE (Depends on: conversations, owners)
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
    metadata      JSONB DEFAULT '{}'::jsonb,
    correlation_id TEXT
);

CREATE INDEX idx_messages_conv_id ON messages(conv_id);
CREATE INDEX idx_messages_owner_id ON messages(owner_id);
CREATE INDEX idx_messages_conv_ts ON messages(conv_id, timestamp);
CREATE INDEX idx_messages_direction ON messages(direction);
CREATE INDEX idx_messages_owner ON messages(message_owner);
CREATE INDEX idx_messages_correlation_id ON messages(correlation_id);

-- JSONB Index for messages.metadata
CREATE INDEX idx_messages_metadata_gin ON messages USING gin(metadata);

-- Unique constraint on message_sid to prevent duplicates (idempotency)
CREATE UNIQUE INDEX idx_messages_metadata_message_sid 
ON messages ((metadata->>'message_sid'));

COMMENT ON TABLE messages IS 'Messages exchanged within conversations';
COMMENT ON COLUMN messages.msg_id IS 'Unique ULID identifier for the message';
COMMENT ON COLUMN messages.conv_id IS 'ULID reference to parent conversation';
COMMENT ON COLUMN messages.owner_id IS 'ULID reference to parent owner';
COMMENT ON COLUMN messages.direction IS 'Message direction: inbound or outbound';
COMMENT ON COLUMN messages.sent_by_ia IS 'Whether this message was generated by AI';
COMMENT ON COLUMN messages.message_owner IS 'Entity that owns/created this message';
COMMENT ON COLUMN messages.correlation_id IS 'Trace ID linking inbound trigger to outbound response';
COMMENT ON INDEX idx_messages_metadata_gin IS 'GIN index for efficient metadata JSONB queries';
COMMENT ON INDEX idx_messages_metadata_message_sid IS 'Unique index on message_sid in metadata to prevent duplicates';

-- ============================================================================
-- 10. AI_RESULTS TABLE (Depends on: messages, features)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_results (
    ai_result_id BIGSERIAL PRIMARY KEY,
    msg_id       TEXT NOT NULL REFERENCES messages(msg_id) ON DELETE CASCADE,
    feature_id   BIGINT NOT NULL REFERENCES features(feature_id) ON DELETE CASCADE,
    result_json  JSONB DEFAULT '{}'::jsonb,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    correlation_id TEXT,
    result_type  TEXT CHECK (result_type IN ('tool', 'agent_log', 'agent_response')) DEFAULT 'agent_log'
);

CREATE INDEX idx_ai_results_msg_id ON ai_results(msg_id);
CREATE INDEX idx_ai_results_feature_id ON ai_results(feature_id);
CREATE INDEX idx_ai_results_processed_at ON ai_results(processed_at);
CREATE INDEX idx_ai_results_correlation_id ON ai_results(correlation_id);
CREATE INDEX idx_ai_results_type ON ai_results(result_type);

-- JSONB Index for ai_results.result_json
CREATE INDEX idx_ai_results_json_gin ON ai_results USING gin(result_json);

COMMENT ON TABLE ai_results IS 'AI processing results for messages';
COMMENT ON COLUMN ai_results.ai_result_id IS 'Unique identifier for the AI result';
COMMENT ON COLUMN ai_results.msg_id IS 'ULID reference to parent message';
COMMENT ON COLUMN ai_results.feature_id IS 'Reference to the feature that processed this';
COMMENT ON COLUMN ai_results.result_json IS 'AI processing results in JSON format';
COMMENT ON COLUMN ai_results.correlation_id IS 'Trace ID linking AI processing to the specific interaction cycle';
COMMENT ON COLUMN ai_results.result_type IS 'Type of AI result: tool, agent_log, or agent_response';
COMMENT ON INDEX idx_ai_results_json_gin IS 'GIN index for efficient result_json queries';

-- ============================================================================
-- 11. CONVERSATION_STATE_HISTORY TABLE (Depends on: conversations)
-- ============================================================================

CREATE TABLE IF NOT EXISTS conversation_state_history (
    history_id   TEXT PRIMARY KEY DEFAULT generate_ulid(),
    conv_id      TEXT NOT NULL REFERENCES conversations(conv_id) ON DELETE CASCADE,
    from_status  TEXT,
    to_status    TEXT NOT NULL,
    changed_by   TEXT CHECK (changed_by IN ('user', 'agent', 'system', 'supervisor', 'tool', 'support')) DEFAULT 'system',
    changed_by_id TEXT,
    reason       TEXT,
    metadata     JSONB DEFAULT '{}'::jsonb,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_conv_state_history_conv_id ON conversation_state_history(conv_id);
CREATE INDEX idx_conv_state_history_created_at ON conversation_state_history(created_at);
CREATE INDEX idx_conv_state_history_to_status ON conversation_state_history(to_status);

-- JSONB Index
CREATE INDEX idx_conv_state_history_metadata_gin ON conversation_state_history USING gin(metadata);

-- Trigger for ULID generation
DROP TRIGGER IF EXISTS trigger_history_ulid ON conversation_state_history;
CREATE TRIGGER trigger_history_ulid
    BEFORE INSERT ON conversation_state_history
    FOR EACH ROW
    EXECUTE FUNCTION set_history_id_on_insert();

COMMENT ON TABLE conversation_state_history IS 'Audit trail for conversation status transitions';
COMMENT ON COLUMN conversation_state_history.history_id IS 'Unique ULID identifier for the history entry';
COMMENT ON COLUMN conversation_state_history.conv_id IS 'ULID reference to parent conversation';
COMMENT ON COLUMN conversation_state_history.changed_by IS 'Who/what triggered the state change';

-- ============================================================================
-- 12. MESSAGE_EMBEDDINGS TABLE (Vector store for RAG)
-- ============================================================================

CREATE TABLE IF NOT EXISTS message_embeddings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content text,
    metadata jsonb,
    embedding extensions.vector(1536)
);

-- Full-Text Search index (portuguese)
CREATE INDEX idx_message_embeddings_fts
ON message_embeddings
USING gin (to_tsvector('portuguese', coalesce(content, '')));

-- Metadata JSONB index
CREATE INDEX idx_message_embeddings_metadata ON message_embeddings USING gin(metadata);

COMMENT ON TABLE message_embeddings IS 'Vector embeddings for messages (RAG/semantic search)';
COMMENT ON COLUMN message_embeddings.embedding IS 'Vector(1536) compatible with OpenAI text-embedding-3-small';
COMMENT ON COLUMN message_embeddings.metadata IS 'Additional metadata (owner_id, session_id, role, timestamp, etc.)';

-- Note: IVFFlat index should be created AFTER having data (> 2000 rows)
-- CREATE INDEX ON message_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Tables created successfully!';
    RAISE NOTICE '✓ 12 tables created with proper relationships';
    RAISE NOTICE '✓ All indexes and constraints configured';
    RAISE NOTICE '✓ JSONB indexes for efficient JSON queries';
    RAISE NOTICE '✓ Vector embeddings support for RAG';
    RAISE NOTICE '==============================================';
END $$;

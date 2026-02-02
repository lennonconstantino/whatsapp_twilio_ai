-- ============================================================================
-- USAGE EXAMPLES & DOCUMENTATION
-- ============================================================================
-- Common queries and usage patterns for the database
-- ============================================================================

-- This file contains examples only - DO NOT EXECUTE in production

/*
===================================================================================
ULID USAGE EXAMPLES
===================================================================================

-- Generate a new ULID
SELECT generate_ulid();
-- Example output: '01ARZ3NDEKTSV4RRFFQ69G5FAV'

-- Validate ULID format
SELECT is_valid_ulid('01ARZ3NDEKTSV4RRFFQ69G5FAV'); -- Returns TRUE
SELECT is_valid_ulid('invalid'); -- Returns FALSE

-- Extract timestamp from ULID
SELECT ulid_to_timestamp('01ARZ3NDEKTSV4RRFFQ69G5FAV');
-- Returns the timestamp when the ULID was created

-- Test insert with auto-generated ULID
INSERT INTO owners (name, email) VALUES ('Test Owner', 'test@example.com')
RETURNING owner_id;

===================================================================================
BASIC CRUD OPERATIONS
===================================================================================

-- Create a new owner
INSERT INTO owners (name, email) 
VALUES ('New Company', 'contact@newcompany.com')
RETURNING owner_id, name, email, created_at;

-- Create a user for that owner
INSERT INTO users (owner_id, profile_name, first_name, last_name, role, phone)
VALUES ('OWNER_ID_HERE', 'john_doe', 'John', 'Doe', 'agent', '+5511999998888')
RETURNING user_id;

-- Create a conversation
INSERT INTO conversations (owner_id, from_number, to_number, channel, status)
VALUES ('OWNER_ID_HERE', 'whatsapp:+5511999998888', 'whatsapp:+14155238886', 'whatsapp', 'pending')
RETURNING conv_id, session_key, started_at;

-- Add a message to the conversation
INSERT INTO messages (conv_id, owner_id, from_number, to_number, body, direction)
VALUES ('CONV_ID_HERE', 'OWNER_ID_HERE', 'whatsapp:+5511999998888', 'whatsapp:+14155238886', 
        'Hello, I need help', 'inbound')
RETURNING msg_id, timestamp;

===================================================================================
COMMON QUERIES
===================================================================================

-- Find all active conversations for an owner
SELECT conv_id, from_number, to_number, status, started_at
FROM conversations
WHERE owner_id = 'OWNER_ID_HERE'
AND status IN ('pending', 'progress', 'human_handoff')
ORDER BY updated_at DESC;

-- Get conversation with all messages
SELECT 
    c.conv_id,
    c.status,
    c.started_at,
    json_agg(
        json_build_object(
            'msg_id', m.msg_id,
            'body', m.body,
            'direction', m.direction,
            'timestamp', m.timestamp,
            'sent_by_ia', m.sent_by_ia
        ) ORDER BY m.timestamp
    ) as messages
FROM conversations c
LEFT JOIN messages m ON c.conv_id = m.conv_id
WHERE c.conv_id = 'CONV_ID_HERE'
GROUP BY c.conv_id;

-- Find conversations by session_key (bidirectional lookup)
SELECT conv_id, status, started_at, session_key
FROM conversations
WHERE owner_id = 'OWNER_ID_HERE'
AND session_key = 'whatsapp:+14155238886::whatsapp:+5511999998888'
AND status IN ('pending', 'progress', 'human_handoff');

-- Get latest message in each conversation
SELECT DISTINCT ON (conv_id)
    conv_id,
    msg_id,
    body,
    direction,
    timestamp
FROM messages
WHERE owner_id = 'OWNER_ID_HERE'
ORDER BY conv_id, timestamp DESC;

-- Count messages per conversation
SELECT 
    conv_id,
    COUNT(*) as message_count,
    COUNT(*) FILTER (WHERE direction = 'inbound') as inbound_count,
    COUNT(*) FILTER (WHERE direction = 'outbound') as outbound_count,
    COUNT(*) FILTER (WHERE sent_by_ia = true) as ai_count
FROM messages
WHERE owner_id = 'OWNER_ID_HERE'
GROUP BY conv_id
ORDER BY message_count DESC;

===================================================================================
JSONB QUERIES
===================================================================================

-- Find conversations by context values
SELECT conv_id, context
FROM conversations
WHERE context @> '{"language": "pt-BR"}';

-- Find conversations by customer_id in context
SELECT conv_id, status, context
FROM conversations
WHERE context->>'customer_id' = '12345'
AND status = 'progress';

-- Update context (merge with existing)
UPDATE conversations
SET context = context || '{"customer_name": "João Silva", "priority": "high"}'::jsonb
WHERE conv_id = 'CONV_ID_HERE';

-- Features config queries
SELECT * FROM features 
WHERE config_json @> '{"api_enabled": true}';

SELECT * FROM features 
WHERE config_json ? 'webhook_url';

SELECT * FROM features 
WHERE config_json->>'enabled' = 'true';

-- Messages metadata queries
SELECT * FROM messages 
WHERE metadata @> '{"read": true}';

-- AI results queries
SELECT * FROM ai_results 
WHERE result_json @> '{"status": "success"}';

===================================================================================
AGGREGATIONS & ANALYTICS
===================================================================================

-- Daily conversation statistics
SELECT 
    DATE(started_at) as date,
    COUNT(*) as total_conversations,
    COUNT(*) FILTER (WHERE status = 'agent_closed') as closed_by_agent,
    COUNT(*) FILTER (WHERE status = 'expired') as expired,
    AVG(EXTRACT(EPOCH FROM (ended_at - started_at))/60) as avg_duration_minutes
FROM conversations
WHERE owner_id = 'OWNER_ID_HERE'
AND started_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(started_at)
ORDER BY date DESC;

-- Messages per hour (for load analysis)
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as message_count,
    COUNT(DISTINCT conv_id) as unique_conversations
FROM messages
WHERE owner_id = 'OWNER_ID_HERE'
AND timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY hour DESC;

-- AI feature usage statistics
SELECT 
    f.name,
    COUNT(ai.ai_result_id) as usage_count,
    COUNT(DISTINCT ai.msg_id) as unique_messages
FROM features f
LEFT JOIN ai_results ai ON f.feature_id = ai.feature_id
WHERE f.owner_id = 'OWNER_ID_HERE'
GROUP BY f.feature_id, f.name
ORDER BY usage_count DESC;

-- User performance metrics
SELECT 
    u.user_id,
    u.first_name,
    u.last_name,
    COUNT(DISTINCT c.conv_id) as conversations_handled,
    COUNT(m.msg_id) as messages_sent,
    AVG(EXTRACT(EPOCH FROM (c.ended_at - c.started_at))/60) as avg_conversation_minutes
FROM users u
LEFT JOIN conversations c ON u.user_id = c.user_id
LEFT JOIN messages m ON c.conv_id = m.conv_id AND m.message_owner = 'agent'
WHERE u.owner_id = 'OWNER_ID_HERE'
AND u.role = 'agent'
GROUP BY u.user_id
ORDER BY conversations_handled DESC;

===================================================================================
VECTOR SEARCH EXAMPLES (RAG)
===================================================================================

-- Search by vector similarity (requires embedding)
SELECT * FROM match_message_embeddings(
    query_embedding := '[0.1, 0.2, ..., 0.9]'::vector(1536),
    match_threshold := 0.5,
    match_count := 10,
    filter := '{"owner_id": "OWNER_ID_HERE"}'::jsonb
);

-- Full-text search on embeddings
SELECT * FROM search_message_embeddings_text(
    query_text := 'como fazer pedido',
    match_count := 5,
    filter := '{"owner_id": "OWNER_ID_HERE"}'::jsonb,
    fts_language := 'portuguese'
);

-- Hybrid search (combines vector + text with RRF)
SELECT * FROM search_message_embeddings_hybrid_rrf(
    query_text := 'problema com pagamento',
    query_embedding := '[0.1, 0.2, ..., 0.9]'::vector(1536),
    match_count := 10,
    match_threshold := 0.5,
    filter := '{"owner_id": "OWNER_ID_HERE"}'::jsonb,
    weight_vec := 1.5,
    weight_text := 1.0,
    rrf_k := 60,
    fts_language := 'portuguese'
);

-- Insert new embedding
INSERT INTO message_embeddings (content, metadata, embedding)
VALUES (
    'Customer asked about refund policy',
    '{"owner_id": "OWNER_ID_HERE", "conv_id": "CONV_ID_HERE", "role": "user"}'::jsonb,
    '[0.1, 0.2, ..., 0.9]'::vector(1536)
);

===================================================================================
STATE MANAGEMENT & AUDIT
===================================================================================

-- Track conversation state changes
INSERT INTO conversation_state_history (conv_id, from_status, to_status, changed_by, reason)
VALUES (
    'CONV_ID_HERE',
    'pending',
    'progress',
    'agent',
    'Agent started handling the conversation'
);

-- Get conversation state history
SELECT 
    history_id,
    from_status,
    to_status,
    changed_by,
    reason,
    created_at
FROM conversation_state_history
WHERE conv_id = 'CONV_ID_HERE'
ORDER BY created_at DESC;

-- Find conversations that changed status recently
SELECT 
    c.conv_id,
    c.status as current_status,
    h.from_status,
    h.to_status,
    h.changed_by,
    h.created_at as changed_at
FROM conversations c
JOIN conversation_state_history h ON c.conv_id = h.conv_id
WHERE c.owner_id = 'OWNER_ID_HERE'
AND h.created_at >= NOW() - INTERVAL '1 hour'
ORDER BY h.created_at DESC;

===================================================================================
SUBSCRIPTION & PLAN MANAGEMENT
===================================================================================

-- Check owner's active subscription and plan
SELECT 
    o.owner_id,
    o.name as owner_name,
    s.subscription_id,
    s.status as subscription_status,
    p.name as plan_name,
    p.display_name,
    p.price_cents,
    s.started_at,
    s.expires_at
FROM owners o
LEFT JOIN subscriptions s ON o.owner_id = s.owner_id AND s.status = 'active'
LEFT JOIN plans p ON s.plan_id = p.plan_id
WHERE o.owner_id = 'OWNER_ID_HERE';

-- Get all features available in a plan
SELECT 
    p.name as plan_name,
    pf.feature_name,
    pf.feature_value
FROM plans p
JOIN plan_features pf ON p.plan_id = pf.plan_id
WHERE p.plan_id = 'PLAN_ID_HERE'
ORDER BY pf.feature_name;

-- Check if owner has access to a specific feature
SELECT EXISTS (
    SELECT 1
    FROM subscriptions s
    JOIN plan_features pf ON s.plan_id = pf.plan_id
    WHERE s.owner_id = 'OWNER_ID_HERE'
    AND s.status = 'active'
    AND pf.feature_name = 'ai_chat'
);

===================================================================================
CLEANUP & MAINTENANCE
===================================================================================

-- Find expired conversations that can be closed
UPDATE conversations
SET status = 'expired', ended_at = NOW()
WHERE status IN ('pending', 'progress')
AND expires_at IS NOT NULL
AND expires_at < NOW()
RETURNING conv_id, from_number, status;

-- Delete old conversation history (older than 90 days)
DELETE FROM conversation_state_history
WHERE created_at < NOW() - INTERVAL '90 days';

-- Find duplicate message_sid (should return nothing if unique constraint works)
SELECT 
    metadata->>'message_sid' as message_sid,
    COUNT(*) as count
FROM messages
WHERE metadata->>'message_sid' IS NOT NULL
GROUP BY metadata->>'message_sid'
HAVING COUNT(*) > 1;

===================================================================================
INDEX USAGE STATISTICS
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

-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

===================================================================================
PERFORMANCE OPTIMIZATION
===================================================================================

-- Rebuild indexes if needed (after bulk updates)
REINDEX TABLE conversations;
REINDEX TABLE messages;
REINDEX TABLE ai_results;

-- Update table statistics for query planner
ANALYZE conversations;
ANALYZE messages;
ANALYZE ai_results;
ANALYZE features;

-- Vacuum tables to reclaim space
VACUUM ANALYZE conversations;
VACUUM ANALYZE messages;

===================================================================================
*/

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Usage examples and documentation ready!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'This file contains:';
    RAISE NOTICE '✓ ULID usage examples';
    RAISE NOTICE '✓ Common CRUD operations';
    RAISE NOTICE '✓ JSONB query patterns';
    RAISE NOTICE '✓ Analytics queries';
    RAISE NOTICE '✓ Vector search examples';
    RAISE NOTICE '✓ Maintenance commands';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'DO NOT execute this file in production!';
    RAISE NOTICE 'Use it as a reference guide only.';
    RAISE NOTICE '==============================================';
END $$;

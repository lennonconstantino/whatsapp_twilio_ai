-- ============================================================================
-- SEED DATA
-- ============================================================================
-- Initial data for development and testing
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Inserting seed data...';
    RAISE NOTICE '==============================================';
END $$;

-- ============================================================================
-- 1. INSERT OWNERS
-- ============================================================================

INSERT INTO owners (owner_id, name, email, created_at, active) VALUES
    ('01ARZ3NDEKTSV4RRFFQ69G5FA1', 'Default Organization', 'admin@example.com', NOW(), true),
    ('01ARZ3NDEKTSV4RRFFQ69G5FA2', 'Test Company', 'test@company.com', NOW(), true)
ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- 2. INSERT USERS
-- ============================================================================

INSERT INTO users (user_id, owner_id, profile_name, first_name, last_name, role, phone, active, created_at) VALUES
    ('01ARZ3NDEKTSV4RRFFQ69G5FB1', '01ARZ3NDEKTSV4RRFFQ69G5FA1', 'admin', 'Admin', 'User', 'admin', '+5511999999999', true, NOW()),
    ('01ARZ3NDEKTSV4RRFFQ69G5FB2', '01ARZ3NDEKTSV4RRFFQ69G5FA1', 'agent1', 'Agent', 'One', 'agent', '+5511988888888', true, NOW()),
    ('01ARZ3NDEKTSV4RRFFQ69G5FB3', '01ARZ3NDEKTSV4RRFFQ69G5FA1', 'user1', 'Regular', 'User', 'user', '+5511977777777', true, NOW()),
    ('01ARZ3NDEKTSV4RRFFQ69G5FB4', '01ARZ3NDEKTSV4RRFFQ69G5FA2', 'test_admin', 'Test', 'Admin', 'admin', '+5511966666666', true, NOW())
ON CONFLICT (user_id) DO NOTHING;

-- ============================================================================
-- 3. INSERT FEATURES
-- ============================================================================

INSERT INTO features (owner_id, name, description, enabled, config_json, created_at) VALUES
    ('01ARZ3NDEKTSV4RRFFQ69G5FA1', 'ai_chat', 'AI-powered chat responses', true, '{"model": "gpt-4", "temperature": 0.7}'::jsonb, NOW()),
    ('01ARZ3NDEKTSV4RRFFQ69G5FA1', 'sentiment_analysis', 'Analyze message sentiment', true, '{}'::jsonb, NOW()),
    ('01ARZ3NDEKTSV4RRFFQ69G5FA1', 'auto_routing', 'Automatic conversation routing', false, '{}'::jsonb, NOW()),
    ('01ARZ3NDEKTSV4RRFFQ69G5FA2', 'ai_chat', 'AI-powered chat responses', true, '{"model": "gpt-3.5-turbo"}'::jsonb, NOW())
ON CONFLICT (owner_id, name) DO NOTHING;

-- ============================================================================
-- 4. INSERT PLANS
-- ============================================================================

INSERT INTO plans (plan_id, name, display_name, description, price_cents, billing_period, is_public, max_users, max_projects, active) VALUES
    ('01ARZ3NDEKTSV4RRFFQ69G5FC1', 'free', 'Free Plan', 'Basic features for individuals', 0, 'lifetime', true, 1, 3, true),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC2', 'starter', 'Starter Plan', 'Perfect for small teams', 1999, 'monthly', true, 5, 10, true),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC3', 'professional', 'Professional Plan', 'Advanced features for growing businesses', 4999, 'monthly', true, 20, 50, true),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC4', 'enterprise', 'Enterprise Plan', 'Custom solution for large organizations', 9999, 'monthly', false, NULL, NULL, true)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- 5. INSERT PLAN_FEATURES
-- ============================================================================

INSERT INTO plan_features (plan_id, feature_name, feature_value) VALUES
    -- Free Plan
    ('01ARZ3NDEKTSV4RRFFQ69G5FC1', 'ai_chat', '{"enabled": true, "monthly_messages": 100}'::jsonb),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC1', 'basic_support', '{"enabled": true}'::jsonb),
    
    -- Starter Plan
    ('01ARZ3NDEKTSV4RRFFQ69G5FC2', 'ai_chat', '{"enabled": true, "monthly_messages": 1000}'::jsonb),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC2', 'sentiment_analysis', '{"enabled": true}'::jsonb),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC2', 'priority_support', '{"enabled": true}'::jsonb),
    
    -- Professional Plan
    ('01ARZ3NDEKTSV4RRFFQ69G5FC3', 'ai_chat', '{"enabled": true, "monthly_messages": 10000}'::jsonb),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC3', 'sentiment_analysis', '{"enabled": true}'::jsonb),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC3', 'auto_routing', '{"enabled": true}'::jsonb),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC3', 'custom_integrations', '{"enabled": true}'::jsonb),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC3', 'priority_support', '{"enabled": true}'::jsonb),
    
    -- Enterprise Plan
    ('01ARZ3NDEKTSV4RRFFQ69G5FC4', 'ai_chat', '{"enabled": true, "monthly_messages": -1}'::jsonb),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC4', 'sentiment_analysis', '{"enabled": true}'::jsonb),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC4', 'auto_routing', '{"enabled": true}'::jsonb),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC4', 'custom_integrations', '{"enabled": true}'::jsonb),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC4', 'dedicated_support', '{"enabled": true}'::jsonb),
    ('01ARZ3NDEKTSV4RRFFQ69G5FC4', 'sla_guarantee', '{"enabled": true}'::jsonb)
ON CONFLICT (plan_id, feature_name) DO NOTHING;

-- ============================================================================
-- 6. INSERT SUBSCRIPTIONS
-- ============================================================================

INSERT INTO subscriptions (subscription_id, owner_id, plan_id, status, started_at, trial_ends_at) VALUES
    ('01ARZ3NDEKTSV4RRFFQ69G5FD1', '01ARZ3NDEKTSV4RRFFQ69G5FA1', '01ARZ3NDEKTSV4RRFFQ69G5FC3', 'active', NOW(), NULL),
    ('01ARZ3NDEKTSV4RRFFQ69G5FD2', '01ARZ3NDEKTSV4RRFFQ69G5FA2', '01ARZ3NDEKTSV4RRFFQ69G5FC2', 'trial', NOW(), NOW() + INTERVAL '14 days')
ON CONFLICT (subscription_id) DO NOTHING;

-- ============================================================================
-- 7. INSERT TWILIO ACCOUNTS
-- ============================================================================

INSERT INTO twilio_accounts (owner_id, account_sid, auth_token, phone_numbers, created_at) VALUES
    ('01ARZ3NDEKTSV4RRFFQ69G5FA1', 'AC_EXAMPLE_SID_1234567890', 'example_auth_token_1234567890', 
     '["+14155238886", "+14155551234"]'::jsonb, NOW()),
    ('01ARZ3NDEKTSV4RRFFQ69G5FA2', 'AC_TEST_SID_0987654321', 'test_auth_token_0987654321',
     '["+14155555678"]'::jsonb, NOW())
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 8. INSERT SAMPLE CONVERSATIONS (optional)
-- ============================================================================

INSERT INTO conversations (
    conv_id, owner_id, user_id, from_number, to_number, 
    status, started_at, channel, phone_number, context
) VALUES
    ('01ARZ3NDEKTSV4RRFFQ69G5FE1', '01ARZ3NDEKTSV4RRFFQ69G5FA1', '01ARZ3NDEKTSV4RRFFQ69G5FB2', 
     'whatsapp:+5511991490733', 'whatsapp:+14155238886', 
     'progress', NOW() - INTERVAL '1 hour', 'whatsapp', '+14155238886',
     '{"customer_name": "João Silva", "language": "pt-BR"}'::jsonb),
    ('01ARZ3NDEKTSV4RRFFQ69G5FE2', '01ARZ3NDEKTSV4RRFFQ69G5FA1', NULL, 
     'whatsapp:+5511987654321', 'whatsapp:+14155238886',
     'pending', NOW() - INTERVAL '30 minutes', 'whatsapp', '+14155238886',
     '{"language": "pt-BR"}'::jsonb)
ON CONFLICT (conv_id) DO NOTHING;

-- ============================================================================
-- 9. INSERT SAMPLE MESSAGES (optional)
-- ============================================================================

INSERT INTO messages (
    msg_id, conv_id, owner_id, from_number, to_number, body, 
    direction, timestamp, sent_by_ia, message_owner, message_type
) VALUES
    ('01ARZ3NDEKTSV4RRFFQ69G5FF1', '01ARZ3NDEKTSV4RRFFQ69G5FE1', '01ARZ3NDEKTSV4RRFFQ69G5FA1',
     'whatsapp:+5511991490733', 'whatsapp:+14155238886', 
     'Olá, preciso de ajuda', 'inbound', NOW() - INTERVAL '1 hour', false, 'user', 'text'),
    ('01ARZ3NDEKTSV4RRFFQ69G5FF2', '01ARZ3NDEKTSV4RRFFQ69G5FE1', '01ARZ3NDEKTSV4RRFFQ69G5FA1',
     'whatsapp:+14155238886', 'whatsapp:+5511991490733',
     'Olá! Como posso ajudá-lo?', 'outbound', NOW() - INTERVAL '59 minutes', true, 'agent', 'text'),
    ('01ARZ3NDEKTSV4RRFFQ69G5FF3', '01ARZ3NDEKTSV4RRFFQ69G5FE1', '01ARZ3NDEKTSV4RRFFQ69G5FA1',
     'whatsapp:+5511991490733', 'whatsapp:+14155238886',
     'Gostaria de saber sobre meu pedido', 'inbound', NOW() - INTERVAL '58 minutes', false, 'user', 'text')
ON CONFLICT (msg_id) DO NOTHING;

-- ============================================================================
-- 10. INSERT SAMPLE AI RESULTS (optional)
-- ============================================================================

INSERT INTO ai_results (msg_id, feature_id, result_json, processed_at) 
SELECT 
    '01ARZ3NDEKTSV4RRFFQ69G5FF1',
    feature_id,
    '{"intent": "support_request", "confidence": 0.95}'::jsonb,
    NOW() - INTERVAL '1 hour'
FROM features 
WHERE owner_id = '01ARZ3NDEKTSV4RRFFQ69G5FA1' AND name = 'ai_chat'
LIMIT 1
ON CONFLICT DO NOTHING;

INSERT INTO ai_results (msg_id, feature_id, result_json, processed_at)
SELECT 
    '01ARZ3NDEKTSV4RRFFQ69G5FF1',
    feature_id,
    '{"sentiment": "neutral", "score": 0.6}'::jsonb,
    NOW() - INTERVAL '1 hour'
FROM features 
WHERE owner_id = '01ARZ3NDEKTSV4RRFFQ69G5FA1' AND name = 'sentiment_analysis'
LIMIT 1
ON CONFLICT DO NOTHING;

-- ============================================================================
-- VERIFICATION & SUMMARY
-- ============================================================================

DO $$
DECLARE
    owner_count INTEGER;
    user_count INTEGER;
    feature_count INTEGER;
    plan_count INTEGER;
    subscription_count INTEGER;
    twilio_count INTEGER;
    conversation_count INTEGER;
    message_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO owner_count FROM owners;
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO feature_count FROM features;
    SELECT COUNT(*) INTO plan_count FROM plans;
    SELECT COUNT(*) INTO subscription_count FROM subscriptions;
    SELECT COUNT(*) INTO twilio_count FROM twilio_accounts;
    SELECT COUNT(*) INTO conversation_count FROM conversations;
    SELECT COUNT(*) INTO message_count FROM messages;
    
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Seed data inserted successfully!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Owners: %', owner_count;
    RAISE NOTICE 'Users: %', user_count;
    RAISE NOTICE 'Features: %', feature_count;
    RAISE NOTICE 'Plans: %', plan_count;
    RAISE NOTICE 'Subscriptions: %', subscription_count;
    RAISE NOTICE 'Twilio Accounts: %', twilio_count;
    RAISE NOTICE 'Conversations: %', conversation_count;
    RAISE NOTICE 'Messages: %', message_count;
    RAISE NOTICE '==============================================';
END $$;

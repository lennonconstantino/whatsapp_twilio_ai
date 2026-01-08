-- ============================================================================
-- Owner Project - Seed Data
-- Initial data for development and testing
-- ============================================================================

-- ============================================================================
-- 1. INSERT OWNERS
-- ============================================================================
INSERT INTO owners (owner_id, name, email, created_at, active) VALUES
    (1, 'Default Organization', 'admin@example.com', NOW(), true),
    (2, 'Test Company', 'test@company.com', NOW(), true)
ON CONFLICT (email) DO NOTHING;

-- Reset sequence to continue from the highest ID
SELECT setval('owners_owner_id_seq', (SELECT COALESCE(MAX(owner_id), 1) FROM owners), true);

-- ============================================================================
-- 2. INSERT USERS
-- ============================================================================
INSERT INTO users (user_id, owner_id, profile_name, first_name, last_name, role, phone, active, created_at) VALUES
    (1, 1, 'admin', 'Admin', 'User', 'admin', '+5511999999999', true, NOW()),
    (2, 1, 'agent1', 'Agent', 'One', 'agent', '+5511988888888', true, NOW()),
    (3, 1, 'user1', 'Regular', 'User', 'user', '+5511977777777', true, NOW()),
    (4, 2, 'test_admin', 'Test', 'Admin', 'admin', '+5511966666666', true, NOW())
ON CONFLICT DO NOTHING;

-- Reset sequence
SELECT setval('users_user_id_seq', (SELECT COALESCE(MAX(user_id), 1) FROM users), true);

-- ============================================================================
-- 3. INSERT FEATURES
-- ============================================================================
INSERT INTO features (feature_id, owner_id, name, description, enabled, config_json, created_at) VALUES
    (1, 1, 'ai_chat', 'AI-powered chat responses', true, '{"model": "gpt-4", "temperature": 0.7}'::jsonb, NOW()),
    (2, 1, 'sentiment_analysis', 'Analyze message sentiment', true, '{}'::jsonb, NOW()),
    (3, 1, 'auto_routing', 'Automatic conversation routing', false, '{}'::jsonb, NOW()),
    (4, 2, 'ai_chat', 'AI-powered chat responses', true, '{"model": "gpt-3.5-turbo"}'::jsonb, NOW())
ON CONFLICT (owner_id, name) DO NOTHING;

-- Reset sequence
SELECT setval('features_feature_id_seq', (SELECT COALESCE(MAX(feature_id), 1) FROM features), true);

-- ============================================================================
-- 4. INSERT TWILIO ACCOUNTS
-- ============================================================================
INSERT INTO twilio_accounts (tw_account_id, owner_id, account_sid, auth_token, phone_numbers, created_at) VALUES
    (1, 1, 'AC_EXAMPLE_SID_1234567890', 'example_auth_token_1234567890', 
     '["+14155238886", "+14155551234"]'::jsonb, NOW()),
    (2, 2, 'AC_TEST_SID_0987654321', 'test_auth_token_0987654321',
     '["+14155555678"]'::jsonb, NOW())
ON CONFLICT DO NOTHING;

-- Reset sequence
SELECT setval('twilio_accounts_tw_account_id_seq', (SELECT COALESCE(MAX(tw_account_id), 1) FROM twilio_accounts), true);

-- ============================================================================
-- 5. INSERT SAMPLE CONVERSATIONS (optional)
-- ============================================================================
INSERT INTO conversations (
    conv_id, owner_id, user_id, from_number, to_number, 
    status, started_at, channel, phone_number, context
) VALUES
    (1, 1, 2, 'whatsapp:+5511991490733', 'whatsapp:+14155238886', 
     'progress', NOW() - INTERVAL '1 hour', 'whatsapp', '+14155238886',
     '{"customer_name": "João Silva"}'::jsonb),
    (2, 1, NULL, 'whatsapp:+5511987654321', 'whatsapp:+14155238886',
     'pending', NOW() - INTERVAL '30 minutes', 'whatsapp', '+14155238886',
     '{}'::jsonb)
ON CONFLICT DO NOTHING;

-- Reset sequence
SELECT setval('conversations_conv_id_seq', (SELECT COALESCE(MAX(conv_id), 1) FROM conversations), true);

-- ============================================================================
-- 6. INSERT SAMPLE MESSAGES (optional)
-- ============================================================================
INSERT INTO messages (
    msg_id, conv_id, from_number, to_number, body, 
    direction, timestamp, sent_by_ia, message_owner, message_type
) VALUES
    (1, 1, 'whatsapp:+5511991490733', 'whatsapp:+14155238886', 
     'Olá, preciso de ajuda', 'inbound', NOW() - INTERVAL '1 hour', false, 'user', 'text'),
    (2, 1, 'whatsapp:+14155238886', 'whatsapp:+5511991490733',
     'Olá! Como posso ajudá-lo?', 'outbound', NOW() - INTERVAL '59 minutes', true, 'agent', 'text'),
    (3, 1, 'whatsapp:+5511991490733', 'whatsapp:+14155238886',
     'Gostaria de saber sobre meu pedido', 'inbound', NOW() - INTERVAL '58 minutes', false, 'user', 'text')
ON CONFLICT DO NOTHING;

-- Reset sequence
SELECT setval('messages_msg_id_seq', (SELECT COALESCE(MAX(msg_id), 1) FROM messages), true);

-- ============================================================================
-- 7. INSERT SAMPLE AI RESULTS (optional)
-- ============================================================================
INSERT INTO ai_results (ai_result_id, msg_id, feature_id, result_json, processed_at) VALUES
    (1, 1, 1, '{"intent": "support_request", "confidence": 0.95}'::jsonb, NOW() - INTERVAL '1 hour'),
    (2, 1, 2, '{"sentiment": "neutral", "score": 0.6}'::jsonb, NOW() - INTERVAL '1 hour'),
    (3, 3, 1, '{"intent": "order_inquiry", "confidence": 0.88}'::jsonb, NOW() - INTERVAL '58 minutes')
ON CONFLICT DO NOTHING;

-- Reset sequence
SELECT setval('ai_results_ai_result_id_seq', (SELECT COALESCE(MAX(ai_result_id), 1) FROM ai_results), true);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
DO $$
DECLARE
    owner_count INTEGER;
    user_count INTEGER;
    feature_count INTEGER;
    twilio_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO owner_count FROM owners;
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO feature_count FROM features;
    SELECT COUNT(*) INTO twilio_count FROM twilio_accounts;
    
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Seed data inserted successfully!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Owners: %', owner_count;
    RAISE NOTICE 'Users: %', user_count;
    RAISE NOTICE 'Features: %', feature_count;
    RAISE NOTICE 'Twilio Accounts: %', twilio_count;
    RAISE NOTICE '==============================================';
END $$;

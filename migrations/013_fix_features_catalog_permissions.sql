-- ============================================================================
-- MIGRATION: FIX BILLING AND AI TABLES PERMISSIONS
-- ============================================================================
-- Explicitly grant permissions to billing and AI tables to resolve 403 Forbidden
-- errors when seeding or accessing via API.
-- ============================================================================

-- Set search path to ensure we are targeting the correct schema
SET search_path = app, extensions, public;

-- Grant permissions for Billing/SaaS tables
-- 1. features_catalog
GRANT ALL ON TABLE features_catalog TO service_role;
GRANT SELECT ON TABLE features_catalog TO authenticated;
GRANT SELECT ON TABLE features_catalog TO anon;

-- 2. feature_usage
GRANT ALL ON TABLE feature_usage TO service_role;
GRANT SELECT ON TABLE feature_usage TO authenticated;

-- 3. plans
GRANT ALL ON TABLE plans TO service_role;
GRANT SELECT ON TABLE plans TO authenticated;
GRANT SELECT ON TABLE plans TO anon;

-- 4. plan_features
GRANT ALL ON TABLE plan_features TO service_role;
GRANT SELECT ON TABLE plan_features TO authenticated;
GRANT SELECT ON TABLE plan_features TO anon;

-- 5. plan_versions
GRANT ALL ON TABLE plan_versions TO service_role;
GRANT SELECT ON TABLE plan_versions TO authenticated;
GRANT SELECT ON TABLE plan_versions TO anon;

-- 6. subscriptions
GRANT ALL ON TABLE subscriptions TO service_role;
GRANT SELECT ON TABLE subscriptions TO authenticated;

-- Ensure sequences are accessible if any (plan_features uses BIGSERIAL)
GRANT USAGE, SELECT ON SEQUENCE plan_features_plan_feature_id_seq TO service_role;
GRANT USAGE, SELECT ON SEQUENCE plan_features_plan_feature_id_seq TO authenticated;

-- If features table still exists and is used
GRANT ALL ON TABLE features TO service_role;
GRANT USAGE, SELECT ON SEQUENCE features_feature_id_seq TO service_role;

-- ============================================================================
-- AI / FINANCE TABLES
-- ============================================================================
-- MOVED TO migrations/feature/003_fix_feature_permissions.sql because 'customer', 'revenue', etc. are feature tables.

-- ============================================================================
-- OTHER AI TABLES
-- ============================================================================

-- 14. ai_results
GRANT ALL ON TABLE ai_results TO service_role;
GRANT SELECT ON TABLE ai_results TO authenticated;

-- 15. conversation_state_history
GRANT ALL ON TABLE conversation_state_history TO service_role;
GRANT SELECT ON TABLE conversation_state_history TO authenticated;

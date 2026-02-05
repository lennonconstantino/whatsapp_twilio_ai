-- ============================================================================
-- MIGRATION: SAAS MULTI-TENANT ARCHITECTURE REFACTORING
-- ============================================================================
-- This migration transforms the Identity module into a proper SaaS multi-tenant
-- architecture with feature catalog, usage tracking, and proper plan inheritance
-- ============================================================================

-- Set search path for the session
SET search_path = app, extensions, public;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Starting SaaS Multi-Tenant Migration...';
    RAISE NOTICE '==============================================';
END $$;

-- ============================================================================
-- STEP 1: CREATE NEW CORE TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- A. FEATURES_CATALOG (Replaces ad-hoc "features" concept)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS features_catalog (
    feature_id      TEXT PRIMARY KEY DEFAULT generate_ulid(),
    feature_key     TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT,
    
    -- Feature type and configuration
    feature_type    TEXT NOT NULL CHECK (feature_type IN (
        'boolean',      -- Simple on/off feature
        'quota',        -- Countable resource with limit
        'tier',         -- Tiered access (bronze/silver/gold)
        'config'        -- Complex JSON configuration
    )),
    
    -- Metadata
    unit            TEXT,           -- 'messages', 'users', 'projects', 'GB'
    category        TEXT,           -- 'integration', 'ai', 'analytics', 'storage'
    display_order   INTEGER,
    
    -- Visibility
    is_public       BOOLEAN DEFAULT TRUE,
    is_deprecated   BOOLEAN DEFAULT FALSE,
    
    -- JSON metadata for extensibility
    metadata        JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_features_catalog_key ON features_catalog(feature_key);
CREATE INDEX idx_features_catalog_type ON features_catalog(feature_type);
CREATE INDEX idx_features_catalog_category ON features_catalog(category);
CREATE INDEX idx_features_catalog_public ON features_catalog(is_public) WHERE is_public = TRUE;

-- Trigger for auto-updating updated_at
CREATE TRIGGER update_features_catalog_updated_at
    BEFORE UPDATE ON features_catalog
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE features_catalog IS 'Global catalog of all features available in the system';
COMMENT ON COLUMN features_catalog.feature_key IS 'Unique identifier used in code (immutable, snake_case)';
COMMENT ON COLUMN features_catalog.feature_type IS 'Type of feature: boolean, quota, tier, or config';
COMMENT ON COLUMN features_catalog.unit IS 'Unit of measurement for quota features';
COMMENT ON COLUMN features_catalog.category IS 'Feature grouping for UI/organization';

-- ----------------------------------------------------------------------------
-- B. PLAN_FEATURES (Enhanced with proper FKs)
-- ----------------------------------------------------------------------------
-- Drop existing plan_features table (we'll recreate with proper structure)
DROP TABLE IF EXISTS plan_features CASCADE;

CREATE TABLE plan_features (
    plan_feature_id BIGSERIAL PRIMARY KEY,
    plan_id         TEXT NOT NULL REFERENCES plans(plan_id) ON DELETE CASCADE,
    feature_id      TEXT NOT NULL REFERENCES features_catalog(feature_id) ON DELETE CASCADE,
    
    -- Feature configuration per plan
    is_enabled      BOOLEAN DEFAULT TRUE,
    quota_limit     INTEGER,        -- NULL = unlimited, 0 = disabled, N = limit
    config_value    JSONB DEFAULT '{}'::jsonb,
    
    -- Display preferences
    display_order   INTEGER,
    is_highlighted  BOOLEAN DEFAULT FALSE,  -- Show prominently in marketing?
    description     TEXT,                    -- Plan-specific override description
    
    -- Metadata
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(plan_id, feature_id)
);

CREATE INDEX idx_plan_features_plan_id ON plan_features(plan_id);
CREATE INDEX idx_plan_features_feature_id ON plan_features(feature_id);
CREATE INDEX idx_plan_features_enabled ON plan_features(plan_id, is_enabled) WHERE is_enabled = TRUE;

-- Trigger for auto-updating updated_at
CREATE TRIGGER update_plan_features_updated_at
    BEFORE UPDATE ON plan_features
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE plan_features IS 'Features included in each plan (defines plan capabilities)';
COMMENT ON COLUMN plan_features.is_enabled IS 'Whether this feature is enabled in this plan';
COMMENT ON COLUMN plan_features.quota_limit IS 'NULL=unlimited, 0=disabled, N=specific limit';
COMMENT ON COLUMN plan_features.config_value IS 'Feature-specific configuration (for config type features)';
COMMENT ON COLUMN plan_features.is_highlighted IS 'Whether to highlight this feature in plan comparison';

-- ----------------------------------------------------------------------------
-- C. FEATURE_USAGE (Critical for tracking tenant usage)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feature_usage (
    usage_id        TEXT PRIMARY KEY DEFAULT generate_ulid(),
    owner_id        TEXT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
    feature_id      TEXT NOT NULL REFERENCES features_catalog(feature_id) ON DELETE CASCADE,
    
    -- Usage tracking
    current_usage   INTEGER DEFAULT 0,
    quota_limit     INTEGER,           -- Inherited from plan, can be overridden
    
    -- Period tracking (for monthly/yearly resets)
    period_start    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    period_end      TIMESTAMP WITH TIME ZONE,
    last_reset_at   TIMESTAMP WITH TIME ZONE,
    last_used_at    TIMESTAMP WITH TIME ZONE,
    
    -- Override management
    is_override     BOOLEAN DEFAULT FALSE,      -- True if manually adjusted by admin
    override_reason TEXT,
    override_by     TEXT,                       -- user_id of admin who made override
    override_at     TIMESTAMP WITH TIME ZONE,
    
    -- Status
    is_active       BOOLEAN DEFAULT TRUE,
    
    -- Metadata for extensibility
    metadata        JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(owner_id, feature_id)
);

CREATE INDEX idx_feature_usage_owner ON feature_usage(owner_id);
CREATE INDEX idx_feature_usage_feature ON feature_usage(feature_id);
CREATE INDEX idx_feature_usage_owner_feature ON feature_usage(owner_id, feature_id);
CREATE INDEX idx_feature_usage_period ON feature_usage(period_start, period_end);
CREATE INDEX idx_feature_usage_active ON feature_usage(owner_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_feature_usage_quota_exceeded ON feature_usage(owner_id) 
    WHERE current_usage >= quota_limit AND quota_limit IS NOT NULL;

-- Trigger for auto-updating updated_at
CREATE TRIGGER update_feature_usage_updated_at
    BEFORE UPDATE ON feature_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE feature_usage IS 'Real-time feature usage tracking per tenant (owner)';
COMMENT ON COLUMN feature_usage.current_usage IS 'Current usage count within the period';
COMMENT ON COLUMN feature_usage.quota_limit IS 'Quota limit (inherited from plan or overridden)';
COMMENT ON COLUMN feature_usage.period_start IS 'Start of current usage period';
COMMENT ON COLUMN feature_usage.period_end IS 'End of current usage period (when to reset)';
COMMENT ON COLUMN feature_usage.is_override IS 'True if quota was manually adjusted by admin';
COMMENT ON COLUMN feature_usage.override_reason IS 'Reason for manual override';

-- ----------------------------------------------------------------------------
-- D. PLAN_VERSIONS (For grandfathering and price changes)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plan_versions (
    version_id      TEXT PRIMARY KEY DEFAULT generate_ulid(),
    plan_id         TEXT NOT NULL REFERENCES plans(plan_id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    
    -- Versioned data (snapshot of plan at this version)
    price_cents     INTEGER NOT NULL,
    billing_period  TEXT NOT NULL CHECK (billing_period IN ('monthly', 'yearly', 'lifetime')),
    max_users       INTEGER,
    max_projects    INTEGER,
    config_json     JSONB DEFAULT '{}'::jsonb,
    
    -- Lifecycle
    effective_from  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    effective_until TIMESTAMP WITH TIME ZONE,
    is_active       BOOLEAN DEFAULT TRUE,
    
    -- Change tracking
    change_reason   TEXT,
    changed_by      TEXT,           -- user_id of admin who made the change
    change_type     TEXT CHECK (change_type IN (
        'price_change',
        'feature_change',
        'limit_change',
        'deprecation',
        'activation'
    )),
    
    -- Metadata
    metadata        JSONB DEFAULT '{}'::jsonb,
    
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(plan_id, version_number)
);

CREATE INDEX idx_plan_versions_plan ON plan_versions(plan_id);
CREATE INDEX idx_plan_versions_active ON plan_versions(plan_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_plan_versions_effective ON plan_versions(effective_from, effective_until);
CREATE INDEX idx_plan_versions_number ON plan_versions(plan_id, version_number);

COMMENT ON TABLE plan_versions IS 'Version history for plans (enables grandfathering and price lock-in)';
COMMENT ON COLUMN plan_versions.version_number IS 'Incremental version number (1, 2, 3, ...)';
COMMENT ON COLUMN plan_versions.effective_from IS 'When this version becomes active';
COMMENT ON COLUMN plan_versions.effective_until IS 'When this version expires (NULL = current)';
COMMENT ON COLUMN plan_versions.is_active IS 'Whether this version is currently active for new subscriptions';

-- ----------------------------------------------------------------------------
-- E. SUBSCRIPTION_EVENTS (Enhanced audit trail)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS subscription_events CASCADE;

CREATE TABLE subscription_events (
    event_id        TEXT PRIMARY KEY DEFAULT generate_ulid(),
    subscription_id TEXT NOT NULL REFERENCES subscriptions(subscription_id) ON DELETE CASCADE,
    
    -- Event details
    event_type      TEXT NOT NULL CHECK (event_type IN (
        -- Lifecycle events
        'created',
        'activated',
        'renewed',
        
        -- Plan changes
        'upgraded',
        'downgraded',
        'plan_changed',
        
        -- Cancellation flow
        'cancellation_requested',
        'cancellation_scheduled',
        'cancellation_reverted',
        'canceled',
        
        -- Status changes
        'expired',
        'paused',
        'resumed',
        'suspended',
        
        -- Payment events
        'payment_succeeded',
        'payment_failed',
        'payment_retried',
        'payment_method_updated',
        
        -- Trial events
        'trial_started',
        'trial_ending_soon',
        'trial_ended',
        'trial_converted',
        
        -- Other
        'feature_override',
        'manual_adjustment'
    )),
    
    -- State transition
    from_plan_id    TEXT REFERENCES plans(plan_id),
    to_plan_id      TEXT REFERENCES plans(plan_id),
    from_status     TEXT,
    to_status       TEXT,
    
    -- Context
    triggered_by    TEXT,           -- user_id, 'system', 'payment_gateway', 'cron'
    ip_address      TEXT,
    user_agent      TEXT,
    
    -- Details
    reason          TEXT,
    description     TEXT,
    
    -- Metadata (flexible for different event types)
    metadata        JSONB DEFAULT '{}'::jsonb,
    
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_subscription_events_subscription ON subscription_events(subscription_id);
CREATE INDEX idx_subscription_events_type ON subscription_events(event_type);
CREATE INDEX idx_subscription_events_created ON subscription_events(created_at DESC);
CREATE INDEX idx_subscription_events_triggered_by ON subscription_events(triggered_by);
CREATE INDEX idx_subscription_events_metadata_gin ON subscription_events USING gin(metadata);

COMMENT ON TABLE subscription_events IS 'Complete audit trail for subscription lifecycle';
COMMENT ON COLUMN subscription_events.event_type IS 'Type of event that occurred';
COMMENT ON COLUMN subscription_events.triggered_by IS 'Who/what triggered the event (user_id, system, etc)';
COMMENT ON COLUMN subscription_events.metadata IS 'Event-specific metadata (amounts, reasons, etc)';

-- ============================================================================
-- STEP 2: ENHANCE EXISTING TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Enhance SUBSCRIPTIONS table
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    -- Add new columns if they don't exist
    
    -- Period tracking
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'app' 
                   AND table_name = 'subscriptions' 
                   AND column_name = 'current_period_start') THEN
        ALTER TABLE subscriptions ADD COLUMN current_period_start TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'app' 
                   AND table_name = 'subscriptions' 
                   AND column_name = 'current_period_end') THEN
        ALTER TABLE subscriptions ADD COLUMN current_period_end TIMESTAMP WITH TIME ZONE;
    END IF;
    
    -- Cancellation tracking
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'app' 
                   AND table_name = 'subscriptions' 
                   AND column_name = 'cancel_at') THEN
        ALTER TABLE subscriptions ADD COLUMN cancel_at TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'app' 
                   AND table_name = 'subscriptions' 
                   AND column_name = 'canceled_at') THEN
        ALTER TABLE subscriptions ADD COLUMN canceled_at TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'app' 
                   AND table_name = 'subscriptions' 
                   AND column_name = 'cancellation_reason') THEN
        ALTER TABLE subscriptions ADD COLUMN cancellation_reason TEXT;
    END IF;
    
    -- Trial tracking
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'app' 
                   AND table_name = 'subscriptions' 
                   AND column_name = 'trial_start') THEN
        ALTER TABLE subscriptions ADD COLUMN trial_start TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'app' 
                   AND table_name = 'subscriptions' 
                   AND column_name = 'trial_end') THEN
        ALTER TABLE subscriptions ADD COLUMN trial_end TIMESTAMP WITH TIME ZONE;
    END IF;
    
    -- Plan versioning
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'app' 
                   AND table_name = 'subscriptions' 
                   AND column_name = 'plan_version_id') THEN
        ALTER TABLE subscriptions ADD COLUMN plan_version_id TEXT REFERENCES plan_versions(version_id);
    END IF;
    
    -- Metadata
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'app' 
                   AND table_name = 'subscriptions' 
                   AND column_name = 'metadata') THEN
        ALTER TABLE subscriptions ADD COLUMN metadata JSONB DEFAULT '{}'::jsonb;
    END IF;
END $$;

-- Update status constraint to include new statuses
ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_status_check;
ALTER TABLE subscriptions ADD CONSTRAINT subscriptions_status_check 
CHECK (status IN (
    'incomplete',           -- Created but payment not confirmed
    'trialing',            -- In trial period
    'active',              -- Active and paid
    'past_due',            -- Payment failed but still active (grace period)
    'paused',              -- Temporarily paused by user/admin
    'pending_cancellation', -- Active until current_period_end
    'canceled',            -- Canceled and no longer active
    'expired',             -- Ended naturally
    'unpaid',              -- Failed payment, access revoked
    'suspended'            -- Suspended by admin (e.g., TOS violation)
));

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_subscriptions_period ON subscriptions(current_period_start, current_period_end);
CREATE INDEX IF NOT EXISTS idx_subscriptions_cancel_at ON subscriptions(cancel_at) WHERE cancel_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_subscriptions_trial ON subscriptions(trial_start, trial_end);
CREATE INDEX IF NOT EXISTS idx_subscriptions_version ON subscriptions(plan_version_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_metadata_gin ON subscriptions USING gin(metadata);

COMMENT ON COLUMN subscriptions.current_period_start IS 'Start of current billing period';
COMMENT ON COLUMN subscriptions.current_period_end IS 'End of current billing period';
COMMENT ON COLUMN subscriptions.cancel_at IS 'When subscription will be canceled (if scheduled)';
COMMENT ON COLUMN subscriptions.canceled_at IS 'When subscription was actually canceled';
COMMENT ON COLUMN subscriptions.trial_start IS 'When trial period started';
COMMENT ON COLUMN subscriptions.trial_end IS 'When trial period ends';
COMMENT ON COLUMN subscriptions.plan_version_id IS 'Version of plan at subscription time (for grandfathering)';

-- ============================================================================
-- STEP 3: CREATE HELPER FUNCTIONS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Function: Initialize feature usage for a new subscription
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION initialize_feature_usage_for_subscription(
    p_owner_id TEXT,
    p_subscription_id TEXT
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_plan_id TEXT;
    v_billing_period TEXT;
    v_period_end TIMESTAMP WITH TIME ZONE;
    v_inserted_count INTEGER := 0;
    v_plan_feature RECORD;
BEGIN
    -- Get subscription details
    SELECT s.plan_id, p.billing_period
    INTO v_plan_id, v_billing_period
    FROM subscriptions s
    JOIN plans p ON s.plan_id = p.plan_id
    WHERE s.subscription_id = p_subscription_id;
    
    IF v_plan_id IS NULL THEN
        RAISE EXCEPTION 'Subscription not found: %', p_subscription_id;
    END IF;
    
    -- Calculate period_end based on billing_period
    v_period_end := CASE v_billing_period
        WHEN 'monthly' THEN NOW() + INTERVAL '1 month'
        WHEN 'yearly' THEN NOW() + INTERVAL '1 year'
        WHEN 'lifetime' THEN NULL
        ELSE NOW() + INTERVAL '1 month'
    END;
    
    -- Insert feature_usage for each plan_feature
    FOR v_plan_feature IN
        SELECT pf.feature_id, pf.quota_limit
        FROM plan_features pf
        WHERE pf.plan_id = v_plan_id
        AND pf.is_enabled = TRUE
    LOOP
        INSERT INTO feature_usage (
            owner_id,
            feature_id,
            current_usage,
            quota_limit,
            period_start,
            period_end,
            is_active
        )
        VALUES (
            p_owner_id,
            v_plan_feature.feature_id,
            0,
            v_plan_feature.quota_limit,
            NOW(),
            v_period_end,
            TRUE
        )
        ON CONFLICT (owner_id, feature_id) DO UPDATE
        SET 
            quota_limit = EXCLUDED.quota_limit,
            period_start = EXCLUDED.period_start,
            period_end = EXCLUDED.period_end,
            is_active = TRUE,
            updated_at = NOW();
        
        v_inserted_count := v_inserted_count + 1;
    END LOOP;
    
    RETURN v_inserted_count;
END;
$$;

COMMENT ON FUNCTION initialize_feature_usage_for_subscription IS 
'Initialize or update feature_usage records for a tenant based on their subscription plan';

-- ----------------------------------------------------------------------------
-- Function: Check if tenant can use a feature
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION check_feature_access(
    p_owner_id TEXT,
    p_feature_key TEXT
)
RETURNS TABLE (
    allowed BOOLEAN,
    reason TEXT,
    current_usage INTEGER,
    quota_limit INTEGER,
    percentage_used NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_feature_id TEXT;
    v_usage RECORD;
BEGIN
    -- Get feature_id from key
    SELECT feature_id INTO v_feature_id
    FROM features_catalog
    WHERE feature_key = p_feature_key;
    
    IF v_feature_id IS NULL THEN
        RETURN QUERY SELECT 
            FALSE,
            'Feature not found in catalog'::TEXT,
            0::INTEGER,
            0::INTEGER,
            0::NUMERIC;
        RETURN;
    END IF;
    
    -- Get usage record
    SELECT * INTO v_usage
    FROM feature_usage
    WHERE owner_id = p_owner_id
    AND feature_id = v_feature_id;
    
    IF v_usage IS NULL THEN
        RETURN QUERY SELECT 
            FALSE,
            'Feature not enabled for this tenant'::TEXT,
            0::INTEGER,
            0::INTEGER,
            0::NUMERIC;
        RETURN;
    END IF;
    
    IF NOT v_usage.is_active THEN
        RETURN QUERY SELECT 
            FALSE,
            'Feature is disabled'::TEXT,
            v_usage.current_usage,
            v_usage.quota_limit,
            0::NUMERIC;
        RETURN;
    END IF;
    
    -- Check quota
    IF v_usage.quota_limit IS NOT NULL AND v_usage.current_usage >= v_usage.quota_limit THEN
        RETURN QUERY SELECT 
            FALSE,
            'Quota exceeded'::TEXT,
            v_usage.current_usage,
            v_usage.quota_limit,
            CASE 
                WHEN v_usage.quota_limit > 0 
                THEN ROUND((v_usage.current_usage::NUMERIC / v_usage.quota_limit::NUMERIC) * 100, 2)
                ELSE 100::NUMERIC
            END;
        RETURN;
    END IF;
    
    -- Feature is accessible
    RETURN QUERY SELECT 
        TRUE,
        'OK'::TEXT,
        v_usage.current_usage,
        v_usage.quota_limit,
        CASE 
            WHEN v_usage.quota_limit IS NOT NULL AND v_usage.quota_limit > 0 
            THEN ROUND((v_usage.current_usage::NUMERIC / v_usage.quota_limit::NUMERIC) * 100, 2)
            ELSE 0::NUMERIC
        END;
END;
$$;

COMMENT ON FUNCTION check_feature_access IS 
'Check if a tenant has access to a specific feature and return usage details';

-- ----------------------------------------------------------------------------
-- Function: Increment feature usage
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION increment_feature_usage(
    p_owner_id TEXT,
    p_feature_key TEXT,
    p_amount INTEGER DEFAULT 1
)
RETURNS TABLE (
    success BOOLEAN,
    new_usage INTEGER,
    quota_limit INTEGER,
    message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_feature_id TEXT;
    v_access_check RECORD;
BEGIN
    -- Get feature_id
    SELECT feature_id INTO v_feature_id
    FROM features_catalog
    WHERE feature_key = p_feature_key;
    
    IF v_feature_id IS NULL THEN
        RETURN QUERY SELECT FALSE, 0, 0, 'Feature not found'::TEXT;
        RETURN;
    END IF;
    
    -- Check access first
    SELECT * INTO v_access_check
    FROM check_feature_access(p_owner_id, p_feature_key);
    
    IF NOT v_access_check.allowed THEN
        RETURN QUERY SELECT 
            FALSE,
            v_access_check.current_usage,
            v_access_check.quota_limit,
            v_access_check.reason;
        RETURN;
    END IF;
    
    -- Increment usage
    UPDATE feature_usage
    SET 
        current_usage = current_usage + p_amount,
        last_used_at = NOW(),
        updated_at = NOW()
    WHERE owner_id = p_owner_id
    AND feature_id = v_feature_id
    RETURNING 
        TRUE,
        current_usage,
        quota_limit,
        'Usage incremented successfully'::TEXT
    INTO success, new_usage, quota_limit, message;
    
    RETURN QUERY SELECT success, new_usage, quota_limit, message;
END;
$$;

COMMENT ON FUNCTION increment_feature_usage IS 
'Safely increment feature usage counter with quota checking';

-- ============================================================================
-- STEP 4: MIGRATE EXISTING DATA
-- ============================================================================

DO $$
DECLARE
    v_features_migrated INTEGER := 0;
    v_usage_initialized INTEGER := 0;
BEGIN
    RAISE NOTICE 'Starting data migration...';
    
    -- Migrate unique feature names from old "features" table to features_catalog
    -- (if old features table exists)
    IF EXISTS (SELECT 1 FROM information_schema.tables 
               WHERE table_schema = 'app' AND table_name = 'features') THEN
        
        INSERT INTO features_catalog (
            feature_key,
            name,
            feature_type,
            category,
            is_public
        )
        SELECT DISTINCT
            name AS feature_key,
            name AS name,
            'boolean' AS feature_type,
            'legacy' AS category,
            TRUE AS is_public
        FROM features
        WHERE name NOT IN (SELECT feature_key FROM features_catalog)
        ON CONFLICT (feature_key) DO NOTHING;
        
        GET DIAGNOSTICS v_features_migrated = ROW_COUNT;
        RAISE NOTICE 'Migrated % unique features to catalog', v_features_migrated;
    END IF;
    
    -- Initialize feature_usage for all active subscriptions
    INSERT INTO feature_usage (
        owner_id,
        feature_id,
        current_usage,
        quota_limit,
        period_start,
        is_active
    )
    SELECT DISTINCT
        s.owner_id,
        pf.feature_id,
        0,
        pf.quota_limit,
        NOW(),
        TRUE
    FROM subscriptions s
    JOIN plan_features pf ON s.plan_id = pf.plan_id
    WHERE s.status IN ('active', 'trialing')
    AND pf.is_enabled = TRUE
    ON CONFLICT (owner_id, feature_id) DO NOTHING;
    
    GET DIAGNOSTICS v_usage_initialized = ROW_COUNT;
    RAISE NOTICE 'Initialized % feature_usage records', v_usage_initialized;
    
END $$;

-- ============================================================================
-- STEP 5: CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_feature_usage_lookup 
ON feature_usage(owner_id, feature_id, is_active);

CREATE INDEX IF NOT EXISTS idx_plan_features_lookup 
ON plan_features(plan_id, is_enabled);

-- Partial indexes for specific scenarios
CREATE INDEX IF NOT EXISTS idx_subscriptions_active 
ON subscriptions(owner_id, plan_id) 
WHERE status IN ('active', 'trialing');

-- ============================================================================
-- FINAL VERIFICATION
-- ============================================================================

DO $$
DECLARE
    v_features_count INTEGER;
    v_plans_count INTEGER;
    v_plan_features_count INTEGER;
    v_subscriptions_count INTEGER;
    v_usage_count INTEGER;
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE '==============================================';
    
    SELECT COUNT(*) INTO v_features_count FROM features_catalog;
    SELECT COUNT(*) INTO v_plans_count FROM plans;
    SELECT COUNT(*) INTO v_plan_features_count FROM plan_features;
    SELECT COUNT(*) INTO v_subscriptions_count FROM subscriptions;
    SELECT COUNT(*) INTO v_usage_count FROM feature_usage;
    
    RAISE NOTICE 'Database state:';
    RAISE NOTICE '  ✓ Features in catalog: %', v_features_count;
    RAISE NOTICE '  ✓ Plans: %', v_plans_count;
    RAISE NOTICE '  ✓ Plan-Feature mappings: %', v_plan_features_count;
    RAISE NOTICE '  ✓ Active subscriptions: %', v_subscriptions_count;
    RAISE NOTICE '  ✓ Feature usage records: %', v_usage_count;
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'New capabilities enabled:';
    RAISE NOTICE '  ✓ Feature catalog management';
    RAISE NOTICE '  ✓ Real-time usage tracking';
    RAISE NOTICE '  ✓ Plan versioning (grandfathering)';
    RAISE NOTICE '  ✓ Enhanced subscription lifecycle';
    RAISE NOTICE '  ✓ Complete audit trail';
    RAISE NOTICE '==============================================';
END $$;

-- Migration: Recreate ai_results table to force schema cache refresh and fix types
-- Description: Drops and recreates the ai_results table with the correct schema.

SET search_path = app, extensions, public;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Recreating ai_results table...';
    RAISE NOTICE '==============================================';

    -- 1. Drop existing table
    DROP TABLE IF EXISTS ai_results CASCADE;

    -- 2. Recreate table with correct schema
    CREATE TABLE ai_results (
        ai_result_id TEXT PRIMARY KEY DEFAULT generate_ulid(),
        msg_id       TEXT NOT NULL REFERENCES messages(msg_id) ON DELETE CASCADE,
        feature_id   TEXT NOT NULL REFERENCES features_catalog(feature_id) ON DELETE CASCADE,
        result_json  JSONB DEFAULT '{}'::jsonb,
        processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        correlation_id TEXT,
        result_type  TEXT CHECK (result_type IN ('tool', 'agent_log', 'agent_response')) DEFAULT 'agent_log'
    );

    -- 3. Recreate Indexes
    CREATE INDEX idx_ai_results_msg_id ON ai_results(msg_id);
    CREATE INDEX idx_ai_results_feature_id ON ai_results(feature_id);
    CREATE INDEX idx_ai_results_processed_at ON ai_results(processed_at);
    CREATE INDEX idx_ai_results_correlation_id ON ai_results(correlation_id);
    CREATE INDEX idx_ai_results_type ON ai_results(result_type);
    CREATE INDEX idx_ai_results_json_gin ON ai_results USING gin(result_json);

    -- 4. Add comments
    COMMENT ON TABLE ai_results IS 'AI processing results for messages';
    COMMENT ON COLUMN ai_results.ai_result_id IS 'Unique identifier for the AI result';
    COMMENT ON COLUMN ai_results.feature_id IS 'Reference to the feature that processed this (ULID)';

    -- 5. Notify PostgREST to reload schema
    NOTIFY pgrst, 'reload';

    RAISE NOTICE '✓ ai_results table recreated successfully';
    RAISE NOTICE '==============================================';
END $$;

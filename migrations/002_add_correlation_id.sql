-- ============================================================================
-- 1. ADD CORRELATION_ID TO MESSAGES
-- ============================================================================
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS correlation_id TEXT;

-- Index for fast lookup of interaction history
CREATE INDEX IF NOT EXISTS idx_messages_correlation_id ON messages(correlation_id);

COMMENT ON COLUMN messages.correlation_id IS 'Trace ID linking inbound trigger to outbound response';

-- ============================================================================
-- 2. ADD CORRELATION_ID TO AI_RESULTS
-- ============================================================================
ALTER TABLE ai_results 
ADD COLUMN IF NOT EXISTS correlation_id TEXT;

-- Index for joining with messages/analytics
CREATE INDEX IF NOT EXISTS idx_ai_results_correlation_id ON ai_results(correlation_id);

COMMENT ON COLUMN ai_results.correlation_id IS 'Trace ID linking AI processing to the specific interaction cycle';

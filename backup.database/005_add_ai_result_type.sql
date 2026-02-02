-- ==============================================
-- Migration: Add result_type to ai_results
-- ==============================================

-- Add result_type column with check constraint and default value
ALTER TABLE ai_results
ADD COLUMN IF NOT EXISTS result_type TEXT 
CHECK (result_type IN ('tool', 'agent_log', 'agent_response')) 
DEFAULT 'agent_log';

-- Add comment for documentation
COMMENT ON COLUMN ai_results.result_type IS 'Type of AI result: tool, agent_log, or agent_response';

-- Add index for filtering by type
CREATE INDEX IF NOT EXISTS idx_ai_results_type ON ai_results(result_type);

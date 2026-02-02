-- Migration: Add handoff fields to conversations table
-- Created at: 2024-01-29
-- Description: Adds agent_id and handoff_at columns for human handoff feature

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS agent_id TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS handoff_at TIMESTAMP WITH TIME ZONE;

-- Create index for performance on agent filtering
CREATE INDEX IF NOT EXISTS idx_conversations_agent_id ON conversations(agent_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status_handoff ON conversations(status) WHERE status = 'human_handoff';

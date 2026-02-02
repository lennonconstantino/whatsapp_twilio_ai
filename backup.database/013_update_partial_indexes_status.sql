-- Migration: Update partial indexes to include human_handoff status
-- Created at: 2026-02-02
-- Description: Updates partial indexes to include 'human_handoff' which is considered an active status in the application logic.
-- Previous definition only covered 'pending' and 'progress'.

-- 1. Recreate Unique Index for Active Sessions
DROP INDEX IF EXISTS idx_conversations_session_key_active;
CREATE UNIQUE INDEX idx_conversations_session_key_active 
ON conversations(owner_id, session_key)
WHERE status IN ('pending', 'progress', 'human_handoff');

-- 2. Recreate Index for Expiration Queries
DROP INDEX IF EXISTS idx_conversations_expires;
CREATE INDEX idx_conversations_expires 
ON conversations(expires_at) 
WHERE status IN ('pending', 'progress', 'human_handoff');

-- 3. Recreate Index for Updates/Ordering
DROP INDEX IF EXISTS idx_conversations_updated;
CREATE INDEX idx_conversations_updated 
ON conversations(updated_at) 
WHERE status IN ('pending', 'progress', 'human_handoff');

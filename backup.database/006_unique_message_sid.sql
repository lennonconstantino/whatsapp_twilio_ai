-- ============================================================================
-- Unique Constraint on Message SID (Idempotency)
-- ============================================================================

CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_metadata_message_sid 
ON messages ((metadata->>'message_sid'));

COMMENT ON INDEX idx_messages_metadata_message_sid IS 'Unique index on message_sid in metadata to prevent duplicates';

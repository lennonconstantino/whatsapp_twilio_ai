-- Migration: Drop redundant index on conversations table
-- Created at: 2026-02-02
-- Description: Drops idx_conversations_session_key which is identical to idx_conversations_owner_session.
-- Note: idx_conversations_owner_session is kept as it is more descriptive.

DROP INDEX IF EXISTS idx_conversations_session_key;

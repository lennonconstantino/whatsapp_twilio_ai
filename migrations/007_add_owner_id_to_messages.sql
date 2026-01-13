-- ============================================================================
-- Migration: Add owner_id to messages table
-- ============================================================================
-- This migration adds owner_id to messages table to support RLS/Triggers
-- that expect this field to be present on all tables.
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Adding owner_id to messages table...';
END $$;

-- 1. Add column (nullable first)
ALTER TABLE messages ADD COLUMN IF NOT EXISTS owner_id TEXT;

-- 2. Backfill data from conversations
UPDATE messages m
SET owner_id = c.owner_id
FROM conversations c
WHERE m.conv_id = c.conv_id
AND m.owner_id IS NULL;

-- 3. Make it NOT NULL (only if all records updated)
DO $$
DECLARE
    null_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO null_count FROM messages WHERE owner_id IS NULL;
    
    IF null_count = 0 THEN
        ALTER TABLE messages ALTER COLUMN owner_id SET NOT NULL;
        RAISE NOTICE 'Column owner_id set to NOT NULL';
    ELSE
        RAISE NOTICE 'WARNING: % messages have NULL owner_id, skipping NOT NULL constraint', null_count;
    END IF;
END $$;

-- 4. Add Foreign Key
ALTER TABLE messages 
    DROP CONSTRAINT IF EXISTS fk_messages_owner;

ALTER TABLE messages 
    ADD CONSTRAINT fk_messages_owner 
    FOREIGN KEY (owner_id) 
    REFERENCES owners(owner_id) 
    ON DELETE CASCADE;

-- 5. Add Index
DROP INDEX IF EXISTS idx_messages_owner_id;
CREATE INDEX idx_messages_owner_id ON messages(owner_id);

-- 6. Update Trigger (if exists) or let existing triggers work
-- The error "record new has no field owner_id" suggests a trigger was already
-- trying to access this field. By adding it, we satisfy the trigger contract.

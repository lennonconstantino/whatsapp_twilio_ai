-- ============================================================================
-- Fix: Replace generic trigger function with specific one to avoid field access errors
-- ============================================================================

-- 1. Drop triggers on messages table
DROP TRIGGER IF EXISTS trigger_messages_ulid ON messages;
DROP TRIGGER IF EXISTS set_ulid_on_insert ON messages;
DROP TRIGGER IF EXISTS trigger_set_ulid_on_insert ON messages;

-- 2. Create a SPECIFIC function for messages table
-- This avoids the "record new has no field user_id" error which happens
-- when a generic function tries to access a field that doesn't exist on the table
CREATE OR REPLACE FUNCTION set_messages_id_on_insert()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.msg_id IS NULL THEN
        NEW.msg_id := generate_ulid();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Create the trigger using the specific function
CREATE TRIGGER trigger_messages_ulid
    BEFORE INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION set_messages_id_on_insert();

-- 4. Informational: verify
DO $$
BEGIN
    RAISE NOTICE 'Replaced trigger_messages_ulid with specific function set_messages_id_on_insert';
END $$;

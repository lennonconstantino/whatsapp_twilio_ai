-- ============================================================================
-- 8. CONVERSATION STATE HISTORY TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS conversation_state_history (
    history_id   TEXT PRIMARY KEY DEFAULT generate_ulid(),
    conv_id      TEXT NOT NULL REFERENCES conversations(conv_id) ON DELETE CASCADE,
    from_status  TEXT,
    to_status    TEXT NOT NULL,
    changed_by   TEXT CHECK (changed_by IN ('user', 'agent', 'system', 'supervisor', 'tool', 'support')) DEFAULT 'system',
    changed_by_id TEXT, -- ID of the user/agent/system component
    reason       TEXT,
    metadata     JSONB DEFAULT '{}'::jsonb,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_state_history_conv_id ON conversation_state_history(conv_id);
CREATE INDEX IF NOT EXISTS idx_conv_state_history_created_at ON conversation_state_history(created_at);
CREATE INDEX IF NOT EXISTS idx_conv_state_history_to_status ON conversation_state_history(to_status);

-- JSONB Index
CREATE INDEX IF NOT EXISTS idx_conv_state_history_metadata_gin ON conversation_state_history USING gin(metadata);

COMMENT ON TABLE conversation_state_history IS 'Audit trail for conversation status transitions';
COMMENT ON COLUMN conversation_state_history.history_id IS 'Unique ULID identifier for the history entry';
COMMENT ON COLUMN conversation_state_history.conv_id IS 'ULID reference to parent conversation';

-- Trigger for ULID generation
CREATE OR REPLACE FUNCTION set_history_id_on_insert()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.history_id IS NULL THEN
        NEW.history_id := generate_ulid();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_history_ulid ON conversation_state_history;
CREATE TRIGGER trigger_history_ulid
    BEFORE INSERT ON conversation_state_history
    FOR EACH ROW
    EXECUTE FUNCTION set_history_id_on_insert();

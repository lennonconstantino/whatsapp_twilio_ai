-- ============================================================================
-- Debug Triggers on Messages Table
-- ============================================================================

DO $$
DECLARE
    trigger_record RECORD;
BEGIN
    RAISE NOTICE 'List of triggers on table "messages":';
    FOR trigger_record IN 
        SELECT 
            tgname, 
            tgtype, 
            proname 
        FROM pg_trigger t
        JOIN pg_proc p ON t.tgfoid = p.oid
        WHERE tgrelid = 'messages'::regclass
    LOOP
        RAISE NOTICE 'Trigger: % | Function: %', trigger_record.tgname, trigger_record.proname;
    END LOOP;
END $$;

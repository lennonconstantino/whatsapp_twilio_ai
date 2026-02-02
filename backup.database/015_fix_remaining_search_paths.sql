-- Migration: Fix mutable search path for remaining functions
-- Created at: 2026-02-02
-- Description: Fixes search_path for set_history_id_on_insert and dynamically fixes get_ulid_from_id/get_id_from_ulid if they exist.

-- 1. Fix known function
ALTER FUNCTION public.set_history_id_on_insert() SET search_path = public, extensions, temp;

-- 2. Dynamically fix potentially existing legacy functions (get_ulid_from_id, get_id_from_ulid)
-- We use dynamic SQL to avoid migration errors if these functions do not exist or have unknown signatures.
DO $$
DECLARE
    func_record RECORD;
BEGIN
    -- Fix get_ulid_from_id (all overloads)
    FOR func_record IN 
        SELECT oid::regprocedure as signature 
        FROM pg_proc 
        WHERE proname = 'get_ulid_from_id' AND pronamespace = 'public'::regnamespace
    LOOP
        RAISE NOTICE 'Securing function: %', func_record.signature;
        EXECUTE format('ALTER FUNCTION %s SET search_path = public, extensions, temp', func_record.signature);
    END LOOP;

    -- Fix get_id_from_ulid (all overloads)
    FOR func_record IN 
        SELECT oid::regprocedure as signature 
        FROM pg_proc 
        WHERE proname = 'get_id_from_ulid' AND pronamespace = 'public'::regnamespace
    LOOP
        RAISE NOTICE 'Securing function: %', func_record.signature;
        EXECUTE format('ALTER FUNCTION %s SET search_path = public, extensions, temp', func_record.signature);
    END LOOP;
END $$;

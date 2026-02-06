-- Migration: Fix ai_results feature_id type and FK
-- Description: Changes feature_id column from BIGINT to TEXT (ULID) to match features_catalog.
--              Updates FK to point to features_catalog instead of legacy features table.

-- Set search path
SET search_path = app, extensions, public;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Fixing ai_results feature_id...';
    RAISE NOTICE '==============================================';

    -- 1. Drop existing FK constraint
    IF EXISTS (SELECT 1 FROM information_schema.table_constraints 
               WHERE constraint_name = 'ai_results_feature_id_fkey' 
               AND table_name = 'ai_results') THEN
        ALTER TABLE ai_results DROP CONSTRAINT ai_results_feature_id_fkey;
    END IF;

    -- 2. Truncate table to avoid type/FK conflicts (it's a log table and we are changing schema fundamentally)
    TRUNCATE TABLE ai_results;

    -- 3. Change column type to TEXT
    ALTER TABLE ai_results ALTER COLUMN feature_id TYPE TEXT;

    -- 4. Add new FK constraint to features_catalog
    ALTER TABLE ai_results 
    ADD CONSTRAINT ai_results_feature_id_fkey 
    FOREIGN KEY (feature_id) 
    REFERENCES features_catalog(feature_id) 
    ON DELETE CASCADE;

    -- 5. Create index if not exists (old index might be valid for TEXT too, but let's ensure)
    DROP INDEX IF EXISTS idx_ai_results_feature_id;
    CREATE INDEX idx_ai_results_feature_id ON ai_results(feature_id);

    RAISE NOTICE '✓ ai_results feature_id updated to TEXT and linked to features_catalog';
    RAISE NOTICE '==============================================';
END $$;

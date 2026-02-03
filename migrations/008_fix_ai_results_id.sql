-- Migration: Fix ai_result_id type from BIGINT to TEXT (ULID)
-- Description: Changes ai_result_id column from BIGSERIAL (int) to TEXT (ULID) to match Pydantic models.

-- 1. Drop the default value (which is likely nextval('sequence'))
ALTER TABLE app.ai_results ALTER COLUMN ai_result_id DROP DEFAULT;

-- 2. Change the column type to TEXT
-- We cast existing IDs to text temporarily, but we will replace them with ULIDs immediately
ALTER TABLE app.ai_results ALTER COLUMN ai_result_id TYPE TEXT USING ai_result_id::text;

-- 3. Update all existing records with new ULIDs using app.generate_ulid() or generate_ulid() if in search_path
-- Using app.generate_ulid() to be explicit as it was created in the app schema context
UPDATE app.ai_results SET ai_result_id = app.generate_ulid();

-- 4. Set the new default value to app.generate_ulid()
ALTER TABLE app.ai_results ALTER COLUMN ai_result_id SET DEFAULT app.generate_ulid();

-- ============================================================================
-- CREATE EXTENSIONS
-- ============================================================================
-- Enable necessary PostgreSQL extensions for the application
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Creating extensions...';
    RAISE NOTICE '==============================================';
END $$;

-- UUID generation (for compatibility and additional UUID features)
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE SCHEMA IF NOT EXISTS app;

-- Set search path for this session to ensure extensions are found/created correctly
SET search_path = app, extensions, public;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA extensions;

-- Vector extension for embeddings (OpenAI, etc.)
CREATE EXTENSION IF NOT EXISTS vector SCHEMA extensions;

-- Trigram extension for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA extensions;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Extensions created successfully!';
    RAISE NOTICE '✓ uuid-ossp: UUID generation functions';
    RAISE NOTICE '✓ vector: Vector similarity search for embeddings';
    RAISE NOTICE '✓ pg_trgm: Trigram text search';
    RAISE NOTICE '==============================================';
END $$;

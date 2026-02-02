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
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Vector extension for embeddings (OpenAI, etc.)
CREATE EXTENSION IF NOT EXISTS vector;

-- Trigram extension for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Extensions created successfully!';
    RAISE NOTICE '✓ uuid-ossp: UUID generation functions';
    RAISE NOTICE '✓ vector: Vector similarity search for embeddings';
    RAISE NOTICE '✓ pg_trgm: Trigram text search';
    RAISE NOTICE '==============================================';
END $$;

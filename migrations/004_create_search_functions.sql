-- ============================================================================
-- CREATE SEARCH FUNCTIONS
-- ============================================================================
-- Vector and text search functions for message_embeddings table
-- These must be created AFTER the message_embeddings table exists
-- ============================================================================

-- Set search path for the session
SET search_path = app, extensions, public;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Creating search functions in app schema...';
    RAISE NOTICE '==============================================';
END $$;

-- ============================================================================
-- VECTOR SEARCH FUNCTION FOR MESSAGE EMBEDDINGS
-- ============================================================================

CREATE OR REPLACE FUNCTION app.match_message_embeddings(
    query_embedding extensions.vector(1536),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 10,
    filter jsonb DEFAULT '{}'
)
RETURNS TABLE (
    id uuid,
    content text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
SET search_path = app, extensions, public, temp
AS $$
BEGIN
    RETURN QUERY
    SELECT
        me.id,
        me.content,
        me.metadata,
        1 - (me.embedding <=> query_embedding) as similarity
    FROM app.message_embeddings me
    WHERE 1 - (me.embedding <=> query_embedding) > match_threshold
    AND me.metadata @> filter
    ORDER BY me.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION app.match_message_embeddings IS 'Search message embeddings by vector similarity';

-- ============================================================================
-- TEXT SEARCH FUNCTION FOR MESSAGE EMBEDDINGS
-- ============================================================================

CREATE OR REPLACE FUNCTION app.search_message_embeddings_text(
    query_text text,
    match_count int,
    filter jsonb DEFAULT '{}'::jsonb,
    fts_language text DEFAULT 'portuguese'
)
RETURNS TABLE (
    id uuid,
    content text,
    metadata jsonb,
    score double precision
)
LANGUAGE sql
STABLE
SET search_path = app, extensions, public, temp
AS $$
    SELECT
        me.id,
        me.content,
        me.metadata,
        ts_rank_cd(
            to_tsvector(fts_language::regconfig, coalesce(me.content, '')),
            plainto_tsquery(fts_language::regconfig, query_text)
        ) as score
    FROM app.message_embeddings me
    WHERE me.metadata @> filter
        AND to_tsvector(fts_language::regconfig, coalesce(me.content, ''))
            @@ plainto_tsquery(fts_language::regconfig, query_text)
    ORDER BY score DESC
    LIMIT match_count
$$;

COMMENT ON FUNCTION app.search_message_embeddings_text IS 'Full-text search on message embeddings using PostgreSQL FTS';

-- ============================================================================
-- HYBRID SEARCH FUNCTION (RRF - Reciprocal Rank Fusion)
-- ============================================================================

CREATE OR REPLACE FUNCTION app.search_message_embeddings_hybrid_rrf(
    query_text text,
    query_embedding extensions.vector(1536),
    match_count int,
    match_threshold double precision,
    filter jsonb DEFAULT '{}'::jsonb,
    weight_vec double precision DEFAULT 1.5,
    weight_text double precision DEFAULT 1.0,
    rrf_k int DEFAULT 60,
    fts_language text DEFAULT 'portuguese'
)
RETURNS TABLE (
    id uuid,
    content text,
    metadata jsonb,
    similarity double precision,
    score double precision
)
LANGUAGE plpgsql
SET search_path = app, extensions, public, temp
AS $$
BEGIN
    RETURN QUERY
    WITH vec_search AS (
        SELECT 
            me.id, 
            1 - (me.embedding <=> query_embedding) as vec_sim,
            ROW_NUMBER() OVER (ORDER BY me.embedding <=> query_embedding) as rank_vec
        FROM app.message_embeddings me
        WHERE 1 - (me.embedding <=> query_embedding) > match_threshold
        AND me.metadata @> filter
        LIMIT match_count * 2
    ),
    text_search AS (
        SELECT 
            me.id, 
            ts_rank_cd(
                to_tsvector(fts_language::regconfig, coalesce(me.content, '')),
                plainto_tsquery(fts_language::regconfig, query_text)
            ) as text_score,
            ROW_NUMBER() OVER (ORDER BY ts_rank_cd(
                to_tsvector(fts_language::regconfig, coalesce(me.content, '')),
                plainto_tsquery(fts_language::regconfig, query_text)
            ) DESC) as rank_text
        FROM app.message_embeddings me
        WHERE me.metadata @> filter
        AND to_tsvector(fts_language::regconfig, coalesce(me.content, ''))
            @@ plainto_tsquery(fts_language::regconfig, query_text)
        LIMIT match_count * 2
    ),
    combined AS (
        SELECT
            COALESCE(v.id, t.id) as id,
            COALESCE(v.vec_sim, 0.0) as vec_sim,
            COALESCE(t.text_score, 0.0) as text_score,
            (
                COALESCE(weight_vec / (rrf_k + v.rank_vec), 0.0) +
                COALESCE(weight_text / (rrf_k + t.rank_text), 0.0)
            ) as rrf_score
        FROM vec_search v
        FULL OUTER JOIN text_search t ON v.id = t.id
    )
    SELECT
        me.id,
        me.content,
        me.metadata,
        c.vec_sim as similarity,
        c.rrf_score as score
    FROM combined c
    JOIN app.message_embeddings me ON c.id = me.id
    ORDER BY c.rrf_score DESC
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION app.search_message_embeddings_hybrid_rrf IS 'Hybrid search using RRF (Reciprocal Rank Fusion) combining Vector and Text search';

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT USAGE ON SCHEMA app TO anon, authenticated, service_role;
GRANT ALL ON FUNCTION app.match_message_embeddings TO anon, authenticated, service_role;
GRANT ALL ON FUNCTION app.search_message_embeddings_text TO anon, authenticated, service_role;
GRANT ALL ON FUNCTION app.search_message_embeddings_hybrid_rrf TO anon, authenticated, service_role;

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Search functions created successfully in app schema!';
    RAISE NOTICE '✓ app.match_message_embeddings()';
    RAISE NOTICE '✓ app.search_message_embeddings_text()';
    RAISE NOTICE '✓ app.search_message_embeddings_hybrid_rrf()';
    RAISE NOTICE '==============================================';
END $$;

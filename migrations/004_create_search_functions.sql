-- ============================================================================
-- CREATE SEARCH FUNCTIONS
-- ============================================================================
-- Vector and text search functions for message_embeddings table
-- These must be created AFTER the message_embeddings table exists
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Creating search functions...';
    RAISE NOTICE '==============================================';
END $$;

-- ============================================================================
-- VECTOR SEARCH FUNCTION FOR MESSAGE EMBEDDINGS
-- ============================================================================

CREATE OR REPLACE FUNCTION match_message_embeddings(
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
SET search_path = public, extensions, temp
AS $$
BEGIN
    RETURN QUERY
    SELECT
        message_embeddings.id,
        message_embeddings.content,
        message_embeddings.metadata,
        1 - (message_embeddings.embedding <=> query_embedding) as similarity
    FROM message_embeddings
    WHERE 1 - (message_embeddings.embedding <=> query_embedding) > match_threshold
    AND message_embeddings.metadata @> filter
    ORDER BY message_embeddings.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_message_embeddings IS 'Search message embeddings by vector similarity';

-- ============================================================================
-- TEXT SEARCH FUNCTION FOR MESSAGE EMBEDDINGS
-- ============================================================================

CREATE OR REPLACE FUNCTION search_message_embeddings_text(
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
SET search_path = public, extensions, temp
AS $$
    SELECT
        me.id,
        me.content,
        me.metadata,
        ts_rank_cd(
            to_tsvector(fts_language::regconfig, coalesce(me.content, '')),
            plainto_tsquery(fts_language::regconfig, query_text)
        ) as score
    FROM public.message_embeddings me
    WHERE me.metadata @> filter
        AND to_tsvector(fts_language::regconfig, coalesce(me.content, ''))
            @@ plainto_tsquery(fts_language::regconfig, query_text)
    ORDER BY score DESC
    LIMIT match_count
$$;

COMMENT ON FUNCTION search_message_embeddings_text IS 'Full-text search on message embeddings using PostgreSQL FTS';

-- ============================================================================
-- HYBRID SEARCH FUNCTION (RRF - Reciprocal Rank Fusion)
-- ============================================================================

CREATE OR REPLACE FUNCTION search_message_embeddings_hybrid_rrf(
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
    score double precision
)
LANGUAGE sql
STABLE
SET search_path = public, extensions, temp
AS $$
    WITH v AS (
        SELECT
            me.id,
            me.content,
            me.metadata,
            row_number() OVER (ORDER BY me.embedding <=> query_embedding) as rnk_v
        FROM public.message_embeddings me
        WHERE me.metadata @> filter
            AND 1 - (me.embedding <=> query_embedding) > match_threshold
        ORDER BY me.embedding <=> query_embedding
        LIMIT match_count
    ),
    t AS (
        SELECT
            me.id,
            me.content,
            me.metadata,
            row_number() OVER (
                ORDER BY ts_rank_cd(
                    to_tsvector(fts_language::regconfig, coalesce(me.content, '')),
                    plainto_tsquery(fts_language::regconfig, query_text)
                ) DESC
            ) as rnk_t
        FROM public.message_embeddings me
        WHERE me.metadata @> filter
            AND to_tsvector(fts_language::regconfig, coalesce(me.content, ''))
                @@ plainto_tsquery(fts_language::regconfig, query_text)
        ORDER BY ts_rank_cd(
            to_tsvector(fts_language::regconfig, coalesce(me.content, '')),
            plainto_tsquery(fts_language::regconfig, query_text)
        ) DESC
        LIMIT match_count
    ),
    u AS (
        SELECT
            coalesce(v.id, t.id) as id,
            coalesce(v.content, t.content) as content,
            coalesce(v.metadata, t.metadata) as metadata,
            v.rnk_v,
            t.rnk_t
        FROM v
        FULL OUTER JOIN t ON v.id = t.id
    )
    SELECT
        id,
        content,
        metadata,
        coalesce(weight_vec / (rrf_k + rnk_v), 0) + coalesce(weight_text / (rrf_k + rnk_t), 0) as score
    FROM u
    ORDER BY score DESC
    LIMIT match_count
$$;

COMMENT ON FUNCTION search_message_embeddings_hybrid_rrf IS 'Hybrid search combining vector similarity and full-text search using Reciprocal Rank Fusion';

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Search functions created successfully!';
    RAISE NOTICE '✓ Vector similarity search';
    RAISE NOTICE '✓ Full-text search (Portuguese)';
    RAISE NOTICE '✓ Hybrid search with RRF';
    RAISE NOTICE '==============================================';
END $$;

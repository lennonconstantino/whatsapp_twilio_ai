-- ==========================================================
-- Hybrid Retrieval for message_embeddings (FTS + Vector + RRF)
-- ==========================================================

-- 1) Full-Text Search index (portuguese)
create index if not exists idx_message_embeddings_fts
on public.message_embeddings
using gin (to_tsvector('portuguese', coalesce(content, '')));

-- 2) Text search function
create or replace function public.search_message_embeddings_text(
  query_text text,
  match_count int,
  filter jsonb default '{}'::jsonb,
  fts_language text default 'portuguese'
)
returns table (
  id uuid,
  content text,
  metadata jsonb,
  score double precision
)
language sql
stable
as $$
  select
    me.id,
    me.content,
    me.metadata,
    ts_rank_cd(
      to_tsvector(fts_language::regconfig, coalesce(me.content, '')),
      plainto_tsquery(fts_language::regconfig, query_text)
    ) as score
  from public.message_embeddings me
  where me.metadata @> filter
    and to_tsvector(fts_language::regconfig, coalesce(me.content, ''))
      @@ plainto_tsquery(fts_language::regconfig, query_text)
  order by score desc
  limit match_count
$$;

-- 3) Hybrid search with Reciprocal Rank Fusion (RRF)
create or replace function public.search_message_embeddings_hybrid_rrf(
  query_text text,
  query_embedding vector(1536),
  match_count int,
  match_threshold double precision,
  filter jsonb default '{}'::jsonb,
  weight_vec double precision default 1.5,
  weight_text double precision default 1.0,
  rrf_k int default 60,
  fts_language text default 'portuguese'
)
returns table (
  id uuid,
  content text,
  metadata jsonb,
  score double precision
)
language sql
stable
as $$
  with v as (
    select
      me.id,
      me.content,
      me.metadata,
      row_number() over (order by me.embedding <=> query_embedding) as rnk_v
    from public.message_embeddings me
    where me.metadata @> filter
      and 1 - (me.embedding <=> query_embedding) > match_threshold
    order by me.embedding <=> query_embedding
    limit match_count
  ),
  t as (
    select
      me.id,
      me.content,
      me.metadata,
      row_number() over (
        order by ts_rank_cd(
          to_tsvector(fts_language::regconfig, coalesce(me.content, '')),
          plainto_tsquery(fts_language::regconfig, query_text)
        ) desc
      ) as rnk_t
    from public.message_embeddings me
    where me.metadata @> filter
      and to_tsvector(fts_language::regconfig, coalesce(me.content, ''))
        @@ plainto_tsquery(fts_language::regconfig, query_text)
    order by ts_rank_cd(
      to_tsvector(fts_language::regconfig, coalesce(me.content, '')),
      plainto_tsquery(fts_language::regconfig, query_text)
    ) desc
    limit match_count
  ),
  u as (
    select
      coalesce(v.id, t.id) as id,
      coalesce(v.content, t.content) as content,
      coalesce(v.metadata, t.metadata) as metadata,
      v.rnk_v,
      t.rnk_t
    from v
    full outer join t on v.id = t.id
  )
  select
    id,
    content,
    metadata,
    coalesce(weight_vec / (rrf_k + rnk_v), 0) + coalesce(weight_text / (rrf_k + rnk_t), 0) as score
  from u
  order by score desc
  limit match_count
$$;


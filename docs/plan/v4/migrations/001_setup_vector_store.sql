-- Enable the pgvector extension to work with embedding vectors
create extension if not exists vector;

-- Create a table to store your documents
-- Table: message_embeddings
-- Columns:
--   id: UUID primary key
--   content: Text content of the message/document
--   metadata: JSONB for additional info (owner_id, session_id, role, timestamp, etc.)
--   embedding: Vector(1536) compatible with OpenAI text-embedding-3-small
create table if not exists message_embeddings (
  id uuid primary key default gen_random_uuid(),
  content text,
  metadata jsonb,
  embedding vector(1536)
);

-- Create a function to search for documents
-- Function: match_message_embeddings
-- Args:
--   query_embedding: The vector to search for
--   match_threshold: Minimum similarity score (0-1)
--   match_count: Max number of results
create or replace function match_message_embeddings (
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  filter jsonb default '{}'
)
returns table (
  id uuid,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    message_embeddings.id,
    message_embeddings.content,
    message_embeddings.metadata,
    1 - (message_embeddings.embedding <=> query_embedding) as similarity
  from message_embeddings
  where 1 - (message_embeddings.embedding <=> query_embedding) > match_threshold
  and message_embeddings.metadata @> filter
  order by message_embeddings.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Create an index for faster queries (IVFFlat)
-- Note: Create this only after having some data (e.g. > 2000 rows) for better centroid calculation.
-- create index on message_embeddings using ivfflat (embedding vector_cosine_ops)
-- with (lists = 100);

-- Story 2.4: Vector Indexing in Supabase
-- Migration: create extension, table, index, function

-- Enable pgvector extension
create extension if not exists vector;

-- Table for document chunks
create table if not exists document_chunks (
  id uuid primary key,
  document_id uuid not null,
  content text not null,
  embedding vector(1536),
  metadata jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- HNSW index for cosine similarity on embedding
create index if not exists document_chunks_embedding_hnsw_idx on document_chunks
using hnsw (embedding vector_cosine_ops)
with (m = 16, ef_construction = 64);

-- Matching function with defaults per decision: threshold=0.75, count=8
create or replace function match_document_chunks (
  query_embedding vector(1536),
  match_threshold float default 0.75,
  match_count int default 8
)
returns table (
  id uuid,
  document_id uuid,
  content text,
  similarity float
)
language sql stable
as $$
  select
    dc.id,
    dc.document_id,
    dc.content,
    1 - (dc.embedding <=> query_embedding) as similarity
  from document_chunks dc
  where 1 - (dc.embedding <=> query_embedding) > match_threshold
  order by (dc.embedding <=> query_embedding) asc
  limit match_count;
$$;

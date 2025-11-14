-- ==================================================
-- Epic 9 Story 9.1: Persistent Conversational Memory
-- Migration: Create chat_messages table + indices
-- ==================================================
-- Author: Dev Agent (Story 9.1 Task 2)
-- Created: 2025-11-06
-- Purpose: Enable hybrid memory architecture (L1 cache + L2 DB storage)
-- 
-- Changes:
-- 1. CREATE TABLE chat_messages (if not exists)
-- 2. CREATE UNIQUE INDEX on idempotency_key (prevent duplicates)
-- 3. CREATE INDEX for session history queries (session_id, created_at)
-- 4. CREATE INDEX for analytics (created_at DESC)
-- 5. CREATE GIN INDEX for full-text search (Italian)
-- 6. CREATE PARTIAL INDEX for archived messages filter
-- ==================================================

-- =====================
-- 1. Create chat_messages table
-- =====================
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    source_chunk_ids UUID[],
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    idempotency_key TEXT NOT NULL
);

ALTER TABLE public.chat_messages OWNER TO postgres;

-- =====================
-- 2. Idempotency Key (UNIQUE constraint)
-- =====================
-- Prevent duplicate messages during retry/network failures
-- Formula: sha256(session_id + timestamp_ms + content_hash)
-- Story 9.1 AC9, Task 2.2
CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_messages_idempotency_key
    ON public.chat_messages(idempotency_key);

-- =====================
-- 3. Session History Index (Primary query pattern)
-- =====================
-- Query pattern: load session history chronologically
-- Usage: SELECT * FROM chat_messages WHERE session_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3
-- Story 9.1 AC4
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created
    ON public.chat_messages(session_id, created_at DESC);

-- =====================
-- 4. Analytics Time Index
-- =====================
-- Query pattern: recent messages across all sessions
-- Usage: SELECT * FROM chat_messages WHERE created_at > $1 ORDER BY created_at DESC
-- Story 9.1 AC4
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at
    ON public.chat_messages(created_at DESC);

-- =====================
-- 5. Full-Text Search Index (Italian language)
-- =====================
-- Query pattern: search conversation content
-- Usage: SELECT * FROM chat_messages WHERE to_tsvector('italian', content) @@ to_tsquery('italian', $1)
-- Story 9.1 AC4
CREATE INDEX IF NOT EXISTS idx_chat_messages_content_fts
    ON public.chat_messages
    USING GIN (to_tsvector('italian', content));

-- =====================
-- 6. Archived Messages Partial Index
-- =====================
-- Query pattern: exclude archived sessions from queries
-- Usage: WHERE metadata->>'archived' IS NULL OR metadata->>'archived' != 'true'
-- Story 9.1 AC4
CREATE INDEX IF NOT EXISTS idx_chat_messages_metadata_archived
    ON public.chat_messages((metadata->>'archived'))
    WHERE (metadata->>'archived') IS NOT NULL;

-- =====================
-- Index Size Estimates (Story 9.1 Dev Notes)
-- =====================
-- idx_chat_messages_session_created: ~500KB per 10K messages
-- idx_chat_messages_created_at: ~200KB per 10K messages
-- idx_chat_messages_content_fts: ~2MB per 10K messages (GIN overhead)
-- idx_chat_messages_metadata_archived: ~50KB (partial, sparse)
-- idx_chat_messages_idempotency_key: ~200KB per 10K messages
-- Total overhead: ~2.95MB per 10K messages
-- Annual storage (50 msg/day): ~9MB/year (well within Supabase Free Tier 500MB)

-- =====================
-- RLS Policies (Future: Story 9.2)
-- =====================
-- TODO Story 9.2: Add Row Level Security policies
-- - Students can only access their own session messages
-- - Admins can access all messages for debugging/analytics
-- Placeholder per ora: public table (no RLS)

-- =====================
-- Grants
-- =====================
-- Grant access to service_role for backend operations
GRANT ALL ON public.chat_messages TO service_role;
GRANT ALL ON public.chat_messages TO postgres;

-- =====================
-- Verification Queries (Manual Testing - Task 2.4)
-- =====================
-- Run these queries after migration to verify:
--
-- 1. List all indices on chat_messages:
--    SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'chat_messages';
--
-- 2. Check table structure:
--    \d public.chat_messages
--
-- 3. Test idempotency constraint (should fail on duplicate key):
--    INSERT INTO public.chat_messages (session_id, role, content, idempotency_key)
--    VALUES ('test', 'user', 'test', 'duplicate_key');
--    -- Second insert with same idempotency_key should conflict
--
-- 4. Test full-text search (Italian):
--    SELECT content FROM public.chat_messages
--    WHERE to_tsvector('italian', content) @@ to_tsquery('italian', 'esercizio');
--
-- 5. Index usage verification (EXPLAIN ANALYZE):
--    EXPLAIN ANALYZE
--    SELECT * FROM public.chat_messages
--    WHERE session_id = 'test_session'
--    ORDER BY created_at DESC
--    LIMIT 100;
--    -- Should use idx_chat_messages_session_created

-- ==================================================
-- Migration Complete
-- ==================================================


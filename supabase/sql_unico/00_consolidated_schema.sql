-- ============================================================================
-- CONSOLIDATED SCHEMA - FisioRAG Database
-- ============================================================================
-- Questo file consolida tutte le migrazioni in un unico script eseguibile
-- su un nuovo progetto Supabase per ottenere lo stesso schema del DB corrente.
-- 
-- Esegui questo script con service_role o postgres role per permessi completi.
-- ============================================================================

BEGIN;

-- ============================================================================
-- SCHEMA DEDICATO PER ESTENSIONI
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS extensions;

-- Abilita estensione pgvector in schema dedicato
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- ============================================================================
-- TABELLA DOCUMENTS: Metadati file sorgente
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_hash TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'pending',
  chunking_strategy JSONB,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS documents_file_hash_idx ON public.documents(file_hash);
CREATE INDEX IF NOT EXISTS documents_status_idx ON public.documents(status);
CREATE INDEX IF NOT EXISTS documents_created_at_idx ON public.documents(created_at DESC);

-- Commenti esplicativi
COMMENT ON TABLE public.documents IS 'Metadati per file sorgente caricati nel sistema';
COMMENT ON COLUMN public.documents.file_hash IS 'Hash SHA-256 per deduplicazione documenti';
COMMENT ON COLUMN public.documents.chunking_strategy IS 'Strategia chunking applicata (es. {"type": "recursive", "chunk_size": 800})';
COMMENT ON COLUMN public.documents.status IS 'Valori ammessi: pending, processing, completed, error';

-- ============================================================================
-- TABELLA DOCUMENT_CHUNKS: Chunk vettorizzati con embedding
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL,
  content TEXT NOT NULL,
  embedding vector(1536),
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indice HNSW per cosine similarity su embedding
CREATE INDEX IF NOT EXISTS document_chunks_embedding_hnsw_idx 
  ON public.document_chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Indice FK per document_id (performance JOIN)
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id
  ON public.document_chunks(document_id);

-- Foreign key constraint verso documents con CASCADE delete
ALTER TABLE public.document_chunks
ADD CONSTRAINT fk_document_chunks_document_id
FOREIGN KEY (document_id)
REFERENCES public.documents(id)
ON DELETE CASCADE;

-- ============================================================================
-- TABELLA PUBLIC.USERS: Mirror di auth.users per test isolation
-- ============================================================================
-- In production, popolare da auth.users tramite trigger/function
-- In test environment, fixture creano direttamente record qui

CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL DEFAULT 'authenticated',
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);

-- ============================================================================
-- TABELLA STUDENT_TOKENS: Credenziali studente annuali
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.student_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  token TEXT UNIQUE NOT NULL,
  is_active BOOLEAN DEFAULT TRUE NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_by_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indici parziali per performance (indicizza solo record attivi)
CREATE INDEX idx_student_tokens_token 
  ON public.student_tokens(token) 
  WHERE is_active = TRUE;

CREATE INDEX idx_student_tokens_created_by 
  ON public.student_tokens(created_by_id);

CREATE INDEX idx_student_tokens_active_not_expired 
  ON public.student_tokens(is_active, expires_at) 
  WHERE is_active = TRUE;

-- ============================================================================
-- TABELLA REFRESH_TOKENS: Sessioni attive studenti
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_token_id UUID NOT NULL REFERENCES public.student_tokens(id) ON DELETE CASCADE,
  token TEXT UNIQUE NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  is_revoked BOOLEAN DEFAULT FALSE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  last_used_at TIMESTAMPTZ
);

-- Indici parziali per performance (indicizza solo token validi)
CREATE INDEX idx_refresh_tokens_token 
  ON public.refresh_tokens(token) 
  WHERE is_revoked = FALSE;

CREATE INDEX idx_refresh_tokens_student_id 
  ON public.refresh_tokens(student_token_id);

CREATE INDEX idx_refresh_tokens_valid 
  ON public.refresh_tokens(is_revoked, expires_at) 
  WHERE is_revoked = FALSE;

-- ============================================================================
-- FUNZIONI UTILITY HARDENED: SECURITY DEFINER + search_path controllato
-- ============================================================================

-- Trigger utility per aggiornare updated_at
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$;

ALTER FUNCTION public.update_updated_at_column()
  OWNER TO service_role;
REVOKE EXECUTE ON FUNCTION public.update_updated_at_column() FROM PUBLIC;

-- Trigger per documents.updated_at
CREATE TRIGGER update_documents_updated_at
  BEFORE UPDATE ON public.documents
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

-- Trigger per autopopolare document_id da metadata in document_chunks
CREATE OR REPLACE FUNCTION public.populate_document_id_from_metadata()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
  IF NEW.document_id IS NULL AND NEW.metadata ? 'document_id' THEN
    NEW.document_id := (NEW.metadata->>'document_id')::uuid;
  END IF;
  RETURN NEW;
END;
$$;

ALTER FUNCTION public.populate_document_id_from_metadata()
  OWNER TO service_role;
REVOKE EXECUTE ON FUNCTION public.populate_document_id_from_metadata() FROM PUBLIC;

CREATE TRIGGER trigger_populate_document_id
  BEFORE INSERT ON public.document_chunks
  FOR EACH ROW
  EXECUTE FUNCTION public.populate_document_id_from_metadata();

-- Funzione di matching semantico con threshold e limit configurabili
CREATE OR REPLACE FUNCTION public.match_document_chunks (
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.75,
  match_count int DEFAULT 8
)
RETURNS TABLE (
  id uuid,
  document_id uuid,
  content text,
  similarity float
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
  SELECT
    dc.id,
    dc.document_id,
    dc.content,
    1 - (dc.embedding <=> query_embedding) AS similarity
  FROM public.document_chunks dc
  WHERE 1 - (dc.embedding <=> query_embedding) > match_threshold
  ORDER BY (dc.embedding <=> query_embedding) ASC
  LIMIT match_count;
$$;

ALTER FUNCTION public.match_document_chunks(vector, float, int)
  OWNER TO service_role;
REVOKE EXECUTE ON FUNCTION public.match_document_chunks(vector, float, int) FROM PUBLIC;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- RLS per public.users (admin-only access)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_admin_all ON public.users
FOR ALL
TO authenticated
USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
WITH CHECK ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- RLS per student_tokens (admin-only management)
-- Nota: SELECT wrapper per auth.jwt() ottimizza performance (Supabase Best Practices)
-- Il query optimizer PostgreSQL cacha il risultato per-statement invece di chiamare per ogni riga
ALTER TABLE public.student_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY student_tokens_admin_all ON public.student_tokens
FOR ALL
TO authenticated
USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
WITH CHECK ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- RLS per refresh_tokens (admin select/update per revoca e audit)
ALTER TABLE public.refresh_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY refresh_tokens_admin_select ON public.refresh_tokens
FOR SELECT
TO authenticated
USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

CREATE POLICY refresh_tokens_admin_revoke ON public.refresh_tokens
FOR UPDATE
TO authenticated
USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
WITH CHECK ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- ============================================================================
-- GRANT per SERVICE_ROLE (backend FastAPI)
-- ============================================================================
-- service_role_key bypassa RLS ma NON bypassa GRANT PostgreSQL
-- Questi GRANT sono CRITICI per il funzionamento del backend

GRANT ALL ON TABLE public.documents TO service_role;
GRANT ALL ON TABLE public.documents TO postgres;

GRANT ALL ON TABLE public.document_chunks TO service_role;
GRANT ALL ON TABLE public.document_chunks TO postgres;

GRANT ALL ON TABLE public.users TO service_role;
GRANT ALL ON TABLE public.users TO postgres;

GRANT ALL ON TABLE public.student_tokens TO service_role;
GRANT ALL ON TABLE public.student_tokens TO postgres;

GRANT ALL ON TABLE public.refresh_tokens TO service_role;
GRANT ALL ON TABLE public.refresh_tokens TO postgres;

COMMIT;

-- ============================================================================
-- VERIFICA POST-DEPLOYMENT (opzionale)
-- ============================================================================
-- Decommentare per verificare schema dopo esecuzione:

-- SELECT table_name, table_type 
-- FROM information_schema.tables 
-- WHERE table_schema = 'public' 
-- ORDER BY table_name;

-- SELECT tablename, indexname, indexdef 
-- FROM pg_indexes 
-- WHERE schemaname = 'public' 
-- ORDER BY tablename, indexname;

-- SELECT grantee, privilege_type, table_name
-- FROM information_schema.table_privileges 
-- WHERE table_schema = 'public'
-- ORDER BY table_name, grantee, privilege_type;


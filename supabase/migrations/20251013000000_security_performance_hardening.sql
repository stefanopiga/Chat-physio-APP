-- Migration: 20251013000000_security_performance_hardening.sql
-- Story 2.7: Hardening di Sicurezza e Ottimizzazione Performance del Database Supabase

BEGIN;

-- =========================================================================
-- Schema dedicato per estensioni e riallocazione vector
-- =========================================================================

CREATE SCHEMA IF NOT EXISTS extensions;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
    ALTER EXTENSION vector SET SCHEMA extensions;
  END IF;
END;
$$;

-- =========================================================================
-- Indice FK per document_chunks(document_id) (AC3)
-- =========================================================================

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id
  ON public.document_chunks(document_id);

-- =========================================================================
-- Funzioni hardened: SECURITY DEFINER + search_path controllato + owner service_role
-- =========================================================================

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

-- Trigger per autopopolare document_id dai metadata
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

DROP TRIGGER IF EXISTS trigger_populate_document_id ON public.document_chunks;
CREATE TRIGGER trigger_populate_document_id
  BEFORE INSERT ON public.document_chunks
  FOR EACH ROW
  EXECUTE FUNCTION public.populate_document_id_from_metadata();

-- Funzione match_document_chunks con hardening
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

-- =========================================================================
-- RLS Policies: wrapper SELECT per auth.jwt()/auth.uid() (AC2)
-- =========================================================================

-- student_tokens
DROP POLICY IF EXISTS student_tokens_admin_all ON public.student_tokens;
CREATE POLICY student_tokens_admin_all ON public.student_tokens
FOR ALL
TO authenticated
USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
WITH CHECK ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- refresh_tokens
DROP POLICY IF EXISTS refresh_tokens_admin_revoke ON public.refresh_tokens;
CREATE POLICY refresh_tokens_admin_revoke ON public.refresh_tokens
FOR UPDATE
TO authenticated
USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
WITH CHECK ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

DROP POLICY IF EXISTS refresh_tokens_admin_select ON public.refresh_tokens;
CREATE POLICY refresh_tokens_admin_select ON public.refresh_tokens
FOR SELECT
TO authenticated
USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- public.users (mirror per test)
DROP POLICY IF EXISTS users_admin_all ON public.users;
CREATE POLICY users_admin_all ON public.users
FOR ALL
TO authenticated
USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
WITH CHECK ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

COMMIT;

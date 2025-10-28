-- Migration: 20251009000000_create_test_users_table.sql
-- Story 5.4.2: FK Constraint Resolution - Test Users Table
-- 
-- Crea tabella public.users per test isolation
-- In production, student_tokens.created_by_id referenzia auth.users(id)
-- Per i test, questa tabella mirror permette di creare user senza accesso a auth schema

-- ============================================================================
-- Tabella public.users: mirror di auth.users per test environment
-- ============================================================================

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

-- RLS policies (admin-only access)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_admin_all ON public.users
FOR ALL
TO authenticated
USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
WITH CHECK ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- GRANT per service_role (backend FastAPI e test)
GRANT ALL ON TABLE public.users TO service_role;
GRANT ALL ON TABLE public.users TO postgres;

-- ============================================================================
-- Migrazione dati esistenti da auth.users a public.users
-- ============================================================================

-- Copia user esistenti da auth.users che sono referenziati in student_tokens
-- Questo evita errore FK constraint quando modifichiamo il constraint
INSERT INTO public.users (id, email, role, created_at, updated_at)
SELECT DISTINCT 
    au.id,
    au.email,
    COALESCE(au.raw_app_meta_data->>'role', 'authenticated') as role,
    au.created_at,
    au.updated_at
FROM auth.users au
INNER JOIN student_tokens st ON st.created_by_id = au.id
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- Modifica FK constraint in student_tokens
-- ============================================================================

-- Drop existing FK constraint che referenzia auth.users
ALTER TABLE student_tokens DROP CONSTRAINT IF EXISTS student_tokens_created_by_id_fkey;

-- Crea new FK constraint che referenzia public.users
-- Questo permette ai test di creare user senza accesso a auth schema
ALTER TABLE student_tokens 
ADD CONSTRAINT student_tokens_created_by_id_fkey 
FOREIGN KEY (created_by_id) REFERENCES public.users(id) ON DELETE CASCADE;

-- Note:
-- - In production environment con auth Supabase, popolare public.users da auth.users tramite trigger/function
-- - In test environment, fixture creano direttamente record in public.users
-- - FK CASCADE garantisce cleanup automatico quando user viene eliminato


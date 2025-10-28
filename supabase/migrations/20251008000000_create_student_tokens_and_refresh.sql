-- Migration: 20251008000000_create_student_tokens_and_refresh.sql
-- Story 1.3.1: Student Token Management System with Refresh Token Pattern
-- Crea tabelle student_tokens e refresh_tokens per gestione accessi studenti annuali

-- ============================================================================
-- Tabella student_tokens: credenziali studente distribuite da admin
-- ============================================================================

CREATE TABLE IF NOT EXISTS student_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  token TEXT UNIQUE NOT NULL,
  is_active BOOLEAN DEFAULT TRUE NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_by_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indici per performance
-- Indice parziale: indicizza solo token attivi (PostgreSQL 18, Sezione 11.8)
-- Beneficio: riduzione dimensione indice, speedup query attivi, speedup soft delete
CREATE INDEX idx_student_tokens_token ON student_tokens(token) WHERE is_active = TRUE;
CREATE INDEX idx_student_tokens_created_by ON student_tokens(created_by_id);
CREATE INDEX idx_student_tokens_active_not_expired ON student_tokens(is_active, expires_at) WHERE is_active = TRUE;

-- RLS policies (admin-only access per management)
-- Performance optimization: wrapping auth.jwt() con SELECT per query optimizer caching (Supabase Best Practices)
ALTER TABLE student_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY student_tokens_admin_all ON student_tokens
FOR ALL
TO authenticated
USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
WITH CHECK ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- Nota performance (Supabase RLS Best Practices):
-- "Use select statement to improve policies that use functions"
-- SELECT wrapping forza initPlan dal query optimizer PostgreSQL, cachando risultato per-statement
-- invece di chiamare auth.jwt() per ogni riga (miglioramento: 94.97-99.993% in test case Supabase)

-- Policy per backend (service_role) per validazione in exchange-code
-- (service_role_key bypassa RLS, policy non necessaria ma documentata)

-- ============================================================================
-- Tabella refresh_tokens: sessioni attive studenti
-- ============================================================================

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_token_id UUID NOT NULL REFERENCES student_tokens(id) ON DELETE CASCADE,
  token TEXT UNIQUE NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  is_revoked BOOLEAN DEFAULT FALSE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  last_used_at TIMESTAMPTZ
);

-- Indici per performance
-- Indici parziali: indicizzano solo token non revocati
CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token) WHERE is_revoked = FALSE;
CREATE INDEX idx_refresh_tokens_student_id ON refresh_tokens(student_token_id);
CREATE INDEX idx_refresh_tokens_valid ON refresh_tokens(is_revoked, expires_at) WHERE is_revoked = FALSE;

-- RLS policies per refresh_tokens
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;

-- Policy per backend (service_role): legge/scrive per validazione refresh
-- (service_role_key bypassa RLS automaticamente)

-- Policy per admin: può revocare refresh tokens quando revoca student token
CREATE POLICY refresh_tokens_admin_revoke ON refresh_tokens
FOR UPDATE
TO authenticated
USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
WITH CHECK ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- Policy per admin: può visualizzare refresh tokens per audit
CREATE POLICY refresh_tokens_admin_select ON refresh_tokens
FOR SELECT
TO authenticated
USING ((SELECT auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- ============================================================================
-- GRANT per service_role (backend FastAPI)
-- ============================================================================

-- GRANT necessari per permettere al backend (service_role_key) di accedere alle tabelle
-- Nota: service_role_key bypassa RLS ma NON bypassa GRANT PostgreSQL
-- IMPORTANTE: Senza questi GRANT, il backend riceverà errore PostgreSQL 42501
--             "permission denied for table student_tokens"
-- Questi GRANT sono CRITICI per il funzionamento del backend
GRANT ALL ON TABLE student_tokens TO service_role;
GRANT ALL ON TABLE student_tokens TO postgres;
GRANT ALL ON TABLE refresh_tokens TO service_role;
GRANT ALL ON TABLE refresh_tokens TO postgres;


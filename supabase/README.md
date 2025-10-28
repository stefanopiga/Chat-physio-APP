# Supabase Database Schema

Schema database PostgreSQL + PGVector per FisioRAG.

## Descrizione

Questa cartella contiene:
- **migrations/**: Migrazioni incrementali del database
- **sql_unico/**: Schema consolidato per setup rapido

## Schema Database

### Tabelle Principali

1. **documents** - Metadati documenti sorgente
   - `id` (UUID, PK)
   - `file_name`, `file_path`, `file_hash`
   - `status` (pending, processing, completed, failed)
   - `metadata` (JSONB)
   - Timestamp: `created_at`, `updated_at`

2. **document_chunks** - Chunks vettorizzati con embeddings
   - `id` (UUID, PK)
   - `document_id` (UUID, FK → documents.id)
   - `content` (TEXT)
   - `embedding` (VECTOR(1536)) - OpenAI embeddings
   - `metadata` (JSONB) - Posizione, classificazione, ecc.
   - Timestamp: `created_at`

3. **student_tokens** - Credenziali accesso studenti
   - `id` (UUID, PK)
   - `token_code` (VARCHAR(12), UNIQUE)
   - `expires_at` (TIMESTAMPTZ)
   - `is_active` (BOOLEAN)
   - FK: `created_by_id` → users.id

4. **refresh_tokens** - Gestione sessioni studenti
   - `id` (UUID, PK)
   - `token_id` (UUID, FK → student_tokens.id)
   - `refresh_token` (VARCHAR, UNIQUE)
   - `expires_at`, `revoked`

5. **users** - Mirror auth.users per test isolation
   - `id` (UUID, PK)
   - `email`, `role` (admin/student)

### Estensioni

- **pgvector** (schema extensions) - Supporto vettori per ricerca semantica

### Indici

- **HNSW index** su `document_chunks.embedding` per cosine similarity
- Indici parziali su token attivi/validi per performance
- Indici FK per JOIN optimization

### Funzioni

1. **match_document_chunks(query_embedding, match_threshold, match_count)**
   - Ricerca semantica vettoriale
   - Cosine similarity con threshold configurabile
   - Ritorna chunks più rilevanti

2. **update_updated_at_column()**
   - Trigger utility per auto-update timestamp

3. **populate_document_id_from_metadata()**
   - Auto-popolazione `document_id` da metadata JSONB

## Setup Locale

### Opzione A: Schema Consolidato (Raccomandato per Setup Nuovo)

Usare lo schema consolidato per creare tutte le tabelle in una volta:

```powershell
# Connessione con service_role
$env:PGPASSWORD = "<your-service-key>"
psql "postgres://postgres.<project-ref>.supabase.co:5432/postgres" -f supabase/sql_unico/00_consolidated_schema.sql
```

Oppure via Supabase Dashboard:
1. Dashboard → SQL Editor
2. Copiare contenuto di `sql_unico/00_consolidated_schema.sql`
3. Eseguire come `service_role`

### Opzione B: Migrazioni Incrementali

Per database esistenti, applicare migrazioni in ordine:

```powershell
# Installare Supabase CLI
scoop install supabase

# Login e link progetto
supabase login
supabase link --project-ref <your-project-ref>

# Push migrations
supabase db push
```

### Migrazioni Disponibili (Ordine Cronologico)

1. `20250922000000_create_document_chunks.sql` - Tabella chunks base
2. `20251004000000_create_documents_table.sql` - Tabella documents + FK
3. `20251005000000_fix_orphan_chunks.sql` - Data migration chunk orfani
4. `20251008000000_create_student_tokens_and_refresh.sql` - Sistema autenticazione studenti
5. `20251009000000_create_test_users_table.sql` - Tabella users per test
6. `20251013000000_security_performance_hardening.sql` - RLS e ottimizzazioni
7. `FIX_GRANT_STUDENT_TOKENS.sql` - Hotfix permessi

**Nota**: Consultare `migrations/README_MIGRATION_20251004.md` per dettagli su pre-requisiti e verifica.

## Verifica Post-Setup

Eseguire query di verifica:

```sql
-- 1. Verifica tabelle create
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('documents', 'document_chunks', 'student_tokens', 'refresh_tokens', 'users');

-- 2. Verifica estensione pgvector
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 3. Verifica indice HNSW
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'document_chunks' 
  AND indexname LIKE '%embedding%';

-- 4. Test funzione match_document_chunks
SELECT match_document_chunks(
  '{0.1, 0.2, ...}'::vector(1536), 
  0.5, 
  5
);

-- 5. Verifica GRANT service_role
SELECT grantee, privilege_type, table_name
FROM information_schema.table_privileges 
WHERE table_schema = 'public'
  AND grantee = 'service_role';
```

## Sicurezza (RLS)

Row Level Security (RLS) è abilitato su tutte le tabelle sensibili:

- **documents**: Admin-only access
- **document_chunks**: Admin-only access
- **student_tokens**: Admin create, students read own
- **refresh_tokens**: Admin manage, students access own

Policy implementate in `20251013000000_security_performance_hardening.sql`.

## Performance

### Ottimizzazioni Implementate

1. **Indice HNSW** su embeddings (cosine similarity search < 100ms)
2. **Indici parziali** su token attivi per filtri frequenti
3. **Funzione SECURITY DEFINER** con `search_path` controllato
4. **Connection pooling** tramite Supabase (PgBouncer)

### Monitoring

Dashboard Supabase → Database → Performance:
- Query slow (> 1s)
- Table sizes
- Index usage

## Troubleshooting

### Errore: extension "vector" does not exist

```sql
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
```

### Errore: permission denied

Verificare che l'utente abbia ruolo `service_role`:

```powershell
# Verificare connection string
echo $env:SUPABASE_SERVICE_KEY
```

### Errore: FK constraint violation

Su database con dati preesistenti, eseguire data migration:

```sql
-- Opzione A: Creare documenti placeholder
INSERT INTO documents (id, file_name, file_path, file_hash, status)
SELECT DISTINCT 
  document_id,
  'migrated_' || document_id,
  '/legacy/',
  'hash_' || document_id,
  'completed'
FROM document_chunks
WHERE document_id NOT IN (SELECT id FROM documents);

-- Opzione B: Eliminare chunk orfani (ATTENZIONE: irreversibile)
DELETE FROM document_chunks
WHERE document_id NOT IN (SELECT id FROM documents);
```

### Query lente su ricerca vettoriale

Verificare HNSW index:

```sql
-- Rebuild index se necessario
REINDEX INDEX CONCURRENTLY idx_document_chunks_embedding_hnsw;
```

## Backup e Restore

### Backup

Supabase esegue backup automatici (retention: 7 giorni per progetti free).

Backup manuale:

```powershell
# Dump schema + data
pg_dump "postgres://postgres.<project-ref>.supabase.co:5432/postgres" > backup.sql

# Dump solo schema
pg_dump --schema-only "postgres://..." > schema.sql
```

### Restore

```powershell
psql "postgres://postgres.<project-ref>.supabase.co:5432/postgres" < backup.sql
```

## Sviluppo Locale con Supabase CLI

Per sviluppo completamente locale:

```powershell
# Start Supabase locale (Docker)
supabase start

# Apply migrations
supabase db reset

# Generare migration da modifiche
supabase db diff -f <migration-name>

# Stop Supabase locale
supabase stop
```

## Riferimenti

- **Schema consolidato**: `sql_unico/00_consolidated_schema.sql`
- **Guide migrazione**: `migrations/README_MIGRATION_20251004.md`
- **Documentazione Supabase**: https://supabase.com/docs/guides/database
- **PGVector docs**: https://github.com/pgvector/pgvector

## Contributors

Sviluppato da Team FisioRAG


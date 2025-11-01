# Supabase Database Schema

Schema database PostgreSQL + PGVector per FisioRAG.

## Descrizione

Questa cartella contiene:
- **migrations/**: Migrazioni incrementali del database
- **sql_unico/**: Schema consolidato per setup rapido

---

## 🐳 Docker Integration

### ⚠️ Supabase è un Servizio Esterno

**IMPORTANTE**: Supabase **NON è presente** in [`docker-compose.yml`](../docker-compose.yml).

**Perché non c'è un container locale Supabase?**

Supabase è un servizio cloud-hosted (Platform-as-a-Service) che fornisce:
- PostgreSQL gestito con PGVector extension
- Authentication & Authorization (Auth.users)
- Real-time subscriptions
- Storage (S3-compatible)
- Auto-scaling e backup automatici

Il sistema FisioRAG si connette a **Supabase Cloud** tramite connection string configurata in variabili d'ambiente.

### Setup Supabase: Cloud vs Local

**Opzione A: Supabase Cloud (Raccomandato per Production)**

Setup tramite [Supabase Dashboard](https://supabase.com/dashboard):
1. Creare progetto su Supabase Cloud
2. Configurare database con schema da `sql_unico/` o `migrations/`
3. Ottenere `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
4. Configurare environment variables (vedere sezione Environment Variables)

**Opzione B: Supabase Local Development (Supabase CLI)**

Per sviluppo completamente locale con Docker:

```powershell
# Prerequisito: Docker Desktop in esecuzione

# Installare Supabase CLI (Windows con Scoop)
scoop install supabase

# Inizializzare progetto locale
supabase init

# Start Supabase stack locale (PostgreSQL, Auth, Storage, etc.)
supabase start

# Output mostra connection strings locali:
# API URL: http://localhost:54321
# DB URL: postgresql://postgres:postgres@localhost:54322/postgres
# Studio URL: http://localhost:54323 (Supabase Dashboard locale)

# Apply migrations
supabase db reset

# Stop stack locale
supabase stop
```

**Nota**: Supabase CLI avvia ~10 container Docker (PostgreSQL, PostgREST, GoTrue Auth, Storage, Realtime, etc.). Verificare risorse disponibili.

### Environment Variables Mapping

**File configurazione root**: [`ISTRUZIONI-USO-VARIABILI-AMBIENTE.md`](../ISTRUZIONI-USO-VARIABILI-AMBIENTE.md)

**Variabili richieste** (in `.env`):

```bash
# Supabase Connection
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<public-anon-key>          # Frontend + public API calls
SUPABASE_SERVICE_ROLE_KEY=<service-role-key> # Backend admin operations (⚠️ SECRET)

# Database Direct Connection (opzionale, per migrazioni)
DATABASE_URL=postgresql://postgres.<project-ref>.supabase.co:5432/postgres
```

**Dove trovare le chiavi:**
- Supabase Dashboard → Project Settings → API
- `SUPABASE_URL`: Project URL
- `SUPABASE_ANON_KEY`: Project API keys → `anon` `public`
- `SUPABASE_SERVICE_ROLE_KEY`: Project API keys → `service_role` ⚠️ **SECRET**

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

---

## 🔐 Security & Connection Details

### ⚠️ IMPORTANTE: service_role vs anon_key

**ATTENZIONE**: Differenze critiche tra le due chiavi Supabase:

| Chiave | Scopo | Permissions | ⚠️ Security Level |
|--------|-------|-------------|-------------------|
| **`SUPABASE_ANON_KEY`** | Frontend, public API calls | Limited by Row Level Security (RLS) policies | ✅ **SAFE** - Può essere esposta in client-side code |
| **`SUPABASE_SERVICE_ROLE_KEY`** | Backend admin operations, bypass RLS | **FULL DATABASE ACCESS** - Bypassa tutte le RLS policies | 🔴 **CRITICAL SECRET** - MAI esporre in frontend o commit in git |

**Best Practices:**

✅ **DO:**
- Usa `anon_key` per tutte le operazioni frontend (React app)
- Usa `service_role` **SOLO** in backend (FastAPI server-side)
- Mantieni `service_role` in `.env` (mai committare)
- Configura RLS policies per proteggere dati con `anon_key`

❌ **DON'T:**
- Mai includere `service_role` in variabili `VITE_*` (esposte nel bundle frontend)
- Mai committare `service_role` in repository
- Mai usare `service_role` in codice client-side

**Security Policy Reference:**
- Per policy RLS dettagliate, vedere migration `20251013000000_security_performance_hardening.sql`
- Supabase Docs: [Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)

### Connection Pooling (PgBouncer)

Supabase fornisce **connection pooling automatico** tramite PgBouncer:

**Connection Strings:**
- **Direct Connection** (transazioni lunghe, migrations): `postgresql://postgres.<project-ref>.supabase.co:5432/postgres`
- **Pooled Connection** (applicazioni, API): `postgresql://postgres.<project-ref>.supabase.co:6543/postgres` (porta 6543)

**Quando usare pooling:**
- ✅ Connessioni applicative frequenti (FastAPI, servizi)
- ✅ Operazioni CRUD standard
- ❌ Migrazioni schema (usare direct connection)
- ❌ Transazioni lunghe o LISTEN/NOTIFY

**Configurazione consigliata** (in `.env`):
```bash
DATABASE_URL=postgresql://postgres.<project-ref>.supabase.co:6543/postgres?pgbouncer=true
```

**Riferimenti:**
- [`ISTRUZIONI-USO-VARIABILI-AMBIENTE.md`](../ISTRUZIONI-USO-VARIABILI-AMBIENTE.md) - Guida completa connection strings
- [Supabase Connection Pooling Docs](https://supabase.com/docs/guides/database/connection-pooling)

### Row Level Security (RLS)

RLS è abilitato su tutte le tabelle sensibili:

- **documents**: Admin-only access
- **document_chunks**: Admin-only access
- **student_tokens**: Admin create, students read own
- **refresh_tokens**: Admin manage, students access own

Policy implementate in `20251013000000_security_performance_hardening.sql`.

---

## ⚡ Performance & Optimization

### Vector Search: HNSW Index

**PGVector HNSW (Hierarchical Navigable Small World)** index è configurato per ricerca semantica veloce.

**Configurazione Index** (da migration `20250922000000_create_document_chunks.sql`):

```sql
CREATE INDEX idx_document_chunks_embedding_hnsw
ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Parametri HNSW spiegati:**

| Parametro | Valore | Significato | Trade-off |
|-----------|--------|-------------|-----------|
| **`m`** | 16 | Numero di connessioni bi-direzionali per nodo nel grafo | ↑ m = migliore recall, maggior memoria |
| **`ef_construction`** | 64 | Dimensione dinamica candidate list durante build | ↑ ef = build più lento, index più accurato |

**Tuning HNSW** (configurato in **Supabase Dashboard → SQL Editor**, NON in docker-compose.yml):

Per dataset più grandi o maggiore accuracy:
```sql
-- Rebuild index con parametri ottimizzati
DROP INDEX idx_document_chunks_embedding_hnsw;
CREATE INDEX idx_document_chunks_embedding_hnsw
ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 32, ef_construction = 128);  -- Maggior accuracy, più memoria
```

**Performance target:**
- Cosine similarity search: < 100ms per query
- Recall@10: > 95%

**Riferimenti:**
- [PGVector HNSW Tuning Guide](https://github.com/pgvector/pgvector#hnsw)
- [Supabase Vector Docs](https://supabase.com/docs/guides/database/extensions/pgvector)

### Query Optimization Tips

**1. Usa il match_document_chunks function per ricerca semantica:**
```sql
SELECT * FROM match_document_chunks(
  query_embedding := '<embedding-vector>'::vector(1536),
  match_threshold := 0.7,  -- Cosine similarity threshold [0-1]
  match_count := 10        -- Top-K results
);
```

**2. Filtra chunks per document_id per scope limitato:**
```sql
SELECT * FROM document_chunks
WHERE document_id = '<specific-doc-id>'
  AND embedding <=> '<query-embedding>'::vector < 0.3  -- Cosine distance
ORDER BY embedding <=> '<query-embedding>'::vector
LIMIT 10;
```

**3. Usa indici parziali per query frequenti:**
```sql
-- Esempio: Solo token attivi e non scaduti
CREATE INDEX idx_student_tokens_active 
ON student_tokens (token_code) 
WHERE is_active = TRUE AND expires_at > NOW();
```

### Monitoring & Tuning

**Supabase Dashboard → Database → Performance:**
- **Slow Queries** (> 1s) - Identificare query da ottimizzare
- **Table Sizes** - Monitorare crescita dati
- **Index Usage** - Verificare indici effettivamente usati
- **Cache Hit Rate** - Target > 99%

**Query per verificare index usage:**
```sql
-- Verifica se HNSW index è usato
EXPLAIN ANALYZE
SELECT * FROM document_chunks
ORDER BY embedding <=> '<query-embedding>'::vector
LIMIT 10;
-- Output dovrebbe mostrare "Index Scan using idx_document_chunks_embedding_hnsw"
```

**Rebuild index se performance degrada:**
```sql
REINDEX INDEX CONCURRENTLY idx_document_chunks_embedding_hnsw;
```

### Ottimizzazioni Implementate

1. ✅ **Indice HNSW** su embeddings (cosine similarity search < 100ms)
2. ✅ **Indici parziali** su token attivi per filtri frequenti
3. ✅ **Funzione SECURITY DEFINER** con `search_path` controllato
4. ✅ **Connection pooling** tramite Supabase (PgBouncer)
5. ✅ **Indici FK** per JOIN optimization

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

---

## 📚 Cross-References

### Documentazione Correlata

| Documento | Descrizione | Link |
|-----------|-------------|------|
| **Data Models Architecture** | Modelli di dati, relazioni, business logic | [`../docs/architecture/sezione-4-modelli-di-dati.md`](../docs/architecture/sezione-4-modelli-di-dati.md) |
| **Frontend Setup** | React app, environment variables | [`../apps/web/README.md`](../apps/web/README.md) |
| **Backend API** | FastAPI, Supabase client usage | [`../apps/api/README.md`](../apps/api/README.md) |
| **Environment Variables** | Connection strings, secrets | [`../ISTRUZIONI-USO-VARIABILI-AMBIENTE.md`](../ISTRUZIONI-USO-VARIABILI-AMBIENTE.md) |

### Riferimenti Esterni

- **Schema consolidato**: `sql_unico/00_consolidated_schema.sql`
- **Guide migrazione**: `migrations/README_MIGRATION_20251004.md`
- **Documentazione Supabase**: https://supabase.com/docs/guides/database
- **PGVector docs**: https://github.com/pgvector/pgvector
- **PGVector HNSW Tuning**: https://github.com/pgvector/pgvector#hnsw
- **Supabase Connection Pooling**: https://supabase.com/docs/guides/database/connection-pooling
- **Supabase Row Level Security**: https://supabase.com/docs/guides/auth/row-level-security

---

## Contributors

Sviluppato da Team FisioRAG


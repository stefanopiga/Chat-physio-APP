# Supabase Database Schema

Schema database PostgreSQL + PGVector per FisioRAG.

## Descrizione

Questa cartella contiene:
- **migrations/**: Migrazioni incrementali del database
- **sql_unico/**: Schema consolidato per setup rapido

---

## 🚀 Quick Start

### Prerequisiti

- **Supabase Account**: [Registrati gratuitamente](https://supabase.com/dashboard)
- **Docker Desktop**: (opzionale, solo per sviluppo locale)
- **Supabase CLI**: (installazione dettagliata nella sezione dedicata)

### Setup Iniziale (3 Step)

**Step 1: Crea Progetto Supabase Cloud**

1. Accedi a [Supabase Dashboard](https://supabase.com/dashboard)
2. Click **"New Project"**
3. Configura:
   - **Name**: `fisiorag-db` (o nome preferito)
   - **Database Password**: Salva in luogo sicuro
   - **Region**: `eu-central-2` (Frankfurt, consigliato per EU)
4. Attendi completamento setup (~2 minuti)

**Step 2: Ottieni Credenziali**

1. Dashboard → **Settings → API**
2. Copia e salva:
   - **Project URL**: `https://<project-ref>.supabase.co`
   - **anon public key**: `eyJhbG...` (per frontend)
   - **service_role key**: `eyJhbG...` ⚠️ **SECRET** (per backend)

3. Dashboard → **Settings → Database → Connection string**
4. Copia **Connection pooling** (porta 6543):
   ```
   postgresql://postgres.<project-ref>:[YOUR-PASSWORD]@aws-1-eu-central-2.pooler.supabase.com:6543/postgres
   ```

**Step 3: Configura Environment Variables**

Crea/aggiorna file `.env` nella root del progetto:

```bash
# Supabase Connection
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-public-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>  # ⚠️ SECRET - Mai committare

# Database Connection (pooled per applicazioni)
DATABASE_URL=postgresql://postgres.<project-ref>:[PASSWORD]@aws-1-eu-central-2.pooler.supabase.com:6543/postgres?pgbouncer=true
```

Guida completa: [`ISTRUZIONI-USO-VARIABILI-AMBIENTE.md`](../ISTRUZIONI-USO-VARIABILI-AMBIENTE.md)

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

### Opzioni di Deployment

**Opzione A: Supabase Cloud (Raccomandato)**

Setup Production-Ready in 5 minuti:
1. Segui **Quick Start** sopra
2. Applica schema database (sezione **Setup Database Schema**)
3. Configura `.env` con credenziali
4. Deploy completato ✅

**Vantaggi**:
- Zero configurazione infrastruttura
- Backup automatici giornalieri
- Auto-scaling
- SSL/TLS nativo
- Dashboard web per monitoring

**Opzione B: Supabase Local Development Stack**

Per sviluppo completamente offline con Docker:

```powershell
# Prerequisito: Docker Desktop in esecuzione

# Installare Supabase CLI (vedere sezione Installazione CLI)
scoop install supabase

# Inizializzare progetto locale (crea cartella supabase/config)
supabase init

# Avvia stack locale (~10 container Docker, ~4GB RAM)
supabase start

# Output mostra connection strings locali:
# API URL: http://localhost:54321
# DB URL: postgresql://postgres:postgres@localhost:54322/postgres
# Studio URL: http://localhost:54323 (Supabase Dashboard locale)
# anon key: eyJhbG...
# service_role key: eyJhbG...

# Apply migrations automatiche dalla cartella supabase/migrations/
supabase db reset

# Stop stack locale
supabase stop
```

**Nota**: Stack locale richiede ~4GB RAM e 10+ container Docker. Per primo setup, consigliato **Opzione A (Cloud)**.

---

## 🛠️ Installazione Supabase CLI

### Windows (Raccomandato: Scoop Package Manager)

**Step 1: Installa Scoop (se non presente)**

```powershell
# Verifica se Scoop già installato
scoop --version

# Se non presente, installa Scoop
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
```

**Step 2: Installa Supabase CLI**

```powershell
scoop install supabase

# Verifica installazione
C:\Users\user\scoop\shims\supabase.exe --version
# Output atteso: 2.58.5 o superiore
```

**Step 3: (Opzionale) Crea Alias per Semplicità**

```powershell
# Aggiungi al profilo PowerShell: $PROFILE
Set-Alias -Name supabase -Value C:\Users\user\scoop\shims\supabase.exe

# Dopo, puoi usare semplicemente:
supabase --version
```

### Metodi Alternativi

**Via NPM:**
```powershell
npm install -g supabase
```

**Via Homebrew (WSL/Linux):**
```bash
brew install supabase/tap/supabase
```

**Riferimenti**:
- [Supabase CLI Official Docs](https://supabase.com/docs/guides/cli)
- [Scoop Package Manager](https://scoop.sh/)

---


**Step 2: Creazione User con ruolo Admin**


accedi alla dashboard supabase, poi

  Authentication → Users → Add user → Create new user
    Compila:
      Email: tizio-caio@example.com 
      Password: [valore password]
      Auto Confirm User: ✅ attiva (importante!)
    Click Create user
      Dopo creazione, click sull'utente → tab User Metadata
      Aggiungi metadato:
        ```
        {
          "role": "admin"
        }
        ```bash
          quindi esegui questa query, sostituisci [ID] con UID dello user appena creato (simile a --> t755b261-4465-71k7-6gu5-054f2r0a3e3da): 
        ```
        ```bash
          UPDATE auth.users SET raw_app_meta_data = jsonb_set(coalesce(raw_app_meta_data, '{}'::jsonb), '{role}', '"admin"') WHERE id = '[ID]'
        ```
      poi verifica con questa query: SELECT id, email, raw_app_meta_data FROM auth.users WHERE id = '[ID]';
    
    Ora aggiorna il file .env nella root alla voce 'ADMIN_EMAIL' e 'ADMIN_PSSWD'

## 📦 Setup Database Schema

Dopo aver creato il progetto Supabase Cloud, applicare lo schema database.

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

### Metodo 1: Schema Consolidato via Dashboard (Raccomandato) ✅

**File**: [`sql_unico/00_consolidated_schema_v2_VERIFIED.sql`](./sql_unico/00_consolidated_schema_v2_VERIFIED.sql)

**Caratteristiche**:
- ✅ Generato tramite reverse engineering da database production (2025-11-11)
- ✅ Schema validato e testato con Supabase CLI 2.58.5
- ✅ Include tutte le tabelle (6), indici HNSW, funzioni, trigger, RLS policies, GRANT
- ✅ Garantito identico al database production funzionante
- ✅ Schema-only: nessun dato incluso (validato)

**Applicazione via Dashboard:**

1. Accedi a **Supabase Dashboard** → tuo progetto
2. Vai su **SQL Editor** (icona database nel menu laterale)
3. Apri il file [`sql_unico/00_consolidated_schema_TEMP.sql`](./sql_unico/00_consolidated_schema_TEMP.sql)
4. Copia **tutto il contenuto** del file (772 righe)
5. Incolla nell'SQL Editor
6. Click **Run** (o Ctrl+Enter)
7. Attendi messaggio di successo (~10-15 secondi)

**Vantaggi**:
- Non richiede CLI installato
- Setup completo in un singolo file SQL
- Interfaccia visuale con feedback immediato
- Schema garantito production-ready

**Verifica applicazione**:
```sql
-- Conteggio tabelle (atteso: 6)
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_schema = 'public';

-- Verifica extension vector disponibile
SELECT * FROM pg_available_extensions WHERE name = 'vector';
```

### Metodo 2: Via Supabase CLI (Professionale) 🚀

**Prerequisiti**:
- Supabase CLI installato (vedere sezione **Installazione Supabase CLI**)
- PostgreSQL Client `psql` (opzionale, solo per query custom)

**Opzione A: Push Migrations da CLI**

```powershell
# 1. Login Supabase (apre browser per autenticazione)
C:\Users\user\scoop\shims\supabase.exe login

# 2. Link progetto esistente
C:\Users\user\scoop\shims\supabase.exe link --project-ref <your-project-ref>
# Project ref visibile in: Dashboard → Settings → General → Reference ID

# 3. Push tutte le migrations dalla cartella supabase/migrations/
C:\Users\user\scoop\shims\supabase.exe db push

# 4. Verifica applicazione migrations
C:\Users\user\scoop\shims\supabase.exe db diff
# Output: "No schema changes detected" = tutto applicato correttamente
```

**Opzione B: Apply Schema via psql**

```powershell
# Installare PostgreSQL client (se non presente)
scoop install postgresql

# Verificare psql disponibile
psql --version

# Applicare schema consolidato
psql "postgresql://postgres.<project-ref>:[PASSWORD]@aws-1-eu-central-2.pooler.supabase.com:5432/postgres" -f supabase/sql_unico/00_consolidated_schema.sql
```

**⚠️ IMPORTANTE**: Per comandi CLI `db push` e `psql`, usare **direct connection** (porta 5432), non pooled (6543).

### Migrazioni Disponibili (Ordine Cronologico)

1. `20250922000000_create_document_chunks.sql` - Tabella chunks base
2. `20251004000000_create_documents_table.sql` - Tabella documents + FK
3. `20251005000000_fix_orphan_chunks.sql` - Data migration chunk orfani
4. `20251008000000_create_student_tokens_and_refresh.sql` - Sistema autenticazione studenti
5. `20251009000000_create_test_users_table.sql` - Tabella users per test
6. `20251013000000_security_performance_hardening.sql` - RLS e ottimizzazioni
7. `FIX_GRANT_STUDENT_TOKENS.sql` - Hotfix permessi

**Nota**: Consultare `migrations/README_MIGRATION_20251004.md` per dettagli su pre-requisiti e verifica.

## 🔍 Verifica Setup e Monitoring Database

### Metodo 1: CLI Inspect Commands (Raccomandato) ✅

**Comandi pre-configurati per statistiche database:**

```powershell
# Sostituisci <CONNECTION_STRING> con la tua direct connection (porta 5432)
# Formato: postgresql://postgres.<ref>:[PASSWORD]@<host>:5432/postgres

# 1. Statistiche tabelle (size, row count)
C:\Users\user\scoop\shims\supabase.exe inspect db table-stats --db-url "<CONNECTION_STRING>"

# Output esempio:
# Name              | Table size | Index size | Total size | Est. row count
# document_chunks   | 48 MB      | 42 MB      | 90 MB      | 5220
# documents         | 288 kB     | 96 kB      | 384 kB     | 90

# 2. Statistiche indici (HNSW verification)
C:\Users\user\scoop\shims\supabase.exe inspect db index-stats --db-url "<CONNECTION_STRING>"

# Output esempio:
# Name                                  | Size  | % Used | Index scans | Unused
# document_chunks_embedding_hnsw_idx    | 42 MB | 100%   | 24          | false

# 3. Statistiche database (cache hit rate, WAL size)
C:\Users\user\scoop\shims\supabase.exe inspect db db-stats --db-url "<CONNECTION_STRING>"

# Output esempio:
# Index Hit Rate | Table Hit Rate | WAL Size
# 1.00 (100%)    | 1.00 (100%)    | 96 MB
```

**⚠️ IMPORTANTE**: Comandi `inspect` richiedono **direct connection** (porta **5432**), NON pooled (6543).

**Errore comune**:
```
ERROR: prepared statement "lrupsc_1_0" already exists
```
**Soluzione**: Cambia porta da 6543 → 5432 nella connection string.

**Connection string corretta per inspect:**
```
postgresql://postgres.<ref>:[PASSWORD]@<host>:5432/postgres
                                      ^^^^^ porta 5432
```

### Metodo 2: Query SQL Custom (via psql o Dashboard)

**Via psql (CLI):**

```powershell
# 1. Verifica tabelle create
psql "<CONNECTION_STRING>" -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('documents', 'document_chunks', 'student_tokens', 'refresh_tokens', 'users')"

# 2. Verifica estensione pgvector
psql "<CONNECTION_STRING>" -c "SELECT * FROM pg_extension WHERE extname = 'vector'"

# 3. Verifica indice HNSW su embeddings
psql "<CONNECTION_STRING>" -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'document_chunks' AND indexname LIKE '%embedding%'"

# 4. Conteggio documenti e chunks
psql "<CONNECTION_STRING>" -c "SELECT (SELECT COUNT(*) FROM documents) as total_documents, (SELECT COUNT(*) FROM document_chunks) as total_chunks"

# 5. Verifica GRANT service_role
psql "<CONNECTION_STRING>" -c "SELECT grantee, privilege_type, table_name FROM information_schema.table_privileges WHERE table_schema = 'public' AND grantee = 'service_role'"
```

**Via Supabase Dashboard:**

1. Dashboard → **SQL Editor**
2. Esegui query di verifica:

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

-- 4. Conteggio documenti e chunks
SELECT 
  (SELECT COUNT(*) FROM documents) as total_documents,
  (SELECT COUNT(*) FROM document_chunks) as total_chunks,
  (SELECT COUNT(*) FROM student_tokens) as total_tokens;

-- 5. Verifica GRANT service_role
SELECT grantee, privilege_type, table_name
FROM information_schema.table_privileges 
WHERE table_schema = 'public'
  AND grantee = 'service_role';
```

### Metodo 3: Supabase Dashboard Built-in Monitoring

**Dashboard → Database → Performance:**
- **Slow Queries**: Query > 1s da ottimizzare
- **Table Sizes**: Crescita dati nel tempo
- **Index Usage**: Verificare indici utilizzati
- **Cache Hit Rate**: Target > 99%

---

## 🔧 Gestione Migrations e Database

### Pull Schema Remoto (per sync locale)

```powershell
# Link progetto (se non già fatto)
C:\Users\user\scoop\shims\supabase.exe login
C:\Users\user\scoop\shims\supabase.exe link --project-ref <your-ref>

# Pull schema remoto → genera migration in supabase/migrations/
C:\Users\user\scoop\shims\supabase.exe db pull
```

### Push Migrations Locali

```powershell
# Push tutte le migrations non ancora applicate
C:\Users\user\scoop\shims\supabase.exe db push

# Verifica differenze tra locale e remoto
C:\Users\user\scoop\shims\supabase.exe db diff
```

### Generare Nuova Migration

```powershell
# Genera migration da modifiche locali
C:\Users\user\scoop\shims\supabase.exe db diff -f <migration-name>

# Esempio: Aggiunta nuova colonna
C:\Users\user\scoop\shims\supabase.exe db diff -f add_new_column_to_documents
```

### Reset Database Locale (⚠️ Distruttivo)

```powershell
# Reset completo database locale (solo stack locale con supabase start)
C:\Users\user\scoop\shims\supabase.exe db reset

# Conferma: Elimina tutti i dati e riapplica migrations
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

Supabase fornisce **connection pooling automatico** tramite PgBouncer per ottimizzare connessioni concurrent.

#### Formati Connection String

**Direct Connection (porta 5432)**
```
postgresql://postgres.<project-ref>:[PASSWORD]@<host>:5432/postgres
```

**Pooled Connection (porta 6543)**
```
postgresql://postgres.<project-ref>:[PASSWORD]@<host>:6543/postgres?pgbouncer=true
```

#### Quando Usare Direct vs Pooled

| Operazione | Connection Type | Porta | Perché |
|------------|----------------|-------|--------|
| **Migrations** (`supabase db push`) | Direct | 5432 | Prepared statements incompatibili con PgBouncer |
| **CLI Inspect** commands | Direct | 5432 | Prepared statements incompatibili con PgBouncer |
| **psql** query custom | Direct | 5432 | Transazioni lunghe, LISTEN/NOTIFY |
| **Applicazioni** (FastAPI, API) | Pooled | 6543 | Performance con connessioni frequenti |
| **Operazioni CRUD** standard | Pooled | 6543 | Riduce overhead connessione |

#### Dove Trovare Connection Strings

**Supabase Dashboard:**
1. Settings → **Database**
2. **Connection string** section
3. Seleziona tab:
   - **Connection pooling** → porta 6543 (per applicazioni)
   - **Direct connection** → porta 5432 (per migrations/CLI)

#### Configurazione Raccomandata (.env)

```bash
# Per applicazioni (FastAPI backend)
DATABASE_URL=postgresql://postgres.<project-ref>:[PASSWORD]@<host>:6543/postgres?pgbouncer=true

# Per migrations e CLI (variabile separata opzionale)
DATABASE_URL_DIRECT=postgresql://postgres.<project-ref>:[PASSWORD]@<host>:5432/postgres
```

#### Troubleshooting Connection Errors

**Errore: "prepared statement already exists"**
```
ERROR: prepared statement "lrupsc_1_0" already exists
```
**Causa**: Usando pooled connection (6543) con comandi CLI inspect  
**Soluzione**: Cambia porta 6543 → 5432

**Errore: "timeout connecting to database"**
**Causa**: Firewall, credenziali errate, o database in pausa  
**Soluzione**:
1. Verifica password corretta
2. Dashboard → Pause/Resume database se in pausa (piano Free)
3. Verifica IP whitelist se configurato

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

---

## 📝 Comandi CLI Utili - Reference Rapido

### Help e Documentazione

```powershell
# Help generale
C:\Users\user\scoop\shims\supabase.exe --help

# Help per categoria database
C:\Users\user\scoop\shims\supabase.exe db --help

# Help per inspect commands
C:\Users\user\scoop\shims\supabase.exe inspect --help

# Versione CLI
C:\Users\user\scoop\shims\supabase.exe --version
```

### Gestione Progetti

```powershell
# Login (apre browser per autenticazione)
C:\Users\user\scoop\shims\supabase.exe login

# Logout
C:\Users\user\scoop\shims\supabase.exe logout

# Lista progetti cloud disponibili
C:\Users\user\scoop\shims\supabase.exe projects list

# Link progetto esistente
C:\Users\user\scoop\shims\supabase.exe link --project-ref <your-ref>

# Unlink progetto
C:\Users\user\scoop\shims\supabase.exe unlink
```

### Database Operations

```powershell
# Pull schema remoto → genera migration locale
C:\Users\user\scoop\shims\supabase.exe db pull

# Push migrations locali → applica a cloud
C:\Users\user\scoop\shims\supabase.exe db push

# Verifica differenze schema locale vs remoto
C:\Users\user\scoop\shims\supabase.exe db diff

# Genera migration da modifiche locali
C:\Users\user\scoop\shims\supabase.exe db diff -f <migration-name>

# Reset database locale (⚠️ solo per stack locale)
C:\Users\user\scoop\shims\supabase.exe db reset
```

### Stack Locale (Docker)

```powershell
# Inizializza progetto locale (crea supabase/config.toml)
C:\Users\user\scoop\shims\supabase.exe init

# Avvia stack locale (~10 container)
C:\Users\user\scoop\shims\supabase.exe start

# Verifica status stack locale
C:\Users\user\scoop\shims\supabase.exe status

# Stop stack locale
C:\Users\user\scoop\shims\supabase.exe stop

# Stop + elimina volumi Docker (⚠️ elimina dati)
C:\Users\user\scoop\shims\supabase.exe stop --no-backup
```

### Configurare Variabili Ambiente (Opzionale)

Per evitare di specificare `--db-url` ogni volta:

```powershell
# PowerShell (sessione temporanea)
$env:DATABASE_URL = "postgresql://postgres.<ref>:[PASSWORD]@<host>:5432/postgres"

# Verifica configurazione
echo $env:DATABASE_URL

# Poi usa comandi senza --db-url
C:\Users\user\scoop\shims\supabase.exe inspect db table-stats
```

Oppure aggiungi a `.env` nella root del progetto (caricato automaticamente da molte applicazioni).

---

## 🎯 Workflow Completi - Guide Pratiche

### Workflow 1: Primo Setup Progetto (da Zero)

**Scenario**: Hai clonato repository e devi configurare database da zero.

```powershell
# 1. Crea progetto Supabase Cloud
# → Vai su https://supabase.com/dashboard
# → New Project → Salva credenziali

# 2. Configura .env nella root del progetto
# → Copia esempio da .env.example
# → Inserisci SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY

# 3. Applica schema via Dashboard SQL Editor
# → Dashboard → SQL Editor
# → Copia contenuto di supabase/sql_unico/00_consolidated_schema.sql
# → Run

# 4. Verifica setup
# → Dashboard → Table Editor → Verifica tabelle create

# 5. (Opzionale) Installa CLI per gestione futura
scoop install supabase
C:\Users\user\scoop\shims\supabase.exe login
C:\Users\user\scoop\shims\supabase.exe link --project-ref <your-ref>

# Setup completato! ✅
```

### Workflow 2: Setup con Supabase CLI (Professionale)

**Scenario**: Setup completo con gestione migrations via CLI.

```powershell
# 1. Installa Supabase CLI
scoop install supabase

# 2. Crea progetto Supabase Cloud (via Dashboard)
# → https://supabase.com/dashboard → New Project

# 3. Configura .env con credenziali

# 4. Login e link progetto
C:\Users\user\scoop\shims\supabase.exe login
C:\Users\user\scoop\shims\supabase.exe link --project-ref <your-ref>

# 5. Push migrations dalla cartella supabase/migrations/
C:\Users\user\scoop\shims\supabase.exe db push

# 6. Verifica applicazione migrations
C:\Users\user\scoop\shims\supabase.exe db diff
# Output: "No schema changes detected" = ✅

# 7. Verifica statistiche database
C:\Users\user\scoop\shims\supabase.exe inspect db table-stats --db-url "postgresql://...5432..."

# Setup completato! ✅
```

### Workflow 3: Sviluppo Locale Completo (Offline)

**Scenario**: Sviluppo completamente offline con database locale Docker.

```powershell
# Prerequisito: Docker Desktop in esecuzione

# 1. Installa Supabase CLI
scoop install supabase

# 2. Inizializza progetto locale
C:\Users\user\scoop\shims\supabase.exe init

# 3. Avvia stack locale (~10 container, ~4GB RAM)
C:\Users\user\scoop\shims\supabase.exe start

# Output:
# API URL: http://localhost:54321
# DB URL: postgresql://postgres:postgres@localhost:54322/postgres
# Studio URL: http://localhost:54323

# 4. Le migrations in supabase/migrations/ sono applicate automaticamente

# 5. Accedi a Studio locale per verificare
# → Apri http://localhost:54323 nel browser

# 6. Lavora in locale, modifica schema, genera migrations
C:\Users\user\scoop\shims\supabase.exe db diff -f my_new_migration

# 7. Quando pronto, push a cloud
C:\Users\user\scoop\shims\supabase.exe login
C:\Users\user\scoop\shims\supabase.exe link --project-ref <your-ref>
C:\Users\user\scoop\shims\supabase.exe db push

# 8. Stop stack locale quando finito
C:\Users\user\scoop\shims\supabase.exe stop

# Setup completato! ✅
```

### Workflow 4: Verifica Database dopo Deploy

**Scenario**: Verificare stato database dopo deploy applicazione.

```powershell
# Metodo 1: Via CLI Inspect (Raccomandato)
C:\Users\user\scoop\shims\supabase.exe inspect db table-stats --db-url "postgresql://...5432..."
C:\Users\user\scoop\shims\supabase.exe inspect db index-stats --db-url "postgresql://...5432..."
C:\Users\user\scoop\shims\supabase.exe inspect db db-stats --db-url "postgresql://...5432..."

# Metodo 2: Via Dashboard
# → Dashboard → Database → Performance
# → Verifica Cache Hit Rate > 99%
# → Verifica Index Usage

# Metodo 3: Via psql (query custom)
scoop install postgresql
psql "postgresql://...5432..." -c "SELECT COUNT(*) FROM document_chunks"
psql "postgresql://...5432..." -c "SELECT pg_size_pretty(pg_database_size('postgres'))"

# Verifica completata! ✅
```

---

## 🚨 Troubleshooting Comune

### Errore: extension "vector" does not exist

**Sintomo**:
```
ERROR: extension "vector" does not exist
```

**Causa**: PGVector extension non abilitata nel progetto Supabase.

**Soluzione**:
```sql
-- Esegui in Dashboard SQL Editor con ruolo service_role
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
```

Oppure verifica che migration `20250922000000_create_document_chunks.sql` sia stata applicata.

---

### Errore: prepared statement already exists

**Sintomo**:
```
ERROR: prepared statement "lrupsc_1_0" already exists
```

**Causa**: Usando pooled connection (porta 6543) con comandi CLI `inspect` che usano prepared statements incompatibili con PgBouncer.

**Soluzione**:
```powershell
# ❌ ERRATO (pooled connection)
C:\Users\user\scoop\shims\supabase.exe inspect db table-stats --db-url "postgresql://...6543..."

# ✅ CORRETTO (direct connection)
C:\Users\user\scoop\shims\supabase.exe inspect db table-stats --db-url "postgresql://...5432..."
#                                                                                     ^^^^^ porta 5432
```

**Regola generale**: Comandi `inspect` e `db push` richiedono **direct connection** (porta 5432).

---

### Errore: permission denied for table

**Sintomo**:
```
ERROR: permission denied for table documents
```

**Causa**: 
1. Usando `anon_key` invece di `service_role` per operazioni admin
2. Row Level Security (RLS) policies bloccano operazione
3. GRANT mancanti per ruolo

**Soluzione**:

**Opzione 1**: Usare `service_role` per operazioni admin backend
```bash
# In .env, verifica di usare service_role per backend
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
```

**Opzione 2**: Verificare GRANT
```sql
-- Verifica permessi per service_role
SELECT grantee, privilege_type, table_name
FROM information_schema.table_privileges 
WHERE table_schema = 'public' AND grantee = 'service_role';

-- Se mancanti, esegui migration FIX_GRANT_STUDENT_TOKENS.sql
-- Oppure applica manualmente:
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
```

**Opzione 3**: RLS policy configuration
```sql
-- Verifica policy RLS per tabella
SELECT * FROM pg_policies WHERE tablename = 'documents';

-- Vedi migration 20251013000000_security_performance_hardening.sql per policy corrette
```

---

### Errore: FK constraint violation (orphan chunks)

**Sintomo**:
```
ERROR: insert or update on table "document_chunks" violates foreign key constraint
```

**Causa**: Tentativo di inserire chunk con `document_id` inesistente in tabella `documents`.

**Soluzione**:

**Opzione 1**: Creare documento prima del chunk
```sql
-- Inserisci documento prima
INSERT INTO documents (id, file_name, file_path, file_hash, status)
VALUES ('<uuid>', 'filename.pdf', '/path/', 'hash123', 'completed');

-- Poi inserisci chunk
INSERT INTO document_chunks (document_id, content, embedding, metadata)
VALUES ('<uuid>', 'content...', '<embedding>', '{}');
```

**Opzione 2**: Data migration per chunk orfani esistenti
```sql
-- Opzione A: Crea documenti placeholder per chunks orfani
INSERT INTO documents (id, file_name, file_path, file_hash, status)
SELECT DISTINCT 
  document_id,
  'migrated_' || document_id,
  '/legacy/',
  'hash_' || document_id,
  'completed'
FROM document_chunks
WHERE document_id NOT IN (SELECT id FROM documents);

-- Opzione B: Elimina chunk orfani (⚠️ irreversibile)
DELETE FROM document_chunks
WHERE document_id NOT IN (SELECT id FROM documents);
```

Riferimento: [`migrations/20251005000000_fix_orphan_chunks.sql`](./migrations/20251005000000_fix_orphan_chunks.sql)

---

### Errore: connection timeout

**Sintomo**:
```
ERROR: timeout connecting to database
```

**Causa**:
1. Database in pausa (piano Free Supabase)
2. Credenziali errate (password)
3. Firewall/IP whitelist
4. Regione errata nella connection string

**Soluzione**:

**1. Verifica stato database**
```
Dashboard → Settings → General → Project Status
Se "Paused", click "Resume"
```

**2. Verifica credenziali**
```powershell
# Dashboard → Settings → Database → Connection string
# Copia nuovamente password e verifica nessun carattere nascosto
```

**3. Verifica IP whitelist (se configurato)**
```
Dashboard → Settings → Database → Connection pooling
→ Add IP address se necessario
```

**4. Test connettività**
```powershell
# Test con psql
psql "postgresql://postgres.<ref>:[PASSWORD]@<host>:5432/postgres" -c "SELECT 1"
```

---

### Query lente su ricerca vettoriale

**Sintomo**: Query `match_document_chunks` impiega > 1 secondo.

**Causa**: 
1. HNSW index non utilizzato
2. Index degradato dopo molti inserimenti
3. Parametri HNSW non ottimizzati

**Soluzione**:

**1. Verifica index usage**
```sql
EXPLAIN ANALYZE
SELECT * FROM document_chunks
ORDER BY embedding <=> '<query-embedding>'::vector
LIMIT 10;

-- Output deve mostrare "Index Scan using document_chunks_embedding_hnsw_idx"
-- Se mostra "Seq Scan", index non utilizzato!
```

**2. Rebuild index**
```sql
-- Rebuild concurrent (non blocca queries)
REINDEX INDEX CONCURRENTLY document_chunks_embedding_hnsw_idx;
```

**3. Ottimizza parametri HNSW**
```sql
-- Per dataset grandi (> 100k chunks), aumenta m e ef_construction
DROP INDEX document_chunks_embedding_hnsw_idx;
CREATE INDEX document_chunks_embedding_hnsw_idx
ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 32, ef_construction = 128);  -- Migliore accuracy, più memoria
```

Riferimento: Sezione **Performance & Optimization** in questo README.

---

### Errore: Supabase CLI comando non trovato

**Sintomo**:
```powershell
supabase : The term 'supabase' is not recognized...
```

**Causa**: Supabase CLI non installato o non nel PATH.

**Soluzione**:

**Windows (Scoop)**:
```powershell
# Installa Scoop se non presente
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression

# Installa Supabase CLI
scoop install supabase

# Usa path completo o crea alias
C:\Users\user\scoop\shims\supabase.exe --version
```

**Alternative**:
```powershell
# Via NPM
npm install -g supabase

# Via Chocolatey
choco install supabase
```

---

### Database troppo grande (piano Free)

**Sintomo**: Errore storage limit exceeded (500MB per progetti Free).

**Causa**: Database ha superato quota Free tier.

**Soluzione**:

**1. Verifica size attuale**
```powershell
C:\Users\user\scoop\shims\supabase.exe inspect db db-stats --db-url "postgresql://...5432..."
# Controlla "Database Size"
```

**2. Identifica tabelle più grandi**
```powershell
C:\Users\user\scoop\shims\supabase.exe inspect db table-stats --db-url "postgresql://...5432..."
```

**3. Pulizia dati**
```sql
-- Elimina chunks vecchi/inutilizzati
DELETE FROM document_chunks
WHERE created_at < NOW() - INTERVAL '90 days';

-- Elimina documenti failed
DELETE FROM documents WHERE status = 'failed';

-- Vacuum per recuperare spazio
VACUUM FULL;
```

**4. Upgrade a piano Pro ($25/mese)**
```
Dashboard → Settings → Billing → Upgrade to Pro
→ 8GB storage incluso
```

---

## 📚 Cross-References

### Documentazione Correlata

| Documento | Descrizione | Link |
|-----------|-------------|------|
| **Data Models Architecture** | Modelli di dati, relazioni, business logic | [`../docs/architecture/sezione-4-modelli-di-dati.md`](../docs/architecture/sezione-4-modelli-di-dati.md) |
| **Frontend Setup** | React app, environment variables | [`../apps/web/README.md`](../apps/web/README.md) |
| **Backend API** | FastAPI, Supabase client usage | [`../apps/api/README.md`](../apps/api/README.md) |
| **Environment Variables** | Connection strings, secrets management | [`../ISTRUZIONI-USO-VARIABILI-AMBIENTE.md`](../ISTRUZIONI-USO-VARIABILI-AMBIENTE.md) |
| **CLI Installation Summary** | Installazione completata CLI, test eseguiti | [`SUPABASE_CLI_INSTALLATION_SUMMARY.md`](./SUPABASE_CLI_INSTALLATION_SUMMARY.md) |
| **CLI Usage Guide** | Guida dettagliata comandi CLI | [`SUPABASE_CLI_USAGE.md`](./SUPABASE_CLI_USAGE.md) |

### File Schema e Migrations

| File | Descrizione | Quando Usare |
|------|-------------|--------------|
| **`sql_unico/00_consolidated_schema.sql`** | Schema completo database (tutte le tabelle in un file) | Setup nuovo progetto da zero |
| **`migrations/20250922000000_create_document_chunks.sql`** | Migration iniziale chunks + PGVector | Primo setup migrations incrementali |
| **`migrations/20251004000000_create_documents_table.sql`** | Tabella documents + FK constraints | Dopo create_document_chunks |
| **`migrations/20251005000000_fix_orphan_chunks.sql`** | Data migration per chunks orfani | Solo se hai chunks esistenti senza documents |
| **`migrations/20251008000000_create_student_tokens_and_refresh.sql`** | Sistema autenticazione studenti | Setup completo auth |
| **`migrations/20251009000000_create_test_users_table.sql`** | Tabella users per test isolation | Setup ambiente test |
| **`migrations/20251013000000_security_performance_hardening.sql`** | RLS policies + performance optimization | Production hardening |
| **`migrations/FIX_GRANT_STUDENT_TOKENS.sql`** | Hotfix permessi service_role | Solo se errori permission denied |
| **`migrations/README_MIGRATION_20251004.md`** | Guida dettagliata migration documents | Pre-requisiti e troubleshooting |

### Riferimenti Esterni

**Supabase Documentation:**
- [Database Guide](https://supabase.com/docs/guides/database)
- [Connection Pooling](https://supabase.com/docs/guides/database/connection-pooling)
- [Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)
- [CLI Reference](https://supabase.com/docs/reference/cli)
- [Migrations Guide](https://supabase.com/docs/guides/cli/local-development#database-migrations)

**PGVector:**
- [PGVector GitHub](https://github.com/pgvector/pgvector)
- [HNSW Index Tuning Guide](https://github.com/pgvector/pgvector#hnsw)
- [Performance Tips](https://github.com/pgvector/pgvector#performance)

**Tools:**
- [Scoop Package Manager](https://scoop.sh/)
- [PostgreSQL Downloads](https://www.postgresql.org/download/)

---

## 📋 Checklist Setup Completo

Usa questa checklist per verificare setup corretto:

- [ ] **Progetto Supabase Cloud creato**
  - [ ] Region selezionata (eu-central-2 raccomandato)
  - [ ] Database password salvata in luogo sicuro

- [ ] **Credenziali configurate in `.env`**
  - [ ] `SUPABASE_URL` impostato
  - [ ] `SUPABASE_ANON_KEY` impostato
  - [ ] `SUPABASE_SERVICE_ROLE_KEY` impostato (⚠️ SECRET)
  - [ ] `DATABASE_URL` impostato (pooled connection, porta 6543)

- [ ] **Schema database applicato**
  - [ ] Via Dashboard SQL Editor: `00_consolidated_schema.sql` eseguito
  - [ ] Oppure via CLI: `supabase db push` completato
  - [ ] Tabelle create: `documents`, `document_chunks`, `student_tokens`, `refresh_tokens`, `users`

- [ ] **Estensioni verificate**
  - [ ] PGVector extension abilitata
  - [ ] HNSW index su `document_chunks.embedding` presente

- [ ] **Permessi verificati**
  - [ ] GRANT service_role su tutte le tabelle
  - [ ] RLS policies configurate correttamente

- [ ] **Supabase CLI (opzionale ma raccomandato)**
  - [ ] CLI installato via Scoop
  - [ ] Login eseguito: `supabase login`
  - [ ] Progetto linkato: `supabase link --project-ref <ref>`

- [ ] **Creazione User con ruolo di Admin**
  - [ ] Creazione User + sql query + di verifica

- [ ] **Test connessione**
  - [ ] CLI inspect funzionante: `supabase inspect db table-stats --db-url "...5432..."`
  - [ ] Application può connettersi con pooled connection (porta 6543)

- [ ] **Verifica performance**
  - [ ] Cache Hit Rate > 99% (Dashboard → Database → Performance)
  - [ ] HNSW index utilizzato per ricerca vettoriale

---

## ℹ️ Versioni e Compatibilità

| Componente | Versione Testata | Note |
|------------|------------------|------|
| **Supabase CLI** | 2.58.5+ | Installato via Scoop su Windows |
| **PostgreSQL** | 15.x | Gestito da Supabase Cloud |
| **PGVector** | 0.5.0+ | Extension abilitata in Supabase |
| **Python** | 3.9+ | Per backend FastAPI |
| **Node.js** | 18+ | Per frontend React |
| **Docker Desktop** | 4.20+ | Solo per stack locale |

**Ultimo aggiornamento documentazione**: 11 Novembre 2025

---

## 👥 Contributors & Support

Sviluppato da Team FisioRAG.

**Support Channels:**
- Issues GitHub per bug e feature requests
- Consultare sezione **Troubleshooting** per problemi comuni
- [Supabase Community Discord](https://discord.supabase.com/) per supporto Supabase

**Contributi benvenuti:**
- Miglioramenti migrations
- Ottimizzazioni performance
- Documentazione aggiuntiva


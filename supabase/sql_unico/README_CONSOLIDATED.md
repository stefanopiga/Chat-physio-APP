# Schema Consolidato FisioRAG

## Descrizione

Il file `00_consolidated_schema.sql` contiene tutte le migrazioni del progetto FisioRAG consolidate in un unico script eseguibile. Questo permette di creare da zero lo schema completo del database su un nuovo progetto Supabase.

## Cosa Include

### Tabelle
1. **documents** - Metadati file sorgente caricati
2. **document_chunks** - Chunk vettorizzati con embedding (vector 1536)
3. **users** - Mirror di auth.users per test isolation
4. **student_tokens** - Sistema credenziali studenti annuali
5. **refresh_tokens** - Gestione sessioni attive studenti

### Estensioni
- **pgvector** - Supporto vettori per ricerca semantica (schema extensions)

### Indici
- HNSW per ricerca vettoriale cosine similarity
- Indici parziali ottimizzati per token attivi/validi
- Indici FK per performance JOIN

### Funzioni
- **match_document_chunks()** - Ricerca semantica con threshold/limit configurabili
- **update_updated_at_column()** - Trigger utility per timestamp
- **populate_document_id_from_metadata()** - Auto-popolazione document_id

### Sicurezza
- Row Level Security (RLS) su tutte le tabelle sensibili
- Funzioni SECURITY DEFINER con search_path controllato
- Policy admin-only per management
- GRANT service_role per backend FastAPI

## Uso

### Nuovo Progetto Supabase

```bash
# Connetti al DB con service_role o postgres
psql "postgres://postgres:[PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres"

# Esegui lo schema consolidato
\i 00_consolidated_schema.sql
```

### Supabase Dashboard

1. Dashboard > SQL Editor
2. Copia contenuto `00_consolidated_schema.sql`
3. Esegui come `service_role` o `postgres`
4. Verifica creazione tabelle e indici

### Verifica Post-Deployment

Decommentare query di verifica in fondo al file consolidato per controllare:
- Tabelle create
- Indici applicati
- GRANT configurati

## Differenze vs Migrazioni Incrementali

### Non Include
- Data migration per chunk orfani (`20251005000000_fix_orphan_chunks.sql`)
  - Non necessaria su DB nuovo senza dati preesistenti
- Copia dati da `auth.users` a `public.users`
  - Su DB nuovo, popolare `public.users` direttamente o tramite trigger

### Consolidamenti
- GRANT ridondanti rimossi (FIX_GRANT_STUDENT_TOKENS già in 20251008)
- Funzioni aggiornate alla versione hardened finale
- RLS policies ottimizzate con SELECT wrapper

## Storico Migrazioni Originali

Migrazioni consolidate in ordine cronologico:

1. `20250922000000_create_document_chunks.sql` - Story 2.4
2. `20251004000000_create_documents_table.sql` - Story 4.4
3. `20251005000000_fix_orphan_chunks.sql` - Data migration
4. `20251008000000_create_student_tokens_and_refresh.sql` - Story 1.3.1
5. `20251009000000_create_test_users_table.sql` - Story 5.4.2
6. `20251013000000_security_performance_hardening.sql` - Story 2.7
7. `FIX_GRANT_STUDENT_TOKENS.sql` - Hotfix permessi

## Note Produzione

### public.users vs auth.users
In produzione con auth Supabase, considerare:
- Trigger/function per sincronizzare `auth.users` → `public.users`
- Oppure modificare FK `student_tokens.created_by_id` per referenziare direttamente `auth.users(id)`

### Test Environment
Per testing isolation, `public.users` permette di:
- Creare user senza accesso a `auth` schema
- Test più veloci senza dipendenze auth Supabase
- Fixture deterministiche per test automatizzati

## Troubleshooting

### Errore: extension "vector" does not exist
```sql
CREATE EXTENSION vector WITH SCHEMA extensions;
```

### Errore: permission denied for table
Verificare GRANT service_role:
```sql
SELECT grantee, privilege_type, table_name
FROM information_schema.table_privileges 
WHERE table_schema = 'public'
  AND table_name IN ('student_tokens', 'refresh_tokens', 'documents', 'document_chunks', 'users');
```

### Errore FK constraint violation
Su DB con dati preesistenti, eseguire data migration prima di applicare FK constraint.


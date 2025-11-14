# Schema Consolidato Supabase - FisioRAG

## File: `00_consolidated_schema_v2_NEWPROJECT.sql`

### Descrizione

Schema SQL consolidato per nuovi progetti Supabase. Contiene tutte le tabelle, indici, funzioni, trigger e policy necessarie per l'applicazione FisioRAG.

**Revision**: 4 (2025-01-12)  
**Status**: Aggiornato con Epic 9 (Persistent Conversational Memory)

---

## 📦 Contenuto

### Tabelle (7 totali)

1. **documents** - Metadati documenti caricati
2. **document_chunks** - Chunk vettoriali per RAG
3. **student_tokens** - Token accesso studenti
4. **refresh_tokens** - Token refresh JWT
5. **users** - Utenti applicazione (mirror di auth.users)
6. **feedback** - Feedback utenti sui messaggi chat
7. **chat_messages** - Memoria persistente conversazioni (Epic 9)

### Funzionalità Principali

- **PGVector Extension**: Embeddings vettoriali per semantic search
- **HNSW Index**: Ricerca vettoriale ottimizzata (m=16, ef_construction=64)
- **Full-Text Search**: Indice GIN per ricerca testuale in Italiano
- **Auto-Sync**: Trigger automatico auth.users → public.users
- **Row Level Security**: Policy RLS per feedback, tokens, users
- **Idempotency**: Deduplicazione messaggi chat via idempotency_key
- **Session History**: Indici ottimizzati per recupero storico conversazioni

---

## 🚀 Utilizzo

### Per Nuovo Progetto Supabase

```bash
# 1. Crea nuovo progetto su supabase.com
# 2. Ottieni le credenziali di connessione
# 3. Esegui lo schema consolidato

psql -h db.<your-project-ref>.supabase.co \
     -U postgres \
     -d postgres \
     -p 5432 \
     -f supabase/sql_unico/00_consolidated_schema_v2_NEWPROJECT.sql
```

### Tramite Supabase CLI

```bash
# 1. Collega il progetto
supabase link --project-ref <your-project-ref>

# 2. Esegui lo schema
supabase db push --db-url "postgresql://postgres:[password]@db.<your-project-ref>.supabase.co:5432/postgres" \
                 --file supabase/sql_unico/00_consolidated_schema_v2_NEWPROJECT.sql
```

### Via Supabase Dashboard (SQL Editor)

1. Accedi a Supabase Dashboard
2. Vai su **SQL Editor**
3. Copia/incolla il contenuto di `00_consolidated_schema_v2_NEWPROJECT.sql`
4. Esegui (Run)

---

## ✅ Verifica Post-Installazione

```sql
-- 1. Verifica tabelle create
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Output atteso: 7 tabelle
-- chat_messages, document_chunks, documents, feedback, 
-- refresh_tokens, student_tokens, users

-- 2. Verifica estensione PGVector
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 3. Verifica indici chat_messages
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'chat_messages';

-- Output atteso: 6 indici
-- idx_chat_messages_idempotency_key (UNIQUE)
-- idx_chat_messages_session_created
-- idx_chat_messages_created_at
-- idx_chat_messages_content_fts (GIN Italian)
-- idx_chat_messages_metadata_archived (PARTIAL)
-- chat_messages_pkey

-- 4. Test idempotency constraint
INSERT INTO public.chat_messages 
  (session_id, role, content, idempotency_key)
VALUES 
  ('test-session', 'user', 'test message', 'test-key-123');

-- Questo dovrebbe fallire (duplicate key):
INSERT INTO public.chat_messages 
  (session_id, role, content, idempotency_key)
VALUES 
  ('test-session', 'user', 'another message', 'test-key-123');
-- ERROR: duplicate key value violates unique constraint

-- Cleanup
DELETE FROM public.chat_messages WHERE idempotency_key = 'test-key-123';
```

---

## 📝 Changelog

### Revision 4 (2025-01-12)
- ✅ Aggiunta tabella `chat_messages` (Epic 9 Story 9.1)
- ✅ Aggiunto indice UNIQUE su `idempotency_key` per deduplicazione
- ✅ Aggiunto indice composto `(session_id, created_at DESC)` per session history
- ✅ Aggiunto indice GIN Full-Text Search in Italiano
- ✅ Aggiunto indice PARTIAL per messaggi archiviati
- ✅ Aggiunto CHECK constraint su `role` (user/assistant/system)
- ✅ Aggiunto campo `source_chunk_ids UUID[]` per citations RAG

### Revision 3 (2025-11-11)
- Rimossi GRANT circolari su extensions
- Pulizia schema per nuovi progetti

### Revision 2
- Schema base consolidato da produzione

---

## 🔒 Note di Sicurezza

### RLS Disabilitato per chat_messages

La tabella `chat_messages` **NON ha RLS abilitato** per scelta progettuale:
- L'accesso è controllato a livello applicativo (FastAPI JWT)
- Il `service_role` del backend gestisce tutte le operazioni
- Future story potranno aggiungere RLS se necessario

### Permessi

- **service_role**: ALL su tutte le tabelle (backend API)
- **postgres**: Owner di tutte le tabelle
- **authenticated**: Solo tramite RLS policy (feedback, tokens, users)
- **anon**: Solo schema extensions (per pgvector public functions)

---

## 📚 Riferimenti

- **Story 9.1**: Hybrid Memory Architecture (L1 cache + L2 DB)
- **Story 9.2**: Session History Retrieval & UI Integration
- **Migration File**: `supabase/migrations/20251106000000_epic9_conversational_memory_indices.sql`
- **Architecture**: `docs/architecture/addendum-persistent-conversational-memory.md`

---

## ⚠️ Importante

Questo file è **AUTOSUFFICIENTE** per nuovi progetti. Non è necessario eseguire altre migration se si parte da zero.

Per progetti esistenti che hanno già lo schema base (Revision 3), eseguire solo la migration Epic 9:
```bash
psql ... -f supabase/migrations/20251106000000_epic9_conversational_memory_indices.sql
```

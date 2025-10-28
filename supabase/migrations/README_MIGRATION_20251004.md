# Guida Esecuzione Migrazione: Tabella Documents

**File**: `20251004000000_create_documents_table.sql`  
**Obiettivo**: Creare tabella `documents` e aggiungere foreign key constraint a `document_chunks`  
**Story Correlata**: 4.4 - Document Chunk Explorer

---

## Pre-Requisiti

Prima di eseguire la migrazione, verificare che la tabella `document_chunks` non contenga record con `document_id` orfani.

### Query di Verifica

Connettersi al database Supabase ed eseguire:

```sql
-- Verifica: conteggio record in document_chunks
SELECT COUNT(*) as total_chunks FROM document_chunks;

-- Verifica: lista document_id univoci
SELECT DISTINCT document_id FROM document_chunks LIMIT 10;
```

Se la tabella `document_chunks` contiene già record, sarà necessario:

1. **Opzione A** (Consigliata): Creare record dummy nella tabella `documents` per i `document_id` esistenti:

   ```sql
   -- Inserire documenti placeholder per document_id esistenti
   INSERT INTO documents (id, file_name, file_path, file_hash, status)
   SELECT DISTINCT 
     document_id,
     'migrated_document_' || document_id,
     '/legacy/' || document_id,
     'hash_' || document_id,
     'completed'
   FROM document_chunks
   WHERE NOT EXISTS (SELECT 1 FROM documents WHERE id = document_chunks.document_id);
   ```

2. **Opzione B** (Solo se appropriato): Eliminare i chunk orfani:

   ```sql
   -- ATTENZIONE: Questa operazione è irreversibile
   DELETE FROM document_chunks
   WHERE document_id NOT IN (SELECT id FROM documents);
   ```

---

## Esecuzione Migrazione

### Metodo 1: Supabase CLI

```bash
# Dalla root del progetto
supabase db push
```

### Metodo 2: Supabase Dashboard

1. Accedere a [Supabase Dashboard](https://app.supabase.com/)
2. Selezionare il progetto
3. Navigare in **SQL Editor**
4. Copiare il contenuto di `20251004000000_create_documents_table.sql`
5. Eseguire la query
6. Verificare l'output per eventuali errori

### Metodo 3: SQL diretto (psql)

```bash
# Utilizzare la connection string dal dashboard Supabase
psql "postgresql://postgres:[PASSWORD]@[PROJECT_REF].supabase.co:5432/postgres" \
  -f supabase/migrations/20251004000000_create_documents_table.sql
```

---

## Verifica Post-Migrazione

Eseguire le seguenti query per confermare il successo della migrazione:

```sql
-- 1. Verifica esistenza tabella
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name = 'documents';

-- 2. Verifica colonne
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'documents'
ORDER BY ordinal_position;

-- 3. Verifica constraint
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'documents';

-- 4. Verifica foreign key su document_chunks
SELECT 
  tc.constraint_name,
  tc.table_name,
  kcu.column_name,
  ccu.table_name AS foreign_table_name,
  ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu
  ON tc.constraint_name = ccu.constraint_name
WHERE tc.table_name = 'document_chunks'
  AND tc.constraint_type = 'FOREIGN KEY';

-- 5. Test inserimento record
INSERT INTO documents (file_name, file_path, file_hash, status)
VALUES ('test_migration.pdf', '/test/test_migration.pdf', 'test_hash_001', 'pending')
RETURNING *;

-- 6. Test query di aggregazione (usata in Story 4.4)
SELECT 
  d.id,
  d.file_name,
  d.created_at,
  COUNT(dc.id) as total_chunks
FROM documents d
LEFT JOIN document_chunks dc ON d.id = dc.document_id
GROUP BY d.id, d.file_name, d.created_at
ORDER BY d.created_at DESC;
```

---

## Rollback (Se Necessario)

In caso di problemi, eseguire il rollback:

```sql
-- Rimuovere foreign key constraint
ALTER TABLE document_chunks
DROP CONSTRAINT IF EXISTS fk_document_chunks_document_id;

-- Rimuovere trigger
DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Rimuovere tabella
DROP TABLE IF EXISTS documents;
```

---

## Note Aggiuntive

- **Backup**: Eseguire sempre un backup del database prima di migrazioni strutturali
- **Timing**: Eseguire la migrazione in orario di basso traffico
- **Monitoraggio**: Verificare i log Supabase dopo l'esecuzione per eventuali warning
- **Documentazione**: Dopo migrazione completata, aggiornare il rischio R-4.4-3 a "RISOLTO"

---

**Riferimenti**:
- Report Indagine: `docs/qa/assessments/INDAGINE_TABELLA_DOCUMENTS_20251004.md`
- Schema Documentato: `docs/architecture/sezione-4-modelli-di-dati.md` (Modello 4.3)
- Story Bloccata: `docs/stories/4.4-document-chunk-explorer.md`


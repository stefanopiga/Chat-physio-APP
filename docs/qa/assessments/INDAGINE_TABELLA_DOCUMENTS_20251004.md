# Report di Indagine Tecnica: Tabella `documents`

**Data**: 2025-10-04  
**Richiedente**: Tech Lead / Scrum Master  
**Esecutore**: Database Administrator (DBA)  
**Obiettivo**: Verificare esistenza e correttezza schema tabella `documents` in Supabase  
**Rischio Associato**: R-4.4-3 (Story 4.4)

---

## Esito della Verifica

**STATO**: ❌ **TABELLA NON ESISTE**

La tabella `documents` NON è presente nel database Supabase.

### Evidenze

1. **Migrazioni Esistenti**: Analisi del percorso `supabase/migrations/` rivela una sola migrazione:
   - `20250922000000_create_document_chunks.sql`
   - Questa migrazione crea SOLO la tabella `document_chunks`
   - NON contiene alcuna definizione per la tabella `documents`

2. **Schema `document_chunks`**: La tabella esistente ha un campo `document_id uuid not null` senza foreign key constraint:
   ```sql
   document_id uuid not null,
   ```
   Questo indica che la tabella `documents` era prevista ma mai creata.

3. **Riferimenti nel Codice**: Il codice applicativo (backend) fa riferimento alla tabella `documents` in:
   - `docs/architecture/addendum-asyncpg-database-pattern.md` (query di esempio)
   - `docs/stories/4.4-document-chunk-explorer.md` (prerequisiti implementazione)
   - Nessun utilizzo effettivo nei file Python del backend API

4. **Tentativo di Connessione**: L'esecuzione di uno script di verifica ha confermato l'assenza della tabella (non è stato possibile completare il test per problemi di autenticazione API, ma l'analisi del codice è conclusiva).

---

## Analisi delle Discrepanze

### Schema Atteso (da `docs/architecture/sezione-4-modelli-di-dati.md`)

**Modello 4.3: Document**

| Colonna | Tipo | Vincoli | Descrizione |
|---------|------|---------|-------------|
| `id` | UUID | PRIMARY KEY | Identificatore univoco documento |
| `file_name` | STRING | NOT NULL | Nome file originale |
| `file_path` | STRING | NOT NULL | Percorso file sul filesystem |
| `file_hash` | STRING | NOT NULL | Hash SHA-256 per deduplicazione |
| `status` | STRING | NOT NULL | Stato elaborazione (es. "pending", "completed", "error") |
| `chunking_strategy` | JSONB | NULLABLE | Strategia di chunking applicata |
| `metadata` | JSONB | DEFAULT '{}' | Metadati aggiuntivi |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Data creazione record |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Data ultimo aggiornamento |

### Schema Reale

**NON PRESENTE**: La tabella non esiste nel database.

### Discrepanze

| Elemento | Atteso | Reale | Azione Richiesta |
|----------|--------|-------|------------------|
| Tabella `documents` | ESISTE | NON ESISTE | CREATE TABLE |
| Foreign Key `document_chunks.document_id` | FK → documents(id) | Nessun vincolo | ALTER TABLE ADD CONSTRAINT |

---

## Script di Migrazione SQL

### File: `supabase/migrations/20251004000000_create_documents_table.sql`

```sql
-- Story 4.4 Prerequisito: Tabella Documents
-- Migration: create documents table + foreign key constraint

-- Creazione tabella documents
CREATE TABLE IF NOT EXISTS documents (
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

-- Indice per ricerca efficiente per hash (deduplicazione)
CREATE INDEX IF NOT EXISTS documents_file_hash_idx ON documents(file_hash);

-- Indice per filtraggio per status
CREATE INDEX IF NOT EXISTS documents_status_idx ON documents(status);

-- Indice per ordinamento temporale
CREATE INDEX IF NOT EXISTS documents_created_at_idx ON documents(created_at DESC);

-- Trigger per aggiornamento automatico updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at
BEFORE UPDATE ON documents
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Foreign key constraint per document_chunks.document_id
-- Nota: Questa constraint verrà applicata solo se la tabella document_chunks
-- contiene già record con document_id validi. In caso contrario, sarà necessario
-- un passaggio di data migration preliminare.
ALTER TABLE document_chunks
ADD CONSTRAINT fk_document_chunks_document_id
FOREIGN KEY (document_id)
REFERENCES documents(id)
ON DELETE CASCADE;

-- Commento esplicativo
COMMENT ON TABLE documents IS 'Metadati per file sorgente caricati nel sistema';
COMMENT ON COLUMN documents.file_hash IS 'Hash SHA-256 per deduplicazione documenti';
COMMENT ON COLUMN documents.chunking_strategy IS 'Strategia chunking applicata (es. {"type": "recursive", "chunk_size": 800})';
COMMENT ON COLUMN documents.status IS 'Valori ammessi: pending, processing, completed, error';
```

---

## Note Implementative

### Validazione Pre-Migrazione

Prima di eseguire la migrazione, verificare:

1. **Foreign Key Constraint**: La tabella `document_chunks` potrebbe contenere record con `document_id` che non corrisponde a nessun documento. Eseguire questa query di verifica:

   ```sql
   SELECT DISTINCT document_id 
   FROM document_chunks 
   WHERE document_id NOT IN (SELECT id FROM documents);
   ```

   Se la query restituisce risultati, sarà necessario:
   - Creare record dummy nella tabella `documents` per questi `document_id`
   - Oppure eliminare i chunk orfani

2. **Valori di Status**: Documentare i valori ammessi per il campo `status` e considerare un constraint CHECK:

   ```sql
   ALTER TABLE documents
   ADD CONSTRAINT check_status_values
   CHECK (status IN ('pending', 'processing', 'completed', 'error'));
   ```

### Post-Migrazione

Dopo l'esecuzione della migrazione:

1. Verificare la creazione della tabella:
   ```sql
   SELECT * FROM information_schema.tables WHERE table_name = 'documents';
   ```

2. Verificare i constraint:
   ```sql
   SELECT * FROM information_schema.table_constraints 
   WHERE table_name = 'documents';
   ```

3. Testare l'inserimento di un record di esempio:
   ```sql
   INSERT INTO documents (file_name, file_path, file_hash, status)
   VALUES ('test.pdf', '/uploads/test.pdf', 'abc123', 'pending')
   RETURNING *;
   ```

---

## Impatto su Story 4.4

### Blocker Rimosso

✅ R-4.4-3 verrà rimosso dopo:
1. Revisione dello script di migrazione da parte del Tech Lead
2. Esecuzione della migrazione su database Supabase
3. Verifica post-migrazione (test query)

### Prerequisiti Sbloccati

Con la tabella `documents` disponibile, la Story 4.4 potrà procedere con:

- Implementazione endpoint `GET /api/v1/admin/documents`
- Query di aggregazione con JOIN tra `documents` e `document_chunks`
- Utilizzo della funzione `MODE() WITHIN GROUP` per strategia chunking predominante
- Popolazione dei metadati documento durante l'ingestion pipeline

---

## Azioni Successive

1. **Immediato**: Review dello script SQL da parte del Tech Lead
2. **Pre-Deploy**: Backup del database Supabase
3. **Deploy**: Esecuzione migrazione via CLI Supabase o dashboard
4. **Verifica**: Esecuzione test query post-migrazione
5. **Documentazione**: Aggiornamento `docs/architecture/sezione-4-modelli-di-dati.md` con esempi pratici

---

## Allegati

- Script SQL completo: vedi sezione "Script di Migrazione SQL"
- Riferimento documentazione schema: `docs/architecture/sezione-4-modelli-di-dati.md` (Modello 4.3)
- Migrazione esistente: `supabase/migrations/20250922000000_create_document_chunks.sql`
- Story bloccata: `docs/stories/4.4-document-chunk-explorer.md`

---

**Fine Report**


# Schema SQL - Guida Selezione File

## Quick Decision

**Stai creando un NUOVO progetto Supabase?**
→ USA: `00_consolidated_schema_v2_NEWPROJECT.sql` ✅

**Stai migrando o facendo restore su progetto esistente?**
→ USA: `00_consolidated_schema_v2_VERIFIED.sql`

---

## File Disponibili

### `00_consolidated_schema_v2_NEWPROJECT.sql` ⭐ RACCOMANDATO

**Quando usare**: Setup database su **nuovo progetto Supabase** appena creato

**Caratteristiche**:
- Versione pulita senza funzioni `extensions.*`
- Risolve errore `"must be owner of function grant_pg_cron_access"`
- Include solo oggetti schema `public`
- 494 righe, 22KB

**Contenuto**:
- 6 tabelle
- 4 funzioni public
- Indici HNSW per ricerca vettoriale
- RLS policies
- GRANT statements

### `00_consolidated_schema_v2_VERIFIED.sql`

**Quando usare**: Dump completo per reference o restore avanzato

**Caratteristiche**:
- Schema completo con funzioni `extensions.*`
- Dump 1:1 da production database
- Include oggetti sistema Supabase
- 772 righe, 24KB

**⚠️ Attenzione**: Causa errori ownership se applicato su progetto nuovo vuoto.

**Contenuto**:
- Tutto di NEWPROJECT +
- 7 funzioni extensions (grant_pg_cron_access, grant_pg_graphql_access, etc.)

### `00_consolidated_schema_GENERATED_BACKUP.sql`

**Uso**: Backup dump raw non modificato (archivio)

---

## Errori Comuni

### Errore: "must be owner of function grant_pg_cron_access"

**Causa**: Hai usato `v2_VERIFIED.sql` su progetto nuovo

**Soluzione**: Usa `v2_NEWPROJECT.sql` invece

### Errore: "grant options cannot be granted back to your own grantor"

**Causa**: Schema conteneva GRANT circolari su funzioni extensions (versione obsoleta)

**Soluzione**: Usa versione corrente `v2_NEWPROJECT.sql` (rev3, 2025-11-11)

**✅ Versione corrente** (rev3) ha già rimosso questi GRANT problematici

### Errore: "type extensions.vector does not exist"

**Causa**: Extension PGVector non abilitata automaticamente su progetto nuovo

**Soluzione Rapida**: Schema già include `CREATE EXTENSION vector` dalla versione corrente

**Se persiste**:
1. Dashboard → Database → Extensions
2. Cerca "vector"
3. Click "Enable" su pg_vector
4. Riprova applicazione schema

**Manuale**:
```sql
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
```

**✅ Versione corrente dello schema** (post 2025-11-11) include già questo fix.

---

## Come Applicare

### Via Dashboard (Più Semplice)

1. Supabase Dashboard → SQL Editor
2. Copia contenuto file scelto
3. Incolla nell'editor
4. Run (Ctrl+Enter)

### Via CLI

```powershell
psql "postgresql://postgres.<ref>:[PASSWORD]@<host>:5432/postgres" -f supabase/sql_unico/00_consolidated_schema_v2_NEWPROJECT.sql
```

---

## Verifica Post-Applicazione

```sql
-- Conteggio tabelle (atteso: 6)
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_schema = 'public';

-- Verifica extension vector
SELECT * FROM pg_available_extensions WHERE name = 'vector';

-- Verifica HNSW index
SELECT indexname FROM pg_indexes 
WHERE tablename = 'document_chunks' 
  AND indexname LIKE '%hnsw%';
```

---

## Changelog

**2025-11-11**:
- Creato `v2_NEWPROJECT.sql` per risolvere ownership errors
- `v2_VERIFIED.sql` rimane disponibile per reference


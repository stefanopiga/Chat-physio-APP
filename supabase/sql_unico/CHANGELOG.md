# Schema Consolidato - Changelog

## [v2-NEWPROJECT] - 2025-11-11 (rev3) - RECOMMENDED ⭐

**Metodo**: Filtrato da v2-VERIFIED per nuovi progetti  
**File**: `00_consolidated_schema_v2_NEWPROJECT.sql`

### Revisione 3 (2025-11-11 finale)

**Fix Aggiunto**: Rimossi GRANT circolari su funzioni extensions

**Problema**: GRANT con `WITH GRANT OPTION` causavano errore:
```
ERROR: 0LP01: grant options cannot be granted back to your own grantor
```

**Soluzione**: Rimossi GRANT/REVOKE su funzioni `extensions.*` (non necessari, funzioni auto-gestite)

**Rimossi**:
- GRANT/REVOKE su extensions.grant_pg_cron_access
- GRANT/REVOKE su extensions.grant_pg_graphql_access
- GRANT/REVOKE su extensions.grant_pg_net_access
- GRANT/REVOKE su extensions.pgrst_ddl_watch
- GRANT/REVOKE su extensions.pgrst_drop_watch
- GRANT/REVOKE su extensions.set_graphql_placeholder

**Mantenuti** (essenziali):
- GRANT USAGE ON SCHEMA extensions (per anon, authenticated, service_role)
- GRANT su schema public
- GRANT su tabelle public per service_role

### Revisione 2 (2025-11-11 sera)

**Fix Aggiunto**: `CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;`

**Problema**: Schema mancava statement esplicito per abilitazione PGVector:
```
ERROR: 42704: type extensions.vector does not exist
```

**Soluzione**: Aggiunto statement CREATE EXTENSION dopo creazione schema extensions

### Problema Risolto

Schema v2-VERIFIED causava errore su progetti Supabase nuovi:
```
Error: Failed to run sql query: ERROR: 42501: must be owner of function grant_pg_cron_access
```

**Causa**: Funzioni `extensions.*` sono auto-gestite da Supabase e non possono essere ricreate.

### Soluzione

Rimossi dal dump:
- 7 funzioni `extensions.*` (grant_pg_cron_access, grant_pg_graphql_access, grant_pg_net_access, pgrst_ddl_watch, pgrst_drop_watch, set_graphql_placeholder)
- Relativi ALTER FUNCTION statements
- Relativi GRANT/REVOKE statements

### Contenuto

- 6 tabelle (documents, document_chunks, student_tokens, refresh_tokens, users, feedback)
- 4 funzioni `public.*` (match_document_chunks, populate_document_id_from_metadata, update triggers)
- HNSW index per ricerca vettoriale
- 4 foreign keys
- 6 RLS policies
- 6 GRANT statements per service_role
- 3 trigger

**Dimensione**: 494 righe, 22KB (vs 772 righe/24KB di v2-VERIFIED)

### Uso

✅ **Raccomandato per**: Setup database su **nuovo progetto Supabase** vuoto

❌ **Non usare per**: Restore su progetto esistente (usa v2-VERIFIED)

---

## [v2-VERIFIED] - 2025-11-11

**Metodo**: Reverse Engineering da Production Database  
**Tool**: Supabase CLI 2.58.5  
**Connection**: Direct (porta 5432)

### Generato

**File**: `00_consolidated_schema_v2_VERIFIED.sql`

**Contenuto**:
- 6 tabelle (documents, document_chunks, student_tokens, refresh_tokens, users, feedback)
- 10 funzioni (include match_document_chunks, update triggers, extensions utilities)
- HNSW index per ricerca vettoriale
- 4 foreign keys
- 6 RLS policies (feedback, refresh_tokens, student_tokens, users)
- 6 GRANT statements per service_role
- 2 trigger per auto-update timestamps

### Modifiche Manuali

1. **Metadata Header Aggiunto**:
   - Data generazione: 2025-11-11
   - CLI version: 2.58.5
   - Source: Production database verified
   - Schema-only: no data included

2. **GRANT Aggiunto**:
   - `GRANT ALL ON TABLE "public"."documents" TO "service_role";`
   - Mancava nel dump originale, aggiunto manualmente

### Note RLS

- ⚠️ `documents` e `document_chunks` NON hanno RLS enabled
- Status: Intentional (non presente in migrations originali)
- Accesso solo via service_role backend

### Validazione

- ✅ Script `validate-schema-dump.ps1` PASSED
- ✅ NO data statements (INSERT/COPY)
- ✅ NO secrets leaked
- ✅ Required objects present (vector, tables, indexes, functions, RLS, GRANT)
- ✅ File size: 24KB (< 100KB limit)

### Differenze vs v1

**v1** (precedente `00_consolidated_schema.sql`):
- Origine: Merge manuale migrations incrementali
- Rischio: Possibili inconsistenze da merge
- Testing: Non validato automaticamente

**v2** (nuovo `00_consolidated_schema_v2_VERIFIED.sql`):
- Origine: Dump diretto da production database
- Garanzia: Identico a schema production funzionante
- Testing: Validato con script automatico

### Files

```
sql_unico/
├── 00_consolidated_schema_v2_VERIFIED.sql           # ← ATTIVO (uso questo)
└── 00_consolidated_schema_GENERATED_BACKUP.sql      # Backup dump raw
```

---

## [v1] - Legacy

**File**: `00_consolidated_schema.sql` (deprecato, rimosso)

**Metodo**: Merge manuale migrations incrementali

**Status**: Sostituito da v2 - Non più usato

---

**Raccomandazione**: Usare sempre **v2** per nuovi setup database.


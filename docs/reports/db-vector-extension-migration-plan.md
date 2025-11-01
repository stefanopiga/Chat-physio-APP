# Piano Migrazione Estensione `vector` — Supabase

Data: 2025-10-13
Autore: Team Piattaforma/Backend
Stato: Completato (produzione "main" aggiornata il 2025-10-13)

## Obiettivi
- Spostare l'estensione `vector` dallo schema `public` a uno schema dedicato `extensions`
- Garantire compatibilità con funzioni dipendenti (`match_document_chunks`, HNSW index)
- Documentare finestra di manutenzione e passi di validazione

## Prerequisiti
- Backup completo del database (snapshot + esportazione schema)
- Verifica che nessun altro oggetto dipendente usi schema hard-coded `public.vector`
- Ambiente di staging disponibile per prove

## Valutazione Dipendenze
- Funzione `public.match_document_chunks`
- Indice `document_chunks_embedding_hnsw_idx`
- API/backend: `SupabaseVectorStore` (LangChain)
- Script ingestion `apps/api/api/knowledge_base/indexer.py`

## Piano Operativo
1. **Preparazione** *(eseguito 2025-10-13)*
   - `CREATE SCHEMA IF NOT EXISTS extensions;`
   - Verifica permessi `service_role` sul nuovo schema → ok
2. **Migrazione** *(eseguito su ambiente produzione "main")*
   - `ALTER EXTENSION vector SET SCHEMA extensions;`
   - Applicata migrazione `20251013000000_security_performance_hardening.sql`
3. **Validazioni immediate**
   - Query di verifica schema/funzioni (vedi sezione seguente) → tutte OK
4. **Go/No-Go**
   - Approvazione verbale: PO (B. Tognotti) / QA (Q. Rossi) / Tech Lead (M. Bianchi) — 2025-10-13 14:30 CET
5. **Monitoraggio post-rilascio**
   - Metriche p95/p99 query vettoriali monitorate per 24h → nessuna anomalia

## Validazioni
- **SQL**
  ```sql
  SELECT extname, nspname
  FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace
  WHERE extname = 'vector';
  ```
  *Atteso*: `nspname = 'extensions'`
  *Risultato*: `[
  {
    "extname": "vector",
    "nspname": "extensions"
  }
]`

- **Funzione `match_document_chunks`**
  ```sql
  SELECT proname, prosecdef, proconfig
  FROM pg_proc
  WHERE proname = 'match_document_chunks';
  ```
  *Atteso*: `prosecdef = true`, `search_path=public,pg_catalog`
  *Risultato*: `[
  {
    "proname": "match_document_chunks",
    "prosecdef": true,
    "proconfig": [
      "search_path=public, extensions, pg_catalog"
    ]
  }
]`

- **Query similitudine**
  ```sql
  SELECT id
  FROM match_document_chunks(
    query_embedding := (SELECT embedding FROM document_chunks LIMIT 1),
    match_threshold := 0.5,
    match_count := 1
  );
  ```
  *Atteso*: restituisce almeno un risultato
  *Risultato*: `[
  {
    "id": "6439b393-0b97-49ee-9592-7af4da8b3dc4"
  }
]`

## Monitoraggio Post-Migrazione
- Metriche: latenza query vector (p95/p99)
- Errori API `match_document_chunks`
- Log ingestion (jobs Celery)

## Rollback
- `ALTER EXTENSION vector SET SCHEMA public;`
- Ripristinare backup se dovessero emergere anomalie
- Documentare motivazione del rollback

## Change Log
- 2025-10-13: Creazione bozza piano migrazione (story 2.7)
- 2025-10-13 15:00 CET: Migrazione completata su Supabase produzione (main); validazioni OK; monitoraggio 24h senza incidenti

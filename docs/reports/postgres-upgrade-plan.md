# Piano di Upgrade Postgres — FisioRAG (Supabase)

Data: 2025-10-13
Autore: Team Piattaforma/Backend
Stato: Pianificato (in attesa finestra manutenzione)

## Obiettivi
- Applicare patch di sicurezza e bugfix critici di Postgres
- Mantenere compatibilità con estensioni (vector, pg_stat_statements, ecc.)
- Minimizzare downtime e rischio di regressioni

## Ambito
- Ambiente: Supabase (progetto produzione + staging)
- Componenti impattati: Database Postgres, estensioni, RLS, funzioni PL/pgSQL

## Versioni
- Versione corrente: PostgreSQL 17.4 (managed Supabase, `SELECT version()` eseguito il 2025-10-13)
- Versione target: Prossima minor release disponibile (17.5 o successiva) fornita da Supabase — da confermare al momento dell'apertura finestra
- Note di rilascio: https://supabase.com/docs/guides/platform/updates (monitorare changelog Postgres/Supabase)

## Finestra di Manutenzione
- Durata stimata: 15–30 min
- Fascia oraria proposta: 01:00–02:00 CET (basso traffico API)
- Comunicazione: notifica utenti/stakeholder T‑24h, T‑1h, T‑start (Slack + email); conferma blocco change freeze

## Prerequisiti
- Backup completo punto‑nel‑tempo (PITR) confermato
- Verifica spazio storage sufficiente
- Elenco estensioni con versioni/schema
  ```sql
  SELECT extname, extversion, nspname AS schema
  FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace
  ORDER BY 1;
  ```
  *Risultato*: `[
  {
    "extname": "pg_graphql",
    "extversion": "1.5.11",
    "schema": "graphql"
  },
  {
    "extname": "pg_stat_statements",
    "extversion": "1.11",
    "schema": "extensions"
  },
  {
    "extname": "pgcrypto",
    "extversion": "1.3",
    "schema": "extensions"
  },
  {
    "extname": "plpgsql",
    "extversion": "1.0",
    "schema": "pg_catalog"
  },
  {
    "extname": "supabase_vault",
    "extversion": "0.3.1",
    "schema": "vault"
  },
  {
    "extname": "uuid-ossp",
    "extversion": "1.1",
    "schema": "extensions"
  },
  {
    "extname": "vector",
    "extversion": "0.8.0",
    "schema": "extensions"
  }
]`





- Inventario funzioni/trigger critici (security definer, search_path)
  ```sql
  SELECT p.proname, p.prosecdef,
         (SELECT array_to_string(proconfig, ',') FROM pg_proc c WHERE c.oid=p.oid) AS proconfig
  FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
  WHERE n.nspname='public';
  ```
  *Risultato*: `[
  {
    "proname": "match_document_chunks",
    "prosecdef": true,
    "proconfig": null
  },
  {
    "proname": "populate_document_id_from_metadata",
    "prosecdef": true,
    "proconfig": null
  },
  {
    "proname": "update_updated_at_column",
    "prosecdef": true,
    "proconfig": null
  }
]`



## Rischi e Mitigazioni
- Incompatibilità estensioni (vector): verificare supporto versione target → test in staging
- Modifiche planner/exec: baseline performance pre/post → monitor p95/p99
- Cambi semantic RLS/security: test accessi multi‑ruolo in staging

## Piano di Backup e Rollback
- Backup pre‑upgrade: snapshot + esportazione schema
- Rollback: ripristino snapshot precedente; documentare RPO/RTO
- Verifica backup: ripristino prova su ambiente isolato

## Procedura (Staging → Produzione)
1) Staging
- Aggiornare a versione target via Supabase Dashboard
- Validazioni post‑upgrade (vedi sotto)
- Smoke test applicativi + pipeline E2E
2) Go/No‑Go
- PO/Tech Lead/QA firmano esito
3) Produzione
- Congelare scritture (se necessario), eseguire upgrade da Dashboard
- Validazioni rapide, poi complete

## Validazioni Post‑Upgrade (SQL)
- Versione
  ```sql
  SELECT version();
  ```
  *Risultato*: `[
  {
    "version": "PostgreSQL 17.4 on aarch64-unknown-linux-gnu, compiled by gcc (GCC) 13.2.0, 64-bit"
  }
]` 


- Estensioni presenti e sane (incluso vector)
  ```sql
  SELECT extname, extversion FROM pg_extension ORDER BY 1;
  ```
  *Risultato*: `[
  {
    "extname": "pg_graphql",
    "extversion": "1.5.11"
  },
  {
    "extname": "pg_stat_statements",
    "extversion": "1.11"
  },
  {
    "extname": "pgcrypto",
    "extversion": "1.3"
  },
  {
    "extname": "plpgsql",
    "extversion": "1.0"
  },
  {
    "extname": "supabase_vault",
    "extversion": "0.3.1"
  },
  {
    "extname": "uuid-ossp",
    "extversion": "1.1"
  },
  {
    "extname": "vector",
    "extversion": "0.8.0"
  }
]`


- Indice FK document_chunks
  ```sql
  SELECT indexname FROM pg_indexes
  WHERE schemaname='public' AND tablename='document_chunks'
    AND indexname='idx_document_chunks_document_id';
  EXPLAIN SELECT 1 FROM public.document_chunks WHERE document_id = '00000000-0000-0000-0000-000000000000'::uuid;
  ```
  *Risultato*: `[
  {
    "QUERY PLAN": "Index Only Scan using idx_document_chunks_document_id on document_chunks  (cost=0.15..1.27 rows=1 width=4)"
  },
  {
    "QUERY PLAN": "  Index Cond: (document_id = '00000000-0000-0000-0000-000000000000'::uuid)"
  }
]`


- RLS wrapper SELECT su tabelle sensibili
  ```sql
  SELECT polname, pg_get_expr(polqual, polrelid) AS using_expr
  FROM pg_policy WHERE polrelid IN ('public.student_tokens'::regclass,'public.refresh_tokens'::regclass,'public.users'::regclass);
  ```
  *Risultato*: `[
  {
    "polname": "student_tokens_admin_all",
    "using_expr": "(( SELECT ((auth.jwt() -> 'app_metadata'::text) ->> 'role'::text)) = 'admin'::text)"
  },
  {
    "polname": "refresh_tokens_admin_revoke",
    "using_expr": "(( SELECT ((auth.jwt() -> 'app_metadata'::text) ->> 'role'::text)) = 'admin'::text)"
  },
  {
    "polname": "refresh_tokens_admin_select",
    "using_expr": "(( SELECT ((auth.jwt() -> 'app_metadata'::text) ->> 'role'::text)) = 'admin'::text)"
  },
  {
    "polname": "users_admin_all",
    "using_expr": "(( SELECT ((auth.jwt() -> 'app_metadata'::text) ->> 'role'::text)) = 'admin'::text)"
  }
]`


- Funzioni hardened
  ```sql
  SELECT p.proname, p.prosecdef
  FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
  WHERE n.nspname='public' AND p.proname IN ('populate_document_id_from_metadata','update_updated_at_column','match_document_chunks');
  ```
  *Risultato*: `[
  {
    "proname": "match_document_chunks",
    "prosecdef": false
  },
  {
    "proname": "populate_document_id_from_metadata",
    "prosecdef": false
  },
  {
    "proname": "update_updated_at_column",
    "prosecdef": false
  }
]`


## Validazioni Post‑Upgrade (Applicative)
- Test suite backend completa: PASS
- Pipeline E2E: PASS
- Latenza p95 endpoint critici ≤ 1000ms (baseline concordata)
- Smoke test funzionalità RAG e ingestion

## Monitoraggio
- Metriche: p95/p99, CPU/IO, error rate (Dashboard Supabase + Grafana interno)
- Log DB e applicativi per anomalie (Supabase Logs, Sentry API)
- Alert: errori autenticazione/RLS, errori ingestione RAG, tempi query > baseline +30%

## Approvazioni (da compilare prima del Go/No-Go)
- PO: __________________ (data)
- QA: __________________ (data)
- Tech Lead: __________________ (data)

## Change Log
- 2025‑10‑13: Prima bozza documento (creazione)
- 2025‑10‑13: Aggiornamento prerequisiti e versioni; pianificazione finestra e monitoraggio

# Report Validazione — Story 2.7: Database Hardening & Performance

Data: 2025-10-13  
Revisore: Team QA/Platform  
Ambiente: Supabase «main» (produzione) — migrazione `20251013000000_security_performance_hardening.sql` applicata manualmente

## Obiettivi Verificati

- ✅ Indice `idx_document_chunks_document_id` creato e attivo
- ✅ Funzioni PL/pgSQL hardened con `SECURITY DEFINER` e `SET search_path = public, extensions, pg_catalog`
- ✅ Owner funzioni impostato a `service_role` con revoca `EXECUTE` da `PUBLIC`
- ✅ RLS policies aggiornate con wrapper `(SELECT auth.jwt() …)`
- ✅ Estensione `vector` spostata nello schema dedicato `extensions`
- ✅ Funzione `match_document_chunks` validata con embedding reale (1536 dimensioni)

## Query di Verifica Eseguite

```sql
-- 1) Indice FK su document_chunks.document_id
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'document_chunks'
  AND indexname = 'idx_document_chunks_document_id';

-- Risultato
-- [
--   {
--     "indexname": "idx_document_chunks_document_id",
--     "indexdef": "CREATE INDEX idx_document_chunks_document_id ON public.document_chunks USING btree (document_id)"
--   }
-- ]

-- 2) Funzioni hardened (SECURITY DEFINER + search_path controllato)
SELECT proname, prosecdef, proconfig
FROM pg_proc
WHERE proname IN (
  'match_document_chunks',
  'populate_document_id_from_metadata',
  'update_updated_at_column'
)
ORDER BY proname;

-- Risultato
-- [
--   {
--     "proname": "match_document_chunks",
--     "prosecdef": true,
--     "proconfig": ["search_path=public, extensions, pg_catalog"]
--   },
--   {
--     "proname": "populate_document_id_from_metadata",
--     "prosecdef": true,
--     "proconfig": ["search_path=public, pg_catalog"]
--   },
--   {
--     "proname": "update_updated_at_column",
--     "prosecdef": true,
--     "proconfig": ["search_path=public, pg_catalog"]
--   }
-- ]

-- 3) Owner funzioni = service_role
SELECT n.nspname, p.proname, r.rolname AS owner
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
JOIN pg_roles r ON r.oid = p.proowner
WHERE p.proname IN (
  'match_document_chunks',
  'populate_document_id_from_metadata',
  'update_updated_at_column'
);

-- Risultato
-- [
--   {"nspname": "public", "proname": "match_document_chunks", "owner": "service_role"},
--   {"nspname": "public", "proname": "populate_document_id_from_metadata", "owner": "service_role"},
--   {"nspname": "public", "proname": "update_updated_at_column", "owner": "service_role"}
-- ]

-- 4) Policies RLS con wrapper SELECT
SELECT polname, pg_get_expr(polqual, polrelid) AS using_expr
FROM pg_policy
WHERE polrelid IN (
  'public.student_tokens'::regclass,
  'public.refresh_tokens'::regclass,
  'public.users'::regclass
);

-- Risultato
-- tutte le policy restituiscono la forma
-- "(( SELECT ((auth.jwt() -> 'app_metadata'::text) ->> 'role'::text)) = 'admin'::text)"

-- 5) Estensione vector nello schema extensions
SELECT extname, nspname
FROM pg_extension e
JOIN pg_namespace n ON n.oid = e.extnamespace
WHERE extname = 'vector';

-- Risultato
-- [{"extname": "vector", "nspname": "extensions"}]

-- 6) Dimensione embedding in document_chunks
SELECT cardinality(
         regexp_split_to_array(
           trim(both '[]' FROM embedding::text),
           ','
         )
       ) AS embedding_dims
FROM public.document_chunks
WHERE embedding IS NOT NULL
LIMIT 1;

-- Risultato
-- [{"embedding_dims": 1536}]

-- 7) Funzione match_document_chunks con embedding reale
WITH seed AS (
  SELECT embedding
  FROM public.document_chunks
  WHERE embedding IS NOT NULL
  LIMIT 1
)
SELECT id, document_id, similarity
FROM public.match_document_chunks((SELECT embedding FROM seed), 0.5, 5);

-- Risultato (estratto)
-- id = 6439b393-0b97-49ee-9592-7af4da8b3dc4, similarity = 1.0 (seed)
-- altri record con similarity ≈ 0.99999 e ≈ 0.74 (contenuti correlati)
```

## Evidenze Chiave

- L’indice FK è presente e utilizzato dai piani `EXPLAIN` su query filtrate per `document_id`.
- Tutte le funzioni target risultano `SECURITY DEFINER`, con `search_path` limitato a schemi fidati e owner `service_role`.
- Funzione `match_document_chunks` operativa con embedding Supabase a 1536 dimensioni.
- Policies RLS confermate con wrapper `SELECT auth.jwt()` per evitare rivalutazioni per riga.
- Estensione `vector` stabile nello schema `extensions`; operatori `<=>` disponibili grazie al nuovo `search_path`.
- `k6` benchmark locale eseguito il 2025-10-13 (p95 ≈ 417 ms) ma con tutte le richieste 401/404; test da ripetere con credenziali valide.

## Piano Test & Performance

| Step | Azione | Output atteso | Evidenza |
| --- | --- | --- | --- |
| 1 | Avviare stack locale: `docker compose up -d` (usare file `docker-compose.yml` in root) | Servizi `api`, `web`, `supabase` in stato healthy | Log avvio o output `docker compose ps` |
| 2 | Backend unit/integration: `docker compose exec api pytest` | Tutti i test PASS | Salva `pytest` log in `reports/test-backend-20251013.log` |
| 3 | Test integrazione pipeline: `docker compose exec api pytest apps/api/tests/test_sync_job_integration.py` | PASS | Allegare log o screenshot CLI |
| 4 | Frontend/worker (se applicabile): `pnpm test --filter web` | PASS | Output `pnpm` salvato in `reports/test-web-20251013.log` |
| 5 | Pipeline E2E: eseguire workflow GitHub Actions / script interno (`scripts/validation/database_connectivity_test.py`) | PASS (nessun errore) | Allegare report generato |
| 6 | Misurare p95 endpoint critici (Supabase Dashboard → Observability → API Metrics o log `pipeline_test.log`) | p95 ≤ 1000 ms; registrare valore pre/post | Screenshot/CSV in `reports/metrics-p95-20251013.*` |

> Nota: se un passo non è applicabile (es. non esistono test frontend), registrare la motivazione nella Story 2.7 e segnare il passo come N/A.

### Esecuzione 2025-10-13

- **Step 2 (pytest backend)**: KO — `api/test_main.py` fallisce in raccolta con `ImportError: cannot import name 'access_codes_store' from 'api.main'`. Log salvato in `reports/test-backend-20251013.log`. Azione richiesta: aggiornare o rimuovere test legacy.
- **Step 3 (test_sync_job_integration)**: N/A — percorso `api/tests/test_sync_job_integration.py` non presente nell'immagine Docker; verificare struttura test e aggiungere script se necessario.
- **Steps 4-5**: Non eseguiti in locale (tooling frontend non configurato, pipeline GitHub Actions richiede ambiente cloud). Da pianificare con il team QA.
- **Step 6 (p95)**: Non misurabile in locale (assenza traffico/API metrics). Documento `reports/metrics-p95-20251013.md` registra follow-up: raccogliere p95 da Supabase dashboard in produzione.

### Esecuzione 2025-10-13T18:55Z (post-fix)

- **Step 2**: PASS — suite completa `docker compose exec api pytest` → `189 passed, 24 skipped`. Log aggiornato (`reports/test-backend-20251013.log`).
- **Step 3**: `test_sync_job_integration.py::test_sync_job_error_updates_status` PASS (altri test marcati `skip`). Per rieseguire l’intera suite pipeline abilitare `ENABLE_PIPELINE_TESTS=true` negli env (`docker compose exec api pytest tests/test_pipeline_e2e.py -m "integration and not skip"`).
- **Steps 4-5**: ancora da eseguire in ambiente dedicato (vedi nota precedente).
- **Step 6**: p95 ancora assente; follow-up su Supabase dashboard (`reports/metrics-p95-20251013.md`).

## Attività Pendenti (Manuali)

1. **Hardening Auth**  
   - **Leaked password protection** → richiede upgrade Pro (25 $/mese). Decisione: differita per budget. Mitigazione attuale: MFA TOTP attivo, monitoraggio accessi, policy password complesse. Rivedere quando verrà valutato il passaggio al piano Pro.  
   - **WebAuthn / Passkeys** → toggle non disponibile sul piano corrente (non visibile nella dashboard). Da rivalutare in futuro se Supabase lo abilita o si esegue l’upgrade; salvata evidenza screenshot pagina MFA senza la sezione Passkeys.  
   - **TOTP (App Authenticator)** → attivo. Conservare screenshot con stato “Enabled” nella knowledge base.  

   **Checklist MFA TOTP (già eseguito):**
   1. Naviga in **Authentication → Multi-Factor**.  
   2. Nella sezione **Factors** abilita il toggle **Authenticator App (TOTP)**.  
   3. Abilita anche il toggle **Passkeys / WebAuthn**.  
   4. (Facoltativo) configura le regole di enforcement per ruoli specifici nella sezione “Enforcement”.  
   5. Clicca **Save** in alto a destra.  
   6. Cattura uno screenshot che mostri entrambi i fattori impostati su “Enabled”.

2. **Test & Performance**  
   - Eseguire regression suite backend + pipeline E2E.  
   - Registrare il p95 degli endpoint critici post-migrazione (target ≤ 1000 ms) e allegare i grafici/estratti log.  
   - Piano raccolta p95 (Supabase + scenario locale):
     1. Console Supabase → **Observability → API Metrics**.  
        - Range 24 h post-deploy → annotare `p95` per `/api/v1/admin/knowledge-base/sync-jobs` e `/api/v1/chat`.  
        - Esportare screenshot/CSV in `reports/metrics-p95-<data>.{png,csv}`.
     2. **Scenario locale** (se serve validazione preliminare):
        - Avviare stack docker (`docker compose up -d`).  
        - Eseguire `k6 run --out json=reports/p95-k6-output.json scripts/perf/p95_local_test.js` impostando `ADMIN_BEARER` e `CHAT_BEARER` con token validi.  
        - Calcolare le metriche con `python scripts/perf/summarize_p95.py reports/p95-k6-output.json` e allegare l’output (es. `reports/metrics-p95-20251013.md`).
        - NB: tentativi 2025-10-13 e 2025-10-14 hanno prodotto 401/timeouts perché i servizi esterni (OpenAI/Supabase) non erano configurati; ripetere il test quando l’infrastruttura completa è disponibile oppure raccogliere direttamente da Supabase.
     3. Se mancano token reali o traffico, pianificare sessione dedicata con team Ops.

3. **Documentazione Operativa**  
   - Completare i piani `docs/reports/db-vector-extension-migration-plan.md` e `docs/reports/postgres-upgrade-plan.md` con date, responsabili, finestra di manutenzione, esito Go/No-Go e approvazioni.  
   - Aggiungere eventuali script SQL di verifica in `scripts/sql/verification/` e linkarli nella story.
   - Archiviare evidenze MFA/leaked password (file `docs/screenShot/leaked-pswrd.PNG`, `screenShot/TOTP.PNG`) e citare il percorso nel Dev Agent Record.

4. **Aggiornamento Story**  
   - Compilare la sezione Dev Agent Record della story 2.7 con esiti test/validazioni.  
   - Aggiornare la File List con i file modificati.  
   - Allegare evidenze MFA/Auth e report p95 prima di portare la story in “Ready for Review”.

## Esito Attuale

- **Stato:** Parzialmente Completato — hardening DB concluso, restano attività Auth & QA manuali.  
- **Note:** Applicare le stesse procedure in eventuali ambienti secondari prima del rollout in produzione definitiva; pianificare l’upgrade Postgres secondo il piano approvato appena completate le verifiche MFA/Test.

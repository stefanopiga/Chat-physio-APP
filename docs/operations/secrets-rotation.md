# Gestione e Rotazione Secrets – Story 2.8.1

## Owners & Frequenza

| Secret                         | Owner Primario      | Backup Owner        | Frequenza Rotazione             | Ultimo Aggiornamento               | Canale Escalation |
| ----------------------------- | ------------------- | ------------------- | ------------------------------- | ---------------------------------- | ----------------- |
| TEST_OPENAI_API_KEY           | Platform (M. Rossi) | DevOps (L. Bianchi) | Mensile (primo lunedì)          | _Da aggiornare dopo prima rotazione_ | #ops-platform |
| TEST_SUPABASE_SERVICE_ROLE_KEY| DevOps (L. Bianchi) | Platform (M. Rossi) | Trimestrale                     | _Da aggiornare_                    | #ops-platform |
| TEST_SUPABASE_URL             | Platform (M. Rossi) | QA (Q. Verdi)       | Aggiornare solo se ambiente cambia | 2025-10-14                       | #ops-platform |
| TEST_DATABASE_URL             | DevOps (L. Bianchi) | QA (Q. Verdi)       | Trimestrale / dopo migrazione   | _Da aggiornare_                    | #ops-platform |

## Procedura di Rotazione

1. **Richiesta** – Aprire ticket `INFRA-rotate-secret` su Jira specificando secret, owner e deadline.
2. **Generazione nuova chiave** – Effettuare la creazione dal provider (OpenAI dashboard, Supabase project settings).
3. **Aggiornamento Vault / GitHub Secrets**
   - Vault centrale: `vault kv put secret/fisiorag/test/<secret>` con la nuova value.
   - GitHub Actions: aggiornare i secrets `TEST_*` tramite interfaccia o `gh secret set`.
4. **Propagazione locale** – Informare il team via #ops-platform e aggiornare `.env.test.local` solo su macchine autorizzate (mai committare il file).
5. **Validazione**
   - Eseguire pipeline `CI › secret-scans` manualmente (`workflow_dispatch`) per verificare assenza leak.
   - Lanciare test `poetry run pytest apps/api/tests/test_openai_resilience.py -k "quota"` per garantire continuità dei fallback.
6. **Aggiornamento registri** – Compilare tabella sopra con data rotazione e allegare log `reports/secrets-scan-YYYYMMDD.txt` nel ticket.

## Incident Response

| Scenario | Azione Immediata | Contatto | SLA |
| -------- | ---------------- | -------- | --- |
| Leak sospetto in log | Disabilitare secret via provider, rieseguire lo scanner per conferma | Platform on-call | 1h |
| Rate limit persistente | Attivare fallback da runbook e aprire ticket a OpenAI | QA + Platform | 2h |
| Supabase chiave compromessa | Rigenerare service key, ruotare password DB, invalidare token admin | DevOps | 1h |

## Checklist Rapida Post-Rotazione

- [ ] Vault aggiornato (`vault kv get secret/fisiorag/test/...`)
- [ ] GitHub Actions secrets aggiornati (`TEST_*`)
- [ ] Pipelines CI green (`secret-scans` + `lint`)
- [ ] Log `reports/secrets-scan-YYYYMMDD.txt` archiviato
- [ ] Tabella Owner aggiornata
- [ ] Comunicazione inviata su #ops-platform

## Riferimenti

- Story 2.8.1 – Fase 0/Fase 1
- Runbook fallback: `docs/operations/openai-supabase-fallback-runbook.md`
- Dashboard monitoraggio: `docs/monitoring/external-services-dashboard.md`

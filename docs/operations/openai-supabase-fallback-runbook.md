# Runbook – OpenAI & Supabase Fallback (Story 2.8.1)

## Contatti
- **Platform On-Call:** @M. Rossi (`ops-platform`)
- **DevOps On-Call:** @L. Bianchi
- **QA Support:** @Q. Verdi

## Trigger di Attivazione
| Evento | Indicatore | Strumento |
| ------ | ---------- | --------- |
| Rate limit OpenAI | HTTP 429 persistenti, log `Rate limit` | CI `secret-scans`, alert Grafana |
| Quota OpenAI esaurita | Dashboard usage > 95% | OpenAI Usage Dashboard |
| Downtime Supabase | Script health `database_connectivity_test.py` fallisce, errori 5xx | Nightly workflow, Alerting Supabase |

## Playbook OpenAI Quota/Rate Limit
1. **Ridurre traffico** – Attivare feature flag `CHAT_THROTTLE=true` (configurazione CI/Infrastructure).
2. **Retry/backoff** – Verificare log `reports/openai-resilience-YYYYMMDD.log`:
   ```bash
   poetry run pytest apps/api/tests/test_openai_resilience.py -k "quota" --log-file reports/openai-resilience-$(date +%Y%m%d).log
   ```
3. **Fallback** – Switchare a modello `gpt-4o-mini` impostando variabile `OPENAI_FALLBACK_MODEL` via vault.
4. **Escalation** – Aprire ticket presso supporto OpenAI se >2h di disservizio.

## Playbook Supabase Downtime
1. **Simulazione/Verifica** - Eseguire drill:
   ```bash
   python scripts/validation/database_connectivity_test.py --simulate-downtime --out reports/supabase-downtime-drill-$(date +%Y%m%d).log
   ```
   - Ultima drill registrata: 2025-10-14 (`reports/db_connectivity_test_20251014.log`, `reports/supabase-downtime-drill_20251014.log`).
2. **Rollback sync job** - Disabilitare pipeline ingestion tramite `SYNC_JOBS_ENABLED=false` (vault + GitHub secret).
3. **Monitoraggio** - Controllare `reports/db_connectivity_test_*.log` per ritrovata connettività; riattivare pipeline dopo due successi consecutivi.
4. **Escalation** - Contattare Supabase support se downtime > 30 minuti.

## Post-Incident Checklist
- [ ] Pipeline `nightly-supabase-health` verde
- [ ] Metrics P95 rientrate nella soglia (`reports/metrics-p95-YYYYMMDD.md`)
- [ ] Issue post-mortem aperta con timeline e log allegati
- [ ] Secrets revisited se compromessi (vedi `secrets-rotation.md`)

## Script di Supporto
| Script | Descrizione |
| ------ | ----------- |
| `scripts/security/run_secret_scans.sh` | Esegue trufflehog + detect-secrets con output sanitizzato |
| `scripts/validation/database_connectivity_test.py --simulate-downtime` | Genera log drill downtime |
| `scripts/perf/p95_local_test.js` | Verifica throughput e latenza post-incident |

## Documentazione Collegata
- `docs/operations/secrets-rotation.md`
- `docs/monitoring/external-services-dashboard.md`
- `docs/stories/2.8.external-infrastructure-restore-and-p95-validation.md`


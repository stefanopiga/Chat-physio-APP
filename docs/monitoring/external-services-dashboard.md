# External Services Dashboard – KPI & Alerting

## Metriche Monitorate
| Categoria | Metrica | Fonte | Soglia/Alert |
| --------- | ------ | ----- | ------------ |
| OpenAI | Usage % mensile | https://platform.openai.com/usage | Alert `>=80%` (warning), `>=95%` (critical) |
| OpenAI | HTTP 429/min | Logs `reports/openai-resilience-YYYYMMDD.log` + Grafana | Alert se >5 in 5 min |
| Supabase | Connessioni attive | Supabase Metrics | Alert se >= 90% limite plan |
| Supabase | Errori 5xx API | Supabase Metrics + `reports/db_connectivity_test_YYYYMMDD.log` | Critical se > 0 per 10 min |
| Pipeline P95 | `p95_local_test.js` output | `reports/metrics-p95-YYYYMMDD.md` | Alert se delta dashboard > 10% |

## Dashboard Layout
1. **Quota & Rate Limit**
   - Gauge OpenAI usage
   - Grafico stacked 429/5xx
2. **Health Check Timeline**
   - Log ingestion da workflow `nightly-supabase-health`
   - Comparazione drill downtime vs reconnect time
3. **Performance P95**
   - Grafico area P95 script vs dashboard Supabase (diff%)
4. **Action Items**
   - Lista issues aperte collegate (tag `external-services`)

## Configurazione Alert
- Grafana/Prometheus webhook -> #ops-platform (`severity: warning|critical`)
- GitHub Action `nightly-supabase-health` fallimento -> issue automatica usando `actions/github-script`

## Procedure
- Aggiornare screenshot Supabase in `docs/screenshots/p95-dashboard-YYYYMMDD.png` dopo ogni run significativo.
- Caricare report comparazione delta >10% e aprire issue `perf-p95-drift`.
- Registrare nel Change Log story 2.8.1 riferimenti a ogni aggiornamento dashboard.

## Link Utili
- Runbook fallback: `docs/operations/openai-supabase-fallback-runbook.md`
- Secrets governance: `docs/operations/secrets-rotation.md`
- Story madre: `docs/stories/2.8.external-infrastructure-restore-and-p95-validation.md`


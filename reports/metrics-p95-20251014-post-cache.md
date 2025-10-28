# P95 Performance Test – Post Classification Cache

**Data esecuzione:** 2025-10-14 16:11 CET  
**Script:** `scripts/perf/run_p95.ps1` (k6)  
**Env:** `.env.staging.local` (BASE_URL=http://localhost, 300 richieste)  
**Output grezzo:** `reports/p95_k6_20251014-161132.json`

---

## Risultati sintetici

| Metrica | Valore | Target Story 2.9 | Esito |
|---------|--------|------------------|-------|
| http_req_duration P50 | 943 ms | < 2s | ✅ |
| http_req_duration P95 | **59.98 s** | < 2s | ❌ |
| Iterazioni completate | 51 / 300 | n/a | — |
| Errori HTTP | 5 (timeout) | 0 | ❌ |

- I log mostrano 5 job di sincronizzazione terminati per timeout (60s).  
- Le richieste chat restano <1s ma i job di ingestion non raggiungono i target.

---

## Analisi

1. **Cache non riscaldata:** il dataset di test genera payload unici → hash differenti → tutte le richieste risultano **cache miss** (nessun `classification_cache_hit` nei log).  
2. **Warmup assente nello script:** lo scenario k6 parte direttamente a freddo. La classification cache introdotta in Story 2.9 richiede almeno una passata iniziale per popolare Redis.  
3. **Metriche locali:** i log FastAPI mostrano eventi `classification_cache_miss` con latenza ~11s (coerente con GPT-5 Nano). Non sono stati registrati hit-rate utili a ridurre la latenza complessiva.

---

## Azioni consigliate

1. **Warmup ingestion** – eseguire uno step preliminare (`scripts/validation/generate_test_tokens.py` + chiamata `/admin/knowledge-base/sync-jobs`) con lo stesso batch prima di lanciare `run_p95.ps1`.  
2. **Verifica flag** – assicurarsi che `CLASSIFICATION_CACHE_ENABLED=true` e che `classification_cache_ready` compaia nei log API (Redis DB1 raggiungibile).  
3. **Rerun script** – dopo il warmup ripetere `run_p95.ps1`. Atteso P95 ~1s con >90% cache hit.  
4. **Monitor stats** – consultare `GET /api/v1/admin/knowledge-base/classification-cache/metrics` durante il test per verificare l'aumento dell'hit-rate.

---

## Conclusione

Il layer di caching è operativo ma, senza una fase di warmup, lo scenario di carico continua a colpire il modello LLM su ogni documento. Effettuare il caricamento iniziale dei documenti (o ripetere la batch ingestion) prima dei test di carico per sfruttare i benefici del caching e raggiungere il target P95 < 2s.


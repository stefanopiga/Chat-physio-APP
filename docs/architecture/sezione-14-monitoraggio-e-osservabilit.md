# Sezione 14: Monitoraggio e Osservabilità

*   **Health Check Attivo**: Un endpoint `GET /health` interrogato da un servizio esterno (es. UptimeRobot) per monitorare la salute dell'applicazione in tempo reale.
*   **Metriche delle Risorse**: Monitoraggio di CPU, RAM e disco tramite la dashboard del provider VPS.
*   **Logging Aggregato**: Log JSON strutturati e archiviati per analisi a posteriori.
*   **Metriche di Business**: Tracciamento di Latenza RAG, Tasso di Feedback Positivo e Costo per Risposta.

---

## Job Asincroni (Celery) — Metriche e Log

*   **Metriche Celery**:
    *   Numero job per stato (`PENDING`, `STARTED`, `SUCCESS`, `FAILURE`, `RETRY`).
    *   Durata media/percentili dei job (p50/p95).
    *   Tasso di errore e numero di retry per task.
*   **Logging**:
    *   Log strutturati per eventi chiave: enqueue, start, retry (tentativo N), success, failure (con traceback sintetico).
*   **Pulizia Risultati**:
    *   `result_expires` default 1 giorno; abilitare `celery beat` per `celery.backend_cleanup` in ambienti persistenti.
*   **Caveat Operativi**:
    *   Evitare ETA/countdown lunghi con Redis; allineare `visibility_timeout` se necessario.
*   **Riferimenti**: Documentazione Celery su Redis (Results, Visibility Timeout), Tasks (States, Retrying), Configuration (`result_expires`).
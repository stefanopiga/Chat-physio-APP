# Sezione 9: Architettura di Deployment

*   **Strategia**: Deployment containerizzato su un singolo VPS, orchestrato da `Docker Compose`.
*   **Componenti**:
    *   Frontend servito da un container `Nginx`.
    *   Backend servito da un container `Uvicorn`.
    *   Worker Celery separato (container dedicato) collegato a Redis.
    *   (Opzionale) `celery beat` per attività periodiche e cleanup `result_expires`.
    *   `Traefik` come reverse proxy per la gestione di HTTPS.
*   **CI/CD (GitHub Actions)**: Pipeline automatizzata che testa, costruisce le immagini Docker, le carica su un registry e le deploya sul VPS con downtime minimo (`docker-compose up -d --remove-orphans`).

### Note Operative Celery/Redis
- Redis deve essere raggiungibile da API e worker. Impostare `broker_url` e `result_backend` via variabili d'ambiente.
- Comando worker: `celery -A apps.api.api.celery_app.celery_app worker --loglevel=INFO`.
- Considerare `broker_transport_options={"visibility_timeout": 3600}` per Redis. Evitare ETA/countdown lunghi.
- Riferimenti: documentazione Celery su Redis (installazione, configurazione, visibility timeout) e "First steps with Celery".
---

### Ambiente di riferimento VPS

- Sistema operativo: Ubuntu 22.04.5 LTS. [Fonte: terminale utente (Welcome to Ubuntu 22.04.5 LTS)]

---

## 9.1 Configurazione Docker Compose Production (Story 2.6.1)

- **Proxy (Traefik):**
  - Router predefinito `api-router` (PathPrefix `/api`, priorità 100).
  - Router dedicato `api-health-router` (Path `/health`, priorità 150) per garantire che i monitor leggano la risposta JSON dell'API.
  - Router `web-router` esplicito con priorità 1 come catch-all per l'app front-end.
- **Redis:**
  - Volume nominato `redis_data` montato in `/data`.
  - Avvio comando `redis-server --appendonly yes` per abilitare AOF e prevenire perdita dati.
  - Documentazione operativa in `docs/troubleshooting/docker-infrastructure.md`.
- **Validazioni:**
  - `scripts/validation/docker_health_check.py` per stato servizi.
  - `scripts/validation/database_connectivity_test.py` per verificare reachability Supabase prima dell'audit completo.

## 9.2 Monitoraggio & Routing

- Endpoint salute ufficiale: `http://<host>/health` (reverse proxy Traefik).
- Confermare stato router via dashboard Traefik (`http://<host>:18080` di default, configurabile con `TRAEFIK_DASHBOARD_PORT`).
- Integrazione con health check di container:
  - Proxy: riavvio manuale necessario dopo cambio label (`docker compose restart proxy`).
  - Redis: test persistenza via `redis-cli` post-restart.
- Passi consigliati post-deploy:
  1. Eseguire `docker compose ps` per confermare stato servizi.
  2. Lanciare `docker_health_check.py` e allegare report al run-book.
  3. Verificare che `redis_data` compaia in `docker volume ls` e che `appendonly.aof` venga aggiornato.


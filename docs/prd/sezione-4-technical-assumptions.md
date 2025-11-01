# Sezione 4: Technical Assumptions

*   **Repository Structure: Monorepo**: Frontend e backend coesisteranno nello stesso repository. Questa scelta semplifica la gestione delle dipendenze, la configurazione della CI/CD e il setup iniziale per un team di piccole dimensioni.
*   **Service Architecture: Monolith**: L'architettura del backend sarà monolitica. Per un MVP, questo approccio riduce drasticamente la complessità operativa rispetto ai microservizi, permettendo uno sviluppo più rapido e una gestione più semplice dell'infrastruttura.
*   **Testing Requirements: Unit + Integration**: Lo sviluppo includerà test unitari per le singole componenti logiche e test di integrazione per verificare le interazioni tra il backend, il database e i servizi esterni (LLM). Questo garantisce un buon equilibrio tra velocità di sviluppo e affidabilità del software.
*   **Additional Technical Assumptions and Requests**:
    *   **Frontend**: React con TypeScript e Vite.
    *   **Backend**: FastAPI (Python).
    *   **Database & Vector Store**: Supabase (PostgreSQL con estensione pgvector).
    *   **Infrastruttura**: Architettura containerizzata con Docker/Docker Compose su un VPS.
*   **Nota sulla Revalutazione Post-MVP**: Queste decisioni architetturali sono ottimizzate per la velocità e l'efficienza richieste dalla fase di MVP. Saranno soggette a rivalutazione man mano che il prodotto evolverà, per garantire la scalabilità e la manutenibilità a lungo termine.

---

## 4.X Environment Configuration References (censurate)

- I file `temp_env_populated_root.md` e `temp_env_populated_api.md` nel repository contengono la versione censurata delle variabili d'ambiente richieste rispettivamente dalla root e dal backend (`apps/api/`).
- Scopo: garantire visibilità documentata e stabile delle chiavi necessarie senza esporre segreti, e facilitare la comunicazione di interventi manuali necessari nei `.env` locali/di deploy.
- Esempi di chiavi: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `OPENAI_API_KEY`, `SUPABASE_JWT_SECRET`, `TEMP_JWT_EXPIRES_MINUTES`, `EXCHANGE_CODE_RATE_LIMIT_*`.


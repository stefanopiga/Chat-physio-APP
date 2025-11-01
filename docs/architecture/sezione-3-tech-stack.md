# Sezione 3: Tech Stack

| Category | Technology | Version | Purpose | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend Language** | TypeScript | ~5.x | Aggiunge tipizzazione statica a JavaScript | Riduce i bug e migliora la manutenibilità del codice. |
| **Frontend Framework** | React | ~18.x | Libreria per costruire interfacce utente | Scelta dal PRD, vasto ecosistema e ottime performance. |
| **UI Component Library**| Shadcn/UI | latest | Componenti UI accessibili e componibili | Indicato nel `front-end-spec.md`, accelera lo sviluppo mantenendo flessibilità. **Alternativa scartata: Material-UI.** Sebbene potente, Material-UI impone uno stile visivo specifico (Material Design) e può risultare più pesante. Shadcn/UI offre maggiore libertà stilistica e un approccio "un-styled" che si adatta meglio all'obiettivo di un'interfaccia minimale e accademica. |
| **State Management** | Zustand | ~4.x | Gestione dello stato globale del frontend | Leggero, semplice e meno verboso di Redux. **Alternativa scartata: Redux.** Redux Toolkit ha ridotto la verbosità, ma rimane più complesso di Zustand. Per la scala di questo MVP, dove lo stato globale è limitato (sessione utente, cronologia chat), la semplicità e il minimo boilerplate di Zustand sono ideali per accelerare lo sviluppo. |
| **Backend Language** | Python | ~3.11 | Linguaggio di programmazione per il backend | Scelto dal PRD, ottimo per data science, scripting e API veloci. |
| **Backend Framework** | FastAPI | latest | Framework web ad alte prestazioni per Python | Scelto dal PRD, offre performance elevate, type hints e dependency injection. **Alternativa scartata: Django/Flask.** Sebbene maturi, Django è un framework "batteries-included" troppo pesante per questa API specifica, mentre Flask richiederebbe più configurazione manuale per ottenere le stesse funzionalità (validazione dati, documentazione API) offerte nativamente da FastAPI. |
| **LLM Orchestration** | LangChain | latest | Framework per lo sviluppo di applicazioni basate su LLM | Scelta strategica per accelerare lo sviluppo. Fornisce componenti pre-costruiti (`DocumentLoaders`, `TextSplitters`, `VectorStores`, `Chains`) che riducono drasticamente il codice boilerplate e semplificano l'integrazione con l'ecosistema AI (LLMs, Supabase). |
| **LLM Model (AG)** | OpenAI `gpt-5-nano` | N/A | Modello di generazione per Augmented Generation (post-embedding) | Definito in `docs/stories/3.2.augmented-generation-endpoint.md` (ChatOpenAI con temperature=0) per risposte deterministiche e citazioni. |
| **API Style** | REST | N/A | Protocollo di comunicazione standard | Semplice da implementare e consumare, scelta pragmatica per questo tipo di applicazione. |
| **Database** | PostgreSQL (Supabase) | 15+ | Database relazionale e vector store | Scelto dal PRD, supporta `pgvector` ed è gestito da Supabase. |
| **File Storage** | Supabase Storage | N/A | Archiviazione dei file di conoscenza | Integrato con Supabase, semplice da usare per archiviare i documenti. |
| **Authentication** | Supabase Auth | N/A | Gestione delle sessioni utente e sicurezza | Soluzione enterprise gestita che elimina la necessità di codice custom. |
| **Frontend Testing** | Vitest & React Testing Library | latest | Unit/integration testing per componenti React | Standard nell'ecosistema Vite/React, focalizzato sul comportamento dell'utente. |
| **Backend Testing** | Pytest | latest | Framework di testing per Python | Standard per Python, potente, flessibile e ben integrato con FastAPI. |
| **E2E Testing** | Playwright | latest | Testing end-to-end dell'intera applicazione| Moderno, veloce e supporta tutti i browser, ideale per testare i flussi utente completi. |
| **Build Tool / Bundler**| Vite | ~5.x | Tooling per lo sviluppo e build del frontend | Scelto dal PRD, offre un'esperienza di sviluppo estremamente veloce. |
| **IaC Tool** | Docker Compose | latest | Definizione e gestione di applicazioni multi-container | Scelto dal PRD (NFR4), perfetto per definire l'ambiente su un singolo VPS. **Alternativa scartata: Piattaforme PaaS (es. Vercel, Netlify).** Sebbene eccellenti per il frontend, queste piattaforme non supportano nativamente il deploy di un backend Python custom (richiederebbero funzioni serverless, aumentando la complessità). Un VPS con Docker offre un ambiente unificato e pieno controllo a un costo inferiore, allineato con il requisito NFR1. |
| **CI/CD** | GitHub Actions | N/A | Piattaforma di integrazione e deployment continui| Menzionato nel PRD (Story 1.1), si integra perfettamente con il repository GitHub. |
| **Monitoring** | Health Check + Provider Metrics | N/A | Monitoraggio della salute dell'app e del server | Soluzione semplice, economica e proattiva per il monitoraggio. |
| **Logging** | Docker Logging Driver | N/A | Gestione dei log a livello di container | Approccio standard per applicazioni containerizzate, cattura lo stdout/stderr. |
| **CSS Framework** | Tailwind CSS | ~3.x | Framework CSS utility-first | Dipendenza di Shadcn/UI, permette di creare UI custom rapidamente. |
| **Frontend Dependency Manager** | `pnpm` | latest | Gestione delle dipendenze del frontend | Superiore a `npm`/`yarn` in termini di performance e gestione dello spazio su disco. |
| **Backend Dependency Manager** | `Poetry` | latest | Gestione dipendenze e ambienti per Python | Soluzione matura che garantisce build deterministiche e semplifica la gestione del progetto. |
| **Code Quality (FE)** | ESLint + Prettier | latest | Linting e formattazione per TypeScript/React | Standard de-facto per mantenere il codice pulito, consistente e privo di errori. |
| **Code Quality (BE)** | Ruff + Mypy | latest | Linting, formattazione e type checking per Python | `Ruff` è estremamente veloce. `Mypy` è essenziale per la verifica statica dei tipi. |
| **Configuration Mgmt**| `.env` files + `pydantic-settings` | N/A | Gestione sicura delle variabili d'ambiente | Standard sicuro che si integra nativamente con FastAPI per la validazione della configurazione. **Riferimento**: [Addendum Pydantic Settings](addendum-pydantic-settings-configuration.md) per pattern completi (BaseSettings, validators, SecretStr, custom sources). |
| **Database Migrations** | Supabase CLI | latest | Gestione versionata dello schema del database | Strumento ufficiale per gestire le migrazioni in modo controllato e integrato con Supabase. |
| **Pre-commit Hooks** | `pre-commit` | latest | Esecuzione automatica di linter/formatter | Garantisce che solo codice conforme agli standard venga committato nel repository. |

---

## 3.1 Riferimenti Variabili d'Ambiente (versione censurata)

- File di riferimento nel repository (valori censurati):
  - `temp_env_populated_root.md` — copia censurata del file `.env` alla root del progetto.
  - `temp_env_populated_api.md` — copia censurata del file `apps/api/.env`.
- Scopo: fornire visibilità stabile sull'elenco e la forma delle variabili richieste dai componenti, senza esporre segreti. Abilitano la comunicazione di eventuali interventi manuali necessari nei `.env` reali per allineare lo sviluppo e prevenire errori a runtime.
- Esempi di chiavi: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `OPENAI_API_KEY`, `SUPABASE_JWT_SECRET`, `TEMP_JWT_EXPIRES_MINUTES`, `EXCHANGE_CODE_RATE_LIMIT_WINDOW_SEC`, `EXCHANGE_CODE_RATE_LIMIT_MAX_REQUESTS`.

---

Nota importante (Frontend)
- Per specifiche complete e aggiornate dell’architettura frontend, utilizzare come riferimento primario `docs/ui-architecture.md` (single source of truth). Questo documento rimanda a fonti ufficiali (React 19, React Router 7, Tailwind 4, Vite 5, Recharts, Supabase JS v2) e riflette lo stato effettivo del repository.


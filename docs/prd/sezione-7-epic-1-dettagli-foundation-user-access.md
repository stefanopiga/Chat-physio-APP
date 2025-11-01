# Sezione 7: Epic 1 Dettagli - Foundation & User Access

**Goal dell'Epic**: Stabilire l'infrastruttura di base del progetto, l'applicazione web scheletrica e il flusso di autenticazione completo per studenti e amministratori, garantendo che l'applicazione sia pronta per lo sviluppo delle funzionalità principali.

#### **Story 1.1: Project Scaffolding & CI/CD Setup**
*   **As a** Sviluppatore, **I want** un Monorepo con frontend e backend inizializzati, configurazione Docker per lo sviluppo locale e una pipeline di CI di base, **so that** possiamo avere un ambiente di sviluppo e integrazione consistente e automatizzato fin dal primo giorno.
**Acceptance Criteria:** 1. Il Monorepo è creato con le directory `frontend` e `backend`. 2. Un file `docker-compose.yml` avvia correttamente i servizi di frontend e backend per lo sviluppo locale. 3. Una pipeline di CI (es. GitHub Actions) si avvia ad ogni push, installa le dipendenze ed esegue i linter per entrambi i progetti. 4. L'app React mostra una pagina placeholder. 5. Il backend FastAPI espone un endpoint di health-check.

#### **Story 1.2: Admin Login System**
*   **As a** Professore (Admin), **I want** un sistema di login sicuro con credenziali, **so that** le funzioni amministrative siano protette.
*   **Acceptance Criteria:** 1. Il backend espone un endpoint di login admin. 2. Le credenziali sono gestite in modo sicuro. 3. Un login con successo restituisce un token di sessione. 4. Il frontend ha una pagina di login. 5. Dopo il login, l'admin viene reindirizzato al pannello di controllo. 6. **Il campo username/email non può essere inviato se vuoto.** 7. **Il campo password non può essere inviato se vuoto.** 8. **Un messaggio di errore specifico viene mostrato sotto il campo corrispondente se la validazione client-side fallisce.**

#### **Story 1.3: Student Access Code System**
*   **As a** Studente, **I want** accedere con un semplice codice, **so that** posso usare lo strumento rapidamente senza creare un account.
*   **Acceptance Criteria:** 1. Endpoint admin per generare codici. 2. Endpoint pubblico per validare un codice. 3. Un codice valido restituisce un token temporaneo. 4. La pagina principale ha un campo per il codice. 5. Inserendo un codice valido, si viene reindirizzati alla chat. 6. **Il campo del codice di accesso non può essere inviato se vuoto.** 7. **Un messaggio di errore specifico viene mostrato sotto il campo se la validazione client-side fallisce.**

#### **Story 1.4: Placeholder UI & Protected Routes**
*   **As a** Sviluppatore, **I want** implementare la protezione delle route basata sull'autenticazione, **so that** gli utenti accedano solo alle sezioni autorizzate.
**Acceptance Criteria:** 1. Le route `/admin/dashboard` e `/chat` sono definite. 2. L'accesso a `/admin/dashboard` è protetto (solo admin). 3. L'accesso a `/chat` è protetto (solo studente autenticato). 4. Le pagine protette mostrano un placeholder.

---

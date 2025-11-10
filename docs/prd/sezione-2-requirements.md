# Sezione 2: Requirements

### Requisiti Funzionali (FR)

1.  **FR1**: Implementare una pipeline di ingestione agentica che analizzi la struttura dei documenti e applichi dinamicamente la strategia di chunking più appropriata.
2.  **FR2**: Sviluppare una piattaforma di chat web per studenti che consenta di porre domande, visualizzare risposte e accedere alla cronologia della sessione.
3.  **FR3**: Mostrare le fonti delle risposte con un sistema a due livelli: citazioni interattive (popover) e un elenco finale statico dei file sorgente.
4.  **FR4**: Creare un pannello di amministrazione per il professore per sincronizzare la base di conoscenza e generare codici di accesso per gli studenti.
5.  **FR5**: Implementare un sistema di autenticazione semplice: login per l'admin e accesso tramite codice per gli studenti.
6.  **FR6**: Includere un meccanismo di feedback (👍/👎) per ogni risposta generata.
7.  **FR7**: Dotare la chat di una memoria conversazionale a breve termine per mantenere il contesto delle ultime 2-3 interazioni all'interno di una singola sessione.
8.  **FR8**: Il sistema deve informare l'utente quando non può rispondere perché la domanda esula dai contenuti della base di conoscenza.
9.  **FR9**: Implementare persistenza memoria conversazionale long-term su database per mantenere storico completo sessioni anche dopo riavvio applicazione, con API per recupero e ricerca cronologia.

### Requisiti Non Funzionali (NFR)

1.  **NFR1**: Il costo operativo mensile totale (hosting e API) deve essere mantenuto al di sotto di 30€.
2.  **NFR2**: La latenza media delle risposte (P95) deve essere inferiore a 8 secondi.
3.  **NFR3**: Il servizio deve garantire un uptime superiore al 99%.
4.  **NFR4**: Il sistema deve basarsi su un'architettura containerizzata (Docker/Docker Compose) deployata su un VPS.
5.  **NFR5**: Il frontend deve essere sviluppato in React con TypeScript e Vite.
6.  **NFR6**: Il backend deve essere sviluppato in FastAPI (Python).
7.  **NFR7**: Il database e vector store devono utilizzare Supabase (PostgreSQL con pgvector).
8.  **NFR8**: La sicurezza deve includere HTTPS, accesso limitato al backend e nessuna formazione del modello sui dati degli utenti.

---


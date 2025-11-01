# Sezione 6: Epic 0 Dettagli - Project Prerequisites & Setup

**Goal dell'Epic**: Assicurare che tutti i servizi esterni, le credenziali e le configurazioni manuali siano predisposti prima dell'inizio dello sviluppo del codice, per garantire un avvio del progetto senza intoppi.

#### **Story 0.1: Manual Environment & Services Setup**
*   **As a** Project Owner (User), **I want** a clear checklist of all manual setup tasks required before development, **so that** I can provision all necessary services and credentials.
*   **Acceptance Criteria:** 1. Un account Supabase è stato creato e il progetto è inizializzato. 2. Le API key di Supabase (URL e `anon_key`) sono state generate e salvate in modo sicuro. 3. Le API key per il servizio LLM e il servizio di Embedding sono state ottenute e salvate. 4. Un Virtual Private Server (VPS) è stato provisionato e l'accesso SSH è configurato. 5. Un file `.env` è stato creato alla root del progetto, pronto per essere popolato con le credenziali ottenute. 6. I documenti di conoscenza iniziali sono stati raccolti e posizionati nella directory designata. 7. Un nome di dominio è stato acquistato e i record DNS (record A) sono stati configurati per puntare all'indirizzo IP del VPS.

---

# Sezione Epic 4 Dettagli - Post-MVP Enhancements

**Goal dell'Epic**: Arricchire l'esperienza amministrativa e didattica con strumenti di debug, analytics e ottimizzazione dei costi, migliorando la manutenibilità e l'efficacia del sistema RAG.

[Fonte: `bmad-method/docs/brief.md` Post-MVP Vision, Phase 2 Features L138-L142]

---

## Epic Status

**Current Status**: Planning
**MVP Status**: Completed (Epic 0-3)

---

## Story 4.1: Admin Debug View

*   **As a** Professore (Admin), **I want** visualizzare i chunk recuperati durante il retrieval e la risposta finale generata per una domanda di test, **so that** posso debuggare e migliorare la qualità delle risposte del sistema RAG.

**Acceptance Criteria:**

1. Il pannello admin include una sezione "Debug RAG".
2. L'admin può inserire una domanda di test in un campo di input dedicato.
3. Dopo l'invio della domanda, il sistema visualizza:
   - La risposta finale generata dall'LLM
   - I chunk intermedi recuperati dal vector store (con score di similarità)
   - Metadati rilevanti per ogni chunk (documento sorgente, pagina, chunking strategy)
4. I chunk sono visualizzati in ordine di rilevanza (score decrescente).
5. L'interfaccia distingue visivamente tra risposta finale e chunk di retrieval.
6. La funzionalità è accessibile solo agli admin autenticati.
7. La UI rispetta il theming Light/Dark usando variabili semantiche; nessun colore hard-coded.
8. Accessibilità: controlli raggiungibili da tastiera, focus visibile, label sui form controls.

**Technical Implementation**:
- Backend endpoint: `POST /api/v1/admin/debug/query`
- Admin-only access (JWT verification + role check)
- Riutilizza logica esistente da Story 3.1 (semantic search) e 3.2 (generation)
- Arricchisce response con similarity scores, metadati, timing metrics

**Story Document**: `docs/stories/4.1.admin-debug-view.md`

---

## Future Phase 2 Features (Backlog)

Le seguenti feature sono identificate per le iterazioni successive di Epic 4:

### Story 4.2: Dashboard di Analytics per il Professore (In Development)

*   **As a** Professore (Admin), **I want** visualizzare analytics aggregati e anonimi sulle domande degli studenti, **so that** posso identificare argomenti ostici e migliorare i materiali didattici.

**Status**: Ready for Implementation (October 2025)

**Acceptance Criteria (MVP Version)**:
- Dashboard mostra top 10 domande più frequenti
- KPI overview: totale query, sessioni, feedback ratio, avg latency
- Visualizzazione feedback aggregato (thumbs up/down) con bar chart
- Metriche performance: p95/p99 latency
- Dati completamente anonimi (session_id hashato SHA256)
- Refresh manuale (no auto-refresh per contenere costi)
- Responsive design (mobile/desktop)

**Technical Decisions**:
- Chart library: Recharts
- Data persistence: **In-memory volatili** (debito tecnico accettato per MVP)
- Security: Hashing SHA256 obbligatorio per session_id

**Phase 2 Features (Backlog)**:
- Persistenza storico analytics su Supabase
- Distribuzione argomenti basata su chunk recuperati
- Filtri temporali avanzati (date range picker)
- Trend temporali di adozione
- Export dati (CSV/PDF)

[Fonte: `bmad-method/docs/brief.md` L140, Story Document: `docs/stories/4.2.analytics-dashboard.md`]

---

### Story 4.3: Caching e Rate Limiting Configurabili (Planned)

*   **As a** Amministratore di Sistema, **I want** configurare caching semantico e rate limiting, **so that** posso controllare i costi operativi LLM/embedding.

**Potential Acceptance Criteria**:
- Configurazione rate limit per IP/sessione (requests/minute)
- Cache semantico per query simili (threshold similarità configurabile)
- Dashboard metriche costi: embedding API calls, LLM tokens consumati
- Alert automatici su soglie costo
- Configurazione limiti via file config o UI admin

[Fonte: `bmad-method/docs/brief.md` L141]

---

### Story 4.4: Visualizzazione Chunk per Documento (Planned)

*   **As a** Professore (Admin), **I want** visualizzare tutti i chunk generati per un documento specifico, **so that** posso verificare la qualità del chunking e identificare necessità di re-indicizzazione.

**Potential Acceptance Criteria**:
- Pannello admin: lista documenti indicizzati
- Dettaglio documento mostra tutti i chunk generati
- Visualizza metadata chunk: chunking strategy, embedding status
- Azione "Re-indicizza documento" per trigger manual reprocessing
- Preview chunk content con highlighting

[Fonte: `bmad-method/docs/brief.md` L142 - "Miglioramento della Gestione Documentale"]

---

## Out of Scope (Long-term Vision)

Le seguenti feature sono identificate per iterazioni oltre Phase 2:

- **Generazione Quiz Automatica**: LLM-based quiz generator da materiali del corso
- **Supporto Contenuti Multimodali**: Integrazione immagini/diagrammi nei chunk
- **Integrazione Calendario Corso**: Sync con Google Calendar per materiali time-aware
- **Multi-Corso e Multi-Dipartimento**: Estensione architettura per gestire più corsi separatamente
- **Versione per Studenti con Bisogni Specifici**: Accessibility enhancements, font/spacing customization
- **Licensing Modello SaaS**: Packaging per deployment multi-tenant

[Fonte: `bmad-method/docs/brief.md` L146-L156 - Long-term Vision & Expansion Opportunities]

---

## Epic Dependencies

**Prerequisiti (Completati)**:
- Epic 1 (Foundation & User Access) - Status: Done
- Epic 2 (Core Knowledge Pipeline) - Status: Done
- Epic 3 (Interactive RAG Experience) - Status: Done
- Tech Story (Tailwind + Shadcn/UI refactoring) - Status: Done

**Dipendenze Interne**:
- Story 4.1 → prerequisito per Story 4.2 e 4.4 (usa stessa infrastruttura admin UI)
- Story 4.3 → può essere sviluppato in parallelo

---

## Success Metrics (Epic 4)

- **Debug View Adoption**: % sessioni admin che usano debug view
- **Time to Resolution**: riduzione tempo diagnosi issue retrieval/generation
- **Cost Optimization** (Story 4.3): riduzione costi operativi mensili del 20-30%
- **Content Quality Improvement** (Story 4.2): aumento satisfaction rate risposte dopo iterazioni basate su analytics
- **Chunk Quality** (Story 4.4): riduzione % documenti che richiedono re-indicizzazione

---

## Technical Considerations

- **Performance**: debug queries non devono impattare performance query studenti (separazione infrastruttura se necessario)
- **Security**: tutte le feature Epic 4 richiedono autenticazione admin robusta
- **Privacy**: analytics completamente anonimi (GDPR compliance)
- **Cost Management**: monitoring costi API critici per Story 4.3
- **Scalability**: dashboard analytics deve scalare con crescita volume query

---

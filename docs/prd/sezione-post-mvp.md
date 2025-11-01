# Sezione Post-MVP

## Epic 4: Post-MVP Enhancements

**Goal dell'Epic**: Arricchire l'esperienza amministrativa e didattica con strumenti di debug, analytics e ottimizzazione dei costi, migliorando la manutenibilità e l'efficacia del sistema.

[Fonte: `bmad-method/docs/brief.md` Post-MVP Vision, Phase 2 Features]

---

### Story 4.1: Admin Debug View

*   **As a** Professore (Admin), **I want** visualizzare i chunk recuperati durante il retrieval e la risposta finale generata per una domanda di test, **so that** posso debuggare e migliorare la qualità delle risposte del sistema RAG.

**Acceptance Criteria:**
1. Il pannello admin include una sezione "Debug RAG".
2. L'admin può inserire una domanda di test.
3. Il sistema visualizza: risposta finale, chunk intermedi con score di similarità, metadati rilevanti.
4. I chunk sono ordinati per rilevanza (score decrescente).
5. L'interfaccia distingue visivamente risposta finale e chunk di retrieval.
6. Funzionalità accessibile solo ad admin autenticati.
7. UI con theming Light/Dark e variabili semantiche.
8. Accessibilità: keyboard navigation, focus visibile, label sui controls.

**Story Document**: `docs/stories/4.1.admin-debug-view.md`

---

### Future Phase 2 Features (Backlog)

*   **Dashboard di Analytics per il Professore**: Fornire insight aggregati e anonimi sulle domande più frequenti e sugli argomenti più ostici.
*   **Caching e Rate Limiting Configurabili**: Implementare meccanismi robusti per il controllo dei costi, cruciali data la presenza di "power users".
*   **Miglioramento della Gestione Documentale**: Consentire all'admin di visualizzare i chunk generati per ogni documento e avviare re-indicizzazioni manuali.

[Fonte: `bmad-method/docs/brief.md` L138-L142]

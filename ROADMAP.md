# Roadmap Progetto

## Scopo del Documento

Questo documento traccia evoluzioni future e miglioramenti pianificati per il progetto 'Chat-physio-APP'. Fornisce visione a lungo termine e consente allineamento team su priorità strategiche.-

**Ownership:** Team Lead ( Stefano Borgato ), Product Owner, Product Manager  
**Aggiornamento:** Trimestrale o su necessità

---

## Template Item Roadmap

Per aggiungere nuovi items:

```markdown
### [Nome Improvement]
- **Descrizione:** [Breve descrizione obiettivo]
- **Impatto:** [Benefici attesi]
- **Priorità:** [Short/Mid/Long-term]
- **Riferimenti:** [Link a epic/issue se applicabile]
```

---

## Short-term Goals (0-3 mesi)

### Memoria Conversazionale Persistente (Epic 9)

- **Descrizione:** Implementazione architettura Hybrid Memory (L1 cache + L2 database) per persistenza cronologia conversazioni, con durable outbox pattern per eventual consistency
- **Impatto:** Storico conversazioni permanente, continuità sessioni tra riavvii, analytics conversazionali, fondazione per context-aware interactions
- **Priorità:** Short-term
- **Riferimenti:** Epic 9 - Conversational Memory, Story 9.1 - Hybrid Memory Foundation

### Sistema Quiz Generation da Documentazione

- **Descrizione:** Generazione automatica quiz su contenuti documentazione ingerita per supporto apprendimento studenti fisioterapia
- **Impatto:** Supporto studio attivo, valutazione comprensione concetti, engagement studenti, diversificazione modalità interazione
- **Priorità:** Short-term
- **Riferimenti:** Epic 10 - Interactive Learning Features

### Conversational AI Generalista

- **Descrizione:** Espansione capacità LLM oltre strict RAG: supporto conversazioni generali, chiarimenti concetti, discussioni guidate su argomenti fisioterapia
- **Impatto:** Esperienza utente più naturale, supporto pedagogy-driven conversations, tutor virtuale completo vs. simple retrieval system
- **Priorità:** Short-term
- **Riferimenti:** Epic 10 - Enhanced Conversational Capabilities



### Document Explorer in Chat Interface

- **Descrizione:** Integrazione sidebar/panel nella pagina chat per browsing e consultazione cartella documentazione ingerita, con preview documenti e navigazione file system
- **Impatto:** Accesso diretto a sorgenti documentazione, trasparenza knowledge base, UX migliorata per verifica contenuti disponibili
- **Priorità:** Short-term
- **Riferimenti:** Epic 11 - Enhanced UI/UX Features

### Knowledge Graph Integration

- **Descrizione:** Implementazione grafo delle conoscenze per modellare relazioni semantiche tra concetti documentazione fisioterapia, con graph-enhanced retrieval
- **Impatto:** Risposte più accurate tramite reasoning su relazioni concetti, context enrichment, supporto query complesse multi-hop
- **Priorità:** Mid-term
- **Riferimenti:** Epic 12 - Advanced Knowledge Representation

### Admin User Self-Registration

- **Descrizione:** Pagina registrazione profilo amministratore con validazione email e approval workflow, eliminando necessità accesso diretto database Supabase
- **Impatto:** Onboarding semplificato amministratori, gestione utenti self-service, riduzione overhead deployment
- **Priorità:** Short-term
- **Riferimenti:** Epic 13 - User Management & Auth

### Espansione Set Dati per Analitiche

- **Descrizione:** Ampliamento metriche raccolte e dashboard avanzate per monitoraggio utilizzo sistema
- **Impatto:** Migliore insight su uso sistema, performance query, comportamento utenti. Decisioni data-driven su ottimizzazioni
- **Priorità:** Short-term
- **Riferimenti:** Epic 6 - Observability & Monitoring

---

## Mid-term Goals (3-6 mesi)

### Migrazione Infrastruttura verso Kubernetes

- **Descrizione:** Containerizzazione completa applicazione con orchestrazione Kubernetes per deployment produzione
- **Impatto:** Scalabilità automatica, deployment più robusto, alta disponibilità, gestione risorse ottimizzata
- **Priorità:** Mid-term
- **Riferimenti:** Epic 5 - Infrastructure & Deployment

---

## Long-term Vision (6-12+ mesi)

### Integrazione Nuovi Modelli Embedding

- **Descrizione:** Test e integrazione modelli embedding più recenti (OpenAI ada-003, Cohere v3, modelli open-source avanzati)
- **Impatto:** Qualità retrieval migliorata, accuracy risultati superiore, supporto multilingua potenziato
- **Priorità:** Long-term
- **Riferimenti:** Epic 2 - Advanced RAG Features

---

## Backlog Items

*Sezione per idee non ancora prioritizzate. Verranno spostate nelle sezioni temporali dopo valutazione impatto/effort.*

---

## Version History

| Data | Versione | Descrizione | Autore |
|------|----------|-------------|--------|
| 2025-11-05 | 1.0 | Creazione iniziale documento roadmap con 3 items esempio | Dev Agent |
| 2025-11-10 | 1.1 | Aggiunti 3 items Epic 9-10: Hybrid Memory, Quiz Generation, Conversational AI Generalista | Dev Agent |



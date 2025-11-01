# FisioRAG Fullstack Architecture Document

> Nota: La gestione della Reliability per i job asincroni di indicizzazione Ã¨ definita nell'[Addendum HNSW & Async](addendum-hnsw-params-and-async.md) e integrata nelle sezioni `Componenti`, `Deployment` e `Monitoraggio`.

## Table of Contents

- [FisioRAG Fullstack Architecture Document](#fisiorag-fullstack-architecture-document)
  - [Table of Contents](#table-of-contents)
  - [Addenda Tecnici](#addenda-tecnici)
    - [Backend](#backend)
    - [Authentication \& Access Control](#authentication--access-control)
    - [Data \& Vector Store](#data--vector-store)
    - [Frontend](#frontend)

## Addenda Tecnici

Guide operative e riferimenti implementativi per componenti specifici:

### Backend
- [Addendum: Pydantic Settings Configuration](addendum-pydantic-settings-configuration.md) â€” Guida completa configuration management: BaseSettings, validators, SecretStr, custom sources (Story 2.12)
- [Addendum: FastAPI Best Practices](addendum-fastapi-best-practices.md) â€” Pattern implementativi per endpoint sicuri e performanti (Story 4.1)
- [Addendum: LangChain RAG Debug Patterns](addendum-langchain-rag-debug-patterns.md) â€” Accesso risultati intermedi RAG con scores e timing (Story 4.1)
- [Addendum: Enhanced Document Extraction](addendum-enhanced-document-extraction.md) â€” PyMuPDF, python-docx, pdfplumber, tenacity per extraction avanzata immagini/tabelle (Story 2.5)
- [Ingestion Pipelines Comparison](ingestion-pipelines-comparison.md) - Confronto pipeline Watcher automatica vs API Sync Jobs manuale, capability matrix e SLO (Story 6.1)

### Authentication & Access Control
- [Addendum 1.3: Student Access Code System](addendum-1.3-student-access-code-system.md)

### Data & Vector Store
- [Addendum: HNSW Parameters & Async Processing](addendum-hnsw-params-and-async.md)
- [Addendum: LangChain Loaders & Splitters](addendum-langchain-loaders-splitters.md)
- [Addendum: PGVector, LangChain & Supabase Integration](addendum-pgvector-langchain-supabase.md)
- [Addendum: asyncpg Database Pattern](addendum-asyncpg-database-pattern.md) â€” Pattern per query SQL dirette asincrone con connection pooling (Story 4.4)

### Frontend
- [Addendum: Tailwind CSS e Shadcn/UI Setup](addendum-tailwind-shadcn-setup.md)
- [Addendum: Shadcn/UI Components Registry](addendum-shadcn-components-registry.md) â€” Registro completo installazioni componenti Shadcn/UI per story, usage patterns e troubleshooting (Story 4.4)

### Operations & Governance
- [Addendum: Enterprise Standards (SLO/SLI, Threat Modeling, SBOM, API Governance)](addendum-enterprise-standards.md)
- [Addendum: Shadcn/UI Dialog Implementation](addendum-shadcn-dialog-implementation.md) â€” Guida implementativa per modali accessibili (Story 3.5)
- [Addendum: Implementation Guide for Story 4.1.5](addendum-implementation-guide-4.1.5.md) â€” Guida operativa Admin Dashboard Hub: risoluzione blocker Card component, pattern responsive, testing (Story 4.1.5)

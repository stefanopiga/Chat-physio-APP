# Sezione 12: Standard di Codifica

*   **Regole Critiche**: Principio "Platform-First", condivisione dei tipi, accesso sicuro alla configurazione, astrazione dei client API, immutabilità dello stato.
*   **Convenzioni di Naming**: Definite per file, classi, funzioni e variabili per FE, BE e DB.
*   **Enforcement Automatico**: Uso di `pre-commit` hooks per eseguire `ESLint`, `Prettier`, `Ruff` e `Mypy` prima di ogni commit.

## Backend: FastAPI Best Practices

Per implementazioni backend con FastAPI, seguire le best practices documentate in:

**Documento**: `docs/architecture/addendum-fastapi-best-practices.md`

**Aree Coperte**:
1. **Endpoint Protetto con JWT**: Pattern per auth admin con verifica role esplicita (mitiga R-4.1-1: Admin Auth Bypass)
2. **Validazione Dati con Pydantic**: Request/response models con validatori custom
3. **Configuration Management**: pydantic-settings per secrets e config sicure
4. **Endpoint Asincrono**: async/await patterns per performance I/O non-bloccanti (mitiga R-4.1-4: Performance Degradation)
5. **Error Handling Centralizzato**: Exception handlers globali con logging strutturato (mitiga R-4.1-6: Error Handling Completeness)
6. **Logging Strutturato per Audit**: JSON logging con PII sanitization (mitiga R-4.1-2: Data Exposure)
7. **Rate Limiting Pattern**: Implementazione rate limiting per controllo costi (mitiga R-4.1-3: Uncontrolled API Costs)
8. **Testing Patterns**: Dependency override per unit/integration testing

**Applicabilità**: Tutti gli endpoint FastAPI del progetto, con particolare enfasi su endpoint admin e operazioni sensibili.

**Riferimenti Rischi Mitigati**:
- CRITICAL: R-4.1-1 (Admin Authentication Bypass)
- HIGH: R-4.1-2 (Data Exposure), R-4.1-3 (API Costs), R-4.1-4 (Performance), R-4.1-6 (Error Handling)

[Fonte: `docs/qa/assessments/4.1-risk-20250930.md`; `docs/qa/assessments/4.1-test-design-20250930.md`]

## Backend: Pydantic Settings Configuration Management

Per la gestione centralizzata della configurazione applicativa, seguire i pattern documentati in:

**Documento**: `docs/architecture/addendum-pydantic-settings-configuration.md`

**Aree Coperte**:
1. **BaseSettings Pattern**: Configurazione centralizzata con type-safety e validazione automatica
2. **Environment Variables**: Naming conventions, prefissi, alias, nested delimiter per sub-models
3. **Field Validators**: Before/After/Wrap validators per validazione custom (range checks, consistency)
4. **Model Validators**: Validazione cross-field e consistency checks multi-parametro
5. **SecretStr Pattern**: Gestione sicura di API keys, passwords, tokens (mitigazione data exposure)
6. **Custom Sources**: Override precedenza sorgenti, file JSON/YAML/TOML, secrets directory
7. **Environment-Specific Config**: Pattern per configurazioni dev/staging/prod
8. **Testing Patterns**: Override configuration in test, dependency injection mocking

**Applicabilità**: 
- Tutti i moduli che richiedono configurazione esterna (`apps/api/api/config.py`)
- Story 2.12 (centralizzazione configurazione LLM: model, temperature, API keys)
- Componenti con secrets (database credentials, API keys, JWT secrets)

**Rischi Mitigati**:
- **OPS-001**: Configuration errors at startup (early validation con fail-fast pattern)
- **SEC-001**: Credential exposure in logs/tracebacks (SecretStr masking)
- **MAINT-001**: Configuration drift between environments (environment-specific overrides)

**Pattern Chiave**:
```python
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_nested_delimiter='__',
        validate_default=True
    )
    
    # Secrets sempre SecretStr
    openai_api_key: SecretStr
    
    # Validazione range con after validator
    openai_temperature: float | None = None
    
    @field_validator('openai_temperature', mode='after')
    @classmethod
    def validate_temp_range(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 2.0):
            raise ValueError(f'Temperature {v} fuori range [0.0, 2.0]')
        return v
```

**Dependency Injection Pattern**:
```python
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()

# Uso in endpoint FastAPI
@app.get("/api/endpoint")
async def endpoint(settings: Settings = Depends(get_settings)):
    model = settings.openai_model
```

[Fonte: Story `2.12.gpt-5-nano-integration.md`; Documentazione ufficiale Pydantic Settings]

## Backend: LangChain RAG Patterns

Per implementazioni RAG con LangChain, seguire i pattern documentati in:

**Documento**: `docs/architecture/addendum-langchain-rag-debug-patterns.md`

**Aree Coperte**:
1. **RunnablePassthrough.assign**: Accumulo risultati intermedi in pipeline LCEL (documents, context, answer)
2. **Retriever con Similarity Scores**: Pattern per includere scores nei metadata documents
3. **Catena RAG Debug-Enabled**: Implementazione completa con visibilità intermedia
4. **Timing Metrics Separati**: Breakdown retrieval vs generation (mitiga R-4.1-8: Timing Metrics Accuracy)
5. **FastAPI Integration**: Endpoint async con LangChain `.ainvoke()`
6. **Testing Patterns**: Mock retriever e integration tests per RAG

**Applicabilità**: Story 4.1 (Admin Debug View), future implementazioni RAG con requisiti di visibilità intermedia o debugging.

**Riferimenti Rischi Mitigati**:
- MEDIUM: R-4.1-8 (Timing Metrics Accuracy)

**Acceptance Criteria Coperti**:
- AC3: Visualizzazione chunk con similarity scores
- AC4: Ordinamento chunk per rilevanza (score decrescente)

[Fonte: `docs/stories/4.1.admin-debug-view.md`; `docs/qa/assessments/4.1-test-design-20250930.md`]

---


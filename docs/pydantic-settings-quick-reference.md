# Pydantic Settings - Quick Reference per Team FisioRAG

> **Scopo**: Guida rapida per trovare informazioni su Pydantic Settings configuration management nel progetto FisioRAG.  
> **Ultima revisione**: 2025-01-17

---

## 📚 Dove Trovare le Informazioni

### Documentazione Principale

| Documento | Contenuto | Quando Usare |
|-----------|-----------|--------------|
| **[Addendum Pydantic Settings](architecture/addendum-pydantic-settings-configuration.md)** | Guida completa: BaseSettings, validators, SecretStr, custom sources, testing | Implementazione configurazione, validazione custom, gestione secrets |
| **[Sezione 12: Standard di Codifica](architecture/sezione-12-standard-di-codifica.md)** | Pattern chiave e best practices per il progetto | Quick reference pattern base, rischi mitigati |
| **[Sezione 3: Tech Stack](architecture/sezione-3-tech-stack.md)** | Configuration Management nel tech stack | Overview tecnologia e razionale scelta |
| **[Addendum FastAPI Best Practices](architecture/addendum-fastapi-best-practices.md)** | Integrazione con FastAPI endpoints | Dependency injection, testing override |

### Story di Riferimento

- **[Story 2.12: GPT-5-nano Integration](stories/2.12.gpt-5-nano-integration.md)** — Implementazione configurazione LLM centralizzata con validators

---

## ⚡ Pattern Essenziali

### 1. BaseSettings Base

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        validate_default=True,
        extra='ignore'
    )
    
    # Secrets sempre SecretStr
    openai_api_key: SecretStr
    database_password: SecretStr
    
    # Config tipizzata
    openai_model: str = 'gpt-5-nano'
    max_retries: int = Field(default=3, ge=1, le=10)
```

**File:** `apps/api/api/config.py`

---

### 2. Field Validators (After Mode - Raccomandato)

```python
from pydantic import field_validator

class Settings(BaseSettings):
    temperature: float | None = None
    
    @field_validator('temperature', mode='after')
    @classmethod
    def validate_range(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 2.0):
            raise ValueError(f'Temperature {v} fuori range [0.0, 2.0]')
        return v
```

**Quando usare:**
- Validazione range/constraints
- Type-safe (valore già validato da Pydantic)
- Business logic validation

---

### 3. Model Validators (Cross-Field)

```python
from pydantic import model_validator
from typing_extensions import Self

class Settings(BaseSettings):
    use_cache: bool
    cache_ttl: int | None = None
    
    @model_validator(mode='after')
    def validate_cache_config(self) -> Self:
        if self.use_cache and self.cache_ttl is None:
            raise ValueError('cache_ttl obbligatorio se use_cache=True')
        return self  # CRITICAL: ritorna self
```

**Quando usare:**
- Validazione dipendenze tra campi
- Consistency checks multi-parametro

---

### 4. Dependency Injection in FastAPI

```python
from functools import lru_cache
from fastapi import Depends

@lru_cache
def get_settings() -> Settings:
    return Settings()

# Uso in endpoint
@app.get("/api/status")
async def status(settings: Settings = Depends(get_settings)):
    return {"model": settings.openai_model}
```

**File:** `apps/api/api/config.py` (singleton pattern)

---

### 5. Nested Models (Environment Variables)

```python
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    host: str = 'localhost'
    port: int = 5432

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter='__')
    database: DatabaseConfig
```

**Environment variables:**
```bash
DATABASE__HOST=prod-db.example.com
DATABASE__PORT=5432
```

---

### 6. SecretStr Pattern

```python
from pydantic import SecretStr

class Settings(BaseSettings):
    api_key: SecretStr  # masked in logs/repr
    
# Accesso valore (solo dove necessario)
real_key = settings.api_key.get_secret_value()
```

**DO:**
- Usare per: API keys, passwords, tokens, JWT secrets
- Chiamare `get_secret_value()` solo dove strettamente necessario

**DON'T:**
- Loggare mai `get_secret_value()` direttamente
- Convertire a stringa in contesti non sicuri

---

### 7. Testing Override

```python
import pytest
from api.config import get_settings

@pytest.fixture
def test_settings():
    return Settings(
        openai_api_key='test-key',
        openai_model='gpt-3.5-turbo'
    )

def test_endpoint(test_settings):
    app.dependency_overrides[get_settings] = lambda: test_settings
    # ... test code
```

---

## 🎯 Checklist Implementazione

Quando implementi nuova configurazione:

- [ ] **Tipo corretto**: `str`, `int`, `float`, `bool`, `SecretStr`
- [ ] **Default sicuro**: valore production-ready
- [ ] **Validator se necessario**: range checks, format validation
- [ ] **Descrizione Field**: `Field(..., description="...")`
- [ ] **ENV_TEMPLATE aggiornato**: documentare nuova variabile
- [ ] **Test configurazione**: test validazione, test override
- [ ] **SecretStr per secrets**: mai `str` per API keys/passwords

---

## 🚨 Rischi Mitigati

| Rischio | Mitigazione Pattern |
|---------|---------------------|
| **OPS-001**: Configuration errors at startup | Validators + fail-fast pattern |
| **SEC-001**: Credential exposure | SecretStr masking |
| **MAINT-001**: Config drift tra ambienti | Environment-specific `.env` files |

---

## 📖 Approfondimenti

Per dettagli completi su:
- **Before/Wrap validators**: `addendum-pydantic-settings-configuration.md` → Sezione 4
- **Custom sources (JSON/YAML)**: `addendum-pydantic-settings-configuration.md` → Sezione 6
- **Environment-specific config**: `addendum-pydantic-settings-configuration.md` → Sezione 7
- **ValidationInfo (context)**: `addendum-pydantic-settings-configuration.md` → Sezione 4.3
- **Nested secrets directory**: `addendum-pydantic-settings-configuration.md` → Sezione 5.4

---

## 🔗 Link Utili

- [Pydantic Settings Official Docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Pydantic Validators Official Docs](https://docs.pydantic.dev/latest/concepts/validators/)
- **Codice di Riferimento**: `apps/api/api/config.py` (implementazione FisioRAG)
- **Story Esempio**: `docs/stories/2.12.gpt-5-nano-integration.md`

---

**Domande?** Consulta l'[Addendum completo](architecture/addendum-pydantic-settings-configuration.md) o contatta l'Architect.


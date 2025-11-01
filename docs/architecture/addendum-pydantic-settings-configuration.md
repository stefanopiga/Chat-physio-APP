# Addendum: Pydantic Settings - Configuration Management Pattern

**Riferimento Story:** 2.12 (Integrazione GPT-5-nano)  
**Data Creazione:** 2025-01-17  
**Scopo:** Guida di riferimento per configuration management con `pydantic-settings`, validazione centralizzata e gestione sicura delle variabili d'ambiente.

---

## Indice

1. [Introduzione e Contesto](#1-introduzione-e-contesto)
2. [BaseSettings: Configurazione Centralizzata](#2-basesettings-configurazione-centralizzata)
3. [Environment Variables: Naming e Parsing](#3-environment-variables-naming-e-parsing)
4. [Validators: Validazione Personalizzata](#4-validators-validazione-personalizzata)
5. [SecretStr e Gestione Credenziali](#5-secretstr-e-gestione-credenziali)
6. [Custom Sources e Override](#6-custom-sources-e-override)
7. [Pattern Applicativi](#7-pattern-applicativi)
8. [Best Practices](#8-best-practices)

---

## 1. Introduzione e Contesto

### 1.1 Perche Pydantic Settings

La gestione della configurazione applicativa in FisioRAG segue il pattern **Settings as Code**:
- **Type-safety**: validazione statica della configurazione a runtime
- **Single Source of Truth**: configurazione centralizzata in `apps/api/api/config.py`
- **Environment-aware**: supporto nativo per file `.env` multipli e override
- **Security-first**: gestione sicura di secrets con `SecretStr`

### 1.2 Integrazione nel Tech Stack

Riferimenti correlati:
- **Tech Stack** -> `sezione-3-tech-stack.md`, riga 30: "Configuration Management: `.env` files + `pydantic-settings`"
- **Standard di Codifica** -> `sezione-12-standard-di-codifica.md`, sezione FastAPI Best Practices
- **Story 2.12** -> `docs/stories/2.12.gpt-5-nano-integration.md`: implementazione configurazione LLM centralizzata

---

## 2. BaseSettings: Configurazione Centralizzata

### 2.1 Concetti Fondamentali

`BaseSettings` eredita da `BaseModel` e aggiunge:
- Caricamento automatico da **variabili d'ambiente**
- Supporto per **file `.env`** (singoli o multipli)
- **Validazione dei default** (attiva di default, a differenza di `BaseModel`)
- **Precedenza delle sorgenti** configurabile

### 2.2 Precedenza Sorgenti (Ordine Decrescente)

1. **CLI arguments** (se `cli_parse_args=True`)
2. **Argomenti espliciti** all'inizializzatore (`Settings(field=value)`)
3. **Variabili d'ambiente** (`os.environ`)
4. **File dotenv** (`.env`)
5. **Secrets directory** (es. Docker Secrets)
6. **Valori di default** dei campi

Le sorgenti piu specifiche prevalgono sempre su quelle generali.

### 2.3 Pattern Base in FisioRAG

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Configurazione centralizzata applicazione FisioRAG."""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,          # env vars case-insensitive
        validate_default=True,         # valida i default
        extra='ignore'                 # ignora variabili extra in .env
    )
    
    # Database
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_key: SecretStr = Field(..., description="Supabase service role key")
    
    # OpenAI (Story 2.12)
    openai_api_key: SecretStr = Field(..., description="OpenAI API key")
    openai_model: str = Field(default='gpt-5-nano', description="LLM model name")
    openai_temperature_chat: float | None = Field(
        default=None, 
        description="Temperatura per chat (None = usa default del modello)"
    )
    openai_temperature_classification: float = Field(
        default=1.0,
        description="Temperatura per classificazione documenti"
    )
    llm_config_refactor_enabled: bool = Field(
        default=True,
        description="Feature flag per rollout sicuro Story 2.12"
    )

# Singleton pattern con caching
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    """Restituisce configurazione singleton con caching."""
    return Settings()
```

### 2.4 Dependency Injection in FastAPI

```python
from fastapi import Depends

@app.get("/api/config/status")
async def config_status(settings: Settings = Depends(get_settings)):
    """Endpoint che accede alla configurazione via DI."""
    return {
        "model": settings.openai_model,
        "temperature_chat": settings.openai_temperature_chat
    }
```

**Vantaggi:**
- Testing semplificato (override `get_settings` nei test)
- Configurazione accessibile in tutto lo stack FastAPI
- Zero accoppiamento con implementazione concreta

---

## 3. Environment Variables: Naming e Parsing

### 3.1 Naming Conventions

**Default behavior:**
```python
class Settings(BaseSettings):
    database_host: str  # legge DATABASE_HOST (case-insensitive)
```

**Con prefisso:**
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='FISIORAG_')
    
    api_key: str  # legge FISIORAG_API_KEY
```

**Con alias:**
```python
from pydantic import Field, AliasChoices

class Settings(BaseSettings):
    # Alias singolo (ignora env_prefix)
    auth_key: str = Field(validation_alias='MY_AUTH_KEY')
    
    # Alias multipli (primo trovato vince)
    redis_dsn: str = Field(
        validation_alias=AliasChoices('SERVICE_REDIS_DSN', 'REDIS_URL')
    )
```

### 3.2 Parsing di Valori Complessi

**Tipi semplici** (`int`, `float`, `str`): parsing diretto da stringa

**Tipi complessi** (`list`, `dict`, sub-models): **parsing JSON** dalla stringa

Esempio:
```bash
# File .env
SERVERS='["server1", "server2", "server3"]'
CONFIG='{"timeout": 30, "retries": 3}'
```

```python
class Settings(BaseSettings):
    servers: list[str]           # parsing da JSON array
    config: dict[str, int]       # parsing da JSON object
```

### 3.3 Nested Models con Delimiter

**Pattern per sub-models annidati:**

```python
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    host: str = 'localhost'
    port: int = 5432
    user: str
    password: SecretStr

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter='__'  # separatore per nesting
    )
    
    database: DatabaseConfig
```

**Variabili d'ambiente corrispondenti:**
```bash
DATABASE__HOST=prod-db.example.com
DATABASE__PORT=5432
DATABASE__USER=admin
DATABASE__PASSWORD=secret123
```

**Alternativa JSON** (override delimiter):
```bash
DATABASE='{"host": "prod-db", "port": 5432, "user": "admin", "password": "secret123"}'
```

La variabile `DATABASE__PORT` prevale sempre su `DATABASE` (nested > JSON).

### 3.4 Disabilitare Parsing JSON (Custom Parsing)

**Caso d'uso:** parsing custom per formati proprietari

```python
from typing import Annotated
from pydantic_settings import NoDecode

class Settings(BaseSettings):
    # Disabilita JSON parsing, usa validator custom
    numbers: Annotated[list[int], NoDecode]
    
    @field_validator('numbers', mode='before')
    @classmethod
    def parse_csv(cls, v: str) -> list[int]:
        return [int(x.strip()) for x in v.split(',')]
```

```bash
# .env
NUMBERS=1,2,3,4,5  # parsing custom (CSV)
```

---

## 4. Validators: Validazione Personalizzata

### 4.1 Tipologie di Validators (Ordine di Esecuzione)

#### 4.1.1 Before Validators (`mode='before'`)

**Quando usare:** preprocessing, conversioni pre-validazione

**Caratteristiche:**
- Ricevono input grezzo (tipo `Any`)
- Eseguiti **prima** della validazione Pydantic
- Output validato da Pydantic secondo il tipo annotato

```python
from pydantic import field_validator
from typing import Any

class Settings(BaseSettings):
    temperature: float
    
    @field_validator('temperature', mode='before')
    @classmethod
    def convert_celsius_to_kelvin(cls, v: Any) -> Any:
        """Converte temperatura da Celsius a Kelvin se stringa con suffisso 'C'."""
        if isinstance(v, str) and v.endswith('C'):
            celsius = float(v[:-1])
            return celsius + 273.15  # conversione
        return v  # pass-through per valori numerici
```

#### 4.1.2 After Validators (`mode='after'`, default)

**Quando usare:** validazione post-type-checking, range checks

**Caratteristiche:**
- Ricevono valore **gia tipizzato** da Pydantic
- Type-safe: annotazione tipo corretta
- **Raccomandati** per business logic validation

```python
class Settings(BaseSettings):
    openai_temperature_chat: float | None = None
    
    @field_validator(
        'openai_temperature_chat',
        'openai_temperature_classification',
        mode='before',
    )
    @classmethod
    def validate_temperature_range(
        cls,
        value: float | str | None,
        info: FieldValidationInfo,
    ) -> float | None:
        """Valida range temperatura OpenAI [0.0, 2.0] con fallback sicuro."""
        default = None if info.field_name == 'openai_temperature_chat' else 1.0
        if value is None:
            return default
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return default
            value = float(stripped)
        value = float(value)
        if not 0.0 <= value <= 2.0:
            raise ValueError(
                f'{info.field_name} fuori range valido [0.0, 2.0]: {value}'
            )
        return value
```

**Aggiornamento QA Gate (Story 2.12):**
- Normalizzazione degli input stringa (conversione `str → float` con trim).
- Fallback ai default sicuri su valori mancanti.
- Errori espliciti su valori fuori range o malformati.

#### 4.1.3 Normalizzazione modello LLM

```python
@field_validator('openai_model', mode='before')
@classmethod
def sanitize_openai_model(cls, value: str | None) -> str:
    """Usa default gpt-5-nano se env mancante o blank."""
    if value is None:
        return 'gpt-5-nano'
    candidate = value.strip()
    if not candidate:
        cls._logger.warning("OPENAI_MODEL blank → fallback default")
        return 'gpt-5-nano'
    return candidate
```

**Nota:** qualsiasi valore non stringa genera `TypeError` in modo da fallire l'avvio dell'app con messaggio chiaro (safe fail).

#### 4.1.4 Wrap Validators (`mode='wrap'`)

**Quando usare:** intercettare errori Pydantic, fallback values

**Caratteristiche:**
- Parametro `handler` obbligatorio (delegazione a Pydantic)
- Controllo completo su exception handling
- Massima flessibilita

```python
from pydantic import ValidatorFunctionWrapHandler, ValidationError

class Settings(BaseSettings):
    max_retries: int = 3
    
    @field_validator('max_retries', mode='wrap')
    @classmethod
    def clamp_retries(
        cls, 
        v: Any, 
        handler: ValidatorFunctionWrapHandler
    ) -> int:
        """Clamp retries a range [1, 10], fallback a 3 se parsing fallisce."""
        try:
            value = handler(v)  # delega validazione a Pydantic
            return max(1, min(value, 10))  # clamp
        except ValidationError:
            return 3  # fallback sicuro
```

### 4.2 Model Validators (Validazione Multi-Campo)

**Pattern per validazione cross-field:**

```python
from pydantic import model_validator
from typing_extensions import Self

class Settings(BaseSettings):
    openai_temperature_chat: float | None = None
    openai_temperature_classification: float = 1.0
    
    @model_validator(mode='after')
    def validate_temperature_consistency(self) -> Self:
        """Assicura coerenza tra temperature diverse."""
        if self.openai_temperature_chat is not None:
            if abs(self.openai_temperature_chat - self.openai_temperature_classification) > 1.5:
                raise ValueError(
                    'Temperature troppo divergenti: possibile configurazione errata'
                )
        return self  # CRITICAL: deve ritornare self
```

**Quando usare:**
- Validazione di vincoli tra campi multipli
- Consistency checks (es. password/password_repeat)
- Post-initialization hooks

### 4.3 ValidationInfo: Accesso a Contesto

**Parametro opzionale per validators:**

```python
from pydantic import ValidationInfo

class Settings(BaseSettings):
    max_connections: int
    
    @field_validator('max_connections', mode='after')
    @classmethod
    def validate_connections(cls, v: int, info: ValidationInfo) -> int:
        """Valida max_connections in base ad altri campi gia validati."""
        # Accesso a campi gia validati
        db_host = info.data.get('database_host')
        
        # Accesso a context custom (passato in model_validate)
        if info.context and info.context.get('environment') == 'production':
            if v < 10:
                raise ValueError('Production richiede almeno 10 connessioni')
        
        return v
```

**Note:**
- `info.data`: dizionario campi gia validati (solo field validators)
- `info.context`: dizionario custom passato in `model_validate(..., context={...})`
- `info.field_name`: nome campo corrente

---

## 5. SecretStr e Gestione Credenziali

### 5.1 Perche SecretStr

**Problema:** credenziali esposte in:
- Log applicativi (`print(settings)`)
- Tracebacks di errore
- Output `repr()` / `str()` in debugging
- Serializzazione JSON accidentale

**Soluzione:** `SecretStr` / `SecretBytes`

### 5.2 Pattern Base

```python
from pydantic import SecretStr

class Settings(BaseSettings):
    openai_api_key: SecretStr
    database_password: SecretStr
    jwt_secret: SecretStr
```

**Output mascherato:**
```python
settings = Settings(
    openai_api_key='sk-proj-abc123',
    database_password='SuperSecret123'
)

print(settings.openai_api_key)
# Output: SecretStr('**********')

# Accesso al valore reale (solo quando necessario)
real_key = settings.openai_api_key.get_secret_value()
# Output: 'sk-proj-abc123'
```

### 5.3 Best Practices SecretStr

**DO:**
- Usare `SecretStr` per: API keys, passwords, tokens, JWT secrets, connection strings con credenziali
- Chiamare `get_secret_value()` solo dove strettamente necessario (es. client API)
- Passare direttamente `SecretStr` ai client che lo supportano (es. alcuni SDK)

**DON'T:**
- Loggare mai `get_secret_value()` direttamente
- Convertire a stringa in contesti non sicuri
- Serializzare in JSON senza mascheramento esplicito

### 5.4 Secrets da File (Docker Secrets Pattern)

**Caso d'uso:** secrets montati come file (Kubernetes, Docker Swarm)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        secrets_dir='/run/secrets',  # directory Docker Secrets
        secrets_dir_missing='warn'   # comportamento se directory mancante
    )
    
    database_password: SecretStr  # legge /run/secrets/database_password
```

**Precedenza:**
- Environment variables > dotenv > secrets directory

**Nested Secrets:**
```python
from pydantic_settings import NestedSecretsSettingsSource

class DatabaseConfig(BaseModel):
    user: str
    password: SecretStr

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        secrets_dir='secrets',
        secrets_nested_delimiter='_'  # flat: db_password
    )
    
    database: DatabaseConfig
```

Layout directory:
```
secrets/
- database_user
- database_password
```

---

## 6. Custom Sources e Override

### 6.1 Customizzazione Precedenza Sorgenti

**Metodo:** override di `settings_customise_sources`

```python
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
)

class Settings(BaseSettings):
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Precedenza custom: env vars > init kwargs > dotenv
        return (
            env_settings,        # massima priorita
            init_settings,
            dotenv_settings,
            file_secret_settings,
        )
```

### 6.2 Aggiungere Sorgenti Custom (es. JSON Config)

```python
import json
from pathlib import Path
from typing import Any
from pydantic.fields import FieldInfo

class JsonConfigSource(PydanticBaseSettingsSource):
    """Sorgente custom per config JSON."""
    
    def get_field_value(
        self, 
        field: FieldInfo, 
        field_name: str
    ) -> tuple[Any, str, bool]:
        """Carica campo da file JSON."""
        config_file = Path('config.json')
        if config_file.exists():
            data = json.loads(config_file.read_text())
            return data.get(field_name), field_name, False
        return None, field_name, False
    
    def __call__(self) -> dict[str, Any]:
        d = {}
        for field_name, field in self.settings_cls.model_fields.items():
            value, key, _ = self.get_field_value(field, field_name)
            if value is not None:
                d[key] = value
        return d

class Settings(BaseSettings):
    @classmethod
    def settings_customise_sources(cls, ...) -> tuple[...]:
        return (
            init_settings,
            JsonConfigSource(settings_cls),  # sorgente custom
            env_settings,
            dotenv_settings,
        )
```

### 6.3 Sorgenti Built-in Aggiuntive

```python
from pydantic_settings import (
    TomlConfigSettingsSource,
    YamlConfigSettingsSource,
    PyprojectTomlConfigSettingsSource,
)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        toml_file=['config.default.toml', 'config.custom.toml']
        # config.custom.toml override config.default.toml
    )
    
    @classmethod
    def settings_customise_sources(cls, ...) -> tuple[...]:
        return (
            init_settings,
            TomlConfigSettingsSource(settings_cls),
            env_settings,
        )
```

### 6.4 Rimozione Sorgenti

```python
@classmethod
def settings_customise_sources(cls, ...) -> tuple[...]:
    # Ignora completamente init kwargs (solo env vars e dotenv)
    return (env_settings, dotenv_settings)
```

---

## 7. Pattern Applicativi

### 7.1 Configurazioni per Ambiente (dev/staging/prod)

**Pattern 1: File `.env` multipli**

```python
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            '.env',                            # default base
            f'.env.{os.getenv("ENV", "dev")}'  # override per ambiente
        )
    )
```

Layout file:
```
.env              # configurazione base
.env.dev          # override dev
.env.staging      # override staging
.env.prod         # override prod
```

**Pattern 2: Validazione condizionale per ambiente**

```python
from typing import Literal

class Settings(BaseSettings):
    environment: Literal['dev', 'staging', 'prod'] = 'dev'
    debug: bool = True
    
    @model_validator(mode='after')
    def validate_environment_config(self) -> Self:
        """Enforce production constraints."""
        if self.environment == 'prod':
            if self.debug:
                raise ValueError('Debug mode non permesso in production')
            if not self.openai_api_key:
                raise ValueError('API key obbligatoria in production')
        return self
```

### 7.2 Sub-models per Configurazioni Complesse

```python
class OpenAIConfig(BaseModel):
    """Configurazione OpenAI isolata."""
    api_key: SecretStr
    model: str = 'gpt-5-nano'
    temperature_chat: float | None = None
    temperature_classification: float = 1.0
    max_tokens: int = 2000
    
    @field_validator('temperature_chat', 'temperature_classification', mode='after')
    @classmethod
    def validate_temperature(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 2.0):
            raise ValueError(f'Temperature {v} fuori range [0.0, 2.0]')
        return v

class DatabaseConfig(BaseModel):
    """Configurazione database isolata."""
    url: str
    service_key: SecretStr
    max_connections: int = 10

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter='__')
    
    openai: OpenAIConfig
    database: DatabaseConfig
```

**Variabili d'ambiente:**
```bash
OPENAI__API_KEY=sk-proj-xyz
OPENAI__MODEL=gpt-5-nano
OPENAI__TEMPERATURE_CHAT=0.7
DATABASE__URL=postgresql://localhost:5432/db
DATABASE__SERVICE_KEY=secret
```

### 7.3 Reload in-place (Development)

```python
import os

# Carica configurazione iniziale
settings = Settings()
print(settings.openai_model)  # 'gpt-5-nano'

# Cambia env var runtime
os.environ['OPENAI_MODEL'] = 'gpt-4'

# Reload manuale
settings.__init__()
print(settings.openai_model)  # 'gpt-4'
```

**Caso d'uso:** testing, debugging, hot-reload configurazione.

---

## 8. Best Practices

### 8.1 Checklist Configurazione Sicura

- [ ] **Secrets sempre `SecretStr`**: API keys, passwords, tokens
- [ ] **Validazione range**: temperature, timeouts, max_retries
- [ ] **Validazione cross-field**: consistency checks tra parametri correlati
- [ ] **Default sicuri**: valori di default production-ready
- [ ] **Environment separation**: file `.env` per ambiente (non committare `.env.prod`)
- [ ] **Documentazione ENV_TEMPLATE**: mantenere `ENV_TEMPLATE.txt` aggiornato
- [ ] **Type hints corretti**: `float | None` vs `float` per optional
- [ ] **Testing config**: test per override e validazione

### 8.2 Gestione `.env` Files

**DO:**
- Committare `.env.example` con valori placeholder
- Usare `.gitignore` per `.env`, `.env.local`, `.env.prod`
- Documentare tutte le variabili in `ENV_TEMPLATE.txt`

**DON'T:**
- Committare mai file `.env` con secrets reali
- Hardcodare secrets nel codice (usa sempre env vars)
- Usare secrets in test (mock o env vars dedicate)

### 8.3 Testing Configuration

**Pattern 1: Override in test**

```python
import pytest
from api.config import Settings, get_settings

@pytest.fixture
def test_settings():
    """Settings mock per test."""
    return Settings(
        openai_api_key='test-key',
        openai_model='gpt-3.5-turbo',  # modello economico per test
        database_url='sqlite:///:memory:'
    )

def test_chat_service(test_settings):
    """Test con configurazione custom."""
    # Override dependency
    app.dependency_overrides[get_settings] = lambda: test_settings
    # ... test code
```

**Pattern 2: Environment vars in test**

```python
import os
import pytest

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Setup env vars per tutti i test."""
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
```

### 8.4 Logging Configurazione (Sicuro)

**Pattern sicuro per logging config (senza secrets):**

```python
import logging

def log_config_summary(settings: Settings):
    """Log configurazione senza esporre secrets."""
    logger = logging.getLogger(__name__)
    logger.info("Configuration loaded:")
    logger.info(f"  OpenAI Model: {settings.openai_model}")
    logger.info(f"  Temperature Chat: {settings.openai_temperature_chat}")
    logger.info(f"  Database URL: {settings.database_url.split('@')[1]}")  # solo host
    # NON loggare mai: settings.openai_api_key.get_secret_value()
```

### 8.5 Validazione Startup

**Pattern per validazione early fail:**

```python
from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
async def validate_config():
    """Valida configurazione all'avvio (fail fast)."""
    try:
        settings = get_settings()
        
        # Validazione connessione database
        # (ping DB, verifica credenziali)
        
        # Validazione API keys (test call minima)
        # (es. GET /models per OpenAI)
        
        logger.info("OK Configuration validated successfully")
        
    except Exception as e:
        logger.error(f"ERR Configuration validation failed: {e}")
        raise  # fail fast, non avviare app con config invalida
```

**Rischio mitigato:**
- **OPS-001**: Early detection configurazione errata (evita runtime failures)

---

## Riferimenti

### Documentazione Ufficiale
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Pydantic Validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [Pydantic Secret Types](https://docs.pydantic.dev/2.2/usage/types/secrets/)

### Documentazione FisioRAG
- **Tech Stack** -> `docs/architecture/sezione-3-tech-stack.md`
- **Standard di Codifica** -> `docs/architecture/sezione-12-standard-di-codifica.md`
- **FastAPI Best Practices** -> `docs/architecture/addendum-fastapi-best-practices.md`
- **Story 2.12** -> `docs/stories/2.12.gpt-5-nano-integration.md`

### File di Configurazione
- **Config centralized** -> `apps/api/api/config.py`
- **ENV template** -> `ENV_TEMPLATE.txt`
- **ENV test template** -> `apps/api/ENV_TEST_TEMPLATE.txt`

---

**Ultima Revisione:** 2025-01-17  
**Reviewer:** Architect  
**Status:** Validato per implementazione Story 2.12


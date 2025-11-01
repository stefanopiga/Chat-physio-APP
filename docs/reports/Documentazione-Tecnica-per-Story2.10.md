# Documentazione Tecnica per Story 2.10 - Ingestione Massiva

Riferimento story: docs/stories/2.10.batch-ingestion-knowledge-base.md  
Data: 2025-10-15  
Ambito: best practice tecniche e pattern di implementazione per lo script `scripts/ingestion/ingest_all_documents.py`, a supporto degli Acceptance Criteria AC1â€“AC6.

## 1. Gestione Rate Limit - Exponential Backoff with Jitter (OPS-001)

### Sintesi della Best Practice

L'**exponential backoff with jitter** Ã¨ la strategia raccomandata per gestire rate limiting (errori HTTP 429). Quando si riceve un errore 429, il client deve attendere un tempo crescente esponenzialmente (2^n secondi) tra i tentativi, aggiungendo un ritardo casuale (jitter) per evitare che piÃ¹ client ritentino simultaneamente. Questo approccio Ã¨ descritto nel RFC 6585 per il codice di stato 429 e standardizzato da AWS Architecture Blog come best practice per sistemi distribuiti.

### Fonti Ufficiali

- **RFC 6585 - Additional HTTP Status Codes (429 Too Many Requests)**: https://datatracker.ietf.org/doc/html/rfc6585
- **AWS Architecture Blog - Exponential Backoff and Jitter**: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- **AWS Builders' Library - Timeouts, Retries and Backoff with Jitter**: https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/

### Esempio di Codice Python 3.11

```python
import time
import random
import requests
from typing import Optional

def ingest_document_with_backoff(
    file_path: str,
    api_url: str,
    max_retries: int = 5,
    base_delay: float = 1.0
) -> Optional[dict]:
    """
    Invia un documento all'API con exponential backoff + jitter per gestire rate limiting.
    
    Args:
        file_path: Percorso del file da inviare
        api_url: URL dell'endpoint API
        max_retries: Numero massimo di tentativi (default: 5)
        base_delay: Ritardo base in secondi per il backoff (default: 1.0)
    
    Returns:
        Response JSON se successo, None se tutti i tentativi falliscono
    """
    for attempt in range(max_retries):
        try:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    api_url,
                    files={'file': f},
                    timeout=30
                )
            
            # Successo - ritorna la risposta
            if response.status_code == 200:
                return response.json()
            
            # Rate limit superato - applica exponential backoff con jitter
            if response.status_code == 429:
                # Controlla se il server fornisce Retry-After header
                retry_after = response.headers.get('Retry-After')
                
                if retry_after:
                    # Usa il valore suggerito dal server
                    delay = float(retry_after)
                else:
                    # Calcola exponential backoff: 2^attempt * base_delay
                    exponential_delay = (2 ** attempt) * base_delay
                    
                    # Aggiungi jitter (randomizzazione 0-100%)
                    # per evitare "thundering herd" (tutti i client ritentano insieme)
                    jitter = random.uniform(0, exponential_delay)
                    delay = exponential_delay + jitter
                
                # Limita il delay massimo a 60 secondi
                delay = min(delay, 60.0)
                
                print(f"Rate limit hit. Tentativo {attempt + 1}/{max_retries}. "
                      f"Attesa {delay:.2f}s...")
                time.sleep(delay)
                continue
            
            # Altri errori HTTP - solleva eccezione
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            print(f"Errore di rete al tentativo {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                # Applica backoff anche per errori di rete
                delay = (2 ** attempt) * base_delay + random.uniform(0, base_delay)
                time.sleep(delay)
            else:
                return None
    
    # Tutti i tentativi esauriti
    print(f"Falliti tutti i {max_retries} tentativi per {file_path}")
    return None
```

---

## 2. Idempotenza e IntegritÃ  Dati - Scrittura Atomica del File di Stato (DATA-001)

### Sintesi della Best Practice

La **scrittura atomica** di file in Python si realizza scrivendo prima su un file temporaneo e poi usando `os.replace()` (o `os.rename()` su sistemi POSIX) per sostituire atomicamente il file di destinazione. Questa operazione Ã¨ garantita atomica a livello di filesystem: il file appare completo o assente, mai parziale o corrotto. Questo Ã¨ il pattern standard per garantire l'integritÃ  di file di stato critici come `ingestion_state.json`.

### Fonte Ufficiale

- **Python tempfile Documentation**: https://docs.python.org/3/library/tempfile.html
- **Stack Overflow - Atomic File Creation Pattern**: https://stackoverflow.com/questions/2333872/how-to-make-file-creation-an-atomic-operation (top-voted answer)
- **ActiveState Code Recipe - Safe Atomic Write**: https://code.activestate.com/recipes/579097-safely-and-atomically-write-to-a-file/

### Esempio di Codice Python 3.11

```python
import json
import tempfile
import os
from pathlib import Path
from typing import Any

def atomic_write_json(file_path: str | Path, data: dict[str, Any]) -> None:
    """
    Scrive un dizionario Python come JSON in modo atomico usando un file temporaneo.
    
    Questo pattern garantisce che:
    - Il file esiste solo se completo e valido
    - Non ci sono mai stati intermedi corrotti su disco
    - In caso di crash durante la scrittura, il vecchio file rimane intatto
    
    Args:
        file_path: Percorso del file JSON di destinazione
        data: Dizionario da serializzare in JSON
    """
    file_path = Path(file_path)
    
    # Crea un file temporaneo nella STESSA directory del file finale
    # Importante: deve essere nello stesso filesystem per os.replace() atomico
    with tempfile.NamedTemporaryFile(
        mode='w',
        encoding='utf-8',
        dir=file_path.parent,  # Stessa directory del file finale
        delete=False,  # Non eliminare automaticamente
        suffix='.tmp'
    ) as tmp_file:
        
        try:
            # Scrivi i dati JSON nel file temporaneo
            json.dump(data, tmp_file, indent=2, ensure_ascii=False)
            tmp_file.flush()  # Forza la scrittura su disco
            os.fsync(tmp_file.fileno())  # Garantisce che i dati siano sul disco
            
            tmp_path = tmp_file.name
            
        except Exception as e:
            # Se la scrittura fallisce, rimuovi il file temporaneo
            if os.path.exists(tmp_file.name):
                os.unlink(tmp_file.name)
            raise RuntimeError(f"Errore durante scrittura JSON: {e}") from e
    
    # Sostituisci atomicamente il file originale con quello temporaneo
    # os.replace() Ã¨ atomico su tutti i sistemi operativi (POSIX e Windows)
    try:
        os.replace(tmp_path, file_path)
    except Exception as e:
        # Se replace fallisce, pulisci il file temporaneo
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise RuntimeError(f"Errore durante replace atomico: {e}") from e


# Esempio d'uso per il file di stato dell'ingestione
def save_ingestion_state(
    state_file: Path,
    processed_files: list[str],
    failed_files: dict[str, str],
    last_processed_timestamp: str
) -> None:
    """
    Salva lo stato dell'ingestione in modo atomico e sicuro.
    
    Args:
        state_file: Percorso del file ingestion_state.json
        processed_files: Lista dei file giÃ  processati con successo
        failed_files: Dizionario {file_path: error_message} dei file falliti
        last_processed_timestamp: Timestamp ISO dell'ultimo file processato
    """
    state_data = {
        "version": "1.0",
        "last_updated": last_processed_timestamp,
        "processed_files": processed_files,
        "failed_files": failed_files,
        "total_processed": len(processed_files),
        "total_failed": len(failed_files)
    }
    
    # Scrittura atomica - garantisce integritÃ  in caso di interruzione
    atomic_write_json(state_file, state_data)
```

---

## 3. Parsing Sicuro dei Documenti - Gestione Eccezioni python-docx (DATA-002)

### Sintesi della Best Practice

La libreria **python-docx** solleva l'eccezione `docx.opc.exceptions.PackageNotFoundError` quando tenta di aprire un file .docx corrotto, mancante o non valido. La best practice consiste nell'intercettare questa eccezione specifica (e altre eccezioni generiche) con un blocco try-except, loggare il file problematico, e continuare con il prossimo file anzichÃ© interrompere l'intero processo di batch. Questo approccio Ã¨ documentato nelle issue GitHub del progetto python-openxml.

### Fonte Ufficiale

- **python-docx Official Documentation - Document API**: https://python-docx.readthedocs.io/en/latest/api/document.html
- **python-docx GitHub Issues - PackageNotFoundError**: https://github.com/python-openxml/python-docx/issues/758
- **Stack Overflow - Handling docx exceptions**: https://stackoverflow.com/questions/47199300/docx-opc-exceptions-packagenotfounderror-package-not-found-at

### Esempio di Codice Python 3.11

```python
from pathlib import Path
from docx import Document
from docx.opc.exceptions import PackageNotFoundError
import logging

# Configura logging per tracciare errori
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_text_from_docx(file_path: Path) -> str | None:
    """
    Estrae il testo da un file .docx gestendo in modo robusto errori di corruzione.
    
    Args:
        file_path: Percorso del file .docx da processare
    
    Returns:
        Testo estratto dal documento, oppure None se il file Ã¨ corrotto/invalido
    """
    try:
        # Tenta di aprire il documento
        doc = Document(str(file_path))
        
        # Estrai tutto il testo dai paragrafi
        full_text = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():  # Ignora paragrafi vuoti
                full_text.append(paragraph.text)
        
        # Estrai testo dalle tabelle (se presenti)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        full_text.append(cell.text)
        
        extracted = '\n'.join(full_text)
        logger.info(f"âœ“ Estratto con successo: {file_path.name} ({len(extracted)} caratteri)")
        return extracted
    
    except PackageNotFoundError:
        # File .docx non valido o corrotto
        logger.error(
            f"âœ— SKIP - File corrotto o non valido (PackageNotFoundError): {file_path.name}"
        )
        return None
    
    except PermissionError:
        # File aperto in un'altra applicazione o permessi insufficienti
        logger.error(
            f"âœ— SKIP - Permessi negati (PermissionError): {file_path.name}"
        )
        return None
    
    except Exception as e:
        # Altre eccezioni impreviste
        logger.error(
            f"âœ— SKIP - Errore imprevisto durante parsing di {file_path.name}: "
            f"{type(e).__name__}: {e}"
        )
        return None


def process_docx_batch(
    docx_dir: Path,
    failed_files: dict[str, str]
) -> dict[str, str]:
    """
    Processa un batch di file .docx, saltando quelli corrotti senza interrompere.
    
    Args:
        docx_dir: Directory contenente i file .docx
        failed_files: Dizionario per tracciare i file falliti (modificato in-place)
    
    Returns:
        Dizionario {file_name: extracted_text} dei file processati con successo
    """
    results = {}
    docx_files = list(docx_dir.glob("*.docx"))
    
    logger.info(f"Trovati {len(docx_files)} file .docx in {docx_dir}")
    
    for docx_file in docx_files:
        # Ignora file temporanei di Word (iniziano con ~$)
        if docx_file.name.startswith('~$'):
            continue
        
        extracted_text = extract_text_from_docx(docx_file)
        
        if extracted_text is not None:
            results[docx_file.name] = extracted_text
        else:
            # Traccia il file fallito per retry o analisi manuale
            failed_files[str(docx_file)] = "Errore durante parsing (vedi log)"
    
    logger.info(
        f"Completato batch: {len(results)} successi, {len(failed_files)} falliti"
    )
    return results
```

---

## 4. Comportamento del Server - Algoritmi Rate Limiting di Traefik e SlowAPI

### Sintesi della Best Practice

**SlowAPI** (basato su flask-limiter) utilizza la libreria **limits** che supporta tre algoritmi di rate limiting: **Fixed Window**, **Moving Window** e **Sliding Window Counter**. L'algoritmo piÃ¹ comune Ã¨ **Fixed Window** (finestra fissa) che Ã¨ memory-efficient e usa un singolo contatore per risorsa. **Traefik Rate Limiting Middleware** utilizza anch'esso un algoritmo basato su finestre temporali. **Nota importante**: nÃ© SlowAPI nÃ© Traefik includono di default l'header `Retry-After` nelle risposte 429, quindi il client deve implementare exponential backoff senza fare affidamento su questo header.

### Fonti Ufficiali

- **SlowAPI Documentation**: https://slowapi.readthedocs.io/
- **SlowAPI GitHub Repository**: https://github.com/laurentS/slowapi
- **limits Library (usata da SlowAPI)**: https://pypi.org/project/limits/
- **Traefik RateLimit Middleware Documentation**: https://doc.traefik.io/traefik/middlewares/http/ratelimit/

### Dettagli degli Algoritmi

**1. Fixed Window (Finestra Fissa)**
- **Come funziona**: Conta le richieste in finestre temporali fisse (es. 1 minuto). Quando la prima richiesta arriva, inizia una finestra che dura per l'intera durata specificata. Tutte le richieste in quella finestra incrementano il contatore. Quando la finestra scade, il contatore si resetta.
- **Vantaggi**: Memory-efficient (un solo contatore per risorsa).
- **Svantaggi**: Burst traffic ai confini delle finestre puÃ² superare temporaneamente il limite.

**2. Moving Window (Finestra Mobile)**
- **Come funziona**: Mantiene un log di timestamp per ogni richiesta. Una nuova richiesta Ã¨ permessa solo se l'n-esima richiesta piÃ¹ vecchia Ã¨ oltre la durata della finestra.
- **Vantaggi**: Distribuzione piÃ¹ uniforme del rate limiting.
- **Svantaggi**: Richiede piÃ¹ memoria (un timestamp per ogni richiesta).

**3. Sliding Window Counter (Finestra Scorrevole)**
- **Come funziona**: Ibrido che approssima Moving Window usando solo due contatori (bucket corrente e precedente) con un calcolo pesato.
- **Vantaggi**: Bilanciamento tra accuratezza e efficienza memoria.

### Esempio di Codice - Client consapevole del rate limiting

```python
import time
from typing import Final

# Configurazione basata sul rate limit del server
# Traefik/SlowAPI configurati a: 10 richieste/minuto
RATE_LIMIT_PER_MINUTE: Final[int] = 10
SAFE_REQUESTS_PER_MINUTE: Final[int] = 8  # Margine di sicurezza (80%)
MIN_DELAY_BETWEEN_REQUESTS: Final[float] = 60.0 / SAFE_REQUESTS_PER_MINUTE


class RateLimitedClient:
    """
    Client HTTP che rispetta automaticamente i rate limit del server.
    
    Implementa un rate limiting client-side per ridurre al minimo
    gli errori 429, combinato con exponential backoff quando si verificano.
    """
    
    def __init__(self, requests_per_minute: int = SAFE_REQUESTS_PER_MINUTE):
        """
        Args:
            requests_per_minute: Numero massimo di richieste al minuto (default: 8)
        """
        self.min_delay = 60.0 / requests_per_minute
        self.last_request_time = 0.0
    
    def wait_if_needed(self) -> None:
        """
        Attende se necessario per rispettare il rate limit client-side.
        
        Questo approccio proattivo riduce significativamente gli errori 429,
        distribuendo uniformemente le richieste nel tempo.
        """
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def send_request(self, url: str, **kwargs) -> dict:
        """
        Invia una richiesta HTTP rispettando il rate limit.
        
        Args:
            url: URL della risorsa
            **kwargs: Parametri addizionali per requests.post()
        
        Returns:
            Response JSON se successo
        """
        import requests
        
        # Attendi per rispettare il rate limit client-side
        self.wait_if_needed()
        
        # Invia la richiesta con retry e backoff (vedi Sezione 1)
        return ingest_document_with_backoff(url, **kwargs)


# Esempio d'uso integrato per ingestione batch
def batch_ingest_with_rate_limiting(
    files: list[Path],
    api_url: str
) -> dict[str, dict]:
    """
    Ingesta un batch di file rispettando rate limit e gestendo errori.
    
    Args:
        files: Lista di file da inviare
        api_url: URL dell'API di ingestione
    
    Returns:
        Dizionario {file_name: response} con i risultati
    """
    client = RateLimitedClient(requests_per_minute=SAFE_REQUESTS_PER_MINUTE)
    results = {}
    
    logger.info(
        f"Inizio batch di {len(files)} file con rate limiting "
        f"({SAFE_REQUESTS_PER_MINUTE} req/min)"
    )
    
    for i, file_path in enumerate(files, 1):
        logger.info(f"[{i}/{len(files)}] Processing: {file_path.name}")
        
        try:
            # Il client gestisce automaticamente:
            # 1. Rate limiting client-side (proattivo)
            # 2. Exponential backoff per 429 (reattivo)
            # 3. Retry per errori di rete
            response = client.send_request(
                api_url,
                files={'file': open(file_path, 'rb')}
            )
            results[file_path.name] = response
            
        except Exception as e:
            logger.error(f"Errore finale per {file_path.name}: {e}")
            results[file_path.name] = {"error": str(e)}
    
    return results
```

---

## Note Finali

**Integrazione delle Best Practice**

Per un'implementazione completa e robusta dello script `ingest_all_documents.py`, Ã¨ fortemente raccomandato:

1. **Combinare rate limiting client-side proattivo** (Sezione 4) con **exponential backoff reattivo** (Sezione 1)
2. **Utilizzare scrittura atomica** (Sezione 2) per salvare lo stato dopo ogni batch parziale (es. ogni 10 file)
3. **Applicare gestione robusta degli errori** (Sezione 3) per file .docx corrotti
4. **Loggare meticolosamente** ogni operazione per facilitare debugging e retry manuali

**Testing Raccomandato**

Prima del deployment in produzione:
- Testare con file .docx deliberatamente corrotti
- Simulare interruzioni forzate (CTRL+C) durante la scrittura dello stato
- Verificare il comportamento con rate limit bassi (es. 2 req/min) per validare exponential backoff
- Controllare che il file di stato sia sempre valido dopo interruzioni


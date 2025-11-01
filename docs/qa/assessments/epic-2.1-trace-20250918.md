# Requirements Traceability Matrix

## Story: epic-2.1 - Document Loader & Text Extractor

### Coverage Summary

- Total Requirements: 5
- Fully Covered: 4 (80%)
- Partially Covered: 0 (0%)
- Not Covered: 1 (20%)

### Requirement Mappings

#### AC1: Il servizio accede a una directory di file

Coverage: FULL

Given-When-Then Mappings:

- Unit Test: `apps/api/tests/test_ingestion.py::test_scan_crea_output_temporanei`
  - Given: directory di watch e temp esistenti
  - When: viene creato un file in watch e lanciato scan_once
  - Then: vengono creati artefatti temporanei e metadati

#### AC2: Scansiona file nuovi/modificati

Coverage: FULL

- Unit Test: `apps/api/tests/test_ingestion.py::test_scan_crea_output_temporanei`
  - Given: file iniziale e inventario vuoto
  - When: modifica del contenuto del file e nuova scansione
  - Then: viene rilevato nuovo hash e nuova registrazione

#### AC3: Il testo viene estratto correttamente (.pdf/.docx)

Coverage: NONE

- Nessun test implementato per `.pdf` o `.docx`.

#### AC4: Il contenuto viene salvato temporaneamente

Coverage: FULL

- Unit Test: `apps/api/tests/test_ingestion.py::test_scan_crea_output_temporanei`
  - Given: contenuto di un `.txt` estratto
  - When: salvataggio in temp
  - Then: creati file `{hash}.txt` e `{hash}.json`

#### AC5: Gestisce errori di parsing

Coverage: FULL

- Unit Test: `apps/api/tests/test_ingestion.py::test_scan_crea_output_temporanei`
  - Given: estrattori che possono sollevare eccezioni
  - When: eccezione durante estrazione
  - Then: `Document.status` è `error` e viene salvato l'errore

### Critical Gaps

1. AC3: Mancano test per `.pdf` e `.docx`.

### Test Design Recommendations

1. Aggiungere unit test per `.pdf`/`.docx` usando mocking dell'estrattore.

### Risk Assessment

- High Risk: Requisito AC3 senza copertura.

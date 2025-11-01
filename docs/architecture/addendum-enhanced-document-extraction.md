# Addendum: Enhanced Document Extraction for Story 2.5

**Context**: Estensione pipeline ingestion (Story 2.1) con extraction avanzata immagini, tabelle e caption detection per completamento pipeline RAG.

**Target Story**: 2.5 — Intelligent Document Preprocessing & Pipeline Completion

**Dependencies**: PyMuPDF (`pymupdf`), tenacity, python-docx (già presente), pdfplumber (optional)

---

## PyMuPDF (fitz) — PDF Extraction

### 1. Basic Text & Image Extraction

Pattern base per extraction testo e immagini embedded da PDF.

```python
import pymupdf  # PyMuPDF (fitz)
import os

# Apri il documento PDF
pdf_path = "documento.pdf"
doc = pymupdf.open(pdf_path)

# Itera su ogni pagina del documento
for page_num in range(len(doc)):
    page = doc[page_num]
    
    # Estrai il testo completo della pagina
    text = page.get_text()
    print(f"=== Pagina {page_num + 1} - Testo ===")
    print(text)
    
    # Ottieni lista delle immagini presenti nella pagina
    # Ogni elemento è una tupla: (xref, smask, width, height, bpc, colorspace, alt. colorspace, name, filter, referencer)
    image_list = page.get_images()
    
    print(f"=== Pagina {page_num + 1} - Immagini: {len(image_list)} ===")
    
    # Itera su ogni immagine trovata
    for img_index, img in enumerate(image_list):
        xref = img[0]  # Cross-reference number dell'immagine
        
        # Estrai i dati binari e i metadati dell'immagine
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]  # Dati binari dell'immagine
        image_ext = base_image["ext"]      # Estensione del formato (jpeg, png, ecc.)
        
        # Salva l'immagine su disco
        image_filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
        with open(image_filename, "wb") as img_file:
            img_file.write(image_bytes)
        
        print(f"Estratta: {image_filename} (formato: {image_ext})")

doc.close()
```

**API Key Methods**:
- `pymupdf.open(path)` — apre documento PDF
- `page.get_text()` — estrae testo pagina
- `page.get_images()` — lista immagini (restituisce tuple con xref)
- `doc.extract_image(xref)` — estrae binary data immagine con metadata

**Use Case Storia 2.5**: AC:1 (riconoscimento PDF), AC:3 (gestione immagini base)

**Reference**: https://pymupdf.readthedocs.io/en/latest/recipes-images.html

---

### 2. Advanced: Caption Detection via Spatial Analysis

Pattern avanzato per identificare didascalie immagini tramite proximity-based analysis.

```python
import pymupdf  # PyMuPDF (fitz)

def estrai_immagini_con_didascalie(pdf_path):
    """
    Estrae immagini e cerca potenziali didascalie basandosi sulla prossimità spaziale.
    """
    doc = pymupdf.open(pdf_path)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Estrai contenuto strutturato della pagina
        page_dict = page.get_text("dict")
        
        print(f"\n=== Pagina {page_num + 1} ===")
        
        # Itera sui blocchi della pagina
        for block in page_dict["blocks"]:
            # Blocco immagine (type=1)
            if block["type"] == 1:
                bbox = block["bbox"]  # (x0, y0, x1, y1)
                
                print(f"\nImmagine trovata:")
                print(f"  Posizione: x0={bbox[0]:.1f}, y0={bbox[1]:.1f}, "
                      f"x1={bbox[2]:.1f}, y1={bbox[3]:.1f}")
                
                # Cerca didascalia nelle immediate vicinanze
                # Strategia: cerca testo nel range verticale sotto l'immagine
                didascalia = cerca_didascalia_vicina(
                    page_dict["blocks"], 
                    bbox,
                    distanza_max=50  # pixel sotto l'immagine
                )
                
                if didascalia:
                    print(f"  Didascalia trovata: '{didascalia}'")
                else:
                    print("  Nessuna didascalia trovata nelle vicinanze")
                    
    doc.close()

def cerca_didascalia_vicina(blocks, image_bbox, distanza_max=50):
    """
    Cerca blocchi di testo immediatamente sotto l'immagine.
    
    Args:
        blocks: Lista di blocchi della pagina
        image_bbox: Bounding box dell'immagine (x0, y0, x1, y1)
        distanza_max: Distanza massima in pixel sotto l'immagine
    
    Returns:
        Stringa con il testo della didascalia, o None
    """
    img_x0, img_y0, img_x1, img_y1 = image_bbox
    img_centro_x = (img_x0 + img_x1) / 2
    
    candidati = []
    
    for block in blocks:
        # Considera solo blocchi di testo (type=0)
        if block["type"] != 0:
            continue
        
        text_bbox = block["bbox"]
        text_x0, text_y0, text_x1, text_y1 = text_bbox
        text_centro_x = (text_x0 + text_x1) / 2
        
        # Verifica se il testo è sotto l'immagine
        # e allineato orizzontalmente
        distanza_verticale = text_y0 - img_y1
        distanza_orizzontale = abs(text_centro_x - img_centro_x)
        
        if (0 <= distanza_verticale <= distanza_max and 
            distanza_orizzontale < (img_x1 - img_x0) / 2):
            
            # Estrai il testo completo dal blocco
            testo = ""
            for line in block["lines"]:
                for span in line["spans"]:
                    testo += span["text"] + " "
            
            candidati.append({
                "testo": testo.strip(),
                "distanza": distanza_verticale
            })
    
    # Restituisci il candidato più vicino
    if candidati:
        candidati.sort(key=lambda x: x["distanza"])
        return candidati[0]["testo"]
    
    return None

# Esempio d'uso
estrai_immagini_con_didascalie("documento.pdf")
```

**Pattern Key Concepts**:
- `page.get_text("dict")` — structured output con blocchi tipizzati (type=0 text, type=1 image)
- **Bounding box analysis**: calcolo distanze verticali/orizzontali tra blocchi
- **Proximity heuristics**: testo entro 50px sotto immagine + allineamento orizzontale
- **Candidate ranking**: ordine per distanza minima

**Use Case Storia 2.5**: AC:3 gestione immagini con caption/didascalie

**Reference**: https://pymupdf.readthedocs.io/en/latest/app1.html

---

## Python-docx — DOCX Extraction

### 3. Structured Table Extraction

Pattern extraction tabelle strutturate da DOCX con accesso row/cell.

```python
from docx import Document

# Apri il documento Word
doc_path = "documento.docx"
doc = Document(doc_path)

# Itera su tutte le tabelle presenti nel documento
for table_idx, table in enumerate(doc.tables):
    print(f"\n=== Tabella {table_idx + 1} ===")
    print(f"Dimensioni: {len(table.rows)} righe x {len(table.columns)} colonne\n")
    
    # Ricostruisci la tabella come lista di liste
    table_data = []
    
    # Itera su ogni riga della tabella
    for row_idx, row in enumerate(table.rows):
        row_data = []
        
        # Itera su ogni cella della riga
        for cell_idx, cell in enumerate(row.cells):
            # Estrai il testo dalla cella
            cell_text = cell.text.strip()
            row_data.append(cell_text)
        
        # Aggiungi la riga alla struttura dati
        table_data.append(row_data)
        print(f"Riga {row_idx + 1}: {row_data}")
    
    # table_data ora contiene la tabella completa come lista di liste
    # Esempio: [['Header1', 'Header2'], ['Valore1', 'Valore2'], ...]

# Esempio alternativo: accesso diretto a una cella specifica
if len(doc.tables) > 0:
    first_table = doc.tables[0]
    # Accedi alla cella alla riga 0, colonna 1
    cell = first_table.cell(0, 1)
    print(f"\nCella (0,1): {cell.text}")
    
    # Accesso tramite rows
    first_row = first_table.rows[0]
    for idx, cell in enumerate(first_row.cells):
        print(f"Colonna {idx}: {cell.text}")
```

**API Key Methods**:
- `doc.tables` — lista tabelle nel documento
- `table.rows` — lista righe tabella
- `row.cells` — lista celle riga
- `cell.text` — testo cella
- `table.cell(row_idx, col_idx)` — accesso diretto cella

**Pattern Structured Data**:
```python
# Conversione tabella → lista dizionari con headers
headers = table_data[0]  # Prima riga come headers
rows = table_data[1:]    # Righe dati

structured_data = [
    {headers[i]: row[i] for i in range(len(headers))}
    for row in rows
]
```

**Use Case Storia 2.5**: AC:4 gestione tabelle DOCX

**Reference**: https://python-docx.readthedocs.io/en/latest/user/tables.html

---

### 4. Image Extraction via Relationships

Pattern extraction immagini embedded in DOCX via navigazione relationships.

```python
from docx import Document
from docx.parts.image import ImagePart
import os

# Apri il documento Word
doc_path = "documento.docx"
doc = Document(doc_path)

# Directory per salvare le immagini estratte
output_dir = "immagini_estratte"
os.makedirs(output_dir, exist_ok=True)

# Dizionario per mappare rId alle immagini
# Estrai tutte le relazioni che puntano a immagini
rels = {}
for r in doc.part.rels.values():
    # Verifica se la relazione punta a una parte immagine
    if isinstance(r._target, ImagePart):
        # Mappa il relationship ID al nome del file immagine
        rels[r.rId] = os.path.basename(r._target.partname)

print(f"Trovate {len(rels)} immagini nel documento\n")

# Estrai e salva le immagini
for idx, (rId, image_filename) in enumerate(rels.items()):
    # Ottieni la parte immagine tramite il relationship ID
    image_part = doc.part.rels[rId]._target
    
    # Accedi ai dati binari dell'immagine
    image_blob = image_part.blob
    
    # Determina l'estensione del file dall'immagine stessa
    # image_part.partname esempio: '/word/media/image1.jpeg'
    ext = os.path.splitext(image_part.partname)[1]
    
    # Salva l'immagine
    output_filename = os.path.join(output_dir, f"immagine_{idx + 1}{ext}")
    with open(output_filename, "wb") as img_file:
        img_file.write(image_blob)
    
    print(f"Salvata: {output_filename}")
    print(f"  - rId: {rId}")
    print(f"  - Nome originale: {image_filename}")
    print(f"  - Dimensione: {len(image_blob)} bytes\n")

# Esempio avanzato: correlazione immagini con i paragrafi
print("=== Correlazione immagini con posizioni nel documento ===\n")
for para in doc.paragraphs:
    # Verifica se il paragrafo contiene un'immagine
    if 'Graphic' in para._p.xml:
        # Estrai il rId dall'XML del paragrafo
        for rId in rels:
            if rId in para._p.xml:
                print(f"Immagine trovata nel paragrafo: {rels[rId]}")
                print(f"  - Relationship ID: {rId}")
                break
```

**API Key Methods**:
- `doc.part.rels` — relationships documento (navigazione internal structure)
- `ImagePart` — type check per relazioni immagini
- `image_part.blob` — binary data immagine
- `image_part.partname` — path interno immagine (es. `/word/media/image1.jpeg`)

**Pattern Advanced**: correlazione immagini-paragrafi via XML inspection (`para._p.xml`)

**Use Case Storia 2.5**: AC:3 gestione immagini DOCX

**Reference**: https://python-docx.readthedocs.io/en/latest/api/document.html

---

## pdfplumber — Advanced Table Extraction (Optional)

### 5. Structured Table Extraction with Configuration

Pattern extraction tabelle complesse da PDF con configurazione granulare.

```python
import pdfplumber

# Apri il documento PDF
pdf_path = "documento.pdf"

with pdfplumber.open(pdf_path) as pdf:
    # Itera su tutte le pagine
    for page_num, page in enumerate(pdf.pages):
        print(f"\n=== Pagina {page_num + 1} ===")
        
        # Estrai tutte le tabelle dalla pagina
        # Ogni tabella è una lista di liste: [riga1, riga2, ...]
        # Ogni riga è una lista di celle: [cella1, cella2, ...]
        tables = page.extract_tables()
        
        if not tables:
            print("Nessuna tabella trovata su questa pagina")
            continue
        
        print(f"Trovate {len(tables)} tabelle\n")
        
        # Itera su ogni tabella trovata
        for table_idx, table in enumerate(tables):
            print(f"--- Tabella {table_idx + 1} ---")
            print(f"Dimensioni: {len(table)} righe x {len(table[0]) if table else 0} colonne")
            
            # Itera su ogni riga della tabella
            for row_idx, row in enumerate(table):
                # Ogni riga è una lista di celle
                print(f"Riga {row_idx + 1}: {row}")
            
            print()  # Riga vuota tra tabelle

# Esempio avanzato: estrazione con configurazione personalizzata
print("\n=== Estrazione con Configurazione Personalizzata ===\n")

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    
    # Configura i parametri di estrazione
    table_settings = {
        "vertical_strategy": "lines",    # Usa linee verticali per delimitare colonne
        "horizontal_strategy": "lines",  # Usa linee orizzontali per delimitare righe
        "snap_tolerance": 3,             # Tolleranza per allineamento linee
        "intersection_tolerance": 3      # Tolleranza per intersezioni
    }
    
    # Estrai tabelle con configurazione personalizzata
    tables = page.extract_tables(table_settings=table_settings)
    
    # Converti in struttura più utilizzabile (es. lista di dizionari)
    if tables:
        for table in tables:
            # Assumi prima riga come header
            headers = table[0]
            rows = table[1:]
            
            # Converti in lista di dizionari
            structured_data = []
            for row in rows:
                row_dict = {headers[i]: row[i] for i in range(len(headers))}
                structured_data.append(row_dict)
            
            print("Dati strutturati:")
            for item in structured_data:
                print(item)

# Esempio con crop per isolare una specifica area
print("\n=== Estrazione da Area Specifica (Crop) ===\n")

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    
    # Definisci bounding box (x0, top, x1, bottom) dell'area di interesse
    bbox = (50, 100, 550, 400)  # Esempio: area centrale della pagina
    
    # Ritaglia la pagina all'area di interesse
    cropped_page = page.crop(bbox)
    
    # Estrai tabelle solo dall'area ritagliata
    tables = cropped_page.extract_tables()
    
    print(f"Tabelle trovate nell'area ritagliata: {len(tables)}")
    for table in tables:
        for row in table:
            print(row)
```

**API Key Methods**:
- `pdfplumber.open(path)` — apre PDF
- `page.extract_tables(table_settings=...)` — extraction tabelle con configurazione
- `page.crop(bbox)` — crop pagina a bounding box specifica
- **table_settings**: `vertical_strategy`, `horizontal_strategy`, tolerance parameters

**Configuration Strategies**:
- `"lines"` — usa linee grafiche per delimitare celle
- `"text"` — usa spacing testo
- `"explicit"` — coordinate manuali

**Use Case Storia 2.5**: troubleshooting tabelle complesse PDF, alternative PyMuPDF, Phase 2 enhancement

**Reference**: https://github.com/jsvine/pdfplumber

---

## Tenacity — Robust Retry Patterns

### 6. Exponential Backoff for API Calls

Pattern retry robusto per chiamate API con backoff esponenziale.

```python
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential, 
    retry_if_exception_type
)
import openai
from openai import RateLimitError, APIError

# Inizializza il client OpenAI
client = openai.OpenAI(api_key="your-api-key")

@retry(
    # Condizione: riprova solo su errori specifici (rate limit e errori API)
    retry=retry_if_exception_type((RateLimitError, APIError)),
    # Strategia di attesa: backoff esponenziale con moltiplicatore 2
    # min=1 secondo, max=60 secondi tra i tentativi
    wait=wait_exponential(multiplier=2, min=1, max=60),
    # Condizione di stop: massimo 5 tentativi
    stop=stop_after_attempt(5)
)
def chiamata_openai_robusta(prompt: str) -> str:
    """
    Effettua una chiamata all'API di OpenAI con retry automatico.
    Gestisce RateLimitError e APIError con backoff esponenziale.
    """
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# Esempio d'uso
try:
    risultato = chiamata_openai_robusta("Analizza questo testo medico...")
    print(f"Risposta ricevuta: {risultato}")
except RateLimitError:
    print("Rate limit superato anche dopo i retry")
except APIError as e:
    print(f"Errore API persistente: {e}")
```

**Tenacity Key Concepts**:
- `@retry()` — decoratore main per retry logic
- `retry_if_exception_type()` — condizioni retry selective
- `wait_exponential(multiplier, min, max)` — backoff esponenziale: wait = multiplier * (2 ** attempt_number), clamped a [min, max]
- `stop_after_attempt(n)` — max tentativi

**Backoff Progression** (multiplier=2, min=1, max=60):
- Attempt 1: immediate
- Attempt 2: wait 2s
- Attempt 3: wait 4s
- Attempt 4: wait 8s
- Attempt 5: wait 16s
- Total: 5 attempts over ~30s

**Use Case Storia 2.5**: AC:6 batch embedding con retry logic per RateLimitError/APIConnectionError

**Reference**: https://tenacity.readthedocs.io/

---

## Integration with Story 2.5

### DocumentExtractor Class Pattern

Implementazione modulo `/apps/api/api/knowledge_base/extractors.py`:

```python
from pathlib import Path
from typing import Dict, Any, List
from enum import Enum
import pymupdf
from docx import Document
from docx.parts.image import ImagePart

class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    UNSUPPORTED = "unsupported"

class DocumentExtractor:
    """Unified document extraction with image/table support."""
    
    def extract(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract text, images, tables from document.
        
        Returns:
            {
                "text": str,
                "images": List[ImageMetadata],
                "tables": List[TableData],
                "metadata": Dict[str, Any]
            }
        """
        file_type = self._detect_file_type(file_path)
        
        if file_type == FileType.PDF:
            return self._extract_pdf(file_path)
        elif file_type == FileType.DOCX:
            return self._extract_docx(file_path)
        elif file_type == FileType.TXT:
            return self._extract_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
    
    def _extract_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Extract from PDF with PyMuPDF (pattern da sezione 1 & 2)."""
        # Implementazione: usa page.get_images() + extract_image()
        # + caption detection con page.get_text("dict")
        pass
    
    def _extract_docx(self, file_path: Path) -> Dict[str, Any]:
        """Extract from DOCX with python-docx (pattern da sezione 3 & 4)."""
        # Implementazione: usa doc.tables per tabelle
        # + doc.part.rels per immagini
        pass
```

### Batch Embedding with Retry Pattern

Implementazione modulo `/apps/api/api/knowledge_base/indexer.py`:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai

@retry(
    retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
)
def _embed_texts_with_retry(texts: List[str], embeddings_model: OpenAIEmbeddings) -> List[List[float]]:
    """
    Batch embedding with exponential backoff retry.
    
    Pattern da sezione 6 (tenacity).
    """
    logger.info(f"Embedding {len(texts)} texts (attempt with retry)")
    
    # Batch size optimization: OpenAI recommends < 2048 texts per batch
    BATCH_SIZE = 100
    all_embeddings = []
    
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        batch_embeddings = embeddings_model.embed_documents(batch)
        all_embeddings.extend(batch_embeddings)
        
        logger.info(f"Embedded batch {i//BATCH_SIZE + 1}/{(len(texts)-1)//BATCH_SIZE + 1}")
    
    return all_embeddings
```

---

## Dependencies

### Installation

```bash
# Backend (apps/api)
cd apps/api
poetry add pymupdf tenacity

# Optional: advanced table extraction
poetry add --group dev pdfplumber
```

### pyproject.toml Updates

```toml
[tool.poetry.dependencies]
pymupdf = "^1.23.0"  # PyMuPDF (fitz)
tenacity = "^8.2.0"   # Retry logic robusto

[tool.poetry.group.dev.dependencies]
pdfplumber = "^0.10.0"  # Optional: table extraction avanzata
```

---

## Testing Patterns

### Unit Test: PyMuPDF Image Extraction

```python
# apps/api/tests/test_pymupdf_extraction.py
def test_extract_images_from_pdf(tmp_path):
    # Setup: crea PDF test con immagine embedded
    pdf_path = tmp_path / "test.pdf"
    # ... (mock PDF con immagine)
    
    # Execute
    extractor = DocumentExtractor()
    result = extractor._extract_pdf(pdf_path)
    
    # Assert
    assert len(result["images"]) > 0
    assert result["images"][0]["format"] in ["jpeg", "png"]
    assert result["images"][0]["size_bytes"] > 0
```

### Unit Test: Tenacity Retry Logic

```python
# apps/api/tests/test_retry_logic.py
from unittest.mock import Mock, patch
import openai

def test_embed_texts_retry_on_rate_limit():
    # Setup: mock OpenAI client che fallisce 2 volte poi succeed
    mock_embeddings = Mock()
    mock_embeddings.embed_documents.side_effect = [
        openai.RateLimitError("Rate limit exceeded"),
        openai.RateLimitError("Rate limit exceeded"),
        [[0.1, 0.2, 0.3]]  # Success al terzo tentativo
    ]
    
    # Execute
    result = _embed_texts_with_retry(["test text"], mock_embeddings)
    
    # Assert
    assert len(result) == 1
    assert mock_embeddings.embed_documents.call_count == 3
```

---

## Troubleshooting

### Issue: PyMuPDF caption detection restituisce None

**Causa**: immagine non ha testo nelle immediate vicinanze (50px default)

**Soluzione**: aumenta `distanza_max` parameter in `cerca_didascalia_vicina()` oppure usa OCR per caption recognition

### Issue: python-docx ImagePart non trova immagini

**Causa**: immagini inline vs floating (solo inline supportate da pattern relationships)

**Soluzione**: verifica con `para._p.xml` per immagini floating, usa XML parsing avanzato

### Issue: pdfplumber extract_tables() restituisce liste vuote

**Causa**: PDF usa immagini di tabelle invece di tabelle strutturate

**Soluzione**: usa OCR-based table extraction (Tesseract + table detection) oppure fallback a layout analysis

### Issue: tenacity non riprova su APIConnectionError

**Causa**: exception type mismatch (subclass non coperta)

**Soluzione**: verifica `retry_if_exception_type` include parent class `Exception` oppure add specific subclasses

---

## References

### Official Documentation
- **PyMuPDF**: https://pymupdf.readthedocs.io/
  - Recipes: https://pymupdf.readthedocs.io/en/latest/recipes-images.html
  - App1 (structured text): https://pymupdf.readthedocs.io/en/latest/app1.html
- **tenacity**: https://tenacity.readthedocs.io/
- **python-docx**: https://python-docx.readthedocs.io/
  - Tables: https://python-docx.readthedocs.io/en/latest/user/tables.html
  - API: https://python-docx.readthedocs.io/en/latest/api/document.html
- **pdfplumber**: https://github.com/jsvine/pdfplumber

### Related Addenda
- [Addendum: LangChain Loaders & Splitters](addendum-langchain-loaders-splitters.md) - PyPDFLoader, Docx2txtLoader (Story 2.1)
- [Addendum: HNSW & Async](addendum-hnsw-params-and-async.md) - Celery retry patterns (Story 2.4)
- [Ingestion Pipelines Comparison](ingestion-pipelines-comparison.md) - Confronto pipeline Watcher automatica vs API Sync Jobs (Story 6.1)

### Target Story
- [Story 2.5: Intelligent Document Preprocessing](../stories/2.5.intelligent-document-preprocessing.md)

---

**Last Updated**: 2025-10-07  
**Author**: Architect (integration materiale fonti ufficiali)  
**Status**: Ready for Implementation


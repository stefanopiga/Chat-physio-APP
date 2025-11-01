# Addendum: Integrazione LangChain (Loaders & Text Splitters)

## Caricamento PDF con PyPDFLoader
Fonte: `https://raw.githubusercontent.com/langchain-ai/langchain/master/docs/docs/integrations/document_loaders/pypdfloader.ipynb`

- PyPI: `langchain-community`, dipendenza: `pypdf`.
- API: `from langchain_community.document_loaders import PyPDFLoader`
- Modalità: `mode="page"` oppure `mode="single"`, opzionale `pages_delimiter` in single-mode.
- Lazy loading: `loader.lazy_load()` restituisce iteratore di `Document`.

```python
# Installazione (se necessario)
# %pip install -qU langchain-community pypdf

from langchain_community.document_loaders import PyPDFLoader

file_path = "./example_data/layout-parser-paper.pdf"
# Caricamento predefinito (single text flow)
loader = PyPDFLoader(file_path)
docs = loader.load()

# Per split per pagina
loader = PyPDFLoader(file_path, mode="page")
docs_by_page = loader.load()

# Single-mode con delimitatore di pagina personalizzato
loader = PyPDFLoader(
    file_path,
    mode="single",
    pages_delimiter="\n-------THIS IS A CUSTOM END OF PAGE-------\n",
)
single_doc = loader.load()

# Lazy load per processare page-by-page
pages = []
for d in loader.lazy_load():
    pages.append(d)
    if len(pages) >= 10:
        # process batch di 10 pagine
        pages = []
```

## Caricamento DOCX
Fonte: `https://raw.githubusercontent.com/langchain-ai/langchain/master/docs/docs/integrations/document_loaders/microsoft_word.ipynb`

- Docx2txt:
  - API: `from langchain_community.document_loaders import Docx2txtLoader`
  - Dipendenza: `docx2txt`
- Unstructured Word:
  - API: `from langchain_community.document_loaders import UnstructuredWordDocumentLoader`
  - Modalità elementi: `mode="elements"` per conservare gli elementi.

```python
# Docx2txtLoader
# %pip install --quiet --upgrade docx2txt
from langchain_community.document_loaders import Docx2txtLoader

docx_loader = Docx2txtLoader("./example_data/fake.docx")
docx_docs = docx_loader.load()

# UnstructuredWordDocumentLoader
from langchain_community.document_loaders import UnstructuredWordDocumentLoader

unstructured_loader = UnstructuredWordDocumentLoader("./example_data/fake.docx")
unstructured_docs = unstructured_loader.load()

# Conservare elementi con metadati dettagliati
unstructured_elements_loader = UnstructuredWordDocumentLoader(
    "./example_data/fake.docx",
    mode="elements",
)
element_docs = unstructured_elements_loader.load()
```

## Suddivisione Testo con RecursiveCharacterTextSplitter
Fonte: `https://raw.githubusercontent.com/langchain-ai/langchain/master/docs/docs/how_to/recursive_text_splitter.ipynb`

- API: `from langchain_text_splitters import RecursiveCharacterTextSplitter`
- Parametri principali: `chunk_size`, `chunk_overlap`, `length_function`, `is_separator_regex`, opzionale `separators=[...]`.
- Metodi: `create_documents([...])` produce `Document`, `split_text(str)` produce `List[str]`.

```python
# %pip install -qU langchain-text-splitters
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    is_separator_regex=False,  # default
)

# Esempio su stringa
long_text = "..."  # testo lungo
chunks = text_splitter.split_text(long_text)

# Esempio su Document(s)
docs = [...]  # lista di langchain_core.documents.Document
chunked_docs = text_splitter.create_documents([d.page_content for d in docs])

# Esempio con separatori per lingue senza spazi (CJK/Thai)
text_splitter_cjk = RecursiveCharacterTextSplitter(
    separators=[
        "\n\n", "\n", " ", ".", ",", "\u200b", "\uff0c", "\u3001", "\uff0e", "\u3002", ""
    ],
    chunk_size=1000,
    chunk_overlap=200,
)
```

## Esempio di Pipeline Completa
Fonti:
- PyPDFLoader: `pypdfloader.ipynb` (vedi sopra)
- RecursiveCharacterTextSplitter: `recursive_text_splitter.ipynb` (vedi sopra)
- DOCX loader: `microsoft_word.ipynb` (vedi sopra)

```python
# Pipeline: carica un file (PDF o DOCX) e splitta in chunk

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_documents(file_path: str):
    if file_path.lower().endswith(".pdf"):
        loader = PyPDFLoader(file_path, mode="page")  # o "single"
        return loader.load()
    elif file_path.lower().endswith(".docx"):
        loader = Docx2txtLoader(file_path)
        return loader.load()
    else:
        raise ValueError("Formato non supportato. Usa .pdf o .docx")

def split_documents(docs, chunk_size=1000, chunk_overlap=200):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    # Converte lista di Document in lista di Document chunked preservando metadati base
    texts = [d.page_content for d in docs]
    chunked = splitter.create_documents(texts)
    return chunked

# Uso
file_path = "./example_data/layout-parser-paper.pdf"  # oppure "./example_data/fake.docx"
docs = load_documents(file_path)
chunks = split_documents(docs, chunk_size=1000, chunk_overlap=200)

# chunks: lista di Document pronti per embedding/indicizzazione
```

### Dipendenze minime
- PDF: `langchain-community`, `pypdf`
- DOCX: `langchain-community`, `docx2txt`
- Splitter: `langchain-text-splitters`

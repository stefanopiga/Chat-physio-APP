# Addendum: LangChain RAG Debug Patterns

**Status**: Active  
**Version**: 1.0  
**Date**: 2025-09-30

## Context

Documento creato per Story 4.1 (Admin Debug View) con pattern implementativi per accesso a risultati intermedi in catena RAG usando LangChain Expression Language (LCEL).

**Problemi Risolti**:
- Accesso a chunk recuperati con similarity scores
- Separazione timing retrieval vs generation
- Visibilità completa pipeline RAG per debugging

**Applicabilità**: Story 4.1, future implementazioni RAG con visibilità intermedia.

[Fonte: Documentazione ufficiale LangChain; `docs/stories/4.1.admin-debug-view.md`]

---

## 1. Pattern: RunnablePassthrough.assign per Accumulazione Risultati

### Problema

Catena RAG standard restituisce solo risposta finale LLM, perdendo informazioni intermedie (chunk recuperati, scores, context).

### Soluzione: Arricchimento Progressivo con assign()

`RunnablePassthrough.assign()` permette di **accumulare** risultati intermedi in un dizionario senza sovrascrivere dati esistenti.

```python
from langchain_core.runnables import RunnablePassthrough

# Pattern base: accumula chiavi progressive
chain = (
    RunnablePassthrough.assign(step1_result=compute_step1)  # Aggiunge key1
    | RunnablePassthrough.assign(step2_result=compute_step2)  # Aggiunge key2, mantiene key1
    | RunnablePassthrough.assign(step3_result=compute_step3)  # Aggiunge key3, mantiene key1+key2
)

# Input: {"question": "..."}
# Output: {"question": "...", "step1_result": ..., "step2_result": ..., "step3_result": ...}
```

**Chiavi da ricordare**:
- ✅ `assign()` non sostituisce dati esistenti
- ✅ Accesso a chiavi precedenti: `lambda inputs: inputs["key"]`
- ✅ Risultato finale sempre dizionario completo

### Esempio Applicato a RAG

```python
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

rag_chain_with_debug = (
    # Step 1: Recupera documenti
    RunnablePassthrough.assign(
        documents=lambda inputs: retriever_with_scores.invoke(inputs["question"])
    )
    # Step 2: Formatta contesto
    | RunnablePassthrough.assign(
        context=lambda inputs: format_docs(inputs["documents"])
    )
    # Step 3: Genera risposta LLM
    | RunnablePassthrough.assign(
        answer=rag_prompt | llm | StrOutputParser()
    )
)

# Input: {"question": "Come trattare lombalgia?"}
# Output: {
#     "question": "Come trattare lombalgia?",
#     "documents": [Doc1, Doc2, ...],  # Chunk con metadata
#     "context": "...",                 # Testo formattato per LLM
#     "answer": "..."                   # Risposta finale
# }
```

**Vantaggi per Story 4.1**:
- Accesso completo a documents per visualizzazione chunk
- Context preservato per debugging
- Timing metrics separabili per retrieval vs generation

[Fonte: LangChain Docs - How to get your RAG application to return sources]

---

## 2. Retriever con Similarity Scores

### Problema

Retriever standard `.as_retriever()` **non include** similarity scores nei metadata documents.

```python
# ❌ ANTI-PATTERN: scores mancanti
retriever = vectorstore.as_retriever()
docs = retriever.invoke("query")
# docs[0].metadata → NO score disponibile
```

### Soluzione: Wrapper Custom con similarity_search_with_score

Usare metodo diretto del vector store per ottenere tuple `(Document, score)`:

```python
from typing import List
from langchain_core.documents import Document
from langchain_core.runnables import chain

@chain
def retriever_with_scores(query: str) -> List[Document]:
    """
    Retriever custom che arricchisce documents con similarity scores.
    
    Critical per Story 4.1:
    - Restituisce score necessario per AC3 (visualizzazione score)
    - Score usato per ordinamento AC4 (chunk per rilevanza)
    
    Args:
        query: Query di ricerca
        
    Returns:
        Lista Document con metadata["score"] popolato
    """
    # similarity_search_with_score → List[Tuple[Document, float]]
    docs_with_scores = vectorstore.similarity_search_with_score(
        query,
        k=8  # Top 8 chunk più rilevanti
    )
    
    # Arricchisci metadata con score
    enriched_docs = []
    for doc, score in docs_with_scores:
        # CRITICAL: aggiunta score a metadata
        doc.metadata["score"] = float(score)
        enriched_docs.append(doc)
    
    return enriched_docs
```

### Dove si Trova lo Score

Dopo arricchimento, score accessibile in:

```python
doc.metadata["score"]  # Float, range tipico 0.0-1.0
```

**Note importanti**:
- Score rappresenta **similarità coseno** (0.0 = nessuna similarità, 1.0 = identico)
- pgVector con `<=>` operator: distanza (inversa di similarità)
- Ordinamento: score più alto = più rilevante

**Story 4.1 Requirements Coverage**:
- AC3: Score visualizzato per ogni chunk → `doc.metadata["score"]`
- AC4: Ordinamento chunk per rilevanza → sort by score desc

[Fonte: LangChain Docs - How to add scores to retriever results]

---

## 3. Catena RAG Completa per Debug View

### Setup Componenti

```python
import os
from typing import List, Optional
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, chain
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from supabase import create_client

# ========== Configurazione ==========

# Supabase client (da Settings)
supabase_client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

# Vector store
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = SupabaseVectorStore(
    client=supabase_client,
    embedding=embeddings,
    table_name="document_chunks",
    query_name="match_documents"
)

# LLM
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    api_key=os.environ["OPENAI_API_KEY"]
)
```

### Retriever con Scores (Riutilizzabile)

```python
@chain
def retriever_with_scores(query: str) -> List[Document]:
    """
    Retriever FisioRAG con similarity scores per debug.
    
    Returns:
        Lista Document ordinati per score (desc) con metadata completi:
        - score: float (similarità coseno)
        - document_id: str (FK a documento padre)
        - document_name: str (filename sorgente)
        - page_number: Optional[int]
        - chunking_strategy: str (es. "recursive")
    """
    docs_with_scores = vectorstore.similarity_search_with_score(query, k=8)
    
    enriched_docs = []
    for doc, score in docs_with_scores:
        doc.metadata["score"] = float(score)
        enriched_docs.append(doc)
    
    # Ordinamento per score decrescente (AC4)
    enriched_docs.sort(key=lambda d: d.metadata["score"], reverse=True)
    
    return enriched_docs
```

### Formattazione Contesto per LLM

```python
def format_docs(documents: List[Document]) -> str:
    """
    Formatta chunk recuperati in contesto testuale per LLM.
    
    Args:
        documents: Lista Document da retriever_with_scores
        
    Returns:
        Stringa formattata con separatori e metadata
    """
    if not documents:
        return "Nessun documento rilevante trovato nella knowledge base."
    
    formatted_parts = []
    for i, doc in enumerate(documents, 1):
        content = doc.page_content.strip()
        doc_name = doc.metadata.get("document_name", "unknown")
        score = doc.metadata.get("score", 0.0)
        
        formatted_parts.append(
            f"[Fonte {i} | File: {doc_name} | Rilevanza: {score:.3f}]\n{content}"
        )
    
    return "\n\n---\n\n".join(formatted_parts)
```

### Catena RAG con Debug Completo

```python
# ========== Prompt Template ==========

rag_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "Sei un assistente esperto in fisioterapia. "
        "Rispondi alla domanda ESCLUSIVAMENTE basandoti sul contesto fornito. "
        "Se l'informazione non è presente, rispondi chiaramente che non è disponibile. "
        "Cita le fonti quando possibile (es. 'Come descritto nella Fonte 1...')."
    ),
    (
        "user",
        "CONTESTO:\n{context}\n\n"
        "DOMANDA: {question}\n\n"
        "RISPOSTA:"
    )
])

# ========== Catena Debug-Enabled ==========

rag_chain_with_debug = (
    # Step 1: Recupera chunk con scores
    RunnablePassthrough.assign(
        documents=lambda inputs: retriever_with_scores.invoke(inputs["question"])
    )
    # Step 2: Formatta contesto per LLM
    | RunnablePassthrough.assign(
        context=lambda inputs: format_docs(inputs["documents"])
    )
    # Step 3: Genera risposta finale
    | RunnablePassthrough.assign(
        answer=rag_prompt | llm | StrOutputParser()
    )
)

# Output structure:
# {
#     "question": str,          # Input originale
#     "documents": List[Doc],   # Chunk con scores e metadata
#     "context": str,           # Contesto formattato (visto da LLM)
#     "answer": str             # Risposta finale LLM
# }
```

**Story 4.1 Coverage**:
- AC3: `documents` contiene chunk + scores + metadata
- AC4: Chunk pre-ordinati per score in `retriever_with_scores`
- AC5: `answer` vs `documents` separati per distinzione visiva

---

## 4. Timing Metrics Separati (R-4.1-8)

### Problema

Timing totale nasconde breakdown retrieval vs generation.

### Soluzione: Timing Incrementale con assign()

```python
import time
from typing import List
from langchain_core.documents import Document
from langchain_core.runnables import RunnablePassthrough

def timed_retrieval(query: str) -> dict:
    """
    Wrapper retriever con timing dedicato.
    
    Returns:
        dict con keys: documents, retrieval_time_ms
    """
    start = time.perf_counter()
    documents = retriever_with_scores.invoke(query)
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    return {
        "documents": documents,
        "retrieval_time_ms": elapsed_ms
    }


def timed_generation(inputs: dict) -> dict:
    """
    Wrapper generation con timing dedicato.
    
    Args:
        inputs: dict con keys question, context
        
    Returns:
        dict con keys: answer, generation_time_ms
    """
    start = time.perf_counter()
    answer = (rag_prompt | llm | StrOutputParser()).invoke(inputs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    return {
        "answer": answer,
        "generation_time_ms": elapsed_ms
    }


# ========== Catena con Timing Separato ==========

rag_chain_with_timing = (
    # Step 1: Retrieval + timing
    RunnablePassthrough.assign(
        retrieval_result=lambda inputs: timed_retrieval(inputs["question"])
    )
    # Step 2: Estrai documents da result
    | RunnablePassthrough.assign(
        documents=lambda inputs: inputs["retrieval_result"]["documents"],
        retrieval_time_ms=lambda inputs: inputs["retrieval_result"]["retrieval_time_ms"]
    )
    # Step 3: Formatta context
    | RunnablePassthrough.assign(
        context=lambda inputs: format_docs(inputs["documents"])
    )
    # Step 4: Generation + timing
    | RunnablePassthrough.assign(
        generation_result=lambda inputs: timed_generation(inputs)
    )
    # Step 5: Estrai answer da result
    | RunnablePassthrough.assign(
        answer=lambda inputs: inputs["generation_result"]["answer"],
        generation_time_ms=lambda inputs: inputs["generation_result"]["generation_time_ms"]
    )
)

# Output:
# {
#     "question": str,
#     "documents": List[Doc],
#     "context": str,
#     "answer": str,
#     "retrieval_time_ms": float,    # Timing separato retrieval
#     "generation_time_ms": float     # Timing separato generation
# }
```

**Vantaggi per R-4.1-8**:
- Timing metrics separati per diagnostica performance
- Accuracy ±10ms verificabile (use `time.perf_counter()`)
- Visibility su bottleneck (retrieval vs generation)

**Testing Requirements (TC-094)**:
- Mock retrieval sleep(0.1) → verifica ~100ms ±10
- Mock generation sleep(0.5) → verifica ~500ms ±10

[Fonte: `docs/qa/assessments/4.1-test-design-20250930.md` TC-094]

---

## 5. Integrazione FastAPI Endpoint Debug

### Modelli Pydantic per Story 4.1

```python
from pydantic import BaseModel, Field
from typing import List, Optional

# ========== Request Model ==========

class DebugQueryRequest(BaseModel):
    """Request per admin debug query."""
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Domanda di test per debug RAG"
    )


# ========== Response Models ==========

class ChunkMetadata(BaseModel):
    """Metadata chunk con validazione."""
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    chunking_strategy: str


class DebugChunk(BaseModel):
    """Chunk con similarity score per debug view."""
    chunk_id: str
    content: str = Field(..., max_length=5000)
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    metadata: ChunkMetadata


class DebugQueryResponse(BaseModel):
    """Response completa debug query."""
    question: str
    answer: str
    chunks: List[DebugChunk]
    retrieval_time_ms: float = Field(..., ge=0.0)
    generation_time_ms: float = Field(..., ge=0.0)
```

### Endpoint Implementation

```python
from typing import Annotated
from fastapi import Depends, HTTPException, status
import time

@app.post("/api/v1/admin/debug/query", response_model=DebugQueryResponse)
async def admin_debug_query(
    body: DebugQueryRequest,
    payload: Annotated[dict, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)]
) -> DebugQueryResponse:
    """
    Admin debug endpoint con visibilità completa pipeline RAG.
    
    Features:
    - Restituisce chunk recuperati con scores
    - Timing separato retrieval vs generation
    - Metadata completi per analisi
    
    Security:
    - Admin-only (JWT + role check)
    - Audit logging (R-4.1-2)
    - Rate limiting (R-4.1-3)
    """
    # Auth check
    if not _is_admin(payload):
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Audit log
    admin_id = payload.get("sub")
    logger.info({
        "event": "admin_debug_query",
        "admin_id": admin_id,
        "question_hash": hashlib.sha256(body.question.encode()).hexdigest()[:16]
    })
    
    try:
        # Invoke catena con timing separato
        result = await rag_chain_with_timing.ainvoke({"question": body.question})
        
        # Estrai componenti
        documents = result["documents"]
        answer = result["answer"]
        retrieval_time = result["retrieval_time_ms"]
        generation_time = result["generation_time_ms"]
        
        # Costruisci response
        chunks = []
        for doc in documents:
            chunk = DebugChunk(
                chunk_id=doc.metadata.get("id", "unknown"),
                content=doc.page_content,
                similarity_score=doc.metadata.get("score", 0.0),
                metadata=ChunkMetadata(
                    document_id=doc.metadata.get("document_id", "unknown"),
                    document_name=doc.metadata.get("document_name", "unknown"),
                    page_number=doc.metadata.get("page_number"),
                    chunking_strategy=doc.metadata.get("chunking_strategy", "unknown")
                )
            )
            chunks.append(chunk)
        
        return DebugQueryResponse(
            question=body.question,
            answer=answer,
            chunks=chunks,
            retrieval_time_ms=retrieval_time,
            generation_time_ms=generation_time
        )
        
    except Exception as e:
        logger.error(f"Debug query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"RAG processing failed: {str(e)}"
        ) from e
```

**Checklist Implementation**:
- ✅ Admin auth check (`_is_admin`)
- ✅ Audit logging con PII sanitization
- ✅ Pydantic validation request/response
- ✅ Error handling robusto
- ✅ Async endpoint (`.ainvoke()`)
- ✅ Timing metrics separati

[Fonte: `docs/architecture/addendum-fastapi-best-practices.md`]

---

## 6. Testing Patterns per RAG Debug

### Mock Retriever per Unit Tests

```python
import pytest
from langchain_core.documents import Document

@pytest.fixture
def mock_retriever_with_scores():
    """Mock retriever con scores predefiniti."""
    def _mock_retriever(query: str) -> List[Document]:
        # Simula 3 chunk con scores decrescenti
        return [
            Document(
                page_content="Contenuto chunk 1...",
                metadata={
                    "id": "chunk_1",
                    "document_id": "doc_123",
                    "document_name": "test.pdf",
                    "page_number": 5,
                    "chunking_strategy": "recursive",
                    "score": 0.95
                }
            ),
            Document(
                page_content="Contenuto chunk 2...",
                metadata={
                    "id": "chunk_2",
                    "document_id": "doc_123",
                    "document_name": "test.pdf",
                    "page_number": 7,
                    "chunking_strategy": "recursive",
                    "score": 0.87
                }
            ),
            Document(
                page_content="Contenuto chunk 3...",
                metadata={
                    "id": "chunk_3",
                    "document_id": "doc_456",
                    "document_name": "test2.pdf",
                    "page_number": 2,
                    "chunking_strategy": "recursive",
                    "score": 0.72
                }
            )
        ]
    return _mock_retriever


def test_retriever_returns_scores(mock_retriever_with_scores):
    """TC: Retriever include scores in metadata."""
    docs = mock_retriever_with_scores("test query")
    
    assert len(docs) == 3
    assert all("score" in doc.metadata for doc in docs)
    assert docs[0].metadata["score"] == 0.95


def test_chunks_ordered_by_score_descending(mock_retriever_with_scores):
    """AC4: Chunk ordinati per score decrescente."""
    docs = mock_retriever_with_scores("test query")
    
    scores = [doc.metadata["score"] for doc in docs]
    assert scores == sorted(scores, reverse=True)
```

### Integration Test Catena Completa

```python
@pytest.mark.asyncio
async def test_rag_chain_returns_all_components(
    mock_retriever_with_scores,
    mock_llm
):
    """BI-001: End-to-end flow con mock components."""
    # Override dependencies
    app.dependency_overrides[retriever_with_scores] = mock_retriever_with_scores
    app.dependency_overrides[llm] = mock_llm
    
    # Invoke chain
    result = await rag_chain_with_timing.ainvoke({
        "question": "Test query"
    })
    
    # Verify structure
    assert "question" in result
    assert "documents" in result
    assert "context" in result
    assert "answer" in result
    assert "retrieval_time_ms" in result
    assert "generation_time_ms" in result
    
    # Verify content
    assert len(result["documents"]) == 3
    assert result["retrieval_time_ms"] > 0
    assert result["generation_time_ms"] > 0
```

---

## 7. Pattern Riassuntivo

### Architettura Pipeline Debug

```
Input: {"question": "..."}
    ↓
[RunnablePassthrough.assign(documents=retriever_with_scores)]
    ↓ Timing Point 1
{"question": "...", "documents": [Doc(score=0.95), ...], "retrieval_time_ms": 150}
    ↓
[RunnablePassthrough.assign(context=format_docs)]
    ↓
{"question": "...", "documents": [...], "context": "...", "retrieval_time_ms": 150}
    ↓ Timing Point 2
[RunnablePassthrough.assign(answer=rag_prompt | llm)]
    ↓
Output: {
    "question": "...",
    "documents": [Doc(score=0.95), Doc(score=0.87), ...],
    "context": "...",
    "answer": "...",
    "retrieval_time_ms": 150,
    "generation_time_ms": 2300
}
```

### Checklist Implementazione Story 4.1

**Retrieval**:
- ✅ Custom retriever con `@chain` decorator
- ✅ `similarity_search_with_score()` per scores
- ✅ Score aggiunto a `doc.metadata["score"]`
- ✅ Ordinamento chunk per score desc

**Pipeline**:
- ✅ `RunnablePassthrough.assign()` per accumulo risultati
- ✅ Documents preservati (non solo context)
- ✅ Timing separato retrieval vs generation

**API Integration**:
- ✅ Pydantic models per request/response
- ✅ Admin auth + role check
- ✅ Async endpoint (`.ainvoke()`)
- ✅ Error handling + audit logging

**Testing**:
- ✅ Mock retriever con scores predefiniti
- ✅ Verifica ordinamento chunk
- ✅ Verifica timing accuracy (±10ms)

---

## Risorse Ufficiali

### LangChain Documentation

1. **How to get your RAG application to return sources**
   - URL: https://python.langchain.com/docs/how_to/qa_sources/
   - Propagazione documenti fonte attraverso catena RAG

2. **How to add scores to retriever results**
   - URL: https://python.langchain.com/docs/how_to/add_scores_retriever/
   - Aggiunta similarity scores a metadata

3. **RunnablePassthrough API Reference**
   - URL: https://python.langchain.com/api_reference/core/runnables/langchain_core.runnables.passthrough.RunnablePassthrough.html
   - Documentazione `.assign()` e composizione

4. **Build a Retrieval Augmented Generation (RAG) App**
   - URL: https://python.langchain.com/docs/tutorials/rag/
   - Tutorial completo RAG con LCEL

5. **LangChain Expression Language (LCEL) Concepts**
   - URL: https://python.langchain.com/docs/concepts/lcel/
   - Guida concettuale LCEL

### Community

6. **Stack Overflow: Return source documents with LCEL**
   - URL: https://stackoverflow.com/questions/77759685/
   - Esempi pratici community-verified

---

## References

- **Story**: `docs/stories/4.1.admin-debug-view.md`
- **Risk Profile**: `docs/qa/assessments/4.1-risk-20250930.md` (R-4.1-8: Timing Metrics)
- **Test Design**: `docs/qa/assessments/4.1-test-design-20250930.md` (TC-094: Timing Accuracy)
- **FastAPI Patterns**: `docs/architecture/addendum-fastapi-best-practices.md`
- **Existing RAG**: `docs/stories/3.1.semantic-search-endpoint.md`, `docs/stories/3.2.augmented-generation-endpoint.md`

---

**Revision History**:

| Date       | Version | Changes                                      |
|------------|---------|----------------------------------------------|
| 2025-09-30 | 1.0     | Initial version - LangChain RAG debug patterns |

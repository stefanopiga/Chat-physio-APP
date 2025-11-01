# Cross-Encoder Quick Reference

**Document Type**: API Reference  
**Date**: 2025-10-22

---

## Installation

```bash
poetry add sentence-transformers@^2.2.2
```

---

## Basic Usage

```python
from sentence_transformers import CrossEncoder

# Initialize model
model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

# Score single query-document pair
query = "spondilolistesi sintomi"
document = "La spondilolistesi è caratterizzata da..."
score = model.predict([[query, document]])
# → score: 0.92 (float, -∞ to +∞, higher = more relevant)

# Score multiple pairs (batch)
pairs = [
    [query, doc1],
    [query, doc2],
    [query, doc3]
]
scores = model.predict(pairs)
# → scores: [0.92, 0.74, 0.45]
```

---

## Model Comparison

| Model | Size | Speed (20 pairs) | Accuracy |
|-------|------|------------------|----------|
| `ms-marco-TinyBERT-L-2-v2` | 15MB | 80ms | Good |
| `ms-marco-MiniLM-L-6-v2` | 80MB | 200ms | **Best** ✅ |
| `ms-marco-MiniLM-L-12-v2` | 120MB | 350ms | Excellent |

---

## Common Patterns

### Pattern 1: Re-rank Search Results

```python
# Initial search results from vector DB
initial_results = [
    {"id": "1", "content": "...", "score": 0.78},
    {"id": "2", "content": "...", "score": 0.75},
    # ...
]

# Re-rank with cross-encoder
query = "user query"
pairs = [[query, r["content"]] for r in initial_results]
rerank_scores = model.predict(pairs)

# Update scores and re-sort
for result, score in zip(initial_results, rerank_scores):
    result["rerank_score"] = float(score)

reranked = sorted(initial_results, key=lambda x: x["rerank_score"], reverse=True)
```

### Pattern 2: Top-K Selection

```python
# Keep only top-k after re-ranking
top_k = 5
top_results = reranked[:top_k]
```

### Pattern 3: Threshold Filtering

```python
# Filter by minimum relevance score
threshold = 0.6
relevant_results = [r for r in reranked if r["rerank_score"] >= threshold]
```

---

## Performance Tips

### 1. Batch Processing
```python
# ✅ GOOD: Batch all pairs
scores = model.predict(pairs)

# ❌ BAD: Individual predictions
scores = [model.predict([[q, d]])[0] for d in documents]
```

### 2. Lazy Loading
```python
class Retriever:
    def __init__(self):
        self._model = None
    
    @property
    def model(self):
        if self._model is None:
            self._model = CrossEncoder('...')
        return self._model
```

### 3. Content Truncation
```python
# Models have max length (512 tokens typical)
MAX_LENGTH = 512
truncated_content = document[:MAX_LENGTH]
```

---

## Error Handling

```python
try:
    scores = model.predict(pairs)
except Exception as e:
    logger.error(f"Re-ranking failed: {e}")
    # Fallback: use original scores
    scores = [r["original_score"] for r in results]
```

---

## Score Interpretation

- **> 0.8**: Highly relevant
- **0.6 - 0.8**: Relevant
- **0.4 - 0.6**: Moderately relevant
- **< 0.4**: Not relevant

**Note**: Scores are not calibrated probabilities. Use for ranking only.

---

## Resources

- Sentence Transformers: https://www.sbert.net/
- MS MARCO models: https://huggingface.co/cross-encoder
- Paper: https://arxiv.org/abs/1901.04085

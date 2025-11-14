# PostgreSQL Pagination

## LIMIT/OFFSET Problems

**Problema principale:** OFFSET richiede al database di fetchare e scartare tutte le righe precedenti.

**Trade-off OFFSET:**
- ✓ Implementazione semplice
- ✓ Navigazione pagine arbitrarie
- ✗ Performance degrada con offset grandi
- ✗ Risultati "drift" con nuovi insert
- ✗ Costo proporzionale al numero pagina

**SQL Standard:**
```sql
SELECT * FROM sales 
ORDER BY sale_date DESC 
OFFSET 10 ROWS 
FETCH NEXT 10 ROWS ONLY;
```

**PostgreSQL syntax:**
```sql
SELECT * FROM sales 
ORDER BY sale_date DESC 
LIMIT 10 OFFSET 10;
```

---

## Keyset Pagination (Seek Method)

**Vantaggi:**
- ✓ Performance costante (non degrada)
- ✓ Risultati stabili con nuovi insert
- ✓ Usa indici in modo efficiente
- ✗ No navigazione pagine arbitrarie
- ✗ Richiede ordinamento deterministico

**Implementazione base (single column):**
```sql
-- Prima pagina
SELECT * FROM sales 
ORDER BY sale_date DESC 
LIMIT 10;

-- Pagina successiva (assumendo last_seen_date dalla pagina precedente)
SELECT * FROM sales 
WHERE sale_date < ?last_seen_date
ORDER BY sale_date DESC 
LIMIT 10;
```

**Problema:** Se ci sono duplicati in sale_date, si perdono risultati.

---

## Keyset con Ordinamento Deterministico

**Requisito:** ORDER BY deve produrre sequenza univoca.

**Soluzione:** Aggiungere colonne fino a rendere ordinamento univoco (tipicamente PK).

**Indice necessario:**
```sql
CREATE INDEX sales_date_id ON sales (sale_date DESC, sale_id DESC);
```

**Query con Row Values (PostgreSQL, Db2):**
```sql
-- Prima pagina
SELECT * FROM sales 
ORDER BY sale_date DESC, sale_id DESC 
LIMIT 10;

-- Pagina successiva
SELECT * FROM sales 
WHERE (sale_date, sale_id) < (?last_date, ?last_id)
ORDER BY sale_date DESC, sale_id DESC 
LIMIT 10;
```

**Alternative senza Row Values (Oracle, MySQL, SQL Server):**
```sql
SELECT * FROM sales 
WHERE sale_date <= ?last_date
  AND NOT (sale_date = ?last_date AND sale_id >= ?last_id)
ORDER BY sale_date DESC, sale_id DESC 
LIMIT 10;
```

Oppure:
```sql
SELECT * FROM sales 
WHERE sale_date < ?last_date
   OR (sale_date = ?last_date AND sale_id < ?last_id)
ORDER BY sale_date DESC, sale_id DESC 
LIMIT 10;
```

---

## Implementazione PostgreSQL Ottimizzata

**Setup tabella:**
```sql
CREATE TABLE sales (
  sale_id SERIAL PRIMARY KEY,
  sale_date TIMESTAMPTZ NOT NULL,
  amount NUMERIC(10,2),
  customer_id INTEGER
);

CREATE INDEX sales_pagination_idx 
ON sales (sale_date DESC, sale_id DESC);
```

**Funzione helper:**
```sql
CREATE OR REPLACE FUNCTION get_sales_page(
  p_page_size INT DEFAULT 10,
  p_last_date TIMESTAMPTZ DEFAULT NULL,
  p_last_id INT DEFAULT NULL
)
RETURNS TABLE (
  sale_id INT,
  sale_date TIMESTAMPTZ,
  amount NUMERIC,
  customer_id INT
) AS $$
BEGIN
  IF p_last_date IS NULL THEN
    -- Prima pagina
    RETURN QUERY
    SELECT s.sale_id, s.sale_date, s.amount, s.customer_id
    FROM sales s
    ORDER BY s.sale_date DESC, s.sale_id DESC
    LIMIT p_page_size;
  ELSE
    -- Pagine successive
    RETURN QUERY
    SELECT s.sale_id, s.sale_date, s.amount, s.customer_id
    FROM sales s
    WHERE (s.sale_date, s.sale_id) < (p_last_date, p_last_id)
    ORDER BY s.sale_date DESC, s.sale_id DESC
    LIMIT p_page_size;
  END IF;
END;
$$ LANGUAGE plpgsql;
```

**Uso:**
```sql
-- Prima pagina
SELECT * FROM get_sales_page(10);

-- Pagina successiva (usando ultimi valori)
SELECT * FROM get_sales_page(10, '2024-01-15 10:30:00', 1234);
```

---

## API Backend Pattern

**FastAPI + asyncpg:**
```python
from fastapi import FastAPI, Query
from datetime import datetime
from typing import Optional

@app.get("/sales")
async def get_sales(
    page_size: int = Query(10, ge=1, le=100),
    last_date: Optional[datetime] = None,
    last_id: Optional[int] = None
):
    if last_date is None:
        # Prima pagina
        query = """
            SELECT sale_id, sale_date, amount, customer_id
            FROM sales
            ORDER BY sale_date DESC, sale_id DESC
            LIMIT $1
        """
        rows = await db.fetch(query, page_size)
    else:
        # Pagine successive
        query = """
            SELECT sale_id, sale_date, amount, customer_id
            FROM sales
            WHERE (sale_date, sale_id) < ($2, $3)
            ORDER BY sale_date DESC, sale_id DESC
            LIMIT $1
        """
        rows = await db.fetch(query, page_size, last_date, last_id)
    
    results = [dict(row) for row in rows]
    
    # Cursor per prossima pagina
    next_cursor = None
    if len(results) == page_size:
        last_result = results[-1]
        next_cursor = {
            "last_date": last_result["sale_date"].isoformat(),
            "last_id": last_result["sale_id"]
        }
    
    return {
        "data": results,
        "next_cursor": next_cursor,
        "page_size": page_size
    }
```

---

## Frontend Integration

**React + TanStack Query:**
```typescript
interface SaleCursor {
  last_date: string;
  last_id: number;
}

function useSales(cursor?: SaleCursor) {
  return useQuery({
    queryKey: ['sales', cursor],
    queryFn: async () => {
      const params = new URLSearchParams({
        page_size: '10',
        ...(cursor && {
          last_date: cursor.last_date,
          last_id: cursor.last_id.toString(),
        }),
      });
      
      const res = await fetch(`/api/sales?${params}`);
      return res.json();
    },
  });
}

// Infinite scroll
function useSalesInfinite() {
  return useInfiniteQuery({
    queryKey: ['sales'],
    queryFn: ({ pageParam }) => fetchSales(pageParam),
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  });
}
```

---

## Best Practices

**Ordinamento:**
- Sempre includere colonna univoca (PK)
- Indice deve matchare ORDER BY esattamente
- DESC/ASC nell'indice deve matchare query

**Performance:**
- Preferire keyset per infinite scroll
- Usare OFFSET solo per paginazione tradizionale
- Limitare OFFSET a pagine basse (<100)
- Monitorare query time con EXPLAIN ANALYZE

**UX:**
- Keyset + infinite scroll: esperienza fluida
- OFFSET + page numbers: navigazione tradizionale
- Cache risultati già visti
- Pre-fetch pagina successiva

**References:**
- https://use-the-index-luke.com/sql/partial-results/fetch-next-page
- https://use-the-index-luke.com/no-offset

# Rate Limiting Backend

## slowapi (FastAPI/Starlette)

**Caratteristiche:**
- Adattamento di flask-limiter per FastAPI/Starlette
- Usa libreria `limits` sottostante
- Supporto Redis, Memcached, Memory backends
- Decorator-based API
- Produzione-ready (milioni req/mese)

**Installazione:**
```bash
pip install slowapi
```

**Setup base FastAPI:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/")
@limiter.limit("5/minute")
async def homepage(request: Request):
    return {"msg": "Hello World"}
```

**Multiple limits:**
```python
@app.get("/expensive")
@limiter.limit("1/second")
@limiter.limit("20/minute")
@limiter.limit("100/hour")
async def expensive_route(request: Request):
    return {"msg": "expensive operation"}
```

**Shared limits:**
```python
# Limite condiviso su gruppo routes
auth_limit = "10/minute"

@app.post("/login")
@limiter.limit(auth_limit)
async def login(request: Request):
    pass

@app.post("/register")
@limiter.limit(auth_limit)
async def register(request: Request):
    pass
```

**Storage backends:**
```python
# Memory (default)
limiter = Limiter(key_func=get_remote_address)

# Redis
from slowapi.middleware import SlowAPIMiddleware
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)

# Memcached
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memcached://localhost:11211"
)
```

**Custom key functions:**
```python
def get_api_key(request: Request):
    return request.headers.get("X-API-Key", "anonymous")

@app.get("/api/data")
@limiter.limit("100/hour", key_func=get_api_key)
async def api_data(request: Request):
    return {"data": "..."}
```

**Repository:** https://github.com/laurentS/slowapi

---

## FastAPI Advanced Dependencies

**Rate limiting con dependencies:**
```python
from fastapi import Depends, HTTPException, Request
from datetime import datetime, timedelta
from collections import defaultdict
import time

# Simple in-memory store (use Redis in production)
request_counts = defaultdict(list)

def rate_limit(
    max_requests: int = 10,
    window_seconds: int = 60
):
    async def limiter(request: Request):
        client_ip = request.client.host
        now = time.time()
        
        # Clean old requests
        request_counts[client_ip] = [
            req_time for req_time in request_counts[client_ip]
            if now - req_time < window_seconds
        ]
        
        # Check limit
        if len(request_counts[client_ip]) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={"Retry-After": str(window_seconds)}
            )
        
        # Record request
        request_counts[client_ip].append(now)
    
    return limiter

@app.get("/limited")
async def limited_route(
    request: Request,
    _: None = Depends(rate_limit(max_requests=5, window_seconds=60))
):
    return {"msg": "success"}
```

---

## Redis Storage Pattern

**Implementazione Redis:**
```python
import redis
from fastapi import FastAPI, HTTPException, Request

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

async def check_rate_limit(
    request: Request,
    max_requests: int = 10,
    window_seconds: int = 60
):
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"
    
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    result = pipe.execute()
    
    request_count = result[0]
    
    if request_count > max_requests:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(window_seconds)}
        )
    
    return request_count

@app.get("/api/endpoint")
async def endpoint(
    request: Request,
    count: int = Depends(check_rate_limit)
):
    return {
        "msg": "success",
        "requests_remaining": 10 - count
    }
```

**Sliding window con Redis:**
```python
import time

async def sliding_window_rate_limit(
    request: Request,
    max_requests: int = 10,
    window_seconds: int = 60
):
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"
    now = time.time()
    window_start = now - window_seconds
    
    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcount(key, window_start, now)
    pipe.expire(key, window_seconds)
    result = pipe.execute()
    
    request_count = result[2]
    
    if request_count > max_requests:
        raise HTTPException(status_code=429)
    
    return request_count
```

---

## Testing Rate Limits

```python
from fastapi.testclient import TestClient

def test_rate_limit():
    client = TestClient(app)
    
    # Prima richiesta: OK
    response = client.get("/limited")
    assert response.status_code == 200
    
    # Richieste successive fino al limite
    for _ in range(4):
        response = client.get("/limited")
        assert response.status_code == 200
    
    # Oltre il limite: 429
    response = client.get("/limited")
    assert response.status_code == 429
    assert "Retry-After" in response.headers
```

---

## Best Practices

**Storage:**
- Usa Redis in produzione
- Memory solo per dev/test
- Considera Redis Cluster per scalabilità

**Limiti:**
- Endpoint pubblici: stringenti (5-10/min)
- Endpoint autenticati: generosi (100-1000/hour)
- Endpoint costosi: molto stringenti (1/sec)

**Headers risposta:**
- X-RateLimit-Limit: limite totale
- X-RateLimit-Remaining: richieste rimanenti
- X-RateLimit-Reset: timestamp reset
- Retry-After: secondi da attendere (se 429)

**Implementazione:**
- Usa decorator pattern (slowapi)
- Centralizza configurazione limiti
- Log rate limit hits per monitoring
- Whitelist IP interni/trusted

"""
Custom middleware per FastAPI application.

Fornisce:
- Request logging strutturato
- Request ID tracking
- Performance metrics
"""
import time
import logging
from uuid import uuid4
from fastapi import Request

logger = logging.getLogger("api")


async def log_requests(request: Request, call_next):
    """
    Middleware per logging HTTP requests.
    
    Logga:
    - Method, path, status code
    - Duration in milliseconds
    - Client IP
    """
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    
    client_ip = request.client.host if request.client else None
    
    logger.info({
        "event": "http_request",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": duration_ms,
        "client_ip": client_ip,
    })
    
    return response


async def add_request_id(request: Request, call_next):
    """
    Middleware per aggiungere request_id unico.
    
    Usato per troubleshooting e correlation logs.
    """
    request_id = str(uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response

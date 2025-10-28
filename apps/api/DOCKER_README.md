# Docker Configuration - FisioRAG API

Configurazione Docker ottimizzata per FisioRAG API con supporto Story 7.2 (Advanced Retrieval).

## Files

- `Dockerfile` - Multi-stage production image (ottimizzato, ~800MB)
- `Dockerfile.dev` - Development image (hot-reload, debug, ~1.2GB)
- `.dockerignore` - Escludi file non necessari per ridurre build context
- `docker-compose.yml` - Configurazione produzione
- `docker-compose.dev.yml` - Configurazione development

## Production Build

### Quick Start (Recommended)

```bash
# From repository root
# Docker Compose fa automaticamente il build
docker compose up -d --build

# View logs
docker compose logs -f api

# Stop all services
docker compose down
```

### Manual Build (Optional)

Build manuale serve solo per testing isolato o push to registry:

```bash
# Build manuale (opzionale)
docker build -t fisio-rag-api:latest -f apps/api/Dockerfile .

# Run manuale (senza compose)
docker run -p 8000:8000 --env-file .env fisio-rag-api:latest
```

**Nota:** Con Docker Compose **NON serve** build manuale. Compose lo fa automaticamente leggendo la sezione `build:` in `docker-compose.yml`.

### Docker Compose Commands

```bash
# Build + start (sempre fresh build)
docker compose up -d --build

# Start (build solo se immagine mancante)
docker compose up -d

# Build senza start
docker compose build

# Rebuild specific service
docker compose build api

# Restart senza rebuild
docker compose restart api

# Stop
docker compose down

# Stop + remove volumes
docker compose down -v
```

### Story 7.2 Feature Flags

Enable advanced retrieval features modificando `.env`:

```bash
# Story 7.2 Feature Flags
ENABLE_CROSS_ENCODER_RERANKING=true
ENABLE_DYNAMIC_MATCH_COUNT=true
ENABLE_CHUNK_DIVERSIFICATION=true
```

## Development Build

### Quick Start Development

```bash
# Start dev environment con hot-reload
docker compose -f docker-compose.dev.yml up -d --build

# Logs with follow
docker compose -f docker-compose.dev.yml logs -f api

# Stop
docker compose -f docker-compose.dev.yml down
```

**Nota:** Anche in dev mode, Docker Compose fa automaticamente il build. Non serve build manuale.

### Features Development Mode

- ✅ Hot-reload su modifiche codice
- ✅ Debug logging enabled
- ✅ Redis port esposta (6379) per debugging
- ✅ Full dev dependencies (pytest, coverage)
- ✅ Volume mount per live code updates

## Multi-Stage Build Benefits

**Production Dockerfile** usa multi-stage build per ridurre dimensione finale:

1. **Builder stage** (~1.2GB):
   - Poetry installato
   - Build tools (gcc, g++)
   - Dipendenze compilate (torch, numpy)

2. **Runtime stage** (~800MB):
   - Solo runtime dependencies
   - No Poetry, no build tools
   - Non-root user (sicurezza)
   - Healthcheck configurato

**Saving:** ~400MB per immagine

## Model Cache

Story 7.2 cross-encoder model (~200MB) scaricato runtime (lazy loading).

Volume persistente previene re-download:

```yaml
volumes:
  model_cache:/app/.cache/torch/sentence_transformers
```

**Primo avvio:** ~30s delay per download model  
**Avvii successivi:** Instant (model cached)

## Healthcheck

Production image include healthcheck:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

Verifica status:

```bash
docker ps
# HEALTH: healthy / unhealthy / starting
```

## Security

### Non-Root User

Production image esegue come user `appuser` (UID 1000):

```dockerfile
USER appuser
```

### Environment Variables

**NON committare** `.env` con secrets. Usare:

1. `.env` locale (gitignored)
2. Docker secrets (production)
3. Vault/Secret Manager (cloud)

## Troubleshooting

### Build Slow

**Cache Poetry dependencies:**

```bash
# Build con cache
docker build --cache-from fisio-rag-api:latest -t fisio-rag-api:latest -f apps/api/Dockerfile .
```

### Out of Memory

Torch + sentence-transformers richiedono ~1GB RAM build-time.

**Aumentare Docker memory limit:**

```bash
# Docker Desktop: Settings → Resources → Memory (≥4GB recommended)
```

### Model Download Fail

**Retry con proxy:**

```bash
docker run -e HTTP_PROXY=http://proxy:8080 fisio-rag-api:latest
```

### Permission Denied

**Fix ownership:**

```bash
# Dentro container
chown -R appuser:appuser /app/.cache
```

## Performance Tuning

### Production Workers

Default: 1 worker (uvicorn)

**Scale con replicas** (Docker Swarm/Kubernetes):

```bash
docker service scale fisio-rag-api=4
```

**Non aumentare `--workers`** (condividono memoria modello).

### Uvicorn Settings

Production Dockerfile usa:

```bash
--loop uvloop         # Performance loop
--no-access-log       # Reduce I/O (use proxy logs)
--workers 1           # Single worker (scale with replicas)
```

## Monitoring

### Container Stats

```bash
docker stats fisio-rag-api
```

### Logs

```bash
# Tail logs
docker logs -f fisio-rag-api

# JSON structured logs
docker logs fisio-rag-api | jq .
```

### Health Endpoint

```bash
curl http://localhost:8000/health
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Build Docker Image
  run: docker build -t fisio-rag-api:${{ github.sha }} -f apps/api/Dockerfile .

- name: Push to Registry
  run: docker push fisio-rag-api:${{ github.sha }}

- name: Deploy
  run: kubectl set image deployment/api api=fisio-rag-api:${{ github.sha }}
```

## References

- Story 7.2: `docs/stories/7.2-advanced-retrieval-optimization.md`
- Docker Best Practices: https://docs.docker.com/develop/dev-best-practices/
- Multi-stage builds: https://docs.docker.com/build/building/multi-stage/


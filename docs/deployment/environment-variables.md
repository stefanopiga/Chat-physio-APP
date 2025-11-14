# Environment Variables Configuration

## Quick Start - New Users

**If you're cloning this project for the first time:**

1. Create `.env` file in project root:

```bash
# Minimal configuration for development without database
ENABLE_PERSISTENT_MEMORY=false
ENABLE_CROSS_ENCODER_RERANKING=false
ENABLE_DYNAMIC_MATCH_COUNT=false
ENABLE_CHUNK_DIVERSIFICATION=false
```

2. Run: `docker compose up --build -d`

---

## Production Configuration

**For production deployment with full features:**

Create `.env` file in project root:

```bash
# Story 9.2: Persistent Memory (requires PostgreSQL)
ENABLE_PERSISTENT_MEMORY=true

# Story 7.2: Advanced RAG Features (optional, increases latency)
ENABLE_CROSS_ENCODER_RERANKING=false
ENABLE_DYNAMIC_MATCH_COUNT=false
ENABLE_CHUNK_DIVERSIFICATION=false

# Traefik Dashboard Port (default 18080)
TRAEFIK_DASHBOARD_PORT=18080
```

**Prerequisites when `ENABLE_PERSISTENT_MEMORY=true`:**
- PostgreSQL database configured
- Database schema migrated (run migrations)
- Backend settings configured with database URL

---

## Environment Variables Reference

### Feature Flags

#### `ENABLE_PERSISTENT_MEMORY` (Story 9.2)
- **Type**: Boolean (`true` / `false`)
- **Default**: `true` (docker-compose.yml)
- **Description**: Enable conversation history persistence to PostgreSQL
- **Dependencies**: 
  - PostgreSQL database with proper schema
  - Backend configured with `DATABASE_URL`
- **Impact**: 
  - `false`: Conversations not saved, UI won't load history
  - `true`: Requires database, saves/loads conversation history
- **When to disable**: Development without database setup

#### `ENABLE_CROSS_ENCODER_RERANKING` (Story 7.2)
- **Type**: Boolean
- **Default**: `false`
- **Description**: Use cross-encoder model for result reranking
- **Impact**: Adds ~2s latency per query, improves relevance
- **When to enable**: Production with high accuracy requirements

#### `ENABLE_DYNAMIC_MATCH_COUNT` (Story 7.2)
- **Type**: Boolean
- **Default**: `false`
- **Description**: Adjust retrieval count based on query complexity
- **Impact**: Variable performance, adaptive result count
- **When to enable**: Advanced RAG scenarios

#### `ENABLE_CHUNK_DIVERSIFICATION` (Story 7.2)
- **Type**: Boolean
- **Default**: `false`
- **Description**: Diversify retrieved chunks across documents
- **Impact**: Broader coverage, may reduce precision
- **When to enable**: When diversity more important than precision

---

## Frontend Build-Time Variables

**Set in docker-compose.yml under `web.build.args`:**

### `VITE_ENABLE_PERSISTENT_MEMORY`
- **Type**: String (`"true"` / `"false"`)
- **Default**: `"true"` (hardcoded in docker-compose.yml)
- **Description**: Frontend feature flag for history loading
- **Build-time**: Compiled into frontend bundle
- **Override**: Modify `docker-compose.yml` web service build args

**To disable frontend persistent memory:**

```yaml
# docker-compose.yml
web:
  build:
    args:
      VITE_ENABLE_PERSISTENT_MEMORY: "false"  # ⬅️ Change here
```

**Note**: Requires rebuild: `docker compose up --build web`

---

## Safety Considerations

### For New Deployments

**Risk: Database Not Configured**

If `ENABLE_PERSISTENT_MEMORY=true` but PostgreSQL not available:
- Backend endpoint returns 503 Service Unavailable
- Frontend shows error: "Failed to load session history"
- Application partially functional (chat works, history doesn't)

**Mitigation**:
1. Start with `ENABLE_PERSISTENT_MEMORY=false`
2. Setup PostgreSQL
3. Run database migrations
4. Enable persistent memory
5. Rebuild containers

### For Production

**Safe Configuration:**
```bash
# .env
ENABLE_PERSISTENT_MEMORY=true  # ✅ Only if DB ready
ENABLE_CROSS_ENCODER_RERANKING=false  # ⚠️ Adds latency
ENABLE_DYNAMIC_MATCH_COUNT=false
ENABLE_CHUNK_DIVERSIFICATION=false
```

**Monitor**:
- Backend `/health` endpoint status
- Frontend console errors (F12 → Console)
- Database connection pool usage

---

## Troubleshooting

### "Failed to load session history" in UI

**Cause**: Backend persistent memory disabled or database unavailable

**Fix**:
1. Check `.env`: `ENABLE_PERSISTENT_MEMORY=true`
2. Verify backend logs: `docker compose logs api`
3. Check database connection
4. Restart: `docker compose restart api`

### Frontend doesn't load history after rebuild

**Cause**: `VITE_ENABLE_PERSISTENT_MEMORY` not set during build

**Fix**:
1. Verify `docker-compose.yml` web build args
2. Force rebuild: `docker compose build --no-cache web`
3. Check browser console: `import.meta.env.VITE_ENABLE_PERSISTENT_MEMORY`

### Docker build timeout (nvidia-cublas-cu12, torch)

**Cause**: Slow network, large package downloads

**Fix**: Already implemented in Dockerfiles:
- pip timeout: 600s
- pip retries: 3
- Poetry max-workers: 10

If still fails, increase timeout in `.env` (not currently supported, requires Dockerfile edit).

---

## Migration from Default Configuration

**If you have an existing deployment:**

1. **Check current configuration**:
   ```bash
   docker compose config | grep PERSISTENT_MEMORY
   ```

2. **Create .env with explicit values**:
   ```bash
   echo "ENABLE_PERSISTENT_MEMORY=true" > .env
   ```

3. **Rebuild**:
   ```bash
   docker compose down
   docker compose up --build -d
   ```

4. **Verify**:
   - Backend: `curl http://localhost/health`
   - Frontend: Open chat, check browser console (F12)

---

## Advanced: Override Without .env

**Using environment variables directly:**

```bash
# Linux/Mac
export ENABLE_PERSISTENT_MEMORY=false
docker compose up -d

# Windows PowerShell
$env:ENABLE_PERSISTENT_MEMORY="false"
docker compose up -d

# Windows CMD
set ENABLE_PERSISTENT_MEMORY=false
docker compose up -d
```

**Using docker compose override:**

```bash
# One-time override
docker compose -e ENABLE_PERSISTENT_MEMORY=false up -d
```


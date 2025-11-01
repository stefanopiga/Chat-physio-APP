# Docker Infrastructure Troubleshooting

Story 2.6.1 introduces persistence and validation guardrails for the Docker Compose stack.

## 1. Redis Data Persistence

- Compose now defines a named volume `redis_data` mounted at `/data`.
- Redis runs with `redis-server --appendonly yes` (AOF) to preserve writes between restarts (i file sono salvati in `/data/appendonlydir/`: manifest + segmenti incrementali).
- Volume is declared at root level in `docker-compose.yml`; verify with:

```powershell
docker volume ls | Select-String redis_data
docker inspect redis_data | ConvertTo-Json
```

### 1.1 Smoke Test

```powershell
docker exec fisio-rag-redis redis-cli SET test_persistence "value_$(Get-Date -Format 'HHmmss')"
docker compose restart redis
Start-Sleep -Seconds 5
docker exec fisio-rag-redis redis-cli GET test_persistence
docker exec fisio-rag-redis ls -lah /data/appendonlydir
```

Expected: key survives reboot, confirming AOF persistence.

### 1.2 Backup & Restore Strategy

1. **Backup**: `docker run --rm --volumes-from fisio-rag-redis -v "$PWD\backups":/backup alpine tar czf /backup/redis-data.tar.gz /data`
2. **Restore**: `docker run --rm --volumes-from fisio-rag-redis -v "$PWD\backups":/backup alpine sh -c "cd / && tar xzf /backup/redis-data.tar.gz"`
3. **Verify**: restart container and confirm keys exist.

Keep at least one recent backup before production deploys.

## 2. Health Check Playbook

The infrastructure validation scripts live in `scripts/validation/`:

- `docker_health_check.py` — service reachability checks.
- `database_connectivity_test.py` — added in Story 2.6.1 to unblock database audits.

Run from repository root:

```powershell
python scripts/validation/docker_health_check.py
```

For database diagnostics see `docs/troubleshooting/database-connectivity.md`.

## 3. Common Docker Compose Issues

| Symptom | Joint Cause | Recovery |
| --- | --- | --- |
| `redis_data` volume missing | `docker compose down -v` executed | Recreate stack: `docker compose up -d`, then re-seed Redis or restore backup. |
| `appendonlydir` empty | Redis container started without new command | `docker compose restart redis` after pulling latest Compose file. |
| Containers stuck `Restarting` | Configuration mismatch or missing env vars | Run `docker compose logs <service>` and compare with `.env` template; fix variables and restart. |
| Proxy routing stale | Traefik cache not refreshed | `docker compose restart proxy` after label updates. |

## 4. Volume Maintenance

- Inspect size: `docker system df`.
- Remove dangling volumes (never `redis_data`): `docker volume prune`.
- For production, store backups off-host or in S3-compatible storage.

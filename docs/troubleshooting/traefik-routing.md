# Traefik Routing Troubleshooting

Story 2.6.1 resolves the `/health` routing conflict and documents recovery procedures.

## 1. Router Priorities

- `api-health-router` — exact match `Path(/health)`, priority `150`.
- `api-router` — `PathPrefix(/api)`, priority `100`.
- `web-router` — catch-all host rule, priority `1`.

Traefik evaluates highest priority first; explicit numbers prevent accidental fallback to the web UI.

## 2. Validating the Fix

```powershell
curl http://localhost/health
```

Expected response:

- HTTP 200
- `Content-Type: application/json`
- Payload similar to `{"status":"ok"}`

Check router status in the Traefik dashboard: `http://localhost:18080` (override with `TRAEFIK_DASHBOARD_PORT` if needed). `api-health-router` should appear under HTTP routers with status `UP`.

## 3. Common Failure Modes

| Symptom | Cause | Resolution |
| --- | --- | --- |
| `/health` returns HTML | `api-health-router` missing or lower priority | Ensure labels in `docker-compose.yml` are applied; restart proxy. |
| 404 response | API container unhealthy or downtime | `docker compose ps api` to confirm status, inspect logs. |
| Traefik ignoring new labels | Docker provider cache not refreshed | `docker compose restart proxy` to reload configuration. |
| TLS redirect loops | Misconfigured entrypoints or middleware | Review Traefik logs and ensure `--entrypoints.web.address=:80` is set. |

## 4. Debug Commands

```powershell
docker compose logs proxy --tail 100
docker compose exec proxy traefik healthcheck
```

Inside the proxy container, inspect dynamic config:

```powershell
docker compose exec proxy cat /etc/traefik/traefik.yml
```

## 5. Extending Routing Rules

When adding new API routes that require direct exposure (e.g. `/metrics`), follow the same pattern:

1. Define a dedicated router with explicit `Path`/`Host` match.
2. Assign priority higher than generic routers but lower than administrative ones to avoid conflicts.
3. Point the router to `api-service` to reuse the backend load balancer.
4. Document the change inline in `docker-compose.yml` and update this guide if behavior differs.

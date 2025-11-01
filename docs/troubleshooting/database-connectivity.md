# Database Connectivity Troubleshooting

Story 2.6.1 introduced a hardened workflow to validate and diagnose Supabase connectivity issues for the FisioRAG stack.

## 1. Quick Checklist

1. `DATABASE_URL` is present in the root `.env` file.
2. Connection string uses the **pooler** endpoint (`port 6543`) for production workloads.
3. `sslmode=require` is included to satisfy Supabase TLS enforcement.
4. Optional tuning parameters (e.g. `connect_timeout=10`) are appended via query string.
5. Credentials match the service role key generated from Supabase.

Verify with:

```powershell
Get-Content .env | Select-String "DATABASE_URL"
```

_Never_ paste secrets into tickets or logs—confirm presence only.

## 2. Connection String Reference

```
postgresql://postgres.<project-ref>:<password>@db.<project-ref>.supabase.co:6543/postgres?sslmode=require&connect_timeout=10
```

- Use the pooler endpoint (`db.<ref>.supabase.co:6543`) for better connection limits.
- `sslmode=require` is mandatory—without it Supabase refuses TLS connections.
- Add `options=-c search_path=public,extensions` if schema access errors persist.

## 3. Validation Script

Story 2.6.1 added `scripts/validation/database_connectivity_test.py` (configurato con `statement_cache_size=0` per compatibilità PgBouncer). Run it from the API environment:

```powershell
cd apps/api
poetry run python ../../scripts/validation/database_connectivity_test.py
```

Expected output:

- Diagnostic dump of parsed URL components (host, port, database).
- `✅ Database connection: SUCCESS` when credentials and network are valid.
- Otherwise, stack trace identifying authentication, DNS, or TLS issues.

## 4. Common Failure Modes

| Symptom | Probable Cause | Mitigation |
| --- | --- | --- |
| `DATABASE_URL not set` | `.env` missing entry, wrong file loaded in Compose | Sync `.env` with `temp_env_populated_root.md` template and restart services. |
| `Connection refused` | Supabase paused project, wrong host/port, firewall blocking | Resume project in Supabase dashboard, double-check host (`db.<ref>.supabase.co`) and port (`6543`), ensure workstation can reach outbound TLS. |
| `invalid sslmode value` | Missing `sslmode=require` parameter | Append `?sslmode=require` to URL and retest. |
| `password authentication failed` | Service role key rotated or typo | Regenerate credentials from Supabase **Database > Connection pooling** section and update `.env`. |
| `Temporary failure in name resolution` | DNS outage or proxy interference | Run `nslookup db.<ref>.supabase.co`, verify VPN/firewall rules allow outbound DNS. |

## 5. Network Diagnostics

PowerShell helpers when testing from Windows hosts:

```powershell
nslookup db.<project-ref>.supabase.co
Test-NetConnection -ComputerName db.<project-ref>.supabase.co -Port 6543
```

Inside the Docker network (after `docker compose up`):

```powershell
docker exec -it fisio-rag-api sh -c "apk add --no-cache postgresql-client && psql \"$DATABASE_URL\" -c 'SELECT 1;'"
```

## 6. Post-Fix Validation

1. Run `database_connectivity_test.py` and expect success.
2. Execute `python scripts/validation/database_integrity_audit.py` from repo root—queries should complete without `ConnectionRefusedError`.
3. Update evidence in `docs/reports/rag-database-integrity-post-fix.md` after a successful audit.

Keep screenshots/logs for ops handoff in case future environments regress.

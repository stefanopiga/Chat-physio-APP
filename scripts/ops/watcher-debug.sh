#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
OUTPUT_DIR="${ROOT_DIR}/ingestion/temp/watcher-debug/${TIMESTAMP}"
mkdir -p "${OUTPUT_DIR}"

capture_cmd() {
  local outfile="$1"
  shift
  {
    echo "\$ $*"
    "$@"
  } >"${outfile}" 2>&1 || true
}

compose_cmd=()
if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    compose_cmd=(docker compose)
  elif command -v docker-compose >/dev/null 2>&1; then
    compose_cmd=(docker-compose)
  fi
fi

if [ "${#compose_cmd[@]}" -gt 0 ]; then
  capture_cmd "${OUTPUT_DIR}/docker-ps.txt" "${compose_cmd[@]}" ps
  capture_cmd "${OUTPUT_DIR}/docker-logs-api.txt" "${compose_cmd[@]}" logs -n 2000 applicazione-api
  capture_cmd "${OUTPUT_DIR}/docker-logs-worker.txt" "${compose_cmd[@]}" logs -n 2000 applicazione-celery-worker
  capture_cmd "${OUTPUT_DIR}/docker-logs-redis.txt" "${compose_cmd[@]}" logs -n 2000 fisio-rag-redis
else
  echo "docker compose not available" >"${OUTPUT_DIR}/docker-info.txt"
fi

capture_cmd "${OUTPUT_DIR}/disk-usage.txt" df -h
capture_cmd "${OUTPUT_DIR}/git-info.txt" git -C "${ROOT_DIR}" status --short
capture_cmd "${OUTPUT_DIR}/git-commit.txt" git -C "${ROOT_DIR}" rev-parse HEAD

if command -v poetry >/dev/null 2>&1; then
  capture_cmd "${OUTPUT_DIR}/settings.json" poetry --directory "${ROOT_DIR}/apps/api" run python -m api.debug.print_settings
else
  echo "poetry not available" >"${OUTPUT_DIR}/settings.json"
fi

echo "Watcher diagnostics collected in ${OUTPUT_DIR}"


#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-reports}"
STAMP="${2:-$(date +%Y%m%d)}"
mkdir -p "${OUT_DIR}"

TRUFFLE_OUT="${OUT_DIR}/secrets-scan-${STAMP}.txt"
CI_LOG="${OUT_DIR}/ci-secrets-scan-${STAMP}.log"
DETECT_OUT="${OUT_DIR}/detect-secrets-raw-${STAMP}.json"

if ! command -v trufflehog >/dev/null 2>&1; then
  echo "[WARN] trufflehog non trovato nel PATH" >&2
  exit 127
fi

if ! command -v detect-secrets >/dev/null 2>&1; then
  echo "[WARN] detect-secrets non trovato nel PATH" >&2
  exit 127
fi

trufflehog filesystem --json . \
  | tee "${TRUFFLE_OUT}" \
  | python - <<'PY' > "${CI_LOG}"
import json
import sys
from hashlib import sha256

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        continue
    raw = data.pop("Raw", None)
    if raw:
        data["hashed_secret"] = sha256(raw.encode("utf-8")).hexdigest()
    print(json.dumps(data, ensure_ascii=False))
PY

detect-secrets scan --all-files > "${DETECT_OUT}"

echo "[INFO] Secret scan completata. Output in ${OUT_DIR}" >&2


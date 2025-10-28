import http from "k6/http";
import { check, sleep } from "k6";

/**
 * k6 load script per misurare latenza endpoints principali.
 *
 * Usage:
 *   k6 run --env BASE_URL="https://staging.example" --env REQUESTS=300 \
 *          --out json=reports/p95_k6_$(date +%Y%m%d).json scripts/perf/p95_local_test.js
 *   # REQUESTS default a 300 se non specificato.
 *
 * NOTE:
 *   - Assicurarsi che Traefik esponga gli endpoint su http://localhost
 *   - Impostare ADMIN_BEARER/CHAT_BEARER con token validi (anche mock) per endpoint protetti
 */

const TOTAL_REQUESTS = Math.max(
  1,
  parseInt(__ENV.REQUESTS || __ENV.P95_REQUESTS || "300", 10),
);
const SYNC_ITERATIONS = Math.max(
  1,
  parseInt(__ENV.SYNC_REQUESTS || String(Math.ceil(TOTAL_REQUESTS / 2)), 10),
);
const CHAT_ITERATIONS = Math.max(1, TOTAL_REQUESTS - SYNC_ITERATIONS);
const SYNC_VUS = Math.max(
  1,
  Math.min(parseInt(__ENV.SYNC_VUS || "5", 10), SYNC_ITERATIONS),
);
const CHAT_VUS = Math.max(
  1,
  Math.min(parseInt(__ENV.CHAT_VUS || "5", 10), CHAT_ITERATIONS),
);

const SYNC_MAX_DURATION = `${Math.ceil(SYNC_ITERATIONS / SYNC_VUS) + 30}s`;
const CHAT_MAX_DURATION = `${Math.ceil(CHAT_ITERATIONS / CHAT_VUS) + 30}s`;
const CHAT_START_TIME = `${Math.ceil(SYNC_ITERATIONS / SYNC_VUS) + 5}s`;

export const options = {
  scenarios: {
    sync_jobs: {
      executor: "shared-iterations",
      exec: "testSyncJob",
      vus: SYNC_VUS,
      iterations: SYNC_ITERATIONS,
      maxDuration: SYNC_MAX_DURATION,
    },
    chat_query: {
      executor: "shared-iterations",
      exec: "testChat",
      vus: CHAT_VUS,
      iterations: CHAT_ITERATIONS,
      startTime: CHAT_START_TIME,
      maxDuration: CHAT_MAX_DURATION,
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<1000"],
  },
};

const BASE_URL = (__ENV.BASE_URL || "http://localhost").trim();
const ADMIN_BEARER = __ENV.ADMIN_BEARER || __ENV.AUTH_BEARER || "Bearer mock_admin_jwt_token";
const CHAT_BEARER = __ENV.CHAT_BEARER || ADMIN_BEARER;

const documentPayload = {
  document_text: "Documento test p95 – benchmark latenza.",
  metadata: {
    document_name: "p95-benchmark.txt",
    source: "k6-load-test",
  },
};

export function testSyncJob() {
  const res = http.post(
    `${BASE_URL}/api/v1/admin/knowledge-base/sync-jobs`,
    JSON.stringify(documentPayload),
    {
      headers: {
        "Content-Type": "application/json",
        Authorization: ADMIN_BEARER,
      },
    },
  );

  check(res, {
    "sync job status 200": (r) => r.status === 200,
  });

  sleep(1);
}

export function testChat() {
  const res = http.post(
    `${BASE_URL}/api/v1/chat`,
    JSON.stringify({
      message: "trattamento lombalgia",
      session_id: "k6-session",
    }),
    {
      headers: {
        "Content-Type": "application/json",
        Authorization: CHAT_BEARER,
      },
    },
  );

  check(res, {
    "chat status 200": (r) => r.status === 200,
  });

  sleep(1);
}

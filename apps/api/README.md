# API Service

Servizio FastAPI per access codes e ingestion.


## Classification Cache (Story 2.9)

Layer Redis per memorizzare i risultati di `classify_content_enhanced` e ridurre la latenza ingestion.
- Env vars: `CLASSIFICATION_CACHE_ENABLED` (default true), `CLASSIFICATION_CACHE_TTL_SECONDS` (default 604800), `CLASSIFICATION_CACHE_REDIS_URL` (facoltativa, DB 1).
- Admin tools: `GET /api/v1/admin/knowledge-base/classification-cache/metrics`, `DELETE /api/v1/admin/knowledge-base/classification-cache/{digest}`, `DELETE /api/v1/admin/knowledge-base/classification-cache`.
- Feature flag rollback: impostare `CLASSIFICATION_CACHE_ENABLED=false` e riavviare il servizio.

## Augmented Generation (AG)

- Modello di generazione post-embedding: `gpt-5-nano` (LangChain `ChatOpenAI`, `temperature=0`).
- Endpoint: `POST /api/v1/chat/sessions/{sessionId}/messages` — implementato con LCEL e PydanticOutputParser.
- Output AG: include `citations` arricchite per popover (`chunk_id`, `document_id`, `excerpt`, `position`).
- Auth: JWT (Supabase), Rate limiting: `60/minute`.
- Logging: eventi `ag_message_request`, `ag_fallback`, `ag_metrics` (con `latency_ms` e `p95_ms`).

### Feedback su messaggi (Story 3.4)
- Endpoint: `POST /api/v1/chat/messages/{messageId}/feedback`
- Body: `{ sessionId: string, vote: 'up'|'down' }`
- Response: `{ ok: boolean }`

Riferimenti:
- `docs/stories/3.2.augmented-generation-endpoint.md`
- `docs/stories/3.4.source-visualization-and-feedback.md`
- `docs/architecture/sezione-3-tech-stack.md`
- `docs/architecture/sezione-5-specifica-api-sintesi.md`
- `docs/architecture/sezione-10-sicurezza-e-performance.md`
# Sezione 4: Modelli di Dati

### 4.1 Modello: `Admin`
*   **Scopo:** Rappresenta l'utente amministratore (professore).
*   **Attributi Chiave:** `id` (UUID), `username` (string), `hashed_password` (string), `created_at` (timestamp), `updated_at` (timestamp).

### 4.2 Modello: `AccessCode`
*   **Scopo:** Rappresenta un codice di accesso per gli studenti.
*   **Attributi Chiave:** `id` (UUID), `code` (string), `is_active` (boolean), `expires_at` (timestamp, nullable), `usage_count` (integer), `last_used_at` (timestamp, nullable), `created_by_id` (UUID, FK to Admin), `created_at`, `updated_at`.

### 4.3 Modello: `Document`
*   **Scopo:** Memorizza i metadati per ogni file sorgente.
*   **Attributi Chiave:** `id` (UUID), `file_name` (string), `file_path` (string), `file_hash` (string), `status` (string), `chunking_strategy` (jsonb), `metadata` (jsonb), `created_at`, `updated_at`.

### 4.4 Modello: `DocumentChunk`
*   **Scopo:** Memorizza i singoli blocchi di testo e i loro embedding.
*   **Attributi Chiave:** `id` (UUID), `document_id` (UUID, FK to Document), `content` (text), `embedding` (vector), `metadata` (jsonb), `created_at`, `updated_at`.

### 4.5 Modello: `ChatMessage`
*   **Scopo:** Memorizza un singolo messaggio di una conversazione.
*   **Attributi Chiave:** `id` (UUID), `session_id` (string), `role` (string), `content` (text), `source_chunk_ids` (array of UUIDs, nullable), `metadata` (jsonb, nullable), `created_at` (timestamp).

### 4.6 Modello: `Feedback`
*   **Scopo:** Registra il feedback (👍/👎) su una risposta.
*   **Attributi Chiave:** `id` (UUID), `chat_message_id` (UUID, FK to ChatMessage), `rating` (string), `created_at` (timestamp).

---

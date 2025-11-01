# Sezione 13: Strategia di Gestione degli Errori

*   **Formato Standard**: Tutti gli errori API restituiscono `{ "detail": "..." }`.
*   **Backend**: Uso di exception handlers centralizzati con logging strutturato. Verranno implementati gestori specifici per i fallimenti delle API esterne (es. timeout, errori 5xx), restituendo un messaggio di errore chiaro e prevenendo crash.
*   **Frontend**: Gestione centralizzata nel `Multi-API Service` e uso di Error Boundaries.
*   **Traceability**: Implementazione di un `Correlation ID` (`X-Request-ID`) per tracciare ogni richiesta end-to-end e semplificare il debugging.

---

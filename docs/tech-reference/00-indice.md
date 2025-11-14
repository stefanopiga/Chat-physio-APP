# Indice Documentazione Tecnica

Materiale di riferimento per implementazione componenti applicazione.

## Contenuti

1. **[Virtual Scrolling](./01-virtual-scrolling.md)**
   - react-window, TanStack Virtual, react-virtuoso
   - Comparazione caratteristiche e bundle size
   - Pattern implementazione

2. **[Toast Notifications](./02-toast-notifications.md)**
   - Sonner (raccomandato shadcn/ui)
   - Setup e configurazione
   - API completa

3. **[Exponential Backoff](./03-exponential-backoff.md)**
   - node-retry library
   - Pattern Retry-After header
   - Implementazione con Promises
   - Best practices retry strategy

4. **[Rate Limiting Backend](./04-rate-limiting-backend.md)**
   - slowapi per FastAPI/Starlette
   - Storage backends (Redis, Memory)
   - Pattern decorator e dependencies
   - Testing rate limits

5. **[PostgreSQL Pagination](./05-postgresql-pagination.md)**
   - Problemi LIMIT/OFFSET
   - Keyset pagination (seek method)
   - Row values e ordinamento deterministico
   - Pattern API backend e frontend integration

6. **[Vite Environment Variables](./06-vite-environment-variables.md)**
   - Variabili built-in e custom
   - File .env hierarchy
   - TypeScript IntelliSense
   - Security best practices

7. **[React Hook Testing](./07-react-hook-testing.md)**
   - @testing-library/react-hooks
   - Pattern test comuni (async, context, effects)
   - Vitest setup
   - Best practices

## Note

- Ogni documento include esempi codice funzionanti
- Link a repository ufficiali per approfondimenti
- Trade-off e raccomandazioni per scelta tecnologica

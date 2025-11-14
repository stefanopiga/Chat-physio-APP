# Story 9.2 - Troubleshooting Persistenza Non Funzionante

## Sintomo
Conversazioni non persistono tra navigazioni (dashboard → chat = chat bianca)

## Verifiche Immediate (Browser)

### 1. Console Debug (F12 → Console)

**Apri browser console durante caricamento ChatPage:**

```javascript
// Verifica feature flag compilato nel bundle
console.log('VITE_ENABLE_PERSISTENT_MEMORY:', import.meta.env.VITE_ENABLE_PERSISTENT_MEMORY);

// Se undefined o "false" → problema build-time flag
// Se "true" → flag OK, problema altro
```

**Output atteso**:
- ✅ `VITE_ENABLE_PERSISTENT_MEMORY: "true"` (string)
- ❌ `VITE_ENABLE_PERSISTENT_MEMORY: undefined` → rebuild richiesto

### 2. Network Tab (F12 → Network)

**Filtra richieste API durante mount ChatPage:**

```
GET /api/v1/chat/sessions/{sessionId}/history/full?limit=100&offset=0
```

**Possibili scenari**:

| Status | Causa | Fix |
|--------|-------|-----|
| 200 OK + empty array | Nessun messaggio salvato (problema Story precedente) | Verifica salvataggio messaggi |
| 404 Not Found | Sessione nuova o mai salvata | Normale per prima conversazione |
| 503 Service Unavailable | Backend `ENABLE_PERSISTENT_MEMORY=false` | Verifica backend env |
| 401 Unauthorized | JWT scaduto/mancante | Login nuovamente |
| 429 Too Many Requests | Rate limit superato | Aspetta 60s |
| No request | Frontend skip (flag false o sessionId null) | Verifica console log |

### 3. localStorage (F12 → Application → Local Storage)

**Verifica sessionId persistito:**

```javascript
// Console browser
localStorage.getItem('chat.sessionId')
```

**Output atteso**:
- ✅ `"UUID-qui"` → sessionId valido
- ❌ `null` → sessione mai inizializzata (problema)

---

## Verifiche Backend (Docker Logs)

### 1. Backend Environment

```bash
docker exec applicazione-api-1 printenv | grep PERSISTENT_MEMORY
```

**Output atteso**:
```
ENABLE_PERSISTENT_MEMORY=true
```

### 2. Backend Logs Durante Request History

```bash
docker compose logs -f api --tail=50
```

**Cerca nel log**:
- `GET /api/v1/chat/sessions/{id}/history/full` → richiesta ricevuta
- `503 Service Unavailable` → flag disabled
- `404 Not Found` → sessione senza history (normale)
- `200 OK` → success (verifica response body)

### 3. Database Connection

```bash
docker compose logs api | grep -i "database\|postgres\|connection"
```

**Possibili errori**:
- `Connection refused` → PostgreSQL non disponibile
- `Authentication failed` → credenziali errate
- `SSL required` → mismatch configurazione SSL

---

## Fix Scenarios

### Scenario A: Frontend Flag Undefined

**Causa**: Build Docker non ha usato ARG corretto

**Verifica**:
```bash
docker compose config | grep VITE_ENABLE_PERSISTENT_MEMORY
```

**Output atteso**:
```yaml
VITE_ENABLE_PERSISTENT_MEMORY: "true"
```

**Se manca o false, rebuild**:
```bash
docker compose build --no-cache web
docker compose up -d web
```

### Scenario B: Backend Flag Disabled

**Causa**: Container non ha letto `.env`

**Verifica**:
```bash
docker exec applicazione-api-1 printenv ENABLE_PERSISTENT_MEMORY
```

**Fix**:
```bash
# Restart container (legge .env automaticamente)
docker compose restart api celery-worker
```

### Scenario C: Nessun Messaggio Mai Salvato

**Causa**: Salvataggio messaggi non funziona (Story precedente)

**Test manuale**:
1. Apri chat studente
2. Scrivi messaggio: "Test persistenza"
3. Attendi risposta AI
4. Controlla backend logs:

```bash
docker compose logs api | grep -i "save\|persist\|message"
```

**Se manca log salvataggio → problema Story precedente (non 9.2)**

### Scenario D: sessionId Non Persiste

**Causa**: localStorage svuotato o bug frontend

**Fix temporaneo console browser**:
```javascript
// Genera nuovo sessionId
const newSessionId = crypto.randomUUID();
localStorage.setItem('chat.sessionId', newSessionId);
location.reload();
```

### Scenario E: Database Non Configurato

**Causa**: PostgreSQL assente o schema non migrato

**Verifica connessione**:
```bash
# Entra nel container API
docker exec -it applicazione-api-1 bash

# Test connessione database (se psql disponibile)
# Oppure verifica logs startup
exit
docker compose logs api --tail=100 | grep -i "database\|startup"
```

**Se database manca**:
```bash
# Disabilita temporaneamente persistent memory
echo "ENABLE_PERSISTENT_MEMORY=false" > .env
docker compose restart api celery-worker
```

---

## Checklist Debug Completa

**Esegui in ordine**:

- [ ] 1. Console browser: `import.meta.env.VITE_ENABLE_PERSISTENT_MEMORY` = `"true"`?
- [ ] 2. localStorage: `chat.sessionId` presente?
- [ ] 3. Network tab: GET history chiamato?
- [ ] 4. Network tab: Status response? (200/404/503/401/429)
- [ ] 5. Backend env: `docker exec applicazione-api-1 printenv ENABLE_PERSISTENT_MEMORY`
- [ ] 6. Backend logs: GET history ricevuto?
- [ ] 7. Database: PostgreSQL disponibile?
- [ ] 8. Test salvataggio: scrivi messaggio, verifica logs save

**Identifica problema**:
- Steps 1-3 fail → **problema frontend**
- Steps 4-6 fail → **problema backend**
- Step 7 fail → **problema database**
- Step 8 fail → **problema Story precedente (salvataggio)**

---

## Comando Debug Completo (Copy-Paste)

```bash
# 1. Verifica env backend
echo "=== Backend Environment ===" && docker exec applicazione-api-1 printenv | grep PERSISTENT_MEMORY

# 2. Verifica compose config
echo "=== Docker Compose Config ===" && docker compose config | grep -A2 "PERSISTENT_MEMORY\|VITE_ENABLE"

# 3. Verifica logs backend (ultimi 30 righe)
echo "=== Backend Logs (last 30) ===" && docker compose logs api --tail=30

# 4. Test health backend
echo "=== Backend Health ===" && curl -s http://localhost/health | jq .

# 5. Verifica container status
echo "=== Container Status ===" && docker compose ps
```

**Invia output di questo comando per analisi.**


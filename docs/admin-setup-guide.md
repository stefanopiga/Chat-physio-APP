# Guida Setup Utente Admin

## Problema Diagnosticato

L'applicazione richiede che gli utenti admin abbiano il campo `app_metadata.role = "admin"` nella sessione Supabase per accedere alla dashboard amministratore.

**Errore comune**: Accesso a `/admin/dashboard` mostra `AccessCodePage` (pagina studente) invece della dashboard admin.

**Causa**: Utente non ha `app_metadata.role = "admin"` configurato in Supabase Auth.

---

## Differenza tra app_metadata e user_metadata

**Supabase distingue due tipi di metadati**:

### `app_metadata` (SICURO)
- **Modificabile solo**: da admin database/backend
- **Non modificabile**: dall'utente
- **Uso**: ruoli, permessi, dati critici per sicurezza
- **Persistente**: salvato nel JWT token

### `user_metadata` (NON SICURO)
- **Modificabile**: dall'utente tramite frontend
- **Non adatto**: per ruoli/permessi
- **Uso**: preferenze UI, avatar, bio

**IMPORTANTE**: Il codice usa `app_metadata.role` per garantire che gli utenti non possano auto-promuoversi ad admin.

---

## Setup Utente Admin: Metodo 1 (Console Supabase)

### Passo 1: Accedi a Supabase Console
1. Vai a [https://supabase.com](https://supabase.com)
2. Login con le tue credenziali
3. Seleziona il progetto FisioRAG

### Passo 2: Crea Utente
1. Vai a **Authentication** → **Users**
2. Click **Add user** → **Create new user**
3. Inserisci:
   - **Email**: `admin@example.com` (tua email admin)
   - **Password**: password sicura
   - **Auto Confirm User**: ✅ (se non usi email verification)

### Passo 3: Aggiungi Ruolo Admin
1. Nella lista utenti, click sull'utente appena creato
2. Scorri fino a **Raw User Meta Data**
3. Trova sezione **App Metadata**
4. Click **Edit** o aggiungi JSON:

```json
{
  "role": "admin"
}
```


### Altrimenti segui questa procedura:

Conferma diagnosi: `raw_app_meta_data` NON contiene `"role": "admin"`.

Esegui SQL in Supabase SQL Editor:

```sql
UPDATE auth.users
SET raw_app_meta_data = jsonb_set(
  raw_app_meta_data,
  '{role}',
  '"admin"'
)
WHERE email = 'stefanopiga1976@gmail.com';
```

Verifica esecuzione:

```sql
SELECT 
  email, 
  raw_app_meta_data
FROM auth.users
WHERE email = 'stefanopiga1976@gmail.com';
```

Output atteso:
```json
{
  "role": "admin",
  "provider": "email",
  "providers": ["email"]
}
```

Procedura post-update:

1. **Logout completo** (DevTools Console):
   ```javascript
   localStorage.clear();
   sessionStorage.clear();
   location.href = '/login';
   ```

2. **Nuovo login**: `http://localhost/login`
   - Email: `stefanopiga1976@gmail.com`
   - Password: (tua password)

3. **Redirect automatico**: `/admin/dashboard` con UI cards

Nuovo token JWT conterrà `app_metadata.role = "admin"` → `AdminGuard` concederà accesso.


5. **Salva**

### Passo 4: Verifica
1. Effettua logout completo dall'applicazione
2. Vai a `http://localhost/login`
3. Login con email/password admin
4. Dovresti essere reindirizzato a `/admin/dashboard` con la nuova UI

---

## Setup Utente Admin: Metodo 2 (SQL Direct)

### Opzione A: Crea Nuovo Utente Admin

```sql
-- Crea utente tramite Supabase Auth API (da fare in Supabase SQL Editor)
-- Nota: Devi prima creare l'utente via console o API, poi eseguire:

UPDATE auth.users
SET raw_app_meta_data = jsonb_set(
  COALESCE(raw_app_meta_data, '{}'::jsonb),
  '{role}',
  '"admin"'
)
WHERE email = 'admin@example.com';
```

### Opzione B: Promuovi Utente Esistente

```sql
-- Promuovi utente esistente a admin
UPDATE auth.users
SET raw_app_meta_data = jsonb_set(
  COALESCE(raw_app_meta_data, '{}'::jsonb),
  '{role}',
  '"admin"'
)
WHERE email = 'tua-email@example.com';
```

**IMPORTANTE**: Dopo l'aggiornamento SQL, l'utente deve:
1. Effettuare logout completo
2. Effettuare nuovo login
3. Il nuovo token JWT conterrà `app_metadata.role = "admin"`

---

## Setup Utente Admin: Metodo 3 (Supabase CLI)

### Prerequisiti
```bash
npm install -g supabase
supabase login
supabase link --project-ref your-project-ref
```

### Crea Admin via Migration
Crea file: `supabase/migrations/YYYYMMDDHHMMSS_create_admin_user.sql`

```sql
-- Crea utente admin (eseguito solo una volta)
-- Nota: user_id deve essere generato o fornito
INSERT INTO auth.users (
  instance_id,
  id,
  aud,
  role,
  email,
  encrypted_password,
  email_confirmed_at,
  raw_app_meta_data,
  raw_user_meta_data,
  created_at,
  updated_at,
  confirmation_token,
  email_change,
  email_change_token_new,
  recovery_token
) VALUES (
  '00000000-0000-0000-0000-000000000000',
  gen_random_uuid(),
  'authenticated',
  'authenticated',
  'admin@example.com',
  crypt('your-secure-password', gen_salt('bf')), -- Usa password sicura
  NOW(),
  '{"role": "admin"}'::jsonb, -- QUESTO È IL CAMPO CHIAVE
  '{}'::jsonb,
  NOW(),
  NOW(),
  '',
  '',
  '',
  ''
)
ON CONFLICT (email) DO UPDATE
SET raw_app_meta_data = jsonb_set(
  COALESCE(auth.users.raw_app_meta_data, '{}'::jsonb),
  '{role}',
  '"admin"'
);
```

Applica migration:
```bash
supabase db push
```

---

## Troubleshooting

### 1. Ho effettuato login ma vedo ancora AccessCodePage

**Soluzione**:
```javascript
// Apri DevTools → Console ed esegui:
console.log(await supabase.auth.getSession());
```

Verifica output:
```json
{
  "data": {
    "session": {
      "user": {
        "app_metadata": {
          "role": "admin"  // DEVE ESSERE PRESENTE
        }
      }
    }
  }
}
```

**Se `app_metadata.role` non è "admin"**:
1. Logout completo: `localStorage.clear()` in DevTools Console
2. Riconfigura utente in Supabase (vedi metodi sopra)
3. Nuovo login

### 2. Errore "Invalid login credentials"

**Causa**: Password errata o utente non esiste

**Soluzione**:
1. Verifica utente esiste in Supabase Console → Authentication → Users
2. Reset password tramite console se necessario
3. Verifica `Auto Confirm User` sia attivo (no email verification)

### 3. Redirect loop su /admin/dashboard

**Causa**: Session esiste ma `app_metadata.role` non è "admin"

**Soluzione**:
```sql
-- Verifica role in database
SELECT email, raw_app_meta_data
FROM auth.users
WHERE email = 'tua-email@example.com';
```

Se `role` manca o è diverso da "admin", esegui:
```sql
UPDATE auth.users
SET raw_app_meta_data = '{"role": "admin"}'::jsonb
WHERE email = 'tua-email@example.com';
```

### 4. Ho modificato user_metadata invece di app_metadata

**Problema**: `user_metadata.role` NON funziona (codice controlla `app_metadata`)

**Soluzione**: Ripeti setup con `app_metadata` (vedi metodi sopra)

---

## Verifica Configurazione Corretta

### Test 1: Verifica Database
```sql
-- Esegui in Supabase SQL Editor
SELECT 
  email,
  raw_app_meta_data->'role' as role,
  created_at
FROM auth.users
WHERE raw_app_meta_data->>'role' = 'admin';
```

Output atteso:
```
email                  | role      | created_at
-----------------------|-----------|------------------
admin@example.com      | "admin"   | 2025-10-02 ...
```

### Test 2: Verifica Session Frontend
```javascript
// DevTools Console dopo login
const { data: { session } } = await supabase.auth.getSession();
console.log('Role:', session?.user?.app_metadata?.role);
// Output atteso: "admin"
```

### Test 3: Verifica AuthService
```javascript
// DevTools Console
import { authService } from '@/services/authService';
const { data: { session } } = await authService.getSession();
console.log('Is Admin:', authService.isAdmin(session));
// Output atteso: true
```

---

## Best Practices

### 1. Password Sicura
- Minimo 12 caratteri
- Mix: maiuscole, minuscole, numeri, simboli
- Non riutilizzare password

### 2. Email Verification
Se attivi email verification:
- Utente deve confermare email prima del primo login
- O usa `Auto Confirm User` in fase creazione utente

### 3. Multi-Admin Setup
Per creare più admin:
```sql
-- Template per creare più admin
UPDATE auth.users
SET raw_app_meta_data = jsonb_set(
  COALESCE(raw_app_meta_data, '{}'::jsonb),
  '{role}',
  '"admin"'
)
WHERE email IN (
  'admin1@example.com',
  'admin2@example.com',
  'admin3@example.com'
);
```

### 4. Role-Based Access Control (RBAC)
Per future estensioni:
```json
{
  "role": "admin",
  "permissions": ["debug", "analytics", "user_management"],
  "department": "IT"
}
```

---

## Security Notes

### Perché app_metadata?
1. **Immutabilità**: Utente NON può modificare il proprio ruolo via frontend
2. **JWT Integrity**: Il ruolo è codificato nel token firmato da Supabase
3. **RLS Policies**: Le policy Row-Level Security controllano `app_metadata.role`

### Esempio Policy RLS Sicura
```sql
-- Solo admin possono vedere access_code table
create policy "access_code_select_admin"
on public.access_code
for select
to authenticated
using (
  (select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin'
);
```

### ⚠️ NON USARE user_metadata per Ruoli
```javascript
// ❌ INSICURO (utente può modificare)
session.user.user_metadata.role = "admin"; 

// ✅ SICURO (solo backend/admin può modificare)
session.user.app_metadata.role = "admin";
```

---

## Riferimenti

- [Supabase Auth: User Management](https://supabase.com/docs/guides/auth/managing-user-data)
- [Supabase Auth: Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)
- [JWT Claims: app_metadata vs user_metadata](https://supabase.com/docs/guides/auth/auth-helpers/auth-ui)
- Codice sorgente: `apps/web/src/services/authService.ts` (linee 66-70)

---

## Analytics Dashboard (Story 4.2)

La dashboard analytics fornisce insight aggregati sull'utilizzo del sistema RAG da parte degli studenti.

### Accesso

1. Login come admin su `http://localhost/login`
2. Dalla `/admin/dashboard`, click su card **"Analytics Dashboard"**
3. Redirect automatico a `/admin/analytics`

### Funzionalità

**Sezione Panoramica**:
- **Domande Totali**: conteggio query utenti
- **Sessioni Attive**: numero sessioni chat in-memory
- **Feedback Positivo**: ratio thumbs up/(up+down) espresso in %
- **Latenza Media**: tempo medio risposta AG (ms)

**Sezione Domande Più Frequenti**:
- Tabella top 10 query ordinate per occorrenze
- Colonne: testo domanda, conteggio, ultimo timestamp query
- Normalizzazione case-insensitive per aggregazione

**Sezione Feedback Aggregato**:
- Bar chart visualizzazione thumbs up/down con Recharts
- Ratio positivo calcolato e displayato sotto grafico

**Sezione Performance Sistema**:
- Card P95 Latency (95° percentile tempo risposta)
- Card P99 Latency (99° percentile tempo risposta)
- Badge warning se P95/P99 > 2000ms
- Conteggio campioni latency tracciati

**Bottone "Aggiorna Dati"**: refresh manuale analytics (no auto-refresh per contenere costi API)

### Limitazioni MVP

**Dati volatili (tech debt R-4.2-1)**:
- Analytics aggregati da store in-memory: `chat_messages_store`, `feedback_store`, `ag_latency_samples_ms`
- Dati persi al restart container API
- Persistenza Supabase pianificata per Phase 2 (Story 4.2.1)

**Rate limiting**:
- Endpoint `/api/v1/admin/analytics`: 30 richieste/ora per admin
- Protezione contro query analytics costose

### Privacy

- Session IDs hashati (SHA256, 16 caratteri) prima dell'esposizione in analytics
- Nessun `user_id` o PII esposto in dashboard
- Audit log eventi `analytics_accessed` con `user_id` admin e conteggi aggregati

### Troubleshooting

**Dashboard mostra tutti zeri**:
- Causa: nessun documento ingerito, nessuna query studenti, nessun feedback
- Soluzione: eseguire almeno 1 query studente con feedback per popolare dati

**Errore 403 Forbidden**:
- Causa: utente non ha `app_metadata.role = "admin"`
- Soluzione: vedi sezioni Setup Utente Admin sopra

**Errore 429 Too Many Requests**:
- Causa: superato rate limit 30 richieste/ora
- Soluzione: attendere reset finestra oraria

### API Reference

**Endpoint**: `GET /api/v1/admin/analytics`

**Headers**:
```
Authorization: Bearer <jwt_token>
```

**Response** (200 OK):
```json
{
  "overview": {
    "total_queries": 150,
    "total_sessions": 25,
    "feedback_ratio": 0.75,
    "avg_latency_ms": 450
  },
  "top_queries": [
    {
      "query_text": "cos'è la scoliosi?",
      "count": 10,
      "last_queried_at": "2025-10-02T10:00:00Z"
    }
  ],
  "feedback_summary": {
    "thumbs_up": 45,
    "thumbs_down": 15,
    "ratio": 0.75
  },
  "performance_metrics": {
    "latency_p95_ms": 800,
    "latency_p99_ms": 1200,
    "sample_count": 150
  }
}
```

**Errors**:
- `401 Unauthorized`: token mancante/invalido
- `403 Forbidden`: utente non admin
- `429 Too Many Requests`: rate limit superato

---

## Appendice: Database Connectivity Debug

- Verificare che `.env` contenga `DATABASE_URL` con endpoint Supabase **pooler** (`...supabase.com:6543` + `sslmode=require`).
- Eseguire lo script `poetry run python ../../scripts/validation/database_connectivity_test.py` da `apps/api` per confermare la connessione (lo script mostra host/porta e gestisce PgBouncer).
- In caso di errori, seguire la guida dettagliata in `docs/troubleshooting/database-connectivity.md` (DNS, firewall, credenziali, SSL).

## Changelog Fix

**Commit**: `79a35b5` - fix(auth): use app_metadata.role instead of user_metadata.role

**Breaking Change**: Utenti admin creati prima di questo fix devono essere riconfigurati con `app_metadata.role = "admin"`.

**Migration Path**:
```sql
-- Migra utenti esistenti da user_metadata a app_metadata
UPDATE auth.users
SET raw_app_meta_data = jsonb_set(
  COALESCE(raw_app_meta_data, '{}'::jsonb),
  '{role}',
  raw_user_meta_data->'role'
)
WHERE raw_user_meta_data->>'role' = 'admin'
  AND (raw_app_meta_data->>'role' IS NULL 
       OR raw_app_meta_data->>'role' != 'admin');
```


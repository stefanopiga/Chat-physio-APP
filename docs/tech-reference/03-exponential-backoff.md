# Exponential Backoff e Retry Logic

## node-retry

**Installazione:**
```bash
npm install retry
```

**Esempio base con DNS resolve:**
```javascript
const dns = require('dns');
const retry = require('retry');

function faultTolerantResolve(address, cb) {
  const operation = retry.operation();
  
  operation.attempt(function(currentAttempt) {
    dns.resolve(address, function(err, addresses) {
      if (operation.retry(err)) {
        return;
      }
      cb(err ? operation.mainError() : null, addresses);
    });
  });
}
```

**Configurazione:**
```javascript
const operation = retry.operation({
  retries: 5,           // Max tentativi
  factor: 3,            // Fattore esponenziale
  minTimeout: 1 * 1000, // Timeout minimo (ms)
  maxTimeout: 60 * 1000,// Timeout massimo (ms)
  randomize: true,      // Randomizzazione
});
```

**Con Promises:**
```javascript
const retry = require('retry');
const delay = require('delay');

function retryer() {
  let operation = retry.operation();
  
  return new Promise((resolve, reject) => {
    operation.attempt(async currentAttempt => {
      console.log('Attempt #:', currentAttempt);
      
      await delay(2000);
      
      const err = !isItGood[numAttempt] ? true : null;
      
      if (operation.retry(err)) {
        numAttempt++;
        return;
      }
      
      if (isItGood[numAttempt]) {
        resolve('All good!');
      } else {
        reject(operation.mainError());
      }
    });
  });
}
```

**Formula timeout:**
```
Math.min(random * minTimeout * Math.pow(factor, attempt), maxTimeout)
```

**API Principale:**

`retry.operation([options])` - Crea RetryOperation
- forever: boolean - Retry infinito
- unref: boolean - Unref setTimeout
- maxRetryTime: number - Tempo massimo totale (ms)

`operation.attempt(fn)` - Esegue funzione con retry
- currentAttempt passato come parametro

`operation.retry(error)` - Determina se ritentare
- Ritorna true se deve ritentare
- Ritorna false se raggiunto max o nessun errore

`operation.mainError()` - Errore più frequente

`operation.errors()` - Array tutti errori (cronologico)

`operation.stop()` - Ferma retry operation

`operation.reset()` - Reset stato interno

**Repository:** https://github.com/tim-kos/node-retry

---

## Pattern Retry-After Header

**Gestione header HTTP:**
```javascript
async function fetchWithRetry(url, options = {}) {
  const operation = retry.operation({
    retries: 5,
    minTimeout: 1000,
    maxTimeout: 30000,
  });
  
  return new Promise((resolve, reject) => {
    operation.attempt(async (currentAttempt) => {
      try {
        const response = await fetch(url, options);
        
        if (response.status === 429 || response.status >= 500) {
          // Leggi Retry-After header
          const retryAfter = response.headers.get('Retry-After');
          const waitTime = retryAfter 
            ? parseInt(retryAfter) * 1000 
            : null;
          
          const error = new Error(`HTTP ${response.status}`);
          error.retryAfter = waitTime;
          
          if (!operation.retry(error)) {
            reject(operation.mainError());
          }
          return;
        }
        
        resolve(response);
      } catch (err) {
        if (!operation.retry(err)) {
          reject(operation.mainError());
        }
      }
    });
  });
}
```

---

## Best Practices

**Retry Strategy:**
- Inizia con timeout brevi (1-2s)
- Factor 2-3 per crescita esponenziale
- Cap massimo realistico (30-60s)
- Randomize per evitare thundering herd

**Retry Conditions:**
- Network errors: sempre
- 5xx errors: sempre
- 429 Rate Limit: con Retry-After
- 4xx errors: mai (eccetto 408, 429)

**Error Handling:**
- Tracking tentativi con currentAttempt
- Log errori intermedi
- Usa mainError() per errore finale
- Stop su errori non recuperabili

**Testing:**
- Mock failures con counter
- Verifica exponential growth
- Test max retries raggiunto
- Verifica Retry-After rispettato

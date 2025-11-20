# Quick Start - Performance Testing

## Build e Test Rapido

### 1. Build Production
```bash
cd /workspace/apps/web
npm run build
```

Output atteso:
```
✓ built in XXXms
dist/index.html                   X.XX kB
dist/assets/react-vendor-XXX.js   ~130 kB │ gzip: ~45 kB
dist/assets/ui-vendor-XXX.js      ~80 kB  │ gzip: ~28 kB
dist/assets/charts-XXX.js         ~100 kB │ gzip: ~35 kB
dist/assets/supabase-XXX.js       ~100 kB │ gzip: ~32 kB
```

### 2. Preview Build
```bash
npm run preview
```

Apri browser a `http://localhost:4173`

### 3. Verifica Code Splitting

**Nel browser (DevTools > Network):**
1. Apri `/login` - carica solo LoginPage chunk
2. Naviga a `/chat` - carica ChatPage chunk on-demand
3. Naviga a `/admin/analytics` - carica AnalyticsPage + charts chunk
4. Verifica che chunks vendor sono cached

**Chunks attesi:**
- `react-vendor-*.js` (caricato all'avvio)
- `LoginPage-*.js` (lazy)
- `ChatPage-*.js` (lazy)
- `AnalyticsPage-*.js` (lazy)
- `charts-*.js` (lazy, solo su AnalyticsPage)

### 4. Test Performance con Lighthouse

**Chrome DevTools:**
1. F12 > Lighthouse
2. Mode: Navigation (default)
3. Device: Mobile
4. Categories: Performance
5. Click "Analyze page load"

**Metriche target (Mobile):**
- Performance Score: **>90**
- First Contentful Paint: **<1.5s**
- Largest Contentful Paint: **<2.5s**
- Time to Interactive: **<3s**
- Cumulative Layout Shift: **<0.1**

### 5. Verifica Memoization

**React DevTools Profiler:**
1. Installa React DevTools
2. Apri Profiler tab
3. Start recording
4. Invia messaggio in chat
5. Stop recording
6. Verifica che ChatMessagesList non re-renderizza tutti i messaggi esistenti

### 6. Bundle Analysis (opzionale)

**Installa visualizer:**
```bash
npm install --save-dev rollup-plugin-visualizer
```

**Aggiungi a vite.config.ts:**
```typescript
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [
    // ... altri plugins
    visualizer({
      open: true,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  // ...
});
```

**Run:**
```bash
npm run build
```

Browser aprirà automaticamente con visualizzazione tree-map del bundle.

## Metriche da Monitorare

### Core Web Vitals
- **LCP** (Largest Contentful Paint): < 2.5s
- **FID** (First Input Delay): < 100ms
- **CLS** (Cumulative Layout Shift): < 0.1

### Custom Metrics
- **Initial Bundle Size**: < 400KB
- **Time to First Byte**: < 600ms
- **First Contentful Paint**: < 1.2s

## Troubleshooting

### Bundle troppo grande
1. Verifica manual chunks in `vite.config.ts`
2. Controlla import non ottimizzati (barrel imports)
3. Usa bundle analyzer per identificare librerie pesanti

### Chunk non caricato lazy
1. Verifica `React.lazy()` in `App.tsx`
2. Controlla che Suspense wrapper sia presente
3. DevTools Network: verifica richieste on-demand

### Re-render eccessivi
1. React DevTools Profiler: identifica componenti
2. Verifica che `React.memo()` sia applicato
3. Controlla dependencies array di useCallback/useMemo

### Cache API non funziona
1. Verifica parameter `useCache=true` in `apiClient.get()`
2. Controlla console per errori
3. TTL configurato in `apiClient.ts` (default 5min)

## Performance Checklist

- [ ] Build production completata senza errori
- [ ] Bundle size < 1MB (total)
- [ ] Initial bundle < 400KB
- [ ] Chunks vendor separati visibili in dist/
- [ ] Lighthouse score > 90
- [ ] LCP < 2.5s
- [ ] Code splitting funzionante (Network tab)
- [ ] Memoization riduce re-renders (Profiler)
- [ ] API cache riduce chiamate duplicate

## Comandi Utili

```bash
# Development
npm run dev

# Production build
npm run build

# Preview production build
npm run preview

# Run tests
npm test

# Bundle analysis
npm run build:analyze

# Lint
npm run lint
```

## Risorse

- [Vite Performance](https://vitejs.dev/guide/performance.html)
- [React Performance](https://react.dev/learn/render-and-commit)
- [Web Vitals](https://web.dev/vitals/)
- [Bundle Analysis](https://github.com/btd/rollup-plugin-visualizer)

---

Ultima revisione: 2025-11-20

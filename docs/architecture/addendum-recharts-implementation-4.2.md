# Addendum: Recharts Implementation Guide - Story 4.2

**Date**: 2025-10-02  
**Author**: Tech Lead  
**Purpose**: Documentazione tecnica di supporto per implementazione grafici Story 4.2 usando Recharts  
**Target**: Developer che implementerà Analytics Dashboard

---

## 1. Installazione

```bash
cd apps/web
pnpm add recharts
```

**Versione target**: `recharts@^2.x` (compatibile con React 18)

---

## 2. Pattern TypeScript per Chart Data

### Feedback Chart Data

```typescript
// apps/web/src/pages/AnalyticsPage.tsx

type FeedbackChartData = {
  name: string;
  count: number;
};

// Esempio trasformazione da API response
const transformFeedbackData = (summary: FeedbackSummary): FeedbackChartData[] => [
  { name: 'Thumbs Up', count: summary.thumbs_up },
  { name: 'Thumbs Down', count: summary.thumbs_down },
];
```

### Performance Chart Data

```typescript
type PerformanceChartData = {
  timestamp: string; // ISO datetime o HH:mm
  p95: number;       // latency ms
  p99: number;       // latency ms
};

// Per MVP: dati statici single-point (no trend temporale)
const mockPerformanceData: PerformanceChartData[] = [
  { 
    timestamp: new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' }),
    p95: performance_metrics.latency_p95_ms,
    p99: performance_metrics.latency_p99_ms
  }
];
```

---

## 3. Feedback Bar Chart - Codice Completo

```typescript
import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';

type FeedbackChartData = {
  name: string;
  count: number;
};

interface FeedbackBarChartProps {
  data: FeedbackChartData[];
}

const FeedbackBarChart: React.FC<FeedbackBarChartProps> = ({ data }) => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart
        data={data}
        margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis 
          dataKey="name" 
          tick={{ fill: '#6b7280' }}
          axisLine={{ stroke: '#d1d5db' }}
        />
        <YAxis 
          tick={{ fill: '#6b7280' }}
          axisLine={{ stroke: '#d1d5db' }}
        />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '8px'
          }}
          cursor={{ fill: 'rgba(59, 130, 246, 0.1)' }}
        />
        <Legend />
        <Bar 
          dataKey="count" 
          fill="#22c55e"  // Tailwind green-500
          radius={[8, 8, 0, 0]}  // Rounded top corners
        />
      </BarChart>
    </ResponsiveContainer>
  );
};

export default FeedbackBarChart;
```

**Usage in AnalyticsPage**:
```typescript
const feedbackData = transformFeedbackData(analytics.feedback_summary);

<section className="space-y-4">
  <h2 className="text-2xl font-semibold">Feedback Aggregato</h2>
  <FeedbackBarChart data={feedbackData} />
  <p className="text-sm text-muted-foreground">
    Ratio positivo: {(analytics.feedback_summary.ratio * 100).toFixed(1)}%
  </p>
</section>
```

---

## 4. Performance Line Chart - Codice Completo

```typescript
import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

type PerformanceChartData = {
  timestamp: string;
  p95: number;
  p99: number;
};

interface PerformanceLineChartProps {
  data: PerformanceChartData[];
}

const PerformanceLineChart: React.FC<PerformanceLineChartProps> = ({ data }) => {
  return (
    <ResponsiveContainer width="100%" height={350}>
      <LineChart
        data={data}
        margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis 
          dataKey="timestamp" 
          tick={{ fill: '#6b7280' }}
          axisLine={{ stroke: '#d1d5db' }}
        />
        <YAxis 
          label={{ 
            value: 'Latency (ms)', 
            angle: -90, 
            position: 'insideLeft',
            style: { fill: '#6b7280' }
          }}
          tick={{ fill: '#6b7280' }}
          axisLine={{ stroke: '#d1d5db' }}
        />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '8px'
          }}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="p95"
          name="P95 Latency"
          stroke="#3b82f6"  // Tailwind blue-500
          strokeWidth={2}
          activeDot={{ r: 6 }}
          dot={{ fill: '#3b82f6', r: 4 }}
        />
        <Line
          type="monotone"
          dataKey="p99"
          name="P99 Latency"
          stroke="#ef4444"  // Tailwind red-500
          strokeWidth={2}
          activeDot={{ r: 6 }}
          dot={{ fill: '#ef4444', r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default PerformanceLineChart;
```

**Usage with Threshold Highlighting**:
```typescript
<section className="space-y-4">
  <h2 className="text-2xl font-semibold">Performance Sistema</h2>
  
  {/* Performance Cards */}
  <div className="grid gap-4 md:grid-cols-2">
    <Card>
      <CardHeader>
        <CardTitle>P95 Latency</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <span className="text-3xl font-bold">
            {analytics.performance_metrics.latency_p95_ms}ms
          </span>
          {analytics.performance_metrics.latency_p95_ms > 2000 && (
            <Badge variant="destructive">⚠ High</Badge>
          )}
        </div>
      </CardContent>
    </Card>
    {/* Similar card for P99 */}
  </div>

  {/* Line Chart (opzionale MVP) */}
  <PerformanceLineChart data={performanceData} />
</section>
```

---

## 5. Integrazione con Tailwind CSS Theming

### Pattern per Dark Mode Support

```typescript
// Definire colori dinamici basati su tema corrente
import { useTheme } from '@/hooks/useTheme'; // assumendo hook esistente

const FeedbackBarChartThemed: React.FC<FeedbackBarChartProps> = ({ data }) => {
  const { theme } = useTheme();
  
  const gridColor = theme === 'dark' ? '#374151' : '#e5e7eb';
  const textColor = theme === 'dark' ? '#9ca3af' : '#6b7280';
  const tooltipBg = theme === 'dark' ? '#1f2937' : '#ffffff';
  
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
        <XAxis dataKey="name" tick={{ fill: textColor }} />
        <YAxis tick={{ fill: textColor }} />
        <Tooltip contentStyle={{ backgroundColor: tooltipBg, color: textColor }} />
        <Bar dataKey="count" fill="#22c55e" />
      </BarChart>
    </ResponsiveContainer>
  );
};
```

### CSS Variables Approach (Raccomandato)

```css
/* apps/web/src/index.css */
:root {
  --chart-grid: #e5e7eb;
  --chart-text: #6b7280;
  --chart-tooltip-bg: #ffffff;
  --chart-success: #22c55e;
  --chart-danger: #ef4444;
  --chart-primary: #3b82f6;
}

.dark {
  --chart-grid: #374151;
  --chart-text: #9ca3af;
  --chart-tooltip-bg: #1f2937;
}
```

```typescript
// Componente usa CSS vars
<CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
<XAxis dataKey="name" tick={{ fill: 'var(--chart-text)' }} />
<Bar dataKey="count" fill="var(--chart-success)" />
```

---

## 6. Responsive Breakpoints

Recharts `ResponsiveContainer` gestisce automaticamente la width. Per height responsive:

```typescript
const useResponsiveChartHeight = () => {
  const [height, setHeight] = useState(300);
  
  useEffect(() => {
    const updateHeight = () => {
      if (window.innerWidth < 768) {
        setHeight(250);  // Mobile
      } else if (window.innerWidth < 1024) {
        setHeight(300);  // Tablet
      } else {
        setHeight(400);  // Desktop
      }
    };
    
    updateHeight();
    window.addEventListener('resize', updateHeight);
    return () => window.removeEventListener('resize', updateHeight);
  }, []);
  
  return height;
};

// Usage
const chartHeight = useResponsiveChartHeight();
<ResponsiveContainer width="100%" height={chartHeight}>
  {/* Chart */}
</ResponsiveContainer>
```

---

## 7. Testing Considerations

### Unit Test con Recharts

```typescript
// apps/web/src/pages/__tests__/AnalyticsPage.test.tsx

import { render, screen } from '@testing-library/react';
import AnalyticsPage from '../AnalyticsPage';

describe('AnalyticsPage - Charts', () => {
  it('renders feedback bar chart with correct data', () => {
    const mockAnalytics = {
      feedback_summary: { thumbs_up: 45, thumbs_down: 12, ratio: 0.789 }
    };
    
    render(<AnalyticsPage analytics={mockAnalytics} />);
    
    // Recharts rende SVG elements
    const barChart = screen.getByRole('img', { hidden: true }); // ResponsiveContainer
    expect(barChart).toBeInTheDocument();
  });
  
  it('displays performance line chart (if implemented)', () => {
    // Test specifico per LineChart
  });
});
```

### E2E Test (Playwright)

```typescript
// apps/web/tests/story-4.2.spec.ts

test('analytics dashboard displays charts', async ({ page }) => {
  // Setup admin session
  await setupAdminSession(page);
  
  await page.goto('/admin/analytics');
  
  // Recharts rende canvas/SVG
  await expect(page.locator('svg.recharts-surface')).toBeVisible({ timeout: 5000 });
  
  // Verifica presenza elementi specifici chart
  await expect(page.locator('text=Thumbs Up')).toBeVisible();
  await expect(page.locator('text=Thumbs Down')).toBeVisible();
});
```

---

## 8. Performance Optimization

### Lazy Loading Recharts

```typescript
// apps/web/src/pages/AnalyticsPage.tsx

import React, { lazy, Suspense } from 'react';

const FeedbackBarChart = lazy(() => import('@/components/charts/FeedbackBarChart'));
const PerformanceLineChart = lazy(() => import('@/components/charts/PerformanceLineChart'));

const AnalyticsPage: React.FC = () => {
  return (
    <div>
      <Suspense fallback={<ChartSkeleton />}>
        <FeedbackBarChart data={feedbackData} />
      </Suspense>
      
      <Suspense fallback={<ChartSkeleton />}>
        <PerformanceLineChart data={performanceData} />
      </Suspense>
    </div>
  );
};
```

### Memoization

```typescript
const MemoizedFeedbackChart = React.memo(FeedbackBarChart, (prev, next) => {
  return (
    prev.data[0]?.count === next.data[0]?.count &&
    prev.data[1]?.count === next.data[1]?.count
  );
});
```

---

## 9. Accessibility

### ARIA Labels per Charts

```typescript
<ResponsiveContainer width="100%" height={300}>
  <BarChart 
    data={data}
    aria-label="Bar chart showing feedback distribution with thumbs up and thumbs down counts"
  >
    {/* Chart content */}
  </BarChart>
</ResponsiveContainer>
```

### Tooltip Accessibile

```typescript
<Tooltip 
  contentStyle={{ backgroundColor: '#fff', border: '1px solid #ccc' }}
  wrapperStyle={{ outline: 'none' }}
  cursor={{ fill: 'rgba(59, 130, 246, 0.1)' }}
  accessibilityLayer  // Recharts v2.x feature
/>
```

---

## 10. Troubleshooting

### Problema: Chart non visibile

**Causa**: `ResponsiveContainer` richiede parent con height definito.

**Soluzione**:
```typescript
<div className="h-[300px]">  {/* Tailwind height class */}
  <ResponsiveContainer width="100%" height="100%">
    <BarChart data={data}>
      {/* ... */}
    </BarChart>
  </ResponsiveContainer>
</div>
```

### Problema: TypeScript errors con Recharts types

**Soluzione**: Installare types se necessario (Recharts v2.x include types built-in)
```bash
pnpm add -D @types/recharts  # Solo se necessario
```

### Problema: Bundle size grande

**Soluzione**: Tree-shaking automatico con import specifici
```typescript
// ✅ Good
import { BarChart, Bar, XAxis } from 'recharts';

// ❌ Bad (import tutto)
import * as Recharts from 'recharts';
```

---

## 11. Quick Reference - Component Imports

### Feedback Bar Chart
```typescript
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
```

### Performance Line Chart
```typescript
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
```

### Optional Components
```typescript
import { Legend, Label, ReferenceLine, ReferenceArea } from 'recharts';
```

---

## References

- **Recharts Official**: https://recharts.org/
- **Recharts GitHub**: https://github.com/recharts/recharts
- **npm Package**: https://www.npmjs.com/package/recharts
- **TypeScript Guide**: Medium - "A Guide to Creating Charts in React with TypeScript" (Brad Dirheimer)
- **Material Tailwind Examples**: https://www.material-tailwind.com/v3/blocks/charts

---

**Last Updated**: 2025-10-02  
**Reviewer**: Tech Lead  
**Status**: Ready for Implementation


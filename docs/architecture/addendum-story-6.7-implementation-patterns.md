# Addendum: Story 6.7 Implementation Patterns

**Date:** 2025-01-21  
**Scope:** Technical implementation patterns for UI/UX enhancements  
**Type:** Implementation Guide

---

## Document Purpose

Questo addendum fornisce pattern tecnici dettagliati per l'implementazione dei miglioramenti UI/UX della Story 6.7, includendo esempi di codice completi, soluzioni ai problemi comuni e best practices di accessibilità.

---

## 1. Navigation Component Pattern

### 1.1 Basic Structure

```tsx
// apps/web/src/components/Navigation.tsx
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';

const Navigation: React.FC = () => {
  const location = useLocation();

  const navLinks = [
    { path: '/chat', label: 'Chat Studente' },
    { path: '/admin/dashboard', label: 'Dashboard Admin' },
    { path: '/login', label: 'Admin Login' },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="border-b bg-background">
      <div className="mx-auto max-w-7xl px-4">
        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-6 h-16">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              className={cn(
                "px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive(link.path)
                  ? "bg-accent text-accent-foreground"
                  : "text-foreground/60 hover:text-foreground hover:bg-accent/50"
              )}
              aria-current={isActive(link.path) ? 'page' : undefined}
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* Mobile Navigation - Simplified */}
        <div className="md:hidden flex items-center justify-between h-16">
          <span className="font-medium text-sm">
            {navLinks.find(l => isActive(l.path))?.label || 'FisioRAG'}
          </span>
          {/* Mobile menu button - implement with Sheet if needed */}
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
```

### 1.2 Mobile Navigation with Sheet (Optional)

```tsx
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Menu } from 'lucide-react'; // or any icon library

const Navigation: React.FC = () => {
  const [open, setOpen] = useState(false);
  // ... resto del componente

  return (
    <nav className="border-b bg-background">
      <div className="mx-auto max-w-7xl px-4">
        {/* Desktop - same as above */}
        
        {/* Mobile */}
        <div className="md:hidden flex items-center justify-between h-16">
          <span className="font-medium">FisioRAG</span>
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <button
                aria-label="Apri menu navigazione"
                className="p-2 rounded-md hover:bg-accent"
              >
                <Menu className="h-6 w-6" />
              </button>
            </SheetTrigger>
            <SheetContent side="left">
              <nav className="flex flex-col gap-4 mt-8">
                {navLinks.map((link) => (
                  <Link
                    key={link.path}
                    to={link.path}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "px-4 py-2 rounded-md text-base font-medium",
                      isActive(link.path) && "bg-accent"
                    )}
                  >
                    {link.label}
                  </Link>
                ))}
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </nav>
  );
};
```

### 1.3 Integration in App.tsx

```tsx
// apps/web/src/App.tsx
import Navigation from './components/Navigation';

function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen">
        <Navigation />
        <main className="flex-1">
          <Routes>
            {/* routes */}
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
```

---

## 2. Loading Indicator In-Chat Pattern

### 2.1 LoadingIndicator Component

```tsx
// apps/web/src/components/LoadingIndicator.tsx
import React from 'react';

const LoadingIndicator: React.FC = () => {
  return (
    <div
      className="self-start bg-muted max-w-[75%] rounded-md p-2"
      role="status"
      aria-live="polite"
      aria-label="L'assistente sta preparando la risposta"
    >
      <div className="text-[12px] opacity-70">assistant</div>
      <div className="flex items-center gap-2">
        <span className="text-sm">L'assistente sta pensando</span>
        <span className="flex gap-1">
          <span className="animate-bounce delay-0">.</span>
          <span className="animate-bounce delay-100">.</span>
          <span className="animate-bounce delay-200">.</span>
        </span>
      </div>
    </div>
  );
};

export default LoadingIndicator;
```

### 2.2 Tailwind Config for Animation Delays

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      animation: {
        bounce: 'bounce 1.4s infinite',
      },
      keyframes: {
        bounce: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-25%)' },
        },
      },
    },
  },
};

// In CSS for delays (add to index.css or component):
// .delay-0 { animation-delay: 0ms; }
// .delay-100 { animation-delay: 100ms; }
// .delay-200 { animation-delay: 200ms; }
```

### 2.3 Integration in ChatMessagesList

```tsx
// apps/web/src/components/ChatMessagesList.tsx
import LoadingIndicator from './LoadingIndicator';

type Props = {
  messages: ChatMessage[];
  loading?: boolean; // NUOVO
};

const ChatMessagesList: React.FC<Props> = ({ messages, loading = false }) => {
  const [pendingFeedback, setPendingFeedback] = useState<string | null>(null);
  const [openCitation, setOpenCitation] = useState<string | null>(null);

  // ... resto del componente

  return (
    <div className="flex flex-col gap-2" data-testid="chat-messages-list">
      {messages.map((m) => (
        // ... rendering messaggi esistente
      ))}
      
      {/* NUOVO: Loading indicator in-chat */}
      {loading && <LoadingIndicator />}
    </div>
  );
};
```

### 2.4 Update ChatPage

```tsx
// apps/web/src/pages/ChatPage.tsx
// RIMUOVERE questa riga (97):
// {loading && <div aria-live="polite" data-testid="chat-loading-indicator">Caricamento...</div>}

// AGGIORNARE il componente ChatMessagesList:
<ChatMessagesList messages={messages} loading={loading} />
```

---

## 3. Full-Height Chat Layout Pattern

### 3.1 ChatPage Layout Structure

```tsx
// apps/web/src/pages/ChatPage.tsx
const ChatPage: React.FC = () => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  // ... stato esistente

  // Auto-scroll al bottom quando arrivano nuovi messaggi
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-screen">
      {/* Header - fisso in alto */}
      <div className="flex-shrink-0 p-4 border-b">
        <div className="flex items-center justify-between max-w-[800px] mx-auto">
          <h1>Chat</h1>
          <div className="flex items-center gap-3">
            <div className="text-[12px] opacity-70">
              Sessione: {sessionId || "-"}
            </div>
            <HelpModal />
          </div>
        </div>
      </div>

      {/* Error message - se presente */}
      {error && (
        <div className="flex-shrink-0 px-4 pt-2">
          <div
            role="alert"
            className="text-destructive max-w-[800px] mx-auto"
            data-testid="chat-error-message"
          >
            {error}
          </div>
        </div>
      )}

      {/* Chat messages - scroll area che cresce */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-[800px] mx-auto">
          <div
            className="rounded-lg border border-border bg-card p-3 text-card-foreground"
            data-testid="chat-messages-container"
          >
            <ChatMessagesList messages={messages} loading={loading} />
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      {/* Input - fisso in basso */}
      <div className="flex-shrink-0 p-4 border-t bg-background">
        <div className="max-w-[800px] mx-auto">
          <ChatInput onSubmit={handleSubmit} loading={loading} />
        </div>
      </div>
    </div>
  );
};
```

### 3.2 Responsive Adjustments

```tsx
// Per mobile, considerare virtual keyboard:
useEffect(() => {
  const handleResize = () => {
    // Force scroll to bottom on keyboard show/hide
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  window.addEventListener('resize', handleResize);
  return () => window.removeEventListener('resize', handleResize);
}, []);
```

---

## 4. Auto-Resize Textarea Pattern

### 4.1 Complete ChatInput with Auto-Resize

```tsx
// apps/web/src/components/ChatInput.tsx
import React, { useState, useRef, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea"; // Se disponibile

type Props = {
  onSubmit: (question: string) => Promise<void> | void;
  loading?: boolean;
};

const ChatInput: React.FC<Props> = ({ onSubmit, loading }) => {
  const [question, setQuestion] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize logic
  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = 'auto'; // Reset
    const scrollHeight = textarea.scrollHeight;
    const maxHeight = 96; // 4 righe * ~24px = 96px

    textarea.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
  };

  useEffect(() => {
    adjustHeight();
  }, [question]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    await onSubmit(q);
    setQuestion("");
    // Reset height after submit
    setTimeout(() => adjustHeight(), 0);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
    // Shift+Enter: default behavior (newline)
  };

  const isDisabled = !!loading || question.trim().length === 0;

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2" data-testid="chat-input-form">
      <textarea
        ref={textareaRef}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Inserisci la tua domanda..."
        disabled={!!loading}
        rows={1}
        data-testid="chat-input-field"
        className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none overflow-y-auto max-h-24"
      />
      <button
        type="submit"
        disabled={isDisabled}
        data-testid="chat-submit-button"
        className="inline-flex items-center justify-center whitespace-nowrap rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50 self-end"
      >
        {loading ? "Invio..." : "Invia"}
      </button>
    </form>
  );
};

export default ChatInput;
```

### 4.2 Using Shadcn Textarea Component

```tsx
// Se usi Shadcn Textarea component:
import { Textarea } from "@/components/ui/textarea";

// Nel rendering:
<Textarea
  ref={textareaRef}
  value={question}
  onChange={(e) => setQuestion(e.target.value)}
  onKeyDown={handleKeyDown}
  placeholder="Inserisci la tua domanda..."
  disabled={!!loading}
  rows={1}
  className="resize-none overflow-y-auto max-h-24"
  data-testid="chat-input-field"
/>
```

### 4.3 Install Shadcn Textarea

```bash
cd apps/web
pnpm dlx shadcn@latest add textarea
```

**File creato:** `apps/web/src/components/ui/textarea.tsx`

---

## 5. Vertical Centering Pattern for Forms

### 5.1 LoginPage Centered Layout

```tsx
// apps/web/src/pages/LoginPage.tsx
const LoginPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // handleLogin logic unchanged...

  return (
    <div className="flex min-h-screen items-center justify-center p-4 bg-background">
      <div className="mx-auto w-full max-w-md space-y-4">
        <h1 className="text-2xl font-semibold text-center">Admin Login</h1>
        <form onSubmit={handleLogin} className="space-y-3">
          {/* form fields unchanged... */}
        </form>
      </div>
    </div>
  );
};
```

### 5.2 AccessCodePage Centered Layout

```tsx
// apps/web/src/pages/AccessCodePage.tsx
const AccessCodePage: React.FC = () => {
  // ... state unchanged

  return (
    <div className="flex min-h-screen items-center justify-center p-4 bg-background">
      <div className="mx-auto w-full max-w-md space-y-4">
        <h1 className="text-2xl font-semibold text-center">Accesso Studente</h1>
        <form onSubmit={onSubmit} className="space-y-3">
          {/* form fields unchanged... */}
        </form>
      </div>
    </div>
  );
};
```

### 5.3 Key CSS Classes Breakdown

- `flex min-h-screen`: Container flex a piena altezza viewport
- `items-center justify-center`: Centramento verticale e orizzontale
- `p-4`: Padding per evitare contenuto attaccato ai bordi su mobile
- `bg-background`: Background coerente con tema
- `w-full max-w-md`: Larghezza 100% su mobile, max 448px su desktop

---

## 6. Dashboard Layout Pattern

### 6.1 Option A: Top Padding (Recommended)

```tsx
// apps/web/src/pages/DashboardPage.tsx
const DashboardPage: React.FC = () => {
  // ... stato esistente

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 pt-20">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Dashboard Amministratore</h1>
        <p className="text-sm text-muted-foreground">Benvenuto, {userEmail}</p>
      </div>

      <section>
        <h2 className="mb-4 text-lg font-semibold">Funzionalità Admin</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {/* card links unchanged... */}
        </div>
      </section>
    </div>
  );
};
```

### 6.2 Option B: Centered Layout (If Minimal Content)

```tsx
// Solo se dashboard ha poco contenuto:
<div className="flex min-h-screen items-center justify-center p-4">
  <div className="mx-auto w-full max-w-5xl space-y-6">
    {/* contenuto dashboard */}
  </div>
</div>
```

**Nota:** Dashboard con molte card è meglio con padding-top per evitare troppo spazio vuoto sopra/sotto.

---

## 7. Testing Patterns

### 7.1 Navigation Component Tests

```tsx
// apps/web/src/components/__tests__/Navigation.test.tsx
import { render, screen } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import Navigation from '../Navigation';

describe('Navigation', () => {
  test('renders all navigation links', () => {
    render(
      <BrowserRouter>
        <Navigation />
      </BrowserRouter>
    );

    expect(screen.getByRole('link', { name: /chat studente/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /dashboard admin/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /admin login/i })).toBeInTheDocument();
  });

  test('highlights active link', () => {
    render(
      <MemoryRouter initialEntries={['/chat']}>
        <Navigation />
      </MemoryRouter>
    );

    const chatLink = screen.getByRole('link', { name: /chat studente/i });
    expect(chatLink).toHaveAttribute('aria-current', 'page');
    expect(chatLink).toHaveClass('bg-accent');
  });

  test('navigates to correct routes', async () => {
    const user = userEvent.setup();
    render(
      <BrowserRouter>
        <Navigation />
      </BrowserRouter>
    );

    const dashboardLink = screen.getByRole('link', { name: /dashboard admin/i });
    await user.click(dashboardLink);

    // Verify URL changed (requires Router context)
    // In real app, test with E2E or mock navigation
  });
});
```

### 7.2 LoadingIndicator Tests

```tsx
// apps/web/src/components/__tests__/LoadingIndicator.test.tsx
import { render, screen } from '@testing-library/react';
import LoadingIndicator from '../LoadingIndicator';

describe('LoadingIndicator', () => {
  test('renders loading message', () => {
    render(<LoadingIndicator />);
    expect(screen.getByText(/sta pensando/i)).toBeInTheDocument();
  });

  test('has correct accessibility attributes', () => {
    const { container } = render(<LoadingIndicator />);
    const indicator = container.firstChild as HTMLElement;

    expect(indicator).toHaveAttribute('role', 'status');
    expect(indicator).toHaveAttribute('aria-live', 'polite');
    expect(indicator).toHaveAttribute('aria-label');
  });

  test('matches message bubble styling', () => {
    const { container } = render(<LoadingIndicator />);
    const indicator = container.firstChild as HTMLElement;

    expect(indicator).toHaveClass('self-start');
    expect(indicator).toHaveClass('bg-muted');
    expect(indicator).toHaveClass('rounded-md');
  });
});
```

### 7.3 ChatInput Textarea Tests

```tsx
// apps/web/src/components/__tests__/ChatInput.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatInput from '../ChatInput';

describe('ChatInput with textarea', () => {
  test('renders textarea instead of input', () => {
    render(<ChatInput onSubmit={jest.fn()} />);
    const textarea = screen.getByTestId('chat-input-field');
    expect(textarea.tagName).toBe('TEXTAREA');
  });

  test('expands on multiline input', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSubmit={jest.fn()} />);
    const textarea = screen.getByTestId('chat-input-field') as HTMLTextAreaElement;

    const initialHeight = textarea.scrollHeight;

    await user.type(textarea, 'Line 1\nLine 2\nLine 3');

    await waitFor(() => {
      expect(textarea.scrollHeight).toBeGreaterThan(initialHeight);
    });
  });

  test('submits on Enter without Shift', async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    render(<ChatInput onSubmit={onSubmit} />);
    const textarea = screen.getByTestId('chat-input-field');

    await user.type(textarea, 'Test question');
    await user.keyboard('{Enter}');

    expect(onSubmit).toHaveBeenCalledWith('Test question');
  });

  test('adds newline on Shift+Enter', async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    render(<ChatInput onSubmit={onSubmit} />);
    const textarea = screen.getByTestId('chat-input-field') as HTMLTextAreaElement;

    await user.type(textarea, 'Line 1');
    await user.keyboard('{Shift>}{Enter}{/Shift}');
    await user.type(textarea, 'Line 2');

    expect(textarea.value).toContain('\n');
    expect(onSubmit).not.toHaveBeenCalled();
  });

  test('limits height to 4 rows', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSubmit={jest.fn()} />);
    const textarea = screen.getByTestId('chat-input-field') as HTMLTextAreaElement;

    // Type 5+ lines
    await user.type(textarea, 'L1\nL2\nL3\nL4\nL5\nL6');

    await waitFor(() => {
      // max-h-24 = 96px
      expect(parseInt(textarea.style.height)).toBeLessThanOrEqual(96);
    });
  });
});
```

### 7.4 E2E Tests (Playwright)

```typescript
// apps/web/tests/ui-enhancements.spec.ts
import { test, expect } from '@playwright/test';

test.describe('UI Enhancements', () => {
  test('navigation header is present on all pages', async ({ page }) => {
    await page.goto('/chat');
    await expect(page.locator('nav')).toBeVisible();

    await page.goto('/admin/dashboard');
    await expect(page.locator('nav')).toBeVisible();

    await page.goto('/login');
    await expect(page.locator('nav')).toBeVisible();
  });

  test('loading indicator appears in chat during response', async ({ page }) => {
    await page.goto('/chat');
    
    const textarea = page.locator('textarea[placeholder*="domanda"]');
    await textarea.fill('Test question');
    
    const submitButton = page.locator('button:has-text("Invia")');
    await submitButton.click();

    // Loading indicator should appear in chat container
    const chatContainer = page.locator('[data-testid="chat-messages-container"]');
    await expect(chatContainer.locator('text=sta pensando')).toBeVisible();
  });

  test('textarea expands up to 4 rows', async ({ page }) => {
    await page.goto('/chat');
    const textarea = page.locator('textarea[placeholder*="domanda"]');

    // Get initial height
    const initialHeight = await textarea.evaluate(el => el.clientHeight);

    // Type multiline text
    await textarea.fill('Line 1\nLine 2\nLine 3\nLine 4');

    // Should have expanded
    const expandedHeight = await textarea.evaluate(el => el.clientHeight);
    expect(expandedHeight).toBeGreaterThan(initialHeight);

    // Type more lines
    await textarea.fill('L1\nL2\nL3\nL4\nL5\nL6\nL7\nL8');

    // Should not exceed max height (96px)
    const maxHeight = await textarea.evaluate(el => el.clientHeight);
    expect(maxHeight).toBeLessThanOrEqual(96);
  });

  test('login form is vertically centered', async ({ page }) => {
    await page.goto('/login');
    
    const formContainer = page.locator('form').locator('..'); // parent div
    const containerClass = await formContainer.getAttribute('class');
    
    expect(containerClass).toContain('items-center');
    expect(containerClass).toContain('justify-center');
  });
});
```

---

## 8. Accessibility Checklist

### 8.1 Navigation
- [x] Semantic `<nav>` element used
- [x] Active link has `aria-current="page"`
- [x] Links have descriptive text (no "click here")
- [x] Keyboard navigable (Tab to links, Enter to activate)
- [x] Focus visible on keyboard navigation
- [x] Mobile menu button has `aria-label`

### 8.2 Loading Indicator
- [x] `role="status"` for non-critical status updates
- [x] `aria-live="polite"` to not interrupt user
- [x] `aria-label` describes what's loading
- [x] Visual animation matches reduced-motion preferences

### 8.3 Textarea Input
- [x] Associated `<label>` (visually hidden OK if placeholder clear)
- [x] `placeholder` text is descriptive
- [x] Error messages have `aria-describedby` linkage
- [x] Submit button has clear text ("Invia")
- [x] Disabled state communicated visually and to screen readers

### 8.4 Forms
- [x] Form has accessible name (heading nearby or `aria-labelledby`)
- [x] Input fields have `<label>` with `htmlFor`
- [x] Error messages have `role="alert"` or `aria-live="assertive"`
- [x] Required fields indicated visually and programmatically
- [x] Focus returns to first error on submit failure

### 8.5 Color Contrast
- [x] Text meets WCAG AA (4.5:1 for normal, 3:1 for large)
- [x] Interactive elements have 3:1 contrast against background
- [x] Active state has sufficient contrast difference

---

## 9. Performance Optimizations

### 9.1 Lazy Load Mobile Sheet

```tsx
import { lazy, Suspense } from 'react';

const Sheet = lazy(() => import('@/components/ui/sheet').then(m => ({ default: m.Sheet })));
// ... altri imports lazy

// Nel componente:
<Suspense fallback={<button>Menu</button>}>
  <Sheet>...</Sheet>
</Suspense>
```

### 9.2 Debounce Textarea Resize (se necessario)

```tsx
import { debounce } from 'lodash-es'; // o implementazione custom

const debouncedAdjustHeight = useMemo(
  () => debounce(adjustHeight, 50),
  []
);

// In onChange:
onChange={(e) => {
  setQuestion(e.target.value);
  debouncedAdjustHeight();
}}
```

### 9.3 Virtual Scrolling for Long Chat (se necessario)

```tsx
// Se chat diventa molto lunga (>100 messaggi), considerare:
import { useVirtualizer } from '@tanstack/react-virtual';

// Implementare virtual scrolling per messaggi
// Mantiene DOM leggero caricando solo messaggi visibili
```

---

## 10. Common Pitfalls and Solutions

### Issue 1: Textarea height jumps on type
**Cause:** Browser calcola scrollHeight con valori vecchi  
**Solution:** Reset height a 'auto' prima di calcolare scrollHeight

```tsx
textarea.style.height = 'auto'; // IMPORTANT: reset first
textarea.style.height = `${textarea.scrollHeight}px`;
```

### Issue 2: Loading indicator causes layout shift
**Cause:** Spazio non riservato per indicatore  
**Solution:** Usa placeholder dello stesso size o `min-height`

```tsx
// In ChatMessagesList, sempre mostrare spazio per loading:
<div className="min-h-[60px]">
  {loading ? <LoadingIndicator /> : null}
</div>
```

### Issue 3: Mobile keyboard covers input
**Cause:** Viewport height non considera keyboard  
**Solution:** Usa `visualViewport` API o `position: sticky`

```tsx
useEffect(() => {
  const handleResize = () => {
    // Scroll input into view when keyboard shows
    inputRef.current?.scrollIntoView({ block: 'nearest' });
  };

  window.visualViewport?.addEventListener('resize', handleResize);
  return () => window.visualViewport?.removeEventListener('resize', handleResize);
}, []);
```

### Issue 4: Navigation active state not updating
**Cause:** `useLocation()` hook non riesegue su route change  
**Solution:** Verificare che componente sia dentro `<BrowserRouter>`

```tsx
// App.tsx - assicurati Navigation sia dentro Router:
<BrowserRouter>
  <Navigation /> {/* ✓ Dentro Router */}
  <Routes>...</Routes>
</BrowserRouter>
```

### Issue 5: Enter key submits form AND adds newline
**Cause:** Non prevenuto default behavior su Enter without Shift  
**Solution:** `e.preventDefault()` nel handler `onKeyDown`

```tsx
const handleKeyDown = (e: React.KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault(); // ← CRITICAL
    handleSubmit(e as any);
  }
};
```

---

## References

- **Shadcn/UI Components:** https://ui.shadcn.com/docs/components
- **React Router:** https://reactrouter.com/en/main/hooks/use-location
- **Tailwind CSS:** https://tailwindcss.com/docs/flex
- **WCAG 2.1 AA:** https://www.w3.org/WAI/WCAG21/quickref/
- **Textarea Auto-Resize:** MDN `scrollHeight` property
- **React Testing Library:** https://testing-library.com/docs/react-testing-library/intro
- **Playwright:** https://playwright.dev/docs/intro

---

**Status:** ✅ Active Implementation Guide  
**Last Updated:** 2025-01-21  
**Owner:** Development Team (Story 6.7)


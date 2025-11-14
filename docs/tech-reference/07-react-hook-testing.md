# React Hook Testing

## @testing-library/react-hooks

**Problema:**
Hooks possono essere chiamati solo dentro componenti funzionali. Testare direttamente causa:
```
Invariant Violation: Hooks can only be called inside the body of a function component.
```

**Soluzione:**
Test harness che esegue hooks in contesto componente funzionale valido.

**Installazione:**
```bash
npm install --save-dev @testing-library/react-hooks
```

---

## Quando Usare

**✓ Usa react-hooks-testing-library:**
- Libreria con custom hooks non legati a componenti specifici
- Hook complesso difficile da testare via interazioni componente

**✗ Non usare:**
- Hook definito e usato solo in un componente
- Hook facilmente testabile tramite componente che lo usa

---

## API Base

**renderHook:**
```typescript
import { renderHook } from '@testing-library/react-hooks'

function useCounter() {
  const [count, setCount] = useState(0)
  const increment = () => setCount(c => c + 1)
  return { count, increment }
}

test('useCounter', () => {
  const { result } = renderHook(() => useCounter())
  
  expect(result.current.count).toBe(0)
  
  act(() => {
    result.current.increment()
  })
  
  expect(result.current.count).toBe(1)
})
```

---

## Testing Pattern Comuni

**Hook con props:**
```typescript
function useCustomHook(initialValue: number) {
  const [value, setValue] = useState(initialValue)
  return { value, setValue }
}

test('useCustomHook with different initial values', () => {
  const { result, rerender } = renderHook(
    ({ initial }) => useCustomHook(initial),
    { initialProps: { initial: 5 } }
  )
  
  expect(result.current.value).toBe(5)
  
  rerender({ initial: 10 })
  expect(result.current.value).toBe(10)
})
```

**Hook async:**
```typescript
function useAsync() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  
  const fetch = async () => {
    setLoading(true)
    const result = await fetchData()
    setData(result)
    setLoading(false)
  }
  
  return { data, loading, fetch }
}

test('useAsync', async () => {
  const { result, waitForNextUpdate } = renderHook(() => useAsync())
  
  expect(result.current.loading).toBe(false)
  
  act(() => {
    result.current.fetch()
  })
  
  expect(result.current.loading).toBe(true)
  
  await waitForNextUpdate()
  
  expect(result.current.loading).toBe(false)
  expect(result.current.data).toBeDefined()
})
```

**Hook con context:**
```typescript
const ThemeContext = React.createContext('light')

function useTheme() {
  return useContext(ThemeContext)
}

test('useTheme', () => {
  const wrapper = ({ children }) => (
    <ThemeContext.Provider value="dark">
      {children}
    </ThemeContext.Provider>
  )
  
  const { result } = renderHook(() => useTheme(), { wrapper })
  
  expect(result.current).toBe('dark')
})
```

**Hook con useEffect:**
```typescript
function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = title
    return () => {
      document.title = ''
    }
  }, [title])
}

test('useDocumentTitle', () => {
  const { rerender, unmount } = renderHook(
    ({ title }) => useDocumentTitle(title),
    { initialProps: { title: 'Initial' } }
  )
  
  expect(document.title).toBe('Initial')
  
  rerender({ title: 'Updated' })
  expect(document.title).toBe('Updated')
  
  unmount()
  expect(document.title).toBe('')
})
```

---

## Vitest Setup

**vitest.config.ts:**
```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})
```

**src/test/setup.ts:**
```typescript
import '@testing-library/jest-dom'
```

**Test con Vitest:**
```typescript
import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react-hooks'

describe('useCounter', () => {
  it('increments counter', () => {
    const { result } = renderHook(() => useCounter())
    
    act(() => {
      result.current.increment()
    })
    
    expect(result.current.count).toBe(1)
  })
})
```

---

## Best Practices

**Wrapping actions in act():**
```typescript
// ✓ Corretto
act(() => {
  result.current.increment()
})

// ❌ Warning: not wrapped in act()
result.current.increment()
```

**Testing async updates:**
```typescript
// Con waitForNextUpdate
await waitForNextUpdate()

// Con waitFor
await waitFor(() => {
  expect(result.current.loading).toBe(false)
})
```

**Cleanup:**
```typescript
test('cleanup on unmount', () => {
  const cleanup = vi.fn()
  
  function useEffectHook() {
    useEffect(() => cleanup, [])
  }
  
  const { unmount } = renderHook(() => useEffectHook())
  
  expect(cleanup).not.toHaveBeenCalled()
  
  unmount()
  
  expect(cleanup).toHaveBeenCalledTimes(1)
})
```

**Mock dependencies:**
```typescript
import { vi } from 'vitest'

vi.mock('./api', () => ({
  fetchData: vi.fn(() => Promise.resolve({ data: 'mock' }))
}))

test('useDataFetch', async () => {
  const { result, waitForNextUpdate } = renderHook(() => useDataFetch())
  
  await waitForNextUpdate()
  
  expect(result.current.data).toEqual({ data: 'mock' })
})
```

---

## API Reference

**renderHook(callback, options):**
- `callback`: Function che chiama il hook
- `options.initialProps`: Props iniziali
- `options.wrapper`: Component wrapper (per context)

**Return value:**
- `result.current`: Valore corrente ritornato dal hook
- `rerender(newProps)`: Re-render con nuove props
- `unmount()`: Unmount del hook
- `waitForNextUpdate()`: Attende prossimo update
- `waitFor(callback)`: Attende condizione

---

## Alternative: Testing via Component

**Se hook è semplice, testare via componente:**
```typescript
function useCounter() {
  const [count, setCount] = useState(0)
  return { count, increment: () => setCount(c => c + 1) }
}

function CounterComponent() {
  const { count, increment } = useCounter()
  return (
    <div>
      <span data-testid="count">{count}</span>
      <button onClick={increment}>Increment</button>
    </div>
  )
}

test('counter via component', () => {
  render(<CounterComponent />)
  
  expect(screen.getByTestId('count')).toHaveTextContent('0')
  
  fireEvent.click(screen.getByRole('button'))
  
  expect(screen.getByTestId('count')).toHaveTextContent('1')
})
```

---

## Repository

https://react-hooks-testing-library.com/

**Note:** Per Vitest React testing docs, URL non disponibile. Riferimento setup sopra.

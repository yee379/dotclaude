---
name: react-patterns
description: React component patterns, hooks, state management, performance optimisation, GraphQL integration with Apollo or urql, TypeScript usage, and testing with React Testing Library for production frontend apps.
license: MIT
compatibility: opencode
---

# React Patterns

Production React patterns — component design, hooks, state, GraphQL integration, and testing.

## When to Use

- Designing or reviewing React components
- Implementing custom hooks or context
- Integrating GraphQL with Apollo Client or urql
- Debugging re-render performance issues
- Writing component tests with React Testing Library
- Setting up TypeScript for a React project

---

## Component Design

### Function components + TypeScript

```tsx
// Props interface — explicit, no implicit children
interface UserCardProps {
  user: User;
  onEdit?: (id: string) => void;
  className?: string;
}

export function UserCard({ user, onEdit, className }: UserCardProps) {
  return (
    <div className={cn("card", className)}>
      <h2>{user.name}</h2>
      <p>{user.email}</p>
      {onEdit && (
        <button onClick={() => onEdit(user.id)}>Edit</button>
      )}
    </div>
  );
}
```

### Component composition over configuration

```tsx
// BAD: prop-driven configuration explosion
<DataTable
  showHeader
  showFooter
  showPagination
  showSearch
  headerContent={...}
  footerContent={...}
/>

// GOOD: composition
<DataTable>
  <DataTable.Header>
    <SearchBar />
  </DataTable.Header>
  <DataTable.Body rows={rows} />
  <DataTable.Footer>
    <Pagination />
  </DataTable.Footer>
</DataTable>
```

### Controlled vs uncontrolled

```tsx
// Controlled — parent owns state (prefer for forms that need validation)
function EmailInput({ value, onChange, error }: ControlledProps) {
  return (
    <div>
      <input value={value} onChange={(e) => onChange(e.target.value)} />
      {error && <span className="error">{error}</span>}
    </div>
  );
}

// Uncontrolled — component owns state (simpler for isolated inputs)
function SearchBar({ onSearch }: { onSearch: (q: string) => void }) {
  const [query, setQuery] = useState("");
  return (
    <input
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      onKeyDown={(e) => e.key === "Enter" && onSearch(query)}
    />
  );
}
```

---

## Hooks

### Custom hooks — extract logic from components

The pattern: encapsulate state + effects behind a named hook; use the cancellation flag to prevent state updates on unmounted components.

```tsx
// Canonical shape — data fetching hook with cancellation
function useUser(id: string) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchUser(id)
      .then((data) => { if (!cancelled) setUser(data); })
      .catch((err) => { if (!cancelled) setError(err); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [id]);

  return { user, loading, error };
}
```

The same shape applies to form state (`useForm`) and debounced values (`useDebounce`) — same encapsulation principle, different internal logic.

### useReducer for complex state

```tsx
type State = {
  status: "idle" | "loading" | "success" | "error";
  data: Order[] | null;
  error: string | null;
};

type Action =
  | { type: "FETCH_START" }
  | { type: "FETCH_SUCCESS"; payload: Order[] }
  | { type: "FETCH_ERROR"; payload: string };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "FETCH_START": return { ...state, status: "loading", error: null };
    case "FETCH_SUCCESS": return { status: "success", data: action.payload, error: null };
    case "FETCH_ERROR": return { ...state, status: "error", error: action.payload };
    default: return state;
  }
}

function OrderList() {
  const [state, dispatch] = useReducer(reducer, { status: "idle", data: null, error: null });
  // ...
}
```

---

## State Management

### Context — for low-frequency global state

```tsx
// auth context
interface AuthContext {
  user: User | null;
  login: (credentials: Credentials) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContext | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  const login = useCallback(async (credentials: Credentials) => {
    const user = await authService.login(credentials);
    setUser(user);
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContext {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
```

### Zustand — for app-wide client state (prefer over Redux)

```tsx
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

interface CartStore {
  items: CartItem[];
  addItem: (product: Product, qty: number) => void;
  removeItem: (productId: string) => void;
  clear: () => void;
}

const useCartStore = create<CartStore>()(
  immer((set) => ({
    items: [],
    addItem: (product, qty) =>
      set((state) => {
        const existing = state.items.find((i) => i.product.id === product.id);
        if (existing) existing.qty += qty;
        else state.items.push({ product, qty });
      }),
    removeItem: (productId) =>
      set((state) => {
        state.items = state.items.filter((i) => i.product.id !== productId);
      }),
    clear: () => set((state) => { state.items = []; }),
  }))
);
```

---

## GraphQL with Apollo Client

For GraphQL integration patterns (queries, mutations, subscriptions, optimistic UI, Federation), see `/graphql-patterns`.

> If you need the optimistic response pattern specifically in a React context, the key is to pass `optimisticResponse` to `useMutation` with the expected shape — Apollo Client will apply it immediately and reconcile on the server response.

---

## Performance

Memoisation, code splitting, and virtual lists — load `references/performance.md`. Apply only
after profiling identifies a real re-render or bundle problem.

---

## Testing with React Testing Library

Load `references/testing.md` for component test shape, accessible queries, and the Apollo
`MockedProvider` setup.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| No `key` on a mapped list: `users.map(u => <UserCard user={u} />)` | Stable key from data: `key={u.id}` — never the index unless the list is static |
| `useEffect(() => { fetch(userId); }, [])` — stale closure over `userId` | List every value the effect reads: `[userId]` |
| Deriving state in an effect: `setFullName` inside `useEffect` on `[first, last]` | Compute inline during render — no state, no effect: ``const fullName = `${first} ${last}` `` |
| Calling a hook conditionally: `if (isAdmin) { useQuery(ADMIN_QUERY) }` | Call unconditionally and branch on options: `useQuery(ADMIN_QUERY, { skip: !isAdmin })` |
| Spreading unknown props into the DOM to "stay flexible" | Declare the props interface explicitly; pass `className`/`children` deliberately |

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

```tsx
// Data fetching hook
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

// Form hook
function useForm<T extends Record<string, unknown>>(initialValues: T) {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const setValue = useCallback((field: keyof T, value: unknown) => {
    setValues((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  }, []);

  return { values, errors, isSubmitting, setValue, setErrors, setIsSubmitting };
}

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
```

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

### Memoisation — only when profiling shows it's needed

```tsx
// useMemo for expensive pure computations
const sortedUsers = useMemo(
  () => [...users].sort((a, b) => a.name.localeCompare(b.name)),
  [users]
);

// useCallback for stable function references passed to memoised children
const handleDelete = useCallback((id: string) => {
  deleteUser({ variables: { id } });
}, [deleteUser]);

// React.memo — prevent re-renders when props haven't changed
const UserRow = React.memo(function UserRow({ user, onDelete }: UserRowProps) {
  return <tr>...</tr>;
});
```

### Code splitting

```tsx
// Route-level splitting
const AdminPanel = lazy(() => import("./pages/AdminPanel"));

function App() {
  return (
    <Suspense fallback={<PageSpinner />}>
      <Routes>
        <Route path="/admin" element={<AdminPanel />} />
      </Routes>
    </Suspense>
  );
}
```

### Virtual lists for long lists

```tsx
import { useVirtualizer } from "@tanstack/react-virtual";

function VirtualUserList({ users }: { users: User[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: users.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 64,
  });

  return (
    <div ref={parentRef} style={{ height: "600px", overflow: "auto" }}>
      <div style={{ height: rowVirtualizer.getTotalSize() }}>
        {rowVirtualizer.getVirtualItems().map((vRow) => (
          <div
            key={vRow.index}
            style={{ position: "absolute", top: vRow.start, height: vRow.size, width: "100%" }}
          >
            <UserRow user={users[vRow.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Testing with React Testing Library

```tsx
// Principle: test behaviour, not implementation

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

describe("UserCard", () => {
  it("renders user name and email", () => {
    render(<UserCard user={{ id: "1", name: "Alice", email: "alice@example.com" }} />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("alice@example.com")).toBeInTheDocument();
  });

  it("calls onEdit when edit button clicked", async () => {
    const onEdit = jest.fn();
    const user = userEvent.setup();
    render(<UserCard user={mockUser} onEdit={onEdit} />);
    await user.click(screen.getByRole("button", { name: /edit/i }));
    expect(onEdit).toHaveBeenCalledWith(mockUser.id);
  });

  it("does not render edit button when onEdit not provided", () => {
    render(<UserCard user={mockUser} />);
    expect(screen.queryByRole("button", { name: /edit/i })).not.toBeInTheDocument();
  });
});

// Async + Apollo mock
import { MockedProvider } from "@apollo/client/testing";

const mocks = [{
  request: { query: GET_USERS, variables: { first: 20 } },
  result: { data: { users: mockUsersConnection } },
}];

it("loads and displays users", async () => {
  render(
    <MockedProvider mocks={mocks} addTypename={false}>
      <UserList />
    </MockedProvider>
  );
  expect(screen.getByRole("progressbar")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("Alice")).toBeInTheDocument());
});
```

---

## Common Mistakes

```tsx
// BAD: missing key prop on lists
users.map((u) => <UserCard user={u} />)

// GOOD: stable key (never use index unless list is static)
users.map((u) => <UserCard key={u.id} user={u} />)

// BAD: useEffect with missing deps (stale closure)
useEffect(() => { fetch(userId); }, []);

// GOOD: explicit deps
useEffect(() => { fetch(userId); }, [userId]);

// BAD: derive state in useEffect
const [fullName, setFullName] = useState("");
useEffect(() => setFullName(`${first} ${last}`), [first, last]);

// GOOD: compute inline
const fullName = `${first} ${last}`;

// BAD: calling hooks conditionally
if (isAdmin) {
  const data = useQuery(ADMIN_QUERY); // violates Rules of Hooks!
}

// GOOD: call hook unconditionally, branch on result
const { data } = useQuery(ADMIN_QUERY, { skip: !isAdmin });
```

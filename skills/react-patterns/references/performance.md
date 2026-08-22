# React Performance Patterns

Load when profiling shows a real re-render or bundle-size problem. Do not apply these
pre-emptively — memoisation has its own cost and obscures data flow.

## Memoisation — only when profiling shows it's needed

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

## Code splitting

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

## Virtual lists for long lists

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

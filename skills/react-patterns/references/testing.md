# Testing React Components

Principle: test behaviour, not implementation. Query by role and accessible name, never by
class name or test ID unless nothing else identifies the element.

```tsx
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
```

## Async + Apollo mock

`MockedProvider` moved to `@apollo/client/testing/react` in Apollo Client v4, and the
`addTypename` prop was removed — mocks must include `__typename` fields matching the cache.

```tsx
import { MockedProvider } from "@apollo/client/testing/react";

const mocks = [{
  request: { query: GET_USERS, variables: { first: 20 } },
  result: { data: { users: mockUsersConnection } },
}];

it("loads and displays users", async () => {
  render(
    <MockedProvider mocks={mocks}>
      <UserList />
    </MockedProvider>
  );
  expect(screen.getByRole("progressbar")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("Alice")).toBeInTheDocument());
});
```

For test-design principles (what to test, coverage targets, good vs bad assertions) see
`/tdd-standards`.

---
name: js-ts-patterns
description: Framework-agnostic JavaScript/TypeScript idioms — compiler strictness, type design, module systems, async patterns, error handling, immutability, and tooling consensus for 2025-2026. Pair with react-patterns for React-specific work.
license: MIT
compatibility: opencode
---

# JS/TS Patterns

Framework-agnostic TypeScript/JavaScript for backend and frontend code. Use when writing or
reviewing JS/TS outside a specific framework's own conventions, setting up `tsconfig.json` or
`eslint.config.js`, or choosing between async/error-handling/module approaches. For React
component patterns, hooks, and state management, use `react-patterns` instead.

## Compiler Strictness

```jsonc
// tsconfig.json — baseline for any new project
{
  "compilerOptions": {
    "strict": true,                        // bundles strictNullChecks, noImplicitAny, etc.
    "noUncheckedIndexedAccess": true,       // arr[i] / record[key] types as T | undefined
    "exactOptionalPropertyTypes": true,     // `?: T` absent vs. present-as-undefined differ
    "verbatimModuleSyntax": true,           // forces explicit `import type` / `export type`
    "noImplicitOverride": true,             // requires `override` on overriding methods
    "module": "nodenext",                   // or "preserve" + noEmit if a bundler transpiles
    "skipLibCheck": true
  }
}
```

`strict` is a moving target — newer TS versions add checks to it. `noUncheckedIndexedAccess` and
`exactOptionalPropertyTypes` are not bundled in `strict`; enable them explicitly. Never disable a
strict sub-flag to silence an error — fix the type.

## Type Design

```typescript
// satisfies — validate shape without widening the inferred type
const config = {
  prod: { url: "https://api.example.com" },
  dev: { url: "http://localhost:3000" },
} satisfies Record<string, { url: string }>;
config.prod.url; // still narrowed to the literal shape, unlike a `: Record<...>` annotation

// Discriminated unions + exhaustiveness check
type Shape =
  | { kind: "circle"; radius: number }
  | { kind: "rect"; w: number; h: number };

function area(s: Shape): number {
  switch (s.kind) {
    case "circle": return Math.PI * s.radius ** 2;
    case "rect": return s.w * s.h;
    default: return assertNever(s); // compile error if a new Shape variant is unhandled
  }
}
function assertNever(x: never): never {
  throw new Error(`Unhandled case: ${JSON.stringify(x)}`);
}
// Caveat: this only catches missing literal cases, not an object with extra properties
// slipping past structurally — don't treat it as an airtight runtime guarantee.
```

- Never use `any`. Prefer `unknown` + narrowing, or a precise type. `as` requires a comment
  justifying why the compiler can't infer it; never chain `as X as Y` — route through `unknown`.
  Enforce with `typescript-eslint`'s `recommended-type-checked` (`no-explicit-any`,
  `no-unsafe-*`), not just style-guide prose — the lint config is what actually gates this.
- Prefer string-literal unions or `as const` objects over `enum` for new code (non-tree-shakeable
  runtime emission, numeric-enum reordering fragility). `const enum` specifically breaks
  `isolatedModules` — never use it.
- Branded types (`type UserId = string & { __brand: "UserId" }`) prevent mixing structurally
  identical primitives. Pair every brand with one "smart constructor" that performs the real
  runtime check — never scatter `as UserId` casts through the codebase. Treat this as an
  available pattern for a specific problem (primitive mix-ups), not a default — it has real
  critics (IDE confusion, "type creep") and little production precedent outside tutorials.

## Module Systems

```jsonc
// package.json — ESM-first is now viable without a dual CJS/ESM build
{
  "type": "module",
  "exports": {
    ".": "./dist/index.js",
    "./utils": "./dist/utils.js"
  }
}
```

- Default to `"type": "module"` and ESM-only publishing. `require(esm)` is stable (Node ≥20.19 /
  22.12), so CJS consumers can still `require()` an ESM-only package — unless that package uses
  top-level await, which `require()` cannot load.
- If you must ship both entry points, use a conditional `exports` block
  (`{ "import": "...", "require": "..." }`) and be aware of the **dual package hazard**: a
  consumer that loads both gets two separate module instances (broken singletons/`instanceof`).
- Node's native TypeScript type stripping (stable) runs `.ts` files directly with no build step —
  but it only strips types (no `tsconfig.json` read, no `.tsx`, throws on `enum`/decorators/
  parameter properties). Use `tsx` or `ts-node` where those are needed, or for real type-checking
  at run time.

## Async Patterns

```typescript
// Parallelize independent work — never await in sequence when operations don't depend on each other
const [user, orders] = await Promise.all([fetchUser(id), fetchOrders(id)]);

// allSettled when partial failure is acceptable
const results = await Promise.allSettled(ids.map(fetchItem));

// Cancellation
const controller = new AbortController();
const signal = controller.signal;
try {
  await fetch(url, { signal });
} finally {
  // Remove any listener you attached to the signal yourself — AbortSignal.any()/timeout()
  // keep internal listeners alive and can leak if never cleaned up.
}
```

- Never leave a promise floating — `await` it, `.catch()` it, `return` it, or mark it
  intentionally fire-and-forget with `void`. Enforce with `typescript-eslint`'s
  `no-floating-promises` and `no-misused-promises` (catches `array.forEach(async x => ...)`,
  which silently drops errors and ordering — use a `for...of` with `await` or `Promise.all`
  instead).
- `return await` inside a `try` is fine — don't "fix" it. ESLint deprecated `no-return-await`;
  omitting the `await` drops the frame from the stack trace on rejection for no benefit.
- Top-level await is safe in ESM and the standard replacement for the async-IIFE wrapper. The
  only real hazard is a circular import where one side needs the other's top-level-awaited export.

## Error Handling

```typescript
// Error.cause — standard way to rethrow with context
try {
  await db.query(sql);
} catch (err) {
  throw new Error("Failed to load user", { cause: err });
}

// catch variables are `unknown` under strict — narrow before use
try {
  risky();
} catch (err) {
  if (err instanceof Error) throw err;
  throw new Error(String(err));
}
```

Custom error classes: `extends Error`, call `super(message, { cause })`, set `this.name`. Attach
structured data as readonly properties; narrow with `instanceof` at the catch site.

Result/Either types (`neverthrow`, `fp-ts`) are a real pattern for making expected failure part of
a function's return type instead of throwing — but they are a minority practice with real
production friction (async/Promise interop overhead, a steeper onboarding curve). Reach for a
plain discriminated-union return (`{ ok: true; value } | { ok: false; error }`) at a specific API
boundary before adopting a full Result library project-wide.

## Null Handling & Immutability

```typescript
// ?? not || for defaults — || also fires on 0, '', false
const port = config.port ?? 3000;
const name = user?.profile?.displayName ?? "Anonymous";

// readonly is compile-time only and shallow — nested contents stay mutable
function render(points: readonly Point[]): void { /* ... */ }
const frozenShape = { kind: "circle", radius: 5 } as const;
```

- Don't let `null`/`undefined` mean two different things in the same API ("not loaded" vs.
  "cleared" vs. "invalid") — use a discriminated union or explicit tagged shape instead of a bare
  nullable return. There's no single industry convention on `null` vs. `undefined` otherwise —
  pick one meaning per project and hold to it.
- `readonly`/`as const`/`Readonly<T>` give zero runtime guarantee and can be bypassed by a mutable
  alias to the same object — don't treat them as a security boundary.
- Immer (`produce`) is a reasonable default for nested state updates (Redux-style reducers), but
  has real documented performance cliffs on array mutations (`sort`/`splice`/`reverse`) and when
  `autoFreeze` is disabled. For performance-sensitive paths, benchmark against `mutative` or a
  plain spread before committing to either.

## Tooling

```javascript
// eslint.config.js — flat config is the only format ESLint supports (v10+)
import tseslint from "typescript-eslint";

export default tseslint.config(
  tseslint.configs.recommendedTypeChecked, // use strictTypeChecked only if the team is TS-fluent
  { languageOptions: { parserOptions: { projectService: true } } },
);
```

- Prettier formats, ESLint lints — load `eslint-config-prettier` last to disable conflicting
  rules. Don't run Prettier through `eslint-plugin-prettier`; keep them as two pipeline steps.
- TS project references for monorepos is a genuine, unresolved split between tools: Nx recommends
  them and automates the maintenance; Turborepo recommends against them in favor of one flat
  `tsconfig` per package plus `tsc --noEmit`. Follow whichever task runner the project already
  uses — there's no universal answer.
- Biome/oxlint are growing fast but remain a fraction of ESLint's install base — a viable
  single-tool choice for formatting and basic linting on a new project, not yet a safe wholesale
  replacement for `typescript-eslint`'s type-aware rules on an existing one.

## Testing & Anti-Patterns

- Vitest vs. Jest: Vitest leads on satisfaction and is the default for new Vite-ecosystem
  projects; Jest still has the larger installed base on existing codebases. Don't migrate a
  working Jest suite without a reason beyond "Vitest is newer."
- `node:test` core API and mocking are stable; coverage, watch mode, and global setup/teardown
  are still experimental — don't rely on those for CI gating yet.
- Never use a non-null assertion (`!`) to silence a type error — narrow with an `if` or fix the
  type. `unbound-method` risk: a class method passed by reference loses `this`
  (`el.addEventListener("click", obj.method)`) — use an arrow-function class field instead.
- Avoid barrel files (`index.ts` re-exporting a whole internal module tree) for internal
  organization — every import pays full re-export resolution cost, and it measurably slows
  builds and test runs at scale. Fine for a package's deliberate, small public API surface.
- Never mutate a function's object/array argument — treat inputs as immutable, enforce with
  `readonly` parameter types.

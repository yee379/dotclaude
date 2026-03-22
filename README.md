# ~/.claude

Global Claude Code configuration, skills, and documentation.

## Structure

```
~/.claude/
├── CLAUDE.md           # Global instructions for Claude (file access, terminal behaviour)
├── README.md           # This file
├── settings.json       # Claude Code settings (model, API, env, hooks)
├── skills/             # Skill library
└── *.md                # Integration and setup documentation
```

## Skill Taxonomy

Skills are named by category and function: `<category>-<function>` or `<function>-<category>`.

### Standards
Reference documents — rules and best practices to follow when writing code.

| Skill | Purpose |
|---|---|
| `code-standards` | TypeScript/JS/React naming, patterns, anti-patterns |
| `tdd-standards` | Test-driven development rules, 80%+ coverage requirement |

### Workflows
Active processes that orchestrate a sequence of steps.

| Skill | Purpose |
|---|---|
| `codebase-workflow` | Backlog management via `todo/`, task files, `TODO.md` |
| `prod-release` | Production release gates, promotion, rollback |

### Reviews
Skills that evaluate something and report findings.

| Skill | Purpose |
|---|---|
| `code-review` | Backend/DevOps correctness, security, performance |
| `design-review` | Visual QA on a live implementation |
| `plan-design-review` | Design critique on a plan (before implementation) |
| `plan-arch-review` | Architecture review — structure, boundaries, consistency |
| `plan-eng-review` | Engineering review — execution, edge cases, test coverage |
| `plan-doc-review` | Documentation review — what docs need updating |
| `plan-ux-review` | UX review from a scientist/end-user perspective |
| `security-review` | Security audit — secrets, auth, injection, supply chain |

### Plan pipeline
Skills that operate on a feature plan, in order.

| Skill | Purpose |
|---|---|
| `plan-draft` | Create a plan: problem framing, requirements, ADRs, design |
| `plan-board-review` | Gate a plan through all reviewers in parallel |
| `plan-closeout` | Close out after a feature ships — docs, changelog, task files |

### Research
Skills for investigation and synthesis.

| Skill | Purpose |
|---|---|
| `deep-research` | Multi-source research with citations |
| `search-first` | Search before writing code |
| `todo-scout` | Scan codebase for backlog candidates |
| `iterative-retrieval` | Progressive context retrieval pattern |

### Patterns
Language/framework best-practice guides.

| Skill | Purpose |
|---|---|
| `python-patterns` | Pythonic idioms, async, testing, project structure |
| `react-patterns` | React components, hooks, state, Apollo/urql, RTL |
| `graphql-design` | Schema design, resolvers, N+1, pagination, federation |
| `twelve-factor` | 12-factor app methodology for cloud-native services |

### Infrastructure
Kubernetes and cloud operations.

| Skill | Purpose |
|---|---|
| `k8s-deploy` | Helm, vcluster, namespace promotion, health probes |
| `k8s-troubleshooting` | Cluster diagnostics, pod logs, storage, networking |
| `system-troubleshooting` | Node/service diagnostics via Loki, InfluxDB, Prometheus |

### Meta
Skills about Claude Code itself.

| Skill | Purpose |
|---|---|
| `skill-stocktake` | Audit skill library for quality |
| `strategic-compact` | Context compaction at logical intervals |
| `agentic-engineering` | Eval-first agentic execution, cost-aware routing |
| `autonomous-loops` | Autonomous loop architectures and patterns |
| `claude-api` | Build apps with the Anthropic SDK |

## Planned

| Skill | Purpose |
|---|---|
| `design-standards` | Visual design rules — spacing, typography, colour, accessibility |
| `research-workflow` | Track research threads across sessions (in testing) |

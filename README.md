# ~/.claude

Global Claude Code configuration, skills, and documentation.

## Structure

```
~/.claude/
├── CLAUDE.md           # Global instructions for Claude (file access, terminal behaviour)
├── README.md           # This file
├── settings.json       # Claude Code settings (model, API, env, hooks)
├── skills/             # Skill library (39 skills)
└── *.md                # Integration and setup documentation
```

## Skill Taxonomy

Skills are named by category and function: `<subject>-<category>`.

### Categories

| Suffix | Meaning | Examples |
|---|---|---|
| `-standards` | Prescriptive rules you must follow — pass/fail, enforced by review. "Do this, not that." | `code-standards`, `tdd-standards` |
| `-patterns` | Reusable solutions to recurring problems — advisory, not mandatory. "Here's how things can be done well." | `python-patterns`, `react-patterns` |
| `-workflow` | Orchestrated sequence of steps that moves something from A to B | `codebase-workflow`, `platform-workflow` |
| `-review` | Evaluates something and reports findings | `code-review`, `codebase-arch-review` |
| `-handbook` | How to do a type of work — methodology, reference, operating modes | `research-handbook`, `multi-agent-handbook` |

The key distinction between `-standards` and `-patterns`: **standards tell you what you must do, patterns show you how things can be done**. Standards have a right/wrong answer; patterns have better/worse tradeoffs.

Some skills don't carry a suffix where the name is already self-documenting (e.g. `search-first`, `codebase-scout`).

---

### Standards
Rules and best practices to follow when writing code.

| Skill | Purpose |
|---|---|
| `code-standards` | TypeScript/JS/React naming, patterns, anti-patterns |
| `tdd-standards` | Test-driven development rules, 80%+ coverage requirement |
| `agentic-standards` | Principles for agentic engineering: eval-first, decomposition, model routing |
| `twelve-factor-standards` | 12-factor app methodology for cloud-native services |

### Patterns
Language/framework best-practice guides.

| Skill | Purpose |
|---|---|
| `python-patterns` | Pythonic idioms, async, testing, project structure |
| `react-patterns` | React components, hooks, state, Apollo/urql, RTL |
| `graphql-patterns` | Schema design, resolvers, N+1, pagination, federation |

### Codebase pipeline
Plan, review, and close out a feature — in order.

| Skill | Purpose |
|---|---|
| `codebase-draft-prd` | Feature planning — problem framing, user stories, requirements, ADRs, system design |
| `codebase-board-review` | Orchestrates all codebase reviewers in parallel; iterates until all pass |
| `codebase-arch-review` | Architecture review — service boundaries, data ownership, consistency, failure domains |
| `codebase-eng-review` | Eng manager review — execution plan, data flow, edge cases, test coverage |
| `doc-review` | Pre-implementation docs planning — identifies every doc needing update |
| `codebase-design-review` | Design critique on a plan — rates each dimension 0–10 and fixes to get there |
| `codebase-ux-review` | UX plan review from a scientist/end-user perspective; triage-gated |
| `codebase-closeout` | Post-ship doc sync — README, ARCHITECTURE, CHANGELOG, todo/ close-out |

### Codebase ops
Day-to-day backlog and discovery.

| Skill | Purpose |
|---|---|
| `codebase-workflow` | Backlog management via `todo/`, task files, `TODO.md` |
| `codebase-scout` | Scan codebase for backlog candidates |

### Platform pipeline
Plan, review, and apply a Kubernetes/infrastructure change — in order.

| Skill | Purpose |
|---|---|
| `platform-draft-prd` | Platform change planning — feasibility, capacity, infra design, operational readiness, ADRs |
| `platform-board-review` | Orchestrates all platform reviewers in parallel; iterates until all pass |
| `codebase-arch-review` | Architecture review (platform mode) — cluster topology, namespaces, network, storage, multi-tenancy |
| `platform-capacity-review` | Cluster capacity and feasibility — CPU, memory, storage, networking, control-plane headroom |
| `platform-security-review` | K8s security — RBAC, network policies, secrets, pod security, mTLS, image supply chain |
| `platform-ops-review` | Operational readiness — runbooks, monitoring, alerting, incident response |
| `platform-eng-review` | Helm chart quality, manifest correctness, resource tuning, health probes, rollout strategy |
| `doc-review` | Pre-implementation platform docs planning — runbooks, architecture diagrams, ADRs |

### Platform ops

| Skill | Purpose |
|---|---|
| `platform-workflow` | Track platform changes, operational health items, and infrastructure decisions |

### Reviews
Standalone review skills for code and live implementations.

| Skill | Purpose |
|---|---|
| `code-review` | Backend/DevOps correctness, security, performance |
| `design-review` | Visual QA on a live implementation (opencode only — uses `$B` browser REPL) |
| `security-review` | App-layer security audit — secrets, auth, injection, supply chain |

### Research

| Skill | Purpose |
|---|---|
| `research-scout` | Challenges framing, surfaces blind spots, and injects outsider thinking before research begins |
| `research-workflow` | Manages research output — cataloguing concepts, reports, and charges with cross-linking |
| `research-handbook` | Multi-source research methodology: parallel subagents, cited reports, operating modes |
| `search-first` | Search for existing tools/libraries before writing custom code |

### Infrastructure
Kubernetes and cloud operations.

| Skill | Purpose |
|---|---|
| `k8s-deploy` | Helm, vcluster, namespace promotion, health probes |
| `troubleshooting` | Cluster diagnostics, pod logs, storage, networking |
| `troubleshooting` | Node/service diagnostics via Loki, InfluxDB, Prometheus |

### Workflows

| Skill | Purpose |
|---|---|
| `prod-release` | Production release gates, staging promotion, rollback |

### Handbooks
How to do a type of work — methodology, patterns, reference guides.

| Skill | Purpose |
|---|---|
| `multi-agent-handbook` | Multi-agent architectures: sequential pipelines → DAG orchestration, iterative context retrieval |

### Meta
Skills about Claude Code itself.

| Skill | Purpose |
|---|---|
| `skill-stocktake` | Audit skill library for quality |
| `strategic-compact` | Context compaction at logical intervals |

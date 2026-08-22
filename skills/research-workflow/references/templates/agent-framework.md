# <Framework Name>

> **Type:** Concept Reference — AI Agent Framework
> **Applied in:** [Report Title](../reports/slug.md), …

*Generated: YYYY-MM-DD | Confidence: High/Medium/Low (<method>)*

---

## 1. What It Is

[1–3 sentence plain-English description: what problem it solves, who maintains it, what layer
of the stack it occupies — orchestration framework, agent runtime, workflow engine, etc.]

## 2. How It Works

[Architecture walkthrough. Cover the execution model — how the agent loop runs, what the
core primitives are, how state flows. Use diagrams or code blocks where they compress
explanation.]

## 3. Key Facts

| Fact | Detail |
|------|--------|
| Current stable version | vX.Y.Z |
| Maturity | Alpha / Beta / GA / Stable |
| Language / runtime | Python 3.10+ / TypeScript / Go / … |
| License | Apache 2.0 / MIT / … |
| Maintained by | Organisation / Foundation |
| GitHub stars (approx) | N k |
| Last release | YYYY-MM-DD |

## 4. Core Primitives

[List and describe the main building blocks: chains, runnables, graphs, agents, tasks, crews,
tools, memory stores, retrievers — whatever this framework exposes. Note which are stable vs
experimental. For each, state: what it does, how it composes with others, and any sharp edges.]

## 5. MCP Integration

[Does this framework support MCP (Model Context Protocol)? If yes: which transports (stdio /
SSE / HTTP), official or community package, version of MCP spec supported, tool filtering
support, multi-server support, authentication model. If no: how are external tools connected
instead, and is MCP on the roadmap?]

## 6. Multi-Agent Patterns

[What multi-agent coordination patterns does this framework support natively?
Cover: supervisor/worker, handoff/delegation, tool-as-agent, hierarchical subagents,
parallel fan-out, broadcast, consensus. Note which patterns require the base framework
vs an extension (e.g. LangGraph on top of LangChain). Code or config examples for the
most relevant patterns.]

## 7. Observability & Tracing

[Built-in observability: traces, spans, cost attribution, session replay. Vendor-specific
products (LangSmith, AgentOps, Langfuse). OpenTelemetry support. What is captured by
default vs requires manual instrumentation?]

## 8. Streaming & Events

[Streaming model: SSE, WebSocket, async iterator, callback-based. Event types emitted.
Is streaming first-class or bolted on? Does it stream intermediate tool results or only
final tokens?]

## 9. Session & State Management

[How is session state persisted across turns? In-memory, database (which?), file-based.
Session resume / fork semantics. Checkpointing frequency and durability guarantees.
Multi-user isolation model — are sessions namespaced, or shared by default?]

## 10. Budget & Resource Controls

[USD / token budget caps: built-in or application-layer? Per-session, per-user, per-group?
Rate limiting support. Effort / quality knobs (if any). How are runaway agents detected and
killed?]

## 11. Kubernetes Deployment

[Official Helm chart / operator / manifests: yes/no, link. Self-hosted platform option.
Recommended pod topology (one pod per session vs persistent service). PVC / storage
requirements. Horizontal scaling model. Any k8s-specific gotchas.]

## 12. Multi-Tenancy

[Per-user session isolation, namespace support, group-scoped access control. Is multi-tenancy
a first-class concept or DIY? How does the framework handle cross-tenant data isolation?
Any RBAC hooks or role-aware primitives?]

## 13. Cogito Fit

[Assess against cogito's three hard requirements: session isolation per user, per-session cost
controls, real-time streaming to a web frontend. Note which requirements are met natively,
which require custom plumbing, and which are blockers.

Additional cogito-specific angles to cover:
- Can it wrap or replace the Session Manager role?
- How does it integrate with agentgateway for MCP tool routing?
- Can AgentProfile / AgentPolicy CRDs drive this framework's configuration?
- Does it support Claude Code / Codex CLI as the underlying code agent harness?
- How does A2A protocol integration work (if at all)?]

## 14. Known Gaps / Limitations

[Sharp edges, things it does NOT do, open issues, CVEs if relevant, version churn / breaking
changes history, community size / maintenance health. Be specific — "limited k8s support" is
not a gap; "no official Helm chart as of vX.Y" is.]

## Sources

- [Name](URL) — fetched YYYY-MM-DD

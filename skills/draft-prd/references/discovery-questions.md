**Purpose & motivation**
- What is the underlying operational or business problem this change solves? (Not "deploy X" — what breaks, slows down, or becomes risky without this?)
- Why now? What changed that makes this the right time?
- Who is asking for this, and what outcome are they expecting?

**Logic & approach**
- What approach is proposed, and why that approach over alternatives? Have simpler options been ruled out (e.g. config change, existing library, a different tool, or doing nothing)?
- Is there prior art — internal or external — for this pattern on this cluster or elsewhere?
- What is the expected failure mode if this goes wrong, and how would recovery work?

**Applicability & scope**
- Which environments does this apply to (staging only, production, all)? Does the rollout need to be phased?
- Are there other services, namespaces, or teams that will be affected — even indirectly?
- Are there compliance, security, or regulatory constraints that shape the design?
- Is there a hard deadline or dependency on another change?

**Unknowns**
- What are you least certain about in this plan? What should be researched or validated before committing?

**Architecture & ownership** (mirrors `codebase-arch-review`)
- Which module or service owns this data or responsibility?
- Does this introduce a new service boundary or data store, or cross an existing one?
- What's the consistency model — eventual or strong — and does the design actually need the stronger one?
- What's the failure domain? What happens to dependents if this component is down?

**Edge cases & failure modes** (mirrors `codebase-eng-review`)
- What happens on partial failure, a retry, or a duplicate request?
- What are the concurrency considerations — can two callers hit this at once, and what breaks if they do?
- What's the rollback path if this fails mid-deploy or mid-migration?

**Security & secrets** (mirrors `security-review`)
- Does this introduce new auth or authz surface?
- Does this introduce new secrets or credentials, and how are they stored/rotated?
- Does this accept new input from an untrusted source?

**Docs & discoverability** (mirrors `doc-review` / `codebase-ux-review`)
- Who is the end user, and how will they discover this?
- Which docs need updating — README, runbook, API docs, CHANGELOG?
- What's the first-use experience if something goes wrong?

Answer these via exploration wherever possible (per Standard Mode step 1). Ask only what exploration can't settle — these are categories to check off, not a script to recite verbatim.

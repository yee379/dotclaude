**Purpose & motivation**
- What is the underlying operational or business problem this change solves? (Not "deploy X" — what breaks, slows down, or becomes risky without this?)
- Why now? What changed that makes this the right time?
- Who is asking for this, and what outcome are they expecting?

**Logic & approach**
- What approach is proposed, and why that approach over alternatives? Have simpler options been ruled out (e.g. config change, existing operator, a different tool)?
- Is there prior art — internal or external — for this pattern on this cluster or elsewhere?
- What is the expected failure mode if this goes wrong, and how would recovery work?

**Applicability & scope**
- Which environments does this apply to (staging only, production, all)? Does the rollout need to be phased?
- Are there other services, namespaces, or teams that will be affected — even indirectly?
- Are there compliance, security, or regulatory constraints that shape the design?
- Is there a hard deadline or dependency on another change?

**Unknowns**
- What are you least certain about in this plan? What should be researched or validated before committing?

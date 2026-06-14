# Architectural Instincts — How Staff Engineers See

These are not checklist items. They are the pattern recognition that separates "reviewed the design" from "caught the load-bearing assumption." Apply them throughout any architecture review.

1. **Boring by default** — Every company gets about three innovation tokens. New infrastructure, novel patterns, and custom protocols each spend one. Everything else should be proven technology (McKinley, Choose Boring Technology). Before adding anything novel, ask: what existing solution almost works? How far would we need to bend it?

2. **Blast radius instinct** — Every structural decision evaluated through "what's the worst case and how many systems/people does it affect?" Small blast radius = safe to try. Large blast radius = needs confidence before committing.

3. **Reversibility preference** — Favour decisions that are cheap to undo. Data model decisions, protocol choices, and service splits are expensive to reverse. Configuration and deployment topology are cheap. Weight them accordingly.

4. **Conway's Law is not optional** — The system will mirror the communication structure of the team that built it. Design both intentionally. If the team structure is wrong for the target architecture, say so explicitly (Skelton/Pais, Team Topologies).

5. **Failure domain isolation** — Every dependency is a potential blast radius amplifier. Ask: if this dependency goes down, what else goes with it? Design failure domains deliberately, not accidentally.

6. **Essential vs accidental complexity** — Before adding any new abstraction: "Is this solving a real problem or one we created?" The right question is not "is this elegant?" but "does this exist because reality requires it?" (Brooks, No Silver Bullet).

7. **Data gravity** — Data is harder to move than code. Where data lives determines what can be fast, what must be consistent, and what can be eventual. Get data ownership right before service boundaries, not after.

8. **Incremental over revolutionary** — Strangler fig, not big bang. If the architecture requires a cutover, it's not architecture — it's a rewrite risk in a diagram. Every architectural change should be a sequence of independently deployable steps (Fowler).

9. **Operational cost is a first-class concern** — A beautiful architecture that requires heroic ops is not beautiful. Design for tired humans at 3am, not your best engineer on their best day.

10. **The two-week smell test** — If a competent engineer can't understand and ship a small feature in two weeks, the architecture has an onboarding problem. Cognitive load is an architectural property (Skelton/Pais).

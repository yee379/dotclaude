# How to Ask Questions During Review

This protocol applies to all codebase review skills (arch-review, eng-review, design-review). Each skill may add domain-specific criteria for option evaluation.

## Core rules

- **One issue = one AskUserQuestion call.** Never combine issues.
- Describe the problem concretely — what structural decision is wrong, what the consequences are, where it shows up in production.
- Present 2-3 options including "do nothing" where reasonable.
- For each option: effort, reversibility, operational cost, innovation tokens spent.
- **Map reasoning to a specific instinct or engineering principle.** One sentence connecting the recommendation to the reasoning (boring by default, data gravity, failure domain isolation, minimal diff, explicit over clever, etc.).
- Label with issue NUMBER + option LETTER (e.g., "3A", "3B").
- **Escape hatch:** If a section has no issues, say so and move on. If an issue has an obvious answer with no real alternatives, state what you'll do and continue — don't waste a question on it. Only use AskUserQuestion when there is a genuine decision with meaningful tradeoffs.
- For each option, specify in one line: effort (human: ~X / CC: ~Y), risk, and maintenance burden. If the complete option is only marginally more effort than the shortcut with CC, recommend the complete option.

## In subagent mode (inside /board-review)

Suppress AskUserQuestion entirely. For every decision point, write a structured `### Decision:` entry in `## Decisions Required` and continue with the best safe default. Document the assumption explicitly.

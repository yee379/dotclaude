# Documentation Impact Tables

Load at the impact-table step. Use the table for the detected mode. Every row must have a
concrete "what changes" entry by the end of the review — not "possibly" or "TBD".

**`AFFECTED?`** — `yes` / `no` / `—`, where `—` means not applicable to this project or change type.
**`IN PLAN?`** — does the plan explicitly call out this doc update as work to be done?

Any row that is **AFFECTED: yes** and **IN PLAN?: no** is a gap. Surface each gap individually.

---

## Codebase mode

```
DOC                  | AFFECTED? | WHAT CHANGES                     | IN PLAN?
---------------------|-----------|----------------------------------|----------
README.md            | yes/no/—  | [what specifically changes]      | yes/no/n-a
ARCHITECTURE.md      | yes/no/—  | [what specifically changes]      | yes/no/n-a
CONTRIBUTING.md      | yes/no/—  | [what specifically changes]      | yes/no/n-a
CLAUDE.md            | yes/no/—  | [what specifically changes]      | yes/no/n-a
API docs             | yes/no/—  | [endpoints added/changed/removed]| yes/no/n-a
CHANGELOG.md         | yes/no/—  | [user-facing entry needed]       | yes/no/n-a
ADRs                 | yes/no/—  | [decisions to record]            | yes/no/n-a
CONTEXT.md           | yes/no/—  | [new/changed domain terms]       | yes/no/n-a
Runbook / on-call    | yes/no/—  | [new failure modes, new alerts]  | yes/no/n-a
Upgrade guide        | yes/no/—  | [breaking changes, migrations]   | yes/no/n-a
Inline code comments | yes/no/—  | [ASCII diagrams, complex logic]  | yes/no/n-a
Other: ___           | yes/no/—  | [specify]                        | yes/no/n-a
```

## Platform mode

```
DOC                           | AFFECTED? | WHAT CHANGES                         | IN PLAN?
------------------------------|-----------|--------------------------------------|----------
ARCHITECTURE.md (cluster)     | yes/no/—  | [cluster topology changes]           | yes/no/n-a
Runbook: <service>            | yes/no/—  | [new failure modes, procedures]      | yes/no/n-a
Onboarding guide              | yes/no/—  | [new steps, new prerequisites]       | yes/no/n-a
Platform README               | yes/no/—  | [new capabilities, changed setup]    | yes/no/n-a
ADRs                          | yes/no/—  | [infrastructure decisions to record] | yes/no/n-a
CONTEXT.md                    | yes/no/—  | [new/changed platform domain terms]  | yes/no/n-a
CHANGELOG / release notes     | yes/no/—  | [operator-facing changes]            | yes/no/n-a
Helm chart README             | yes/no/—  | [new values, changed defaults]       | yes/no/n-a
Capacity baseline doc         | yes/no/—  | [updated cluster capacity figures]   | yes/no/n-a
Network topology diagram      | yes/no/—  | [new services, new paths]            | yes/no/n-a
Secret rotation runbook       | yes/no/—  | [new secrets, changed rotation]      | yes/no/n-a
On-call rotation doc          | yes/no/—  | [new service, new rotation entry]    | yes/no/n-a
Application onboarding guide  | yes/no/—  | [new self-service capabilities]      | yes/no/n-a
Monitoring/alerting guide     | yes/no/—  | [new dashboards, new alert rules]    | yes/no/n-a
Security posture doc          | yes/no/—  | [RBAC changes, new policies]         | yes/no/n-a
Migration/upgrade guide       | yes/no/—  | [breaking changes, migration steps]  | yes/no/n-a
```

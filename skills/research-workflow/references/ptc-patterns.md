# Programmatic Tool Calling — Research Workspace

Reference for the three Anthropic PTC techniques used by the `research` and
`research-workflow` skills to reduce token consumption on multi-step research operations.
Source: [Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)

---

## Technique 1 — Tool Search (load index first, schemas on demand)

Before calling any research tool, load the lightweight index (~500 tokens):

```
Read: research/tools/index.json
```

Pick only the tool names you need, then load their full schemas:

```
Read: research/tools/schemas/<tool_name>.json
```

Never load all schemas upfront. A typical research session needs 2–3 tools — loading only
those saves 85% of the schema-token cost.

---

## Technique 2 — Programmatic Tool Calling (batch queries off-context)

When a task requires multiple tool calls — searching, checking for duplicates, reading
two concepts, inspecting the topic queue — write a Python code block instead of calling
tools one-by-one in prose. Intermediate results stay in the execution environment and
never enter the context window.

```python
import sys, os
sys.path.insert(0, "research/tools")
from research_tools import search_concepts, search_reports, get_concept, list_topics, blast_radius

# Check what's already covered before starting work
existing_concepts = search_concepts("SkillNet skill registry")
existing_reports  = search_reports("SkillNet integration AKH")
todo_items        = list_topics(status="todo")

# Only read full files if a match is found
if existing_concepts["total"] > 0:
    full = get_concept(existing_concepts["matches"][0]["file"])

# Check priority before adding a new topic
priority = blast_radius(["npm", "PyPI", "registry"])
```

**When to use PTC vs direct tools:**

| Situation | Approach |
|-----------|----------|
| Single file read (known path) | Use Read tool directly |
| Single Bash command (known invocation) | Use Bash tool directly |
| 2+ tool calls with no dependency between them | Write Python; batch all calls |
| Need to filter/transform before reading files | Write Python |
| Checking for duplicates before creating | Write Python (search first, get if found) |
| Session start orientation (topics + index scan) | Write Python |
| Pre-flight check before spawning subagents | Write Python |

---

## Technique 3 — Tool Use Examples (read examples before calling)

Every schema in `research/tools/schemas/` includes an `examples` array showing exact
input/output pairs. Before calling any tool, read the `examples` field:

```python
import json
schema = json.loads(open("research/tools/schemas/catalogue_concept.json").read())
for ex in schema["examples"]:
    print(ex["description"])   # explains WHEN to use this pattern
    print(ex["input"])          # shows exact field values
    print(ex["output"])         # shows what the tool returns
```

---

## Available tools

| Tool | Side effects | When to use |
|------|-------------|-------------|
| `search_concepts` | No | Before creating a concept, to check for duplicates |
| `search_reports` | No | Before creating a report, to check for duplicates |
| `get_concept` | No | Read a concept file without knowing its path |
| `get_report` | No | Read a report file without knowing its path |
| `list_topics` | No | Session start orientation; check blocked/todo items |
| `blast_radius` | No | Before adding any TOPICS.md row (required by priority rules) |
| `catalogue_concept` | **Yes** | Schema only — actual write uses Write tool after human review |
| `write_report` | **Yes** | Schema only — actual write uses Write tool after human review |
| `answer_charge` | **Yes** | Schema only — actual write uses Write tool after human review |

**Note on write tools:** `catalogue_concept`, `write_report`, and `answer_charge` schemas
define the structured input for human review. Use them to validate your intent before
writing — call the schema, confirm the fields look correct, then use the Write tool to
actually create the file per the existing workflow steps.

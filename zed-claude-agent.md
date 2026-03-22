# Zed Editor — Claude Agent + LiteLLM Integration Guide

> **Related documentation:**
> - [`litellm-integration.md`](./litellm-integration.md) — Exhaustive Claude Code CLI + LiteLLM testing (settings.json precedence, proxy findings, model mapping, auth)
> - [`zed-claude-acp-launch-chain.md`](./zed-claude-acp-launch-chain.md) — Deep research on how Zed spawns and communicates with the Claude agent process (source-code archaeology, env propagation, ACP protocol, patch analysis)
>
> **Note:** Zed's Agent panel supports multiple providers. This document
> covers the **Claude ACP** agent server (`claude-acp`). Copilot Chat
> (`copilot_chat`) and OpenCode (`opencode`) are separate provider paths
> configured independently in `~/.config/zed/settings.json` and are not
> covered here.

## Goal

Get the **Agent panel** in the [Zed editor](https://zed.dev) working with
the self-hosted LiteLLM proxy at SLAC (`sdf-llm.slac.stanford.edu`), so
that Claude Agent operates through the institutional proxy rather than
hitting Anthropic's API directly.

## Status: 🟢 Working (patch-free)

- ✅ Claude Code CLI fully working with LiteLLM (see `litellm-integration.md`)
- ✅ LiteLLM API validated (auth, streaming, tool use, token counting)
- ✅ Dex device-flow authentication working
- ✅ Key proxy/auth/model pitfalls documented
- ✅ Full ACP launch chain reverse-engineered (5 layers, env flow mapped)
- ✅ Two patches to `claude-agent-acp` package analysed — **neither required**
- ✅ Native Bun binary confirmed self-configuring from `settings.json`
- ✅ `control_request/initialize` ACP handshake protocol documented
- ✅ **Zed Agent panel working through sdf-llm — zero patches, zero `launchctl`**
- ✅ **Root cause of previous failures identified: Zed's `"proxy"` setting**

### ✅ Verified Working Configuration (2026-03-22)

**`~/.claude/settings.json`** — fully self-contained, no patches needed:
```json
{
  "model": "copilot-claude-sonnet-4.6",
  "apiKeyHelper": "cat ~/.claude/.token",
  "env": {
    "ANTHROPIC_BASE_URL": "https://sdf-llm.slac.stanford.edu",
    "ANTHROPIC_SMALL_FAST_MODEL": "copilot-claude-haiku-4.5",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "copilot-claude-haiku-4.5",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "copilot-claude-sonnet-4.6",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "copilot-claude-opus-4.6",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "NO_PROXY": "sdf-llm.slac.stanford.edu,localhost,127.0.0.1",
    "npm_config_proxy": ""
  }
}
```

> ⚠️ **No `//` comments inside the `env` object!** JSONC comments inside
> `env` silently break `apiKeyHelper`. See Critical Finding below.
>
> `ANTHROPIC_AUTH_TOKEN: ""` is no longer needed as of v2.1.79 —
> `apiKeyHelper` alone is sufficient to bypass the login gate.

**`~/.config/zed/settings.json`** — two changes required:

1. The `"proxy"` key must be commented out:
```jsonc
  // "proxy": "socks5://127.0.0.1:9051",
```

2. Remove any stale `ANTHROPIC_*` env vars from `agent.tool_permissions.tools.terminal.env`
   (these would override the correct values from `~/.claude/settings.json`
   when the agent runs terminal commands).

**Why:** Zed injects `HTTP_PROXY=socks5://...` into all subprocess
environments when `"proxy"` is set. The `claude` subprocess (running as
`node cli.js`) dies **before** it reads `settings.json` — so `NO_PROXY`
in settings.json cannot save it. The subprocess never gets the chance to
self-configure. Once the proxy line is removed from Zed settings, the
subprocess starts cleanly, reads `settings.json`, and everything works —
no patches, no `launchctl`, no shell wrappers.

> **Confirmed 2026-03-22:** Re-enabling Zed's `"proxy"` with
> `NO_PROXY=sdf-llm.slac.stanford.edu,localhost,127.0.0.1` in
> `~/.claude/settings.json` was tested — the Agent still fails. The
> subprocess dies before settings.json is loaded. The same `NO_PROXY`
> value **does** fix the CLI (native Bun binary), because Bun reads
> settings.json faster and has a different HTTP stack. Only `node cli.js`
> (the ACP runtime) is affected.

### Critical Finding: Zed's `"proxy"` Setting Is the Root Cause (2026-03-22)

The previous investigation in `zed-claude-acp-launch-chain.md` tested
two hypotheses for the Zed Agent failure (auth token timing, inherited
shell proxy vars) and disproved both. The actual root cause was missed
because it wasn't an inherited shell variable — **Zed itself injects
`HTTP_PROXY`** based on its own `"proxy"` config key:

| Source | Var | Strippable via `env -u`? | `NO_PROXY` in settings.json helps? |
|--------|-----|--------------------------|-------------------------------------|
| Shell (`~/.zshrc`) | `ALL_PROXY`, `HTTPS_PROXY`, etc. | ✅ Yes | ✅ Yes — native binary reads settings.json before network calls |
| **Zed settings** (`"proxy"`) | `HTTP_PROXY`, `npm_config_proxy` | ❌ No — Zed adds it after launch | ❌ No — `node cli.js` subprocess dies before reading settings.json |

This is why:
- `env -u ... open -a Zed` didn't help (Launch Services ignores caller env)
- `env -u ... /Applications/Zed.app/Contents/MacOS/zed` didn't help (Zed re-injects)
- `NO_PROXY` in `~/.claude/settings.json` didn't help (subprocess dies before loading it)
- The patches' `delete_env` worked (deletes the var from `process.env` inside the node process, after Zed injected it, before subprocess spawn)
- Commenting out `"proxy"` in Zed settings works (prevents injection entirely)

---

### Critical Finding: JSONC Comments in `env` Silently Break Auth (2026-03-22, v2.1.79)

`//` comment lines inside the `"env"` object in `~/.claude/settings.json`
cause `apiKeyHelper` to silently fail. The JSONC parser handles comments
correctly elsewhere in the file (hooks, permissions, model, etc.), but
the `env` block validation rejects the entire block when comments are
present — **with no error, no warning, and no debug log entry**.

| Symptom | Where |
|---------|-------|
| `Not logged in · Please run /login` | CLI (`claude -p ...`) |
| `Authentication required` | Zed Agent panel |
| `"authMethod": "none"` | `claude auth status` |
| `has Authorization header: false` → `Could not resolve authentication method` | `--debug-file` log |

**Reproduction** — a single `//` line inside `env` is enough:

```jsonc
  "env": {
    "ANTHROPIC_BASE_URL": "https://sdf-llm.slac.stanford.edu",
    "NO_PROXY": "sdf-llm.slac.stanford.edu"
    // "HTTP_PROXY": ""          ← THIS BREAKS apiKeyHelper
  }
```

**Fix:** Remove all `//` comments from the `env` object. Move commented-out
env vars into a separate note outside the JSON, or delete them entirely.

**Diagnosis:**

```bash
# Quick check — if this says "none", the env block is broken:
claude auth status
# Expected: "authMethod": "api_key_helper"

# Full debug:
claude -p "say PASS" --debug-file /tmp/claude-debug.log 2>&1
grep -E "auth|apiKey" /tmp/claude-debug.log
```

---

## 1. The Launch Chain

Zed's Agent panel does **not** call the Anthropic API directly. It spawns
a multi-layer process chain that terminates in a `claude` subprocess
communicating over stdio. Understanding this chain is essential for
debugging.

### 1.1 The five layers

```
Zed (macOS GUI app)
  └─ Layer 1: spawns Node process
       └─ Layer 2: node dist/index.js  (@zed-industries/claude-agent-acp)
            └─ Layer 3: dist/acp-agent.js — createSession() builds spawn env
                 └─ Layer 4: @anthropic-ai/claude-agent-sdk — ProcessTransport.initialize()
                      └─ Layer 5: child_process.spawn("node", ["cli.js", ...flags], { env: B })
                           └─ claude subprocess (reads ~/.claude/settings.json on startup)
```

### 1.2 Key details at each layer

**Layer 1 — Zed spawns Node.** Zed is a macOS GUI application — launched
from the Dock or Spotlight, not a terminal. This means `~/.zshrc`,
`~/.zprofile`, and friends are **never sourced**. The Node process inherits
only the minimal macOS GUI environment: `PATH=/usr/bin:/bin:/usr/sbin:/sbin`,
`HOME`, `USER`, `LOGNAME`, `TMPDIR`, and a few system vars. Any
`export ANTHROPIC_BASE_URL=...` in your shell profile is absent.

The ACP package lives under a content-hash cache path:
```
~/Library/Application Support/Zed/node/cache/_npx/<hash>/node_modules/@zed-industries/claude-agent-acp/
```

**Layer 2 — `index.js` entrypoint.** Reads
`/Library/Application Support/ClaudeCode/managed-settings.json` (enterprise
MDM path — does **not** exist on non-managed machines). If absent,
`process.env` remains the bare GUI environment. This is where Patch 1
injects env vars and deletes proxy vars (see §3).

**Layer 3 — `acp-agent.js` / `createSession()`.** Builds the spawn env:

```js
const options = {
    env: {
        ...process.env,                              // (1) node process env
        ...userProvidedOptions?.env,                 // (2) env from ACP client _meta params
        ...createEnvForGateway(this.gatewayAuthMeta), // (3) gateway overrides
    },
    executable: process.execPath,                    // Zed's managed Node binary
    pathToClaudeCodeExecutable: await claudeCliPath(),
};
```

`createEnvForGateway()` (when gateway auth is active) sets:
- `ANTHROPIC_BASE_URL` → Anthropic's gateway endpoint (overwrites proxy URL!)
- `ANTHROPIC_AUTH_TOKEN: ""` → bypasses the interactive login gate
- `ANTHROPIC_CUSTOM_HEADERS` → gateway auth headers

Because it spreads **last**, it overwrites any `ANTHROPIC_BASE_URL` set
earlier. This is the motivation for Patch 2's env re-asserts (see §3).

**Important:** `createSession()` reads `~/.claude/settings.json` via a
`SettingsManager` but uses it **only for model selection and permissions**.
It does **not** apply the `env` block from settings.json to `process.env`
or to the spawn env.

**Layer 4 — SDK `ProcessTransport`.** Receives the `options` from Layer 3,
constructs final env `B`, strips `NODE_OPTIONS` and `DEBUG`, then calls
`child_process.spawn()`.

**Layer 5 — `claude` subprocess.** What gets spawned:

| Context | Binary | Runtime |
|---------|--------|---------|
| Via Zed / ACP | `node .../claude-agent-sdk/cli.js` | Node.js |
| Via Homebrew CLI | `/opt/homebrew/bin/claude` | Bun (native arm64) |
| Via `CLAUDE_CODE_EXECUTABLE` | Whatever path that var points to | Varies |

Both are the same Claude Code application. In ACP mode it runs with
`--output-format stream-json --input-format stream-json` and communicates
with the SDK over stdio.

**The `claude` binary reads `~/.claude/settings.json` on startup and applies
its `env` block to its own `process.env`.** This is confirmed by empirical
testing (CLI works with zero `ANTHROPIC_*` vars in the shell) and by debug
logs showing `settingsEnv keys: ANTHROPIC_BASE_URL,...` during startup.

> **⚠️ Caveat:** Whether this self-configuration is sufficient in
> ACP-spawned mode (under Node.js rather than native Bun) has **not been
> confirmed**. The Zed agent test without patches failed — see §4.

### 1.3 The ACP protocol handshake

The SDK sends a `control_request/initialize` message to the subprocess
**before** any user prompt:

```json
{
  "type": "control_request",
  "request_id": "<uuid>",
  "request": {
    "subtype": "initialize",
    "hooks": null,
    "sdkMcpServers": null,
    "jsonSchema": null,
    "systemPrompt": null,
    "appendSystemPrompt": null,
    "agents": null
  }
}
```

The subprocess must respond with a `control_response` before the SDK sends
the first user message. Without this handshake, the subprocess exits
cleanly after ~410 ms.

**Full protocol sequence:**
1. Spawn: `node cli.js --output-format stream-json --verbose --input-format stream-json --replay-user-messages --session-id <uuid>`
2. → stdin: `control_request/initialize`
3. ← stdout: `system/init` + `control_response` (success)
4. → stdin: `user` message
5. ← stdout: `user` replay, `assistant` message(s), `result`

### 1.4 `ANTHROPIC_AUTH_TOKEN` vs `ANTHROPIC_API_KEY` — different roles

These two vars are frequently confused but serve entirely different purposes
in the Zed context:

| Variable | Purpose | Scope |
|----------|---------|-------|
| `ANTHROPIC_API_KEY` | The actual API credential sent as `x-api-key` / `Authorization: Bearer` on every HTTP request to the API (or proxy). This is what LiteLLM validates. | HTTP request layer |
| `ANTHROPIC_AUTH_TOKEN` | A **startup gate** for the `claude` binary. On startup, the binary checks: (1) is `ANTHROPIC_AUTH_TOKEN` set? → skip login; (2) does `~/.claude/.credentials.json` exist? → use stored OAuth; (3) neither → **launch interactive login flow** (hangs in headless ACP mode). Setting it to `""` satisfies check 1 — the binary sees the var is present and skips the login gate. | Binary startup only |

This is why `createEnvForGateway()` includes `ANTHROPIC_AUTH_TOKEN: ""` with
the comment `"Must be specified to bypass claude login requirement"` — it is
setting the startup gate, not the API credential.

---

## 2. The Patches

Two Python scripts patch the installed `claude-agent-acp` package to make
the Zed Agent work with the LiteLLM proxy. Both are idempotent and create
`.bak` backups. They must be re-run whenever Zed silently updates the
package via `npx`.

### 2.1 Patch 1: `patch-index-js.py` — env injection + proxy var deletion

**Target:** `dist/index.js` (Layer 2)

Inserts a block at line 2 (before any imports) that reads
`~/.claude/settings.json` and:

1. Iterates `settings.env` and sets each key on `process.env`
2. Iterates `settings.delete_env` and deletes each key from `process.env`

| What it does | Load-bearing? | Why |
|---|---|---|
| Injects `ANTHROPIC_BASE_URL` into node `process.env` | ⚠️ Ambiguous | Redundant in CLI mode (binary self-configures); unconfirmed in ACP mode |
| Injects `ANTHROPIC_API_KEY` into node `process.env` | ⚠️ Ambiguous | Same |
| Injects `ANTHROPIC_AUTH_TOKEN: ""` | ⚠️ Ambiguous | CLI tests show settings.json is read first; likely redundant; unconfirmed in ACP mode |
| Injects `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | ⚠️ Ambiguous | Same |
| **Deletes `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` / variants** | **✅ Confirmed** | T6 test proved `ALL_PROXY` without `NO_PROXY` hangs the binary; binary cannot remove inherited vars itself |

The `delete_env` feature is a custom extension — not a standard
`settings.json` key the binary processes. It strips SOCKS5/HTTP proxy vars
from `process.env` before the subprocess env is constructed via
`{...process.env}` in `createSession()`.

### 2.2 Patch 2: `patch-acp-agent-js.py` — gateway env override + debug logging

**Target:** `dist/acp-agent.js` (Layer 3)

Two injections into `createSession()`:

1. **Debug log** — logs `ANTHROPIC_BASE_URL`, `HTTP_PROXY`, and gateway
   auth state to stderr (visible in Zed's log output)
2. **Three env re-asserts** after the `createEnvForGateway()` spread:

```js
...(process.env.ANTHROPIC_BASE_URL ? { ANTHROPIC_BASE_URL: process.env.ANTHROPIC_BASE_URL } : {}),
...(process.env.ANTHROPIC_API_KEY ? { ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY } : {}),
...(process.env.ANTHROPIC_AUTH_TOKEN !== undefined ? { ANTHROPIC_AUTH_TOKEN: process.env.ANTHROPIC_AUTH_TOKEN } : {}),
```

| What it does | Load-bearing? | Why |
|---|---|---|
| Re-asserts `ANTHROPIC_BASE_URL` after gateway spread | ⚠️ Ambiguous | Binary may self-correct from settings.json; unconfirmed in ACP mode |
| Re-asserts `ANTHROPIC_API_KEY` after gateway spread | ⚠️ Ambiguous | Same |
| Re-asserts `ANTHROPIC_AUTH_TOKEN` after gateway spread | ⚠️ Ambiguous | Same |
| **Debug log of env state at `createSession()` time** | **✅ Useful** | Only visibility into node process env at call time |

---

## 3. Env Flow Diagram

```
macOS GUI launch (no shell profile)
  └─ Zed spawns: node dist/index.js
       │
       │  process.env = { PATH, HOME, USER, ... }  ← bare macOS GUI env
       │                 possibly: HTTP_PROXY=socks5://... (from Zed proxy config)
       │
       ├─ [PATCH 1, line 2 of index.js]
       │    reads ~/.claude/settings.json
       │    sets: ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN="",
       │          CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
       │    deletes: HTTP_PROXY, HTTPS_PROXY, ALL_PROXY, http_proxy, https_proxy,
       │             all_proxy, npm_config_proxy, npm_config_https_proxy
       │
       ├─ loadManagedSettings()
       │    → /Library/Application Support/ClaudeCode/managed-settings.json
       │    → null (absent on non-managed machine) → no-op
       │
       └─ runAcp() → ClaudeAcpAgent.createSession()
            │
            │  [PATCH 2 debug log: shows process.env state here]
            │
            │  spawn env B = {
            │    ...process.env,                          ← proxy vars deleted by Patch 1 ✓
            │    ...userProvidedOptions?.env,
            │    ...createEnvForGateway(gatewayAuthMeta), ← may set BASE_URL=gateway
            │    [PATCH 2 re-asserts]                     ← forces process.env to win
            │  }
            │
            └─ child_process.spawn("node", ["cli.js", ...flags], { env: B })
                 └─ claude subprocess
                      starts with env B
                      │
                      └─ reads ~/.claude/settings.json on startup
                           applies env block to own process.env:
                             ANTHROPIC_BASE_URL  = <proxy URL>     ✓
                             ANTHROPIC_API_KEY   = <jwt or "">     ✓
                             ANTHROPIC_AUTH_TOKEN = ""              ✓
                             CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = 1 ✓
                           proxy vars absent (deleted from B by Patch 1) ✓
                           │
                           └─ POST <proxy>/v1/messages
```

---

## 4. Investigation Status

### ✅ Confirmed working

| Scenario | Evidence |
|----------|----------|
| Native binary (`/opt/homebrew/bin/claude`) self-configures from `settings.json` in CLI mode | T1–T5: all PASS with zero `ANTHROPIC_*` env vars |
| Native binary works with `ALL_PROXY` + `NO_PROXY` set | T5: PASS |
| Native binary hangs with `ALL_PROXY` and **no** `NO_PROXY` | T6: HANG (confirmed failure mode) |
| Native binary completes full ACP pipe protocol round-trip from Node.js | T8a: PASS |
| `settings.json` `env` block is loaded by `node cli.js` subprocess | Debug log: `settingsEnv keys: ANTHROPIC_BASE_URL,...` |
| **Zed Agent works without patches when `"proxy"` is commented out** | Live testing 2026-03-22 |
| **`NO_PROXY` in settings.json fixes CLI but NOT Zed ACP** | Tested: re-enabling Zed proxy with full `NO_PROXY` still fails |
| **`NO_PROXY=...,localhost,127.0.0.1` fixes CLI hang with shell proxy vars** | `claude -p` with `ALL_PROXY` set now passes without `env -u` |

### ✅ Root cause resolved

The Zed Agent failure without patches was caused by **Zed's own `"proxy"`
setting** injecting `HTTP_PROXY=socks5://...` into the ACP node process
environment. This flowed into the `claude` subprocess spawn env via
`{...process.env}` in `createSession()`. The subprocess died instantly —
Node.js attempted to route through the SOCKS proxy and failed before
reading `settings.json`.

**Previous hypotheses from `zed-claude-acp-launch-chain.md` were correctly
disproved** (auth token timing, inherited shell proxy vars) — the actual
cause was a third source of proxy vars that wasn't tested: Zed itself.

| Hypothesis | Status | Evidence |
|---|---|---|
| `ANTHROPIC_AUTH_TOKEN` missing → binary hangs on auth check | ❌ Disproved | CLI works with zero `ANTHROPIC_*` vars |
| Inherited shell proxy vars (`ALL_PROXY` etc.) | ❌ Disproved | `env -u` + direct binary launch still failed |
| **Zed `"proxy"` setting injects `HTTP_PROXY` into subprocesses** | ✅ **Confirmed root cause** | Commenting out `"proxy"` in Zed settings → Agent works immediately |

### What the patches actually protected against

| Patch component | Necessary? | Why |
|---|---|---|
| Patch 1: env injection (`ANTHROPIC_BASE_URL`, etc.) | ❌ No | `settings.json` self-configuration is sufficient |
| Patch 1: `delete_env` (proxy var removal) | ✅ Yes — **if** Zed `"proxy"` is enabled | Only mechanism to strip vars Zed injects; `NO_PROXY` in settings.json cannot help because subprocess dies before reading it |
| Patch 2: gateway env re-asserts | ❌ No | Not relevant for non-gateway (self-hosted proxy) setup |
| Patch 2: debug logging | Nice to have | Only visibility into node process env at `createSession()` time |

**Bottom line:** If Zed's `"proxy"` is commented out, zero patches are
needed. If you need the proxy for other Zed traffic, only the `delete_env`
portion of Patch 1 is load-bearing. `NO_PROXY` in `~/.claude/settings.json`
is not a substitute — the `node cli.js` subprocess dies before it loads
settings.json. (The native Bun binary used by the CLI does not have this
problem — it reads settings.json before any network activity.)

### Historical: `node cli.js` standalone test issues

These findings from `zed-claude-acp-launch-chain.md` remain valid but are
no longer blocking — they were artefacts of testing `node cli.js` outside
the SDK harness:

| Scenario | Symptom | Explanation |
|----------|---------|-------------|
| `node cli.js` without `--print` flag | Exits at ~410 ms | TUI `initLayout()` detects non-TTY, exits |
| `node cli.js` with `--print` + correct flags | Stalls ~4.4 s then SessionEnd | stdin-close race + `FXz()` init timing |
| `node cli.js` via `test-acp-spawn.mjs` | Exits at 410 ms or stalls | Incomplete ACP handshake outside SDK |

---

## 5. Configuration Details

### `~/.claude/settings.json`

```json
{
  "model": "copilot-claude-sonnet-4.6",
  "apiKeyHelper": "cat ~/.claude/.token",
  "env": {
    "ANTHROPIC_BASE_URL": "https://sdf-llm.slac.stanford.edu",
    "ANTHROPIC_SMALL_FAST_MODEL": "copilot-claude-haiku-4.5",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "copilot-claude-haiku-4.5",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "copilot-claude-sonnet-4.6",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "copilot-claude-opus-4.6",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "NO_PROXY": "sdf-llm.slac.stanford.edu,localhost,127.0.0.1",
    "npm_config_proxy": ""
  }
}
```

> ⚠️ **No `//` comments inside the `env` object!** See §2 Critical Finding.

This config is shared by both the CLI and the Zed Agent. The `claude`
subprocess reads it on startup and self-configures — no env vars need to
reach it from the parent process.

**What each key does:**

| Key | Required? | Purpose |
|-----|-----------|---------|
| `ANTHROPIC_BASE_URL` | ✅ Yes | Routes to sdf-llm instead of api.anthropic.com |
| `ANTHROPIC_SMALL_FAST_MODEL` | ✅ Yes | Overrides the internal "small fast model" used by WebFetch preflight, tool search, and prompt hooks. Defaults to `claude-haiku-4-5-20251001` which is **not mapped** on sdf-llm — causes "internal haiku submodel invalid" errors. Set to `copilot-claude-haiku-4.5`. |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | Recommended | Resolves `/model haiku` and skill hooks with `model: "haiku"`. Defaults to `claude-haiku-4-5-20251001` (not mapped). Set to `copilot-claude-haiku-4.5`. |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Recommended | Resolves `/model sonnet` and subagent alias `"sonnet"`. Defaults to `claude-sonnet-4-6` (not mapped). Set to `copilot-claude-sonnet-4.6`. |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | Recommended | Resolves `/model opus` and subagent alias `"opus"`. Defaults to `claude-opus-4-6` (not mapped). Set to `copilot-claude-opus-4.6`. |
| `ANTHROPIC_AUTH_TOKEN: ""` | ❌ Removed | Previously required to bypass the login gate in headless ACP mode. As of v2.1.79, `apiKeyHelper` alone is sufficient. Keeping it is harmless but unnecessary. |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | Recommended | Suppresses background calls to Anthropic servers (telemetry, updates). Not strictly required but good hygiene. |
| `NO_PROXY` | Recommended | Bypasses proxy for sdf-llm, localhost, and 127.0.0.1. **Required for CLI** when shell has `ALL_PROXY`/`HTTP_PROXY` set — without it, the CLI hangs. Does NOT help the Zed ACP subprocess (dies before loading settings.json). Include all three: `sdf-llm.slac.stanford.edu,localhost,127.0.0.1`. |
| `npm_config_proxy: ""` | Recommended | Blanks out the `npm_config_proxy` env var. Zed injects this (alongside `HTTP_PROXY`) when its `"proxy"` setting is active, and the shell may also set it via `.zshrc`/`.npmrc`. Node.js HTTP libraries honour it, so a stale `socks5://…` value causes hangs. Setting it to `""` in the `env` block ensures it is cleared for the CLI path; for the Zed ACP subprocess it is a belt-and-suspenders measure (the subprocess may die before loading settings.json if Zed's `"proxy"` is active — see §2 Critical Finding on Zed proxy). |
| `apiKeyHelper` | ✅ Yes | Reads fresh JWT from `~/.claude/.token` on each invocation. Preferred over hardcoding `ANTHROPIC_API_KEY` because the Dex JWT expires every ~12h. |
| `model` | ✅ Yes | Default `claude-sonnet-4-6` is not mapped on sdf-llm. Must use a `copilot-claude-*` alias. |

Verified working in both CLI and Zed Agent contexts (2026-03-22, v2.1.79).

### `~/.config/zed/settings.json`

Two changes required:

**1. Comment out the `"proxy"` key:**

```jsonc
  // "proxy": "socks5://127.0.0.1:9051",
```

If you need the SOCKS proxy for other Zed traffic (git, extensions, etc.),
see §8 for alternatives.

**2. Remove stale `ANTHROPIC_*` env vars from `agent.tool_permissions`:**

The `terminal.env` block under `agent.tool_permissions.tools.terminal`
should not contain `ANTHROPIC_API_KEY` or `ANTHROPIC_BASE_URL`. These
would override the correct values from `~/.claude/settings.json` when the
agent runs terminal commands (e.g. `curl`, `claude`).

### Model names

Must use `copilot-claude-*` aliases — the default `claude-sonnet-4-6` is
not mapped on sdf-llm.

| Alias | Tier |
|-------|------|
| `copilot-claude-haiku-4.5` | Fast, cheap |
| `copilot-claude-sonnet-4` | Balanced |
| `copilot-claude-sonnet-4.5` | **Recommended default** |
| `copilot-claude-sonnet-4.6` | Latest Sonnet |
| `copilot-claude-opus-4.5` | High capability |
| `copilot-claude-opus-4.6` | Highest capability |

Set the default via `"model"` in `settings.json` (top-level key, not inside
`env`). The Zed Agent panel may also send a model name via ACP — if it sends
an unmapped name, the request will fail with 400.

---

## 6. Token Management

### Acquiring a token (Dex device flow)

```bash
# Step 1: Request device code
DEVICE_RESP=$(curl -s -X POST https://dex.slac.stanford.edu/device/code \
  -d "client_id=ai-playground-cli&scope=openid email profile groups offline_access")

# Step 2: Open verification URL in browser
echo "$DEVICE_RESP" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(f'Open: {d[\"verification_uri_complete\"]}')"

# Step 3: Authenticate in browser, then poll for token
DEVICE_CODE=$(echo "$DEVICE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['device_code'])")
TOKEN_RESP=$(curl -s -X POST https://dex.slac.stanford.edu/token \
  -d "grant_type=urn:ietf:params:oauth:grant-type:device_code&device_code=$DEVICE_CODE&client_id=ai-playground-cli")

# Step 4: Save token
echo "$TOKEN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'],end='')" \
  > ~/.claude/.token
chmod 600 ~/.claude/.token
```

### Checking token validity

```bash
python3 -c "
import json, base64, time
t = open('$HOME/.claude/.token').read()
p = json.loads(base64.urlsafe_b64decode(t.split('.')[1] + '=='))
remaining = (p['exp'] - time.time()) / 3600
print('VALID' if remaining > 0 else 'EXPIRED', f'({remaining:.1f}h remaining)')
"
```

The token expires every ~12 hours. Refresh by re-running the device flow.

---

## 7. Troubleshooting

### Agent panel shows "Query closed before response received"

The `claude` subprocess is dying before completing the ACP handshake.
Most likely cause: **proxy vars in the subprocess environment**.

1. **Check Zed's proxy setting:**
   ```bash
   grep -i proxy ~/.config/zed/settings.json
   ```
   If `"proxy": "socks5://..."` is active (not commented out), that's the
   problem. Comment it out: `// "proxy": "socks5://..."`.

2. **Check what the ACP process actually sees:**
   ```bash
   ps eww $(pgrep -f "node.*claude-agent-acp") | tr ' ' '\n' | grep -iE "PROXY|ANTHROPIC" | sort -u
   ```
   If `HTTP_PROXY=socks5://...` appears, it's being injected by Zed.

3. **Check token validity.** Expired JWT → 401 → subprocess may exit
   immediately.

### Agent panel shows "Authentication required"

The `apiKeyHelper` is silently failing. Most common cause: **JSONC
comments (`//`) inside the `"env"` object in `~/.claude/settings.json`**.

1. **Remove all `//` comments from the `env` block.** Even a single
   comment line breaks the env parser and causes `apiKeyHelper` to be
   ignored entirely — with zero log output. See §2 Critical Finding.

2. **Check token validity.** Expired JWT → 401 → "Authentication required".
   ```bash
   python3 -c "import json,base64,time; t=open('$HOME/.claude/.token').read(); \
     p=json.loads(base64.urlsafe_b64decode(t.split('.')[1]+'==')); \
     print('VALID' if p['exp']>time.time() else 'EXPIRED', f'({(p[\"exp\"]-time.time())/3600:.1f}h)')"
   ```

3. **Verify from CLI:**
   ```bash
   claude auth status
   # Expected: "authMethod": "api_key_helper"
   # Broken:   "authMethod": "none"
   ```

### Agent panel shows spinner / hangs indefinitely

1. **Check `ANTHROPIC_BASE_URL`.** If missing, the subprocess tries
   `api.anthropic.com` which won't accept the Dex JWT.

2. **Check for proxy vars.** Inherited proxy vars or Zed's `"proxy"`
   setting may cause the subprocess to hang connecting through SOCKS.

### Agent returns 400 errors

- **Model not mapped.** Ensure `"model": "copilot-claude-sonnet-4.5"` (or
  another `copilot-claude-*` alias) is set in `~/.claude/settings.json`.
  The default `claude-sonnet-4-6` is not configured on sdf-llm.

### Agent returns 401 errors

- **Token expired.** Refresh via device flow (§6).
- **Token not reaching subprocess.** Verify `apiKeyHelper` is configured
  in `~/.claude/settings.json` and that there are **no `//` comments
  inside the `env` object** (see §2 Critical Finding — this silently
  disables `apiKeyHelper`).
- **Quick check:** `claude auth status` — if `"authMethod": "none"`,
  the settings.json `env` block is broken.

### Agent works in CLI but not in Zed

The most common cause is Zed's `"proxy"` setting injecting SOCKS proxy
vars. The CLI works because it runs as the native Bun binary which handles
`NO_PROXY` correctly, or because your shell doesn't have proxy vars. In
Zed, the subprocess gets `HTTP_PROXY=socks5://...` from Zed itself.

| | CLI | Zed ACP |
|---|---|---|
| Binary | Native Bun (`/opt/homebrew/bin/claude`) | `node cli.js` (Homebrew Node) |
| Shell env | Full login shell (`.zshrc` etc.) | Bare macOS GUI env + Zed-injected vars |
| Proxy vars | From shell (strippable via `env -u`) | **From Zed settings (not strippable via `env -u`)** |
| Settings.json | Self-configures; sufficient | Self-configures; sufficient **if no SOCKS proxy vars** |

**Fix:** Comment out `"proxy"` in `~/.config/zed/settings.json`.

### Debugging with Claude CLI directly

```bash
# Verify settings.json is correct
claude -p "say PASS" --model copilot-claude-sonnet-4.5

# With debug logging
claude -p "say PASS" --model copilot-claude-sonnet-4.5 --debug-file /tmp/claude-debug.log
cat /tmp/claude-debug.log
```

Look for `[API:auth]`, `[API:request]`, and `[STARTUP]` entries.

---

## 8. Proxy Options and Alternatives

### The core constraint

Node.js (undici) **cannot speak SOCKS**. It only supports HTTP CONNECT
proxies via its `EnvHttpProxyAgent`. When `HTTP_PROXY=socks5://...` is in
the process environment, undici tries to speak HTTP to a SOCKS endpoint
and the process hangs or dies. This is why Zed's
`"proxy": "socks5://..."` kills the Claude ACP subprocess.

Additionally, the `node cli.js` subprocess dies **before** reading
`~/.claude/settings.json`, so `NO_PROXY` in settings.json cannot help
in the Zed ACP context (confirmed 2026-03-22). It does work for the
CLI (native Bun binary reads settings.json faster).

### Current working setup (Option A)

**Use `sdf-llm.slac.stanford.edu` directly — no proxy needed.**

`sdf-llm.slac.stanford.edu` has public DNS, a valid TLS cert, and is
directly reachable without any proxy. This is the simplest setup and is
what is currently configured and working. Zed's `"proxy"` is commented
out; the Claude Agent reaches sdf-llm directly.

| Pros | Cons |
|------|------|
| Zero moving parts | Zed's other traffic (git, extensions) loses proxy |
| No patches needed | Can't reach `llm.sdf` (internal hostname) |
| Already working | |

### Option B: Privoxy HTTP CONNECT bridge (for enterprise network access)

If you need to reach `llm.sdf.slac.stanford.edu` (internal hostname,
enterprise network only, self-signed TLS), or if you want Zed's proxy
to work for all traffic including Claude ACP, run a local HTTP CONNECT
bridge that forwards through your SOCKS tunnel.

**Architecture:**

```
Zed → "proxy": "http://127.0.0.1:10102"
  → node cli.js (HTTP CONNECT ✓)
    → privoxy (127.0.0.1:10102)
      → socks5://127.0.0.1:10101 (SSH tunnel to enterprise network)
        → llm.sdf.slac.stanford.edu
```

Node.js can speak HTTP CONNECT natively, so the subprocess won't die on
startup. The bridge converts HTTP CONNECT → SOCKS5 transparently.

**Install:**

```bash
brew install privoxy
```

**Configure** — create/edit `/opt/homebrew/etc/privoxy/config`:

```
listen-address  127.0.0.1:10102
forward-socks5  /  127.0.0.1:10101  .
```

This tells privoxy to listen on port 10102 (HTTP CONNECT) and forward
all traffic through the SOCKS5 tunnel on port 10101.

**Start:**

```bash
# One-off
privoxy /opt/homebrew/etc/privoxy/config

# Or as a service
brew services start privoxy
```

**Zed settings** — change the proxy to HTTP:

```jsonc
"proxy": "http://127.0.0.1:10102",
```

**Claude settings** (`~/.claude/settings.json`) — point at the internal
hostname:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://llm.sdf.slac.stanford.edu",
    "ANTHROPIC_AUTH_TOKEN": "",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "NO_PROXY": "localhost,127.0.0.1",
    "NODE_TLS_REJECT_UNAUTHORIZED": "0"
  },
  "apiKeyHelper": "cat ~/.claude/.token",
  "model": "copilot-claude-haiku-4.5"
}
```

> **⚠️ `NODE_TLS_REJECT_UNAUTHORIZED=0`** is needed because
> `llm.sdf.slac.stanford.edu` uses a self-signed TLS certificate. This
> disables TLS verification for all connections from the subprocess. A
> more secure alternative is to provide the CA certificate via
> `NODE_EXTRA_CA_CERTS=/path/to/ca.pem` in the `env` block.

| Pros | Cons |
|------|------|
| All Zed traffic works through proxy (git, extensions, Claude) | Extra dependency (privoxy) |
| Can reach internal `llm.sdf` endpoint | Must keep privoxy + SOCKS tunnel running |
| No patches needed | Self-signed TLS cert requires workaround |
| Node.js speaks HTTP CONNECT natively | More moving parts |

**Status:** Not yet tested. Needs verification.

### Option C: SSH port forward (no proxy at all)

Forward a local port through SSH directly to the internal LiteLLM
endpoint. No proxy infrastructure needed — just an SSH session.

```bash
ssh -L 19999:llm.sdf.slac.stanford.edu:443 <jumphost> -N
```

**Claude settings:**

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://localhost:19999",
    "ANTHROPIC_AUTH_TOKEN": "",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "ANTHROPIC_CUSTOM_HEADERS": "Host: llm.sdf.slac.stanford.edu",
    "NODE_TLS_REJECT_UNAUTHORIZED": "0"
  },
  "apiKeyHelper": "cat ~/.claude/.token",
  "model": "copilot-claude-haiku-4.5"
}
```

**Zed settings** — proxy not needed for Claude (localhost is direct).
The Zed SOCKS proxy is orthogonal — it can stay enabled or disabled
independently since the Claude Agent connects to localhost, not through
the proxy. If Zed's `"proxy"` is enabled, combine with Option D
(`delete_env` patch) to prevent SOCKS vars from killing the subprocess.
If it's commented out (as in Option A), no patch needed.

| Pros | Cons |
|------|------|
| No extra dependencies beyond SSH | Must keep SSH session alive |
| Simple to set up | Self-signed TLS cert requires workaround |
| Independent of Zed proxy setting | `ANTHROPIC_CUSTOM_HEADERS` needed for Host header |

**Status:** Documented in `litellm-integration.md` §4 as tested and
working for CLI. Not yet tested with Zed ACP.

### Option D: Minimal `delete_env` patch + keep SOCKS proxy

Keep Zed's SOCKS proxy for git/extensions. Apply only the `delete_env`
portion of Patch 1 to strip proxy vars from the ACP subprocess env.
The Claude Agent uses `sdf-llm.slac.stanford.edu` directly (no proxy).

```
Zed → "proxy": "socks5://127.0.0.1:10101"
  ├─ git, extensions, etc. → through SOCKS ✓
  └─ claude-agent-acp node process
       ├─ [PATCH: delete HTTP_PROXY, npm_config_proxy from process.env]
       └─ claude subprocess → direct to sdf-llm.slac.stanford.edu ✓
```

The patch is a small block injected at line 2 of `dist/index.js` in the
`claude-agent-acp` package. It reads `~/.claude/settings.json` and
deletes keys listed under a custom `delete_env` array:

```json
{
  "delete_env": [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
    "npm_config_proxy", "npm_config_https_proxy"
  ]
}
```

| Pros | Cons |
|------|------|
| Zed proxy works for all other traffic | Must re-apply patch after Zed updates `claude-agent-acp` |
| Direct to sdf-llm (no bridge, no tunnel) | `delete_env` is non-standard settings.json key |
| No extra dependencies | |

**Status:** Previously tested and working (see
`zed-claude-acp-launch-chain.md` §3).

### Option E: Upstream fix in `claude-agent-acp`

The ideal long-term fix. If `index.js` were changed to:

1. Read `~/.claude/settings.json` (not just the enterprise MDM path)
2. Apply the user `env` block to `process.env`
3. Support a `delete_env` key for removing inherited vars

Then no patches would be needed, and the Zed proxy could stay enabled.
The subprocess would inherit a clean env with the correct `NO_PROXY`.

**Status:** Not submitted. Would need a PR to
`@zed-industries/claude-agent-acp`.

### Summary

| Option | Proxy for Zed | Claude route | Extra deps | Patches | Tested |
|--------|--------------|-------------|------------|---------|--------|
| **A: Direct sdf-llm** (current) | ❌ No (Zed `"proxy"` disabled) | Direct to sdf-llm | None | None | ✅ Working |
| **B: Privoxy bridge** | ✅ HTTP CONNECT | Via bridge → SOCKS → llm.sdf | privoxy | None | ❌ Not yet |
| **C: SSH port forward** | ✅ Independent | Via SSH tunnel → llm.sdf | SSH session | None (combine w/ D if Zed proxy enabled) | ❌ Not yet |
| **D: Patch + SOCKS** | ✅ SOCKS | Direct to sdf-llm | None | `delete_env` | ✅ Previously |
| **E: Upstream fix** | ✅ Any | Any | None | None (upstream) | ❌ Not submitted |

### Request `claude-sonnet-4-6` alias on sdf-llm

Separate from the proxy issue: if the sdf-llm admin adds a model alias
`claude-sonnet-4-6` → `copilot-claude-sonnet-4.6`, Claude Code would work
without requiring `model` in `settings.json`. See `litellm-integration.md` §1.

---

## 9. Zed Settings — Multiple Agent Providers

Zed supports multiple agent providers simultaneously. A typical setup:

| Zed config key | Provider | What it does |
|---|---|---|
| `agent.default_model` with `provider: "copilot_chat"` | GitHub Copilot | Routes through GitHub's Copilot infrastructure |
| `agent_servers.opencode` | OpenCode | Separate agent server with its own model list |
| `agent_servers.claude-acp` | Claude ACP | Spawns `claude` subprocess → sdf-llm (this document) |

These do not conflict with each other. The `~/.claude/settings.json`
config only affects the Claude ACP path. Copilot Chat and OpenCode have
their own configuration in `~/.config/zed/settings.json`.

**Caution:** The `agent.tool_permissions.tools.terminal.env` block applies
to terminal commands run by **any** agent provider. Do not put
`ANTHROPIC_*` vars there — they would override the correct values from
`~/.claude/settings.json` when the Claude ACP agent runs terminal commands,
and would be meaningless for other providers.

---

## 9. Key Findings Reference (from CLI Testing)

These findings from `litellm-integration.md` apply to the Zed Agent because
it spawns the same `claude` binary:

| Finding | Impact on Zed Agent |
|---------|---------------------|
| **Inherited SOCKS proxy vars cause hangs** (Node.js can't speak SOCKS) | Patch 1 deletes them; without patches, `NO_PROXY` in settings.json may help |
| **`ANTHROPIC_AUTH_TOKEN=""` causes CLI hangs** | Different in ACP context — `""` is the correct value (login gate bypass); only dangerous in `settings.json` for CLI `-p` mode |
| **settings.json `env` overrides shell ENV** | Relevant because the subprocess reads settings.json; a wrong value in settings cannot be fixed from the spawn env |
| **Default model `claude-sonnet-4-6` not mapped on sdf-llm** | Must set `"model"` in settings.json |
| **JWT expires ~12h** | Use `apiKeyHelper` to read from disk; refresh token file as needed |
| **Extended thinking not available through LiteLLM** | LiteLLM strips the `thinking` param; Claude Code disables it on non-Anthropic hosts |
| **`modelAliases` does not work in settings.json** | Use top-level `model` key instead |

---

## 10. Key Findings Reference (from CLI Testing)
## 11. Open Questions

### Resolved

- [x] **Root cause of Zed Agent failure without patches.** Zed's `"proxy"`
  setting injects `HTTP_PROXY=socks5://...` into subprocess env. Commenting
  it out fixes the issue completely — no patches needed. (2026-03-22)
- [x] **Does `apiKeyHelper` work in ACP-spawned context?** Yes — verified
  working. The subprocess reads `settings.json` and executes the helper
  command. (2026-03-22)
- [x] **Can `delete_env` be replaced by commenting out Zed proxy?** Yes.
  The `NO_PROXY` in `settings.json` is applied by the subprocess but by
  that point it's too late — the subprocess dies before reading settings.
  The only fix is to prevent the proxy var from reaching the subprocess
  in the first place (comment out Zed `"proxy"` or use `delete_env` patch).
- [x] **Are patches necessary?** No — if Zed's `"proxy"` is commented out.
  The `claude` subprocess self-configures from `~/.claude/settings.json`.
  Only the `delete_env` portion of Patch 1 is needed if the proxy must
  remain enabled. (2026-03-22)
- [x] **Stale `ANTHROPIC_*` vars in Zed `terminal.env`.** Removed. These
  were for an earlier setup pointing at the internal hostname
  (`llm.sdf.slac.stanford.edu`) with a non-JWT key. (2026-03-22)

### Must investigate

- [ ] **Does the Zed Agent model selector override settings.json `model`?**
  If Zed sends an unmapped model name via ACP, the request will fail with 400.
- [ ] **Can Zed's `"proxy"` coexist with Claude Agent?** Test Option C
  (HTTP CONNECT proxy instead of SOCKS) or a minimal `delete_env`-only
  patch for environments where the SOCKS proxy is needed.
- [ ] **Which env vars in `~/.claude/settings.json` are truly required?**
  Minimal testing (CLI only) showed `ANTHROPIC_BASE_URL` + `apiKeyHelper`
  + `model` is sufficient. `ANTHROPIC_AUTH_TOKEN: ""` and
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` may be optional — needs
  verification in the ACP context specifically.
- [ ] **Can the `node cli.js` startup be made proxy-resilient?** The root
  issue is that `node cli.js` makes (or triggers) a network call before
  reading `settings.json`. If this could be fixed upstream, `NO_PROXY` in
  settings.json would be sufficient and the Zed proxy could stay enabled.

### Nice to have

- [ ] Automate token refresh so the Agent panel never hits expired JWTs
- [ ] Create a Zed task or keybinding for quick token refresh
- [ ] Test streaming, tool use, and file edits through the Agent panel
- [ ] Request upstream `claude-agent-acp` fix to read user settings.json
- [ ] Test model switching in the Agent panel (do all `copilot-claude-*` aliases work?)

---

## 12. Quick Validation Checklist

Run through after any configuration change:

1. **Token is fresh:**
   ```
   python3 -c "import json,base64,time; t=open('$HOME/.claude/.token').read(); p=json.loads(base64.urlsafe_b64decode(t.split('.')[1]+'==')); print('VALID' if p['exp']>time.time() else 'EXPIRED', f'({(p[\"exp\"]-time.time())/3600:.1f}h remaining)')"
   ```

2. **API responds:**
   ```
   curl -sf -H "Authorization: Bearer $(cat ~/.claude/.token)" \
     https://sdf-llm.slac.stanford.edu/v1/models | \
     python3 -c "import sys,json; ms=json.load(sys.stdin)['data']; print(f'{len(ms)} models available')"
   ```

3. **CLI works:**
   ```
   claude -p "say PASS" --model copilot-claude-haiku-4.5
   ```

4. **Zed proxy is disabled:**
   ```
   grep '"proxy"' ~/.config/zed/settings.json
   ```
   Should be commented out (`// "proxy": ...`) or absent.

5. **No stale ANTHROPIC vars in Zed terminal.env:**
   ```
   grep -A2 '"terminal"' ~/.config/zed/settings.json | grep ANTHROPIC
   ```
   Should return nothing.

6. **No SOCKS proxy in ACP process (after opening Agent panel):**
   ```
   ps eww $(pgrep -f "node.*claude-agent-acp") 2>/dev/null | tr ' ' '\n' | grep -i "socks"
   ```
   Should return nothing.

7. **Zed Agent works:**
   Open Agent panel, select Claude ACP provider, type a message, verify
   response appears.
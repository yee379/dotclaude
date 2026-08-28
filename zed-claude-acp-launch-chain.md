# How Zed Launches the Claude ACP Agent

**Topic:** Full launch chain from Zed UI → `claude-agent-acp` node process → `claude` binary subprocess; env propagation; and a re-examination of what the patches in `scripts/` actually protect against.
**Research date:** 2026-03-21
**Source:** Live inspection of installed packages (`@zed-industries/claude-agent-acp` v0.22.1, `@anthropic-ai/claude-agent-sdk` v0.2.76, `/opt/homebrew/bin/claude` native arm64 binary) and empirical testing on macOS arm64.

---

## 0. Reference: `ANTHROPIC_AUTH_TOKEN` vs `ANTHROPIC_API_KEY`

These two env vars are frequently confused but serve entirely different purposes.

### `ANTHROPIC_API_KEY`

The standard API credential sent as an HTTP header on every request to the Anthropic API (or a proxy). Transmitted as `x-api-key: <value>` or `Authorization: Bearer <value>`. This is what LiteLLM validates. It is the "what key do I use to call the API" credential and is consulted only when the `claude` binary constructs outbound HTTP requests.

### `ANTHROPIC_AUTH_TOKEN`

A startup gate specific to the `claude` CLI binary. It has nothing to do with API calls. On startup the binary checks for a valid authentication state in this order:

1. Is `ANTHROPIC_AUTH_TOKEN` set in env? → use it as a Bearer token and **skip the login prompt entirely**
2. Does `~/.claude/.credentials.json` exist? → use the stored OAuth session from `claude auth login`
3. Neither → **launch interactive OAuth login flow** — which hangs forever in headless ACP mode

Setting `ANTHROPIC_AUTH_TOKEN=""` (empty string) satisfies check 1: the binary sees the var is present, treats it as "auth token provided", and skips straight past the interactive login gate. The real API credential (`ANTHROPIC_API_KEY`) is then used separately for the actual HTTP requests.

This is why `createEnvForGateway()` in `acp-agent.js` includes the comment:

```js
ANTHROPIC_AUTH_TOKEN: "",  // Must be specified to bypass claude login requirement
```

It is setting the startup gate, not the API credential.

### Auth state in this proxy setup

- `~/.claude/.credentials.json` does not exist (no `claude auth login` session)
- `ANTHROPIC_API_KEY` is intentionally left empty in `~/.claude/settings.json` (the proxy supplies the real key upstream)
- `settings.json` contains `ANTHROPIC_AUTH_TOKEN: ""` which bypasses the interactive login check

> **⚠ Ambiguous:** Whether the binary reads `settings.json` (and thus sees `ANTHROPIC_AUTH_TOKEN: ""`) *before* or *after* it performs the auth check is not directly observable from the minified source. Empirical testing shows the native binary (`/opt/homebrew/bin/claude`) does read `settings.json` first — running `claude -p 'say hi'` with no ANTHROPIC vars in the shell env works correctly. Whether the same ordering holds in ACP headless mode (`--output-format stream-json`) is unconfirmed.

---

## 1. The Launch Chain

### 1.1 Layer 1 — Zed (GUI app) spawns a Node process

Zed runs the ACP agent using its own bundled Node binary, roughly equivalent to:

```sh
npx @zed-industries/claude-agent-acp
```

Because Zed is a **macOS GUI application** — launched from the Dock or Spotlight, not a terminal — it is not a child of any login shell. This means:

- `~/.zshrc`, `~/.zprofile`, `~/.profile` and equivalents are **never sourced**
- `process.env` inside the spawned Node process contains only the minimal set that macOS injects into all GUI processes: `PATH=/usr/bin:/bin:/usr/sbin:/sbin`, `HOME`, `USER`, `LOGNAME`, `TMPDIR`, and a few system vars
- Any `export ANTHROPIC_BASE_URL=...` lines in your shell profile are absent

The installed package lives under a content-hash cache path:

```
~/Library/Application Support/Zed/node/cache/_npx/<hash>/node_modules/@zed-industries/claude-agent-acp/
```

### 1.2 Layer 2 — `dist/index.js` entrypoint

`index.js` is the first file executed. Its relevant unpatched logic is:

```js
import { loadManagedSettings, applyEnvironmentSettings } from "./utils.js";
import { claudeCliPath, runAcp } from "./acp-agent.js";

const managedSettings = loadManagedSettings();
if (managedSettings) {
    applyEnvironmentSettings(managedSettings);
}
runAcp();
```

`loadManagedSettings()` reads a single hardcoded platform path — on macOS:

```
/Library/Application Support/ClaudeCode/managed-settings.json
```

This is an **enterprise MDM path** for system-wide policy deployment. It is not `~/.claude/settings.json`. On a non-managed machine it does not exist, so `loadManagedSettings()` returns `null`, `applyEnvironmentSettings` is never called, and `process.env` remains the bare GUI environment.

`applyEnvironmentSettings` itself can only set vars, not delete them:

```js
export function applyEnvironmentSettings(settings) {
    if (settings.env) {
        for (const [key, value] of Object.entries(settings.env)) {
            process.env[key] = value;
        }
    }
}
```

After this, `runAcp()` starts the ACP server loop on stdin/stdout and blocks.

### 1.3 Layer 3 — `dist/acp-agent.js` and `createSession()`

When the Zed UI sends a prompt over the ACP stdio stream, `ClaudeAcpAgent` calls `createSession()`. This builds an `options` object — including an explicit `env` block — and passes it to `query()` from `@anthropic-ai/claude-agent-sdk`:

```js
const options = {
    env: {
        ...process.env,                             // (1) node process env
        ...userProvidedOptions?.env,                // (2) env from ACP client _meta params
        ...createEnvForGateway(this.gatewayAuthMeta), // (3) gateway overrides (may set ANTHROPIC_BASE_URL)
    },
    executable: process.execPath,                   // Zed's managed Node binary
    pathToClaudeCodeExecutable: await claudeCliPath(),
    // ...
};
```

`createEnvForGateway()` is active when Zed is configured to use Anthropic's paid gateway (claude.ai subscription or enterprise). When `gatewayAuthMeta` is non-null it returns:

```js
{
    ANTHROPIC_BASE_URL: gatewayMeta.gateway.baseUrl,  // Anthropic's endpoint URL
    ANTHROPIC_CUSTOM_HEADERS: "...",
    ANTHROPIC_AUTH_TOKEN: "",   // comment: "Must be specified to bypass claude login requirement"
}
```

Because it spreads last, it would overwrite any `ANTHROPIC_BASE_URL` set earlier. This is the motivation for Patch 2 — but see §3.2 for a re-examination of whether it matters.

`createSession()` also creates a `SettingsManager` that reads `~/.claude/settings.json`, but this is used only for model selection and permission settings. **It does not apply the `env` block from `~/.claude/settings.json` to `process.env`, and the merged env does not flow into the subprocess env constructed above.**

`claudeCliPath()` resolves to `@anthropic-ai/claude-agent-sdk/cli.js` unless `CLAUDE_CODE_EXECUTABLE` is set.

### 1.4 Layer 4 — `@anthropic-ai/claude-agent-sdk` spawns the subprocess

The SDK's `ProcessTransport` class receives `options` from `createSession()`. In `initialize()` it constructs the final subprocess env:

```js
let { env: B = { ...process.env }, ... } = this.options;
delete B.NODE_OPTIONS;          // always stripped
delete B.DEBUG;                 // stripped unless DEBUG_CLAUDE_AGENT_SDK is set
if (!B.CLAUDE_CODE_ENTRYPOINT) B.CLAUDE_CODE_ENTRYPOINT = "sdk-ts";
```

`B` starts from `this.options.env` — the object built in `createSession()`. It then calls `child_process.spawn`:

```js
spawn(nodeExecutable, [pathToClaudeCodeExecutable, ...cliFlags], { env: B, ... })
```

The subprocess receives **exactly and only** the contents of `B` as its initial environment. There is no further shell evaluation, no profile sourcing.

### 1.5 Layer 5 — the `claude` subprocess

What gets spawned depends on context:

| Invocation | Binary |
|---|---|
| Via Zed / ACP (npx) | `node .../claude-agent-sdk/cli.js` — a Node script |
| Via Homebrew | `/opt/homebrew/bin/claude` — Mach-O 64-bit arm64 (Bun-compiled) |
| Via `CLAUDE_CODE_EXECUTABLE` | Whatever path that var points to |

Both are the same Claude Code application. In ACP mode it runs with `--output-format stream-json --input-format stream-json` and communicates with the SDK over stdio.

**The `claude` binary reads `~/.claude/settings.json` on startup and applies its `env` block to its own `process.env`.** This is confirmed by the binary containing `settings.json`, `ANTHROPIC_BASE_URL`, `settings_load_started`, and `settings_load_completed` as string literals, and by empirical testing of the native binary in CLI mode (see §2).

> **⚠ Ambiguous:** Whether this self-configuration is sufficient when the binary is spawned by the ACP SDK in headless mode is not yet confirmed. The Zed agent test without patches failed (see §7), meaning we cannot yet assert that self-configuration works correctly in the ACP-spawned case.

---

## 2. Why `claude` Works from the CLI Without Any `ANTHROPIC_*` Env Vars

```sh
❯ printenv | grep ANTHROPIC
❯ claude -p 'say hi'
Hi there! 👋 How can I help you today?
```

This works because **the `claude` binary is self-configuring**. On startup it reads `~/.claude/settings.json` and applies the `env` block to its own `process.env`, regardless of what its parent process passed.

In this setup, `~/.claude/settings.json` contains:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:19999",
    "ANTHROPIC_AUTH_TOKEN": "",
    "ANTHROPIC_API_KEY": "",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  }
}
```

There is no `~/.claude/.credentials.json` (no OAuth session). `ANTHROPIC_API_KEY` is explicitly empty. The binary can only be succeeding by routing to the local proxy via `ANTHROPIC_BASE_URL` — which it reads from `settings.json` itself. The proxy then supplies the real upstream API key.

> **⚠ Unconfirmed for ACP-spawned mode:** It was expected that the same self-configuration would happen when the binary is spawned by the ACP SDK in Zed. However, empirical testing (§7) showed the Zed agent panel failed to become interactive when patches were removed. The cause of that failure is not yet isolated — it may be unrelated to settings.json self-configuration — but the claim that self-configuration is sufficient in the ACP-spawned case cannot currently be made.

---

## 3. The Patches — What They Actually Protect

Two patches are applied to the installed `claude-agent-acp` package by the scripts in `scripts/`. Both are idempotent (strip old patches before reapplying) and create `.bak` backups on first run. They must be re-run whenever Zed silently updates the package via `npx`.

The original motivation for each patch was correct, but knowing that the binary self-configures from `settings.json` changes the analysis of what is genuinely load-bearing vs. belt-and-suspenders.

### 3.1 Patch 1: `patch-index-js.py` — Entry point env injection and proxy var deletion

**Target file:** `dist/index.js`

**What it does:** Inserts a block at line 2 (before any imports) that reads `~/.claude/settings.json` and:

1. Iterates `s.env` and sets each key on `process.env`
2. Iterates `s.delete_env` and deletes each key from `process.env`
3. Logs the result to stderr

**The env-injection part (item 1):** ⚠ **Ambiguous — may or may not be redundant.** The vars it injects — `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` — are present in `settings.json` and the native binary demonstrably reads them in CLI mode. Whether they are also self-applied correctly when the binary is spawned in ACP headless mode is unconfirmed (the Zed test without patches failed; root cause not yet isolated).

**The `delete_env` part (item 2): confirmed necessary in environments with `ALL_PROXY` set.** `delete_env` is not a standard `settings.json` key the binary processes — it is a custom feature of these patches. It strips SOCKS5/HTTP proxy vars (`HTTP_PROXY`, `HTTPS_PROXY`, `http_proxy`, `https_proxy`, `npm_config_proxy`, `npm_config_https_proxy`, `ALL_PROXY`, `all_proxy`) from the node `process.env` before the subprocess env is constructed from `{...process.env}`.

Direct testing confirmed: the native binary hangs when `ALL_PROXY=socks5://...` is set without `NO_PROXY=localhost,127.0.0.1`, because it routes `http://127.0.0.1:19999` through the SOCKS5 tunnel which cannot reach localhost on the remote end (see §7, T6). The Zed ACP process env does include `NO_PROXY=localhost,127.0.0.1` alongside the proxy vars, so this specific failure mode may not apply — but `delete_env` removes the risk entirely.

The binary has no mechanism to remove inherited proxy vars on its own.

**Summary of Patch 1:**

| What it does | Load-bearing? | Why |
|---|---|---|
| Injects `ANTHROPIC_BASE_URL` into node `process.env` | ⚠ Ambiguous | Confirmed redundant in CLI mode; unconfirmed in ACP-spawned mode |
| Injects `ANTHROPIC_API_KEY` into node `process.env` | ⚠ Ambiguous | Confirmed redundant in CLI mode; unconfirmed in ACP-spawned mode |
| Injects `ANTHROPIC_AUTH_TOKEN: ""` into node `process.env` | ⚠ Ambiguous | CLI tests show settings.json is read first, so likely redundant; unconfirmed in ACP mode |
| Injects `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | ⚠ Ambiguous | Confirmed redundant for native binary in CLI mode; unconfirmed in ACP-spawned mode |
| Deletes `HTTP_PROXY` / `HTTPS_PROXY` / variants | **Yes — confirmed** | T6 test proved ALL_PROXY without NO_PROXY hangs the binary; binary cannot remove inherited vars itself |

### 3.2 Patch 2: `patch-acp-agent-js.py` — Gateway env override and debug logging

**Target file:** `dist/acp-agent.js`

**What it does:** Two injections into `createSession()`:

1. **Debug log** immediately before the `options` block — logs `ANTHROPIC_BASE_URL`, `HTTP_PROXY`, and whether `gatewayAuthMeta` is active to stderr, visible in Zed's log output
2. **Three env re-asserts** after the `createEnvForGateway()` spread, to force `process.env` values to win:

```js
...(process.env.ANTHROPIC_BASE_URL ? { ANTHROPIC_BASE_URL: process.env.ANTHROPIC_BASE_URL } : {}),
...(process.env.ANTHROPIC_API_KEY ? { ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY } : {}),
...(process.env.ANTHROPIC_AUTH_TOKEN !== undefined ? { ANTHROPIC_AUTH_TOKEN: process.env.ANTHROPIC_AUTH_TOKEN } : {}),
```

**The env re-assert part (item 2):** ⚠ **Ambiguous — may or may not be redundant.** The original concern was that `createEnvForGateway()` would overwrite `ANTHROPIC_BASE_URL` in the spawn env with Anthropic's gateway URL. Whether the binary then self-corrects this from `settings.json` in ACP-spawned mode is unconfirmed (see §1.5 note). The re-asserts are harmless and provide a safety net.

**The debug log (item 1): genuinely useful.** It makes the final state of `process.env` visible at the point `createSession()` is called — specifically whether `ANTHROPIC_BASE_URL` is pointing to the local proxy and whether `gatewayAuthMeta` is active. This is invaluable when diagnosing why requests are going to the wrong endpoint, since the binary's own startup logging does not reveal these values.

**Summary of Patch 2:**

| What it does | Load-bearing? | Why |
|---|---|---|
| Re-asserts `ANTHROPIC_BASE_URL` after gateway spread | ⚠ Ambiguous | Self-correction from `settings.json` confirmed for CLI mode; unconfirmed for ACP-spawned mode |
| Re-asserts `ANTHROPIC_API_KEY` after gateway spread | ⚠ Ambiguous | Same as above |
| Re-asserts `ANTHROPIC_AUTH_TOKEN` after gateway spread | ⚠ Ambiguous | Same as above |
| Debug log of env state before `createSession()` | **Yes — confirmed useful** | Only visibility into node process env state at call time |

---

## 4. Env Flow Summary

```
macOS GUI launch (no shell profile)
  └─ Zed spawns: node dist/index.js
       │
       │  process.env = { PATH, HOME, USER, ... }  ← bare macOS GUI env
       │                 possibly: HTTP_PROXY=socks5://... (from Zed proxy setting)
       │
       ├─ [PATCH 1, line 2 of index.js]
       │    reads ~/.claude/settings.json
       │    sets: ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN="",
       │          CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1         ← redundant (binary handles)
       │    deletes: HTTP_PROXY, HTTPS_PROXY, http_proxy, https_proxy,        ← LOAD-BEARING
       │             npm_config_proxy, npm_config_https_proxy, ALL_PROXY, all_proxy
       │
       ├─ loadManagedSettings() → /Library/Application Support/ClaudeCode/managed-settings.json
       │    → null (absent on non-managed machine) → no-op
       │
       └─ runAcp() → ClaudeAcpAgent.createSession()
            │
            │  [PATCH 2 debug log: shows process.env state here]            ← USEFUL
            │
            │  spawn env B = {
            │    ...process.env,                          ← HTTP_PROXY deleted by Patch 1 ✓
            │    ...userProvidedOptions?.env,
            │    ...createEnvForGateway(gatewayAuthMeta), ← may set ANTHROPIC_BASE_URL=gateway
            │    [PATCH 2 re-asserts]                     ← redundant; binary overrides anyway
            │  }
            │
            └─ child_process.spawn("node", ["cli.js", ...flags], { env: B })
                 └─ claude binary subprocess
                      starts with env B (possibly ANTHROPIC_BASE_URL=gateway URL from B)
                      │
                      └─ reads ~/.claude/settings.json on startup             ← SELF-CONFIGURES
                           applies env block to own process.env:
                             ANTHROPIC_BASE_URL = http://127.0.0.1:19999  ✓ (overrides B)
                             ANTHROPIC_API_KEY  = ""                       ✓
                             ANTHROPIC_AUTH_TOKEN = ""                     ✓
                             CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = 1  ✓
                           HTTP_PROXY is absent (deleted from B by Patch 1) ✓
                           │
                           └─ POST http://127.0.0.1:19999/v1/messages
                                └─ litellm-proxy.py → upstream LiteLLM
```

---

## 5. What Would Break Without the Patches

> **⚠ Note:** This section was written before live testing. Empirical testing (§7) showed the Zed agent fails without patches even when `NO_PROXY=localhost,127.0.0.1` is present alongside the proxy vars. The root cause of that failure is not yet isolated. The table below reflects what is confirmed vs. what is still ambiguous.

| Scenario | Effect without patches | Confidence |
|---|---|---|
| `ALL_PROXY` set, `NO_PROXY` absent | Binary hangs routing `http://127.0.0.1:19999` through SOCKS5 | ✅ Confirmed (T6) |
| `ALL_PROXY` set, `NO_PROXY=localhost,127.0.0.1` present | Native binary works (T5). Whether `node cli.js` in ACP mode also works is unconfirmed — T7 was inconclusive | ⚠ Ambiguous |
| No proxy vars at all | Native binary works in CLI mode. ACP-spawned mode untested without patches | ⚠ Ambiguous |
| Gateway auth active in Zed | `createEnvForGateway()` sets `ANTHROPIC_BASE_URL` to Anthropic's endpoint; binary may or may not self-correct from `settings.json` in ACP mode | ⚠ Ambiguous |
| Settings.json `env` block missing or wrong | Patches are the only source of correct env values for the node process; binary would receive wrong spawn env | ✅ Patches needed |

---

## 6. Cleaner Alternatives

### `launchctl setenv` (makes Patch 1's env injection redundant)

Setting env vars at the launchd level makes them available to all GUI processes without file patching:

```sh
launchctl setenv ANTHROPIC_BASE_URL http://127.0.0.1:19999
launchctl setenv ANTHROPIC_API_KEY sk-your-litellm-key
launchctl setenv ANTHROPIC_AUTH_TOKEN ""
launchctl setenv CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC 1
launchctl unsetenv HTTP_PROXY
launchctl unsetenv HTTPS_PROXY
```

This does not survive reboots. A `~/Library/LaunchAgents/` plist is required for persistence. This approach addresses the node-process env gap but still cannot remove vars that are set dynamically by Zed (e.g. its own proxy setting propagating `HTTP_PROXY`).

### Upstream fix in `claude-agent-acp`

The ideal fix would be for `index.js` to call `applyEnvironmentSettings` with the user settings from `~/.claude/settings.json` (not just the enterprise MDM path) and to add `delete_env` support. This would make Patch 1 entirely unnecessary. Patch 2 would remain useful only for its debug logging.

### Simplest safe minimum

> **⚠ Unconfirmed:** It was hypothesised that if `HTTP_PROXY` is absent and `settings.json` is correctly configured, neither patch would be required. This has **not been confirmed** — the Zed agent test without patches failed (§7) and the root cause is not yet known. Do not remove patches until the failure mode is fully understood.

---

## 7. Investigation Log

A step-by-step record of changes made and observations, to track what is actually required.

### 2026-03-21 — Patches removed; baseline test

**Action:** Both patches removed from all installed `claude-agent-acp` package copies.

- `acp-agent.js` — restored from `.bak` (backup existed from original patch run)
- `index.js` — patch block stripped via regex (no `.bak` existed); the `// --- LITELLM_PROXY_PATCH --- … // --- END LITELLM_PROXY_PATCH ---` block removed

Both cache dirs cleaned:
```
~/Library/Application Support/Zed/node/cache/_npx/a88cf5ea522c16cf/…
~/Library/Application Support/Zed/node/cache/_npx/b17a338e32143bc4/…
```

Verified clean with: `grep -r "LITELLM_PROXY_PATCH" … → All clean`

**Current state of `~/.claude/settings.json` at time of removal:**
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:19999",
    "ANTHROPIC_AUTH_TOKEN": "",
    "ANTHROPIC_API_KEY": "",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  }
}
```
(Plus `hooks` block — omitted for brevity. No `delete_env` key present.)

**Hypothesis being tested:** The `claude` binary reads `~/.claude/settings.json` on startup and self-applies its `env` block, making the node-process env injection in Patch 1 redundant. Patch 2's gateway re-asserts are similarly redundant. Neither patch should be required for correct proxy routing.

**Planned test sequence:**

1. Restart Zed (force reload of now-clean JS files) and send a prompt in the agent panel
   - **Pass:** response arrives via proxy → binary self-configuration confirmed
   - **Fail → connection refused:** binary not routing to proxy; settings.json env not applied
   - **Fail → auth error / login prompt hang:** `ANTHROPIC_AUTH_TOKEN=""` timing issue
   - **Fail → "Query closed before response received":** background `api.anthropic.com` call hang (missing `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`)

2. If step 1 passes: check whether `HTTP_PROXY` is present in the Zed process env
   - `Activity Monitor → claude-agent-acp process → Open Files & Ports` or
   - `ps eww <pid> | tr ' ' '\n' | grep PROXY`
   - **If absent:** `delete_env` in Patch 1 was never needed in this environment
   - **If present:** re-apply only the `delete_env` portion and retest

3. Document actual result and update conclusions in §5 accordingly.

**Result — Step 1 FAILED: agent panel processes start but no prompt is ever available**

Zed was restarted and the ACP process chain was observed in `ps`:

```
79881  npm exec @zed-industries/claude-agent-acp@0.22.2   (Ss)
79979  node .../claude-agent-acp                          (S)
79980  claude                                             (S)
```

All three processes started and remained alive (all in `S` / interruptible sleep). The Zed agent panel never became interactive. The Zed log showed:

```
16:55:22  INFO  Received prompt request for session: 2fe5dee7-…
16:55:22  INFO  Thread::send called with model: Claude Sonnet 4.6
16:59:13  INFO  Cancelling on session: 2fe5dee7-…   ← Zed gave up after ~4 min
16:59:22  INFO  Received prompt request …            ← retry, same result
```

**Diagnosis via `lsof` and `ps eww`:**

The ACP node process (79979) had the following proxy vars in its env (inherited from Zed's own environment, which has a SOCKS5 tunnel configured):

```
HTTP_PROXY=socks5://127.0.0.1:9051
HTTPS_PROXY=socks5://127.0.0.1:9051
ALL_PROXY=socks5://127.0.0.1:9051
NO_PROXY=localhost,127.0.0.1
```

These flow into the `claude` subprocess (79980) via `{...process.env}` in `createSession()`.

`lsof -p 79980` showed:
- `stderr (fd 2) → /dev/null` — no debug output visible
- **Zero TCP connections** — the `claude` binary made no network calls at all
- Only pipes and unix sockets back to the parent node process

The zero-TCP finding rules out "background call to `api.anthropic.com` hanging". The binary was stuck **before making any network call**.

**Initial hypothesis (subsequently disproved): `ANTHROPIC_AUTH_TOKEN` timing**

The first suspect was the auth startup gate (see §0): spawn env has no `ANTHROPIC_AUTH_TOKEN`, no `~/.claude/.credentials.json` exists, so perhaps the binary entered the interactive OAuth login flow before reading `settings.json`. However, this is ruled out by the following observation:

> Running `claude -p 'say hi'` from the terminal — with `printenv | grep ANTHROPIC` returning nothing — works correctly.

There is no `ANTHROPIC_AUTH_TOKEN` in the shell env either, and no credentials file. Yet the CLI invocation succeeds. This proves the binary reads `settings.json` and applies its `env` block (including `ANTHROPIC_AUTH_TOKEN: ""`) **before** the auth check, in both interactive and headless modes. The auth timing hypothesis is therefore wrong.

**Revised hypothesis: proxy vars + runtime difference**

The one thing that genuinely differs between a CLI invocation and an ACP-spawned invocation is the **binary being executed**:

| Invocation | Runtime | Proxy var handling |
|---|---|---|
| `claude -p 'say hi'` from shell | Native Bun binary (`/opt/homebrew/bin/claude`) | Bun's `fetch` respects `NO_PROXY` — `http://127.0.0.1:19999` goes direct |
| ACP-spawned subprocess | `node cli.js` under Homebrew Node (`/opt/homebrew/Cellar/node/25.1.0/bin/node`) | Node's HTTP / `undici` behaviour with `ALL_PROXY` + `NO_PROXY` is different |

`lsof` confirmed the ACP subprocess executable is `/opt/homebrew/Cellar/node/25.1.0/bin/node`, not the native Bun binary. So the proxy vars (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`) may interact with Node.js's module loading, `undici`, or an npm-level proxy shim in a way that causes a hang before any explicit `connect()` call — which would explain the zero-TCP observation.

The `NO_PROXY=localhost,127.0.0.1` entry is present but may be insufficient: `ALL_PROXY` is known to override `NO_PROXY` in some runtimes and HTTP libraries.

**Next step:** Apply a minimal targeted patch to `acp-agent.js` only — delete `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `http_proxy`, `https_proxy`, `all_proxy` from the spawn env — then retest. Do **not** add `ANTHROPIC_AUTH_TOKEN` to the spawn env (it is not needed: the binary handles it via `settings.json`). This will isolate whether the proxy vars alone are the root cause.

---

### 2026-03-21 — Native binary ENV var tests

To establish a clean baseline independent of the ACP/node layer, the native binary (`/opt/homebrew/bin/claude`) was tested directly with controlled ENV configurations. All tests used `-p 'say: Tn_LABEL' --max-turns 1`.

Shell env at time of testing had: `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY=socks5://127.0.0.1:9051`, `NO_PROXY=localhost,127.0.0.1` — no `ANTHROPIC_*` vars.

| Test | ENV configuration | Result |
|---|---|---|
| T1 | Current shell env (proxy vars, no ANTHROPIC vars) | ✅ PASS — settings.json self-configuration works with proxy vars present |
| T2 | `env -i HOME=$HOME` — completely clean, only HOME | ✅ PASS — binary self-configures from settings.json with no inherited env at all |
| T3 | Clean + `ANTHROPIC_BASE_URL=http://127.0.0.1:19999` explicit | ✅ PASS — explicit env var works, consistent with settings.json |
| T4 | Clean + base URL + `ANTHROPIC_API_KEY=""` + `ANTHROPIC_AUTH_TOKEN=""` | ✅ PASS — empty key + empty auth token work together |
| T5 | Clean + ALL proxy vars + `NO_PROXY=localhost,127.0.0.1` + base URL | ✅ PASS — native binary correctly bypasses SOCKS5 for localhost via NO_PROXY |
| T6 | Clean + ALL proxy vars, **no `NO_PROXY`** + base URL | ❌ HANG — `ALL_PROXY` without `NO_PROXY` routes `http://127.0.0.1:19999` through SOCKS5 tunnel; connection never reaches local proxy |

**Key finding from T6:** `ALL_PROXY` without `NO_PROXY=localhost,127.0.0.1` is a confirmed failure mode for the native binary. The SOCKS5 tunnel exits on a remote machine which cannot reach `127.0.0.1:19999` locally.

**Key finding from T1–T5:** The native binary is entirely self-sufficient via `settings.json` in all proxy configurations where `NO_PROXY` covers localhost. No ANTHROPIC vars need to be set in the spawning shell's environment.

**Note on `--print` mode and `node cli.js`:** The native binary (`/opt/homebrew/bin/claude`) handles `--print` / `-p` mode correctly because it reads `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` from `settings.json` before making background calls. The `node cli.js` variant of the same binary hangs in `--print` mode — background calls to `api.anthropic.com` are not suppressed in time (or at all) in that runtime. This is a runtime difference, not a settings difference.

---

### 2026-03-21 — Testing the proxy var hypothesis directly

**Test 1: native Bun binary with all proxy vars set**

```sh
HTTP_PROXY=socks5://127.0.0.1:9051 \
HTTPS_PROXY=socks5://127.0.0.1:9051 \
ALL_PROXY=socks5://127.0.0.1:9051 \
NO_PROXY=localhost,127.0.0.1 \
  /opt/homebrew/bin/claude -p 'say: NATIVE_PROXY_TEST' --max-turns 1
```

**Result: PASS** — returned `NATIVE_PROXY_TEST` immediately. The native Bun binary works correctly with all proxy vars present; `NO_PROXY=localhost,127.0.0.1` is sufficient for it to reach `http://127.0.0.1:19999` directly.

**Test 2: `node cli.js` (ACP runtime) without proxy vars, using `--print` mode**

```sh
node cli.js -p 'say: NODE_NO_PROXY_TEST' --max-turns 1
```

**Result: HUNG** — no output, zero TCP connections, after 30+ seconds. Killed manually.

This initially looked like evidence that `node cli.js` was broken regardless of proxy vars. However, the README documents this explicitly:

> `claude --print` (and `claude -p`) hang even with `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` set, because `--print` mode runs the full interactive startup sequence which makes more background calls than ACP headless mode.

So `--print` mode always hangs when the LiteLLM token is used, because the binary makes background calls to `api.anthropic.com` that receive no meaningful response. This test was using the wrong invocation mode.

**Test 3: `node cli.js` in actual ACP mode (`--output-format stream-json --input-format stream-json`), with and without proxy vars**

Ran the binary in the same mode the SDK uses, first without proxy vars, then with `ALL_PROXY` / `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` all set. In both cases after 3 seconds:

- Zero TCP connections
- Process in `S+` state (sleeping, foreground)
- No output

**This is expected and normal behaviour for ACP mode.** The binary starts up and then waits on stdin for the SDK to send the first ACP message (the user prompt, formatted as `stream-json`). When invoked from a terminal without the SDK's pipe infrastructure, stdin is the terminal — no message ever arrives — so the process waits indefinitely. This is not a hang; it is the correct idle state.

Critically: **proxy vars made zero difference** to this behaviour. The process state, TCP connections, and timing were identical with and without `ALL_PROXY` set.

**Conclusion: proxy var hypothesis also disproved**

Both of the hypotheses proposed to explain the ACP hang without patches have now been eliminated:

| Hypothesis | Status | Reason eliminated |
|---|---|---|
| `ANTHROPIC_AUTH_TOKEN` missing → binary hangs on auth check before reading `settings.json` | ❌ Disproved | `claude -p 'say hi'` works from CLI with no `ANTHROPIC_AUTH_TOKEN` in env; binary must read `settings.json` first |
| Proxy vars (`ALL_PROXY` etc.) cause `node cli.js` to hang | ❌ Disproved | Behaviour of `node cli.js` in ACP mode is identical with and without proxy vars |

**What we actually know:**
- Without patches, the Zed agent panel never becomes interactive (4-min timeout, then Zed cancels)
- The `claude` subprocess starts and sits in normal ACP idle state (waiting on stdin)
- The ACP node process (79979) is also alive
- Zero TCP connections on either process

**Open question:** If neither the auth token timing nor the proxy vars are causing the hang, what is? The most likely remaining candidate is something in the **ACP initialization handshake** between the SDK (node 79979) and the `claude` subprocess (79980) — specifically whether the SDK successfully sends the init message and the binary responds. This requires instrumenting the actual pipe communication, which cannot be done with the binary's stderr redirected to `/dev/null`.

**What T7 showed:** `node cli.js` in ACP mode with proxy vars + `NO_PROXY` also showed zero TCP connections and sat in `S+` state — identical to the no-proxy-vars case. The test was inconclusive because it could not complete the ACP handshake from a terminal (stdin needs proper ACP protocol messages from the SDK). The proxy vars made no observable difference to startup behaviour.

**State of investigation:** Both hypotheses disproved. The Zed agent failure without patches remains unexplained. The cause is somewhere in the ACP initialisation handshake that is invisible without stderr from the subprocess.

**Next step:** Instrument the ACP stack to capture stderr from the `claude` subprocess. The subprocess's `fd 2` is currently `/dev/null` (set by the SDK spawn). Options:
1. Patch the SDK spawn call to redirect stderr to a file or pipe
2. Run the full ACP node process manually from a terminal with stderr wired to a file and trigger a prompt from Zed
3. Re-apply the original patches (which restore working state) and use the debug log in Patch 2 to observe the env at `createSession()` time, then isolate further from there

---

### 2026-03-22 — Direct pipe-protocol testing: purpose, method, and findings so far

#### Why this test series exists

The previous investigation left a single open question: *does the ACP pipe protocol actually work when `node cli.js` is the subprocess?* The native Bun binary was confirmed working (T1–T5), but all tests of `node cli.js` in ACP mode were inconclusive because the tests could not complete the protocol handshake from a shell — the binary just sat in idle `S+` state waiting for stdin.

The goal of the 2026-03-22 tests is to answer the question definitively: **can we drive `node cli.js` through the complete ACP stream-json protocol from Node.js, get a response, and confirm that the env/proxy configuration is correct?** Once we can do that standalone, we know the protocol works and can narrow the Zed failure to the patch/env layer.

Two test scripts were created:

- `research/test-acp-node.mjs` — earlier harness using `--print --verbose --input-format stream-json --output-format stream-json` (the native binary's flag set). **Used for T8a (native binary) only.** Not valid for `node cli.js` because `--print` is not the flag set the SDK uses.
- `research/test-acp-spawn.mjs` — revised harness that replicates the exact spawn the SDK's `sdk.mjs` `ProcessTransport.initialize()` uses. Run with `node research/test-acp-spawn.mjs [native|zed-node|hb-node] [--debug]`.

---

#### What source-code archaeology revealed about the actual spawn

Before running any tests we read the source of the two relevant SDK files:

- `@anthropic-ai/claude-agent-sdk/cli.js` — the 12 MB bundle that becomes the `claude` subprocess in non-static-binary mode
- `@anthropic-ai/claude-agent-sdk/sdk.mjs` — the programmatic SDK that `acp-agent.js` imports

Key findings from `sdk.mjs` `ProcessTransport.initialize()`:

**Actual CLI flags the SDK passes to the subprocess (NO `--print`):**
```
--output-format stream-json
--verbose
--input-format stream-json
--replay-user-messages        ← boolean flag; value "" from extraArgs is a silent-exit trap
--session-id <uuid>
[... plus any extraArgs, model, permission-mode flags ...]
```

The native binary's `--print --input-format stream-json` (which requires `--verbose`) is a completely different invocation path. The SDK programmatic API never passes `--print`.

**`pathToClaudeCodeExecutable` default:**
When not explicitly set (which is the case when `isStaticBinary()` is false and `CLAUDE_CODE_EXECUTABLE` is unset), `sdk.mjs`'s `query()` function defaults it to `<sdk-dir>/cli.js` — i.e., itself. So the subprocess is always `node cli.js`.

**`executable` default:**
`getDefaultExecutable()` returns `"bun"` if running under Bun, `"node"` otherwise. `acp-agent.js` overrides this with `process.execPath` (its own Node.js binary path), which in the live Zed process is Homebrew Node v25.1.0.

**stderr disposition:**
`spawnLocalProcess()` sets `stdio[2]` to `"ignore"` unless `DEBUG_CLAUDE_AGENT_SDK` or `options.stderr` is set. This is why stderr from the live `claude` subprocess has always been invisible — it goes to `/dev/null` by design.

**Confirmed live process binaries (from `lsof` on the running Zed processes):**
Both the acp-agent node process (pid 79979) and the claude subprocess (pid 79980) are running under `/opt/homebrew/Cellar/node/25.1.0/bin/node` — **Homebrew Node v25.1.0**, not Zed's bundled Node v22.5.1. This means `process.execPath` in `acp-agent.js` resolves to the Homebrew binary, and that is what spawns the subprocess.

**Correct test variant is therefore T8c (hb-node):** `hb-node cli.js` with the SDK flags, no `--print`.

---

#### T8a — Native binary via direct pipe protocol

**Flags:** `--print --verbose --session-id <uuid> --input-format stream-json --output-format stream-json --replay-user-messages`
**Runtime:** `/opt/homebrew/bin/claude` (native Bun binary, v2.1.79)

**Result: ✅ PASS**

The native binary completes the full round-trip. Key observations:
- The binary does **not** emit `system/init` before receiving a user message on stdin. The init message only appears *after* the first `user` message arrives. Any test that waits for init before sending a message will deadlock.
- The result message type is `{"type":"result","subtype":"success",...}` — a top-level `type` field, **not** `{"type":"system","subtype":"result",...}`.
- `apiKeySource: "none"` in the init message confirms the binary is routing through the local proxy (no direct API key present).
- stderr is empty; all env config is self-applied from `~/.claude/settings.json`.
- The native binary requires `--verbose` when combining `--print` with `--output-format=stream-json`. Without it: `Error: When using --print, --output-format=stream-json requires --verbose`.

---

#### T8b / T8c — `node cli.js` with native-binary flags: HANG

Using `--print --verbose` with `node cli.js` (either Zed Node v22 or HB Node v25) produced a **complete hang** — zero stdout, zero stderr, zero TCP connections, process in `S+` state. This was the original unexplained failure mode.

Once the correct SDK flags (no `--print`) were identified from source inspection, the symptom changed to a **silent immediate exit** (code 0, ~410 ms, no output). This was progress — the binary was at least running past startup.

---

#### Discovery: the `control_request/initialize` handshake

The SDK's `Query` class constructor immediately calls `this.initialization = this.initialize()`, which sends a `control_request` message to the subprocess stdin *before* any user message:

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

The subprocess must respond with a `control_response` before the SDK sends the first user message. Without this handshake, the subprocess exits cleanly (code 0) approximately 410 ms after startup, after completing its own init sequence, because it has no pending work — stdin has not indicated that a session is starting.

**Protocol order (correct full sequence):**
1. Spawn: `node cli.js --output-format stream-json --verbose --input-format stream-json --replay-user-messages --session-id <uuid>`
2. → stdin: `control_request/initialize`
3. ← stdout: `system/init`  +  `control_response` (success)
4. → stdin: `user` message
5. ← stdout: `user` replay (because `--replay-user-messages`), `assistant` message(s), `result`

**Protocol order we were (incorrectly) using before this discovery:**
1. Spawn with `--print` (wrong flags for `node cli.js`)
2. → stdin: `user` message (sent without prior handshake)
3. ← nothing (exits or hangs)

---

#### T8c with correct flags + control_request/initialize: still exits at 410 ms

After adding the `control_request/initialize` message, the subprocess still exits at ~410 ms with code 0, zero stdout. The debug log (`--debug-to-stderr`) shows:

```
[DEBUG] MDM settings load completed in 0ms
[DEBUG] settings.json at /Library/Application Support/ClaudeCode/managed-settings.json — broken symlink
[DEBUG] settings.json at /Users/ytl/.claude/settings.local.json — broken symlink
[DEBUG] CA certs: Config fallback — globalEnv keys: (empty), settingsEnv keys: ANTHROPIC_BASE_URL,ANTHROPIC_AUTH_TOKEN,ANTHROPIC_API_KEY,CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC
[DEBUG] [init] configureGlobalMTLS starting
[DEBUG] [init] configureGlobalMTLS complete
[DEBUG] [init] configureGlobalAgents starting
[DEBUG] CA certs: useSystemCA=false, extraCertsPath=undefined
[DEBUG] Git remote URL: null
[DEBUG] No git remote URL found
← process exits (code 0, ~32 ms after configureGlobalAgents starting)
```

**Observations:**
- `settingsEnv keys: ANTHROPIC_BASE_URL,...` — settings.json IS being loaded and env applied.
- `globalEnv keys: (empty)` — the env vars we set on the shell process are not visible as "globalEnv" in the binary's internal accounting. This is not an error; "globalEnv" refers to a different source in the binary's config hierarchy, not `process.env`.
- The process exits before producing any stdout. There is no network activity and no assistant response.
- The `control_request/initialize` message was written to stdin but produced no visible response on stdout.

**Hypothesis:** The subprocess may be reading and discarding the `control_request/initialize` message silently, then exiting because there is no further input within its startup window. Or the handshake message format is slightly wrong for this version of `cli.js` (v2.1.76 vs native binary v2.1.79).

---

#### Important: the `extraArgs: {"replay-user-messages": ""}` trap

`acp-agent.js` passes `extraArgs: {"replay-user-messages": ""}` to the SDK. The SDK iterates `extraArgs` and for non-null values does `h.push("--" + key, value)`, which produces `--replay-user-messages ""` (empty string as a separate argument).

When the CLI parser sees `--replay-user-messages ""`, the empty string `""` is consumed as the positional `[prompt]` argument. The binary then runs with an empty prompt and exits immediately (code 0, no output, ~410 ms). This is a **silent-exit trap** that was present in our earlier tests.

In `test-acp-spawn.mjs` this is now handled correctly: `--replay-user-messages` is passed without a following empty-string argument.

However, the subprocess still exits at 410 ms even without the empty string. So while this trap was eliminated, it was not the root cause.

---

#### Current state and next steps

**What is confirmed:**
- The correct subprocess invocation uses `--output-format stream-json --verbose --input-format stream-json --replay-user-messages --session-id <uuid>` (no `--print`).
- The correct runtime for the subprocess in the live Zed process is Homebrew Node v25.1.0 running `@anthropic-ai/claude-agent-sdk/cli.js`.
- The SDK sends a `control_request/initialize` message before any user message. The test harness now does this correctly.
- The native binary (T8a) completes the full protocol round-trip correctly via direct pipe from Node.js.
- The `node cli.js` subprocess (T8c) exits cleanly at ~410 ms with zero output even when the correct flags and `control_request/initialize` are used.

**What is unknown:**
- Why the `control_request/initialize` message does not prevent the subprocess from exiting. The subprocess may require the message to arrive before a startup deadline, or the message format may be subtly wrong for `cli.js` v2.1.76.
- Whether the subprocess version mismatch matters: `cli.js` reports v2.1.76 but the native binary is v2.1.79. The protocol may have changed.
- Whether the Zed ACP failure (without patches) is caused by this same 410 ms exit, or whether the live process (which does have the proper SDK `Query` class driving it) actually succeeds at the handshake but fails later.

**Immediate next steps:**
1. Verify the `control_request/initialize` message arrives before the subprocess exits. The 410 ms gap suggests the subprocess starts its shutdown before our 200 ms delay has elapsed. Try sending the init message at 50 ms or immediately on spawn.
2. Check whether the subprocess exits due to a parsing error on the `control_request` message or simply because stdin has no data yet when it reaches its startup decision point.
3. Compare `cli.js` v2.1.76 protocol handling with native v2.1.79 by inspecting the `control_request` parsing code in `cli.js`.
4. Cross-check: does the live Zed process (with patches, currently running) actually receive a `control_response` from its subprocess? This can be checked by patching the `write()` call in `sdk.mjs` to log to stderr.

**Test scripts to resume from:**
- `research/test-acp-spawn.mjs hb-node --debug` — the active test
- `research/test-acp-node.mjs native` — confirmed working baseline

---

### 2026-03-22 (continued) — The 4.4-second stall, `--print` mode anatomy, and the direct SDK approach

#### Why `node cli.js` exits immediately without `--print`

Source inspection of `OVz()` (the main CLI action handler in `cli.js`) confirmed:

```
if (!L6)   // L6 = O.print (--print flag)
    Promise.resolve().then(() => initLayout());
```

When `--print` is absent, `initLayout()` is called asynchronously. This initialises the TUI layout, detects that stdout is not a TTY, and exits with code 0. The exit fires at ~410 ms — after module loading and settings init but before anything reads stdin. This is why `--replay-user-messages`, `--input-format stream-json`, and the `control_request/initialize` message in the stdin buffer are all silently ignored.

**Conclusion:** `node cli.js` in the SDK programmatic flags (`--output-format stream-json --verbose --input-format stream-json`) without `--print` is fundamentally broken as a standalone invocation. The process exits via TUI init before reading any stdin.

With `--print` added, `initLayout()` is skipped, and the binary proceeds to the `for await` message loop over `process.stdin`. This is the mode that stays alive.

---

#### The 4.4-second stall with `--print`

With `--print` + the full flag set + `control_request/initialize` sent, the subprocess stays alive but produces zero stdout. Debug logging (`--debug-to-stderr`) shows:

```
[DEBUG] configureGlobalAgents starting
[DEBUG] CA certs: useSystemCA=false, extraCertsPath=undefined
[DEBUG] Git remote URL: null
[DEBUG] No git remote URL found
← 4.4-second gap (no debug output) →
[DEBUG] Getting matching hook commands for SessionEnd
[DEBUG] Found 0 hook matchers / Matched 0 unique hooks
```

`configureGlobalAgents complete` is **never logged**, which means the process exits during or immediately after `BK1()` returns. Confirmed: `BK1()` is synchronous (sets up axios http agents/proxy interceptors) and should return instantly.

The gap is not caused by:
- Network calls to the proxy (proxy responds instantly to all tested endpoints including empty API key)
- TCP connections (lsof shows zero TCP during the entire window)
- DNS resolution (no UDP connections either)

**The 5-second race pattern** — found in the stdin-close handler inside the print-mode session code:

```javascript
if (G.inflightPromise)
    await Promise.race([
        G.inflightPromise,
        new Promise(o6 => setTimeout(o6, 5000))   // ← 5-second timeout
    ]);
G.abortController?.abort();
await oF8();
o();
Z.done();   // ← closes the output queue → triggers SessionEnd
```

This fires when stdin closes (`D = true`). After at most 5 seconds it calls `Z.done()` which closes the output stream and triggers SessionEnd cleanup. The observed 4.4-second value is consistent with this: the `G.inflightPromise` (the FXz initialise call) resolves at ~4.4 s, which is earlier than the 5 s hard timeout.

**Why does stdin close?** In our FIFO tests, the FIFO writer (`sleep 20`) should keep stdin open. However, the `so6.read()` async generator reads from `process.stdin` using `for await (let q of process.stdin)`. On macOS, a named FIFO writer subshell can release the write end of the FIFO in subtle ways. If the write end closes before the 5-second timeout, the `for await` completes, `inputClosed = true` is set, and the stdin-close handler fires.

**What takes ~4.4 seconds inside FXz?** `FXz()` calls `await Tv6(G1())` (compute available output styles) and `await Ik8()` (load plugins). `Ik8()` calls `_z()` which scans configured plugin directories. On a machine with no plugins installed but with slow filesystem metadata (or a full home directory scan), this could take several seconds. This is the most likely cause of the ~4.4 s window but has not been confirmed with a timer.

---

#### `CLAUDE_CODE_ENVIRONMENT_KIND=bridge` — what it actually does

Setting `CLAUDE_CODE_ENVIRONMENT_KIND=bridge` calls `ku1("remote-control")` which sets an internal `sessionSource = "remote-control"` metadata field. It does NOT activate a different stdin-reading mode or a different protocol. The actual protocol switch happens through the combination of:

- `--input-format stream-json` → `wVz()` returns `process.stdin` directly
- `--output-format stream-json` → output is emitted as newline-delimited JSON
- `--replay-user-messages` → user messages are echoed back on stdout
- The `control_request/initialize` message → triggers `FXz()` which sends `control_response` and registers the session

---

#### The `extraArgs: {"replay-user-messages": ""}` trap (confirmed fixed)

`acp-agent.js` passes `extraArgs: {"replay-user-messages": ""}` to the SDK. The SDK iterates extraArgs and for any non-null value pushes `["--" + key, value]` — so `["--replay-user-messages", ""]` with an empty string as a separate argv element. The CLI parser sees the empty string as the positional `[prompt]` argument, runs with an empty prompt, and exits immediately (code 0, no output, ~410 ms). This was present in all early tests and has been fixed in `test-acp-spawn.mjs`.

---

#### Proposed next step: use `sdk.mjs query()` directly

All the manual protocol work above can be bypassed by calling the SDK's `query()` function directly from our test harness, exactly as `acp-agent.js` does. This would:

1. Let the SDK handle the `control_request/initialize` handshake, `FXz` timing, and stdin management
2. Test the actual code path that runs in production
3. Give us a clean pass/fail answer: does the SDK→subprocess round-trip work?

The test would look like:

```javascript
// test-acp-sdk-query.mjs
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const SDK_PATH = `${process.env.HOME}/Library/Application Support/Zed/node/cache/_npx/b17a338e32143bc4/node_modules/@anthropic-ai/claude-agent-sdk/sdk.mjs`;
const { query } = await import(SDK_PATH);

for await (const msg of query({
    prompt: "say PING",
    options: {
        pathToClaudeCodeExecutable: SDK_CLI,   // sdk/cli.js
        executable: "/opt/homebrew/bin/node",
        env: { ...process.env, ...settingsEnv, CLAUDE_CODE_ENVIRONMENT_KIND: "bridge" },
        maxTurns: 1,
    }
})) {
    console.log(msg);
}
```

If this works, the protocol is fine and the Zed failure is entirely in the patch/env layer. If this also hangs or errors, we have isolated the SDK→subprocess call as broken in the current environment.

**This is the recommended next test to run** before doing any further manual protocol analysis.

---

#### Summary of all confirmed facts as of 2026-03-22

| Fact | How confirmed |
|---|---|
| Native binary works end-to-end via pipe protocol from Node.js | T8a PASS |
| Both live Zed processes (79979 and 79980) run under Homebrew Node v25.1.0 | `lsof -p` |
| Correct subprocess runtime is `hb-node` (T8c), not `zed-node` (T8b) | `lsof` |
| SDK uses `--output-format stream-json --verbose --input-format stream-json` (no `--print`) | `sdk.mjs` source |
| `pathToClaudeCodeExecutable` defaults to `sdk-dir/cli.js` when not set | `sdk.mjs query()` source |
| `node cli.js` without `--print` exits at 410 ms via TUI `initLayout()` | `OVz()` source + debug |
| `node cli.js` with `--print` stays alive but stalls ~4.4 s then SessionEnd | Shell test + debug log |
| The ~4.4 s stall ends when the `Promise.race([inflightPromise, 5000ms])` resolves | Source inspection |
| Zero TCP connections during the stall | `lsof` polling at 200 ms intervals |
| Proxy responds instantly to all endpoints including empty API key | `curl` tests |
| `CLAUDE_CODE_ENVIRONMENT_KIND=bridge` only sets sessionSource metadata | `cli.js` source |
| `extraArgs {"replay-user-messages":""}` causes silent empty-prompt exit | Source + testing |
| `so6.read()` iterates `process.stdin` line-by-line for stream-json mode | `cli.js` source |
| `FXz()` sends `control_response/success` after setting up hooks/output styles | `cli.js` source |
| `settings.json` env block IS loaded by `cli.js` subprocess | Debug log confirms `settingsEnv keys` |

**Test scripts to resume from:**
- `research/test-acp-spawn.mjs hb-node --debug` — current manual protocol test
- `research/test-acp-node.mjs native` — confirmed working baseline
- `research/test-acp-sdk-query.mjs` — **to be created** — recommended next step

# Zed + Claude Agent ACP + LiteLLM Proxy

Running the Claude Code ACP agent (`claude-agent-acp`) in Zed's agent panel through a local LiteLLM proxy (`litellm-proxy.py`) requires several patches. The proxy exists for two distinct, separable reasons:

1. **Network access** — SLAC's LiteLLM is behind the SLAC network. The SOCKS5 tunnel solves that. Python's stdlib HTTP client can't speak SOCKS5 natively, so the proxy bridges that gap.
2. **Protocol friction** — Claude Code speaks a slightly different dialect of the Anthropic API than SLAC's older LiteLLM deployment expects: header names differ, newer request body fields cause nginx 400s, model version strings use a different separator, and prompt-caching annotations are not understood.

These two concerns are tangled together in the proxy right now but are fundamentally separable — which matters when thinking about what to change or replace (see [Background & Context](#background--context)).

Verify everything is working end-to-end with:

```sh
python3 ~/.claude/litellm-proxy-test.py   # expects: PASS 25  FAIL 0  WARN 0
```

---

## Architecture

```
~/.config/zed/settings.json
  ├─ "proxy": disabled                   ← was SOCKS5; routing local proxy through SOCKS hangs
  ├─ "agent.default_model.provider":     ← must be "claude-acp", not "copilot_chat"
  │     "claude-acp"
  │
Zed Agent Panel
  └─ npx @zed-industries/claude-agent-acp     (node process)
       │   ↑ index.js entrypoint patch: sets env from settings.json, deletes HTTP_PROXY
       │
       ├─ acp-agent.js createSession()
       │     ↑ [DEBUG-ENV] log: shows final env state before spawning claude
       │     env: {
       │       ...process.env,                      ← patched ✓
       │       ...userProvidedOptions?.env,
       │       ...createEnvForGateway(gatewayMeta),  ← may override ANTHROPIC_BASE_URL
       │       ANTHROPIC_BASE_URL: process.env...,   ← patch forces win ✓
       │       ANTHROPIC_API_KEY: process.env...,    ← patch forces win ✓
       │       ANTHROPIC_AUTH_TOKEN: process.env..., ← patch forces win ✓
       │     }
       │
       └─ @anthropic-ai/claude-agent-sdk
            └─ query() → spawns `claude` binary (native Mach-O arm64)
                 │   env: { ...constructed env above }
                 └─ POST http://127.0.0.1:19999/v1/messages
                      └─ litellm-proxy.py
                           ├─ strips/rewrites non-standard body fields
                           ├─ normalises auth headers (single Authorization: Bearer)
                           ├─ rewrites model names (hyphens → dots)
                           └─ SOCKS5 127.0.0.1:9051 (ssh tunnel)
                                └─ https://sdf-llm.slac.stanford.edu (LiteLLM)
```

---

## Root Causes & Fixes

### 1. Shell `HTTP_PROXY` Routing the Local Proxy Through SOCKS

The shell sets `HTTP_PROXY=socks5://127.0.0.1:9051` (SSH SOCKS tunnel to SLAC). Zed's GUI launcher inherits this, so the `claude` child process routes its connection to `http://127.0.0.1:19999` (the local proxy) through the SOCKS tunnel — where `127.0.0.1:19999` doesn't exist. The connection hangs silently.

**Fix:** The `index.js` entrypoint patch reads `delete_env` from `~/.claude/settings.json` and calls `delete process.env[k]` for each proxy-related var. Setting them to `""` is insufficient — some HTTP clients treat an empty string as "use empty proxy URL" rather than "no proxy". Full deletion is required.

---

### 2. Zed's Application-Level `"proxy"` Setting

Separate from the `HTTP_PROXY` env var, Zed has its own `"proxy"` setting in `~/.config/zed/settings.json` that it applies to all connections it manages. This caused the same problem as root cause 1: `127.0.0.1:19999` was being tunneled through SOCKS to SLAC, where nothing listens on that port. Deleting `HTTP_PROXY` from the env has no effect on this setting.

**Fix:** Comment out `"proxy"` in `~/.config/zed/settings.json`:

```json
// "proxy": "socks5://127.0.0.1:9051"  // DISABLED — routes local proxy through SOCKS
```

**Caveat:** This disables Zed's SOCKS proxy for all of its own HTTP connections (telemetry, extension registry, etc.). SSH remote connections configured in `ssh_connections` still work because they use SSH's own transport. If other Zed features break, see [Caveats](#caveats).

---

### 3. Wrong `default_model` Provider

`agent.default_model` in `~/.config/zed/settings.json` had `"provider": "copilot_chat"`. This is Zed's built-in GitHub Copilot Chat integration — a direct language-model provider, not an agent server. It does not appear in the agent panel's model picker (which only lists agent servers like `claude-acp`), but when persisted as `default_model` it silently routes all agent panel requests to Copilot's backend (`api.business.githubcopilot.com`).

The picker selection and the persisted `default_model` value can diverge — the picker may look correct while the file still contains the wrong provider. Always check the file directly.

**Fix:** Edit `~/.config/zed/settings.json` directly — see the [Configuration](#configuration) section for the correct block.


Also remove `"enable_thinking": true` and `"effort": "high"` from `default_model` — these cause the `claude` binary to emit unsupported request fields (see [Root Cause 5](#5-non-standard-request-body-fields--nginx-400)).

---

### 4. `createEnvForGateway()` Overriding `ANTHROPIC_BASE_URL`

In `acp-agent.js`, the env passed to `query()` is:

```js
env: {
    ...process.env,
    ...userProvidedOptions?.env,
    ...createEnvForGateway(this.gatewayAuthMeta),  // may clobber ANTHROPIC_BASE_URL!
}
```

If Zed uses gateway authentication, `createEnvForGateway()` returns `{ ANTHROPIC_BASE_URL: <gatewayUrl>, ... }`, silently overwriting the patched value that points to the local proxy. The `claude` binary then sends requests directly to Anthropic's gateway rather than through the local proxy.

**Fix:** Patch `acp-agent.js` to re-assert `process.env` values after the gateway spread:

```js
env: {
    ...process.env,
    ...userProvidedOptions?.env,
    ...createEnvForGateway(this.gatewayAuthMeta),
    // LITELLM_PROXY_PATCH: force patched values to win over gateway overrides
    ...(process.env.ANTHROPIC_BASE_URL ? { ANTHROPIC_BASE_URL: process.env.ANTHROPIC_BASE_URL } : {}),
    ...(process.env.ANTHROPIC_API_KEY ? { ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY } : {}),
    ...(process.env.ANTHROPIC_AUTH_TOKEN !== undefined ? { ANTHROPIC_AUTH_TOKEN: process.env.ANTHROPIC_AUTH_TOKEN } : {}),
},
```

A debug log line is also injected just before the options block to make the final env state visible in the Zed log:

```js
// LITELLM_PROXY_PATCH: debug env state
process.stderr.write("[DEBUG-ENV] ANTHROPIC_BASE_URL=" +
    JSON.stringify(process.env.ANTHROPIC_BASE_URL) +
    " HTTP_PROXY=" + JSON.stringify(process.env.HTTP_PROXY) +
    " gatewayAuthMeta=" + JSON.stringify(!!this.gatewayAuthMeta) + "\n");
```

---

### 5. Non-standard Request Body Fields → nginx 400

The `claude` binary (v2.1.79) sends several fields that SLAC's LiteLLM deployment does not recognise. nginx validates the upstream request body and returns a plain HTML `400 Bad Request` (no JSON error body) before LiteLLM ever sees it:

| Field | Triggered by | Problem |
|-------|-------------|---------|
| `thinking: {type: "adaptive"}` | `enable_thinking: true` in Zed settings | Non-standard format; valid is `{type: "enabled", budget_tokens: N}` |
| `context_management` | `effort` in Zed settings | New SDK extension; LiteLLM has no concept of it |
| `output_config` | `effort` in Zed settings | New SDK extension for effort-level routing |

**Fix (two-pronged):** Remove `enable_thinking` and `effort` from `default_model` in Zed settings so the binary stops generating these fields. The proxy also strips them as a backstop, along with several `anthropic-beta` header flags that trigger the same rejection.

---

### 6. Background Calls to `api.anthropic.com` Hanging

The `claude` binary makes background startup calls to `api.anthropic.com` even in ACP/headless mode: telemetry, fast-mode status (`/api/claude_code_penguin_mode`), plugin security manifest, OAuth client data, quota check, etc. Because `ANTHROPIC_API_KEY` is set to the LiteLLM token (which Anthropic's servers don't recognise), these calls complete the TLS handshake but then hang waiting for a response. This blocks the subprocess long enough to trigger the ACP SDK's "Query closed before response received" timeout — with no embedded error detail, since the subprocess itself never reported a specific failure.

**Fix:** Set `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` in `~/.claude/settings.json`. The entrypoint patch injects it into the `claude` binary's env, suppressing most background calls. If hangs persist, adding `127.0.0.1 api.anthropic.com` to `/etc/hosts` forces immediate connection refusal instead of hanging (nothing listens on port 443 locally).

Note: running `claude --print` directly from the terminal still hangs even with this flag set, because `--print` mode runs the full interactive startup sequence which makes more background calls than ACP headless mode. Use `curl` to test the proxy directly instead (see [Debugging](#debugging)).

---

### 7. Prompt-Caching `cache_control` Blocks → nginx 400

The `claude` binary sends the `system` field as an array of content blocks (Anthropic prompt-caching format, API ≥ 2024-06-01) and annotates blocks with `cache_control: {"type": "ephemeral"}`. SLAC's LiteLLM/nginx does not understand the `cache_control` field and returns a plain 400. The proxy was already stripping the `anthropic-beta: prompt-caching-*` header, but leaving the body annotations in place — they were orphaned noise that the upstream rejected.

**Fix:** `litellm-proxy.py` calls `_strip_cache_control_from_blocks()` from `maybe_rewrite_body` for both the top-level `system` array and every `messages` content array.

---

### 8. Duplicate `Authorization` Headers → nginx 400

The Anthropic TypeScript SDK (used internally by the `claude` binary) sends an `authorization: Bearer <token>` header directly (OAuth-style). The proxy was only stripping `x-api-key` from incoming requests — it passed the `authorization` header through unchanged, then also injected its own `Authorization: Bearer <api_key>`. nginx receives both headers and treats it as a malformed request, returning 400 before LiteLLM sees anything.

This wasn't caught by the test suite because `litellm-proxy-test.py` uses `x-api-key` (the original Anthropic native style). The real `claude` binary uses Bearer auth directly.

**Fix:** Added `authorization` to the stripped-header set in `_proxy()`. The proxy strips any incoming auth header (regardless of case) and emits a single canonical `Authorization: Bearer <api_key>` using the key from `~/.claude/settings.json`.

---

### 9. Model Name Mismatch

Claude Code sends model names with hyphens (`claude-sonnet-4-6`); SLAC's LiteLLM expects dots (`claude-sonnet-4.6`). LiteLLM rejects with 400, which the SDK surfaces as a generic "Query closed before response received" error.

**Fix:** `litellm-proxy.py` rewrites model names in `maybe_rewrite_body`:

| Received | Forwarded |
|----------|-----------|
| `claude-sonnet-4-6` | `claude-sonnet-4.6` |
| `claude-opus-4-6` | `claude-opus-4.6` |
| `claude-sonnet-4-5` | `claude-sonnet-4.5` |
| `claude-haiku-4-5` | `claude-haiku-4.5` |

---

### 10. Empty API Key

Zed launches `claude-agent-acp` as a GUI app without inheriting shell env vars, so `ANTHROPIC_API_KEY` is absent. The proxy would forward an empty key and LiteLLM would reject with 401. The `claude` binary also prompts for interactive login if no auth token is present, which hangs the headless process.

**Fix:** `ANTHROPIC_AUTH_TOKEN=""` in `~/.claude/settings.json` bypasses the interactive login check. `ANTHROPIC_API_KEY` is injected via the entrypoint patch. The proxy also falls back to the key loaded from `settings.json` at startup if a client sends an empty or missing key.

---

## Configuration

### `~/.claude/settings.json`

Read by the entrypoint patch at startup; also used by `litellm-proxy.py` as a fallback API key source.

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:19999",
    "ANTHROPIC_AUTH_TOKEN": "",
    "ANTHROPIC_API_KEY": "<your-litellm-api-key>",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  },
  "delete_env": [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "npm_config_proxy",
    "npm_config_https_proxy",
    "ALL_PROXY",
    "all_proxy"
  ]
}
```

- `ANTHROPIC_AUTH_TOKEN: ""` — intentional empty string; do not fill this in. It bypasses the CLI interactive login flow that would otherwise hang the headless process. See [Root Cause 10](#10-empty-api-key) and the [`ANTHROPIC_AUTH_TOKEN=""` vs `ANTHROPIC_API_KEY`](#anthropic_auth_token-vs-anthropic_api_key) caveat.
- `ANTHROPIC_API_KEY` — sent by the `claude` binary to the proxy; also used by the proxy as a fallback when clients send empty keys
- `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1"` — suppresses background `api.anthropic.com` calls that hang due to the LiteLLM token being unrecognised by Anthropic
- `delete_env` — vars to fully remove from `process.env` (not just blank out)

---

### `~/.config/zed/settings.json`

```json
// "proxy": "socks5://127.0.0.1:9051"   ← DISABLED; routes local proxy through SOCKS

"agent": {
  "default_model": {
    "provider": "claude-acp",
    "model": "claude-sonnet-4.6"
    // enable_thinking and effort MUST NOT be present — they generate unsupported body fields
  },
  "favorite_models": []
}
```


---

### `litellm-proxy.py` Request Sanitisation

`_proxy()` calls `maybe_rewrite_body(body)` and `maybe_rewrite_headers(hdrs)` before forwarding upstream. Together they:

- Rewrite model names: hyphens → dots
- Strip `context_management` and `output_config` (unsupported SDK extensions)
- Remove `thinking: {type: "adaptive"}` (non-standard; safe to drop — equivalent to no thinking)
- Add `budget_tokens: 16000` if `thinking: {type: "enabled"}` is missing it
- Strip `cache_control` from every block in `system` and `messages` content arrays
- Strip `anthropic-beta` flags: `context-management-2025-06-27`, `prompt-caching-scope-2026-01-05`, `effort-2025-11-24`
- Strip `anthropic-dangerous-direct-browser-access` header (browser CORS bypass; irrelevant for LiteLLM, may trigger WAF rules)

Auth header normalisation in `_proxy()`:

- Strips any incoming `authorization` header from the client (regardless of case)
- Adds a single canonical `Authorization: Bearer <api_key>` header
- Strips `x-api-key` (replaced by `Authorization: Bearer`)

---

## Entrypoint Patches

Both patches are **overwritten whenever Zed updates `claude-agent-acp`**. Re-apply after any Zed update that touches the agent package.

Signs the patches have been overwritten:
- `[PATCH]` stops appearing in `~/Library/Logs/Zed/Zed.log`
- `[DEBUG-ENV]` stops appearing in logs
- Agent starts failing again

Check for new `_npx` hash directories:
```sh
ls -d ~/Library/Application\ Support/Zed/node/cache/_npx/*/node_modules/@zed-industries/claude-agent-acp/ 2>/dev/null
```

Run the `ls` command above to find the current hash(es) after any Zed update.

---

### `index.js` Entrypoint Patch

Inserts env injection immediately after the shebang line in:
```
~/Library/Application Support/Zed/node/cache/_npx/<hash>/node_modules/@zed-industries/claude-agent-acp/dist/index.js
```

```sh
python3 << 'PYEOF'
import os, glob, re

pattern = os.path.expanduser(
    "~/Library/Application Support/Zed/node/cache/_npx/*/node_modules/@zed-industries/claude-agent-acp/dist/index.js"
)
for entrypoint in glob.glob(pattern):
    with open(entrypoint, "r") as f:
        content = f.read()

    # Remove old patch if present
    content = re.sub(
        r'// --- LITELLM_PROXY_PATCH ---.*?// --- END LITELLM_PROXY_PATCH ---\n',
        '', content, flags=re.DOTALL
    )

    lines = content.split("\n")
    inject = '''// --- LITELLM_PROXY_PATCH ---
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
try {
    const s = JSON.parse(readFileSync(join(homedir(), ".claude", "settings.json"), "utf8"));
    if (s.env) { for (const [k, v] of Object.entries(s.env)) { process.env[k] = v; } }
    if (s.delete_env) { for (const k of s.delete_env) { delete process.env[k]; } }
    process.stderr.write("[PATCH] env applied: ANTHROPIC_BASE_URL=" + (process.env.ANTHROPIC_BASE_URL || "") + " HTTP_PROXY=" + (process.env.HTTP_PROXY || "(deleted)") + "\\n");
} catch(e) { process.stderr.write("[PATCH] error: " + e.message + "\\n"); }
// --- END LITELLM_PROXY_PATCH ---'''

    lines.insert(1, inject)

    with open(entrypoint, "w") as f:
        f.write("\n".join(lines))
    print(f"Patched: {entrypoint}")
PYEOF
```

---

### `acp-agent.js` Patch

Patches the env construction in:
```
~/Library/Application Support/Zed/node/cache/_npx/<hash>/node_modules/@zed-industries/claude-agent-acp/dist/acp-agent.js
```

Two insertions: a `[DEBUG-ENV]` log line before `const options = {`, and env override lines after `createEnvForGateway()`.

```sh
python3 << 'PYEOF'
import os, glob, re, shutil

pattern = os.path.expanduser(
    "~/Library/Application Support/Zed/node/cache/_npx/*/node_modules/@zed-industries/claude-agent-acp/dist/acp-agent.js"
)

debug_line = '        // LITELLM_PROXY_PATCH: debug env state\n        process.stderr.write("[DEBUG-ENV] ANTHROPIC_BASE_URL=" + JSON.stringify(process.env.ANTHROPIC_BASE_URL) + " HTTP_PROXY=" + JSON.stringify(process.env.HTTP_PROXY) + " gatewayAuthMeta=" + JSON.stringify(!!this.gatewayAuthMeta) + "\\n");\n'

env_override = '                // LITELLM_PROXY_PATCH: force patched values to win over gateway overrides\n                ...(process.env.ANTHROPIC_BASE_URL ? { ANTHROPIC_BASE_URL: process.env.ANTHROPIC_BASE_URL } : {}),\n                ...(process.env.ANTHROPIC_API_KEY ? { ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY } : {}),\n                ...(process.env.ANTHROPIC_AUTH_TOKEN !== undefined ? { ANTHROPIC_AUTH_TOKEN: process.env.ANTHROPIC_AUTH_TOKEN } : {}),\n'

for path in glob.glob(pattern):
    with open(path, "r") as f:
        content = f.read()

    # Remove old patches if present
    if "LITELLM_PROXY_PATCH" in content:
        content = re.sub(r' *// LITELLM_PROXY_PATCH:.*\n(?: *process\.stderr\.write.*\n)?', '', content)
        content = re.sub(r' *// LITELLM_PROXY_PATCH:.*\n(?: *\.\.\.\(process\.env\.ANTHROPIC_.*\n)*', '', content)

    # 1. Add debug line before "const options = {"
    content = re.sub(
        r'(        const options = \{)',
        debug_line + r'\1',
        content,
        count=1
    )

    # 2. Add env override after "...createEnvForGateway(this.gatewayAuthMeta),"
    content = re.sub(
        r'(                \.\.\.createEnvForGateway\(this\.gatewayAuthMeta\),)\n',
        r'\1\n' + env_override,
        content,
        count=1
    )

    bak = path + ".bak"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)

    with open(path, "w") as f:
        f.write(content)
    print(f"Patched: {path}")
PYEOF
```

Then restart Zed.

---

## Verification

```sh
python3 ~/.claude/litellm-proxy-test.py
```

25 checks across 8 categories:

| Category | What it checks |
|----------|----------------|
| Infrastructure | SOCKS tunnel reachable, proxy process running, proxy port listening |
| JS Patches | `index.js` and `acp-agent.js` patched in all `_npx` dirs |
| Proxy: basics | POST /v1/messages → 200, `?beta=true` stripped, model rewrite |
| Proxy: stripping | `context_management`, `output_config`, `thinking`, beta headers |
| Proxy: auth | Empty `x-api-key` falls back to `settings.json` key |
| Proxy: streaming | `stream=true` returns SSE `data:` lines |
| Proxy: real-world | Full combined payload (all bad fields + `?beta=true`) → 200 |
| Zed log | `[PATCH]` and `[DEBUG-ENV]` present and correct, no routing errors |

Expected: `PASS 25   FAIL 0   WARN 0`

### If a check fails

| Failing category | Likely cause | See |
|---|---|---|
| Infrastructure | SOCKS tunnel down, or proxy not running / not listening | [Check the SOCKS tunnel](#check-the-socks-tunnel), [Check proxy logs](#check-proxy-logs) |
| JS Patches | Zed updated `claude-agent-acp` and overwrote the patches | [Entrypoint Patches](#entrypoint-patches) |
| Proxy: basics / stripping / auth | Proxy logic or `settings.json` misconfigured | [litellm-proxy.py Request Sanitisation](#litellm-proxypy-request-sanitisation) |
| Proxy: streaming | SOCKS tunnel dropping mid-request | [Check the SOCKS tunnel](#check-the-socks-tunnel) |
| Proxy: real-world | A new unsupported field appeared in Claude Code requests | [Root Cause 5](#5-non-standard-request-body-fields--nginx-400) |
| Zed log | Patch not applied or wrong `default_model` provider | [Entrypoint Patches](#entrypoint-patches), [Root Cause 3](#3-wrong-default_model-provider) |

---

## Debugging

### Confirm patches are loaded

```sh
grep -E 'PATCH|DEBUG-ENV' ~/Library/Logs/Zed/Zed.log | tail -10
```

Expected:
```
[PATCH] env applied: ANTHROPIC_BASE_URL=http://127.0.0.1:19999 HTTP_PROXY=(deleted)
[DEBUG-ENV] ANTHROPIC_BASE_URL="http://127.0.0.1:19999" HTTP_PROXY=undefined gatewayAuthMeta=false
```

If `gatewayAuthMeta=true`, Zed is using gateway auth — the `acp-agent.js` patch should force our values to win, but if `ANTHROPIC_BASE_URL` in the debug line still shows the wrong URL, the patch didn't apply.

### Check Zed agent errors

```sh
grep -iE 'Query closed|acp_thread|Unable to connect|auth.*required|Internal error|githubcopilot|closed unexpectedly' \
  ~/Library/Logs/Zed/Zed.log | tail -20
```

| Error | Likely cause |
|-------|-------------|
| `githubcopilot` URLs | `default_model.provider` is still `copilot_chat` — fix `agent.default_model` in `~/.config/zed/settings.json` |
| `Unable to connect to API` | Proxy returned non-2xx; check proxy log for `UPSTREAM 4xx RESPONSE BODY` |
| `No language model configured` | Same as above — wrong provider in settings |
| `Query closed before response received` (no detail) | Background `api.anthropic.com` calls hanging — check `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` is set |
| `Query closed` + `socks connect error` | SOCKS tunnel dropped mid-request — restart tunnel |

For `UPSTREAM 400` errors, inspect the dumped request body:
```sh
ls -t /tmp/proxy_debug_request_*.json | head -1 | xargs python3 -c "
import json, sys
body = json.load(open(sys.argv[1]))
print('fields:', list(body.keys()))
sys_field = body.get('system', [])
if isinstance(sys_field, list):
    for i, blk in enumerate(sys_field):
        print(f'system[{i}]:', list(blk.keys()))
"
```

### Check proxy logs

```sh
# Foreground (recommended for debugging):
python3 ~/.claude/litellm-proxy.py

# Background:
nohup python3 ~/.claude/litellm-proxy.py > /tmp/litellm-proxy.log 2>&1 &
tail -f /tmp/litellm-proxy.log
```

A successful request looks like:
```
[proxy] POST /v1/messages (len=... stream=True)
[proxy] model rewrite: claude-sonnet-4-6 -> claude-sonnet-4.6
[proxy] stripped cache_control from system block(s)
[proxy] -> upstream POST /v1/messages
[proxy] <- upstream 200 text/event-stream (stream=True)
[proxy] streamed N bytes for /v1/messages
```

If stripping lines appear (`stripped unsupported body field`, `stripped cache_control`, etc.), the proxy is catching fields the Zed settings fix should have prevented — requests will still succeed, but check that `enable_thinking` and `effort` are absent from `default_model`.

### Check process network connections

While a prompt is pending in Zed:

```sh
ps aux | grep -E 'claude-agent|claude' | grep -v grep
# For each claude PID:
lsof -i -n -P -p <PID> | grep TCP
```

The `claude` child process should have a TCP connection to `127.0.0.1:19999`. If it has zero connections, or a connection to `127.0.0.1:9051`, either the Zed proxy setting is still active or a gateway override is in effect.

### Test the proxy directly

```sh
curl -s --max-time 30 -X POST http://127.0.0.1:19999/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: " \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-sonnet-4-6","max_tokens":10,"messages":[{"role":"user","content":"say hi"}]}'
```

Expected: a JSON response with `"type":"message"` and content.

### Test the `claude` binary directly

```sh
ANTHROPIC_BASE_URL=http://127.0.0.1:19999 \
ANTHROPIC_API_KEY="<your-key>" \
ANTHROPIC_AUTH_TOKEN="" \
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
claude -p "say hi" --output-format text
```

If this works but Zed doesn't, the problem is in how Zed launches or configures the agent, not in the proxy or binary itself.

> **Note:** `claude --print` (and `claude -p`) hang even with `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` set, because `--print` mode runs the full interactive startup sequence which makes more background calls than ACP headless mode. Use `curl` to test the proxy directly (see [Test the proxy directly](#test-the-proxy-directly)) — don't use the binary to validate the proxy. See [Root Cause 6](#6-background-calls-to-apianthropic-com-hanging) for details.

### Check the SOCKS tunnel

```sh
nc -z 127.0.0.1 9051 && echo "SOCKS UP" || echo "SOCKS DOWN"
grep "socks connect error" ~/Library/Logs/Zed/Zed.log | tail -5
```

If down, restart:
```sh
ssh localhost -N -D9051 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 &
```

For automatic reconnection:
```sh
brew install autossh
autossh -M 0 -N -D9051 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 localhost
```

---

## Caveats

### Disabling Zed's proxy setting

Commenting out `"proxy"` means Zed no longer routes its own HTTP connections through the SOCKS tunnel. SSH remote sessions (`ssh_connections`) still work — they use SSH's own transport. Zed's own services (telemetry, extension registry, GitHub Copilot) will connect directly; if your network requires SOCKS for general internet access, these may break. Zed doesn't support per-feature proxy settings, so there's no more targeted option currently.

### Patches are fragile

Both `index.js` and `acp-agent.js` are overwritten whenever Zed updates the `claude-agent-acp` package. When that happens, re-run the patch scripts in [Entrypoint Patches](#entrypoint-patches) and restart Zed.

### `ANTHROPIC_AUTH_TOKEN=""` vs `ANTHROPIC_API_KEY`

- `ANTHROPIC_AUTH_TOKEN=""` skips the interactive login flow. Without it, the binary prompts for auth and hangs in headless mode.
- `ANTHROPIC_API_KEY` is the actual LiteLLM token. The proxy normalises it from whatever auth header format the client uses into a single `Authorization: Bearer`.
- If env injection fails and the binary sends an empty key, the proxy falls back to the key loaded from `~/.claude/settings.json` at startup.

### SOCKS tunnel reliability

The SSH tunnel can drop without warning. In-flight requests fail with `socks connect error: unexpected end of file` embedded in the "Query closed" detail. This is distinct from the background-call hang failure mode (which has no embedded detail). Use `autossh` for automatic reconnection.

---

## Background & Context

### LiteLLM Integration Modes

LiteLLM has three distinct ways of handling Anthropic-format traffic — they're easy to confuse:

**Mode 1: `/v1/messages` — Translation endpoint**

LiteLLM exposes its own `/v1/messages` that accepts Anthropic-format requests and routes them to any backend (Bedrock, Vertex AI, OpenAI, real Anthropic, etc.), translating to/from that provider's native format. This is what SLAC's deployment exposes and what we're hitting.

Officially supported features include full Anthropic messages format (streaming SSE, tool use, thinking), cost tracking, virtual keys, guardrails, and `drop_params: True` to silently discard unknown fields. Known active bugs as of early 2026:

| Issue | Description |
|-------|-------------|
| [#23981](https://github.com/BerriAI/litellm/issues/23981) / [#23150](https://github.com/BerriAI/litellm/issues/23150) | Cost calculated but **never written** to SpendLogs for `/v1/messages` traffic — budget enforcement silently bypassed for all Claude Code / Cursor / Windsurf clients |
| [#23841](https://github.com/BerriAI/litellm/issues/23841) | Newer Claude Code sends `{"type": "input_text"}` content blocks; LiteLLM only handles `{"type": "text"}`, so these are silently dropped, causing empty-input 422s from downstream providers |
| [#16716](https://github.com/BerriAI/litellm/issues/16716) | Synchronous Anthropic token-counting call blocks the async event loop, causing cascading health-check timeouts (may be fixed in mainline but present in older deployments) |

**Mode 2: `/anthropic/v1/messages` — Pure pass-through**

LiteLLM proxies requests straight to `api.anthropic.com`, substituting your LiteLLM virtual key for a real Anthropic key. No translation — a thin authenticated forwarding layer. This doesn't apply to our use case: SLAC's LiteLLM serves its own models from SLAC compute rather than forwarding to Anthropic.

**Mode 3: Anthropic → OpenAI Chat Completions translation (experimental)**

A newer feature that translates Anthropic-format requests to OpenAI Chat Completions format before forwarding. Not relevant here and actively buggy as of early 2026.

---

### The Simple Case vs Our Constraints

When there's no network complexity and LiteLLM is reasonably up to date, the entire Claude Code integration is just two env vars:

```sh
export ANTHROPIC_BASE_URL=http://my-litellm-server:4000
export ANTHROPIC_API_KEY=sk-my-litellm-key
```

Modern LiteLLM accepts `x-api-key` and `Authorization: Bearer` interchangeably, and `drop_params: True` in the server config makes it forward-compatible with new Claude Code body fields. Claude Code just works.

The SLAC setup has constraints that this path doesn't handle:

| Constraint | Why it requires the proxy |
|---|---|
| SLAC network not publicly reachable | Requires SOCKS5 tunnel; Python stdlib has no native SOCKS5 client |
| SLAC LiteLLM is an older version | Missing `drop_params: True`; strict nginx rejects unknown body fields and `anthropic-beta` headers |
| Only `Authorization: Bearer` accepted | Older LiteLLM doesn't accept `x-api-key` |
| Model names use `.` separators | Claude Code sends `claude-sonnet-4-6`; SLAC expects `claude-sonnet-4.6` |
| Prompt-caching annotations cause 400 | Older LiteLLM + nginx rejects `cache_control` in content blocks |

None of these reflect wrong decisions — they reflect the SLAC deployment predating Claude Code as a major use case and before LiteLLM hardened this path. An upgrade of the SLAC LiteLLM instance would eliminate most of the body/header sanitisation work.

---

### Proxy Scope: Permanent vs Temporary Jobs

It's useful to distinguish what the proxy must always do from what it's doing only to compensate for version lag:

**Permanent (won't go away without an architecture change):**

- **SOCKS5 tunneling** — As long as SLAC is behind a firewall and we're not on VPN, something has to speak SOCKS5.
- **SSE streaming relay** — Lightweight chunked pass-through; the right approach regardless.

**Likely temporary (a SLAC LiteLLM upgrade would fix):**

- Stripping `anthropic-beta` header flags — A newer nginx/LiteLLM config handles these.
- Stripping `cache_control` from content blocks — Newer LiteLLM + `drop_params: True` handles it.
- Stripping `context_management`, `output_config`, `thinking: {type: adaptive}` — Same; fields from recent Claude Code versions that older LiteLLM rejects.
- Model name rewriting — Could be fixed in SLAC's `config.yaml` model aliases.
- Auth header conversion (`x-api-key` → `Authorization: Bearer`) — Modern LiteLLM accepts both; this could go away.
- Stripping `?beta=true` query params — nginx-specific rejection.

---

### The Official Right Way (When You Have a Modern LiteLLM)

With a current LiteLLM deployment, the setup LiteLLM recommends for Claude Code is:

**Server-side** (`config.yaml`):
```yaml
model_list:
  - model_name: claude-sonnet-4-5
    litellm_params:
      model: anthropic/claude-sonnet-4-5-20250929
      api_key: os.environ/ANTHROPIC_API_KEY

litellm_settings:
  drop_params: True   # silently drop unknown fields; forward-compatible with new Claude Code versions
```

**Client-side:**
```sh
export ANTHROPIC_BASE_URL=http://your-litellm-server:4000
export ANTHROPIC_API_KEY=sk-your-virtual-key
```

The `drop_params: True` flag is the single biggest difference between a deployment that requires a sanitisation proxy and one that doesn't.

---

### Alternative Approaches Considered

**Direct SOCKS5 via env var**

Python's `requests` and some tools respect `ALL_PROXY=socks5://...`, but `httpx` (which the Anthropic SDK uses) has inconsistent SOCKS5 support and the `anthropic` SDK doesn't expose proxy configuration cleanly. Setting `HTTP_PROXY` or `HTTPS_PROXY` with a SOCKS5 URL is also what poisoned the Zed integration in the first place (Root Cause 1). The local proxy intercepts at the HTTP level before the SDK is involved, which is more reliable.

**LiteLLM's `/anthropic/` pass-through endpoint**

Setting `ANTHROPIC_BASE_URL=http://litellm:4000/anthropic` makes LiteLLM forward to real Anthropic with a virtual key substituted. This only makes sense when LiteLLM is a credentialled gateway to Anthropic's infrastructure — not when it's serving SLAC's own models.

**SSH + WireGuard or direct VPN**

A proper VPN to the SLAC network would eliminate the SOCKS5 requirement entirely and let the Anthropic SDK connect directly to `sdf-llm.slac.stanford.edu`. The cleanest long-term architecture, but requires infra changes on the SLAC side.

**mitmproxy or Caddy as the local proxy**

These handle SOCKS5 upstream forwarding and header rewriting with far less code, and include native connection pooling. The trade-off is a non-stdlib dependency and less control over exact behaviour (e.g. the model name rewriting regex). The custom Python script is a better fit here because the rewriting logic is non-trivial and zero install dependencies matter in HPC environments.

---

### Future State

The proxy is the right approach for the current constraints. The ideal end states, in rough order of likelihood:

1. **SLAC upgrades LiteLLM to a recent version with `drop_params: True`** — eliminates most body/header sanitisation. The proxy shrinks to SOCKS5 tunnel + auth header swap (or disappears entirely if SLAC also updates to accept `x-api-key`).

2. **SLAC adds a VPN/WireGuard endpoint** — eliminates the SOCKS5 requirement. The proxy reduces to just auth header normalisation, or disappears if SLAC's version also accepts `x-api-key`.

3. **LiteLLM fixes the remaining `/v1/messages` bugs** (spend logging #23981, `input_text` blocks #23841) and SLAC upgrades — at that point the integration becomes as simple as two env vars for anyone without a network barrier.

The proxy is a shim compensating for two things: network topology and version lag. Both are fixable over time without replacing the fundamental architecture.

---

## Key File Locations

| File | Purpose |
|------|---------|
| `~/.claude/settings.json` | Env vars injected by entrypoint patch; proxy API key fallback |
| `~/.claude/litellm-proxy.py` | Local proxy: SOCKS5 tunneling, request sanitisation, auth normalisation |
| `~/.claude/litellm-proxy-test.py` | 25-check automated test suite |
| `~/.claude/litellm-proxy-README.md` | This file |
| `~/.config/zed/settings.json` | Zed app settings — `"proxy"` (disabled) and `"default_model"` |
| `~/Library/Application Support/Zed/node/cache/_npx/<hash>/node_modules/@zed-industries/claude-agent-acp/dist/index.js` | Entrypoint (patched) |
| `~/Library/Application Support/Zed/node/cache/_npx/<hash>/node_modules/@zed-industries/claude-agent-acp/dist/acp-agent.js` | ACP agent (patched) — builds env for `query()`, contains `createEnvForGateway()` |
| `/opt/homebrew/bin/claude` | Native Claude Code binary (Mach-O arm64, v2.1.79) |
| `~/Library/Logs/Zed/Zed.log` | Zed log — check for `[PATCH]`, `[DEBUG-ENV]`, and errors |


---

## References

- LiteLLM `/v1/messages` endpoint docs: https://docs.litellm.ai/docs/anthropic_unified
- LiteLLM Anthropic pass-through docs: https://docs.litellm.ai/docs/pass_through/anthropic_completion
- LiteLLM proxy config reference: https://docs.litellm.ai/docs/proxy/configs
- GitHub: "I WISH LITELLM HAD: Claude Code, Cursor, VSCode, OpenCode, RooCode" — https://github.com/BerriAI/litellm/issues/19284
- GitHub #23981: `/v1/messages` spend never written to SpendLogs — https://github.com/BerriAI/litellm/issues/23981
- GitHub #23841: `input_text` content blocks silently dropped — https://github.com/BerriAI/litellm/issues/23841
- GitHub #16716: Synchronous Anthropic token counting blocks event loop — https://github.com/BerriAI/litellm/issues/16716
# Claude Code + LiteLLM Integration Guide

## Goal

Configure Claude Code to use a self-hosted LiteLLM proxy service at SLAC
instead of hitting Anthropic's API directly.

## Status: 🟢 Working

- ✅ LiteLLM API validated via curl
- ✅ Dex device flow authentication working
- ✅ `ANTHROPIC_AUTH_TOKEN` can carry the JWT (not just `ANTHROPIC_API_KEY`)
- ✅ **Startup hang root causes identified and resolved** — see §5
- ✅ **Verified minimal working config** — see below
- ✅ **Verified fully self-contained settings.json** — no shell ENV needed (except `env -u`)
- ✅ P0 precedence tests complete — **settings.json `env` wins over shell ENV**
- ✅ `BASE_URL` works in settings.json
- ✅ Top-level `model` key works in settings.json (preferred over `ANTHROPIC_MODEL` env)
- ✅ `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` confirmed **not required**


### ✅ Verified Working Configurations (2025-07-18)

Two verified approaches — choose based on whether you want the config in
settings.json or in a shell wrapper.

#### Option A: Fully self-contained settings.json (recommended)

Everything lives in settings.json. Only `env -u` needed at launch.

**settings.json:**
```json
{
  "model": "copilot-claude-sonnet-4.5",
  "env": {
    "ANTHROPIC_BASE_URL": "https://sdf-llm.slac.stanford.edu",
    "ANTHROPIC_API_KEY": "<jwt from ~/.claude/.token>",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "NO_PROXY": "sdf-llm.slac.stanford.edu"
  }
}
```

`model` is a top-level settings key (not inside `env`). This is cleaner than
`ANTHROPIC_MODEL` in the `env` block — both work, but `model` is the proper
Claude Code setting. It sets the default but does **not** prevent switching —
`--model` flag and `/model` in interactive mode override it per-session.

**Model precedence (verified):**
`--model` flag / `/model` command > settings.json `model` key > `ANTHROPIC_MODEL` env > built-in default (`claude-sonnet-4-6`)

> **⚠️ `modelAliases` does not work.** Claude Code does not recognize a
> `modelAliases` key in settings.json — tested and confirmed that the API
> still receives the unmapped model name. Use `model` instead.

**Shell launch** — no `env -u` needed, `NO_PROXY` in settings handles it:
```
claude
```

⚠️ The JWT in settings.json expires (~12h). Must be refreshed manually or
via `apiKeyHelper` (see §5 — not yet tested). Do NOT add
`ANTHROPIC_AUTH_TOKEN` to settings.json — an empty string causes hangs
(see Finding 2), and there's no advantage over `ANTHROPIC_API_KEY` here.

#### Option B: Minimal settings.json + shell ENV

Settings.json carries only non-sensitive config. Auth provided at launch.

**settings.json:**
```json
{
  "env": {
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "NO_PROXY": "sdf-llm.slac.stanford.edu"
  }
}
```
(`DISABLE_NONESSENTIAL_TRAFFIC` is optional — verified PASS without it too.
Recommended to keep it to prevent telemetry/update calls to Anthropic servers.)

**Shell launch:**
```
ANTHROPIC_API_KEY=$(cat ~/.claude/.token) \
  ANTHROPIC_BASE_URL=https://sdf-llm.slac.stanford.edu \
  claude --model copilot-claude-sonnet-4.5
```

Either `ANTHROPIC_AUTH_TOKEN` or `ANTHROPIC_API_KEY` can carry the JWT
(both verified).

#### Key constraint for both options

**Proxy vars must be bypassed** when the shell has global `*_PROXY`
variables pointing at a SOCKS proxy. Node.js honors these but cannot speak
SOCKS, causing hangs (see Finding 1). Two approaches:

- **`NO_PROXY=sdf-llm.slac.stanford.edu`** in settings.json `env` (preferred —
  keeps global proxy vars intact, verified that Node.js honors `NO_PROXY`)
- **`env -u ALL_PROXY -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy`**
  at launch (brute force — removes all proxy vars from the process)

#### ⚠️ settings.json `env` takes precedence over shell ENV

**Confirmed:** settings.json `env` values **override** shell process
environment variables. Shell ENV cannot rescue a bad value in settings.

| Test | settings `API_KEY` | shell `API_KEY` | Result |
|------|-------------------|-----------------|--------|
| P0a-r | `""` | `<jwt>` | ❌ "Not logged in" — settings wins |
| P0b-r | `<jwt>` | *(none)* | ✅ PASS — settings carries JWT |
| P0c-r | `"wrong"` | `<jwt>` | ⏱ TIMEOUT — settings wins, wrong token hangs |

**Implication:** If you set a value in settings.json `env`, you cannot
override it from the shell. Either put the correct value in settings, or
omit it entirely and provide it via shell ENV.

### Critical Findings (2025-07-18)

The following findings were identified during P0 testing (2025-07-18,
Claude Code v2.1.79). Root causes of the startup hang are items 1–2;
items 3–9 are additional observations.

1. **Inherited proxy env vars cause hangs.** The test shell has global
   `ALL_PROXY`, `HTTPS_PROXY`, `HTTP_PROXY` (and lowercase variants)
   pointing at a SOCKS proxy. Node.js (via undici's `EnvHttpProxyAgent`,
   added in undici v6.14.0) honors `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY`
   env vars, but its `ProxyAgent` only supports **HTTP CONNECT proxies** —
   not SOCKS. When these vars point at a `socks5://` URL, undici attempts
   to speak HTTP to a SOCKS endpoint and hangs indefinitely.
   This was the original "startup hang" attributed to `BASE_URL` in
   settings.json — the real cause was the inherited proxy environment.
   **Preferred fix:** `NO_PROXY=sdf-llm.slac.stanford.edu` in settings.json
   `env` block — Node.js honors `NO_PROXY` and bypasses the proxy for that
   host (verified). **Alternative:** `env -u ALL_PROXY -u HTTPS_PROXY ...`
   at launch (also built into `test-matrix.sh`).
   **References:**
   [nodejs/undici#1650](https://github.com/nodejs/undici/issues/1650) (feature request),
   [nodejs/undici#2994](https://github.com/nodejs/undici/pull/2994) (implementation PR).

2. **`ANTHROPIC_AUTH_TOKEN=""` in settings.json causes hangs.** After
   removing proxy vars, P0 tests revealed that having
   `ANTHROPIC_AUTH_TOKEN=""` (empty string) in the settings.json `env`
   block causes Claude Code to hang, regardless of shell ENV overrides.
   When `AUTH_TOKEN` is a valid JWT or completely absent from settings,
   Claude Code connects normally. Shell ENV does **not** override
   settings.json `AUTH_TOKEN=""`. **Fix:** Do not set `ANTHROPIC_AUTH_TOKEN`
   to empty string in settings.json; either omit it or set it to a valid JWT.

3. **Default model `claude-sonnet-4-6` not mapped on sdf-llm.** Claude Code
   v2.1.79 defaults to model `claude-sonnet-4-6`, which is not configured
   on the LiteLLM proxy (returns 400). **Fix:** Set `"model":
   "copilot-claude-sonnet-4.5"` in settings.json (preferred), or use
   `--model` flag / `ANTHROPIC_MODEL` env var. Alternatively, request that
   `claude-sonnet-4-6` be added as an alias on sdf-llm.

4. **`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` is not required.** Tested
   with no `env` block at all in settings.json (not even `DISABLE_TRAFFIC`),
   providing only `AUTH_TOKEN`, `BASE_URL`, and `--model` via shell — PASS.
   The flag is good hygiene but not a functional requirement.

5. **`ANTHROPIC_API_KEY=""` (empty string) in settings is harmless.** Unlike
   `AUTH_TOKEN=""`, having `API_KEY=""` in settings.json does NOT cause a
   hang. Tested with `API_KEY=""` + `AUTH_TOKEN=<jwt>` in settings — works
   fine (P0d result). Only `AUTH_TOKEN=""` is toxic.

6. **settings.json `env` takes precedence over shell ENV.** Shell process
   environment variables do **not** override values set in the settings.json
   `env` block. If settings has `API_KEY=""`, shell `API_KEY=<jwt>` is
   ignored → "Not logged in". If settings has `API_KEY="wrong"`, shell
   `API_KEY=<jwt>` is ignored → hangs. **Fix:** Either set correct values
   in settings.json, or omit the key entirely and provide via shell.

7. **`BASE_URL` works in settings.json.** Tested with `BASE_URL=sdf-llm`
   in settings.json `env` block, auth via shell — PASS. Also tested fully
   self-contained (BASE_URL + API_KEY + MODEL all in settings) — PASS.

8. **`ANTHROPIC_MODEL` works in settings.json.** When set in the `env`
   block, the `--model` flag is not required. Tested fully self-contained
   config with no shell ENV and no `--model` flag — PASS.

9. **Fully self-contained settings.json verified.** `BASE_URL` + `API_KEY`
   + `ANTHROPIC_MODEL` + `DISABLE_TRAFFIC` all in settings.json `env`,
   no shell ENV at all (only `env -u` for proxy vars) — PASS.

---

## 1. LiteLLM Service

### Endpoints

| Item | Value |
|------|-------|
| **External URL** | `https://sdf-llm.slac.stanford.edu` |
| **Internal URL** | `https://llm.sdf.slac.stanford.edu` (enterprise network only, self-signed TLS) |
| **Identity Provider** | Dex at `https://dex.slac.stanford.edu` |
| **OAuth Client ID** | `ai-playground-cli` |
| **Fronted by** | nginx reverse proxy (only `/v1/*` paths exposed) |

Both hostnames serve the same LiteLLM instance with the same models.

### Confirmed API routes (via curl)

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/v1/models` | GET | ✅ 200 | Returns available models (~26 as of 2025-07-18) |
| `/v1/messages` | POST | ✅ 200 | Anthropic Messages API |
| `/v1/chat/completions` | POST | ✅ 200 | OpenAI-compatible |
| `/v1/completions` | POST | ✅ 200 | Legacy text completions |
| `/v1/messages/count_tokens` | POST | ✅ 200 | Token counting |
| `/v1/embeddings` | POST | ❌ 400 | No embedding model configured |

| `/health`, `/ui/*`, `/sso/*`, `/key/*` | * | ❌ 404 | Admin endpoints not exposed |

### Available models

**Claude (via `copilot-claude-*` aliases) — all verified with Claude Code `--model`:**

| Model alias | `--model` flag | Notes |
|-------------|---------------|-------|
| `copilot-claude-haiku-4.5` | ✅ PASS | |
| `copilot-claude-sonnet-4` | ✅ PASS | |
| `copilot-claude-sonnet-4.5` | ✅ PASS | Recommended default |
| `copilot-claude-sonnet-4.6` | ✅ PASS | |
| `copilot-claude-opus-4.5` | ✅ PASS | |
| `copilot-claude-opus-4.6` | ✅ PASS | |

**GPT (via `copilot-gpt-*`):**
`copilot-gpt-4.1`, `copilot-gpt-4o`, `copilot-gpt-4o-mini`, `copilot-gpt-5-mini`,
`copilot-gpt-5.1`, `copilot-gpt-5.1-codex`, `copilot-gpt-5.1-codex-max`,
`copilot-gpt-5.1-codex-mini`, `copilot-gpt-5.2`, `copilot-gpt-5.2-codex`,
`copilot-gpt-5.3-codex`

**Gemini:** `copilot-gemini-2.5-pro`, `copilot-gemini-3-flash-preview`,
`copilot-gemini-3-pro-preview`, `copilot-gemini-3.1-pro-preview`

**Local/self-hosted:** `gpt-oss:120b`, `nemotron-3-super:120b`,
`qwen3.5:9b`, `qwen3.5:27b`, `qwen3.5:122b`

### Model switching in Claude Code

**`--model` flag (verified):** All 6 `copilot-claude-*` aliases work with
`claude -p "..." --model <name>`. Tested 2025-07-18.

**`/model` slash command (verified):** In interactive mode, `/model <name>`
switches models mid-conversation. All three tiers verified interactively
(2025-07-18):
- `/model copilot-claude-haiku-4.5` → ✅ PASS
- `/model copilot-claude-sonnet-4.6` → ✅ PASS
- `/model copilot-claude-opus-4.6` → ✅ PASS

**⚠️ Built-in shortcuts do NOT work with sdf-llm.** The shorthand names
(`sonnet`, `opus`, `haiku`) resolve to standard Anthropic model IDs that
are not mapped on the proxy:

| Command | Resolves to | sdf-llm |
|---------|-------------|---------|
| `/model sonnet` | `claude-sonnet-4-6` | ❌ 400 |
| `/model opus` | `claude-opus-4-6` | ❌ 400 |
| `/model haiku` | `claude-haiku-4-5` | ❌ 400 |
| `/model copilot-claude-haiku-4.5` | `copilot-claude-haiku-4.5` | ✅ verified |
| `/model copilot-claude-sonnet-4.6` | `copilot-claude-sonnet-4.6` | ✅ verified |
| `/model copilot-claude-opus-4.6` | `copilot-claude-opus-4.6` | ✅ verified |

Always use the full `copilot-claude-*` alias with `/model`. This limitation
goes away if the sdf-llm admin adds aliases for the standard Anthropic model
names (see "Action needed" above).

### Model name mapping (confirmed via curl, 2025-07-18)

| Model ID | `/v1/messages` | Notes |
|----------|---------------|-------|
| `claude-sonnet-4-20250514` (standard) | ✅ Works | Only standard ID that works |
| `claude-sonnet-4-6` | ❌ 400 | **Claude Code v2.1.79 default** — not mapped |
| `claude-opus-4-20250514` | ❌ 400 | Not mapped |
| `claude-haiku-4-20250414` | ❌ 400 | Not mapped |
| All other standard Anthropic IDs | ❌ 400 | Not mapped |
| All shorthand names (`claude-sonnet-4`, etc.) | ❌ 400 | Not mapped |
| All `copilot-claude-*` aliases | ✅ Works | Reliable names |

### Action needed: Request model alias for `claude-sonnet-4-6`

Claude Code v2.1.79 sends model name `claude-sonnet-4-6` by default. This
is a standard Anthropic model ID that Claude Code uses internally — it
cannot be changed without `--model` flag or `ANTHROPIC_MODEL` env var.

sdf-llm does not have this ID mapped, so requests fail with 400. The
workaround is to always specify `--model copilot-claude-sonnet-4.5` (or
set `ANTHROPIC_MODEL` in settings.json). This works, but means every user
must know to do it.

**Request for sdf-llm admin:** Add a model alias in LiteLLM's config so
that `claude-sonnet-4-6` routes to the same backend as
`copilot-claude-sonnet-4.6` (or whichever Sonnet variant is preferred as
the default). This is a server-side LiteLLM config change —
no client changes needed. Once added, Claude Code would work out of the
box without requiring `--model` or `ANTHROPIC_MODEL`.

Ideally, also map other standard Anthropic IDs that Claude Code may use
in future versions (e.g., `claude-opus-4-20250514`, `claude-haiku-4-20250414`).

---

## 2. Authentication — Device Flow via Dex

### OIDC discovery

```
https://dex.slac.stanford.edu/.well-known/openid-configuration
```

| Endpoint | URL |
|----------|-----|
| Device authorization | `https://dex.slac.stanford.edu/device/code` |
| Token | `https://dex.slac.stanford.edu/token` |
| JWKS | `https://dex.slac.stanford.edu/keys` |

Scopes: `openid`, `email`, `groups`, `profile`, `offline_access`

### Device flow steps

**Step 1 — Request device code:**
```
curl -s -X POST https://dex.slac.stanford.edu/device/code \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=ai-playground-cli&scope=openid email profile groups offline_access"
```

**Step 2 — User opens `verification_uri_complete` in browser and authenticates.**

**Step 3 — Poll for token:**
```
curl -s -X POST https://dex.slac.stanford.edu/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:device_code&device_code=<DEVICE_CODE>&client_id=ai-playground-cli"
```

### Token details

| Field | Value |
|-------|-------|
| Issuer | `https://dex.slac.stanford.edu` |
| Audience | `ai-playground-cli` |
| Signing | RS256 |
| Lifetime | ~12 hours (`expires_in: 43199`) |
| Claims | `iss`, `sub`, `aud`, `exp`, `iat`, `at_hash`, `email`, `email_verified`, `name` |

Use the `access_token` as the Bearer token. (The `id_token` also returns
200 in testing, but `access_token` is the standard practice.)

---

## 3. Confirmed: curl API Tests

These tests were run directly via curl against `sdf-llm.slac.stanford.edu`
with a valid Dex JWT. **All confirmed.**

### Auth headers

| Test | Result |
|------|--------|
| `Authorization: Bearer <access_token>` only | ✅ 200 |
| `x-api-key: <access_token>` only | ✅ 200 |
| Both headers (what Claude Code sends) | ✅ 200 |
| `Authorization: Bearer <id_token>` | ✅ 200 |
| Mixed: Bearer=access_token, x-api-key=id_token | ✅ 200 |
| No auth | ❌ 401 |
| Fake token | ❌ 401 |

### URL format

| URL | Result |
|-----|--------|
| `https://sdf-llm.slac.stanford.edu/v1/messages` | ✅ 200 |
| `https://sdf-llm.slac.stanford.edu:443/v1/messages` | ✅ 200 |
| `https://sdf-llm.slac.stanford.edu//v1/messages` (double slash) | ❌ 404 |

**Use `https://sdf-llm.slac.stanford.edu` — no trailing slash.**

### API features

| Feature | Result |
|---------|--------|
| Streaming (`"stream": true`) | ✅ Full SSE lifecycle |
| System message | ✅ Applied correctly |
| Tool use | ✅ Returns `stop_reason: "tool_use"` |
| Token counting (`/v1/messages/count_tokens`) | ✅ Works |
| Without `anthropic-version` header | ✅ Optional |
| Without `content-type` header | ❌ 400 (required) |
| Extended thinking (beta) | ❌ Not functional — see details below |

**Extended thinking investigation (2025-07-18):**

Two independent issues prevent extended thinking from working through sdf-llm:

1. **LiteLLM strips or ignores the `thinking` parameter.** Tested via curl
   with `"thinking": {"type": "enabled", "budget_tokens": 512}` and the
   `anthropic-beta: interleaved-thinking-2025-05-14` header. Response
   returns 200 but contains only a `text` content block — no `thinking`
   block. Token counts are identical with and without the thinking parameter,
   confirming thinking is not happening at all (not just stripped from the
   response — it's never triggered).

2. **Claude Code doesn't attempt extended thinking on non-Anthropic hosts.**
   Debug logs (`--debug-file`) show no mention of thinking, beta headers,
   or budget tokens when `ANTHROPIC_BASE_URL` points to sdf-llm. Claude Code
   detects the non-first-party host and disables features like extended
   thinking and tool search (confirmed by debug line: `[ToolSearch:optimistic]
   disabled: ANTHROPIC_BASE_URL=...is not a first-party Anthropic host`).

**Both issues are server-side / upstream — no client-side fix available.**
Would require LiteLLM config changes to pass through the `thinking` parameter
and `anthropic-beta` header, plus potentially a Claude Code setting to enable
extended thinking on third-party hosts.

---

## 4. Network Topology

| Hostname | DNS | Direct | Notes |
|----------|-----|--------|-------|
| `sdf-llm.slac.stanford.edu` | Public | ✅ Yes | **Recommended.** Valid TLS cert, no proxy needed |
| `llm.sdf.slac.stanford.edu` | Enterprise only | ❌ SERVFAIL | Internal; self-signed TLS; requires proxy or port forward |

**Use `sdf-llm.slac.stanford.edu` for Claude Code.** It is directly
reachable, has a valid public TLS cert, and requires no proxy configuration.

### ⚠️ Inherited proxy env vars

If your shell has global `*_PROXY` env vars (`ALL_PROXY`, `HTTPS_PROXY`,
`HTTP_PROXY`, and lowercase variants) pointing at a SOCKS proxy, Node.js
will try to route through it but **cannot speak SOCKS** — causing hangs.
Node.js's built-in fetch (undici) only supports HTTP CONNECT proxies via
its `EnvHttpProxyAgent`
([nodejs/undici#2994](https://github.com/nodejs/undici/pull/2994)).

**Preferred fix** — add `NO_PROXY` to settings.json `env`:
```json
{
  "env": {
    "NO_PROXY": "sdf-llm.slac.stanford.edu"
  }
}
```

Node.js honors `NO_PROXY` and bypasses the proxy for the listed host
(verified). This is cleaner than `env -u` because it keeps your global
proxy vars intact for other tools.

**Alternative** — unset proxy vars at launch:
```
env -u ALL_PROXY -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy \
  claude ...
```

### Internal hostname (`llm.sdf`)

The internal hostname can be reached via SSH port forward + additional env
vars (`NODE_TLS_REJECT_UNAUTHORIZED=0`, `ANTHROPIC_CUSTOM_HEADERS` for
Host header override). This was tested and works, but is unnecessary when
`sdf-llm` is directly reachable.

---

## 5. Claude Code Configuration

Claude Code is configured via two layers:

1. **`~/.claude/settings.json`** — persistent `env` block, read at startup
2. **Shell environment variables** — set at runtime

### ✅ RESOLVED: Startup Hang Root Causes

The startup hang originally attributed to `BASE_URL` in settings.json
had **two independent causes**, both identified during P0 testing
(2025-07-18):

**Cause 1: Inherited proxy environment variables.**
The shell has `ALL_PROXY`, `HTTPS_PROXY`, `HTTP_PROXY` (and lowercase
variants) set globally, pointing at a SOCKS proxy. Node.js honors these
and routes Claude Code's HTTPS requests through the proxy, which cannot
reach sdf-llm — causing an indefinite hang.

Evidence: `env -i` (clean environment) eliminated the hang immediately.
Selectively unsetting the five proxy vars with `env -u` also works.

**Cause 2: `ANTHROPIC_AUTH_TOKEN=""` in settings.json `env` block.**
After removing proxy vars, tests with `AUTH_TOKEN=""` in settings still
hung, while tests with `AUTH_TOKEN=<jwt>` or `AUTH_TOKEN` absent connected
normally. Claude Code appears to use the empty `AUTH_TOKEN` from
settings.json for an auth flow that fails non-gracefully, and shell ENV
does **not** override it.

Evidence (P0 results with proxy vars removed):
| Test | `AUTH_TOKEN` in settings | Result |
|------|--------------------------|--------|
| P0a  | `""`                     | ⏱ TIMEOUT |
| P0b  | `""`                     | ⏱ TIMEOUT |
| P0c  | `""`                     | ⏱ TIMEOUT |
| P0d  | `<jwt>`                  | ❌ 400 (connected — model not found) |
| P0e  | *(absent)*               | ❌ 400 (connected — model not found) |
| P0f  | `""`                     | ⏱ TIMEOUT |

**Neither cause was `BASE_URL` in settings.json.** The original hypothesis
was wrong — `BASE_URL` is fine in settings as long as proxy vars are
removed and `AUTH_TOKEN` is not set to empty string.

**Additional finding:** Claude Code v2.1.79 defaults to model
`claude-sonnet-4-6`, which returns 400 from sdf-llm. This is why P0d and
P0e got 400 errors instead of PASS — auth worked, but the model wasn't
mapped. Use `--model copilot-claude-sonnet-4.5` (or another mapped name).

### ✅ Verified: `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` Not Required

Tested with no `env` block at all in settings.json — only `hooks` present.
Shell ENV provided `AUTH_TOKEN=<jwt>`, `BASE_URL=sdf-llm`,
`--model copilot-claude-sonnet-4.5`, with proxy vars unset. Result: **PASS**.

This confirms the flag is not required for basic functionality. It prevents
Claude Code from making telemetry/update calls to Anthropic's servers,
which is recommended on a locked-down network but not a blocker.

### ✅ Verified: Debug/Verbose Logging

Claude Code supports debug logging via CLI flags (not environment variables):

**Flags:**
- `-d` / `--debug` — enables debug mode, logs to stderr (may not appear in `-p` mode)
- `-d "api,hooks"` — filter by category (comma-separated, `!` prefix to exclude)
- `--debug-file <path>` — write debug logs to a file (**recommended**)

**Usage:**
```
claude -p "test" --model copilot-claude-sonnet-4.5 --debug-file /tmp/claude-debug.log
```

**Debug categories observed in log output:**
`API:request`, `API:auth`, `STARTUP`, `init`, `ToolSearch:optimistic`,
`LSP MANAGER`, `LSP SERVER MANAGER`, `Perfetto`, `3P telemetry`,
`ScheduledTasks`, `claudeai-mcp`, `clientData`

**What the debug log shows (useful for troubleshooting):**
- Settings loading order and which paths are checked
- CA cert and mTLS configuration
- OAuth token check flow (`[API:auth]`)
- API client creation and headers (`[API:request]`)
- Whether nonessential traffic is skipped (`[clientData]`)
- Skill/plugin loading
- Hook matching and execution
- Stream start timing

**Not environment variables:** `CLAUDE_CODE_DEBUG`, `DEBUG`, and `NODE_DEBUG`
are not used by Claude Code for its own debug output. The `--debug` flag and
`--debug-file` flag are the correct mechanisms.

### ✅ Verified: `API_KEY=""` in settings.json is harmless

Tested with `API_KEY=""` + `AUTH_TOKEN=<jwt>` in settings.json `env` block
(P0d configuration), `BASE_URL` via shell, `--model` flag. Result: **PASS**
(after adding `--model` — original P0d got 400 only because of default
model, not auth).

Unlike `AUTH_TOKEN=""`, an empty `API_KEY` does not cause a hang. Claude Code
tolerates `API_KEY=""` as long as auth is provided via `AUTH_TOKEN`.

### ✅ RESOLVED: settings.json `env` Precedence Over Shell ENV

Tested with `AUTH_TOKEN` omitted from settings (to avoid hang confound),
varying `API_KEY` in settings vs shell:

| Test | settings `API_KEY` | shell `API_KEY` | Result | Interpretation |
|------|-------------------|-----------------|--------|----------------|
| P0a-r | `""` | `<jwt>` | ❌ "Not logged in" | Settings `""` wins, shell ignored |
| P0b-r | `<jwt>` | *(none)* | ✅ PASS | Settings carries JWT directly |
| P0c-r | `"wrong"` | `<jwt>` | ⏱ TIMEOUT | Settings `"wrong"` wins, causes hang |

**Conclusion: settings.json `env` takes precedence over shell ENV.**
Shell process environment cannot override a value present in settings.json
`env`. If a key exists in settings (even as empty string), the shell
value for that key is ignored.

**Implication for configuration:** Either put the correct value in
settings.json `env`, or **omit the key entirely** so shell ENV is used.
Setting a key to `""` as a "placeholder" is dangerous — it will block
the shell override and may cause hangs (for `AUTH_TOKEN`) or auth
failure (for `API_KEY`).

### ✅ Verified: `BASE_URL` Works in settings.json

| Test | settings.json `env` | Shell ENV | `--model` | Result |
|------|---------------------|-----------|-----------|--------|
| B1 | `BASE_URL=sdf-llm`, `DISABLE_TRAFFIC` | `API_KEY=<jwt>` | `copilot-claude-sonnet-4.5` | ✅ PASS |
| B2 | `BASE_URL=sdf-llm`, `API_KEY=<jwt>`, `DISABLE_TRAFFIC` | *(none)* | `copilot-claude-sonnet-4.5` | ✅ PASS |
| B3 | `BASE_URL=sdf-llm`, `API_KEY=<jwt>`, `MODEL=copilot-claude-sonnet-4.5`, `DISABLE_TRAFFIC` | *(none)* | *(none)* | ✅ PASS |

B3 is the fully self-contained config — no shell ENV, no `--model` flag.
Only `env -u` to remove inherited proxy vars is needed at launch.

### `ANTHROPIC_AUTH_TOKEN` can carry the JWT (confirmed)

Tested with shell ENV overrides and proxy vars unset (`env -u`):

| Shell ENV | Result |
|-----------|--------|
| `ANTHROPIC_API_KEY=<jwt>` + `ANTHROPIC_BASE_URL=sdf-llm` | ✅ PASS |
| `ANTHROPIC_AUTH_TOKEN=<jwt>` + `ANTHROPIC_BASE_URL=sdf-llm` (no API_KEY) | ✅ PASS |
| Both `AUTH_TOKEN=<jwt>` + `API_KEY=<jwt>` + `BASE_URL=sdf-llm` | ✅ PASS |
| `--model copilot-claude-sonnet-4.5` | ✅ PASS |
| `--model copilot-claude-opus-4.6` | ✅ PASS |

**Either `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` can carry the JWT.**

### Relevant environment variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_BASE_URL` | LiteLLM proxy URL |
| `ANTHROPIC_API_KEY` | JWT token (sent as both `x-api-key` and `Authorization: Bearer`) |
| `ANTHROPIC_AUTH_TOKEN` | Alternative auth token — can also carry the JWT. ⚠️ Do not set to `""` in settings.json |
| `ANTHROPIC_MODEL` | Override default model name (prefer top-level `model` key in settings.json instead) |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | Prevents calls to Anthropic's servers |
| `NO_PROXY` | Comma-separated hostnames to bypass proxy (preferred fix for SOCKS proxy hangs) |
| `ANTHROPIC_CUSTOM_HEADERS` | Custom headers to add to API requests (e.g., Host header override) |

### ✅ ANSWERED: settings.json + Shell ENV Matrix

All key questions answered (see summary below). The full N1 matrix was
not re-run after the proxy fix and is retained for reference only.

**Abbreviations:**
- `BASE_URL` = `ANTHROPIC_BASE_URL`
- `AUTH_TOKEN` = `ANTHROPIC_AUTH_TOKEN`
- `API_KEY` = `ANTHROPIC_API_KEY`
- `DISABLE_TRAFFIC` = `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` (value: `"1"`)

> **⚠️ All `claude -p` tests must be wrapped with a timeout** (30s).
> Claude Code hangs indefinitely on some misconfigurations.
>
> **Token file:** `~/.claude/.token` (gitignored, mode 600).
> **Test runner:** `~/.claude/test-matrix.sh` (handles settings, timeouts, restore).

#### P0: Precedence tests

P0 tests isolate ENV precedence without triggering the startup hang.
**No `BASE_URL` in settings.json** — `BASE_URL` is always provided via shell ENV.

> **⚠️ `test-matrix.sh` now unsets inherited proxy vars** (`ALL_PROXY`,
> `HTTPS_PROXY`, `HTTP_PROXY`, and lowercase) via `env -u` in `run_test()`.
> This was added after discovering that inherited proxy vars were the
> primary cause of the startup hang (see §5 Critical Findings).

| Test | settings.json | Shell ENV | What it tests | Result |
|------|--------------|-----------|---------------|--------|
| **P0a** | `AUTH_TOKEN=""`, `API_KEY=""` | `API_KEY=<jwt>`, `BASE_URL=sdf-llm` | Does shell `API_KEY` override settings `API_KEY=""`? | ⏱ TIMEOUT |
| **P0b** | `AUTH_TOKEN=""`, `API_KEY=<jwt>` | `BASE_URL=sdf-llm` | Can settings.json carry the JWT directly? | ⏱ TIMEOUT |
| **P0c** | `AUTH_TOKEN=""`, `API_KEY="wrong"` | `API_KEY=<jwt>`, `BASE_URL=sdf-llm` | **Definitive:** if PASS → shell wins; if FAIL → settings wins | ⏱ TIMEOUT |
| **P0d** | `AUTH_TOKEN=<jwt>`, `API_KEY=""` | `BASE_URL=sdf-llm` | Can `AUTH_TOKEN` in settings carry the JWT? | ❌ 400 (model) |
| **P0e** | `DISABLE_TRAFFIC` only | `API_KEY=<jwt>`, `AUTH_TOKEN=<jwt>`, `BASE_URL=sdf-llm` | Can shell ENV fully substitute for missing settings entries? | ❌ 400 (model) |

All P0 tests include `DISABLE_TRAFFIC="1"` in settings. 30s timeout.

| **P0f** | `AUTH_TOKEN=""`, `API_KEY=""` | `API_KEY=<jwt>`, `BASE_URL=sdf-llm`, `ANTHROPIC_MODEL=claude-sonnet-4-20250514` | Does adding model at runtime rescue a config that otherwise hangs? | ⏱ TIMEOUT |

**P0 analysis (2025-07-18):**
- P0a/b/c/f all have `AUTH_TOKEN=""` in settings → all TIMEOUT. This
  confirms `AUTH_TOKEN=""` causes the hang (even with proxy vars removed).
- P0d (`AUTH_TOKEN=<jwt>`) and P0e (`AUTH_TOKEN` absent) both connected
  successfully but got 400 because the default model `claude-sonnet-4-6`
  is not mapped on sdf-llm.
- **P0d proves** settings.json `AUTH_TOKEN` can carry the JWT directly.
- **P0e proves** shell ENV can fully substitute for missing settings entries.
- P0a/b/c precedence questions are **blocked** by the `AUTH_TOKEN=""`
  hang — these tests need to be re-run without `AUTH_TOKEN` in settings.
- **Next steps:** ~~Re-run P0a–P0c without `AUTH_TOKEN` in settings~~ **Done** — see P0a-r/P0b-r/P0c-r below.
  ~~Add `--model` to P0d/P0e~~ — implicitly verified by V3 (same config + model = PASS).

**P0 revised tests (2025-07-18, AUTH_TOKEN omitted from settings):**

| Test | settings `API_KEY` | shell `API_KEY` | Result | Meaning |
|------|-------------------|-----------------|--------|---------|
| P0a-r | `""` | `<jwt>` | ❌ "Not logged in" | Settings wins — shell doesn't override |
| P0b-r | `<jwt>` | *(none)* | ✅ PASS | Settings can carry the JWT |
| P0c-r | `"wrong"` | `<jwt>` | ⏱ TIMEOUT | Settings wins — wrong token hangs |

**Conclusion: settings.json `env` takes precedence over shell ENV.**

**Additional verification tests (2025-07-18, outside test-matrix.sh):**

| Test | settings.json `env` | Shell ENV | `--model` | Result |
|------|---------------------|-----------|-----------|--------|
| V1 | `DISABLE_TRAFFIC` only | `AUTH_TOKEN=<jwt>`, `BASE_URL=sdf-llm` | `copilot-claude-sonnet-4.5` | ✅ PASS (3/3) |
| V2 | `DISABLE_TRAFFIC` only | `API_KEY=<jwt>`, `BASE_URL=sdf-llm` | `copilot-claude-sonnet-4.5` | ✅ PASS |
| V3 | `API_KEY=""`, `AUTH_TOKEN=<jwt>`, `DISABLE_TRAFFIC` | `BASE_URL=sdf-llm` | `copilot-claude-sonnet-4.5` | ✅ PASS |
| V4 | *(no env block at all)* | `AUTH_TOKEN=<jwt>`, `BASE_URL=sdf-llm` | `copilot-claude-sonnet-4.5` | ✅ PASS |
| B1 | `BASE_URL=sdf-llm`, `DISABLE_TRAFFIC` | `API_KEY=<jwt>` | `copilot-claude-sonnet-4.5` | ✅ PASS |
| B2 | `BASE_URL + API_KEY + DISABLE_TRAFFIC` | *(none)* | `copilot-claude-sonnet-4.5` | ✅ PASS |
| B3 | `BASE_URL + API_KEY + MODEL + DISABLE_TRAFFIC` | *(none)* | *(none)* | ✅ PASS |

All verification tests used `env -u` to remove inherited proxy vars.

- **V1** (3/3): Established the minimal config — `DISABLE_TRAFFIC` in settings, everything else via shell.
- **V2**: Confirmed `API_KEY` works as alternative to `AUTH_TOKEN` for carrying the JWT.
- **V3**: Confirmed `API_KEY=""` is harmless when `AUTH_TOKEN=<jwt>` is present.
- **V4**: Confirmed `DISABLE_TRAFFIC` is not required — no `env` block at all still works.
- **B1**: Confirmed `BASE_URL` works in settings.json.
- **B2**: Confirmed fully self-contained settings (BASE_URL + API_KEY), only `--model` via flag.
- **B3**: Confirmed fully self-contained settings including `ANTHROPIC_MODEL` — no shell ENV, no flags.

#### Dimension 1: settings.json `env` configurations

> **⚠️ Note:** S1, S3, S4, S6, S7, S8, S10 have `AUTH_TOKEN=""` — these
> will **all hang** regardless of shell ENV (see Finding 2). Only S2, S5,
> S9 are viable. These configs need redesign: replace `AUTH_TOKEN=""` with
> `AUTH_TOKEN` absent or `AUTH_TOKEN=<jwt>`.

| ID | `BASE_URL` | `AUTH_TOKEN` | `API_KEY` | `DISABLE_TRAFFIC` | Extra |
|----|------------|-------------|-----------|-------------------|-------|
| **S1** (full) | `sdf-llm` | `""` | `""` | `"1"` | ⚠️ AUTH_TOKEN="" → will hang |
| **S2** (no AUTH_TOKEN) | `sdf-llm` | ❌ absent | `""` | `"1"` | |
| **S3** (no API_KEY) | `sdf-llm` | `""` | ❌ absent | `"1"` | ⚠️ AUTH_TOKEN="" → will hang |
| **S4** (no BASE_URL) | ❌ absent | `""` | `""` | `"1"` | ⚠️ AUTH_TOKEN="" → will hang |
| **S5** (minimal) | ❌ absent | ❌ absent | ❌ absent | `"1"` | |
| **S6** (full, llm.sdf) | `llm.sdf` | `""` | `""` | `"1"` | ⚠️ AUTH_TOKEN="" → will hang |
| **S7** (full + model) | `sdf-llm` | `""` | `""` | `"1"` | ⚠️ AUTH_TOKEN="" → will hang |
| **S8** (full, no DISABLE) | `sdf-llm` | `""` | `""` | ❌ absent | ⚠️ AUTH_TOKEN="" → will hang |
| **S9** (empty env) | ❌ absent | ❌ absent | ❌ absent | ❌ absent | `"env": {}` — completely empty |
| **S10** (full, jwt in settings) | `sdf-llm` | `""` | `<jwt>` | `"1"` | ⚠️ AUTH_TOKEN="" → will hang; JWT in API_KEY won't help |

~~S7 tests the hypothesis that the hang is caused by model negotiation~~ —
**Disproven.** Model causes 400 error, not hang. Hang is from `AUTH_TOKEN=""`.

~~S8 tests whether `DISABLE_NONESSENTIAL_TRAFFIC` is masking or causing the
hang~~ — **Answered by V4.** `DISABLE_TRAFFIC` is not required and not
involved in the hang.

S9 tests a truly empty env block. ~~S10 tests whether the JWT can live
entirely in settings.json~~ — S10 has `AUTH_TOKEN=""` so it will hang
regardless. **Needs redesign:** remove `AUTH_TOKEN` or set to `<jwt>`.

#### Dimension 2: Shell ENV at runtime

| ID | `API_KEY` | `BASE_URL` | `AUTH_TOKEN` | `ANTHROPIC_MODEL` | `--model` flag |
|----|-----------|------------|-------------|-------------------|----------------|
| **E1** | `<jwt>` | — | — | — | — |
| **E2** | `<jwt>` | `sdf-llm` | — | — | — |
| **E3** | `<jwt>` | `sdf-llm` | `""` | — | — |
| **E4** | — | `sdf-llm` | `<jwt>` | — | — |
| **E5** | `<jwt>` | `sdf-llm` | `<jwt>` | — | — |
| **E6** | `<jwt>` | `sdf-llm` | — | `claude-sonnet-4-20250514` | — |
| **E7** | `<jwt>` | `sdf-llm` | — | — | `claude-sonnet-4-20250514` |
| **E8** | `<jwt>` | `sdf-llm` | — | — | — | + `CLAUDE_CODE_DEBUG=1` |

~~E6/E7 test whether explicitly setting the model avoids the hang~~ —
**Moot.** The hang is from proxy vars / `AUTH_TOKEN=""`, not model
negotiation. E6/E7 are still useful for testing model override behavior.

E8 enables debug logging — less urgent now that hang causes are identified,
but still useful for observing Claude Code behavior. (Exact debug env var
needs confirmation: `CLAUDE_CODE_DEBUG`? `DEBUG`? `NODE_DEBUG`? `--verbose`?)

#### Matrix N1: Direct to `sdf-llm.slac.stanford.edu`

> **⚠️ Stale results.** This matrix was run before the proxy var fix
> (`env -u` / `NO_PROXY`) was applied. All ⏱ results are proxy-hang
> artifacts, not meaningful test outcomes. The matrix has not been re-run
> because all key questions were answered via targeted P0/V/B tests above.

S × E matrix. Each: `claude -p "respond PASS only"` with 30s timeout.
| | **E1** | **E2** | **E3** | **E4** | **E5** | **E6** | **E7** | **E8** |
|------|---|---|---|---|---|---|---|---|
| **S1** (full) | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ |
| **S2** (no AUTH_TOKEN) | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ |
| **S3** (no API_KEY) | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ |
| **S4** (no BASE_URL) | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ |
| **S5** (minimal) | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ |
| **S7** (full + model) | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ |
| **S8** (no DISABLE) | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ |
| **S9** (empty env) | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ |
| **S10** (jwt in settings) | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ | ⏱ |

#### Phase 0: Sniffer diagnostic (lower priority)

~~Before running the full matrix, run `llm-sniffer.py` to observe exactly
what Claude Code sends at startup. This directly answers the startup hang
hypotheses.~~ **Startup hang is resolved** (proxy vars + `AUTH_TOKEN=""`).
The sniffer is still useful for observing model negotiation and request
structure, but is no longer blocking.

```
# Terminal 1: start sniffer
python3 ~/.claude/llm-sniffer.py -v --port 18080

# Terminal 2: run claude through the sniffer
perl -e 'alarm 30; exec @ARGV' -- env \
  ANTHROPIC_API_KEY=$(cat ~/.claude/.token) \
  ANTHROPIC_BASE_URL=http://127.0.0.1:18080 \
  claude -p "respond PASS only"
```

The sniffer logs will show:
- What requests Claude Code makes at startup (paths, methods)
- What headers it sends (auth, model, version)
- What model name it uses by default
- Whether the upstream returns an error that Claude Code mishandles
- Whether the hang occurs before or after the first request

#### Test runner: `~/.claude/test-matrix.sh`

A script automates all matrix tests. It backs up `settings.json` before
each run and restores it afterwards.

```
# Run P0 precedence tests first
./test-matrix.sh p0

# Run full N1 matrix (~8 min with 30s timeouts)
./test-matrix.sh n1

# Run a single cell
./test-matrix.sh S1 E1

# Run one settings config against all E
./test-matrix.sh S2

# Run everything
./test-matrix.sh all
```

#### Key questions this matrix answers

1. ~~What is the minimal settings.json for Claude Code to work?~~ **ANSWERED.** No `env` block required at all. Auth, URL, and model can all be provided via shell ENV. `DISABLE_TRAFFIC` is optional. Alternatively, everything can live in settings.json (B3).
2. ~~Can shell ENV fully replace settings.json entries?~~ **Yes.** Verified via P0e and V4.
3. ~~Which missing entries cause hangs vs error messages?~~ **ANSWERED.** `AUTH_TOKEN=""` → hang. `API_KEY=""` → "Not logged in" (if no other auth). `API_KEY="wrong"` → hang. Missing entries → fine if shell provides them.
4. ~~Can `ANTHROPIC_AUTH_TOKEN` replace `ANTHROPIC_API_KEY` for carrying the JWT?~~ **Yes.** Both work, verified independently (V1 and V2).
5. ~~**Is the startup hang caused by model negotiation?**~~ **No.** Default model `claude-sonnet-4-6` causes a 400 error, not a hang.
6. ~~**Is the startup hang caused by the BASE_URL being in settings.json at all?**~~ **No.** BASE_URL works fine in settings (B1/B2/B3).
7. ~~**Is `DISABLE_NONESSENTIAL_TRAFFIC` involved?**~~ **No.** V4 confirmed it's not required — PASS with no `env` block at all.
8. ~~**Can settings.json carry the JWT directly?**~~ **Yes.** P0b-r (`API_KEY=<jwt>`), P0d (`AUTH_TOKEN=<jwt>`), B2, B3 all work.
9. ~~**What does Claude Code actually send?**~~ Less urgent now that hang causes are identified. Sniffer still useful for debugging model negotiation.
10. ~~Can Claude Code reach `llm.sdf.slac.stanford.edu`?~~ **Yes** — but requires additional env vars and is not recommended. Direct to `sdf-llm` is simpler. See §4.
11. ~~**Does shell `API_KEY` override settings `API_KEY`?**~~ **No.** Settings wins. P0a-r (`API_KEY=""` in settings, `<jwt>` in shell → "Not logged in"), P0c-r (`"wrong"` in settings, `<jwt>` in shell → TIMEOUT).
12. ~~**Do S1–S3 need redesign?**~~ **Yes, but lower priority.** The full N1 matrix is less urgent now that all key questions are answered. S1/S3/S4/S6/S7/S8/S10 have `AUTH_TOKEN=""` → will hang.
13. ~~**Can `BASE_URL` live in settings.json?**~~ **Yes.** B1/B2/B3 all confirmed.

**Remaining questions:**

14. *(none — all key questions answered)*

### apiKeyHelper (future)

`apiKeyHelper` is a top-level settings.json key that points to a command.
Claude Code runs it and uses its stdout as the API key. This decouples
token management from settings.json — the token file can be refreshed
independently without editing settings.

**Simplest approach — read from token file:**

```json
{
  "model": "copilot-claude-sonnet-4.5",
  "apiKeyHelper": "cat ~/.claude/.token",
  "env": {
    "ANTHROPIC_BASE_URL": "https://sdf-llm.slac.stanford.edu",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  }
}
```

With this config, settings.json is fully static — no JWT embedded in it.
You refresh `~/.claude/.token` however you like (device flow, cron job,
manual paste) and Claude Code picks it up automatically via the helper.

This is cleaner than Option A (JWT in `ANTHROPIC_API_KEY`) because
settings.json never needs editing when the token expires (~12h).

**Status:** Not yet tested. Needs verification that Claude Code actually
calls the helper and uses its output as the API key.

**Future enhancement — refresh token support:**
If Dex issues refresh tokens (via `offline_access` scope — requested but
not yet confirmed working), the helper script could automatically refresh
expired tokens:
1. Read cached token from `~/.claude/.token`
2. Check if expired (decode JWT, check `exp` claim)
3. If valid, print to stdout
4. If expired, use refresh token from `~/.claude/.refresh_token` to get
   a new access token, update `~/.claude/.token`, print to stdout
5. If refresh also fails, exit non-zero (Claude Code should show an error)

This would only require a manual device flow once — after that, the helper
handles renewal silently. But this depends on refresh tokens working, which
is untested.

---

## 6. Quick Validation Commands

```
# Get a token via device flow and save to ~/.claude/.token
DEVICE_RESP=$(curl -s -X POST https://dex.slac.stanford.edu/device/code \
  -d "client_id=ai-playground-cli&scope=openid email profile groups offline_access")
echo "$DEVICE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Open: {d[\"verification_uri_complete\"]}')"
# ... authenticate in browser ...
DEVICE_CODE=$(echo "$DEVICE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['device_code'])")
TOKEN_RESP=$(curl -s -X POST https://dex.slac.stanford.edu/token \
  -d "grant_type=urn:ietf:params:oauth:grant-type:device_code&device_code=$DEVICE_CODE&client_id=ai-playground-cli")
echo "$TOKEN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'],end='')" > ~/.claude/.token
chmod 600 ~/.claude/.token

# Test API via curl
curl -s -H "Authorization: Bearer $(cat ~/.claude/.token)" \
  https://sdf-llm.slac.stanford.edu/v1/models | python3 -m json.tool

# Test Claude Code — interactive (if NO_PROXY is in settings.json)
ANTHROPIC_API_KEY=$(cat ~/.claude/.token) \
  ANTHROPIC_BASE_URL=https://sdf-llm.slac.stanford.edu \
  claude --model copilot-claude-sonnet-4.5

# Test Claude Code — interactive (if NO_PROXY is NOT in settings.json)
NO_PROXY=sdf-llm.slac.stanford.edu \
  ANTHROPIC_API_KEY=$(cat ~/.claude/.token) \
  ANTHROPIC_BASE_URL=https://sdf-llm.slac.stanford.edu \
  claude --model copilot-claude-sonnet-4.5

# Test Claude Code — one-shot with timeout
perl -e 'alarm 30; exec @ARGV' -- env \
  NO_PROXY=sdf-llm.slac.stanford.edu \
  ANTHROPIC_API_KEY=$(cat ~/.claude/.token) \
  ANTHROPIC_BASE_URL=https://sdf-llm.slac.stanford.edu \
  claude -p "say hello" --model copilot-claude-sonnet-4.5
```

---

## 7. Open Questions

### Must investigate

- [x] **Startup hang:** ~~Why does Claude Code hang?~~ **RESOLVED** — Two causes: (1) inherited `*_PROXY` env vars routing through non-functional SOCKS proxy; (2) `ANTHROPIC_AUTH_TOKEN=""` in settings.json triggers non-graceful auth failure. See §5 Critical Findings.
- [x] **Minimal working config:** **VERIFIED** — No `env` block needed in settings.json. Auth + URL + model via shell ENV. See §Status.
- [x] **Fully self-contained config:** **VERIFIED** — `BASE_URL` + `API_KEY` + `ANTHROPIC_MODEL` + `DISABLE_TRAFFIC` all in settings.json, no shell ENV needed (only `env -u` for proxy vars). See B3 test.
- [x] **Is `ANTHROPIC_AUTH_TOKEN=""` required in settings.json?** **No — it causes hangs.** Must be absent or set to a valid JWT.
- [x] **Is `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` required?** **No.** Works without it (V4 test). Good hygiene but not functional.
- [x] **API_KEY precedence:** **Settings.json wins.** Shell ENV does not override settings.json `env` values. See P0a-r/P0c-r tests.
- [x] **Can `BASE_URL` live in settings.json?** **Yes.** See B1/B2/B3 tests.
- [x] **Can `ANTHROPIC_MODEL` live in settings.json?** **Yes.** See B3 test — no `--model` flag needed. Even better: use top-level `model` key (see Option A).
- [x] **Does `modelAliases` work?** **No.** Tested — Claude Code ignores it and sends the original model name to the API. Use `model` key instead.

- [ ] **Request `claude-sonnet-4-6` alias on sdf-llm.** See §1 "Action needed" for details. Claude Code defaults to this model name; without a server-side alias, `--model` or `ANTHROPIC_MODEL` is always required.

### Nice to have

- [ ] Build `apiKeyHelper` script for automatic token management
- [ ] Test if refresh tokens work (from `offline_access` scope)
- [x] ~~Investigate why extended thinking blocks are stripped by the proxy~~ **Two causes:** (1) LiteLLM strips/ignores the `thinking` param — token counts identical with and without it; (2) Claude Code doesn't even attempt thinking on non-Anthropic hosts. See §3 "API features". No client-side fix.
- [ ] Request model alias additions on sdf-llm for other standard Anthropic IDs (covered by §1 alias request)
- [x] ~~Test `/model` switching in interactive mode~~ **Verified.** `/model copilot-claude-sonnet-4.6` works. Built-in shortcuts (`sonnet`, `opus`, `haiku`) do NOT work — they resolve to unmapped standard Anthropic IDs. Must use full `copilot-claude-*` alias. See §1 "Model switching in Claude Code".
- [x] ~~Test `modelOverrides` in settings.json for mapping standard IDs → copilot aliases~~ **Tested as `modelAliases` — does not work.** Use top-level `model` key to set default model. No client-side remapping exists; request server-side aliases instead (see §1).
- [x] ~~Confirm the correct debug/verbose env var for Claude Code~~ **Not env vars.** Use `--debug-file <path>` (recommended) or `-d` / `--debug` CLI flags. See §5 "Debug/Verbose Logging".
- [ ] Create a launch wrapper script (e.g., `~/.local/bin/claude-sdf`) that handles `env -u`, token loading, `BASE_URL`, and `--model` automatically
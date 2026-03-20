# Plan: Generalize `litellm-proxy-README.md`

## Context

`litellm-proxy-README.md` is currently a highly specialized document written for SLAC staff
who want to connect Claude Code (running in Zed) to SLAC's internal LiteLLM service at
`sdf-llm.slac.stanford.edu`. The proxy itself (`litellm-proxy.py`) is already fully generic
— all behavior is controlled via CLI flags with no hardcoded SLAC URLs — but the documentation
assumes a SLAC reader throughout.

The goal is to restructure the README so that:
1. Any user with any LiteLLM service can understand and use the proxy
2. Operators can easily expose the proxy as a shared service for others to connect to
3. SLAC-specific details are preserved but demoted to an Appendix

---

## Proposed New Document Structure

```
litellm-proxy-README.md  (restructured)
│
├─ §1   What This Is & Why You Need It
│        ├─ "The Simple Case" callout (2-line env var approach)
│        └─ "Do I need this proxy?" checklist
│
├─ §2   Quick Start
│        ├─ Step 1: Configure ~/.claude/settings.json  (generic placeholders)
│        ├─ Step 2: Start the proxy
│        └─ Step 3: Verify
│
├─ §3   Architecture                                   (generic ASCII diagram)
│
├─ §4   CLI Reference                                  (keep verbatim — already generic)
│
├─ §5   What the Proxy Does (Protocol Translation)     (keep verbatim — already generic)
│
├─ §6   Running as a Shared Service                    ★ NEW
│        ├─ Three deployment topologies
│        ├─ Option A: SSH reverse tunnel
│        ├─ Option B: Reverse proxy (nginx / Caddy)
│        └─ Option C: Direct network exposure + auth model
│
├─ §7   Connecting to a Shared Proxy                   ★ NEW — minimal 3-step client guide
│
├─ §8   Network Access: SOCKS5 Tunnelling              (genericized)
│
├─ §9   Zed Integration                                (keep verbatim — already generic)
│
├─ §10  Verification & Debugging                       (strip SLAC URLs from log examples)
│
├─ §11  Root Causes & Known Issues                     (genericized language)
│
├─ §12  Compatibility & LiteLLM Integration Modes      (keep verbatim — already generic)
│
├─ §13  Alternative Approaches Considered              (keep verbatim)
│
├─ §14  Appendix: SLAC Configuration Example           ← all SLAC-specific content lands here
│
└─ §15  References
```

---

## Content Migration Map

| Current content | Destination | Treatment |
|---|---|---|
| Title + opening paragraph | §1 What This Is | Rewrite: remove Zed/ACP focus; lead with "Claude Code + any LiteLLM" |
| Architecture diagram (SLAC URL) | §3 Architecture | Replace `sdf-llm.slac.stanford.edu` → `<your-litellm-server>` |
| "Running the Proxy" + Prerequisites | §2 Quick Start | Split: prerequisites → Step 1; startup → Step 2 |
| "Confirming it's working" | §2 Quick Start Step 3 | Move inline |
| Root Causes & Fixes §§1–8 | §11 Root Causes | Replace "SLAC's LiteLLM/nginx" → "older LiteLLM versions"; keep all technical detail |
| `~/.claude/settings.json` example | §2 Quick Start Step 1 | Genericize: replace SLAC URL with `<your-litellm-server>` |
| `~/.config/zed/settings.json` | §9 Zed Integration | Keep as-is — Zed-specific but already generic |
| Request Sanitisation table | §5 What the Proxy Does | Keep verbatim |
| Entrypoint patch scripts | §9 Zed Integration | Keep verbatim |
| Verification + Debugging | §10 | Keep verbatim; strip SLAC URLs from example log snippets |
| "SOCKS Proxying" | §8 SOCKS5 Tunnelling | Replace `sdf-login.slac.stanford.edu` → `<gateway-host>`; exact SLAC command → Appendix |
| Background: LiteLLM modes + Official Right Way | §12 Compatibility | Keep verbatim — already generic |
| Background: SLAC constraints table | §14 Appendix | Move entirely |
| "Future State" | §14 Appendix | Move entirely |
| CLI options table | §4 CLI Reference | Keep verbatim — no SLAC-specific defaults |
| Key File Locations table | near §15 | Mark SLAC-specific entries `[SLAC example]` |
| References | §15 References | Keep verbatim |

---

## New Sections to Add

### §1 — "The Simple Case" callout

Place right after the opening paragraph:

> **You may not need this proxy.** If your LiteLLM server is modern, reachable on your
> local network, and configured with `drop_params: True`, just set:
> ```sh
> export ANTHROPIC_BASE_URL=http://your-litellm-server:4000
> export ANTHROPIC_API_KEY=sk-your-virtual-key
> ```
> **Use this proxy when** the direct approach fails — see the checklist below.

"Do I need this proxy?" checklist:
- [ ] LiteLLM server rejects unknown request fields (HTTP 400 / 422)?
- [ ] Server expects `Authorization: Bearer` but Claude Code sends `x-api-key`?
- [ ] Model names sent by Claude Code don't match what your server expects?
- [ ] Server is not directly reachable (needs SOCKS5 / SSH tunnel)?
- [ ] You want to inspect / log all traffic between Claude Code and LiteLLM?

---

### §6 — Running as a Shared Service (entirely new)

**Three deployment topologies:**

```
[Local only]     claude  ──→  local proxy  ──→  LiteLLM
[Team shared]    users   ──→  shared proxy host  ──→  LiteLLM
[Network-gated]  users   ──→  local proxy  ──→  SOCKS tunnel  ──→  LiteLLM
                                                               ↑ (SLAC example, see Appendix)
```

**Option A — SSH Reverse Tunnel** (operator exposes local proxy on a shared host):
```sh
# Run on operator's machine:
ssh -R 19999:127.0.0.1:19999 user@shared-host
# Users connect via:
export ANTHROPIC_BASE_URL=http://shared-host:19999
```

**Option B — Reverse proxy (nginx / Caddy):**
```nginx
# nginx snippet (TLS termination handled upstream)
location / {
    proxy_pass http://127.0.0.1:19999;
    proxy_set_header Host $host;
}
```
Caddy: `reverse_proxy localhost:19999`

**Option C — Direct exposure** — start proxy with a non-loopback bind address; use
firewall rules to restrict who can reach it. The proxy has no built-in auth at the
proxy layer; handle TLS and auth at the reverse-proxy tier.

**Auth model for multi-user deployments:** The proxy normalises the auth header and
forwards the key in `Authorization: Bearer`. Each user can supply their own LiteLLM
virtual key via `ANTHROPIC_API_KEY`; the `--token` flag forces a single shared key for
all requests. Recommend per-user keys + per-key rate limits configured in LiteLLM.

---

### §7 — Connecting to a Shared Proxy (entirely new)

Minimal guide for end-users who don't operate the proxy — they just want to point
their Claude Code at a proxy someone else is running:

```sh
# Step 1: Get the proxy URL and your LiteLLM virtual key from the proxy operator.

# Step 2: Set the two env vars (in ~/.claude/settings.json or your shell profile):
export ANTHROPIC_BASE_URL=http://<proxy-host>:<proxy-port>
export ANTHROPIC_API_KEY=<your-virtual-key>

# Step 3: Smoke test — should return a short assistant message:
curl -s http://<proxy-host>:<proxy-port>/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: <your-virtual-key>" \
  -d '{"model":"claude-sonnet-4-5","max_tokens":10,
       "messages":[{"role":"user","content":"hi"}]}'
```

If the proxy is behind SSH: `ssh -L 19999:localhost:19999 user@proxy-host` forwards
the port to your local machine.

---

## SLAC-Specific Content: Abstract vs. Preserve

### Replace with generic placeholders in the main body

| Current (SLAC-specific) | Generic replacement |
|---|---|
| `https://sdf-llm.slac.stanford.edu` | `https://<your-litellm-server>` |
| `<user>@sdf-login.slac.stanford.edu` | `<user>@<gateway-host>` |
| Model name rewrite table (hyphen → dot) | Reframe: "some deployments expect dots; use `--model-map` or `--force-model`" |
| `--target` default shown as SLAC URL | Change shown default to `http://localhost:4000` (LiteLLM default port) |
| "SLAC's LiteLLM/nginx rejects…" | "older LiteLLM versions may reject…" |

### Move verbatim to Appendix §14

- The "Simple Case vs Our Constraints" table (exact SLAC constraints — invaluable as worked example)
- Exact SSH SOCKS tunnel command (`ssh -D 9051 ... sdf-login.slac.stanford.edu`)
- SLAC model name rewrite table (hyphen → dot)
- SLAC-specific Future State / upgrade roadmap
- Full startup sequence (proxy + SOCKS + verify) with SLAC-specific paths
- Note that `litellm-proxy-test.py` is SLAC-tuned; other deployments should adapt the infrastructure checks

**Appendix §14 opening callout:**
> **This appendix describes the configuration used at SLAC (SLAC National Accelerator
> Laboratory) as a worked example of the "Network-gated" topology. If you are not a
> SLAC user, treat it as a reference for adapting the proxy to your environment.**

---

## What Does NOT Change

| File / section | Reason |
|---|---|
| `litellm-proxy.py` — logic | Already fully configurable via CLI; no functional changes needed |
| `litellm-proxy.py` — docstring | Minor: replace `sdf-llm.slac.stanford.edu` → `<your-litellm-server>` |
| `litellm-proxy-test.py` | Remains SLAC-specific; README notes it is SLAC-tuned |
| CLI options table (§4) | Already 100% generic |
| Protocol translation section (§5) | Already generic |
| Zed entrypoint patch scripts (§9) | Already generic |

---

## Verification Criteria

After the README rewrite:

1. A reader unfamiliar with SLAC can follow §1–§7 to connect Claude Code to any LiteLLM service.
2. A SLAC user can jump straight to Appendix §14 and follow the same workflow as today.
3. A proxy operator can find everything needed to expose the proxy to their team in §6.
4. Search the final document for `slac`, `sdf-llm`, `sdf-login` — these strings appear **only** in §14 (Appendix) and §15 (References), nowhere in the main body.

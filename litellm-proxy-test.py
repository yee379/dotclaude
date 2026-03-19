#!/usr/bin/env python3
"""
litellm-proxy-test.py — Comprehensive test suite for the Zed + LiteLLM proxy setup.

Tests:
  1. Infrastructure      — SOCKS tunnel, proxy process, proxy port
  2. JS Patches          — index.js and acp-agent.js patched in all _npx dirs
  3. Proxy: basics       — POST /v1/messages, ?beta=true stripped, model rewrite
  4. Proxy: stripping    — context_management, output_config, thinking, beta headers
  5. Proxy: auth         — empty x-api-key falls back to settings.json key
  6. Proxy: streaming    — stream=true returns SSE data: lines
  7. Proxy: real-world   — full combined payload (all bad fields + ?beta=true) → 200
  8. Zed log             — [PATCH] and [DEBUG-ENV] present and correct, no routing errors

Usage:
    python3 ~/.claude/litellm-proxy-test.py
"""

import sys, os, json, socket, glob, re, time, subprocess
import http.client

# ── Config ────────────────────────────────────────────────────────────────
PROXY_HOST  = "127.0.0.1"
PROXY_PORT  = 19999
SOCKS_HOST  = "127.0.0.1"
SOCKS_PORT  = 9051
PROXY_LOG   = "/tmp/litellm-proxy.log"
ZED_LOG     = os.path.expanduser("~/Library/Logs/Zed/Zed.log")
ACP_DIST    = os.path.expanduser(
    "~/Library/Application Support/Zed/node/cache/_npx/"
    "*/node_modules/@zed-industries/claude-agent-acp/dist/"
)

# Minimal valid payload — intentionally small so each test is fast
_BASE_BODY = {
    "model":    "claude-sonnet-4-6",
    "max_tokens": 8,
    "messages": [{"role": "user", "content": "hi"}],
}

# ── Terminal colours ──────────────────────────────────────────────────────
_IS_TTY = sys.stdout.isatty()
def _c(code, s): return f"\033[{code}m{s}\033[0m" if _IS_TTY else s
GREEN  = lambda s: _c("32", s)
RED    = lambda s: _c("31", s)
YELLOW = lambda s: _c("33", s)
CYAN   = lambda s: _c("36", s)
BOLD   = lambda s: _c("1",  s)
DIM    = lambda s: _c("2",  s)

# ── Result tracking ───────────────────────────────────────────────────────
_results = []   # list of (status, name, detail)

def _record(status, name, detail=""):
    _results.append((status, name, detail))
    icon = {"PASS": GREEN("✅ PASS"), "FAIL": RED("❌ FAIL"), "WARN": YELLOW("⚠️  WARN")}[status]
    line = f"  {icon}  {name}"
    if detail:
        line += f"  {DIM(detail[:120])}"
    print(line)

def ok(name, detail=""):   _record("PASS", name, detail)
def fail(name, detail=""): _record("FAIL", name, detail)
def warn(name, detail=""): _record("WARN", name, detail)

def section(title):
    width = 56
    pad   = "─" * max(0, width - len(title) - 1)
    print(f"\n{BOLD(CYAN(f'── {title} {pad}'))}")

# ── HTTP helpers ──────────────────────────────────────────────────────────

def _log_offset():
    try:    return os.path.getsize(PROXY_LOG)
    except: return 0

def _new_log_lines(offset):
    try:
        with open(PROXY_LOG, "r", errors="replace") as f:
            f.seek(offset)
            return f.read().splitlines()
    except:
        return []

def proxy_post(path="/v1/messages", body=None, extra_headers=None, timeout=30):
    """
    POST to the proxy.  Returns (http_status, response_body_str, new_proxy_log_lines).
    Returns (None, error_message, []) on connection failure.
    """
    if body is None:
        body = dict(_BASE_BODY)

    body_bytes = json.dumps(body).encode("utf-8")
    hdrs = {
        "Content-Type":      "application/json",
        "x-api-key":         "",
        "anthropic-version": "2023-06-01",
        "Content-Length":    str(len(body_bytes)),
    }
    if extra_headers:
        for k, v in extra_headers.items():
            if v is None:
                hdrs.pop(k, None)
            else:
                hdrs[k] = v

    offset = _log_offset()
    try:
        conn = http.client.HTTPConnection(PROXY_HOST, PROXY_PORT, timeout=timeout)
        conn.request("POST", path, body=body_bytes, headers=hdrs)
        resp     = conn.getresponse()
        status   = resp.status
        rb       = resp.read().decode("utf-8", errors="replace")
        conn.close()
    except Exception as exc:
        return None, str(exc), []

    new_lines = _new_log_lines(offset)
    return status, rb, new_lines

def _log_has(lines, *patterns):
    """Return True if any line contains ALL of the given patterns."""
    for line in lines:
        if all(p.lower() in line.lower() for p in patterns):
            return True
    return False

# ── Test groups ───────────────────────────────────────────────────────────

def test_infrastructure():
    section("1. Infrastructure")

    # Stale claude / claude-agent-acp processes
    r = subprocess.run(["pgrep", "-f", r"claude(?!.*litellm-proxy)"],
                       capture_output=True, text=True)
    stale = [p.strip() for p in r.stdout.strip().splitlines() if p.strip()]
    # Also check for node acp processes
    r2 = subprocess.run(["pgrep", "-f", "claude-agent-acp"],
                        capture_output=True, text=True)
    stale += [p.strip() for p in r2.stdout.strip().splitlines() if p.strip()]
    # Deduplicate
    stale = sorted(set(stale))
    if stale:
        warn("No stale claude/acp processes",
             f"PIDs {', '.join(stale)} still running — kill with: kill {' '.join(stale)}")
    else:
        ok("No stale claude/acp processes")

    # SOCKS tunnel
    try:
        s = socket.create_connection((SOCKS_HOST, SOCKS_PORT), timeout=3)
        s.close()
        ok("SOCKS tunnel reachable", f"{SOCKS_HOST}:{SOCKS_PORT}")
    except Exception as e:
        fail("SOCKS tunnel reachable",
             f"{e} — run: ssh -D {SOCKS_PORT} -q -N <user>@sdf-login.slac.stanford.edu")

    # Proxy process
    r = subprocess.run(["pgrep", "-f", "litellm-proxy.py"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        pids = r.stdout.strip().replace("\n", ", ")
        ok("Proxy process running", f"PID {pids}")
    else:
        fail("Proxy process running",
             "not found — run: nohup python3 ~/.claude/litellm-proxy.py "
             "> /tmp/litellm-proxy.log 2>&1 &")

    # Proxy port
    try:
        s = socket.create_connection((PROXY_HOST, PROXY_PORT), timeout=3)
        s.close()
        ok("Proxy port listening", f"{PROXY_HOST}:{PROXY_PORT}")
    except Exception as e:
        fail("Proxy port listening", str(e))


def test_patches():
    section("2. JS Patches")

    for filename in ("index.js", "acp-agent.js"):
        files = glob.glob(ACP_DIST + filename)
        if not files:
            fail(f"{filename} files found",
                 "no _npx hash dirs — check Zed installation")
            continue
        for path in sorted(files):
            hash_dir = path.split("_npx/")[1].split("/")[0][:16]
            try:
                content = open(path).read()
            except Exception as e:
                fail(f"{filename} readable [{hash_dir}]", str(e))
                continue
            if "LITELLM_PROXY_PATCH" in content:
                ok(f"{filename} patched [{hash_dir}]")
            else:
                fail(f"{filename} patched [{hash_dir}]",
                     "patch absent — re-apply patches from README and restart Zed")


def test_basic():
    section("3. Proxy — Basic Requests")

    # Plain POST
    status, body, log = proxy_post()
    if status == 200:
        ok("POST /v1/messages → 200")
    else:
        fail("POST /v1/messages → 200",
             f"status={status}  body={body[:160]}")

    # ?beta=true path — THE KEY FIX: must be stripped so nginx doesn't 400
    status, body, log = proxy_post(path="/v1/messages?beta=true")
    beta_stripped = _log_has(log, "stripped query params", "beta")
    if status == 200 and beta_stripped:
        ok("POST /v1/messages?beta=true → 200", "query param stripped before upstream")
    elif status == 200:
        warn("POST /v1/messages?beta=true → 200",
             "no 'stripped query params' log line — stripping may be silent")
    else:
        fail("POST /v1/messages?beta=true → 200",
             f"status={status} — nginx returned 400; ?beta= not stripped")

    # Model name rewriting  claude-sonnet-4-6  →  claude-sonnet-4.6
    status, body, log = proxy_post()   # body already uses claude-sonnet-4-6
    rewritten = _log_has(log, "model rewrite", "claude-sonnet-4.6")
    if rewritten:
        ok("Model rewrite  claude-sonnet-4-6 → claude-sonnet-4.6")
    else:
        warn("Model rewrite  claude-sonnet-4-6 → claude-sonnet-4.6",
             "no rewrite log line — model name may not need rewriting or log delayed")


def test_stripping():
    section("4. Proxy — Field & Header Stripping")

    cases = [
        (
            "context_management stripped → 200",
            {"context_management": {"enabled": True}},
            None,
            ("stripped", "context_management"),
        ),
        (
            "output_config stripped → 200",
            {"output_config": {"format": "text"}},
            None,
            ("stripped", "output_config"),
        ),
        (
            "thinking type=adaptive stripped → 200",
            {"thinking": {"type": "adaptive"}},
            None,
            ("stripped", "adaptive"),
        ),
        (
            "thinking type=enabled missing budget_tokens → budget_tokens injected → 200",
            {"thinking": {"type": "enabled"}},
            None,
            ("budget_tokens",),
        ),
        (
            "anthropic-beta unsupported flags stripped → 200",
            {},
            {"anthropic-beta": "context-management-2025-06-27,"
                               "effort-2025-11-24,"
                               "prompt-caching-scope-2026-01-05"},
            ("stripped anthropic-beta header entirely",),
        ),
        (
            "anthropic-dangerous-direct-browser-access stripped → 200",
            {},
            {"anthropic-dangerous-direct-browser-access": "true"},
            ("stripped header", "anthropic-dangerous"),
        ),
    ]

    for label, extra_body, extra_headers, log_patterns in cases:
        body = {**_BASE_BODY, **extra_body}
        status, resp_body, log = proxy_post(
            body=body, extra_headers=extra_headers
        )
        log_hit = _log_has(log, *log_patterns) if log_patterns else True
        if status == 200 and log_hit:
            ok(label)
        elif status == 200:
            warn(label, f"status=200 but no proxy log match for {log_patterns}")
        else:
            fail(label,
                 f"status={status}  body={resp_body[:160]}")


def test_auth():
    section("5. Proxy — Auth / API Key Fallback")

    # Empty x-api-key — proxy must fall back to settings.json key
    status, body, log = proxy_post(extra_headers={"x-api-key": ""})
    if status == 200:
        ok("Empty x-api-key → 200 via settings.json fallback")
    elif status == 401:
        fail("Empty x-api-key fallback",
             "401 — check ANTHROPIC_API_KEY in ~/.claude/settings.json env block")
    else:
        fail("Empty x-api-key fallback", f"status={status}  body={body[:160]}")

    # No x-api-key header at all
    status, body, log = proxy_post(extra_headers={"x-api-key": None})
    if status == 200:
        ok("Missing x-api-key header → 200 via settings.json fallback")
    else:
        warn("Missing x-api-key header fallback",
             f"status={status} (may be fine if upstream accepts no key)")

    # Root cause 8 regression guard: claude binary sends `authorization: Bearer`
    # directly (OAuth-style) rather than x-api-key.  The proxy must strip the
    # incoming header and emit exactly ONE canonical Authorization header — not
    # two.  nginx returns 400 for duplicate Authorization headers.
    status, body, log = proxy_post(
        extra_headers={"x-api-key": None, "authorization": "Bearer test-sdk-token"},
    )
    if status == 200:
        # Confirm only ONE Authorization header was forwarded (no duplicate)
        auth_lines = [l for l in log if "authorization" in l.lower() and "bearer" in l.lower()]
        dup = len(auth_lines) > 1
        if dup:
            fail("authorization Bearer header dedup",
                 f"proxy log shows multiple auth lines → duplicate header bug: {auth_lines}")
        else:
            ok("authorization Bearer header → 200 (no duplicate Authorization)")
    else:
        fail("authorization Bearer header dedup",
             f"status={status} — proxy may be forwarding duplicate Authorization headers")


def test_streaming():
    section("6. Proxy — Streaming (SSE)")

    body = {**_BASE_BODY, "stream": True}
    body_bytes = json.dumps(body).encode("utf-8")
    hdrs = {
        "Content-Type":      "application/json",
        "x-api-key":         "",
        "anthropic-version": "2023-06-01",
        "Accept":            "text/event-stream",
        "Content-Length":    str(len(body_bytes)),
    }
    offset = _log_offset()
    try:
        conn = http.client.HTTPConnection(PROXY_HOST, PROXY_PORT, timeout=30)
        conn.request("POST", "/v1/messages", body=body_bytes, headers=hdrs)
        resp = conn.getresponse()
        status = resp.status
        # Read a reasonable chunk — don't need the whole stream
        chunk = resp.read(8192).decode("utf-8", errors="replace")
        conn.close()
    except Exception as exc:
        fail("Streaming SSE /v1/messages", str(exc))
        return

    log = _new_log_lines(offset)
    streamed = _log_has(log, "streamed") or _log_has(log, "stream=True")

    if status == 200 and "data:" in chunk:
        ok("Streaming SSE /v1/messages → 200 + data: lines",
           f"{chunk.count('data:')} data: events in first 8 KB")
    elif status == 200:
        warn("Streaming SSE /v1/messages → 200 but no data: lines",
             f"response start: {chunk[:120]}")
    else:
        fail("Streaming SSE /v1/messages",
             f"status={status}  body={chunk[:160]}")

    # Streaming with ?beta=true (the real pattern the claude binary uses)
    body_bytes2 = json.dumps({**_BASE_BODY, "stream": True}).encode("utf-8")
    hdrs2 = {**hdrs, "Content-Length": str(len(body_bytes2))}
    offset2 = _log_offset()
    try:
        conn = http.client.HTTPConnection(PROXY_HOST, PROXY_PORT, timeout=30)
        conn.request("POST", "/v1/messages?beta=true", body=body_bytes2, headers=hdrs2)
        resp2 = conn.getresponse()
        st2 = resp2.status
        chunk2 = resp2.read(8192).decode("utf-8", errors="replace")
        conn.close()
    except Exception as exc:
        fail("Streaming SSE /v1/messages?beta=true", str(exc))
        return

    log2 = _new_log_lines(offset2)
    beta_stripped = _log_has(log2, "stripped query params", "beta")
    if st2 == 200 and "data:" in chunk2 and beta_stripped:
        ok("Streaming SSE /v1/messages?beta=true → 200", "beta stripped + data: lines")
    elif st2 == 200 and "data:" in chunk2:
        warn("Streaming SSE /v1/messages?beta=true → 200",
             "no strip log line (may be silent)")
    else:
        fail("Streaming SSE /v1/messages?beta=true",
             f"status={st2}  body={chunk2[:160]}")


def test_real_world():
    section("7. Proxy — Real-World Combined Payload")

    # Mirrors what the claude binary actually sends:
    #   path  :  /v1/messages?beta=true
    #   body  :  model with hyphens + context_management + output_config
    #            + thinking(adaptive) + stream=true
    #   hdrs  :  anthropic-beta unsupported flags
    #            + anthropic-dangerous-direct-browser-access
    body = {
        "model":               "claude-sonnet-4-6",
        "max_tokens":          8,
        "stream":              True,
        "messages":            [{"role": "user", "content": "hi"}],
        "context_management":  {"enabled": True, "max_tokens": 8000},
        "output_config":       {"format": "text"},
        "thinking":            {"type": "adaptive"},
        "metadata":            {"user_id": "test-suite"},
    }
    extra_headers = {
        "anthropic-beta": (
            "context-management-2025-06-27,"
            "effort-2025-11-24,"
            "prompt-caching-scope-2026-01-05"
        ),
        "anthropic-dangerous-direct-browser-access": "true",
        "Accept": "text/event-stream",
    }

    body_bytes = json.dumps(body).encode("utf-8")
    hdrs = {
        "Content-Type":      "application/json",
        "x-api-key":         "",
        "anthropic-version": "2023-06-01",
        "Content-Length":    str(len(body_bytes)),
        **extra_headers,
    }

    offset = _log_offset()
    try:
        conn = http.client.HTTPConnection(PROXY_HOST, PROXY_PORT, timeout=30)
        conn.request("POST", "/v1/messages?beta=true",
                     body=body_bytes, headers=hdrs)
        resp   = conn.getresponse()
        status = resp.status
        chunk  = resp.read(8192).decode("utf-8", errors="replace")
        conn.close()
    except Exception as exc:
        fail("Real-world combined payload", str(exc))
        return

    log = _new_log_lines(offset)
    checks = {
        "beta stripped":           _log_has(log, "stripped query params", "beta"),
        "model rewritten":         _log_has(log, "model rewrite", "claude-sonnet-4.6"),
        "context_management gone": _log_has(log, "stripped", "context_management"),
        "output_config gone":      _log_has(log, "stripped", "output_config"),
        "thinking adaptive gone":  _log_has(log, "stripped", "adaptive"),
        "beta flags gone":         _log_has(log, "stripped anthropic-beta header entirely"),
    }
    all_checks = all(checks.values())

    if status == 200 and all_checks:
        ok("Real-world combined payload → 200", "all stripping confirmed in proxy log")
    elif status == 200:
        missing = [k for k, v in checks.items() if not v]
        warn("Real-world combined payload → 200",
             f"no proxy log confirmation for: {', '.join(missing)}")
    else:
        failed_checks = [k for k, v in checks.items() if not v]
        fail("Real-world combined payload",
             f"status={status}  unconfirmed: {', '.join(failed_checks)}  "
             f"body={chunk[:120]}")


def test_zed_log():
    section("8. Zed Log")

    try:
        with open(ZED_LOG, "r", errors="replace") as f:
            lines = f.read().splitlines()
    except Exception as e:
        fail("Zed log readable", str(e))
        return

    # [PATCH] line
    patch_lines = [l for l in lines if "[PATCH]" in l and "env applied" in l]
    if patch_lines:
        last = patch_lines[-1]
        url_ok  = "ANTHROPIC_BASE_URL=http://127.0.0.1:19999" in last
        prox_ok = "HTTP_PROXY=(deleted)" in last
        if url_ok and prox_ok:
            ok("[PATCH] line correct",
               last.split("] ")[-1][:80] if "] " in last else last[-80:])
        else:
            issues = []
            if not url_ok:  issues.append("wrong ANTHROPIC_BASE_URL")
            if not prox_ok: issues.append("HTTP_PROXY not deleted")
            warn("[PATCH] line has wrong values",
                 f"{'; '.join(issues)} — last: {last[-100:]}")
    else:
        fail("[PATCH] line present",
             "never emitted — patch not loaded or Zed not restarted since patch")

    # [DEBUG-ENV] line
    debug_lines = [l for l in lines if "[DEBUG-ENV]" in l]
    if debug_lines:
        last = debug_lines[-1]
        url_ok  = 'ANTHROPIC_BASE_URL="http://127.0.0.1:19999"' in last
        prox_ok = "HTTP_PROXY=undefined" in last
        gw_ok   = "gatewayAuthMeta=false" in last
        if url_ok and prox_ok:
            gw_note = "" if gw_ok else " (⚠️  gatewayAuthMeta=true — gateway may override env)"
            ok("[DEBUG-ENV] line correct", f"URL✓ HTTP_PROXY✓{gw_note}")
        else:
            issues = []
            if not url_ok:  issues.append("wrong ANTHROPIC_BASE_URL")
            if not prox_ok: issues.append("HTTP_PROXY not undefined")
            if not gw_ok:   issues.append("gatewayAuthMeta=true")
            warn("[DEBUG-ENV] line has wrong values",
                 f"{'; '.join(issues)} — last: {last[-120:]}")
    else:
        warn("[DEBUG-ENV] line not seen",
             "only emitted on session/new — start the agent panel once and re-run")

    # Recent errors (last 300 lines)
    recent = lines[-300:]

    cop = [l for l in recent if "githubcopilot" in l.lower()]
    if cop:
        warn("No Copilot routing errors in last 300 lines",
             f"{len(cop)} hit(s) — check default_model.provider in ~/.config/zed/settings.json")
    else:
        ok("No Copilot routing errors in last 300 lines")

    no_model = [l for l in recent if "No language model configured" in l]
    if no_model:
        warn("No 'No language model configured' in last 300 lines",
             f"{len(no_model)} hit(s) — ensure provider=claude-acp in Zed agent panel model picker")
    else:
        ok("No 'No language model configured' in last 300 lines")

    connect_err = [l for l in recent
                   if "Unable to connect to API" in l or "Query closed before response" in l]
    if connect_err:
        warn("No connection errors in last 300 lines",
             f"{len(connect_err)} hit(s) — check proxy log for upstream status")
    else:
        ok("No connection errors in last 300 lines")


# ── Summary ───────────────────────────────────────────────────────────────

def summary():
    passes = [r for r in _results if r[0] == "PASS"]
    fails  = [r for r in _results if r[0] == "FAIL"]
    warns  = [r for r in _results if r[0] == "WARN"]

    width = 56
    print(f"\n{BOLD('─' * (width + 4))}")
    print(BOLD("  Summary"))
    print(
        f"  {GREEN(f'PASS {len(passes):2d}')}   "
        f"{RED(f'FAIL {len(fails):2d}')}   "
        f"{YELLOW(f'WARN {len(warns):2d}')}"
    )

    if fails:
        print(f"\n{RED(BOLD('  Failed:'))}")
        for _, name, detail in fails:
            print(f"    {RED('•')} {name}")
            if detail:
                print(f"      {DIM(detail[:110])}")

    if warns:
        print(f"\n{YELLOW(BOLD('  Warnings:'))}")
        for _, name, detail in warns:
            print(f"    {YELLOW('•')} {name}")
            if detail:
                print(f"      {DIM(detail[:110])}")

    print()
    return 0 if not fails else 1


# ── Entry point ───────────────────────────────────────────────────────────

def main():
    print(BOLD(CYAN("\n═══ Zed + LiteLLM Proxy — Test Suite ════════════════")))
    print(DIM(f"  proxy={PROXY_HOST}:{PROXY_PORT}  socks={SOCKS_HOST}:{SOCKS_PORT}  log={PROXY_LOG}"))

    test_infrastructure()
    test_patches()
    test_basic()
    test_stripping()
    test_auth()
    test_streaming()
    test_real_world()
    test_zed_log()

    return summary()


if __name__ == "__main__":
    sys.exit(main())
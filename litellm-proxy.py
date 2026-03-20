#!/usr/bin/env python3
"""
Proxy: Claude CLI  -->  [this proxy on localhost]  -->  SOCKS5  -->  LiteLLM

- Rewrites x-api-key to Authorization: Bearer
- Streams SSE responses (required by Claude CLI)
- Routes through a SOCKS5 proxy (e.g. ssh -D tunnel)
- Pure stdlib Python -- zero pip dependencies

Architecture
~~~~~~~~~~~~
Claude CLI (claude) sends Anthropic-native HTTP requests:

    POST /v1/messages            (non-streaming)
    POST /v1/messages   stream   (SSE, text/event-stream)

with authentication via the ``x-api-key`` header.

The LiteLLM instance at SLAC (sdf-llm.slac.stanford.edu) exposes an
Anthropic-compatible ``/v1/messages`` endpoint but expects a standard
``Authorization: Bearer <token>`` header instead of ``x-api-key``.

This proxy sits on localhost, accepts requests from Claude CLI, rewrites the
auth header, and forwards them upstream through a SOCKS5 tunnel.

SOCKS5 tunnel
~~~~~~~~~~~~~
The SLAC LiteLLM server is only reachable from the SLAC network.  To access
it from an external machine, set up a SOCKS5 proxy via an SSH dynamic
port-forward to a SLAC host you can reach::

    ssh -D 9051 -q -N <your-slac-user>@sdf-login.slac.stanford.edu

This opens a local SOCKS5 proxy on 127.0.0.1:9051.  The proxy script then
tunnels every upstream connection through it:

    Claude CLI
      --> http://127.0.0.1:19999/v1/messages   (this proxy)
        --> SOCKS5 127.0.0.1:9051               (ssh tunnel)
          --> https://sdf-llm.slac.stanford.edu/v1/messages  (LiteLLM)

Request path mapping
~~~~~~~~~~~~~~~~~~~~
Claude CLI is configured with ``ANTHROPIC_BASE_URL=http://127.0.0.1:19999``.
It appends API paths such as ``/v1/messages`` to that base, so the proxy
receives requests like::

    POST /v1/messages HTTP/1.1
    Host: 127.0.0.1:19999
    x-api-key: <litellm-token>
    anthropic-version: 2023-06-01
    content-type: application/json

    {"model": "claude-sonnet-4", "max_tokens": 8096, "messages": [...]}

The proxy then:
  1. Strips ``x-api-key`` and adds ``Authorization: Bearer <token>``
  2. Prepends TARGET_BASE to self.path and forwards upstream.  Since the
     default TARGET_URL is ``https://sdf-llm.slac.stanford.edu`` (no /v1),
     and Claude CLI sends ``/v1/messages?beta=true``, the upstream path
     becomes ``/v1/messages?beta=true`` — exactly what LiteLLM expects.
  3. Streams the SSE response back using HTTP chunked transfer encoding

Note: Do NOT add ``/v1`` to LITELLM_TARGET — Claude CLI already includes it
in the request path.

Usage
~~~~~
1. Start your SSH SOCKS tunnel::

       ssh -D 9051 -q -N <user>@sdf-login.slac.stanford.edu

2. Start this proxy::

       python3 ~/.claude/litellm-proxy.py [OPTIONS]

3. In the shell where you run ``claude``::

       export ANTHROPIC_BASE_URL=http://127.0.0.1:19999
       export ANTHROPIC_API_KEY=<your-litellm-api-key>
       # Make sure no conflicting proxy vars are set:
       unset HTTPS_PROXY HTTP_PROXY ALL_PROXY

4. Run Claude CLI::

       claude

CLI Arguments
~~~~~~~~~~~~~
Run ``python3 litellm-proxy.py --help`` for the full list.  Key options:

  --token BEARER_TOKEN
        Bearer token for the upstream API.  Takes precedence over the
        ANTHROPIC_API_KEY environment variable and ~/.claude/settings.json.

  --fetch-token
        Obtain a fresh bearer token via OAuth2 Device Authorization Grant
        (RFC 8628).  NOT YET IMPLEMENTED — placeholder for future work.
        Mutually exclusive with --token.

  --force-model NAME
        Replace *every* client-requested model name with NAME upstream.
        Useful when the LiteLLM backend only has one model alias registered.
        Highest priority among all rewrite rules.

  --model-map FROM=TO
        Rewrite model name FROM to TO before forwarding (may be repeated).
        Example: --model-map claude-sonnet-4-6=my-sonnet-alias
        Overrides the auto hyphen-to-dot rewrite; overridden by --force-model.

  --no-model-rewrite
        Disable the automatic ``claude-X-Y -> claude-X.Y`` hyphen-to-dot
        rewrite.  Explicit --model-map entries still apply.

  --port PORT        Local listen port     (default: 19999, env: PROXY_PORT)
  --target URL       Upstream LiteLLM URL  (env: LITELLM_TARGET)
  --socks-host HOST  SOCKS5 proxy host     (default: 127.0.0.1, env: SOCKS_HOST)
  --socks-port PORT  SOCKS5 proxy port     (default: 9051, env: SOCKS_PORT)
  --no-ssl-verify    Skip TLS verification (env: SSL_VERIFY=0)

Environment variables (lower priority than CLI flags)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    LITELLM_TARGET      Upstream LiteLLM URL  (default: https://sdf-llm.slac.stanford.edu)
                        Do NOT include /v1 — Claude CLI already sends /v1/messages.
    PROXY_PORT          Local listen port     (default: 19999)
    SOCKS_HOST          SOCKS5 proxy host     (default: 127.0.0.1)
    SOCKS_PORT          SOCKS5 proxy port     (default: 9051)
    ANTHROPIC_API_KEY   Bearer token fallback (also read from ~/.claude/settings.json)
    SSL_VERIFY          Set to "0" to skip TLS verification (default: verify enabled)
"""

import argparse
import http.server
import http.client
import hashlib
import json
import socket
import ssl
import struct
import sys
import os
import time
import threading
from urllib.parse import urlparse, parse_qs, urlencode

# ── Config (module-level defaults; overridden by CLI args in main()) ────────
# Values here are seeded from environment variables so the script is still
# usable when invoked without any CLI flags.
TARGET_URL = os.environ.get("LITELLM_TARGET", "https://sdf-llm.slac.stanford.edu")
PORT       = int(os.environ.get("PROXY_PORT", "19999"))
SOCKS_HOST = os.environ.get("SOCKS_HOST", "127.0.0.1")
SOCKS_PORT = int(os.environ.get("SOCKS_PORT", "9051"))
SSL_VERIFY = os.environ.get("SSL_VERIFY", "1") != "0"
# SOCKS5 tunnelling is OFF by default.  Enabled by --socks, or implicitly when
# --socks-host / --socks-port is given, or when the SOCKS_HOST env var is set.
USE_SOCKS  = False
# API_KEY is intentionally left empty here; it is set by main() after all
# token-source precedence rules are evaluated (CLI > env > settings.json).
API_KEY    = ""

# Derived from TARGET_URL — updated by _derive_target().
TGT_SCHEME = ""
TGT_HOST   = ""
TGT_PORT   = 80
TGT_BASE   = ""


def _derive_target(url):
    """Parse *url* and refresh the TGT_* module globals."""
    global TGT_SCHEME, TGT_HOST, TGT_PORT, TGT_BASE
    p = urlparse(url)
    TGT_SCHEME = p.scheme
    TGT_HOST   = p.hostname
    TGT_PORT   = p.port or (443 if p.scheme == "https" else 80)
    TGT_BASE   = p.path.rstrip("/")


_derive_target(TARGET_URL)

CHUNK = 4096

# ── Session ID tracking ────────────────────────────────────────────────────
# Maps a conversation fingerprint (hash of first user message) to a short ID.
# This lets all log lines for a single Claude conversation share the same sid.
_session_map: dict = {}
_session_lock = threading.Lock()


def _get_session_id(body: bytes | None) -> str:
    """Return a short 6-char session ID derived from the conversation.

    The ID is stable across all requests in the same conversation: it is keyed
    on the *content* of the very first user message in the ``messages`` array.
    If the body cannot be parsed (non-JSON, no messages, etc.) a per-call
    random ID is used so logs are still tagged.
    """
    try:
        if body:
            obj = json.loads(body)
            msgs = obj.get("messages")
            if msgs and isinstance(msgs, list):
                # Use the first message's content as the stable fingerprint.
                first = msgs[0]
                content = first.get("content", "")
                if isinstance(content, list):
                    # Extract text from content-block arrays
                    content = "".join(
                        b.get("text", "") for b in content if isinstance(b, dict)
                    )
                key = str(content)[:512]  # cap to avoid huge keys
                digest = hashlib.sha256(key.encode("utf-8", errors="replace")).hexdigest()[:6]
                with _session_lock:
                    if digest not in _session_map:
                        _session_map[digest] = digest
                        # Prune old entries — keep at most 256 sessions in RAM
                        if len(_session_map) > 256:
                            oldest = next(iter(_session_map))
                            del _session_map[oldest]
                    return digest
    except Exception:
        pass
    # Fallback: random 6-char ID for this request only
    import secrets
    return secrets.token_hex(3)


# ── Model name rewriting ───────────────────────────────────────────────────
# All three of the variables below are populated from CLI args inside main().

# Unconditional override: every client-requested model is replaced with this
# value.  None means disabled.
_FORCE_MODEL = None

# Explicit per-name map.  Keys are the names the client sends; values are the
# names forwarded upstream.  Takes precedence over the auto rewrite but is
# itself overridden by _FORCE_MODEL.
#
# Pre-seeded with known versioned aliases that LiteLLM registers without the
# date suffix.  CLI --model-map entries are merged on top and can override
# these defaults.
_MODEL_MAP = {
    # Versioned aliases: strip date suffixes that LiteLLM doesn't register.
    # Keys are the hyphenated names Claude CLI sends; the auto hyphen-to-dot
    # rewrite runs after this map, so dotted-key entries are not needed here.
    "claude-haiku-4-5-20251001":  "claude-haiku-4.5",
    "claude-sonnet-4-20250514":   "claude-sonnet-4",
    "claude-sonnet-4-5-20251022": "claude-sonnet-4.5",
    "claude-sonnet-4-6-20260101": "claude-sonnet-4.6",
    "claude-opus-4-20250514":     "claude-opus-4",
    "claude-opus-4-5-20251101":   "claude-opus-4.5",
    "claude-opus-4-6-20260101":   "claude-opus-4.6",
}        # type: dict[str, str]

# When True, the automatic ``claude-X-Y -> claude-X.Y`` hyphen-to-dot
# rewrite is skipped.  Explicit _MODEL_MAP entries still apply.
_NO_AUTO_REWRITE = False

import re as _re

_MODEL_RE = _re.compile(
    r'^(claude-(?:sonnet|opus|haiku)-\d+)-(\d+)(.*)$'
)


def rewrite_model_name(name):
    """Rewrite *name* for LiteLLM compatibility.

    Priority (highest first):

    1. ``--force-model NAME``  — unconditional override; every request uses NAME.
    2. ``--model-map FROM=TO`` — exact-match explicit remapping (repeatable).
                                 Also covers the pre-seeded _MODEL_MAP defaults
                                 (e.g. ``claude-haiku-4-5-20251001`` ->
                                 ``claude-haiku-4.5``).
    3. Auto hyphen-to-dot     — e.g. ``claude-sonnet-4-6`` -> ``claude-sonnet-4.6``.
                                Disabled by ``--no-model-rewrite``.
    """
    # 1. Unconditional override
    if _FORCE_MODEL is not None:
        if _FORCE_MODEL != name:
            sys.stderr.write("[proxy] force-model: %s -> %s\n" % (name, _FORCE_MODEL))
            sys.stderr.flush()
        return _FORCE_MODEL

    # 2. Explicit map
    if name in _MODEL_MAP:
        mapped = _MODEL_MAP[name]
        sys.stderr.write("[proxy] model-map: %s -> %s\n" % (name, mapped))
        sys.stderr.flush()
        return mapped

    # 3. Auto hyphen-to-dot
    if not _NO_AUTO_REWRITE:
        m = _MODEL_RE.match(name)
        if m:
            rewritten = "%s.%s%s" % (m.group(1), m.group(2), m.group(3))
            sys.stderr.write("[proxy] model rewrite: %s -> %s\n" % (name, rewritten))
            sys.stderr.flush()
            return rewritten

    return name


# ── API key loading ────────────────────────────────────────────────────────

def _load_api_key():
    """Load bearer token from ANTHROPIC_API_KEY env or ~/.claude/settings.json.

    Returns the key string, or an empty string if neither source has one.
    This function is used as the *last* fallback inside main(); callers
    should check env / CLI args first.
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    try:
        import pathlib
        settings = json.loads(
            pathlib.Path.home().joinpath(".claude", "settings.json").read_text()
        )
        key = settings.get("env", {}).get("ANTHROPIC_API_KEY", "")
    except Exception:
        pass
    return key


# ── Device-flow token fetch (stub) ─────────────────────────────────────────

def fetch_token_device_flow():
    """Obtain a bearer token via OAuth2 Device Authorization Grant (RFC 8628).

    THIS IS A STUB — the actual network calls are not yet implemented.

    When implemented, the flow will proceed as follows:

    Step 1 — Read configuration
        Load ``client_id``, ``device_auth_url``, ``token_url``, and
        optionally ``scope`` from a ``device_flow`` block in
        ``~/.claude/settings.json``::

            {
              "device_flow": {
                "client_id":       "...",
                "device_auth_url": "https://auth.example.com/oauth/device/code",
                "token_url":       "https://auth.example.com/oauth/token",
                "scope":           "openid offline_access"
              }
            }

    Step 2 — Request device & user codes
        POST to ``device_auth_url`` with ``client_id`` (and ``scope`` if
        provided).  The server responds with::

            {
              "device_code":      "...",
              "user_code":        "ABCD-1234",
              "verification_uri": "https://auth.example.com/activate",
              "expires_in":       600,
              "interval":         5
            }

    Step 3 — Prompt the user
        Print the ``user_code`` and ``verification_uri`` to stderr so the
        user knows where to complete authorization.  Optionally open the
        URI in the default browser.

    Step 4 — Poll the token endpoint
        Every ``interval`` seconds, POST to ``token_url`` with
        ``device_code`` and ``grant_type=urn:ietf:params:oauth:grant-type:device_code``.
        Possible responses:

        - ``authorization_pending`` — keep polling.
        - ``slow_down``             — increase the polling interval by 5 s.
        - ``access_token`` present  — success; return the token.
        - ``expired_token``         — raise an error.

    Step 5 — Persist (optional)
        Write the ``access_token`` (and ``refresh_token`` if present) back
        to ``~/.claude/settings.json`` under ``env.ANTHROPIC_API_KEY`` so
        that subsequent proxy invocations do not require re-authentication.

    Returns
    -------
    str
        The ``access_token`` obtained from the authorization server.

    Raises
    ------
    NotImplementedError
        Always, until this stub is implemented.
    """
    raise NotImplementedError(
        "\n"
        "--fetch-token: device flow is not yet implemented.\n"
        "\n"
        "To authenticate, use one of the following alternatives:\n"
        "  --token <bearer-token>                 (CLI flag)\n"
        "  export ANTHROPIC_API_KEY=<token>       (environment variable)\n"
        "  ~/.claude/settings.json                (env.ANTHROPIC_API_KEY key)\n"
    )


# Fields not understood by older LiteLLM deployments that cause nginx 400
_STRIP_BODY_FIELDS = ("context_management", "output_config")

# Query parameters that SLAC's nginx rejects with 400 Bad Request
# The claude binary appends ?beta=true when it uses beta features, but
# SLAC's nginx does not accept query strings on /v1/messages.
_STRIP_QUERY_PARAMS = frozenset({"beta"})

# Flags in anthropic-beta that Claude Code *requires* for correct operation.
# These are passed through to LiteLLM unchanged.  Everything else is stripped
# so that SLAC's nginx / older LiteLLM versions don't return 400.
#
# claude-code-20250219   — activates Claude Code agentic behaviour + tool-use
#                          response shapes.  Without it the model emits a
#                          different output format that Claude Code's SSE parser
#                          cannot handle, causing the agent to stall silently.
_ANTHROPIC_BETA_PASSTHROUGH = frozenset({
    "claude-code-20250219",
})


def _strip_cache_control_from_blocks(content):
    """Remove cache_control from every content block in a list.

    The claude binary annotates prompt-caching blocks with
    ``cache_control: {type: "ephemeral"}``.  Older LiteLLM deployments
    (and their nginx frontends) don't understand this field and return 400.
    Since we already drop the ``anthropic-beta: prompt-caching-*`` header
    entirely, the annotations are orphaned anyway — safe to strip.
    Returns (new_content, changed_bool).
    """
    if not isinstance(content, list):
        return content, False
    changed = False
    cleaned = []
    for block in content:
        if isinstance(block, dict) and "cache_control" in block:
            block = {k: v for k, v in block.items() if k != "cache_control"}
            changed = True
        cleaned.append(block)
    return cleaned, changed


def maybe_rewrite_body(body):
    """Rewrite request body for LiteLLM compatibility.

    Changes applied:
    - Model name: rewrite via rewrite_model_name() (force / map / auto-dot)
    - Strip fields unknown to older LiteLLM: context_management, output_config
    - Adaptive thinking: {"type": "adaptive"} -> removed entirely
      (LiteLLM only understands {"type": "enabled", "budget_tokens": N})
    - Strip cache_control from system / message content blocks (prompt-caching
      annotations that SLAC's LiteLLM/nginx rejects with 400 Bad Request)
    """
    if not body:
        return body
    try:
        obj = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return body
    if not isinstance(obj, dict):
        return body

    changed = False

    # 1. Rewrite model name
    if "model" in obj:
        original = obj["model"]
        rewritten = rewrite_model_name(original)
        if rewritten != original:
            obj["model"] = rewritten
            changed = True

    # 2. Strip unsupported top-level fields
    for field in _STRIP_BODY_FIELDS:
        if field in obj:
            del obj[field]
            sys.stderr.write("[proxy] stripped unsupported body field: %s\n" % field)
            sys.stderr.flush()
            changed = True

    # 3. Normalize thinking field
    thinking = obj.get("thinking")
    if isinstance(thinking, dict):
        t_type = thinking.get("type")
        if t_type == "adaptive":
            # "adaptive" is a newer SDK format; remove it so LiteLLM
            # doesn't choke — it's semantically equivalent to "don't force
            # thinking" so removing it is safe.
            del obj["thinking"]
            sys.stderr.write("[proxy] stripped unsupported thinking type=adaptive\n")
            sys.stderr.flush()
            changed = True
        elif t_type == "enabled" and not thinking.get("budget_tokens"):
            # budget_tokens is required when type=enabled
            obj["thinking"]["budget_tokens"] = 16000
            sys.stderr.write("[proxy] added missing thinking.budget_tokens=16000\n")
            sys.stderr.flush()
            changed = True

    # 4. Strip cache_control from system and message content blocks.
    #    claude binary v2.1.76+ annotates prompt-caching blocks with
    #    cache_control: {type: "ephemeral"}.  We already strip the
    #    anthropic-beta prompt-caching header, so these annotations are
    #    orphaned and cause a plain nginx 400 from SLAC LiteLLM.
    if isinstance(obj.get("system"), list):
        cleaned, c = _strip_cache_control_from_blocks(obj["system"])
        if c:
            obj["system"] = cleaned
            sys.stderr.write("[proxy] stripped cache_control from system block(s)\n")
            sys.stderr.flush()
            changed = True
    msgs_stripped = 0
    for msg in obj.get("messages", []):
        if isinstance(msg, dict) and isinstance(msg.get("content"), list):
            cleaned, c = _strip_cache_control_from_blocks(msg["content"])
            if c:
                msg["content"] = cleaned
                msgs_stripped += 1
                changed = True
    if msgs_stripped:
        sys.stderr.write("[proxy] stripped cache_control from %d message(s)\n" % msgs_stripped)
        sys.stderr.flush()

    if changed:
        return json.dumps(obj).encode("utf-8")
    return body


def maybe_rewrite_headers(hdrs):
    """Strip headers that older LiteLLM deployments reject.

    - anthropic-beta: flags not in _ANTHROPIC_BETA_PASSTHROUGH are removed.
      SLAC's LiteLLM returns nginx 400 for unrecognised flags, but
      claude-code-20250219 *must* be forwarded — without it the model
      produces a different SSE output shape that Claude Code cannot parse,
      causing the agent to stall.
    - anthropic-dangerous-direct-browser-access: CORS-bypass header added
      by the SDK for browser contexts; meaningless (and WAF-triggering)
      when talking to LiteLLM.
    """
    for hk in list(hdrs.keys()):
        lo = hk.lower()
        if lo == "anthropic-dangerous-direct-browser-access":
            del hdrs[hk]
            sys.stderr.write("[proxy] stripped header: %s\n" % hk)
            sys.stderr.flush()
        elif lo == "anthropic-beta":
            flags = [b.strip() for b in hdrs[hk].split(",") if b.strip()]
            kept    = [f for f in flags if f in _ANTHROPIC_BETA_PASSTHROUGH]
            dropped = [f for f in flags if f not in _ANTHROPIC_BETA_PASSTHROUGH]
            del hdrs[hk]
            if kept:
                hdrs[hk] = ", ".join(kept)
                sys.stderr.write("[proxy] anthropic-beta kept: %s\n" % ", ".join(kept))
                sys.stderr.flush()
            if dropped:
                sys.stderr.write("[proxy] anthropic-beta dropped: %s\n" % ", ".join(dropped))
                sys.stderr.flush()

    return hdrs


# ── SOCKS5 helper (RFC 1928) ───────────────────────────────────────────────

def socks5_connect(dest_host, dest_port, proxy_host=None, proxy_port=None, timeout=10):
    """Open a TCP socket to dest_host:dest_port via a SOCKS5 proxy.

    ``proxy_host`` and ``proxy_port`` default to the module-level
    ``SOCKS_HOST`` / ``SOCKS_PORT`` globals so that changes made by
    ``main()`` after argument parsing are always picked up at call time.
    Using ``None`` as the sentinel (rather than the globals directly as
    default-argument values) avoids the Python gotcha where default
    arguments are evaluated once at function-definition time.
    """
    if proxy_host is None:
        proxy_host = SOCKS_HOST
    if proxy_port is None:
        proxy_port = SOCKS_PORT

    sock = socket.create_connection((proxy_host, proxy_port), timeout=timeout)
    # Greeting: version=5, 1 auth method, method=0 (no auth)
    sock.sendall(b"\x05\x01\x00")
    resp = sock.recv(2)
    if resp != b"\x05\x00":
        sock.close()
        raise ConnectionError("SOCKS5 handshake failed (auth): %r" % resp)
    # Connect request
    host_bytes = dest_host.encode("ascii")
    req = (b"\x05\x01\x00\x03"
           + bytes([len(host_bytes)])
           + host_bytes
           + struct.pack("!H", dest_port))
    sock.sendall(req)
    # Read reply header (4 bytes minimum)
    head = sock.recv(4)
    if len(head) < 4 or head[1] != 0:
        sock.close()
        raise ConnectionError("SOCKS5 connect failed: status=%r" % (head[1:2],))
    atyp = head[3]
    if atyp == 1:      # IPv4
        sock.recv(4 + 2)
    elif atyp == 3:    # Domain
        dlen = sock.recv(1)[0]
        sock.recv(dlen + 2)
    elif atyp == 4:    # IPv6
        sock.recv(16 + 2)
    return sock


def make_upstream():
    """Return an http.client connection to the upstream, optionally via SOCKS5.

    When ``USE_SOCKS`` is True the connection is tunnelled through the SOCKS5
    proxy at ``SOCKS_HOST:SOCKS_PORT`` (enable with ``--socks``).
    When ``USE_SOCKS`` is False (the default) a direct TCP connection is made.
    """
    if USE_SOCKS:
        raw = socks5_connect(TGT_HOST, TGT_PORT)
        # socks5_connect uses a short timeout (10 s) for the handshake itself.
        # Extend it now so that slow LLM responses don't hit a 10-second read
        # timeout during conn.getresponse() / resp.read().  The conn.sock
        # override below bypasses http.client's own timeout= setting, so we
        # must set it on the raw socket directly.
        raw.settimeout(300)
        if TGT_SCHEME == "https":
            ctx = ssl.create_default_context()
            if not SSL_VERIFY:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            wrapped = ctx.wrap_socket(raw, server_hostname=TGT_HOST)
            conn = http.client.HTTPSConnection(TGT_HOST, TGT_PORT, context=ctx, timeout=300)
            conn.sock = wrapped
        else:
            conn = http.client.HTTPConnection(TGT_HOST, TGT_PORT, timeout=300)
            conn.sock = raw
    else:
        # Direct connection — no SOCKS tunnel.
        if TGT_SCHEME == "https":
            ctx = ssl.create_default_context()
            if not SSL_VERIFY:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            conn = http.client.HTTPSConnection(TGT_HOST, TGT_PORT, context=ctx, timeout=300)
        else:
            conn = http.client.HTTPConnection(TGT_HOST, TGT_PORT, timeout=300)
    return conn


# ── HTTP handler ───────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):
    timeout = 300
    protocol_version = "HTTP/1.1"

    def _proxy(self):
        # Strip query params that SLAC's nginx rejects (e.g. ?beta=true -> 400)
        _parsed_req = urlparse(self.path)
        _req_qs_in = parse_qs(_parsed_req.query)
        _stripped_qp = sorted(set(_req_qs_in) & _STRIP_QUERY_PARAMS)
        _req_qs_out = {k: v for k, v in _req_qs_in.items() if k not in _STRIP_QUERY_PARAMS}
        _clean_path = _parsed_req.path + (
            "?" + urlencode(_req_qs_out, doseq=True) if _req_qs_out else ""
        )
        path = TGT_BASE + _clean_path
        clen = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(clen) if clen else None

        # Compute a stable session ID for this conversation
        sid = _get_session_id(body)
        _P = "[proxy:%s]" % sid  # log prefix for all lines in this request

        if _stripped_qp:
            sys.stderr.write("%s stripped query params: %s\n" % (_P, ", ".join(_stripped_qp)))
            sys.stderr.flush()

        # Log incoming request
        stream_req = (
            self.headers.get("Accept", "") == "text/event-stream"
            or (body and b'"stream":true' in (body if isinstance(body, bytes) else body.encode()))
        )
        sys.stderr.write("%s %s %s (len=%d stream=%s)\n" % (
            _P, self.command, self.path, clen, stream_req))
        sys.stderr.flush()

        # Rewrite model names in JSON request bodies
        body = maybe_rewrite_body(body)
        # Update Content-Length after potential rewrite
        if body and isinstance(body, bytes):
            clen = len(body)

        hdrs = {}
        api_key = None
        for k, v in self.headers.items():
            lo = k.lower()
            if lo in ("host", "transfer-encoding", "content-length", "accept-encoding"):
                continue
            if lo == "x-api-key":
                api_key = v
                continue
            if lo == "authorization":
                # Capture the incoming Authorization: Bearer value so we can
                # pass it through when no startup --token was configured.
                # We still strip the header here and re-add it below as a
                # single canonical Authorization: Bearer to avoid duplicates
                # that nginx rejects with 400.
                if v.lower().startswith("bearer "):
                    api_key = api_key or v[len("bearer "):].strip()
                continue
            hdrs[k] = v
        if not api_key and API_KEY:
            api_key = API_KEY
        if api_key:
            hdrs["Authorization"] = "Bearer " + api_key
        hdrs["Host"] = (
            TGT_HOST if TGT_PORT in (80, 443)
            else "%s:%d" % (TGT_HOST, TGT_PORT)
        )
        # Strip LiteLLM-incompatible headers
        hdrs = maybe_rewrite_headers(hdrs)
        if body:
            hdrs["Content-Length"] = str(
                len(body) if isinstance(body, bytes) else len(body.encode("utf-8"))
            )

        # ── Upstream request with retry on 504 / connection error ──────────
        # 504 means nginx received the request but the LiteLLM backend timed
        # out generating a response (common with large context windows).
        # Retry up to _RETRIES times with a short back-off before giving up.
        _RETRIES = 2
        conn = None
        resp = None
        streaming = False
        last_exc = None
        for _attempt in range(_RETRIES + 1):
            # Close any connection left open by a previous (failed) attempt.
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
            try:
                conn = make_upstream()
                lbl = "" if _attempt == 0 else " (retry %d/%d)" % (_attempt, _RETRIES)
                sys.stderr.write("%s -> upstream %s %s%s\n" % (_P, self.command, path, lbl))
                sys.stderr.flush()
                conn.request(self.command, path, body=body, headers=hdrs)
                resp = conn.getresponse()
                ct = resp.getheader("Content-Type", "")
                streaming = "text/event-stream" in ct
                sys.stderr.write("%s <- upstream %d %s (stream=%s)\n" % (
                    _P, resp.status, ct[:60], streaming))
                sys.stderr.flush()

                if resp.status == 504 and _attempt < _RETRIES:
                    resp.read()  # drain body so the connection can be reused/closed cleanly
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = None
                    sys.stderr.write(
                        "%s 504 gateway timeout on attempt %d/%d — retrying in 5s\n"
                        % (_P, _attempt + 1, _RETRIES + 1)
                    )
                    sys.stderr.flush()
                    time.sleep(5)
                    continue  # next iteration opens a fresh connection

                last_exc = None
                break  # usable response (2xx, 4xx, or final 5xx)

            except Exception as exc:
                last_exc = exc
                if _attempt < _RETRIES:
                    sys.stderr.write(
                        "%s connect error on attempt %d/%d: %s — retrying in 3s\n"
                        % (_P, _attempt + 1, _RETRIES + 1, exc)
                    )
                    sys.stderr.flush()
                    time.sleep(3)
                    continue
                # Final attempt exhausted — fall through to error handler below.

        if last_exc is not None:
            self.log_error("upstream: %s", last_exc)
            try:
                body_j = json.dumps(
                    {"error": {"type": "proxy_error", "message": str(last_exc)}}
                ).encode()
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body_j)))
                self.close_connection = True
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body_j)
            except Exception:
                pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            return

        try:
            # Log request and response details on non-2xx for debugging
            if resp.status >= 300:
                body_snippet = ""
                if body:
                    raw = body if isinstance(body, bytes) else body.encode()
                    body_snippet = raw[:2000].decode("utf-8", errors="replace")
                    # Dump full request body to file for inspection
                    try:
                        dump_path = "/tmp/proxy_debug_request_%d.json" % int(time.time())
                        with open(dump_path, "wb") as _df:
                            _df.write(raw)
                        sys.stderr.write("%s DUMPED full request body (%d bytes) to %s\n"
                                         % (_P, len(raw), dump_path))
                    except Exception as _de:
                        sys.stderr.write("%s failed to dump request body: %s\n" % (_P, _de))
                sys.stderr.write("%s REQ PATH: %s\n" % (_P, path))
                sys.stderr.write("%s REQ HEADERS:\n" % _P)
                for hk, hv in hdrs.items():
                    if hk.lower() == "authorization":
                        sys.stderr.write("%s   %s: Bearer <redacted>\n" % (_P, hk))
                    else:
                        sys.stderr.write("%s   %s: %s\n" % (_P, hk, hv[:200]))
                sys.stderr.write("%s REQ BODY (first 2000 chars): %s\n" % (_P, body_snippet))
                sys.stderr.flush()

            self.send_response_only(resp.status)
            skip = {
                "connection", "keep-alive", "transfer-encoding",
                "proxy-authenticate", "proxy-authorization",
                "te", "trailers", "upgrade",
            }
            for k, v in resp.getheaders():
                if k.lower() not in skip:
                    self.send_header(k, v)

            # Log upstream error response body for debugging
            if resp.status >= 300 and not streaming:
                err_body = resp.read()
                sys.stderr.write("%s UPSTREAM %d RESPONSE BODY (%d bytes): %s\n" % (
                    _P, resp.status, len(err_body),
                    err_body[:2000].decode("utf-8", errors="replace")))
                sys.stderr.flush()
                # Tell the HTTP/1.1 keep-alive loop not to read another request —
                # the client will have closed the socket after seeing this error.
                self.close_connection = True
                self.send_header("Connection", "close")
                self.send_header("Content-Length", str(len(err_body)))
                self.end_headers()
                self.wfile.write(err_body)
                self.wfile.flush()
                return

            if streaming:
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                total = 0
                chunks = 0
                last_log = time.monotonic()
                _LOG_INTERVAL = 5.0   # seconds between heartbeat lines
                sys.stderr.write("%s SSE stream started for %s\n" % (_P, self.path))
                sys.stderr.flush()
                while True:
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    total += len(chunk)
                    chunks += 1
                    hx = format(len(chunk), "x")
                    self.wfile.write(hx.encode() + b"\r\n")
                    self.wfile.write(chunk + b"\r\n")
                    self.wfile.flush()
                    now = time.monotonic()
                    if now - last_log >= _LOG_INTERVAL:
                        sys.stderr.write(
                            "%s SSE streaming \u2026 %d bytes / %d chunks (%s)\n"
                            % (_P, total, chunks, self.path)
                        )
                        sys.stderr.flush()
                        last_log = now
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
                sys.stderr.write("%s SSE stream done: %d bytes / %d chunks for %s\n" % (
                    _P, total, chunks, self.path))
                sys.stderr.flush()
            else:
                data = resp.read()
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                self.wfile.flush()
                sys.stderr.write("%s sent %d bytes for %s\n" % (_P, len(data), self.path))
                sys.stderr.flush()

        except Exception as exc:
            self.log_error("send response: %s", exc)
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_HEAD = _proxy

    def log_message(self, fmt, *args):
        st = args[1] if len(args) > 1 else "-"
        sys.stderr.write("[proxy] %s %s -> %s\n" % (self.command, self.path, st))
        sys.stderr.flush()


class Threaded(http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def process_request(self, req, addr):
        threading.Thread(target=self._handle, args=(req, addr), daemon=True).start()

    def _handle(self, req, addr):
        try:
            self.finish_request(req, addr)
        except Exception:
            self.handle_error(req, addr)
        finally:
            self.shutdown_request(req)

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        # ConnectionResetError / BrokenPipeError happen when the client closes
        # the socket immediately after receiving an error response (e.g. 504).
        # The HTTP/1.1 keep-alive loop then tries to read the next request and
        # hits the closed socket — this is benign noise, not a proxy bug.
        if isinstance(exc, (ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


# ── Argument parsing ───────────────────────────────────────────────────────

def _parse_args():
    """Build and return the argument parser result."""
    p = argparse.ArgumentParser(
        prog="litellm-proxy.py",
        description="Anthropic <-> LiteLLM SOCKS5 Proxy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Environment variables (lower priority than CLI flags):\n"
            "  LITELLM_TARGET     upstream base URL\n"
            "  PROXY_PORT         local listen port\n"
            "  SOCKS_HOST         SOCKS5 proxy host\n"
            "  SOCKS_PORT         SOCKS5 proxy port\n"
            "  ANTHROPIC_API_KEY  bearer token\n"
            "  SSL_VERIFY=0       disable TLS verification\n"
        ),
    )

    # ── Authentication ────────────────────────────────────────────────────
    auth = p.add_argument_group("authentication")
    tok_ex = auth.add_mutually_exclusive_group()
    tok_ex.add_argument(
        "--token",
        metavar="BEARER_TOKEN",
        default=None,
        help=(
            "Bearer token for the upstream API.  Overrides ANTHROPIC_API_KEY "
            "env and ~/.claude/settings.json."
        ),
    )
    tok_ex.add_argument(
        "--fetch-token",
        action="store_true",
        default=False,
        help=(
            "Obtain a fresh bearer token via OAuth2 Device Authorization Grant "
            "(RFC 8628).  NOT YET IMPLEMENTED.  "
            "Mutually exclusive with --token."
        ),
    )

    # ── Model rewriting ───────────────────────────────────────────────────
    mod = p.add_argument_group("model rewriting")
    mod.add_argument(
        "--force-model",
        metavar="NAME",
        default=None,
        help=(
            "Replace every client-requested model name with NAME upstream.  "
            "Useful when the LiteLLM backend only exposes one model alias.  "
            "Takes the highest priority among all rewrite rules."
        ),
    )
    mod.add_argument(
        "--model-map",
        metavar="FROM=TO",
        action="append",
        default=[],
        dest="model_map",
        help=(
            "Rewrite model name FROM to TO before forwarding (may be repeated).  "
            "Example: --model-map claude-sonnet-4-6=my-sonnet-alias.  "
            "Overrides the auto hyphen-to-dot rewrite; overridden by --force-model."
        ),
    )
    mod.add_argument(
        "--no-model-rewrite",
        action="store_true",
        default=False,
        help=(
            "Disable the automatic claude-X-Y -> claude-X.Y hyphen-to-dot "
            "rewrite.  Explicit --model-map entries still apply."
        ),
    )

    # ── Network / proxy ───────────────────────────────────────────────────
    net = p.add_argument_group("proxy / network")
    net.add_argument(
        "--port",
        type=int,
        default=None,
        metavar="PORT",
        help=(
            "Local listen port.  "
            "(default: %s, env: PROXY_PORT)" % os.environ.get("PROXY_PORT", "19999")
        ),
    )
    net.add_argument(
        "--target",
        metavar="URL",
        default=None,
        help=(
            "Upstream LiteLLM base URL, e.g. https://sdf-llm.slac.stanford.edu.  "
            "Do NOT include /v1 — the client already sends /v1/messages.  "
            "(env: LITELLM_TARGET)"
        ),
    )
    net.add_argument(
        "--socks",
        action="store_true",
        default=False,
        help=(
            "Enable SOCKS5 tunnelling (off by default).  "
            "Also enabled implicitly when --socks-host or --socks-port is supplied, "
            "or when the SOCKS_HOST environment variable is set."
        ),
    )
    net.add_argument(
        "--socks-host",
        metavar="HOST",
        default=None,
        help=(
            "SOCKS5 proxy host; implies --socks.  "
            "(default: %s, env: SOCKS_HOST)" % os.environ.get("SOCKS_HOST", "127.0.0.1")
        ),
    )
    net.add_argument(
        "--socks-port",
        type=int,
        default=None,
        metavar="PORT",
        help=(
            "SOCKS5 proxy port; implies --socks.  "
            "(default: %s, env: SOCKS_PORT)" % os.environ.get("SOCKS_PORT", "9051")
        ),
    )
    net.add_argument(
        "--no-ssl-verify",
        action="store_true",
        default=False,
        help="Disable TLS certificate verification.  (env: SSL_VERIFY=0)",
    )

    return p.parse_args()


# ── Entry point ────────────────────────────────────────────────────────────

def main():
    global TARGET_URL, PORT, SOCKS_HOST, SOCKS_PORT, SSL_VERIFY, API_KEY, USE_SOCKS
    global _MODEL_MAP, _FORCE_MODEL, _NO_AUTO_REWRITE

    args = _parse_args()

    # ── Token resolution (highest to lowest priority) ─────────────────────
    if args.fetch_token:
        try:
            token = fetch_token_device_flow()
            token_source = "device flow"
        except NotImplementedError as exc:
            sys.stderr.write("[proxy] ERROR: %s\n" % exc)
            sys.exit(1)
    elif args.token is not None:
        token = args.token
        token_source = "--token (CLI arg)"
    elif os.environ.get("ANTHROPIC_API_KEY"):
        token = os.environ["ANTHROPIC_API_KEY"]
        token_source = "ANTHROPIC_API_KEY (env)"
    else:
        token = _load_api_key()
        token_source = (
            "~/.claude/settings.json" if token else "(none — per-request key will be used)"
        )
    API_KEY = token

    # ── Network config ────────────────────────────────────────────────────
    if args.port is not None:
        PORT = args.port
    if args.target is not None:
        TARGET_URL = args.target
        _derive_target(TARGET_URL)
    if args.socks_host is not None:
        SOCKS_HOST = args.socks_host
    if args.socks_port is not None:
        SOCKS_PORT = args.socks_port
    # SOCKS is enabled if explicitly requested, or implicitly when the caller
    # supplies --socks-host / --socks-port, or sets the SOCKS_HOST env var
    # (backward-compat for setups that relied on the env var alone).
    USE_SOCKS = (
        args.socks
        or args.socks_host is not None
        or args.socks_port is not None
        or bool(os.environ.get("SOCKS_HOST"))
    )
    if args.no_ssl_verify:
        SSL_VERIFY = False

    # ── Model rewriting config ────────────────────────────────────────────
    if args.force_model:
        _FORCE_MODEL = args.force_model

    for entry in args.model_map:
        if "=" not in entry:
            sys.stderr.write(
                "[proxy] WARNING: --model-map %r ignored (expected FROM=TO format)\n" % entry
            )
            sys.stderr.flush()
            continue
        frm, _, to = entry.partition("=")
        _MODEL_MAP[frm.strip()] = to.strip()

    if args.no_model_rewrite:
        _NO_AUTO_REWRITE = True

    # ── Startup banner ────────────────────────────────────────────────────
    sep = "=" * 62
    sys.stderr.write(sep + "\n")
    sys.stderr.write("  Anthropic <-> LiteLLM SOCKS5 Proxy\n")
    sys.stderr.write(sep + "\n")
    sys.stderr.write("  Listen:      http://127.0.0.1:%d\n" % PORT)
    if USE_SOCKS:
        sys.stderr.write("  SOCKS5:      %s:%d\n" % (SOCKS_HOST, SOCKS_PORT))
    else:
        sys.stderr.write("  SOCKS5:      disabled (direct connection)\n")
    sys.stderr.write("  Upstream:    %s\n" % TARGET_URL)
    sys.stderr.write("  SSL verify:  %s\n" % SSL_VERIFY)
    sys.stderr.write("  Token:       %s\n" % token_source)
    # Model rewriting summary
    if _FORCE_MODEL:
        sys.stderr.write("  Model:       force-override -> %s\n" % _FORCE_MODEL)
    else:
        if _MODEL_MAP:
            for frm, to in sorted(_MODEL_MAP.items()):
                sys.stderr.write("  Model-map:   %s -> %s\n" % (frm, to))
        if _NO_AUTO_REWRITE:
            sys.stderr.write("  Model:       auto hyphen->dot rewrite DISABLED\n")
        else:
            sys.stderr.write("  Model:       auto hyphen->dot rewrite enabled\n")
    sys.stderr.write(sep + "\n")
    sys.stderr.write("  export ANTHROPIC_BASE_URL=http://127.0.0.1:%d\n" % PORT)
    sys.stderr.write("  export ANTHROPIC_API_KEY=<your-litellm-key>\n")
    sys.stderr.write(sep + "\n")
    sys.stderr.flush()

    srv = Threaded(("127.0.0.1", PORT), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("\nShutting down.\n")
        srv.shutdown()


if __name__ == "__main__":
    main()

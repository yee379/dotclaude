#!/usr/bin/env python3
"""
llm-sniffer.py — Transparent HTTP proxy that logs all request/response traffic
between Claude Code and the upstream LiteLLM endpoint.

Usage:
    python3 llm-sniffer.py [--port 18080] [--upstream https://sdf-llm.slac.stanford.edu]

Then set ANTHROPIC_BASE_URL=http://127.0.0.1:18080 in settings.json or shell ENV.
"""

import argparse
import datetime
import json
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ANSI colors
C_RESET = "\033[0m"
C_CYAN = "\033[36m"
C_YELLOW = "\033[33m"
C_GREEN = "\033[32m"
C_RED = "\033[31m"
C_DIM = "\033[2m"
C_BOLD = "\033[1m"

request_counter = 0
counter_lock = threading.Lock()


def timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def truncate(s, maxlen=200):
    if len(s) <= maxlen:
        return s
    return s[:maxlen] + f"... ({len(s)} bytes total)"


def pretty_json(data):
    try:
        parsed = json.loads(data)
        return json.dumps(parsed, indent=2)
    except (json.JSONDecodeError, TypeError):
        return data


class SnifferHandler(BaseHTTPRequestHandler):
    upstream = "https://sdf-llm.slac.stanford.edu"
    verbose = False

    def log_message(self, format, *args):
        # suppress default logging
        pass

    def _handle(self):
        global request_counter
        with counter_lock:
            request_counter += 1
            req_id = request_counter

        ts = timestamp()
        method = self.command
        path = self.path
        upstream_url = f"{self.upstream}{path}"

        # --- Log request ---
        print(f"\n{C_BOLD}{C_CYAN}{'='*72}{C_RESET}")
        print(f"{C_BOLD}[{ts}] #{req_id} {C_YELLOW}{method} {path}{C_RESET}")
        print(f"{C_DIM}  → {upstream_url}{C_RESET}")

        # Headers
        print(f"\n  {C_BOLD}Request Headers:{C_RESET}")
        redacted_headers = {}
        for key, value in self.headers.items():
            display_value = value
            key_lower = key.lower()
            if key_lower in ("authorization", "x-api-key", "anthropic-api-key"):
                if len(value) > 20:
                    display_value = value[:10] + "..." + value[-10:]
                redacted_headers[key] = display_value
            else:
                redacted_headers[key] = value
            print(f"    {C_GREEN}{key}{C_RESET}: {display_value}")

        # Body
        content_length = int(self.headers.get("Content-Length", 0))
        request_body = b""
        if content_length > 0:
            request_body = self.rfile.read(content_length)
            body_str = request_body.decode("utf-8", errors="replace")
            print(f"\n  {C_BOLD}Request Body:{C_RESET}")
            if self.verbose:
                print(f"    {pretty_json(body_str)}")
            else:
                print(f"    {truncate(body_str, 500)}")

            # Highlight model name if present
            try:
                body_json = json.loads(body_str)
                if "model" in body_json:
                    print(f"\n  {C_BOLD}{C_YELLOW}  model: {body_json['model']}{C_RESET}")
            except (json.JSONDecodeError, TypeError):
                pass

        # --- Forward to upstream ---
        req_headers = dict(self.headers)
        # Remove hop-by-hop headers
        for h in ("Host", "Transfer-Encoding"):
            req_headers.pop(h, None)

        try:
            upstream_req = Request(
                upstream_url,
                data=request_body if request_body else None,
                headers=req_headers,
                method=method,
            )
            response = urlopen(upstream_req, timeout=60)
            status = response.status
            resp_headers = dict(response.headers)
            resp_body = response.read()

        except HTTPError as e:
            status = e.code
            resp_headers = dict(e.headers)
            resp_body = e.read()

        except URLError as e:
            print(f"\n  {C_RED}UPSTREAM ERROR: {e.reason}{C_RESET}")
            self.send_error(502, f"Upstream error: {e.reason}")
            return

        except Exception as e:
            print(f"\n  {C_RED}PROXY ERROR: {e}{C_RESET}")
            self.send_error(502, str(e))
            return

        # --- Log response ---
        ts2 = timestamp()
        status_color = C_GREEN if 200 <= status < 300 else C_RED if status >= 400 else C_YELLOW
        print(f"\n  {C_BOLD}[{ts2}] Response: {status_color}{status}{C_RESET}")

        print(f"\n  {C_BOLD}Response Headers:{C_RESET}")
        for key, value in resp_headers.items():
            print(f"    {C_GREEN}{key}{C_RESET}: {value}")

        resp_body_str = resp_body.decode("utf-8", errors="replace")
        is_streaming = "text/event-stream" in resp_headers.get("Content-Type", "")

        if is_streaming:
            lines = resp_body_str.split("\n")
            event_count = sum(1 for l in lines if l.startswith("data:"))
            print(f"\n  {C_BOLD}Response Body:{C_RESET} (SSE stream, {event_count} data events)")
            if self.verbose:
                for line in lines[:50]:
                    if line.strip():
                        print(f"    {line}")
                if len(lines) > 50:
                    print(f"    ... ({len(lines)} lines total)")
            else:
                # Show first and last data events
                data_lines = [l for l in lines if l.startswith("data:")]
                if data_lines:
                    print(f"    {truncate(data_lines[0], 200)}")
                    if len(data_lines) > 1:
                        print(f"    ...")
                        print(f"    {truncate(data_lines[-1], 200)}")
        else:
            print(f"\n  {C_BOLD}Response Body:{C_RESET}")
            if self.verbose:
                print(f"    {pretty_json(resp_body_str)}")
            else:
                print(f"    {truncate(resp_body_str, 500)}")

            # Highlight error messages
            try:
                resp_json = json.loads(resp_body_str)
                if "error" in resp_json:
                    print(f"\n  {C_RED}{C_BOLD}  ERROR: {resp_json['error']}{C_RESET}")
            except (json.JSONDecodeError, TypeError):
                pass

        print(f"{C_DIM}{'─'*72}{C_RESET}")

        # --- Send response back to client ---
        self.send_response(status)
        # Forward response headers, skip hop-by-hop
        skip_headers = {"transfer-encoding", "connection", "keep-alive"}
        for key, value in resp_headers.items():
            if key.lower() not in skip_headers:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(resp_body)))
        self.end_headers()
        self.wfile.write(resp_body)

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_PUT(self):
        self._handle()

    def do_DELETE(self):
        self._handle()

    def do_PATCH(self):
        self._handle()

    def do_OPTIONS(self):
        self._handle()

    def do_HEAD(self):
        self._handle()


def main():
    parser = argparse.ArgumentParser(
        description="HTTP proxy that logs Claude Code ↔ LiteLLM traffic"
    )
    parser.add_argument(
        "--port", "-p", type=int, default=18080,
        help="Local port to listen on (default: 18080)"
    )
    parser.add_argument(
        "--upstream", "-u", default="https://sdf-llm.slac.stanford.edu",
        help="Upstream LiteLLM URL (default: https://sdf-llm.slac.stanford.edu)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show full request/response bodies (default: truncated)"
    )
    args = parser.parse_args()

    SnifferHandler.upstream = args.upstream.rstrip("/")
    SnifferHandler.verbose = args.verbose

    server = HTTPServer(("127.0.0.1", args.port), SnifferHandler)

    print(f"{C_BOLD}llm-sniffer{C_RESET} listening on {C_CYAN}http://127.0.0.1:{args.port}{C_RESET}")
    print(f"  upstream: {C_YELLOW}{SnifferHandler.upstream}{C_RESET}")
    print(f"  verbose:  {args.verbose}")
    print()
    print(f"Set in settings.json or shell ENV:")
    print(f'  ANTHROPIC_BASE_URL=http://127.0.0.1:{args.port}')
    print()
    print(f"Press Ctrl+C to stop.")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{C_DIM}Shutting down...{C_RESET}")
        server.shutdown()


if __name__ == "__main__":
    main()
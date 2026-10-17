# Client-Side and Browser Security

Loaded at §4.11. **Trigger:** the change touches HTML or a server-side template, any
JS/TS/React/Vue component, a value stored in the browser, a cookie, CORS or CSP configuration, a
file upload that is later served, or any endpoint a browser calls with credentials.

**An XSS in an authenticated application is account takeover.** The attacker executes as the
user, inside the session, so every control verified in §4.3 is satisfied — the requests genuinely
are the user's — and no server-side check detects it.

---

## 1. Sink hunt

| Sink | Command |
|---|---|
| React | `rg -n 'dangerouslySetInnerHTML'` |
| Vue / Angular | `rg -n 'v-html\|\[innerHTML\]\|bypassSecurityTrust'` |
| DOM write | `rg -n '\.innerHTML\s*=\|\.outerHTML\s*=\|insertAdjacentHTML\|document\.write'` |
| Dynamic code | `rg -n '\beval\(\|new Function\(\|setTimeout\(\s*["'"'"']\|setInterval\(\s*["'"'"']'` |
| jQuery | `rg -n '\$\(\s*[a-z_]\|\.html\(\s*[a-z_]'` |
| URL sinks | `rg -n 'href\s*=\s*\{\|src\s*=\s*\{\|window\.location\s*=\|\.setAttribute\(\s*["'"'"']href'` |
| Escaping off | `rg -n '\|safe\b\|\{\{\{\|mark_safe\(\|Html\.Raw\|autoescape\s*(off\|False)\|SafeString'` |
| postMessage | `rg -n 'addEventListener\(\s*["'"'"']message'` |
| Upload served inline | `rg -n 'Content-Disposition\|content_type\s*=\|mimetype'` |

Per hit: **is the value user-influenced?** Trace it. Then — sanitised by a maintained library
(DOMPurify, `bleach`) or by hand? **A hand-rolled sanitiser is a finding on its own**, whether or
not you can defeat it in the review: escaping is context-dependent and block-lists rot.

Also:
- **URL sinks** accept `javascript:`, `data:`, `vbscript:` — require an allow-list of schemes,
  not a check for `javascript:`
- **SVG and HTML uploads** served from your origin execute in your origin. Separate origin, or
  `Content-Disposition: attachment` plus `X-Content-Type-Options: nosniff`
- **Client-side template/expression injection** — user data reaching an interpolated template,
  spreadsheet formula, or expression evaluator

## 2. Which XSS

- **Stored** — in the database, fires for every viewer including admins. Worst case.
- **Reflected** — in the request, needs a delivered link.
- **DOM-based** — never leaves the client (fragment, client router, `postMessage`). **Absent from
  server logs**, so undetectable after the fact. Grep the client bundle, not only the server.

## 3. Content Security Policy

`api-security.md` sets `default-src 'self'`. Verify it constrains anything:

- [ ] No `'unsafe-inline'` or `'unsafe-eval'` in `script-src` — either defeats CSP as an XSS
      control. Nonce or hash for inline scripts
- [ ] No wildcard or broad CDN host in `script-src` — one JSONP endpoint or vulnerable library on
      an allowed host restores full script execution
- [ ] `object-src 'none'` and `base-uri 'self'` — `<base>` injection redirects every relative URL
- [ ] `frame-ancestors` set (the clickjacking control; `X-Frame-Options` is the legacy fallback)
- [ ] `form-action` restricted, so an injected form cannot post credentials off-origin
- [ ] Report-only mode with a collector someone reads — and an end date. Report-only blocks
      nothing; enforce once the reports are clean
- [ ] Content that must run script (a user- or agent-authored HTML preview) renders in a document
      of its own served with a `sandbox` CSP, which gives it an opaque origin. An `srcdoc` frame
      inherits the parent's origin. The parent's `message` receiver checks `event.source` is that
      frame and `event.origin === "null"`

## 4. Token storage and cookies

- [ ] A token in `localStorage`/`sessionStorage` is readable by any XSS on the origin. `HttpOnly`
      cookie plus `SameSite` is the stronger default (`jwt-authentication.md`). A deliberate
      bearer-token-in-JS choice needs its rationale in the review
- [ ] Every cookie: `HttpOnly`, `Secure`, explicit `SameSite`
- [ ] **Scope:** `Domain=.example.com` sends the session to every subdomain, so one vulnerable or
      third-party-hosted subdomain reads it. Prefer host-only cookies and the `__Host-` prefix
- [ ] Session identifier rotated on login and any privilege change (`vuln-classes.md` 8)
- [ ] **The gateway's cookie too.** An SSO proxy's session cookie on a parent domain with no
      `SameSite` makes every sibling host same-site, and browsers' Lax-by-default does not stop a
      same-site request. Read its `Set-Cookie`, not the application's
- [ ] `Clear-Site-Data: "cookies"` clears cookies for the whole registrable domain — every sibling
      application's session. Send `"cache", "storage"` unless that is intended

## 5. CSRF

- [ ] Every **cookie-authenticated, state-changing** endpoint has a defence. `SameSite=Lax` alone
      is insufficient: it permits top-level GET-initiated navigation, is not uniformly enforced,
      and does not help against a same-site subdomain. Pair it with a synchroniser token or a
      verified `Origin`
- [ ] A JSON-content-type defence is **verified**: confirm the endpoint rejects
      `application/x-www-form-urlencoded` and `text/plain`, which bypass preflight
- [ ] `GET` requests have no side effects
- [ ] Login CSRF (victim logged into the attacker's account) and logout CSRF considered
- [ ] WebSocket handshakes validate `Origin` — CORS does not apply
- [ ] `Sec-Fetch-Site` is the simplest robust gate: refuse a state-changing request whose value is
      `same-site` or `cross-site`. The application's own pages send `same-origin`; non-browser
      clients send none. It can be enforced at a gateway for an application you cannot patch — then
      confirm no more specific route rule wins over it (`vuln-classes.md` 19)
- [ ] An application-wide guard (JSON content type, `Origin` check) is verified **per route**: one
      route registered without the dependency is the bypass

## 6. Cross-origin surface

- [ ] CORS behaviour tested on a real request, not read: origin reflected, `null` accepted, or
      `*` with credentials
- [ ] `postMessage` — sender uses an exact `targetOrigin` (never `*` with data); receiver checks
      `event.origin` against an allow-list before touching `event.data`
- [ ] `target="_blank"` carries `rel="noopener"`
- [ ] Third-party embeds sandboxed; third-party scripts carry an SRI hash (§4.7)
- [ ] Origin allow-lists are exact — not `startsWith`/`endsWith`, which
      `evil-example.com` and `example.com.evil.com` defeat

## 7. The client is not a trust boundary

- [ ] **Every** client-side validation is repeated server-side. List them and confirm
- [ ] Client-side authorisation — hidden button, filtered menu, disabled field — is not access
      control. The endpoint behind it must deny
- [ ] Grep the **built bundle** for API keys, internal hostnames, unreleased endpoint paths,
      staff-only flags
- [ ] Source maps not published to production, or access-controlled
- [ ] Data the API returns but the UI hides is disclosed (§4.8)

## 8. Content on the origin from a less-trusted source

- [ ] A server that proxies files from a less-trusted backend (a worker, a runner, a user's host,
      object storage) does not pass the backend's `Content-Type` and `Content-Disposition` through.
      Force `attachment`, `X-Content-Type-Options: nosniff` and `Content-Security-Policy: sandbox`,
      or the backend's owner serves HTML on your origin
- [ ] A `blob:` URL has the origin of the page that made it. A blob built with a server-supplied
      type (SVG, HTML, XHTML) runs its script when opened in its own tab. Give active types an
      inert type, or sanitise before making the blob
- [ ] `window.open("")` returns a same-origin `about:blank` tab; assigning an unchecked URL to its
      `location` runs `javascript:` on your origin. Parse with `new URL()` and navigate only for
      `http:` and `https:`
- [ ] Links from tool output, MCP elicitations, pull-request metadata or any third-party record are
      attacker-controlled `href`s, scheme-checked like user input

## 9. Persistence after an XSS

- [ ] Service workers and Cache Storage written by same-origin script outlive the page and the
      session, and the next account on the same browser reads them back. Naming caches per user
      does not help: script on the origin can open any cache name
- [ ] Clear them from the server when the account changes: an `HttpOnly` cookie holding an HMAC of
      the user, which script can neither read nor forge, and `Clear-Site-Data: "cache", "storage"`
      on a document response when the cookie is missing or names someone else. Treat a missing
      cookie as another user's, so evicting it only forces a clear

---

A stored XSS reachable by a lower-privileged user against a higher-privileged viewer is
`blocking`: the attack path is the privilege boundary it crosses.

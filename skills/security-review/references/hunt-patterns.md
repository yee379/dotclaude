# Hunt Patterns — Actively Search for Vulnerable Code

Load at Step 2. These are the *finding* engine — run them instead of asking "are there any
injection risks?" and hoping. Scope every command to the diff where possible
(`git diff --name-only $(git merge-base HEAD main)...HEAD`), then widen to the whole repo for
the classes marked **repo-wide**.

All patterns are Rust-regex (ripgrep) compatible — no lookahead/lookbehind. `rg` is assumed;
substitute `grep -rnE` if unavailable. **A hit is a lead, not a finding.** Every hit must be
read in context and either dismissed with a reason or promoted per `severity-rubric.md`.

---

## Injection and dangerous sinks

| Class | Command | A hit means |
|---|---|---|
| Code execution | `rg -n '\beval\(\|\bexec\(\|new Function\('` | Any user-reachable path into this is critical |
| Shell injection | `rg -n 'shell=True\|os\.system\(\|os\.popen\(\|child_process\.exec\('` | Check whether any argument derives from input; `exec` vs `execFile` matters |
| SQL string building | `rg -n 'execute\(f"\|execute\(.*%\|execute\(.*\.format\|execute\(.*\+\|query\(.*\$\{'` | Parameterisation absent — trace the variable to its source |
| Deserialization | `rg -n 'pickle\.loads?\(\|dill\.loads\|yaml\.load\(\|node-serialize\|unserialize\('` | `yaml.load` without `Loader=SafeLoader` is RCE; pickle over untrusted bytes is RCE |
| Template injection | `rg -n 'Template\(.*\+\|render_template_string\(\|from_string\('` | User-controlled template source is RCE in Jinja/ERB |
| Path traversal | `rg -n 'os\.path\.join\([^)]*(request\|param\|filename\|user)\|send_file\(\|sendFile\('` | Needs a canonicalise-then-verify-prefix check, not just sanitisation |
| XXE | `rg -n 'etree\.parse\(\|minidom\.parse\|XMLReader\|SAXParser'` | Confirm external entity resolution is disabled |

## Authorisation and tenancy

| Class | Command | A hit means |
|---|---|---|
| IDOR / BOLA | `rg -n 'def \w+\([^)]*\b(id\|_id\|uuid\|slug)\b'` then read each handler | Any handler taking a caller-supplied identifier without an ownership predicate in the query |
| Tenant bleed | `rg -n '\.query\(\|\.filter\(\|select\(\|findOne\(' -A2` | Look for the absence of `tenant_id` / `org_id` / `user_id` in multi-tenant tables |
| Mass assignment | `rg -n '\*\*(request\|payload\|body\|data)\b\|Object\.assign\(\s*\w+,\s*req\.body\|\.update\((request\|payload\|body)'` | Caller can set fields the schema never intended — `is_admin`, `balance`, `owner_id` |
| Alternate path | `rg -n '@app\.\(get\|post\)\|@router\.\|app\.use\(' -g '!*test*'` | Compare the full route inventory against routes that carry an auth dependency — the gap is the bypass |
| Debug/internal routes | `rg -n 'debug=True\|DEBUG\s*=\s*True\|/__\|/internal/\|/admin\|actuator\|pprof'` | Reachable in production? On which port/ingress? |

## Secrets and credentials

| Class | Command | A hit means |
|---|---|---|
| Hardcoded (**repo-wide**) | `rg -n '(api[_-]?key\|secret\|passwd\|password\|token\|bearer)\s*[:=]\s*["'"'"'][A-Za-z0-9_\-/+]{12,}'` | Read each — a real value, not a placeholder or test fixture |
| Known key shapes (**repo-wide**) | `rg -n 'sk-[A-Za-z0-9]{16,}\|AKIA[0-9A-Z]{16}\|ghp_[A-Za-z0-9]{20,}\|-----BEGIN [A-Z ]*PRIVATE KEY'` | Any hit is blocking until proven fake |
| Git history | `git log -p -S'PRIVATE KEY' --all \| head -50` · `gitleaks detect --no-banner` · `trufflehog git file://. --only-verified` | `.gitignore` says nothing about what is already committed — a leaked key stays leaked until rotated |
| Untracked-but-present | `git status --porcelain --ignored \| rg 'settings\|\.env\|token\|credential'` | A `git add -A` away from a leak; check `.gitignore` actually covers it |
| Timing-unsafe compare | `rg -n '==\s*\w*(token\|secret\|signature\|hmac\|digest)\|(token\|secret\|signature)\w*\s*=='` | Must be `hmac.compare_digest` / `crypto.timingSafeEqual` |

## Transport, crypto, and session

| Class | Command | A hit means |
|---|---|---|
| TLS disabled | `rg -n 'verify=False\|rejectUnauthorized\s*:\s*false\|NODE_TLS_REJECT_UNAUTHORIZED\|InsecureSkipVerify'` | Always a finding in a production path |
| Weak crypto | `rg -n '\bmd5\b\|\bsha1\(\|\bDES\b\|MODE_ECB\|random\.random\(\|Math\.random\('` | MD5/SHA1 for integrity or passwords; `random` for tokens is predictable |
| JWT misuse | `rg -n 'jwt\.decode\(\|verify\s*:\s*false\|algorithms\s*=\s*\[\s*\]\|"none"'` | `decode` without an explicit `algorithms` allowlist accepts `alg: none` or algorithm confusion |
| Cookie flags | `rg -n 'set_cookie\(\|res\.cookie\('` | Confirm `HttpOnly`, `Secure`, `SameSite` on every one |
| CORS | `rg -n 'allow_origins\|Access-Control-Allow-Origin\|cors\('` | `*` combined with credentials, or origin reflected from the request |

## Outbound requests and untrusted content

| Class | Command | A hit means |
|---|---|---|
| SSRF | `rg -n 'requests\.(get\|post\|put)\(\s*[a-z_]\|httpx\.\w+\(\s*[a-z_]\|urlopen\(\|fetch\(\s*[a-z_]\|axios\.\w+\(\s*[a-z_]'` | URL from a variable — trace it. Allowlist the host, block link-local/metadata ranges, disable redirects |
| Open redirect | `rg -n 'redirect\(\s*(request\|params\|next\|url\|return_to)\|RedirectResponse\('` | Destination must be validated against an allowlist, not just "starts with /" |
| Webhook receiver | `rg -n 'webhook\|/hooks\?/\|X-Hub-Signature\|Stripe-Signature'` | Every inbound webhook needs HMAC verification over the **raw** body, before parsing |
| Decompression bomb | `rg -n 'zipfile\|tarfile\|gzip\.open\|extractall\('` | `extractall` without a member-count/size cap and path check |
| ReDoS | `rg -n '\(\.\*\)\+\|\(\.\+\)\+\|\(\[\^.*\]\*\)\+'` | Nested quantifier on user input — a 30-char string can hang a worker |
| LLM prompt injection | `rg -n 'system_prompt\|messages\.append\|tool_choice\|tools\s*='` | Untrusted text reaching a prompt that has tool access = attacker-controlled tool calls. Check tool allowlist and output handling |

## Logging and disclosure

| Class | Command | A hit means |
|---|---|---|
| Secrets in logs | `rg -n '(logger\|log\|console)\.\w+\(.*(password\|token\|secret\|authorization\|cookie\|card\|cvv\|ssn)'` | Any hit is a finding — logs propagate to aggregators with wider access |
| Log forging | `rg -n '(logger\|log)\.\w+\(f?"[^"]*\{.*(request\|param\|input)'` | Unescaped newlines in user input let an attacker forge log entries |
| Stack traces | `rg -n 'traceback\.\|printStackTrace\|debug=True\|app\.run\('` | Confirm the production error handler returns a generic message |

## Infrastructure and pipeline

| Class | Command | A hit means |
|---|---|---|
| Pod security | `rg -n 'privileged:\s*true\|runAsUser:\s*0\|hostNetwork:\s*true\|hostPID\|hostPath\|allowPrivilegeEscalation:\s*true\|automountServiceAccountToken:\s*true'` | Each needs an explicit justification or it is a finding |
| Mutable image | `rg -n 'image:\s*[^@]+:(latest\|main\|dev\|stable)'` | Not reproducible; a rebuilt tag silently changes what runs |
| Wildcard RBAC | `rg -n 'verbs:.*\*\|resources:.*\*\|ClusterRoleBinding' -A3` | `*` on verbs or resources, or a binding to `cluster-admin` |
| CI injection | `rg -n 'pull_request_target\|workflow_run\|\$\{\{\s*github\.event\.' .github/workflows/` | `pull_request_target` + untrusted checkout = secrets to a fork. `${{ github.event.* }}` in `run:` is script injection |
| Unpinned actions | `rg -n 'uses:\s*[^@]+@(v?[0-9]+\|main\|master)$' .github/workflows/` | A moved tag runs new code with your secrets — pin to a commit SHA |
| Dependency confusion | check every internal package name resolves from the private index only; `rg -n 'extra-index-url\|registry='` | A public package of the same name can take priority |

## Client-side and browser sinks

Skip only if the change touches no template, no client bundle, and no browser-facing response.
Full treatment in `client-side-security.md` — an XSS in an authenticated app is account takeover,
so these rank alongside the server-side injection table, not below it.

| Class | Command | A hit means |
|---|---|---|
| Framework HTML sink | `rg -n 'dangerouslySetInnerHTML\|v-html\|\[innerHTML\]\|bypassSecurityTrust'` | Trace the value; sanitised by DOMPurify or by hand? A hand-rolled sanitiser is itself a finding |
| DOM write | `rg -n '\.innerHTML\s*=\|\.outerHTML\s*=\|insertAdjacentHTML\|document\.write'` | DOM-based XSS never appears in server logs — undetectable after the fact |
| Dynamic code (client) | `rg -n '\beval\(\|new Function\(\|setTimeout\(\s*["'"'"']\|setInterval\(\s*["'"'"']'` | String-argument timers are `eval` |
| Template escaping off | `rg -n '\|safe\b\|\{\{\{\|mark_safe\(\|Html\.Raw\|autoescape\s*(off\|False)'` | Escaping disabled on a path that may carry user data |
| URL sink | `rg -n 'href\s*=\s*\{\|src\s*=\s*\{\|window\.location\s*=\|location\.href\s*='` | `javascript:` / `data:` need an allow-list of schemes, not a blocklist |
| postMessage | `rg -n 'addEventListener\(\s*["'"'"']message\|postMessage\('` | Receiver must check `event.origin`; sender must not use `*` |
| Tabnabbing | `rg -n 'target=.?_blank'` | Needs `rel="noopener"` |
| Token in web storage | `rg -n 'localStorage\.\|sessionStorage\.'` | A token here is readable by any XSS on the origin |
| CSP weakened | `rg -n "unsafe-inline\|unsafe-eval\|Content-Security-Policy"` | Either directive defeats CSP as an XSS control |
| Secrets in the bundle | `rg -n '(api[_-]?key\|token\|secret)' dist/ build/ .next/ 2>/dev/null` | Grep the **built** output, not the source |
| Proxied content headers | `rg -n -i 'content-disposition\|content-type' -g '*proxy*' -g '*route*'` then read each forwarding site | A header copied from a less-trusted backend decides how the browser renders it on your origin |
| Blob with a supplied type | `rg -n 'createObjectURL\(\|new Blob\('` | Is the type taken from a response? An SVG or HTML blob runs script in a tab of its own |
| Same-origin blank tab | `rg -n "window\.open\(\s*[\"']{2}"` | Followed by a `location` assignment of an unchecked URL: `javascript:` on your origin |
| Origin storage that persists | `rg -n 'serviceWorker\.register\|caches\.open\|indexedDB\.open'` | What clears it when the account using the browser changes? |
| Origin check by prefix | `rg -n 'startsWith\(.*origin\|endsWith\(.*\(host\|origin\)\|origin\.includes\('` | `evil-example.com` and `example.com.evil.com` both pass |

## API shape and GraphQL

| Class | Command | A hit means |
|---|---|---|
| GraphQL server | `rg -n 'strawberry\|graphene\|ariadne\|ApolloServer\|makeExecutableSchema\|graphql_sync'` | Then check the four controls below explicitly |
| Introspection / playground | `rg -n 'introspection\|graphiql\|playground\|ApolloServerPluginLandingPage'` | Enabled in production publishes the whole schema, including staff-only fields |
| Depth / complexity limit | `rg -n 'depth_limit\|max_depth\|complexity\|costAnalysis\|validationRules'` | **Absence** is the finding — recursive nesting is an unauthenticated DoS |
| Batching / aliasing | `rg -n 'allowBatchedHttpRequests\|batch\|operations\s*:' ` | Aliases let one HTTP request carry N operations — count-based rate limiting is bypassed entirely (1000 login attempts, one request) |
| Resolver-level authz | `rg -n 'def resolve_\|resolvers\s*=' -A3` | Authorisation on the top-level query only leaves nested resolvers reachable via another parent |
| Bulk/export endpoint | `rg -n '/export\|/bulk\|/download\|\.csv\|stream_all\|iter_all'` | Per-record authorisation frequently absent on the bulk path that exists beside a checked single-record path |

---

## Coverage rule

Run **every** table above, or state explicitly in the output which table you skipped and why.
"Not applicable" requires a reason grounded in the code (e.g. "no outbound HTTP anywhere in the
service"), not an assumption.

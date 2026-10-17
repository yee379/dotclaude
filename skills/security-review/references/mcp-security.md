## Scope

The existing LLM tool-call item (`vuln-classes.md` class 9) covers untrusted content reaching a
model through an already-trusted tool. This file covers the tool-serving infrastructure itself — an
MCP server can be the vulnerable component even when the content flowing through it is clean.

Named CVEs to check library/server versions against: CVE-2025-6514 (mcp-remote, OAuth-proxy command
injection), CVE-2025-53109/53110 (sandbox escape and symlink bypass in the Filesystem MCP server),
CVE-2025-49596 (MCP Inspector, unauthenticated RCE), CVE-2026-0755 (gemini-mcp-tool, command
injection). A 2026 disclosure wave also found design-level weaknesses in the MCP STDIO transport
itself, not just individual server bugs — check the transport layer's patch currency, not only each
server's.

## No Default-Open Servers

```python
# BAD: any local process can call the server over STDIO/SSE with no check
@server.tool()
async def read_file(path: str): ...

# GOOD: every tool call authenticates the caller, even over a local transport
@server.tool()
async def read_file(path: str, ctx: Context):
    require_authenticated(ctx)
    ...
```

A server trusted "because it only runs locally" is still reachable by any other local process —
local execution is not an authentication boundary.

## Tool Descriptions Are Untrusted Input

- **Tool poisoning:** a tool's description contains instructions aimed at the model, not the user —
  treat tool metadata the same as any other untrusted content reaching the model.
- **Rug pull:** a server's tool definitions can change after the user approved them once —
  re-verify on every load, not only at first connection.
- **Tool shadowing:** one server's tool name or description can override or spoof another's — check
  for name collisions across configured servers, not just within one.

## Least Privilege and Confused Deputy

- Scope each MCP server's filesystem/shell/network access to the minimum the task needs — the same
  least-privilege question as any other tool integration, asked again because MCP servers are
  commonly granted broad access by default (filesystem-root, full shell).
- Where an MCP server itself authenticates via OAuth (e.g., a hosted server with its own IdP flow),
  review it against `oauth-oidc-security.md` — confused-deputy weaknesses in MCP's own OAuth flows
  are a documented pattern, not hypothetical.

## Checklist

- [ ] Every MCP server (including local STDIO/SSE) requires authentication — "runs locally" is not a
      substitute
- [ ] Server and transport versions checked against known CVEs, not just the top-level package
- [ ] Tool descriptions re-verified on each load, not trusted from first approval
- [ ] No two configured servers expose colliding tool names without an explicit precedence check
- [ ] Each server's filesystem/shell/network grant is scoped to the task, not full-machine access
- [ ] A server with its own OAuth flow reviewed against `oauth-oidc-security.md`

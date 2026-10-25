# Security Model

## Threat boundaries

Internet traffic terminates at Caddy. REST/MCP/Grafana bind to loopback only. UFW should continue exposing only 22/80/443.

## Credentials

Use four distinct trust domains:

1. HAE webhook token
2. MCP token / future OAuth access token
3. dashboard session signing secret + password hash
4. Grafana admin credentials

Never reuse them.

## Dashboard authentication

- PBKDF2-SHA256 password hashing with 600k iterations and random salt.
- Signed, expiring HttpOnly session cookie.
- SameSite=Lax and Secure in HTTPS deployments.
- Double-submit CSRF check for mutations.
- Login rate limiting by source IP.

## DDoS

Application rate limiting is **not volumetric DDoS protection**. With a public personal endpoint, the recommended production topology is:

```text
Internet -> Cloudflare proxied DNS -> Caddy -> loopback services
```

Cloudflare (or equivalent upstream) absorbs volumetric traffic; Caddy/Fail2ban/application controls handle host/application abuse. Do not claim otherwise.

Before enabling a proxy, configure trusted proxy handling deliberately so IP-based rate limiting uses only headers written by Caddy/trusted upstream.

## HAE

- bearer token
- maximum body size (25 MiB default; use HAE Batch Requests)
- JSON envelope validation
- no raw body logging
- raw path outside web root

## MCP

The initial package implements an official SDK `TokenVerifier` with one preconfigured bearer token for clients that support explicit bearer configuration. Modern MCP remote authorization is OAuth 2.1 resource-server oriented. For clients that require automatic OAuth discovery (including some hosted MCP experiences), replace the static verifier with a real IdP integration (Auth0/Keycloak/Entra/etc.) rather than rolling a custom authorization server.

This is intentionally an adapter change; tools/resources/application services do not change.

MCP transport DNS-rebinding protection remains enabled. `bemestar.example.com` and local development hosts are explicit allowlist entries. Treat an unexpected HTTP 421 from `/mcp` as a transport-security/Host configuration issue, not an authentication failure.

## LLM privacy

No data leaves the server by default. When `BEMESTAR_LLM_*` is configured, summary JSON used by `/api/v1/insights/daily` is transmitted to that configured provider. Treat provider configuration as an explicit privacy decision.

Never send raw HAE payloads to an LLM provider.

## Logs

Allowed:

- ingestion UUID
- stream
- status
- error class/message
- record counts

Forbidden:

- raw payloads
- passwords/tokens
- full session cookies
- raw GPS routes
- sensitive metric dumps

## File permissions

Recommended:

```text
/etc/bem-estar/bem-estar.env      0600 bem-estar:bem-estar
/var/lib/bem-estar                0750 bem-estar:bem-estar
/var/backups/bem-estar            0750 bem-estar:bem-estar
```

## Supply chain

- Commit `uv.lock`/resolved lock once dependency resolution is run on the connected server.
- Use `npm ci` with committed `package-lock.json` after first dashboard install.
- Keep dependency upgrades separate from feature changes.
- Do not let AI agents introduce unreviewed runtime dependencies casually.

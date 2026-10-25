# MCP Client Integration

## Transport

Public endpoint:

```text
https://bemestar.example.com/mcp
```

Transport: stateless Streamable HTTP using MCP Python SDK v2.

The MCP ASGI adapter explicitly allowlists the configured public hostname through `TransportSecuritySettings`. This is required by SDK v2 DNS-rebinding protection; do not remove it or a reverse-proxied production hostname can fail with HTTP 421 before authentication. Localhost is retained for local Inspector/testing.

## Bootstrap authentication

The repository starts in **resource-server + static bearer verifier** mode. This is appropriate for MCP clients that can explicitly attach:

```http
Authorization: Bearer <BEMESTAR_MCP_TOKEN>
```

It is deliberately a different token from the HAE webhook token.

The SDK also serves RFC 9728 protected-resource metadata at:

```text
https://bemestar.example.com/.well-known/oauth-protected-resource/mcp
```

## Hosted clients / automatic OAuth

For a hosted client that expects browser authorization/discovery, static bearer is not the final architecture. The MCP server should remain the OAuth **resource server**, while a real authorization server/IdP issues refreshable access tokens. The server-side integration point is `TokenVerifier`.

Production target:

```text
Hosted MCP client
   -> protected-resource metadata
   -> IdP authorization + refresh token
   -> Bearer access token
   -> Bem Estar MCP resource server
```

When implementing:

1. choose IdP (do not invent a bespoke auth protocol)
2. configure authorization-server metadata and `offline_access`/refresh tokens where the client requires them
3. validate token issuer, expiry, scopes and audience/resource
4. replace `StaticTokenVerifier`; do not touch MCP tools/resources
5. test each client independently
6. rotate/disable the static token when no longer needed

## Exposed tools

- `get_health_summary`
- `get_metric_history`
- `analyze_sleep`
- `analyze_training_load`
- `analyze_workouts`
- `compare_periods`
- `get_ingestion_status`
- `recompute_metrics`

`recompute_metrics` changes derived/cache state but not RAW/canonical health facts. If multi-user authorization is added later, enforce a separate compute/admin scope before keeping this tool public.

## Resources

- `bemestar://today`
- `bemestar://day/{date}`
- `bemestar://metric/{metric}`

## Prompts

- `daily_review`
- `weekly_training_review`
- `sleep_review`

## Privacy

An MCP caller can receive personal health summaries. Treat the MCP token/IdP access as sensitive. The MCP server never returns RAW payload paths and should not expose GPS route data unless an explicit future feature is reviewed.

# Upstream Sources Checked During Bootstrap

Checked on 2026-09-15.

This page records the upstream documentation consulted while designing the implementation. The
repository summarizes the facts it needs; it does not reproduce upstream prose, code or assets.
Upstream text, code and trademarks remain the property of their respective owners.

## Health Auto Export

- REST API automation guide: https://help.healthyapps.dev/en/health-auto-export/automations/rest-api/
- JSON export overview: https://help.healthyapps.dev/en/health-auto-export/export-format/
- Health Metrics JSON format: https://help.healthyapps.dev/en/health-auto-export/export-format/health-metrics/
- Workouts JSON v2 format: https://help.healthyapps.dev/en/health-auto-export/export-format/workouts/
- Deep-link automation examples: https://help.healthyapps.dev/en/health-auto-export/automations/deep-link/

Relevant facts used: REST POST, custom headers, JSON v2, Since Last Sync, Previous 7 Days, Batch Requests, standard automation headers, `data.metrics`, aggregated/unaggregated sleep structures, workout v2 structure and minute/second workout metric grouping.

## MCP

- Python SDK v2 repository/docs: https://github.com/modelcontextprotocol/python-sdk
- v2 changes: https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/whats-new.md
- Streamable HTTP: https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/transports/streamable-http.mdx
- Python SDK authorization: https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/authorization.md
- Python SDK ASGI/transport security: https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/asgi.md

Relevant facts used: v2 is stable line, `MCPServer` replaces legacy `FastMCP`, 2026-07-28 protocol support, stateless Streamable HTTP, OAuth 2.1 resource-server authorization model, resources/tools/prompts semantics, and explicit production Host/Origin allowlisting for DNS-rebinding protection.

## FastAPI

- Advanced middleware / TrustedHostMiddleware: https://fastapi.tiangolo.com/advanced/middleware/

## Observability version check

- Prometheus download page (3.14.0 stable on 2026-08-17): https://prometheus.io/download/
- Grafana download page (13.2.1 stable on 2026-09-01): https://grafana.com/grafana/download

The compose file pins those stable versions rather than `latest`.

## Caddy

- `request_body` directive: https://caddyserver.com/docs/caddyfile/directives/request_body
- Caddy request matchers: https://caddyserver.com/docs/caddyfile/matchers

Relevant fact used: Caddy 2.10+ supports matcher-scoped `request_body { max_size ... }`, returning HTTP 413 when the request body exceeds the configured maximum. The target host runs Caddy 2.11.4.

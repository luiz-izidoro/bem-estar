# Edge / Abuse / DDoS Plan

Bem Estar separates three different threats that are often incorrectly called “DDoS”:

1. **credential brute force / request abuse** — handled at application level with bounded rate limiting and strong credentials;
2. **oversized HAE request bodies** — rejected by both Caddy and FastAPI;
3. **volumetric network attacks** — must be absorbed by the hosting/network edge, not Python.

Current request path:

```text
Internet -> edge 80/443 -> Caddy -> loopback services
```

Controls included in this repository:

- REST/MCP bind only to loopback;
- Caddy is the only normal public ingress;
- login, REST and HAE rate buckets are separate;
- rate-limiter key memory is LRU-bounded;
- HAE uses a dedicated high-entropy bearer token;
- Caddy limits HAE request bodies to 25 MB;
- FastAPI independently enforces streaming body size;
- `/metrics` and Prometheus are not public;
- health RAW data is never served as static files;
- fail2ban continues to protect SSH independently.

## Optional upstream proxy/CDN

If attack volume or public exposure later justifies it, an upstream proxy/CDN such as Cloudflare can be added:

```text
Internet -> upstream proxy -> edge -> Caddy -> loopback services
```

This is **optional**, not a bootstrap dependency. It also means a third party sits in the HTTPS data path for HAE health exports, so privacy/operational trade-offs should be accepted explicitly before enabling it.

If enabled:

- never cache `/api`, `/auth`, `/mcp`, `/webhooks`, or health responses;
- do not place an interactive browser challenge on `/webhooks/hae/v2`;
- preserve the long HAE bearer token and body limits;
- use provider-native rate rules for `/auth/login`;
- do not copy provider IP ranges into this repository as a one-time static list; automate updates if origin firewall restriction is adopted.

## What the application does not claim

The in-process rate limiter is not a replacement for network DDoS mitigation. Its purpose is to make credential guessing, accidental loops, and low-volume abuse expensive while keeping memory bounded on the 4 GiB VPS.

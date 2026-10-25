# Portals, URLs and Credentials

## Production endpoint inventory

Assuming DNS is configured for `bemestar.example.com`:

| Component | URL | Authentication | Exposure |
|---|---|---|---|
| Personal Dashboard/PWA | `https://bemestar.example.com/` | Dashboard username + password | Public HTTPS |
| HAE webhook | `https://bemestar.example.com/webhooks/hae/v2` | `Authorization: Bearer <WEBHOOK_TOKEN>` | Public HTTPS |
| Legacy HAE compatibility | `https://bemestar.example.com/v1/health-auto-export` | same HAE bearer | Public HTTPS during migration |
| MCP | `https://bemestar.example.com/mcp` | `Authorization: Bearer <MCP_TOKEN>` for static-token clients | Public HTTPS |
| Grafana | `https://bemestar.example.com/grafana/` | Grafana username/password | Public HTTPS |
| Health check | `https://bemestar.example.com/healthz` | none | Public HTTPS |
| Readiness check | `https://bemestar.example.com/readyz` | none | Public HTTPS |
| REST backend | `http://127.0.0.1:8787` | internal | Server loopback only |
| MCP backend | `http://127.0.0.1:8788` | bearer | Server loopback + Caddy |
| Prometheus | `http://127.0.0.1:9090` | none | Server loopback only |
| Grafana backend | `http://127.0.0.1:3000/grafana/` | Grafana login | Server loopback + Caddy |

Prometheus is intentionally **not** exposed through Caddy. If direct Prometheus UI access is ever required, use an SSH tunnel rather than publishing it:

```bash
ssh -L 9090:127.0.0.1:9090 deploy@203.0.113.10
```

Then open `http://127.0.0.1:9090` on the client machine.

## Credential separation

Never reuse one secret for several surfaces.

| Secret | Used by | Stored on server |
|---|---|---|
| Dashboard password | human login | only PBKDF2 hash in `/etc/bem-estar/bem-estar.env` |
| Session signing secret | REST session cookies | `/etc/bem-estar/bem-estar.env` |
| HAE webhook token | iPhone HAE REST automation | `/etc/bem-estar/bem-estar.env` + iPhone HAE configuration |
| MCP token | MCP client supporting static Bearer | `/etc/bem-estar/bem-estar.env` + client configuration |
| Grafana admin password | Grafana web portal | `/etc/bem-estar/observability.env` |
| LLM API key | optional insight provider | `/etc/bem-estar/bem-estar.env` if enabled |
| SSH private key | SSH client only | **never** store in this repository or Bem Estar server config |

## Generate production credentials

From the repository root:

```bash
python3 scripts/generate_production_config.py \
  --domain bemestar.example.com \
  --username admin
```

The script prompts for the Dashboard password and creates a private local directory:

```text
generated-config/
├── bem-estar.env
├── observability.env
└── ACCESS-CREDENTIALS.txt
```

Files/directories are written with restrictive permissions and `generated-config/` is gitignored.

`ACCESS-CREDENTIALS.txt` is intentionally a **one-time transfer sheet**. Put its HAE token, MCP token and Grafana password in your password manager, then securely delete the file.

The Dashboard password is not written back in plaintext; only its PBKDF2 hash goes into `bem-estar.env`.

## Install the environment files

On the server:

```bash
sudo install -d -o root -g bem-estar -m 0750 /etc/bem-estar
sudo install -o root -g bem-estar -m 0640 generated-config/bem-estar.env /etc/bem-estar/bem-estar.env
sudo install -o root -g bem-estar -m 0640 generated-config/observability.env /etc/bem-estar/observability.env
```

Verify ownership without printing secret values:

```bash
sudo stat -c '%U %G %a %n' /etc/bem-estar/bem-estar.env /etc/bem-estar/observability.env
```

Expected:

```text
root bem-estar 640 ...
```

## HAE credential

Copy only the webhook token to HAE:

```text
Authorization
Bearer <BEMESTAR_WEBHOOK_TOKEN>
```

Do not place the Dashboard, MCP or Grafana secret in the iPhone automation.

## MCP credential

For MCP clients that support configuring an HTTP Authorization header directly:

```text
Server URL: https://bemestar.example.com/mcp
Authorization: Bearer <BEMESTAR_MCP_TOKEN>
```

The current static-token mode is a single-owner bootstrap mode. Some hosted MCP clients require an OAuth Authorization Server and cannot be configured with a static Bearer token. In that case, do **not** weaken the endpoint or make it anonymous. Add an external OAuth/OIDC provider according to `docs/14-MCP-CLIENT-INTEGRATION.md`.

## Dashboard login

```text
URL:      https://bemestar.example.com/
Username: admin
Password: the value entered during generate_production_config.py
```

Only the salted PBKDF2 hash is stored on the server.

## Grafana login

```text
URL:      https://bemestar.example.com/grafana/
Username: admin
Password: generated in ACCESS-CREDENTIALS.txt
```

Grafana sign-up and analytics reporting are disabled by the supplied Compose configuration.

## Credential rotation

### HAE token

1. Generate a new high-entropy token.
2. Change `BEMESTAR_WEBHOOK_TOKEN` in `/etc/bem-estar/bem-estar.env`.
3. `sudo systemctl restart bem-estar-rest`.
4. Replace the Authorization header in all HAE automations.
5. Trigger a manual test.

Keep the transition short because the backend intentionally accepts only one active HAE token.

### MCP token

1. Generate a new token.
2. Change `BEMESTAR_MCP_TOKEN`.
3. Restart `bem-estar-mcp`.
4. Update MCP clients.

### Dashboard password

Generate a new hash without placing the password on the command line:

```bash
python3 scripts/generate_secrets.py --password-hash-only
```

Copy only the new `BEMESTAR_DASHBOARD_PASSWORD_HASH` into the environment file and restart the REST service.

### Grafana password

Prefer changing it in Grafana after first login and then updating the protected operations record/password manager. `GF_SECURITY_ADMIN_PASSWORD` primarily bootstraps the initial admin account; do not assume changing the environment variable later resets an existing Grafana database user.

## What must never be committed

- `/etc/bem-estar/*.env`
- generated `ACCESS-CREDENTIALS.txt`
- API keys
- HAE or MCP tokens
- cookies/session tokens
- SSH private keys
- Grafana password
- RAW Apple Health payloads
- SQLite production database/backups

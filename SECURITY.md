# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.2.x | Yes |
| < 0.2 | No |

## Reporting a vulnerability

Please report vulnerabilities privately through **GitHub Security Advisories**
(the repository's **Security** tab, then **Report a vulnerability**). Do not open a public
issue for a security problem.

Include, when possible:

- affected version or commit;
- impacted component (REST API, MCP server, HAE webhook, dashboard, deployment);
- impact and attack preconditions;
- a minimal reproduction using synthetic data;
- suggested remediation, if known.

Never include real Apple Health payloads, tokens, password hashes, session cookies or other
personal data in a report.

## Scope

In scope: source code, default configuration, deployment units and compose files in this
repository.

Out of scope: vulnerabilities in third-party dependencies (report them upstream), misconfigured
hosts, compromised devices or accounts, and social engineering.

## Handling

Maintainers will acknowledge reports on a best-effort basis, validate the issue, prepare a fix
and coordinate disclosure through the advisory. No bounty or response-time SLA is offered.

## Baseline controls

- Secrets are supplied through environment files and are never committed.
- HAE and MCP use separate bearer tokens; the dashboard uses a signed HttpOnly session cookie
  with CSRF protection.
- Raw health payloads are private and must not be served by the reverse proxy.
- Production refuses to start with placeholder secrets.
- Rate limiting, request-size ceilings and bounded metric labels are enabled by default.

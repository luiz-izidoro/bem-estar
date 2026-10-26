# Publishing to GitHub

This checklist is for the repository owner. It complements [`CONTRIBUTING.md`](../CONTRIBUTING.md)
and [`SECURITY.md`](../SECURITY.md); no credential belongs in the repository.

## Repository settings

| Setting | Value |
|---|---|
| Name | `bem-estar` |
| Visibility | public |
| Default branch | `main` |
| License | MIT (detected from `LICENSE`) |
| Description | Self-hosted Apple Health ingestion, deterministic metrics, REST API, MCP and dashboard |
| Topics | `apple-health`, `health`, `mcp`, `fastapi`, `sqlite`, `self-hosted`, `privacy` |

## Before the first push

- [ ] `make check` and `./scripts/verify_release.sh` pass on the publication commit.
- [ ] `git status` is clean; no `.env`, `generated-config/`, `var/`, database, raw payload or
      personal report is staged.
- [ ] `git log` shows the intended author identity.
- [ ] `RELEASE-MANIFEST.md` matches the files in the commit (regenerate it if anything changed).
- [ ] `uv.lock` and `dashboard/package-lock.json` are committed.
- [ ] The target-server gates in [`VALIDATION.md`](../VALIDATION.md) are understood as pending.

## Push

```bash
git remote add origin https://github.com/luiz-izidoro/bem-estar.git
git push -u origin main
```

## Branch protection for `main`

- Require a pull request before merging (at least one approval for non-owners).
- Require the status checks: `Python 3.12`, `Python 3.13`, `Python 3.14`, `Dashboard`,
  `Analyze python` and `Analyze javascript-typescript`.
- Require branches to be up to date before merging.
- Require linear history and block force pushes and deletion.
- Include administrators in the rules.

## Security settings

- Enable **private vulnerability reporting** (SECURITY tab).
- Enable **secret scanning** and **push protection**.
- Enable **Dependabot alerts** and **Dependabot security updates** (the repository already
  carries `.github/dependabot.yml` for weekly version updates).
- Keep the default `GITHUB_TOKEN` permissions read-only.
- Do not grant Actions write access to repository contents; the workflows only need `contents:
  read` (CodeQL also needs `security-events: write`).

## Code-only publication

This repository intentionally does **not** publish GitHub Releases or version tags. The code on
`main` is the deliverable; use [`CHANGELOG.md`](../CHANGELOG.md) for version history.

Do not attach databases, raw payloads, generated credentials or build outputs to issues, pull
requests or repository assets.

## Post-push verification

- [ ] `CI` is green on `main` for Python 3.12, 3.13 and 3.14.
- [ ] `Dashboard` job builds successfully.
- [ ] `CodeQL` analysis completes for Python and JavaScript/TypeScript.
- [ ] README, LICENSE, NOTICE, SECURITY, CONTRIBUTING and THIRD_PARTY_NOTICES render correctly.
- [ ] Dependabot security updates remain enabled; routine version PRs are disabled.
- [ ] A test clone follows `README.md` quick start successfully.

## Never commit

- `.env` or any real environment file;
- `generated-config/` and `ACCESS-CREDENTIALS.txt`;
- `var/`, SQLite databases, raw HAE payloads, reports;
- tokens, password hashes, private keys or signing material;
- personal paths, real hostnames, IP addresses or email addresses.

## Operational gates not covered by public CI

MCP Streamable HTTP end-to-end, Caddy validation/reload, Docker Compose for
Prometheus/Grafana, real HAE traffic and off-host backup restore require a real host or device.
See [`VALIDATION.md`](../VALIDATION.md).

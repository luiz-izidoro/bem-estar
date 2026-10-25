# Changelog

## Unreleased — publication readiness

- relicensed under the MIT License (copyright holder: Bem Estar Contributors);
- removed personal, domain and infrastructure identifiers from documentation and examples;
- made lint, formatting and strict typing gates pass and added them to CI;
- added SECURITY, CONTRIBUTING, CODE_OF_CONDUCT, THIRD_PARTY_NOTICES, issue forms, pull-request
  template, Dependabot and CodeQL;
- pinned dashboard dependencies with `package-lock.json` and added `uv.lock`;
- fixed CSV parsing of `trusted_hosts`/`cors_origins` from `.env`, so the documented quick start
  works from a clean clone;
- added a screenshot-driven README with quick start, configuration, architecture and MCP usage;
- rounded deterministic insight values and added regression coverage;
- refreshed validation evidence and release metadata.

## 0.2.0 — 2026-09-15 — audited bootstrap

- hardened HAE webhook body/disk/rate behavior;
- made reconciliation correction-safe and compatible with missing HAE source provenance;
- fixed sleep waking-day assignment;
- added worker leases and stale-job recovery;
- added explicit active metric version registry and stronger metric provenance;
- reduced unnecessary historical metric rewrites;
- hardened login, deployment, backup and restore paths;
- added scheduled 180-day RAW retention;
- added production credential/config generator;
- added complete HAE, portal/credential and first-deploy runbooks;
- added Caddy webhook body limit and systemd memory/task ceilings;
- expanded regression suite to 22 tests.

## 0.1.0 — 2026-09-15 — initial bootstrap

Initial modular Bem Estar platform: HAE v2 ingestion, canonical SQLite storage, deterministic metrics, REST, MCP, React PWA, systemd/Caddy deployment and Prometheus/Grafana scaffolding.

# Resolved Decisions and Assumptions

Project assumptions and resolved decisions:

- Host: Ubuntu 26.04 LTS x86_64, 2 vCPU, 3.7 GiB RAM.
- Existing ingress: Caddy on 80/443; UFW default deny; SSH key only; root login off; fail2ban active.
- Existing deployment: loopback `:8787`, systemd hardened, `/opt/bem-estar/current`, config `/etc/bem-estar/`.
- Domain: any public hostname, for example `bemestar.example.com`.
- Deploy preference: simplest appropriate choice. Result: systemd for application, Docker only for Grafana/Prometheus.
- Database: SQLite WAL.
- Dashboard: React, PWA, bilingual PT-BR/English.
- Login: simple owner login + abuse controls; upstream DDoS proxy recommended.
- MCP: public internet, personal use, no VPN; separate auth token initially, architecture ready for OAuth IdP.
- HAE: webhook push, four primary streams, historical bootstrap + reconciliation.
- Metrics: HRV, RHR, HR, sleep, weight/body composition, activity, workouts, TRIMP, CTL/ATL/TSB, ACWR, recovery/readiness, VO2max/trends.
- Readiness: complete documented deterministic v1, versioned.
- AI: enabled as optional feature via abstract provider; deterministic fallback remains.
- Notifications: port included from start.
- Backup: included.
- Raw: compressed local retention, default one year; no automatic deletion until backup policy is proven.
- Observability: Prometheus + Grafana now.
- AI agents: repository governed by AGENTS.md and ADR/metric versioning rules.
- Git: repository initialized with a clean initial commit.
- Language: all technical/code documentation English; UI supports English and Portuguese.
- License: MIT.

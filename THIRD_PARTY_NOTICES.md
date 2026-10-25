# Third-party notices

Bem Estar is distributed under the MIT License (see [`LICENSE`](LICENSE)). It depends on
third-party software that remains under its own licenses. **No third-party source code is
vendored in this repository**; dependencies are installed from their official distributions.

This list covers direct dependencies. Transitive dependencies are resolved by `pip`/`npm` and
carry their own licenses; consult the lockfiles and package metadata for the complete graph.

## Python runtime dependencies

| Package | License |
| --- | --- |
| Alembic | MIT |
| FastAPI | MIT |
| HTTPX | BSD-3-Clause |
| MCP Python SDK | MIT |
| orjson | MPL-2.0 AND (Apache-2.0 OR MIT) |
| prometheus-client | Apache-2.0 AND BSD-2-Clause |
| Pydantic | MIT |
| pydantic-settings | MIT |
| SQLAlchemy | MIT |
| Uvicorn | BSD-3-Clause |

## Frontend dependencies

| Package | License |
| --- | --- |
| React / React DOM | MIT |
| Vite | MIT |
| @vitejs/plugin-react | MIT |
| TypeScript | Apache-2.0 |
| @types/react, @types/react-dom | MIT |

## Development-only dependencies

| Package | License |
| --- | --- |
| mypy | MIT |
| pytest | MIT |
| pytest-cov | MIT |
| Ruff | MIT |

## Runtime services and images

The deployment examples use services that are pulled at runtime and are **not** redistributed
here:

| Component | License |
| --- | --- |
| Caddy | Apache-2.0 |
| Prometheus | Apache-2.0 |
| Grafana | AGPL-3.0 |

Container images remain subject to their own terms. Review them before redistributing a
deployment.

## Documentation and product names

The documentation summarizes facts from the official documentation of Health Auto Export, the
Model Context Protocol, FastAPI, Caddy, Prometheus and Grafana. Links are recorded in
[`docs/12-SOURCES.md`](docs/12-SOURCES.md). Those projects and their documentation remain the
property of their respective authors.

Apple Health, Apple Watch, Health Auto Export, Grafana, Prometheus, Docker, Python, Node.js and
other product names are trademarks or registered trademarks of their respective owners. Their
use here is descriptive and does not imply affiliation or endorsement.

This project is independent and is not affiliated with, endorsed by, or sponsored by Apple Inc.,
Health Auto Export, or any MCP client vendor.

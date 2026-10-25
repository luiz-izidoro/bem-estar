# ADR 0001 — Modular monolith with separate interface processes

Status: Accepted
Date: 2026-09-15

## Context

A single-owner personal health platform must run reliably on 2 vCPU / ~4 GiB RAM while supporting webhook ingestion, dashboard/API, worker processing and MCP access.

## Decision

Use one repository, one canonical SQLite database and one domain/application core. Run REST, worker and MCP as separate systemd processes. Keep Grafana/Prometheus outside the application runtime.

## Alternatives considered

1. Microservices — rejected for operational and resource overhead without scaling benefit.
2. One Python process for everything — rejected because MCP/worker lifecycle failures would unnecessarily affect webhook availability.
3. Serverless — rejected because raw persistence, private state and existing VM make it less direct.

## Consequences

Simple transactions and shared contracts; independent process restart/upgrade; no distributed consistency problem. SQLite remains a single-writer constraint, acceptable for this workload.

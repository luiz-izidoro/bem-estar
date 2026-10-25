# ADR 0002 — Durable raw inbox before parsing

Status: Accepted
Date: 2026-09-15

## Context

HAE runs on iOS with background/time/memory constraints and may send large/retried payloads. Metric/parser bugs must be repairable without asking the phone to reproduce old data.

## Decision

Webhook persists authenticated JSON payload gzip + ingestion row and returns 202. Worker parses later. Raw is retained for replay/audit.

## Consequences

Webhook is fast and reliable; parser errors are replayable. Disk usage increases and raw data needs strong permissions/retention controls.

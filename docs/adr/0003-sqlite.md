# ADR 0003 — SQLite WAL for canonical storage

Status: Accepted
Date: 2026-09-15

## Context

One user, one worker, read-heavy dashboard/MCP, ~4 GiB VM.

## Decision

SQLite WAL + SQLAlchemy/Alembic. Repository seams preserve a future PostgreSQL option.

## Consequences

Very low operational overhead and easy backups; single-writer behavior means worker concurrency should remain one until measurements justify change.

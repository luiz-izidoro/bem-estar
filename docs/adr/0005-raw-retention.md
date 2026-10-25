# ADR 0005 — 180-day local RAW payload retention

Status: Accepted

## Context

The target VPS has limited local free space. HAE RAW payloads are valuable for replay/parser recovery but retaining every compressed request forever is unnecessary once canonical data is stable.

## Decision

- keep canonical SQLite data and derived metrics indefinitely unless a future explicit retention policy says otherwise;
- keep successfully processed RAW HAE payloads locally for 180 days by default;
- run a daily systemd maintenance timer to prune processed RAW files past retention;
- never prune pending/processing/failed payloads automatically;
- record pruned RAW references as `pruned://...` rather than deleting ingestion history;
- use off-host backup when long-term RAW replay is desired.

## Consequences

The server can bound RAW storage while retaining six months of parser replay evidence. Reprocessing beyond the local retention horizon depends on canonical data, HAE re-export availability, or an optional off-host RAW backup.

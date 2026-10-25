# Health Auto Export Configuration

The canonical production flow is:

```text
Apple Health -> Health Auto Export -> HTTPS POST -> Bem Estar durable inbox -> worker
```

Canonical endpoint:

```text
https://bemestar.example.com/webhooks/hae/v2
```

Compatibility endpoint during migration:

```text
https://bemestar.example.com/v1/health-auto-export
```

For the exact current iPhone setup, headers, metrics, four automation profiles, reconciliation, historical bootstrap and troubleshooting, use:

```text
docs/16-HAE-WEBHOOK-SETUP.md
```

Machine-readable automation plan:

```text
config/hae/automation-plan.yaml
```

The backend expects JSON export v2, recommends Batch Requests, and uses dedicated Bearer authentication plus `X-Bemestar-Stream` to classify the inbound automation.

HAE automatically provides `automation-name`, `automation-id`, `automation-aggregation`, `automation-period` and `session-id`; Bem Estar retains those values for provenance.

The normal sync pattern is `Since Last Sync`. Reconciliation intentionally resends recent data because Apple Health records may arrive late or be revised. Canonical ingestion is idempotent and supports in-place correction of a logical sample slot.

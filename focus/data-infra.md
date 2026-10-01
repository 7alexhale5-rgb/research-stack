# Focus lens: data-infra (data and infrastructure)

Use this lens for databases, schemas, queues, caches, pipelines, hosting and other infrastructure
choices. Its rule comes from the system-design proof gate: every core technology choice needs a
one-line rationale tied to the workload, never an unargued default.

## Triggers

Suggested when the topic mentions databases, Postgres, schema, warehouse, ETL, pipelines, queues,
Kafka, caching, Redis, infra, Kubernetes, serverless or CDN.

## Sub-question lens

1. **Workload:** what are the read/write ratio, consistency needs, data size and growth, latency
   target, and failure tolerance?
2. **Options against the workload:** which storage, transport and compute options fit (for
   example SQL vs document vs KV, REST vs gRPC, sync vs queue), and what are the documented limits
   and failure modes of each?
3. **Operations:** cost at our scale, managed-service limits and quotas, the provider's incident
   history, and the migration path.

## Tool stack

| Tool           | Tier       | Use it for                                                    | Skip when                      |
| -------------- | ---------- | ------------------------------------------------------------- | ------------------------------ |
| `vendor-docs`  | free       | Limits, quotas, pricing and deprecations from the source      | never                          |
| `jepsen`       | free       | Independent consistency and partition testing                 | the store has no Jepsen report |
| `db-engines`   | free       | Popularity trend and system properties                        | the choice is not a database   |
| `status-pages` | free       | Incident history for managed services                         | self-hosted                    |
| `gcloud`       | free (CLI) | Live quotas and regions on your own Google Cloud project      | not on Google Cloud            |

Pair with `devtools` for client libraries and `security` for tenant isolation.

## Authorities

Official docs (postgresql.org, kubernetes.io, the cloud provider's docs) and Jepsen outrank
benchmark blogs. A vendor benchmark of its own product is one source and is labelled as such.

## Freshness

- Cache TTL: 30 days for limits and pricing, 180 days for architecture guidance.
- Dated trap: managed-service quotas and free tiers change often. Copy the number and the date.

## Audit mode

With `--target <repo>`: find the schema and migration files, infra-as-code and service configs.
Summarize the current architecture, then check each component's version against its support
window. Tag `[AUDIT:infra]`.

## Report addendum

Add a **Data and infra trade-offs** section:

```text
### Data and infra trade-offs
| Decision        | Choice      | Rationale tied to the workload                    | Rejected (why)              | Source         |
| --------------- | ----------- | ------------------------------------------------- | --------------------------- | -------------- |
| Primary store   | Postgres 17 | relational joins, 95% reads, < 200 GB in 2 years  | DynamoDB (access patterns)  | [DOCS + JEP]   |
```

## Pathway mapping

- pathway-operating-layer: `data` (the system-design research gate is satisfied by this table).
- development-protocol rows: `research`, `planning`, `premortem`.

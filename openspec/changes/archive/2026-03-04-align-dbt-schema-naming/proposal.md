## Why

The Salesforce dbt transformation project currently lands modeled outputs in prefixed schemas (`staging_staging`, `staging_intermediate`, `staging_marts`) instead of the intended canonical layer schemas. This creates operator confusion, drifts from documented architecture, and complicates downstream querying.

## What Changes

- Align dbt schema resolution so Salesforce models materialize into canonical schemas: `staging`, `intermediate`, and `marts`.
- Preserve `raw_salesforce` as the ingestion and pipeline state schema.
- Remove dependence on prefixed modeled schemas for normal operation in this single-environment deployment.
- Clarify schema contract expectations in transformation requirements and operational documentation.

## Capabilities

### New Capabilities
- `salesforce-modeled-schema-contract`: Define and enforce canonical schema landing behavior for Salesforce dbt layers in the homelab deployment.

### Modified Capabilities
- `salesforce-dbt-transformation-dag`: Update transformation capability requirements so dbt orchestration targets canonical modeled schemas without environment-prefix schema expansion.

## Impact

- Affected code: dbt project schema naming behavior and related transformation configuration in `dags/dbt/`.
- Affected systems: Postgres warehouse modeled schemas and dbt outputs.
- Affected operations: warehouse introspection and downstream querying paths now align with canonical `staging`/`intermediate`/`marts` naming.

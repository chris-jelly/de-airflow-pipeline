## Why

The pipeline currently lands Salesforce data into a `bronze` schema with source-oriented tables and text-typed columns, but the team prefers a dbt-native layering model (`raw` -> `staging` -> `intermediate` -> `marts`) and does not want medallion schema terminology. We need a dbt-driven transformation DAG and schema realignment so downstream consumers can rely on typed, validated, and analytics-friendly datasets with clear data quality guarantees.

## What Changes

- Add a new Airflow DAG that executes dbt transformations from Salesforce raw landing tables into modeled layers.
- Introduce a dbt project for Salesforce with layered models (`staging`, `intermediate`, `marts`) and schema-level separation from raw ingestion.
- Add first-pass type normalization from raw text fields into typed staging columns for `accounts`, `contacts`, and `opportunities`.
- Add dbt data quality validations with explicit severity tiers (`error`, `warn`, `info`) for structural, relational, and business-rule checks.
- Add query-ready marts and a lightweight opportunity history pattern to support current and near-term dashboard use cases.
- Re-scope the existing Salesforce extraction DAG to land into `raw_salesforce` (instead of `bronze`) and update its schema/task naming contract.
- Configure orchestration so the dbt DAG can run independently while skipping work when no new raw data is available.

## Capabilities

### New Capabilities
- `salesforce-dbt-transformation-dag`: Airflow orchestration for dbt runs over Salesforce raw data, including freshness gating and run behavior.
- `salesforce-staging-intermediate-modeling`: Typed Salesforce staging/intermediate models in dbt for accounts, contacts, and opportunities.
- `salesforce-analytics-quality-marts`: dbt validation severity model plus marts and lightweight opportunity history outputs for analytics consumption.

### Modified Capabilities
- `salesforce-dag`: Extraction schema contract changes from `bronze` to `raw_salesforce`, including updated task/schema naming and downstream table targets.

## Impact

- Affected code: new dbt project structure, new dbt Airflow DAG, and associated tests/configuration.
- Affected runtime: additional per-DAG container image and dependency path for dbt execution.
- Affected data model: replacement of `bronze` naming with `raw_salesforce` for ingestion plus new modeled schemas (`staging`, `intermediate`, `marts`).
- Affected operations: new orchestration schedule/trigger behavior, validation outcomes, and transformation observability.

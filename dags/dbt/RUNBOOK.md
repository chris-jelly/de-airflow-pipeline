# Salesforce dbt Transformation Runbook

## Scope

This runbook covers the `salesforce_dbt_transformation` DAG and dbt project under `dags/dbt`.

## Schema Layout (single `warehouse` database)

- `raw_salesforce`: ingestion landing tables and dbt transformation state table.
- `staging`: typed first-pass models from raw source text fields.
- `intermediate`: current-state incremental upsert models keyed by Salesforce entity IDs.
- `marts`: query-ready account/opportunity analytics models and lightweight opportunity history snapshots.

## Schedule and Freshness Gating

- DAG schedule: `@hourly`.
- Freshness gate task: `check_raw_salesforce_freshness`.
- Skip behavior: if `MAX(extracted_at)` from raw Salesforce tables is not newer than `raw_salesforce.dbt_transformation_state.last_raw_marker`, dbt tasks are skipped.
- Execute behavior: when freshness advances, the DAG runs `dbt build` and diagnostics, then updates `last_raw_marker`.

## Validation Severity Interpretation

- `error`: contract and critical quality checks; these fail the run.
- `warn`: drift-oriented checks; surfaced as warnings but do not fail by default.
- `info`: monitor-only diagnostics tagged as `info` and run through diagnostic test selection.

## Focused Validation Commands

Run from `dags/dbt` with warehouse credentials exported as environment variables (`DBT_HOST`, `DBT_USER`, `DBT_PASSWORD`, `DBT_DBNAME`):

```bash
uv sync
uv run dbt parse
uv run dbt ls --select path:models/staging+
uv run dbt ls --select path:models/marts+
```

Expected outcomes:

- `dbt parse` succeeds without graph compilation errors.
- `dbt ls` returns Salesforce staging and marts model selection lists.

## Rollback Path

1. Pause or disable the `salesforce_dbt_transformation` DAG in Airflow.
2. Repoint workloads to prior trusted tables (if needed).
3. Revert deployment to a previous dbt DAG image tag.
4. If required, clear `raw_salesforce.dbt_transformation_state` rows for `salesforce_dbt` before re-enabling.

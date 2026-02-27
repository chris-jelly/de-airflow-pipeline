## Why

The Salesforce dbt transformation DAG runs in pods where git-synced DAG files are mounted read-only, while dbt writes build artifacts at runtime. This causes dbt commands to fail even when SQL is valid, so the pipeline needs a runtime-safe write-path strategy.

## What Changes

- Update dbt task execution to write dbt artifacts (`target`, logs, package install path) to writable runtime directories such as `/tmp` instead of the DAG source mount.
- Improve dbt task failure observability by logging dbt stdout/stderr in Airflow task logs.
- Add tests that validate dbt command configuration does not assume writable DAG project mounts.

## Capabilities

### New Capabilities
- `salesforce-dbt-runtime-filesystem`: Ensure dbt tasks run successfully when DAG code is mounted read-only by configuring writable artifact/log paths.

### Modified Capabilities
- None.

## Impact

- Affected code: `dags/dbt/salesforce_dbt_transformation_dag.py` and dbt DAG tests.
- Affected runtime: Airflow worker pod dbt execution behavior under git-sync read-only DAG mounts.
- Affected operations: improved incident triage via dbt stderr/stdout visibility in task logs.

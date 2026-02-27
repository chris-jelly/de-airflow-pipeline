## 1. Runtime Write-Path Safety

- [x] 1.1 Update dbt environment construction in `salesforce_dbt_transformation_dag.py` to set writable runtime paths (`DBT_TARGET_PATH`, `DBT_LOG_PATH`, `DBT_PACKAGES_INSTALL_PATH`) under `/tmp/dbt`.
- [x] 1.2 Ensure all dbt subprocess commands (`build`, diagnostics/tests) use the shared writable-path environment without project-dir writes.

## 2. Failure Observability

- [x] 2.1 Refactor dbt subprocess execution to capture stdout/stderr and log command context before raising on non-zero exit.
- [x] 2.2 Add clear log messages for success and failure paths that preserve dbt output context in Airflow task logs.

## 3. Validation and Regression Coverage

- [x] 3.1 Add/update dbt DAG unit tests to assert writable runtime path env vars are present for dbt command execution.
- [x] 3.2 Add/update tests for failure handling to verify stderr/stdout context is emitted when dbt subprocess fails.
- [x] 3.3 Run dbt DAG test suite and document expected verification command/results in the change workflow.

Verification (this session): `cd dags/dbt && uv run ruff format salesforce_dbt_transformation_dag.py tests/test_salesforce_dbt_transformation_dag.py && uv run pytest -v` -> 7 passed.

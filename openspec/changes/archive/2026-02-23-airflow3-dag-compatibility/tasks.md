## 1. K3d Helm Values — Airflow 3

- [x] 1.1 Update `k3d/values-airflow.yaml` image tag from `2.8.1` to `3.1.5-python3.13`
- [x] 1.2 Rename `config.kubernetes` section to `config.kubernetes_executor`
- [x] 1.3 Remove `config.api.auth_backends` (legacy REST API auth, replaced by FastAPI in Airflow 3)
- [x] 1.4 Pin Helm chart version to 1.19 in K3d setup scripts (verify `k3d/scripts/` for install/upgrade commands)
- [x] 1.5 Update `k3d/AGENTS.md` to reflect Airflow 3 config patterns (`kubernetes_executor` section, FastAPI auth)

## 2. Postgres Ping DAG

- [x] 2.1 Create `dags/postgres-ping/` directory
- [x] 2.2 Create `dags/postgres-ping/postgres_ping_dag.py` using TaskFlow API (`@dag`, `@task` decorators)
- [x] 2.3 Implement ping task: connect to warehouse Postgres via `PostgresHook(postgres_conn_id=warehouse_postgres_{env})`, execute `SELECT 1`, log result and server timestamp
- [x] 2.4 Add `executor_config` pod override mounting `AIRFLOW_CONN_WAREHOUSE_POSTGRES` from Kubernetes secret (ADR-002 pattern)
- [x] 2.5 Configure DAG with `schedule="@hourly"`, `catchup=False`
- [x] 2.6 Use lazy import pattern — `PostgresHook` imported inside task function, not at module level

## 3. Salesforce DAG — TaskFlow Migration

- [x] 3.1 Replace `DAG()` constructor with `@dag` decorator on a function
- [x] 3.2 Convert `create_bronze_schema` from `PythonOperator` to `@task` decorated function
- [x] 3.3 Convert `extract_salesforce_to_postgres` from `PythonOperator` to `@task` decorated function
- [x] 3.4 Wire task dependencies using TaskFlow return values / function calls instead of `>>` operator on `PythonOperator` instances
- [x] 3.5 Preserve task IDs (`create_bronze_schema`, `extract_accounts`, `extract_opportunities`, `extract_contacts`)
- [x] 3.6 Remove `default_args` `executor_config` passthrough — apply `executor_config` via `@task` decorator kwargs or DAG-level config

## 4. Salesforce DAG — conn_id Migration

- [x] 4.1 Replace `PostgresHook(host=..., login=..., password=..., ...)` with `PostgresHook(postgres_conn_id=postgres_conn_id)`
- [x] 4.2 Replace `SalesforceHook(consumer_key=..., consumer_secret=..., domain=...)` with `SalesforceHook(salesforce_conn_id=salesforce_conn_id)`
- [x] 4.3 Remove manual `os.getenv()` calls for individual credential env vars from task functions
- [x] 4.4 Refactor `executor_config` pod override: replace individual secret env vars (`POSTGRES_HOST`, `POSTGRES_USER`, etc.) with `AIRFLOW_CONN_WAREHOUSE_POSTGRES` and `AIRFLOW_CONN_SALESFORCE` from Kubernetes secrets
- [x] 4.5 Document required Kubernetes secret format for `AIRFLOW_CONN_*` env vars (connection URI / JSON format) — note downstream homelab repo work needed

## 5. Salesforce DAG — Minor Fixes

- [x] 5.1 Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` for `extracted_at` column
- [x] 5.2 Add `from datetime import timezone` import
- [x] 5.3 Verify lazy import pattern preserved (provider hooks and `pandas` inside task functions only)

## 6. Tests

- [x] 6.1 Update `dags/salesforce/tests/test_salesforce_extraction_dag.py` for TaskFlow DAG structure (task discovery may differ from classic DAG)
- [x] 6.2 Update task dependency assertions to work with TaskFlow API
- [x] 6.3 Update executor config assertions (new `AIRFLOW_CONN_*` env vars instead of individual credential vars)
- [x] 6.4 Add basic tests for `postgres_ping_dag` (DAG parses, correct task IDs, schedule, executor config)
- [x] 6.5 Run `scripts/test-all-dags.sh` and verify all tests pass

## 7. Documentation

- [x] 7.1 Update `CONTAINER_STRATEGY.md` — replace all `2.8.1` / `2.8.1-python3.11` references with `3.1.5-python3.13`
- [x] 7.2 Update `KUBERNETES.md` — replace all `2.8.1` / `2.8.1-python3.11` references with `3.1.5-python3.13`
- [x] 7.3 Document the `AIRFLOW_CONN_*` pod-level secret pattern in `KUBERNETES.md` (how it works with ADR-002)

## 8. Build & Verify

- [x] 8.1 Rebuild Salesforce DAG container image (`dags/salesforce/Dockerfile`) and verify it builds cleanly
- [x] 8.2 Verify both DAGs parse correctly with `airflow dags list` in K3d (or local Airflow if available)
- [x] 8.3 Run ruff format on all modified Python files

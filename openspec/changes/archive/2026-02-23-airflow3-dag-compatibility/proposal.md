## Why

The homelab Airflow deployment has been upgraded to Airflow 3, but the DAGs in this repo were written for Airflow 2.x. The existing Salesforce DAG syncs via git-sync but does not execute correctly. The K3d local development environment still targets Airflow 2.8.1, making it impossible to develop and test against the production Airflow 3 environment. We need to bring this repo's DAGs, development tooling, and documentation into alignment with Airflow 3.

## What Changes

- **Add a Postgres ping DAG** using the TaskFlow API (`@dag`/`@task` decorators) that connects to Postgres and runs a simple query, proving DAG sync, task execution, and database connectivity work end-to-end in the homelab environment
- **Modernize the Salesforce DAG** to Airflow 3 patterns:
  - Migrate from `PythonOperator` to TaskFlow API (`@task` decorators)
  - Switch from direct hook parameter passing to Airflow Connection `conn_id` pattern for both `PostgresHook` and `SalesforceHook`
  - Replace deprecated `datetime.utcnow()` with timezone-aware `datetime.now(timezone.utc)`
- **BREAKING**: Update K3d Helm values for Airflow 3:
  - Update Airflow image from `2.8.1` to Airflow 3.x
  - Rename `[kubernetes]` config section to `[kubernetes_executor]`
  - Update or remove `api.auth_backends` configuration (legacy REST API replaced by FastAPI in Airflow 3)
  - Remove or update `flower` configuration if present
- **Update documentation** (`CONTAINER_STRATEGY.md`, `KUBERNETES.md`) to reflect Airflow 3 image tags and patterns

## Capabilities

### New Capabilities

- `postgres-ping-dag`: A simple health-check DAG using TaskFlow API that validates Postgres connectivity and task execution. Serves as a smoke test for the homelab deployment pipeline.

### Modified Capabilities

_(No existing specs to modify)_

- `salesforce-dag`: Modernize the existing Salesforce extraction DAG to use Airflow 3 patterns — TaskFlow API, `conn_id`-based hooks, and timezone-aware datetimes. Treat as a new capability spec since no prior spec exists.
- `k3d-dev-environment`: Update the local K3d development environment configuration to target Airflow 3, including Helm values, config sections, and API authentication.

## Impact

- **DAG code**: `dags/salesforce/salesforce_extraction_dag.py` — significant refactor (TaskFlow migration, hook pattern change). New DAG file for Postgres ping.
- **DAG packaging**: New `dags/postgres-ping/` directory with its own `pyproject.toml` and `Dockerfile` following the per-DAG container strategy, or minimal enough to run on the base Airflow image.
- **K3d config**: `k3d/values-airflow.yaml` — breaking changes to Helm values (image tag, config sections).
- **Documentation**: `CONTAINER_STRATEGY.md`, `KUBERNETES.md` — version references updated.
- **Dependencies**: Provider packages (`apache-airflow-providers-postgres`, `apache-airflow-providers-salesforce`) must be verified compatible with Airflow 3.
- **Existing tests**: `dags/salesforce/tests/` will need updates to match the refactored DAG structure.
- **Out-of-scope downstream work (homelab repo)**: Switching to `conn_id`-based hooks requires Airflow Connections to be configured in the homelab deployment (e.g., via Helm `extraEnv`, `connections` config, or Kubernetes secrets defining `AIRFLOW_CONN_*` environment variables). This configuration lives in the homelab repo and is not part of this change, but must be done before the updated Salesforce DAG will execute successfully in production.

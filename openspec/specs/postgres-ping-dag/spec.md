## ADDED Requirements

### Requirement: Postgres connectivity health check DAG

The system SHALL provide a DAG named `postgres_ping` that validates Postgres database connectivity and task execution by running a simple query against the external warehouse Postgres database.

#### Scenario: DAG parses successfully on Airflow 3

- **WHEN** the Airflow 3 scheduler scans the `dags/` directory
- **THEN** the `postgres_ping` DAG SHALL be discovered and parsed without import errors using only dependencies available in the base `apache/airflow` image

#### Scenario: Successful Postgres ping

- **WHEN** the `postgres_ping` DAG executes its ping task
- **THEN** the task SHALL connect to the warehouse Postgres using the `warehouse_postgres` connection ID, execute `SELECT 1`, and log the result along with the current server timestamp

#### Scenario: Connection failure

- **WHEN** the Postgres connection is unreachable or misconfigured
- **THEN** the task SHALL fail with a clear error message indicating the connection issue

### Requirement: TaskFlow API pattern

The DAG SHALL use the Airflow TaskFlow API (`@dag` and `@task` decorators) exclusively. It SHALL NOT use `PythonOperator` or other classic operator patterns.

#### Scenario: DAG definition uses decorators

- **WHEN** the DAG file is inspected
- **THEN** the DAG SHALL be defined with `@dag` decorator and all tasks SHALL be defined with `@task` decorators

### Requirement: No custom container image

The Postgres ping DAG SHALL run on the base `apache/airflow` image without requiring a custom Dockerfile, `pyproject.toml`, or additional Python dependencies beyond what the base image provides.

#### Scenario: Execution on base image

- **WHEN** a KubernetesExecutor worker pod runs a task from this DAG
- **THEN** the task SHALL execute successfully using the base Airflow image (no `executor_config` image override required)

### Requirement: Pod override for warehouse connection

The DAG SHALL define an `executor_config` with a pod override that mounts the `AIRFLOW_CONN_WAREHOUSE_POSTGRES` environment variable from a Kubernetes secret. This follows the ADR-002 pod-level secret isolation pattern — the warehouse connection is only available to executor pods running this DAG's tasks.

#### Scenario: Warehouse connection mounted in executor pod

- **WHEN** a KubernetesExecutor worker pod runs a task from this DAG
- **THEN** the pod SHALL have the `AIRFLOW_CONN_WAREHOUSE_POSTGRES` environment variable mounted from the appropriate Kubernetes secret

#### Scenario: Scheduler does not receive warehouse connection

- **WHEN** the scheduler pod is inspected
- **THEN** it SHALL NOT have the `AIRFLOW_CONN_WAREHOUSE_POSTGRES` environment variable

### Requirement: DAG file location

The DAG file SHALL be located at `dags/postgres-ping/postgres_ping_dag.py`, following the per-DAG directory convention used in this repository.

#### Scenario: File placement

- **WHEN** the repository is checked out
- **THEN** the DAG file SHALL exist at `dags/postgres-ping/postgres_ping_dag.py`

### Requirement: DAG schedule

The DAG SHALL be configured with `schedule="@hourly"` and `catchup=False` to provide regular health checks without backfilling historical runs.

#### Scenario: Scheduled execution

- **WHEN** the DAG is deployed and unpaused
- **THEN** it SHALL execute once per hour and SHALL NOT attempt to run for past missed intervals

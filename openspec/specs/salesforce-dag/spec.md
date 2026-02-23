## ADDED Requirements

### Requirement: TaskFlow API migration

The Salesforce extraction DAG SHALL use the Airflow TaskFlow API. The DAG SHALL be defined with the `@dag` decorator. All task functions (`create_bronze_schema`, `extract_accounts`, `extract_opportunities`, `extract_contacts`) SHALL be defined with `@task` decorators.

#### Scenario: DAG uses TaskFlow decorators

- **WHEN** the DAG file is inspected
- **THEN** the DAG SHALL be defined with `@dag` and all tasks SHALL use `@task` decorators instead of `PythonOperator`

#### Scenario: Task dependencies preserved

- **WHEN** the DAG is parsed
- **THEN** `create_bronze_schema` SHALL have no upstream dependencies, and `extract_accounts`, `extract_opportunities`, and `extract_contacts` SHALL each depend on `create_bronze_schema`

#### Scenario: Task IDs unchanged

- **WHEN** the DAG is parsed
- **THEN** the task IDs SHALL remain `create_bronze_schema`, `extract_accounts`, `extract_opportunities`, and `extract_contacts`

### Requirement: Connection-based hook instantiation

All hooks SHALL be instantiated using Airflow Connection `conn_id` references instead of direct parameter passing. The DAG SHALL use `PostgresHook(postgres_conn_id=...)` and `SalesforceHook(salesforce_conn_id=...)`.

#### Scenario: PostgresHook uses conn_id

- **WHEN** a task needs to connect to Postgres
- **THEN** it SHALL instantiate `PostgresHook` with a `postgres_conn_id` parameter referencing an Airflow Connection, not with individual `host`, `login`, `password`, `database`, `port` parameters

#### Scenario: SalesforceHook uses conn_id

- **WHEN** a task needs to connect to Salesforce
- **THEN** it SHALL instantiate `SalesforceHook` with a `salesforce_conn_id` parameter referencing an Airflow Connection, not with individual `consumer_key`, `consumer_secret`, `domain` parameters

#### Scenario: Connection IDs use static names

- **WHEN** the DAG resolves connection IDs
- **THEN** the connection IDs SHALL be static strings (`warehouse_postgres`, `salesforce`) matching the `AIRFLOW_CONN_*` env vars mounted in executor pods

### Requirement: Pod override with AIRFLOW_CONN env vars

The `executor_config` pod override SHALL mount `AIRFLOW_CONN_*` environment variables from Kubernetes secrets instead of individual credential env vars. This preserves ADR-002 pod-level secret isolation while using the Airflow connection system.

#### Scenario: Pod override defines connection env vars

- **WHEN** the executor config is inspected
- **THEN** the pod override SHALL define `AIRFLOW_CONN_WAREHOUSE_POSTGRES` and `AIRFLOW_CONN_SALESFORCE` environment variables sourced from Kubernetes secrets

#### Scenario: Individual credential env vars removed

- **WHEN** the executor config is inspected
- **THEN** the pod override SHALL NOT contain individual env vars like `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `SALESFORCE_CONSUMER_KEY`, etc.

#### Scenario: Scheduler does not receive connection secrets

- **WHEN** the scheduler pod is inspected
- **THEN** it SHALL NOT have `AIRFLOW_CONN_WAREHOUSE_POSTGRES` or `AIRFLOW_CONN_SALESFORCE` environment variables mounted

### Requirement: Timezone-aware datetime usage

The DAG SHALL use `datetime.now(timezone.utc)` instead of the deprecated `datetime.utcnow()` for all timestamp generation.

#### Scenario: Extracted_at timestamp is timezone-aware

- **WHEN** the extraction task adds an `extracted_at` audit column
- **THEN** it SHALL use `datetime.now(timezone.utc)` to generate the timestamp

### Requirement: Lazy import pattern preserved

Provider hooks and heavy libraries (`pandas`, `SalesforceHook`, `PostgresHook`) SHALL continue to be imported inside task functions, not at module level. This ensures the scheduler can parse the DAG using only the base Airflow image.

#### Scenario: Module-level imports are lightweight

- **WHEN** the scheduler parses the DAG file at module level
- **THEN** only `airflow` core imports and `kubernetes.client.models` SHALL be imported; provider hooks and `pandas` SHALL NOT be imported at the top level

### Requirement: Extraction logic unchanged

The Salesforce extraction logic (query all records, clean nested objects, add audit columns, write to bronze schema via pandas `to_sql`) SHALL remain functionally identical. This change is a structural refactor, not a logic change.

#### Scenario: Same Salesforce objects extracted

- **WHEN** the DAG executes
- **THEN** it SHALL extract `Account`, `Opportunity`, and `Contact` objects to `bronze.accounts`, `bronze.opportunities`, and `bronze.contacts` tables respectively

#### Scenario: Audit columns present

- **WHEN** records are written to Postgres
- **THEN** each record SHALL include `extracted_at` (timezone-aware timestamp) and `dag_run_id` columns

### Requirement: Updated tests

The test suite SHALL be updated to work with the TaskFlow API DAG structure while maintaining equivalent coverage for task IDs, task dependencies, and executor configuration.

#### Scenario: Tests validate TaskFlow DAG structure

- **WHEN** tests are run
- **THEN** they SHALL verify the DAG contains the expected task IDs, correct dependency graph, and executor config with pod overrides

#### Scenario: Tests pass without Airflow connections

- **WHEN** tests are run in CI without database or Salesforce access
- **THEN** they SHALL validate DAG structure and configuration without requiring live connections

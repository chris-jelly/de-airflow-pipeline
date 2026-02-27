## MODIFIED Requirements

### Requirement: TaskFlow API migration

The Salesforce extraction DAG SHALL use the Airflow TaskFlow API. The DAG SHALL be defined with the `@dag` decorator. All task functions (`create_raw_salesforce_schema`, `extract_accounts`, `extract_opportunities`, `extract_contacts`) SHALL be defined with `@task` decorators.

#### Scenario: DAG uses TaskFlow decorators

- **WHEN** the DAG file is inspected
- **THEN** the DAG SHALL be defined with `@dag` and all tasks SHALL use `@task` decorators instead of `PythonOperator`

#### Scenario: Task dependencies preserved

- **WHEN** the DAG is parsed
- **THEN** `create_raw_salesforce_schema` SHALL have no upstream dependencies, and `extract_accounts`, `extract_opportunities`, and `extract_contacts` SHALL each depend on `create_raw_salesforce_schema`

#### Scenario: Task IDs unchanged

- **WHEN** the DAG is parsed
- **THEN** the task IDs SHALL remain `create_raw_salesforce_schema`, `extract_accounts`, `extract_opportunities`, and `extract_contacts`

### Requirement: Extraction logic unchanged

The Salesforce extraction logic SHALL use curated explicit field lists and watermark-based incremental queries by `SystemModstamp`, while continuing to extract `Account`, `Opportunity`, and `Contact` into raw landing tables.

#### Scenario: Same Salesforce objects extracted

- **WHEN** the DAG executes
- **THEN** it SHALL extract `Account`, `Opportunity`, and `Contact` objects to `raw_salesforce.accounts`, `raw_salesforce.opportunities`, and `raw_salesforce.contacts` tables respectively

#### Scenario: Incremental extraction query behavior

- **WHEN** the extraction task queries Salesforce
- **THEN** it SHALL use an explicit curated field list per object and SHALL apply watermark filtering by `SystemModstamp` instead of querying all historical rows on every run

#### Scenario: Audit columns present

- **WHEN** records are written to Postgres
- **THEN** each record SHALL include `extracted_at` (timezone-aware timestamp) and `dag_run_id` columns

### Requirement: Updated tests

The test suite SHALL be updated to work with the renamed raw schema creation task and schema targets while maintaining equivalent coverage for task IDs, task dependencies, and executor configuration.

#### Scenario: Tests validate TaskFlow DAG structure

- **WHEN** tests are run
- **THEN** they SHALL verify the DAG contains the expected task IDs, correct dependency graph, and executor config with pod overrides

#### Scenario: Tests pass without Airflow connections

- **WHEN** tests are run in CI without database or Salesforce access
- **THEN** they SHALL validate DAG structure and configuration without requiring live connections

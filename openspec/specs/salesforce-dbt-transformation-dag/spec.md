## ADDED Requirements

### Requirement: Dedicated dbt transformation DAG
The system SHALL provide a dedicated Airflow DAG that orchestrates dbt transformations for Salesforce raw landing tables and downstream modeled layers.

#### Scenario: DAG is discoverable and scoped to dbt transformation
- **WHEN** Airflow parses DAG files
- **THEN** a dbt transformation DAG for Salesforce SHALL be present as a distinct DAG from extraction DAGs

#### Scenario: DAG executes dbt transformation workflow
- **WHEN** the transformation DAG runs
- **THEN** it SHALL execute dbt commands that build Salesforce transformation models and run configured validations

### Requirement: Independent scheduling with freshness gating
The dbt transformation DAG SHALL be independently schedulable and SHALL skip transformation work when raw Salesforce data has not advanced since the last successful transformation run.

#### Scenario: No new raw data
- **WHEN** raw Salesforce freshness markers have not changed since the previous successful dbt run
- **THEN** the DAG SHALL short-circuit without executing dbt build steps

#### Scenario: New raw data available
- **WHEN** raw Salesforce freshness markers have advanced since the previous successful dbt run
- **THEN** the DAG SHALL execute dbt transformation and validation steps

### Requirement: Operational observability for transformation runs
The dbt transformation DAG SHALL emit run-level observability signals for execution path and outcome.

#### Scenario: Skip path is observable
- **WHEN** a run short-circuits due to unchanged raw data
- **THEN** task logs SHALL explicitly indicate that no new data was detected and dbt was skipped

#### Scenario: Build path is observable
- **WHEN** a run executes dbt steps
- **THEN** task logs SHALL indicate selected dbt command scope and final run outcome

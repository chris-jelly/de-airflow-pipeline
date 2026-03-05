## MODIFIED Requirements

### Requirement: Dedicated dbt transformation DAG
The system SHALL provide a dedicated Airflow DAG that orchestrates dbt transformations for Salesforce raw landing tables and downstream modeled layers in canonical schemas.

#### Scenario: DAG is discoverable and scoped to dbt transformation
- **WHEN** Airflow parses DAG files
- **THEN** a dbt transformation DAG for Salesforce SHALL be present as a distinct DAG from extraction DAGs

#### Scenario: DAG executes dbt transformation workflow
- **WHEN** the transformation DAG runs
- **THEN** it SHALL execute dbt commands that build Salesforce transformation models and run configured validations

#### Scenario: DAG builds canonical modeled schemas
- **WHEN** the transformation DAG executes dbt model builds
- **THEN** modeled outputs SHALL materialize into canonical schemas `staging`, `intermediate`, and `marts`

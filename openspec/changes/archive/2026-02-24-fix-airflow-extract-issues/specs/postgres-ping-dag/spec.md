## MODIFIED Requirements

### Requirement: TaskFlow API pattern

The DAG SHALL use the Airflow TaskFlow API (`@dag` and `@task` decorators) imported from `airflow.sdk`. It SHALL NOT use `PythonOperator` or other classic operator patterns.

#### Scenario: DAG definition uses decorators

- **WHEN** the DAG file is inspected
- **THEN** the DAG SHALL be defined with `@dag` decorator and all tasks SHALL be defined with `@task` decorators, imported from `airflow.sdk`

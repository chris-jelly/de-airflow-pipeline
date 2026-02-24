## MODIFIED Requirements

### Requirement: Lazy import pattern preserved

Provider hooks and heavy libraries (`pandas`, `SalesforceHook`, `PostgresHook`) SHALL continue to be imported inside task functions, not at module level. This ensures the scheduler can parse the DAG using only the base Airflow image.

#### Scenario: Module-level imports are lightweight

- **WHEN** the scheduler parses the DAG file at module level
- **THEN** only `airflow.sdk`, `datetime`, and `kubernetes.client.models` SHALL be imported; provider hooks and `pandas` SHALL NOT be imported at the top level

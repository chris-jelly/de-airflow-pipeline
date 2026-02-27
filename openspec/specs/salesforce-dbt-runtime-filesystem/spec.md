## ADDED Requirements

### Requirement: dbt execution SHALL use writable runtime artifact paths
The Salesforce dbt transformation DAG SHALL configure dbt to write runtime artifacts to writable filesystem paths that are independent of the DAG source mount.

#### Scenario: Read-only DAG source mount
- **WHEN** the DAG executes dbt commands in an environment where the DAG/project directory is mounted read-only
- **THEN** dbt runtime artifacts (including compiled output and logs) SHALL be written to writable paths and the dbt command SHALL execute without failing due to read-only filesystem errors

#### Scenario: Runtime path consistency across dbt tasks
- **WHEN** the DAG executes multiple dbt commands in one run
- **THEN** each dbt command SHALL use the same writable runtime path strategy for artifact and log output

### Requirement: dbt task failures SHALL expose command output context
The Salesforce dbt transformation DAG SHALL emit actionable dbt subprocess output in task logs when dbt commands fail.

#### Scenario: dbt command fails
- **WHEN** a dbt subprocess exits non-zero
- **THEN** task logs SHALL include the executed dbt command and stderr/stdout context sufficient for root-cause analysis

#### Scenario: Airflow wrapper exception is raised
- **WHEN** Airflow wraps a failed dbt subprocess in a task exception
- **THEN** the original dbt output context SHALL still be present in task logs prior to task failure

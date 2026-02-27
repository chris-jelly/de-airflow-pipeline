## 1. Extraction Schema Contract Update

- [x] 1.1 Update Salesforce extraction DAG schema creation and write targets from `bronze` to `raw_salesforce`.
- [x] 1.2 Rename and align extraction schema task naming (for example `create_raw_salesforce_schema`) and dependency wiring.
- [x] 1.3 Update extraction DAG unit tests/spec assertions for renamed task IDs and raw schema targets.

## 2. dbt Project and Runtime Setup

- [x] 2.1 Scaffold a new dbt project structure for Salesforce transformations under `dags/dbt/` (models, macros, tests, and project config).
- [x] 2.2 Add dbt runtime dependencies and a dedicated DAG container image following per-DAG image conventions.
- [x] 2.3 Extend local and CI image build configuration to include the dbt image and verify build success.

## 3. Airflow dbt Transformation DAG

- [x] 3.1 Create a new Airflow DAG for Salesforce dbt transformations with independent scheduling.
- [x] 3.2 Implement raw freshness pre-check logic that short-circuits dbt tasks when data has not advanced.
- [x] 3.3 Implement dbt command tasks (build/test flow) and run-level logging for skip vs execute outcomes.
- [x] 3.4 Add DAG-level tests that validate task IDs, dependency graph, and skip-path behavior.

## 4. Salesforce Staging and Intermediate Models

- [x] 4.1 Implement staging models for accounts, contacts, and opportunities with explicit first-pass type casting from raw text fields.
- [x] 4.2 Implement intermediate current-state models with unique-key upsert semantics for mutable entities.
- [x] 4.3 Ensure incremental logic uses `SystemModstamp` as the technical change driver and supports late-arriving updates.

## 5. Quality Policy and Marts

- [x] 5.1 Define dbt tests for structural contracts (keys, uniqueness, critical relationships, critical numeric bounds) at error severity.
- [x] 5.2 Define warning-level tests for drift checks (accepted values, soft freshness, cast-failure thresholds).
- [x] 5.3 Add monitor-only diagnostics for info-level quality visibility.
- [x] 5.4 Build query-ready marts for account and opportunity analytics.
- [x] 5.5 Add a lightweight opportunity history snapshot model and enforce snapshot-grain uniqueness.

## 6. Validation and Documentation

- [x] 6.1 Run focused dbt validation commands for staging and marts selections and capture expected outcomes.
- [x] 6.2 Run Airflow DAG unit tests and fix any dependency or parsing issues.
- [x] 6.3 Document operational runbook guidance for one-database schema layout (`raw_salesforce`, `staging`, `intermediate`, `marts`), schedule, freshness gating, severity interpretation, and rollback path.

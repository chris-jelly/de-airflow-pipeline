## Why

The Salesforce extraction DAG currently fails because it generates invalid SOQL (`SELECT *`) and is architected as a full-table append load. We need a reliable incremental extraction pattern so daily runs pull only changed records and reduce load, runtime, and duplicate risk.

## What Changes

- Fix SOQL query construction by using explicit curated field lists per object (`Account`, `Contact`, `Opportunity`) instead of `SELECT *`.
- Change extraction behavior from full refresh append to watermark-based incremental pulls using `SystemModstamp`.
- Add per-object watermark state management so each run resumes from the last successful extraction boundary.
- Introduce deterministic incremental ordering (`SystemModstamp`, `Id`) and idempotent load semantics for reruns/retries.
- Keep delete handling out of scope for this change; deleted-record strategy will be addressed in a future change.

## Capabilities

### New Capabilities
- `salesforce-incremental-watermark-extract`: Defines watermark-based incremental extraction behavior and state tracking for Salesforce object pulls.

### Modified Capabilities
- `salesforce-dag`: Update extraction requirements from full-object query-all behavior to curated-field incremental behavior with stable ordering and state-aware execution.

## Impact

- Affected DAG code: `dags/salesforce/salesforce_extraction_dag.py`.
- Affected tests: `dags/salesforce/tests/test_salesforce_extraction_dag.py` and new tests for incremental query generation/state handling.
- Affected data model: bronze load behavior for `accounts`, `contacts`, and `opportunities`, plus watermark persistence metadata.
- Operational impact: lower API/query volume and faster daily runs; delete propagation intentionally deferred.

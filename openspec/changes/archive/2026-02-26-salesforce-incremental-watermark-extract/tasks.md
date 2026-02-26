## 1. Query and configuration refactor

- [x] 1.1 Replace wildcard SOQL generation with curated explicit field lists for `Account`, `Contact`, and `Opportunity`
- [x] 1.2 Add `SystemModstamp` and `Id` validation for each curated field set
- [x] 1.3 Implement deterministic incremental query construction with `ORDER BY SystemModstamp, Id`

## 2. Watermark state management

- [x] 2.1 Add Postgres-backed per-object watermark state storage and bootstrap behavior for first run
- [x] 2.2 Implement watermark read/write flow so watermark advances only after successful object load
- [x] 2.3 Add overlap-window handling for retry safety without changing in-scope delete behavior

## 3. Incremental load behavior

- [x] 3.1 Update extraction task logic to filter by watermark and process only inserts/updates
- [x] 3.2 Implement idempotent load semantics keyed by Salesforce `Id` for reruns/retries
- [x] 3.3 Preserve existing audit columns (`extracted_at`, `dag_run_id`) in incremental writes

## 4. Tests and validation

- [x] 4.1 Add tests that fail if SOQL contains `SELECT *` and verify explicit field usage per object
- [x] 4.2 Add tests for watermark bootstrap, incremental filtering, deterministic ordering, and watermark advancement rules
- [x] 4.3 Add tests confirming delete strategy is not implemented in this change (inserts/updates only)

## 5. Deployment and verification

- [x] 5.1 Capture runbook notes for known limitation (no hard-delete handling) and follow-up change reference

## 1. Query Compatibility Logic

- [x] 1.1 Locate the Salesforce query-construction path used by `extract_accounts`, `extract_opportunities`, and `extract_contacts` and isolate where curated field lists are converted into SOQL.
- [x] 1.2 Implement a shared field-compatibility helper used by all Salesforce object extractions in this DAG.
- [x] 1.3 In the helper, add object describe metadata retrieval and build the final select list as curated fields intersected with available object fields.
- [x] 1.4 In the helper, enforce required tracking fields (`Id`, `SystemModstamp`) after filtering and raise a clear pre-query error if either is unavailable.

## 2. Observability and Runtime Behavior

- [x] 2.1 Add warning logs for skipped curated fields, including object name and skipped field names.
- [x] 2.2 Add info logs for final selected fields per object before query execution.
- [x] 2.3 Verify incremental query semantics are preserved (`SystemModstamp` filter and `ORDER BY SystemModstamp, Id`).
- [x] 2.4 Keep metrics out of scope for this change; ensure logging is sufficient to diagnose field-compatibility outcomes.

## 3. Tests and Validation

- [x] 3.1 Update or add unit tests for SOQL construction to cover missing optional fields (e.g., Opportunity without `CurrencyIsoCode`) and explicit-field query output.
- [x] 3.2 Add test coverage for fail-fast behavior when required tracking fields would be absent from the final selected list.
- [x] 3.3 Run the relevant test suite and confirm no regressions in DAG structure or extraction query behavior.

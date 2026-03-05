## 1. Schema Naming Alignment

- [x] 1.1 Implement dbt schema naming configuration so model `+schema` values resolve to canonical schemas (`staging`, `intermediate`, `marts`) without target-schema prefixing.
- [x] 1.2 Verify dbt project/profile configuration remains consistent with canonical schema contract and does not reintroduce prefixed modeled schemas.

## 2. Validation and Warehouse Verification

- [x] 2.1 Run the Salesforce dbt transformation flow and verify modeled objects materialize in `staging`, `intermediate`, and `marts`.
- [x] 2.2 Confirm prefixed modeled schemas (`staging_staging`, `staging_intermediate`, `staging_marts`) are not populated by the updated run.

## 3. Documentation and Operational Clarity

- [x] 3.1 Update operational documentation/runbook references to declare canonical modeled schemas as the supported contract.
- [x] 3.2 Add or update tests/assertions that guard against regressions in schema naming behavior.

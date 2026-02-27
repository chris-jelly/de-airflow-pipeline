## Why

`extract_opportunities` is retrying because the current Opportunity SOQL includes `CurrencyIsoCode`, which is not available in the target Salesforce org (`INVALID_FIELD`). Authentication and connectivity are already healthy (`extract_accounts` and `extract_contacts` succeed), so this is a schema-compatibility gap in the DAG query construction for opportunities.

## What Changes

- Update opportunity extraction to avoid querying fields that are not present on `Opportunity` in the connected org.
- Preserve incremental behavior (`SystemModstamp` watermark, deterministic `ORDER BY SystemModstamp, Id`) while adapting the selected field list to the org schema.
- Add validation and observability around selected vs. skipped fields so schema mismatches are visible without failing extraction for optional fields.
- Add/adjust tests to cover object field compatibility handling and prevent regressions for invalid-field query failures.

## Capabilities

### New Capabilities
- `salesforce-field-compatibility-selection`: Build object queries from curated fields intersected with fields available in the connected Salesforce org, with clear logging for skipped fields.

### Modified Capabilities
- `salesforce-incremental-watermark-extract`: Strengthen extraction requirements so curated field selection is schema-compatible per object while keeping watermark-driven incremental semantics unchanged.

## Impact

- Affected code: Salesforce extraction query-building logic in the Airflow DAG for `Opportunity` (and shared extraction helper paths used by other objects).
- Affected behavior: Opportunity task no longer fails on unsupported optional fields; extraction remains incremental and deterministic.
- Affected testing: DAG/unit tests for SOQL composition and extraction-path resilience to missing Salesforce fields.

## Context

The Airflow Salesforce extraction DAG currently builds SOQL using curated static field lists per object. In production, `extract_opportunities` fails with `SalesforceMalformedRequest (INVALID_FIELD)` because `CurrencyIsoCode` is included in the Opportunity select list but is not available in the connected org. Connectivity is confirmed healthy because account and contact extractions succeed.

The change must preserve existing incremental semantics: per-object `SystemModstamp` watermark filtering, deterministic ordering by `SystemModstamp, Id`, and retry-safe loading behavior.

## Goals / Non-Goals

**Goals:**
- Prevent extraction failures caused by optional curated fields that do not exist in the connected Salesforce org.
- Keep curated explicit field selection and incremental watermark behavior unchanged in intent.
- Improve operator visibility by logging which curated fields are skipped per object.
- Add regression tests that cover invalid-field prevention for opportunity extraction.

**Non-Goals:**
- Redesign object mapping or bronze table modeling.
- Implement Salesforce delete capture.
- Change authentication, connection setup, or secret mounting.

## Decisions

- Build SOQL from `curated_fields INTERSECT available_object_fields`.
  - Rationale: keeps curated intent while adapting to org-specific schema differences.
  - Alternative considered: remove `CurrencyIsoCode` only. Rejected because the next missing optional field would cause the same runtime failure.
- Treat `Id` and `SystemModstamp` as required extraction fields.
  - Rationale: these fields are required for deterministic ordering, watermarking, and idempotent merge semantics.
  - Alternative considered: make all fields optional. Rejected because dropping key tracking fields would break correctness.
- Fetch available fields from Salesforce object describe metadata during task execution and construct query before running extraction.
  - Rationale: metadata reflects the connected org at runtime and avoids hardcoding org assumptions.
  - Alternative considered: static environment-specific field profiles. Rejected due to operational drift and maintenance burden.
- Log selected and skipped curated fields for each object at info/warn level.
  - Rationale: gives immediate diagnostics for schema mismatch without hard task failure for optional fields.
- Implement field-compatibility filtering as a shared helper used by all Salesforce object extractions in this DAG.
  - Rationale: prevents divergence between object paths and makes future object onboarding mostly configuration-driven.
  - Alternative considered: inline filtering logic per object branch. Rejected due to duplication and higher regression risk.
- Defer custom metrics instrumentation for this change; prioritize reliable logging first.
  - Rationale: current observability baseline is minimal, and logs provide immediate operational value without adding infra/config complexity.

## Risks / Trade-offs

- Describe call adds API overhead per extraction task -> mitigate by fetching describe once per object per run and reusing it in query construction.
- Silent data sparsity if too many optional fields are skipped -> mitigate by explicit warning logs that list skipped fields and by tests asserting required fields are always present.
- Schema drift could still break extraction if required fields are unavailable -> mitigate with fail-fast validation and actionable error messages before query execution.

## Migration Plan

- Deploy DAG update with schema-compatible field filtering and logging.
- Validate in Airflow that `extract_opportunities` no longer retries on `INVALID_FIELD` and continues to produce bronze rows.
- Rollback strategy: revert to previous DAG revision if unexpected extraction behavior appears.

## Open Questions

- Should skipped optional field counts be emitted as metrics in addition to logs?
- If metrics are added later, should they use Airflow StatsD naming conventions or an app-specific namespace?

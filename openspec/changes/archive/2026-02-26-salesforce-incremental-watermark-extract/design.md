## Context

The current Salesforce DAG builds invalid SOQL (`SELECT *`) and uses a full-object append load, which both fails at runtime and creates long-term data quality risk in bronze tables. The team has aligned on a watermark-only incremental strategy for now, with hard-delete handling explicitly deferred.

The change touches DAG extraction behavior, query construction, and run-state management across three Salesforce objects (`Account`, `Contact`, `Opportunity`). The existing Airflow and connection patterns remain in place and should not be reworked.

## Goals / Non-Goals

**Goals:**
- Replace invalid wildcard SOQL with explicit curated field lists per object.
- Extract only changed rows by `SystemModstamp` using per-object watermark state.
- Make incremental queries deterministic (`ORDER BY SystemModstamp, Id`) and safe for retries.
- Preserve current DAG structure (TaskFlow topology and object coverage) while changing extraction semantics.

**Non-Goals:**
- Implementing Salesforce hard-delete capture or reconciliation.
- Replatforming to CDC/event-driven ingestion.
- Reworking broader medallion architecture beyond this DAG's bronze responsibilities.

## Decisions

- **Use `SystemModstamp` as the watermark field.**
  - Rationale: It is available on all target objects and is appropriate for change-tracking windows.
  - Alternative considered: `LastModifiedDate` as watermark. Rejected because `SystemModstamp` is the preferred replication-oriented timestamp for this use case.

- **Adopt curated explicit field lists rather than dynamic `describe`-driven query generation at runtime.**
  - Rationale: Explicit lists are deterministic, testable, and reduce runtime metadata dependency.
  - Alternative considered: runtime metadata discovery to auto-build `SELECT` fields. Rejected for now to minimize moving parts and failure modes.

- **Persist per-object watermark state and only advance on successful object load.**
  - Rationale: Prevents data loss from partial failures and enables safe retries.
  - Alternative considered: storing watermark in Airflow Variables only. Rejected due to weaker traceability and coupling to scheduler metadata; a DB-backed state record is preferred.

- **Use overlap and idempotent merge semantics for retry safety.**
  - Rationale: Small overlap windows reduce edge-case misses around commit timing; idempotent load prevents duplicates.
  - Alternative considered: strict `>` without overlap. Rejected due to potential missed rows at window boundaries.

- **Keep delete strategy out of scope in this change.**
  - Rationale: The immediate issue is correctness of incremental upserts. Delete capture can be a dedicated follow-up change.

## Risks / Trade-offs

- **[Risk]** Curated field lists drift from org schema over time. **-> Mitigation:** Add tests/validation that verify configured fields exist and fail fast with actionable errors.
- **[Risk]** Incorrect watermark advancement can skip updates. **-> Mitigation:** Advance watermark only after successful write/merge and validate row counts/logged boundaries.
- **[Risk]** Overlap window increases repeated rows per run. **-> Mitigation:** Enforce deterministic ordering plus idempotent merge keyed by Salesforce `Id`.
- **[Risk]** Hard deletes remain invisible. **-> Mitigation:** Document as accepted limitation and plan a dedicated delete-strategy change.

## Migration Plan

1. Introduce curated field configuration and watermark-aware query generation in the DAG logic.
2. Create and initialize watermark state storage for each object.
3. Deploy changes and run one controlled backfill/bootstrap cycle to establish first watermark values.
4. Monitor first scheduled runs for row counts, watermark movement, and duplicate behavior.
5. Roll back by reverting to previous DAG image if needed; no destructive schema migration is required for rollback.

## Open Questions

- Should bronze target semantics be append-only plus downstream dedupe, or direct upsert to a current-state bronze table?
- What overlap duration should be defaulted (for example, 5 minutes vs 15 minutes) based on observed run durations?
- Where should watermark state live in Postgres (dedicated metadata table in `bronze` schema vs separate metadata schema)?

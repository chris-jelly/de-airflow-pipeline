## Context

The existing Salesforce extraction DAG loads `Account`, `Contact`, and `Opportunity` into `bronze` PostgreSQL tables with mostly text-typed source fields and incremental watermark extraction by `SystemModstamp`. The repository does not yet contain a dbt project or dbt orchestration DAG, but platform patterns already support per-DAG container images and pod-level secret mounting.

During exploration, the team aligned on dropping `bronze/silver/gold` schema semantics in favor of dbt-native layering (`raw` landing plus `staging`, `intermediate`, `marts`). This change therefore expands scope to include updates to the existing extraction DAG contract.

The new change must introduce a transformation layer that is reliable in low-change test environments, supports eventual dashboard use cases, and remains aligned with current Airflow and dbt modeling conventions.

## Goals / Non-Goals

**Goals:**
- Add a dedicated Airflow DAG that runs dbt transformation and validation workflows for Salesforce data.
- Build typed staging/intermediate models from raw Salesforce landing data with explicit casting and normalization rules.
- Define a clear quality severity model (`error`, `warn`, `info`) that is strict for structural correctness and tolerant for expected source drift.
- Produce query-oriented marts and lightweight opportunity history suitable for future Streamlit dashboards.
- Keep orchestration independently schedulable while avoiding wasteful no-op dbt runs when raw data has not changed.
- Replace extraction landing schema naming from `bronze` to `raw_salesforce` and align task/schema naming accordingly.

**Non-Goals:**
- Replacing the existing Salesforce extraction DAG or changing its object scope.
- Implementing production dashboard code (Streamlit app) in this change.
- Building full enterprise SCD2 history for every Salesforce entity.
- Solving Salesforce hard-delete replication (still deferred).

## Decisions

### 1) Schema strategy: single database with layer-specific schemas

The solution uses one Postgres database (`warehouse`) with schema boundaries instead of separate databases:
- `raw_salesforce` for ingestion landing tables
- `staging`, `intermediate`, and `marts` for dbt model layers

- Rationale: keeps operations simple at current scale while preserving clear lifecycle boundaries.
- Alternative considered: dedicated raw database with per-source schemas. Rejected as unnecessary complexity for current scope.

### 2) Orchestration pattern: independent schedule with freshness guard

The dbt DAG will run on its own schedule, but execution will be gated by a pre-check against raw freshness markers (for example `max(SystemModstamp)`/`max(extracted_at)` across source tables). If no new raw data is present since the last successful dbt run, the DAG short-circuits.

- Rationale: preserves independent operability and easier testing while approximating event-driven execution.
- Alternative considered: strict DAG-to-DAG chaining from extraction to dbt run. Rejected for lower operational flexibility and tighter failure coupling.

### 3) dbt model layering: staging -> intermediate -> marts

The dbt project will follow dbt-native layers:
- `staging`: one model per raw source table with typing and light normalization.
- `intermediate`: entity-level current-state and reusable transformations.
- `marts`: query-ready dimensions/facts and a lightweight opportunity history output.

- Rationale: clear lineage, composability, and alignment with current platform direction.
- Alternative considered: direct bronze-to-mart transforms. Rejected because it couples cleaning with business logic and reduces maintainability.

### 4) Incremental correctness for mutable Salesforce entities

Incremental logic will key off `SystemModstamp` as the technical change timestamp. Models requiring current-state semantics will use upsert-style incremental behavior (unique-key based) so corrections to older business-dated records are captured.

- Rationale: addresses late-arriving updates and mutable records without depending on business dates like `CloseDate`.
- Alternative considered: incremental by business date only. Rejected because post-close edits would be missed.

### 5) First-pass type policy from raw text fields

Staging models will explicitly cast into target types:
- ids and free-form fields as text
- money as numeric
- counts/probability as numeric or integer
- booleans as boolean
- business dates as date
- operational timestamps as timestamptz

Invalid cast behavior will yield null typed values and be surfaced by validation tests.

- Rationale: preserves load continuity while making data quality issues visible.
- Alternative considered: hard-fail on first bad value. Rejected for poorer resilience and less actionable observability.

### 6) Quality severity model

Validation outcomes are tiered:
- `error`: fail dbt build for contract-breaking issues (key null/uniqueness, required relationships, critical range constraints).
- `warn`: non-blocking checks for likely source or model drift (accepted values drift, soft freshness breaches, cast-failure thresholds).
- `info`: monitor-only diagnostics (distribution and volume changes).

- Rationale: balances trust guarantees with practical behavior in a low-change test org.
- Alternative considered: all-tests-as-errors. Rejected due to excessive brittleness and operational noise.

### 7) History strategy: lightweight opportunity snapshots

### 8) Existing extraction DAG contract update

The existing Salesforce extraction DAG will be updated to create and write into `raw_salesforce` instead of `bronze`, including renamed schema-creation task naming in DAG code/tests and updated target table references.

- Rationale: avoids mixed terminology and keeps ingestion semantics explicit.
- Alternative considered: keep `bronze` and map to `raw` conceptually in docs only. Rejected because it preserves ambiguity and ongoing cognitive overhead.

The design includes a bounded history pattern for opportunities (for example daily or run-scoped snapshots at opportunity grain) instead of broad SCD2 across all entities.

- Rationale: enables trend and pipeline movement analysis with low complexity.
- Alternative considered: no history outputs. Rejected because it limits future analytics and dashboard value.

## Risks / Trade-offs

- [Schema drift between Salesforce orgs can alter field availability] -> Mitigation: keep staging models explicit, track cast/null anomalies, and document optional-field handling.
- [Independent scheduling can still run unnecessarily] -> Mitigation: implement freshness pre-check short-circuit and verify runtime metrics.
- [Schema rename can break existing downstream references] -> Mitigation: update DAG/tests/specs in same change and verify no remaining `bronze` references in active code paths.
- [Severity thresholds may initially be too strict or too lax] -> Mitigation: start with conservative defaults and tune via observed runs.
- [Snapshot history can grow over time] -> Mitigation: define retention/partition strategy and keep initial scope to opportunities only.
- [Additional dbt image/dependency path increases operational footprint] -> Mitigation: follow existing per-DAG image pattern and CI matrix extension.

## Migration Plan

1. Update extraction DAG contract from `bronze` to `raw_salesforce` and adjust tests.
2. Scaffold dbt project and model folders for Salesforce transformations.
3. Add dbt execution DAG and runtime image/dependencies.
4. Deploy staging typed models and baseline tests.
5. Deploy intermediate and marts models including opportunity history output.
6. Enable severity-based validations and tune thresholds after initial runs.
7. Promote with rollback path: disable new DAG and optionally restore prior schema naming if required.

## Open Questions

- What exact freshness signal should govern dbt short-circuiting (`SystemModstamp`, `extracted_at`, or a combined watermark table view)?
- What snapshot cadence best fits expected test-org usage (per run vs daily)?
- Should initial relationship tests for optional links be warning-only until data quality baseline stabilizes?

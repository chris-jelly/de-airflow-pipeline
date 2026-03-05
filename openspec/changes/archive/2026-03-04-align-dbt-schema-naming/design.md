## Context

The Salesforce transformation stack is designed around canonical warehouse layers: `raw_salesforce`, `staging`, `intermediate`, and `marts`. In runtime, dbt currently materializes modeled outputs into prefixed schemas (`staging_staging`, `staging_intermediate`, `staging_marts`) due to default schema concatenation behavior, which diverges from the intended contract and from schema bootstrap behavior in the Airflow DAG.

This change standardizes materialization to canonical modeled schemas in the current single-environment homelab deployment.

## Goals / Non-Goals

**Goals:**
- Ensure dbt models land in `staging`, `intermediate`, and `marts` exactly.
- Keep raw ingestion and pipeline state in `raw_salesforce`.
- Align runtime behavior with documented architecture and operator expectations.
- Preserve existing model logic, dependency graph, and freshness-gated orchestration.

**Non-Goals:**
- Introducing multi-environment schema isolation patterns (dev/staging/prod) in this change.
- Redesigning dbt model SQL, marts semantics, or quality policy behavior.
- Performing broad warehouse refactors beyond modeled schema naming alignment.

## Decisions

### 1) Canonical schema contract for modeled layers
Modeled dbt layers will materialize to fixed schema names: `staging`, `intermediate`, and `marts`.

- Rationale: this is the explicit architecture target and avoids cognitive overhead from prefixed schema drift.
- Alternative considered: retain prefixed names and update documentation. Rejected because it preserves accidental behavior and conflicts with existing operational intent.

### 2) Preserve raw schema boundary
`raw_salesforce` remains the sole landing and state schema for extraction tables and dbt pipeline state.

- Rationale: maintains clear separation between ingestion and modeled analytics layers.
- Alternative considered: consolidate state metadata into modeled schemas. Rejected to avoid mixing ingestion state with transformed data layers.

### 3) No compatibility bridge required
The change assumes direct adoption of canonical schema names without maintaining long-lived compatibility aliases for prefixed schema names.

- Rationale: current environment is single-tenant homelab with no required staged cutover.
- Alternative considered: temporary compatibility views between old and new names. Rejected as unnecessary operational overhead for current scope.

## Risks / Trade-offs

- [Risk] Existing ad hoc queries may reference `staging_*` schemas. -> Mitigation: communicate canonical schema contract and validate critical queries after change.
- [Risk] Schema naming overrides could be unintentionally changed later by dbt config drift. -> Mitigation: codify the requirement in OpenSpec and add explicit checks in validation steps.
- [Trade-off] We intentionally do not optimize for future multi-environment isolation in this change. -> Mitigation: if environments are introduced later, propose a separate change to define environment-aware schema naming policy.

## Migration Plan

1. Implement dbt schema naming alignment so modeled layers resolve to canonical schema names.
2. Run transformation DAG and verify model objects materialize under `staging`, `intermediate`, and `marts`.
3. Confirm no new objects are created in `staging_staging`, `staging_intermediate`, or `staging_marts`.
4. Remove any now-unused prefixed modeled schemas if present.

Rollback: restore prior dbt schema naming behavior and rerun transformation DAG to rematerialize prefixed schemas.

## Open Questions

- Should a lightweight automated check be added to fail runs if prefixed modeled schemas reappear?

## Context

This repo's DAGs target Airflow 2.x patterns but the homelab deployment now runs Airflow 3. The existing Salesforce DAG syncs via git-sync but doesn't execute correctly. The K3d local dev environment still targets Airflow 2.8.1, so there's no way to develop or test against the production runtime.

The codebase follows a per-DAG container image strategy (ADR-001) with pod-level secret mounting (ADR-002). The Salesforce DAG uses `PythonOperator` with direct hook parameter passing — reading env vars from pod-mounted secrets and passing them as constructor args to `PostgresHook` and `SalesforceHook`. This bypasses Airflow's connection management entirely.

## Goals / Non-Goals

**Goals:**

- Make all DAGs parse and execute correctly on Airflow 3.x
- Add a Postgres ping DAG as a minimal smoke test for the deployment pipeline
- Modernize the Salesforce DAG to TaskFlow API and `conn_id`-based hooks
- Update K3d Helm values so local dev matches the production Airflow 3 environment
- Preserve the security model from ADR-002 (pod-level secret isolation)

**Non-Goals:**

- Changing the homelab repo (Airflow Connections config is out of scope but noted)
- Changing the per-DAG container image strategy (ADR-001)
- Adding new Salesforce objects or changing extraction logic
- Production deployment or CI/CD pipeline changes

## Decisions

### 1. Use `AIRFLOW_CONN_*` environment variables for `conn_id`-based hooks

**Decision:** Switch hooks from direct parameter passing to `conn_id` references, with connections defined via `AIRFLOW_CONN_*` environment variables mounted in pod overrides.

**Rationale:** Airflow supports defining connections as environment variables in URI or JSON format (e.g., `AIRFLOW_CONN_WAREHOUSE_POSTGRES='postgresql://user:pass@host:5432/db'`). This lets us use the standard `conn_id` API while keeping secrets mounted only in executor pods — preserving ADR-002's security model. The scheduler/webserver never see these env vars.

**Alternatives considered:**
- *Airflow Connections in metadata DB:* Rejected per ADR-002 — stores credentials in the DB, visible to all components.
- *Keep direct parameter passing:* Works but fragile, not the supported API path in Airflow 3 providers, and no connection testing or UI visibility.

**Downstream impact:** The homelab repo will need to construct `AIRFLOW_CONN_*` env vars from existing Kubernetes secrets and mount them in the Airflow Helm values or pod template. This is out of scope for this change.

### 2. Postgres ping DAG runs on the base Airflow image (no custom container)

**Decision:** The Postgres ping DAG will not have its own Dockerfile or `pyproject.toml`. It will run on the base `apache/airflow` image using only `apache-airflow-providers-postgres`, which is included in the base image.

**Rationale:** The purpose of this DAG is to validate that DAG sync, task execution, and Postgres connectivity work. Adding container build complexity defeats the point — if the base image can't run a simple Postgres query, we have bigger problems. The DAG needs no extra dependencies (no pandas, no salesforce provider).

**Alternatives considered:**
- *Own container per ADR-001:* Unnecessarily complex for a health-check DAG with zero custom dependencies.

**Structure:** `dags/postgres-ping/postgres_ping_dag.py` — a single file, no package structure needed.

### 3. TaskFlow API for both DAGs

**Decision:** Use `@dag` and `@task` decorators for both the new Postgres ping DAG and the refactored Salesforce DAG.

**Rationale:** TaskFlow is the primary API in Airflow 3. It eliminates boilerplate (`PythonOperator`, `op_kwargs`, explicit `dag=dag` assignments), provides automatic XCom serialization, and is what the Airflow docs now teach. Since we're already doing a significant refactor of the Salesforce DAG (hook pattern change), migrating to TaskFlow at the same time minimizes total disruption.

**Alternatives considered:**
- *TaskFlow for new DAG only, keep classic for Salesforce:* Avoids risk on the Salesforce DAG but means maintaining two patterns in the same repo.

### 4. Airflow 3.x image tag for K3d

**Decision:** Update `k3d/values-airflow.yaml` to use `apache/airflow:3.1.5-python3.13`, matching the version already specified in `dags/salesforce/pyproject.toml` and `dags/salesforce/Dockerfile`.

**Rationale:** The DAG code and Dockerfile already target 3.1.5. The Helm values are the only thing still pinned to 2.8.1. Aligning them eliminates the version mismatch between scheduler/webserver and executor pods.

### 5. Helm config section renames and removals

**Decision:** Apply the following changes to `k3d/values-airflow.yaml`:
- Rename `config.kubernetes` → `config.kubernetes_executor`
- Remove `config.api.auth_backends` (Airflow 3 uses FastAPI with its own auth)
- Keep `flower.enabled: false` and `redis.enabled: false` (harmless, documents intent)

**Rationale:** These are breaking config changes in Airflow 3. The `[kubernetes]` section was renamed to `[kubernetes_executor]`. The REST API auth backend config is no longer applicable since Airflow 3 replaced the Flask-based API with FastAPI.

### 6. Salesforce DAG `executor_config` refactored to use connection URI env vars

**Decision:** Replace the individual secret env vars (`POSTGRES_HOST`, `POSTGRES_USER`, etc.) with composed `AIRFLOW_CONN_*` env vars in the pod override. The connection URI will be constructed from the same Kubernetes secrets using variable interpolation or an init container.

**Rationale:** With `conn_id`-based hooks, the individual env vars are no longer needed. The `AIRFLOW_CONN_*` format is what Airflow reads to populate its connection registry at the pod level.

**Trade-off:** Constructing a connection URI from individual secret keys is more complex in Kubernetes manifests (K8s doesn't support env var interpolation natively). Options:
- Store the full connection URI as a single secret key (simplest, requires homelab repo change)
- Use an init container or entrypoint script to compose the URI from individual keys
- Keep individual env vars *and* add the `AIRFLOW_CONN_*` var (redundant but pragmatic for migration)

**Decision:** For now, define the `AIRFLOW_CONN_*` env vars in the pod override assuming the homelab repo will provide pre-composed connection URI secrets. Document the required secret format. The K3d local dev values will hardcode test connection URIs directly.

## Risks / Trade-offs

- **[Risk] Salesforce provider `conn_id` behavior untested** → Mitigation: The Salesforce provider's `conn_id` support for OAuth flows needs verification. If `SalesforceHook(salesforce_conn_id=...)` doesn't support the consumer key/secret OAuth pattern via connection extras, we may need to keep direct parameter passing for the Salesforce hook specifically. Research the provider docs during implementation.

- **[Risk] Airflow 3 Helm chart compatibility** → Mitigation: The official Airflow Helm chart version must support Airflow 3 images. Verify which chart version is needed (likely chart version 2.x+). The K3d setup scripts may need a Helm repo update.

- **[Risk] Test breakage from TaskFlow migration** → Mitigation: The existing tests import `dag` directly and inspect tasks. TaskFlow DAGs create task objects differently. Tests will need to be updated to match, but the assertions (task IDs, dependencies, executor config) remain the same conceptually.

- **[Trade-off] Two connection patterns during migration** → The Salesforce DAG in this repo will use `conn_id`, but the homelab repo needs to provide `AIRFLOW_CONN_*` env vars. Until the homelab repo is updated, the Salesforce DAG won't execute in production. The Postgres ping DAG (using the Airflow metadata DB connection) will work immediately.

- **[Trade-off] Postgres ping DAG skips per-DAG container strategy** → Intentional. A health-check DAG with zero custom dependencies doesn't warrant its own image. If it later grows to need custom deps, it can be containerized then.

## Migration Plan

1. Update K3d Helm values and verify the local cluster starts with Airflow 3
2. Add the Postgres ping DAG — verify it parses and executes in K3d
3. Refactor the Salesforce DAG (TaskFlow + conn_id pattern)
4. Update tests for both DAGs
5. Update documentation (`CONTAINER_STRATEGY.md`, `KUBERNETES.md`)
6. Build and push updated Salesforce container image
7. (Out of scope) Homelab repo: configure `AIRFLOW_CONN_*` secrets, update Helm values

**Rollback:** Git revert. The homelab repo's git-sync will pick up the previous DAG version. No database migrations or stateful changes involved.

## Open Questions

- ~~Which Airflow Helm chart version is required for Airflow 3.x images?~~ **Resolved:** Helm chart version 1.19. The K3d setup scripts should pin to this version.
- ~~Does `SalesforceHook` support OAuth consumer key/secret via `conn_id` extras, or only username/password?~~ **Resolved:** Yes. `SalesforceHook(salesforce_conn_id=...)` supports OAuth 2.0 JWT authentication via connection extras (Consumer Key + Private Key). The old direct `consumer_key`/`consumer_secret`/`domain` kwargs are not part of the current constructor signature. The `AIRFLOW_CONN_SALESFORCE` env var will need to encode the OAuth credentials in JSON extras format.
- ~~Should the Postgres ping DAG use the Airflow metadata DB connection (`airflow_db`) or expect a separate warehouse Postgres connection?~~ **Resolved:** Use the external warehouse Postgres connection (`warehouse_postgres_{env}`). This validates the full `AIRFLOW_CONN_*` pod-level secret mounting pattern end-to-end. The DAG will need an `executor_config` pod override to mount the connection env var, same pattern as the Salesforce DAG.

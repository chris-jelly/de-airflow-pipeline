## Context

The Salesforce dbt transformation DAG executes dbt commands from the dbt project directory. In KubernetesExecutor environments that use git-sync, DAG source code is mounted read-only in worker pods. dbt writes runtime artifacts such as compiled output, manifests, and logs by default, which causes failures when those writes target read-only paths.

The current implementation also wraps dbt failures as `CalledProcessError` without consistently emitting dbt stdout/stderr, which slows down operational triage.

## Goals / Non-Goals

**Goals:**
- Ensure dbt build/test commands run successfully when project code is mounted read-only.
- Route dbt runtime writes to writable ephemeral paths.
- Improve task logs so dbt failures include actionable stderr/stdout context.
- Add tests that enforce runtime write-path behavior and logging expectations.

**Non-Goals:**
- Changing dbt model logic or quality thresholds.
- Introducing persistent artifact storage for dbt outputs.
- Reworking Airflow git-sync topology or Kubernetes volume mounts.

## Decisions

### 1) Use writable `/tmp` paths for dbt runtime artifacts

dbt command execution will set environment variables for writable locations (`DBT_TARGET_PATH`, `DBT_LOG_PATH`, and `DBT_PACKAGES_INSTALL_PATH`) under `/tmp/dbt`.

- Rationale: `/tmp` is writable in worker containers and isolates runtime artifacts from immutable source code.
- Alternative considered: write into project-relative directories. Rejected because git-sync DAG mounts are read-only in production-like environments.

### 2) Keep project discovery dynamic via DAG file location

The dbt project directory remains resolved from the DAG file path (already updated), which supports both local and git-sync layouts.

- Rationale: avoids hardcoded path assumptions across deployment topologies.
- Alternative considered: fixed absolute path. Rejected due to environment-dependent mount structure.

### 3) Capture dbt subprocess output in task logs

dbt subprocess invocation will capture output and emit structured logs on success/failure, including command, return code, and stderr snippets on error.

- Rationale: removes opaque failure mode where Airflow only surfaces wrapper exceptions.
- Alternative considered: rely on default subprocess logging. Rejected due to incomplete context in current task logs.

### 4) Add focused tests for runtime config behavior

DAG tests will validate that dbt commands are invoked with environment variables that route writes to writable paths and that failure logging paths are exercised.

- Rationale: prevents regressions from future path refactors.
- Alternative considered: only manual k3d verification. Rejected because automated guardrails are needed in CI.

## Risks / Trade-offs

- [Ephemeral artifacts are lost after pod completion] -> Mitigation: rely on Airflow logs for operational diagnostics, keep artifact persistence out of scope.
- [Environment variable drift between build/test tasks] -> Mitigation: centralize dbt environment construction in one helper.
- [Verbose stderr logging may expose sensitive values] -> Mitigation: avoid logging credential env vars and log command/output only.
- [Tests may overfit subprocess implementation details] -> Mitigation: assert behavioral contracts (write paths/logging) rather than exact command formatting.

## Migration Plan

1. Update dbt DAG command environment construction to include `/tmp` write paths.
2. Update dbt subprocess handling to log stdout/stderr with failure context.
3. Add/adjust unit tests for runtime write-path behavior and logging.
4. Validate with local pytest and one k3d run against git-sync mounted DAGs.
5. Rollback path: revert to previous DAG revision if unexpected runtime behavior appears.

## Open Questions

- Should dbt `target/` and logs be optionally shipped to object storage in a follow-up change for post-run artifact retention?
- Do we want a shared helper pattern for all tool-based DAG tasks that need writable runtime paths in read-only DAG mounts?

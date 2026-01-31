# k3d Environment Management

- Scripts are located in `scripts/` and should be executable.
- `cluster-config.yaml` defines the cluster topology.
- Scripts should use `#!/bin/bash` and `set -euo pipefail` for robustness.
- When using `grep` in a pipeline with `pipefail`, handle exit code 1 (no matches) if that is a valid state (e.g., `... | grep pattern || true`).
- Network verification scripts should use a transient `busybox` pod to verify DNS and external connectivity.
- Resource checks can query node conditions (MemoryPressure, DiskPressure, PIDPressure) via `kubectl get nodes -o jsonpath`.

## Helm Configuration
- For `KubernetesExecutor` local development, use `podTemplate` value to inject `hostPath` volumes into worker pods. Top-level `extraVolumes` only apply to Scheduler/Webserver.
- Ensure `postgresql.auth` credentials match `data.metadataConnection` in the values file.

## Image Registry & Tagging
- The local registry is available at `localhost:5111` (host) and `k3d-registry.localhost:5000` (cluster).
- Tag images as `localhost:5111/name:tag` for pushing from the host.
- Inside the cluster, images can be pulled from the registry or loaded directly via `k3d image import` (though registry is preferred for this pipeline).
- When using `docker build` for DAGs, run from the `REPO_ROOT` context to include shared configuration if needed, even if the Dockerfile is in `dags/{type}`.

## Helm Chart Gotchas (Airflow 1.12.0)
- `{{ .Release.Name }}` cannot be used in `values.yaml` files. Hardcode service names or use external config management.
- `helm upgrade --install --wait` can cause a deadlock with `post-install` hooks (like `migrateDatabaseJob`) if pods wait for the hook (via init containers). Set `migrateDatabaseJob.useHelmHooks: false` to run the job as a standard resource.
- Validating keys: `workers.enabled` and `createUserJob.enabled` are not valid in this chart version.
- Bitnami PostgreSQL images for local dev: verify tag availability. `latest` works for local `k3d`, but specific versions like `16.1.0` might be missing from public repos or require specific `debian` suffix combinations.

## Airflow Configuration
- **API Authentication:** Default is `session`. To use Basic Auth (e.g., for curl/scripts), set `config.api.auth_backends` to `airflow.api.auth.backend.basic_auth,airflow.api.auth.backend.session`.
- **Volume Mounts:** `extraVolumes` and `extraVolumeMounts` must be defined under each component section (`scheduler`, `webserver`, `triggerer`) in `values.yaml`. Top-level definitions are ignored by the chart.
- **DAG Parsing:** Scheduler runs the default Airflow image. Ensure DAG top-level code does not import libraries (like `pandas`) not present in the base image. Use the Lazy Import Pattern.
- **Ignore Files:** Use `.airflowignore` with Regex patterns (e.g. `\.venv`) to exclude local virtual environments from DAG scanning to avoid recursive loop errors.


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

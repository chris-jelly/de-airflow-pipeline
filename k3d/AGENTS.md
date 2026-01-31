# k3d Environment Management

- Scripts are located in `scripts/` and should be executable.
- `cluster-config.yaml` defines the cluster topology.
- Scripts should use `#!/bin/bash` and `set -euo pipefail` for robustness.
- When using `grep` in a pipeline with `pipefail`, handle exit code 1 (no matches) if that is a valid state (e.g., `... | grep pattern || true`).

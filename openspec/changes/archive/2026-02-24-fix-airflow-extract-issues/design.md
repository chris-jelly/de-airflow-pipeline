## Context

The Salesforce extraction DAG has been failing on every run with `ModuleNotFoundError: No module named 'airflow.providers.salesforce'` since the Airflow 3 migration. Investigation revealed the root cause is not a missing dependency declaration — `apache-airflow-providers-salesforce>=5.12.0` is already in `dags/salesforce/pyproject.toml` — but a site-packages shadowing issue in the Dockerfile.

The base Airflow image (`apache/airflow:3.1.5-python3.13`) installs packages into `/home/airflow/.local/lib/python3.13/site-packages/`. The Dockerfile's `uv pip install --system .` installs into `/usr/python/lib/python3.13/site-packages/`. Only the former is on `sys.path`. Python finds the `airflow` package from the base image first and never searches the system site-packages for provider submodules.

Additionally, both DAGs use the deprecated `from airflow.decorators import dag, task` import path, and the salesforce `pyproject.toml` has a mismatched ruff `target-version`.

## Goals / Non-Goals

**Goals:**
- Fix the Salesforce provider import failure so all extract tasks run successfully
- Ensure Dockerfile dependency installs go to the correct site-packages location
- Pin the `uv` version for reproducible container builds
- Eliminate Airflow 3 deprecation warnings from DAG imports
- Correct the ruff `target-version` mismatch

**Non-Goals:**
- Changing extraction logic or adding new DAG functionality
- Adding CI test workflows (separate change)
- Addressing infrastructure-side warnings (git-sync env vars, JWT key length) — those live in the homelab repo
- Upgrading the base Airflow image version

## Decisions

### Decision 1: Install as `airflow` user without `--system`

**Choice:** Switch from `USER root` + `uv pip install --system` to `USER airflow` + `uv pip install` so dependencies install into `/home/airflow/.local/lib/python3.13/site-packages/`.

**Alternatives considered:**
- **Add `/usr/python/.../site-packages` to `PYTHONPATH`**: Would work but is fragile — it couples the Dockerfile to the internal layout of the base image, which could change between Airflow releases. Also creates ambiguity about which copy of a package wins when both site-packages dirs have it.
- **Use `pip` instead of `uv`**: Would install to the right place by default (as airflow user), but we want `uv` for speed and consistency with the rest of the toolchain.
- **Use `uv pip install --target`**: Overly complex — requires setting `PYTHONPATH` to the custom target.

**Rationale:** Installing as the `airflow` user without `--system` puts packages exactly where the base image's Python expects them. This is the simplest fix and avoids any path manipulation. The `uv` binary still needs to be copied as root, but the install step itself runs as `airflow`. The `root` user is still needed for `mkdir` and `COPY --chown`, so the Dockerfile switches users at the install step rather than at the end.

### Decision 2: Pin `uv` to a specific version tag

**Choice:** Replace `ghcr.io/astral-sh/uv:latest` with a specific version (e.g., `ghcr.io/astral-sh/uv:0.7.12`). Use the latest stable version at implementation time.

**Alternatives considered:**
- **Keep `:latest`**: Convenient but the current approach already demonstrated reproducibility issues. Different builds on the same commit can get different `uv` versions.
- **SHA-pin the image**: Maximum reproducibility but harder to maintain — requires manual updates and doesn't convey version information.

**Rationale:** Version tags provide both reproducibility and readability. The `uv` project publishes tags for every release. When `uv` needs updating, the version is changed explicitly in the Dockerfile.

### Decision 3: Import path is an implementation detail, not a spec-level requirement

**Choice:** The delta specs note the import path change under the existing "lazy import" and "TaskFlow API" requirements, but do not make the specific module path (`airflow.sdk` vs `airflow.decorators`) a normative requirement.

**Rationale:** The specs require "TaskFlow API (`@dag` and `@task` decorators)" — that's the behavioral requirement. The module path those decorators come from is an implementation detail that may change again in future Airflow versions. The delta specs update the allowed-import list in the lazy-import scenario to reflect `airflow.sdk` instead of `airflow.decorators`.

## Risks / Trade-offs

**[Risk] `uv pip install` without `--system` may behave differently regarding dependency resolution** → The base image's packages are in the user site-packages, so `uv` will see them as installed and only add missing ones. This is the desired behavior — it avoids reinstalling the entire Airflow stack. If resolution issues arise, `--reinstall-package <name>` can target specific packages.

**[Risk] Pinned `uv` version becomes stale** → Accepted trade-off. Stale-but-working is better than latest-but-broken. A future change or Dependabot/Renovate setup can address version bumps.

**[Risk] User-space install may need write permissions to `.local`** → The base Airflow image already sets up `/home/airflow/.local` with correct ownership for the `airflow` user. No additional permissions needed.

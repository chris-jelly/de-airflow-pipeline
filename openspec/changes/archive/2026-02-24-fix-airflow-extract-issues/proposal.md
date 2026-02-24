## Why

The `salesforce_extraction` DAG fails on every run with `ModuleNotFoundError: No module named 'airflow.providers.salesforce'`. The root cause is a site-packages shadowing bug in the Dockerfile: `uv pip install --system .` installs providers into `/usr/python/lib/python3.13/site-packages/`, but that path is not on `sys.path`. Python finds the `airflow` package from the base image's user site-packages (`/home/airflow/.local/...`) first, and never looks in the system site-packages for submodules. The Salesforce provider is on disk — Python just can't see it.

Additionally, both DAGs import `@dag` and `@task` from the deprecated `airflow.decorators` path instead of `airflow.sdk`, producing `DeprecatedImportWarning` on every task execution under Airflow 3.

## What Changes

- **Fix Dockerfile site-packages targeting**: Remove `--system` from the `uv pip install` command and run the install as the `airflow` user so dependencies go into `/home/airflow/.local/lib/python3.13/site-packages/` — the same location the base Airflow image uses and the only site-packages directory on `sys.path`. This fixes the provider import failure.
- **Pin `uv` version in Dockerfile**: Replace `ghcr.io/astral-sh/uv:latest` with a pinned version for reproducible builds.
- **Migrate DAG imports to `airflow.sdk`**: Update `from airflow.decorators import dag, task` to `from airflow.sdk import dag, task` in both `dags/salesforce/salesforce_extraction_dag.py` and `dags/postgres-ping/postgres_ping_dag.py` to eliminate deprecation warnings and align with Airflow 3 conventions.
- **Fix ruff `target-version`**: Update `dags/salesforce/pyproject.toml` from `target-version = "py311"` to `target-version = "py313"` to match `requires-python = ">=3.13"`.

## Capabilities

### New Capabilities

_None — this change fixes existing capabilities, it does not introduce new ones._

### Modified Capabilities

- `salesforce-dag`: Module-level import updated from `airflow.decorators` to `airflow.sdk` for `@dag` and `@task` decorators. The lazy-import requirement's allowed-import list needs updating to reflect `airflow.sdk` instead of `airflow.decorators`.
- `postgres-ping-dag`: Same import path migration from `airflow.decorators` to `airflow.sdk`.

## Impact

- **Dockerfile**: `dags/salesforce/Dockerfile` — install command changes from `uv pip install --system` (as root) to `uv pip install` (as airflow user); `uv` image tag pinned.
- **DAG files**: `dags/salesforce/salesforce_extraction_dag.py` and `dags/postgres-ping/postgres_ping_dag.py` — import statement changes.
- **Container image**: `ghcr.io/chris-jelly/de-airflow-pipeline-salesforce:latest` — rebuild will now correctly install providers into the importable site-packages.
- **CI**: The GitHub Actions workflow (`.github/workflows/build-and-push-container.yml`) will produce the fixed image on merge.
- **Tests**: Existing DAG structure tests may reference the old import path and need updating.
- **Specs**: Both `salesforce-dag` and `postgres-ping-dag` specs need delta specs to reflect the `airflow.sdk` import path.
- **Config**: `dags/salesforce/pyproject.toml` ruff `target-version` corrected to `py313`.

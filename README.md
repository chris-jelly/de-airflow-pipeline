# de-airflow-pipeline

An Apache Airflow project for running containerized data pipelines on Kubernetes.
It currently focuses on a Salesforce-to-Postgres flow with three parts: raw extraction, dbt transformations, and a lightweight Postgres health check.

## What lives here

- `dags/salesforce/` - Salesforce extraction DAG and its image-specific dependencies.
- `dags/dbt/` - dbt transformation DAG, dbt project, tests, and runbook.
- `dags/postgres-ping/` - hourly warehouse connectivity smoke-test DAG that runs on the base Airflow image.
- `k3d/` - local Kubernetes development environment for Airflow with KubernetesExecutor.
- `.devcontainer/` - reproducible dev container setup.
- `adrs/` - architecture decisions such as per-DAG images and pod-level secret mounting.
- `openspec/` - spec-driven change history and current requirements.

## Current pipeline

### 1. Salesforce extraction

The `salesforce` DAG pulls curated fields from Salesforce `Account`, `Contact`, and `Opportunity` objects and writes raw landing tables to the `raw_salesforce` schema.

Key traits:

- Uses Airflow TaskFlow API.
- Uses incremental extraction with `SystemModstamp` watermarks.
- Writes audit metadata such as `extracted_at` and DAG run identifiers.
- Mounts secrets only into executor pods through `executor_config`.

### 2. dbt transformations

The `salesforce_dbt_transformation` DAG runs dbt models against the raw landing data and materializes modeled layers into canonical warehouse schemas:

- `staging`
- `intermediate`
- `marts`

The DAG skips work when raw Salesforce data has not advanced since the last successful transformation run.

### 3. Postgres health check

The `postgres_ping` DAG runs an hourly `SELECT 1` against the warehouse connection to verify scheduler parsing, KubernetesExecutor task execution, and warehouse reachability.

## Development setup

### Tooling

This repo uses `mise` to install shared tools. The current toolchain includes:

- `uv`
- `pre-commit`
- `kubectl`
- `helm`
- `k3d`
- `k9s`
- `jq`
- Salesforce CLI

Install tools from the repo root:

```bash
mise install
```

Entering the project also triggers `scripts/setup_project` through the `mise` hook.

### Option 1: Dev container

If you want an isolated environment, use the dev container in `.devcontainer/`.
See `.devcontainer/README.md` for setup details.

### Option 2: Local shell

If you are working directly on the host:

```bash
mise install
pre-commit install
pre-commit install --hook-type commit-msg
```

## Working on DAGs

Each DAG lives in its own directory under `dags/` with its own `pyproject.toml`.
That keeps dependencies scoped to the DAG image that needs them.

Common commands:

```bash
# Test every DAG project
./scripts/test-all-dags.sh

# Work on the Salesforce extraction DAG
cd dags/salesforce
uv sync
uv run ruff check .
uv run pytest -v

# Work on the dbt DAG and dbt project
cd dags/dbt
uv sync
uv run ruff check .
uv run pytest -v
uv run dbt parse
```

## Local Airflow with k3d

The `k3d/` directory contains a local Kubernetes environment for running Airflow with `KubernetesExecutor`, local image builds, and Kubernetes secrets.

Quick start:

```bash
./k3d/scripts/full-setup.sh
```

That flow:

1. Creates the k3d cluster.
2. Prompts for Salesforce and Postgres secrets.
3. Builds and loads the `salesforce` and `dbt` DAG images.
4. Deploys Airflow through Helm.

After setup, Airflow is available at `http://localhost:30080` with default local credentials:

- username: `admin`
- password: `admin`

For the full workflow, troubleshooting steps, and cluster details, see `k3d/README.md`.

## Container builds

GitHub Actions builds separate GHCR images for DAGs that need custom dependencies:

- `ghcr.io/<owner>/<repo>-salesforce`
- `ghcr.io/<owner>/<repo>-dbt`

The workflow definition lives in `.github/workflows/build-and-push-container.yml`.

## Repository conventions

- Python packaging and task execution use `uv`.
- Python formatting and linting use `ruff`.
- Git hooks are managed with `pre-commit`.
- Commit messages are expected to use Commitizen format.
- Architectural decisions live in `adrs/`.
- Requirement and change artifacts live in `openspec/`.

## Useful references

- `k3d/README.md` - local Airflow-on-Kubernetes environment.
- `dags/dbt/RUNBOOK.md` - dbt DAG behavior, validation commands, and rollback notes.
- `.devcontainer/README.md` - dev container workflow.
- `adrs/README.md` - architecture decision index.

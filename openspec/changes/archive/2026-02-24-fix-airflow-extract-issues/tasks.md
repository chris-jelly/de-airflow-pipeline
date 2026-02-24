## 1. Fix Dockerfile site-packages targeting

- [x] 1.1 Pin `uv` version in Dockerfile `COPY --from` stage (replace `ghcr.io/astral-sh/uv:latest` with a specific version tag)
- [x] 1.2 Restructure Dockerfile install step: switch to `USER airflow` before `uv pip install`, remove `--system` flag, keep `--no-cache`
- [x] 1.3 Verify the build succeeds locally: `docker build -f dags/salesforce/Dockerfile -t test-salesforce .`
- [x] 1.4 Verify the Salesforce provider is importable in the built image: `docker run --rm --entrypoint python test-salesforce -c "from airflow.providers.salesforce.hooks.salesforce import SalesforceHook; print('OK')"`

## 2. Migrate DAG imports to airflow.sdk

- [x] 2.1 Update `dags/salesforce/salesforce_extraction_dag.py`: change `from airflow.decorators import dag, task` to `from airflow.sdk import dag, task`
- [x] 2.2 Update `dags/postgres-ping/postgres_ping_dag.py`: change `from airflow.decorators import dag, task` to `from airflow.sdk import dag, task`

## 3. Fix pyproject.toml config

- [x] 3.1 Update `dags/salesforce/pyproject.toml`: change `target-version = "py311"` to `target-version = "py313"` in `[tool.ruff]`

## 4. Update tests

- [x] 4.1 Check existing tests for any references to `airflow.decorators` and update to `airflow.sdk` if needed
- [x] 4.2 Run `scripts/test-all-dags.sh` and verify all tests pass

## 5. Verify

- [x] 5.1 Run `ruff check` across both DAG directories
- [x] 5.2 Rebuild the container image and confirm all providers are importable from within the image

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a data engineering pipeline that extracts data from Salesforce and loads it into PostgreSQL using Apache Airflow. The project is configured for Kubernetes deployment and uses environment variables for connection configurations.

## Development Environment

- Package Manager: **UV** (as specified in user's global CLAUDE.md)
- Python: 3.9+
- Environment Manager: mise (configured in `mise.toml`)

## Common Commands

### Setup and Installation

Each DAG type is its own complete project. Work in the DAG's directory:

```bash
# Work on Salesforce DAG
cd dags/salesforce

# Install dependencies (runtime + dev tools)
uv sync

# This installs:
# - Apache Airflow 2.8.1 with Kubernetes
# - Salesforce and Postgres providers
# - pandas, psycopg2-binary
# - Dev tools: pytest, ruff, black
```

### Code Quality

```bash
# From within dags/salesforce/
uv run ruff format .
uv run ruff check .
```

### Testing

```bash
# From within dags/salesforce/
uv run pytest

# Or specific test
uv run pytest tests/test_salesforce_extraction_dag.py
```

### DAG Validation

```bash
# From within dags/salesforce/
uv run python -m py_compile salesforce_extraction_dag.py
```

### Container Development

```bash
# From repo root
docker build -f dags/salesforce/Dockerfile -t de-airflow-pipeline-salesforce:local .

# Test container
docker run -it --rm de-airflow-pipeline-salesforce:local bash

# The container is automatically built and published to GHCR via GitHub Actions
# See KUBERNETES.md for deployment details
```

### Testing All DAGs (if needed)

```bash
# From repo root
for dag_dir in dags/*/; do
  echo "Testing $(basename $dag_dir)"
  cd "$dag_dir" && uv run pytest && cd - || exit 1
done
```

## Architecture

### Data Pipeline Structure
- **Bronze Layer**: Raw Salesforce data extracted to PostgreSQL (`bronze` schema)
- **Staging/Warehouse**: Placeholder dbt structure exists in `dags/dbt/de_warehouse/`

### Key Components

#### DAG Structure (`dags/`)

Each DAG type is structured as a complete, independent project:

```
dags/
└── salesforce/
    ├── salesforce_extraction_dag.py  # DAG file
    ├── pyproject.toml                # Complete dependencies (Airflow + providers + dev tools)
    ├── Dockerfile                    # Container build
    └── tests/                        # DAG-specific tests
```

- `salesforce/salesforce_extraction_dag.py`: Main extraction pipeline that pulls Account, Contact, and Opportunity data from Salesforce to PostgreSQL bronze layer

#### Connection Strategy
The pipeline uses **environment variables** for all connections instead of Airflow connections:

**Salesforce Environment Variables:**
- `SALESFORCE_USERNAME`
- `SALESFORCE_PASSWORD`
- `SALESFORCE_SECURITY_TOKEN`
- `SALESFORCE_DOMAIN` (optional, defaults to 'login')

**PostgreSQL Environment Variables:**
- `POSTGRES_HOST`
- `POSTGRES_DATABASE`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_PORT` (optional, defaults to 5432)

#### DAG Development Pattern: Lazy Imports

**IMPORTANT**: All DAGs in this repository use the **Lazy Import Pattern** for provider dependencies.

**Why**: The Airflow scheduler runs on the base Apache Airflow image without provider packages. Each DAG's tasks run in specialized Docker images with their specific dependencies. To allow the scheduler to parse DAGs while keeping worker pods isolated, we use lazy imports.

**Pattern**:

```python
from typing import TYPE_CHECKING

# Type hints only - not executed at runtime (for IDE support)
if TYPE_CHECKING:
    from airflow.providers.salesforce.hooks.salesforce import SalesforceHook
    from airflow.providers.postgres.hooks.postgres import PostgresHook

# DAG definition (parsed by scheduler)
dag = DAG(...)

def my_task_function(**context):
    """Task function docstring."""
    # Import providers at runtime (available in worker pod)
    from airflow.providers.salesforce.hooks.salesforce import SalesforceHook
    from airflow.providers.postgres.hooks.postgres import PostgresHook

    # Task logic here
    sf_hook = SalesforceHook(...)
    # ...
```

**Benefits**:
- Scheduler can parse all DAGs without provider packages
- Each DAG runs in its own specialized image via `executor_config`
- Scales to 10+ different DAG types without scheduler bloat
- Improves DAG parsing performance
- Maintains type safety for IDEs

**When creating new DAG types**:
1. Create `dags/<type>/` directory structure with `tests/` subdirectory
2. Add complete `pyproject.toml` with Airflow core + specific providers + dev tools
3. Add `Dockerfile` for container build
4. Use `TYPE_CHECKING` for type hints at module level in DAG files
5. Move actual provider imports inside task functions
6. Specify custom image in `executor_config` pointing to your DAG's container
7. Update CI/CD matrix in `.github/workflows/build-and-push-container.yml`

**Why this structure**:
- Complete isolation: Each DAG has only its required dependencies
- Production parity: `uv sync` installs exact container environment
- No confusion: One pyproject.toml per DAG type, no root dependencies
- Aligns with ADR-001: Per-DAG container images strategy

**Workflow**:
```bash
cd dags/salesforce    # Enter DAG project
uv sync               # Install complete environment
uv run pytest         # Test this DAG
uv run ruff format .  # Format code
```

### Deployment
- Designed for Kubernetes deployment with KubernetesExecutor
- Container published to GitHub Container Registry (GHCR) automatically
- Uses UV for fast, reproducible dependency installation in containers
- Uses Kubernetes secrets mounted as environment variables
- Pre-commit hooks configured for code quality
- See **KUBERNETES.md** for detailed deployment instructions

### Dependencies
- Apache Airflow 2.8.1 with Kubernetes support
- Salesforce and PostgreSQL providers
- pandas for data manipulation
- Development tools: pytest, black, ruff

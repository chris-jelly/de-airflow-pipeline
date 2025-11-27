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
```bash
# Install dependencies
uv sync

# Install development dependencies
uv sync --dev

# Setup development environment (runs automatically via mise hooks)
./scripts/setup_project
```

### Code Quality
```bash
# Format code
uv run black .

# Lint code
uv run ruff check .

# Run tests
uv run pytest
```

### Airflow Development
```bash
# Test DAG syntax
uv run python -m py_compile dags/salesforce_extraction_dag.py

# Run Airflow locally (if needed for testing)
export AIRFLOW_HOME=$(pwd)
uv run airflow db init
uv run airflow dags list
```

### Container Development
```bash
# Build container locally
docker build -t de-airflow-pipeline:local .

# Test container
docker run -it --rm de-airflow-pipeline:local bash

# The container is automatically built and published to GHCR via GitHub Actions
# See KUBERNETES.md for deployment details
```

## Architecture

### Data Pipeline Structure
- **Bronze Layer**: Raw Salesforce data extracted to PostgreSQL (`bronze` schema)
- **Staging/Warehouse**: Placeholder dbt structure exists in `dags/dbt/de_warehouse/`

### Key Components

#### DAGs (`dags/`)
- `salesforce_extraction_dag.py`: Main extraction pipeline that pulls Account, Contact, and Opportunity data from Salesforce to PostgreSQL bronze layer

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

**When creating new DAGs**:
1. Use `TYPE_CHECKING` for type hints at module level
2. Move actual imports inside task functions
3. Specify custom image in `executor_config`
4. Create corresponding `pyproject.<dag-type>.toml` and `Dockerfile.<dag-type>`

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
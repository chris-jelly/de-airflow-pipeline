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
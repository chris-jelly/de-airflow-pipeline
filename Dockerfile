# Use official Apache Airflow image as base
FROM apache/airflow:2.8.1-python3.11

# Switch to root to install UV and dependencies
USER root

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create necessary directories
RUN mkdir -p /opt/airflow/dags

# Switch to airflow user for the rest of the setup
USER airflow

# Set working directory
WORKDIR /opt/airflow

# Copy dependency files
COPY --chown=airflow:root pyproject.toml uv.lock ./

# Install dependencies using UV
# UV will respect the uv.lock file for reproducible builds
RUN uv sync --frozen --no-dev

# Copy DAGs and other project files
COPY --chown=airflow:root dags/ /opt/airflow/dags/
COPY --chown=airflow:root scripts/ /opt/airflow/scripts/

# Set PYTHONPATH to ensure our packages are found
ENV PYTHONPATH="/opt/airflow:${PYTHONPATH}"

# The base image already has the correct ENTRYPOINT and CMD
# which will be used by the KubernetesExecutor

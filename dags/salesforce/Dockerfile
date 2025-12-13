# Use official Apache Airflow image as base
FROM apache/airflow:3.1.5-python3.13

# Switch to root to install UV and dependencies
USER root

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create necessary directories
RUN mkdir -p /opt/airflow/dags

# Set working directory
WORKDIR /opt/airflow

# Copy this DAG's pyproject.toml
COPY --chown=airflow:root dags/salesforce/pyproject.toml ./pyproject.toml

# Install dependencies using UV as root (--system requires root permissions)
# This image only contains dependencies needed for Salesforce extraction
RUN uv pip install --system --no-cache .

# Switch to airflow user for runtime
USER airflow

# Copy ALL DAGs (scheduler needs to discover all DAG files)
COPY --chown=airflow:root dags/ /opt/airflow/dags/

# Set PYTHONPATH to ensure our packages are found
ENV PYTHONPATH="/opt/airflow"

# The base image already has the correct ENTRYPOINT and CMD
# which will be used by the KubernetesExecutor

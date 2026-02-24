# Use official Apache Airflow image as base
FROM apache/airflow:3.1.5-python3.13

# Switch to root to install UV and dependencies
USER root

# Install UV
COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /usr/local/bin/uv

# Create necessary directories
RUN mkdir -p /opt/airflow/dags

# Set working directory
WORKDIR /opt/airflow

# Copy this DAG's pyproject.toml
COPY --chown=airflow:root dags/salesforce/pyproject.toml ./pyproject.toml

# Switch to airflow user so dependencies install into
# /home/airflow/.local/lib/python3.13/site-packages/ — the only
# site-packages directory on sys.path in the base Airflow image.
USER airflow

# Install dependencies (no --system: installs into user site-packages)
RUN uv pip install --no-cache .

# Copy ALL DAGs (scheduler needs to discover all DAG files)
COPY --chown=airflow:root dags/ /opt/airflow/dags/

# Set PYTHONPATH to ensure our packages are found
ENV PYTHONPATH="/opt/airflow"

# The base image already has the correct ENTRYPOINT and CMD
# which will be used by the KubernetesExecutor

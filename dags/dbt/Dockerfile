FROM apache/airflow:3.1.5-python3.13

USER root

COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /usr/local/bin/uv

RUN mkdir -p /opt/airflow/dags

WORKDIR /opt/airflow

COPY --chown=airflow:root dags/dbt/pyproject.toml ./pyproject.toml

USER airflow

RUN uv pip install --no-cache .

COPY --chown=airflow:root dags/ /opt/airflow/dags/

ENV PYTHONPATH="/opt/airflow"

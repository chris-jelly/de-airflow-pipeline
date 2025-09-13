FROM apache/airflow:2.8.1-python3.11
USER root
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv
ENV UV_SYSTEM_PYTHON=1
COPY pyproject.toml de_airflow_pipeline/ /tmp/
RUN cd /tmp && uv pip install --no-cache . && rm -rf /tmp/*
USER airflow
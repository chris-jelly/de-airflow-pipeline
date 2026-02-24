"""Postgres connectivity health-check DAG.

A minimal smoke-test DAG that validates:
- DAG sync and scheduling work on Airflow 3
- KubernetesExecutor task execution works
- External warehouse Postgres connectivity via AIRFLOW_CONN_* pod-level secrets

Runs on the base apache/airflow image — no custom container required.
"""

from datetime import datetime, timedelta

from airflow.sdk import dag, task
from kubernetes.client import models as k8s

# Connection IDs — single environment, no suffix (see ADR: consolidated dev/prod)
postgres_conn_id = "warehouse_postgres"

# Pod override: mount AIRFLOW_CONN_WAREHOUSE_POSTGRES from K8s secret (ADR-002)
executor_config = {
    "pod_override": k8s.V1Pod(
        spec=k8s.V1PodSpec(
            containers=[
                k8s.V1Container(
                    name="base",
                    env=[
                        k8s.V1EnvVar(
                            name="AIRFLOW_CONN_WAREHOUSE_POSTGRES",
                            value_from=k8s.V1EnvVarSource(
                                secret_key_ref=k8s.V1SecretKeySelector(
                                    name="warehouse-postgres-conn",
                                    key="AIRFLOW_CONN_WAREHOUSE_POSTGRES",
                                )
                            ),
                        ),
                    ],
                )
            ]
        )
    )
}


@dag(
    dag_id="postgres_ping",
    description="Health-check: validate Postgres connectivity via warehouse connection",
    schedule="@hourly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "data-team",
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
    },
)
def postgres_ping():
    @task(task_id="ping", executor_config=executor_config)
    def ping():
        """Connect to warehouse Postgres, run SELECT 1, and log the result."""
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        hook = PostgresHook(postgres_conn_id=postgres_conn_id)
        records = hook.get_records("SELECT 1 AS ping, NOW() AS server_time")
        row = records[0]
        print(f"Postgres ping OK — result={row[0]}, server_time={row[1]}")

    ping()


postgres_ping()

"""Salesforce dbt transformation DAG.

Builds and validates Salesforce dbt models from raw landing tables into
staging, intermediate, and marts schemas.
"""

from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
import subprocess

from airflow.sdk import dag, task
from kubernetes.client import models as k8s

postgres_conn_id = "warehouse_postgres"
DBT_PROJECT_DIR = str(Path(__file__).resolve().parent)
DBT_STATE_PIPELINE = "salesforce_dbt"
DBT_RUNTIME_ROOT = "/tmp/dbt"

logger = logging.getLogger(__name__)

executor_config = {
    "pod_override": k8s.V1Pod(
        spec=k8s.V1PodSpec(
            containers=[
                k8s.V1Container(
                    name="base",
                    image=os.getenv(
                        "DBT_DAG_IMAGE",
                        "ghcr.io/chris-jelly/de-airflow-pipeline-dbt:latest",
                    ),
                    image_pull_policy="Always",
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


def should_run_dbt(
    latest_raw_marker: datetime | None,
    last_processed_marker: datetime | None,
) -> bool:
    """Return whether dbt should run based on freshness markers."""
    if latest_raw_marker is None:
        return False
    if last_processed_marker is None:
        return True
    return latest_raw_marker > last_processed_marker


def _build_dbt_env() -> dict[str, str]:
    """Build dbt runtime environment from Airflow connection metadata."""
    from airflow.providers.postgres.hooks.postgres import PostgresHook

    hook = PostgresHook(postgres_conn_id=postgres_conn_id)
    conn = hook.get_connection(postgres_conn_id)

    env = os.environ.copy()
    env.update(
        {
            "DBT_HOST": conn.host,
            "DBT_USER": conn.login,
            "DBT_PASSWORD": conn.password,
            "DBT_PORT": str(conn.port or 5432),
            "DBT_DBNAME": conn.schema,
            "DBT_PROFILES_DIR": DBT_PROJECT_DIR,
            "DBT_TARGET_PATH": f"{DBT_RUNTIME_ROOT}/target",
            "DBT_LOG_PATH": f"{DBT_RUNTIME_ROOT}/logs",
            "DBT_PACKAGES_INSTALL_PATH": f"{DBT_RUNTIME_ROOT}/dbt_packages",
        }
    )
    return env


def _run_dbt_command(command: list[str]) -> None:
    """Execute dbt command with consistent runtime paths and logging."""
    env = _build_dbt_env()
    command_str = " ".join(command)
    logger.info("Running dbt command: %s", command_str)

    try:
        result = subprocess.run(
            command,
            check=True,
            cwd=DBT_PROJECT_DIR,
            env=env,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.error("dbt command failed with exit code %s: %s", exc.returncode, command_str)
        if exc.stdout:
            logger.error("dbt stdout:\n%s", exc.stdout.strip())
        if exc.stderr:
            logger.error("dbt stderr:\n%s", exc.stderr.strip())
        raise

    if result.stdout:
        logger.info("dbt stdout:\n%s", result.stdout.strip())
    if result.stderr:
        logger.warning("dbt stderr:\n%s", result.stderr.strip())


@dag(
    dag_id="salesforce_dbt_transformation",
    description="Run Salesforce dbt transformations with freshness gating",
    schedule="@hourly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "data-team",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
)
def salesforce_dbt_transformation():
    @task(task_id="create_modeling_schemas", executor_config=executor_config)
    def create_modeling_schemas() -> None:
        """Create transformation schemas and dbt state table."""
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        hook = PostgresHook(postgres_conn_id=postgres_conn_id)
        hook.run(
            """
            CREATE SCHEMA IF NOT EXISTS staging;
            CREATE SCHEMA IF NOT EXISTS intermediate;
            CREATE SCHEMA IF NOT EXISTS marts;

            CREATE TABLE IF NOT EXISTS raw_salesforce.dbt_transformation_state (
                pipeline_name TEXT PRIMARY KEY,
                last_raw_marker TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );
            """
        )

    @task.short_circuit(task_id="check_raw_salesforce_freshness", executor_config=executor_config)
    def check_raw_salesforce_freshness(**context) -> bool:
        """Short-circuit dbt when raw Salesforce data has not advanced."""
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        hook = PostgresHook(postgres_conn_id=postgres_conn_id)
        latest_raw = hook.get_first(
            """
            SELECT MAX(raw_marker)
            FROM (
                SELECT MAX(extracted_at) AS raw_marker FROM raw_salesforce.accounts
                UNION ALL
                SELECT MAX(extracted_at) AS raw_marker FROM raw_salesforce.contacts
                UNION ALL
                SELECT MAX(extracted_at) AS raw_marker FROM raw_salesforce.opportunities
            ) markers
            """
        )[0]

        last_processed = hook.get_first(
            """
            SELECT last_raw_marker
            FROM raw_salesforce.dbt_transformation_state
            WHERE pipeline_name = %s
            """,
            parameters=(DBT_STATE_PIPELINE,),
        )
        last_processed_marker = last_processed[0] if last_processed else None

        should_execute = should_run_dbt(
            latest_raw_marker=latest_raw,
            last_processed_marker=last_processed_marker,
        )

        if not should_execute:
            logger.info(
                "Skipping dbt run: latest_raw_marker=%s last_processed_marker=%s",
                latest_raw,
                last_processed_marker,
            )
            return False

        logger.info(
            "Executing dbt run: latest_raw_marker=%s last_processed_marker=%s",
            latest_raw,
            last_processed_marker,
        )
        context["ti"].xcom_push(key="latest_raw_marker", value=latest_raw.isoformat())
        return True

    @task(task_id="dbt_build_salesforce", executor_config=executor_config)
    def dbt_build_salesforce() -> None:
        """Run dbt build for Salesforce staging/intermediate/marts models."""
        command = ["dbt", "build", "--select", "path:models/staging+ path:models/intermediate+ path:models/marts+"]
        _run_dbt_command(command)

    @task(task_id="dbt_test_diagnostics", executor_config=executor_config)
    def dbt_test_diagnostics() -> None:
        """Run warning/info diagnostics separately for observability."""
        command = ["dbt", "test", "--select", "tag:warn tag:info"]
        _run_dbt_command(command)

    @task(task_id="record_last_processed_marker", executor_config=executor_config)
    def record_last_processed_marker(**context) -> None:
        """Persist the raw freshness marker after successful dbt execution."""
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        latest_raw_marker = context["ti"].xcom_pull(
            task_ids="check_raw_salesforce_freshness",
            key="latest_raw_marker",
        )
        if not latest_raw_marker:
            logger.info("No latest raw marker found; skipping state update")
            return

        hook = PostgresHook(postgres_conn_id=postgres_conn_id)
        hook.run(
            """
            INSERT INTO raw_salesforce.dbt_transformation_state
                (pipeline_name, last_raw_marker, updated_at)
            VALUES (%s, %s::timestamptz, NOW())
            ON CONFLICT (pipeline_name)
            DO UPDATE SET
                last_raw_marker = EXCLUDED.last_raw_marker,
                updated_at = NOW()
            """,
            parameters=(DBT_STATE_PIPELINE, latest_raw_marker),
        )

    schema_setup = create_modeling_schemas()
    freshness_gate = check_raw_salesforce_freshness()
    dbt_build = dbt_build_salesforce()
    dbt_diagnostics = dbt_test_diagnostics()
    update_marker = record_last_processed_marker()

    schema_setup >> freshness_gate >> dbt_build >> dbt_diagnostics >> update_marker


salesforce_dbt_transformation()

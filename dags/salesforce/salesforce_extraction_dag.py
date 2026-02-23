"""Salesforce to PostgreSQL extraction DAG.

Extracts Account, Opportunity, and Contact objects from Salesforce
and loads them into a PostgreSQL bronze schema.

Uses:
- TaskFlow API (@dag / @task decorators)
- conn_id-based hooks (AIRFLOW_CONN_* env vars mounted in executor pods)
- Lazy import pattern (provider hooks + pandas imported inside tasks only)
- ADR-002 pod-level secret isolation via executor_config
"""

from datetime import datetime, timedelta, timezone

from airflow.decorators import dag, task
from airflow.models import Variable
from kubernetes.client import models as k8s

# Resolve environment at parse time (lightweight — no provider imports)
env = Variable.get("environment", default_var="dev")
postgres_conn_id = f"warehouse_postgres_{env}"
salesforce_conn_id = f"salesforce_{env}"

# KubernetesExecutor configuration — mount AIRFLOW_CONN_* env vars from K8s secrets
# SECURITY: Secrets are mounted ONLY in executor pods for this DAG, not globally (ADR-002)
#
# Required Kubernetes secrets (managed in homelab repo):
#   warehouse-postgres-conn:
#     AIRFLOW_CONN_WAREHOUSE_POSTGRES: "postgresql://user:pass@host:5432/dbname"
#   salesforce-conn:
#     AIRFLOW_CONN_SALESFORCE: '{"conn_type":"salesforce","extra":{"consumer_key":"...","private_key":"...","domain":"login"}}'
executor_config = {
    "pod_override": k8s.V1Pod(
        spec=k8s.V1PodSpec(
            containers=[
                k8s.V1Container(
                    name="base",
                    image="ghcr.io/chris-jelly/de-airflow-pipeline-salesforce:latest",
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
                        k8s.V1EnvVar(
                            name="AIRFLOW_CONN_SALESFORCE",
                            value_from=k8s.V1EnvVarSource(
                                secret_key_ref=k8s.V1SecretKeySelector(
                                    name="salesforce-conn",
                                    key="AIRFLOW_CONN_SALESFORCE",
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
    dag_id="salesforce_extraction",
    description="Extract Salesforce data to PostgreSQL bronze layer",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "data-team",
        "depends_on_past": False,
        "email_on_failure": False,
        "email_on_retry": False,
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
)
def salesforce_extraction():
    @task(task_id="create_bronze_schema", executor_config=executor_config)
    def create_bronze_schema():
        """Create bronze schema in PostgreSQL."""
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        pg_hook = PostgresHook(postgres_conn_id=postgres_conn_id)
        pg_hook.run("CREATE SCHEMA IF NOT EXISTS bronze;")

    @task(executor_config=executor_config)
    def extract_salesforce_to_postgres(sf_object: str, table_name: str, **context):
        """Extract Salesforce object data directly to PostgreSQL."""
        import json

        import pandas as pd
        from airflow.providers.postgres.hooks.postgres import PostgresHook
        from airflow.providers.salesforce.hooks.salesforce import SalesforceHook

        sf_hook = SalesforceHook(salesforce_conn_id=salesforce_conn_id)
        pg_hook = PostgresHook(postgres_conn_id=postgres_conn_id)

        # Query Salesforce
        sf_conn = sf_hook.get_conn()
        query = f"SELECT * FROM {sf_object}"
        result = sf_conn.query_all(query)

        if not result["records"]:
            print(f"No records found for {sf_object}")
            return

        # Process records
        records = []
        for record in result["records"]:
            # Remove Salesforce metadata
            record.pop("attributes", None)
            # Convert None values and handle nested objects
            clean_record = {}
            for key, value in record.items():
                if isinstance(value, dict):
                    clean_record[key] = json.dumps(value)
                else:
                    clean_record[key] = value
            records.append(clean_record)

        # Convert to DataFrame
        df = pd.DataFrame(records)

        # Add audit columns
        df["extracted_at"] = datetime.now(timezone.utc)
        df["dag_run_id"] = context["dag_run"].run_id

        # Generate CREATE TABLE statement
        columns_sql = []
        for col in df.columns:
            if col in ["extracted_at"]:
                columns_sql.append(f'"{col}" TIMESTAMP WITH TIME ZONE')
            elif col in ["dag_run_id"]:
                columns_sql.append(f'"{col}" VARCHAR(255)')
            else:
                columns_sql.append(f'"{col}" TEXT')

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS bronze.{table_name} (
            {", ".join(columns_sql)}
        );
        """

        # Execute CREATE TABLE
        pg_hook.run(create_table_sql)

        # Insert data
        df.to_sql(
            name=table_name,
            con=pg_hook.get_sqlalchemy_engine(),
            schema="bronze",
            if_exists="append",
            index=False,
            method="multi",
        )

        print(f"Successfully loaded {len(df)} records to bronze.{table_name}")

    # Wire dependencies: schema first, then parallel extractions
    schema = create_bronze_schema()
    extract_accounts = extract_salesforce_to_postgres.override(
        task_id="extract_accounts"
    )(sf_object="Account", table_name="accounts")
    extract_opportunities = extract_salesforce_to_postgres.override(
        task_id="extract_opportunities"
    )(sf_object="Opportunity", table_name="opportunities")
    extract_contacts = extract_salesforce_to_postgres.override(
        task_id="extract_contacts"
    )(sf_object="Contact", table_name="contacts")

    schema >> [extract_accounts, extract_opportunities, extract_contacts]


salesforce_extraction()

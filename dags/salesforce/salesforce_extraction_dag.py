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
import logging

from airflow.sdk import dag, task
from kubernetes.client import models as k8s

# Connection IDs — single environment, no suffix (see ADR: consolidated dev/prod)
postgres_conn_id = "warehouse_postgres"
salesforce_conn_id = "salesforce"

WATERMARK_LOOKBACK_MINUTES = 10

CURATED_FIELDS = {
    "Account": [
        "Id",
        "Name",
        "AccountNumber",
        "Type",
        "Industry",
        "AnnualRevenue",
        "NumberOfEmployees",
        "Website",
        "Phone",
        "OwnerId",
        "ParentId",
        "BillingStreet",
        "BillingCity",
        "BillingState",
        "BillingPostalCode",
        "BillingCountry",
        "ShippingStreet",
        "ShippingCity",
        "ShippingState",
        "ShippingPostalCode",
        "ShippingCountry",
        "IsDeleted",
        "CreatedDate",
        "LastModifiedDate",
        "SystemModstamp",
        "CustomerPriority__c",
        "SLA__c",
        "Active__c",
        "NumberofLocations__c",
        "UpsellOpportunity__c",
        "SLASerialNumber__c",
        "SLAExpirationDate__c",
    ],
    "Contact": [
        "Id",
        "AccountId",
        "FirstName",
        "LastName",
        "Name",
        "Email",
        "Phone",
        "MobilePhone",
        "Title",
        "Department",
        "LeadSource",
        "MailingStreet",
        "MailingCity",
        "MailingState",
        "MailingPostalCode",
        "MailingCountry",
        "OwnerId",
        "IsDeleted",
        "CreatedDate",
        "LastModifiedDate",
        "SystemModstamp",
        "Level__c",
        "Languages__c",
    ],
    "Opportunity": [
        "Id",
        "AccountId",
        "Name",
        "StageName",
        "Amount",
        "Probability",
        "CloseDate",
        "Type",
        "ForecastCategoryName",
        "IsClosed",
        "IsWon",
        "LeadSource",
        "NextStep",
        "CampaignId",
        "OwnerId",
        "CurrencyIsoCode",
        "IsDeleted",
        "CreatedDate",
        "LastModifiedDate",
        "SystemModstamp",
        "DeliveryInstallationStatus__c",
        "TrackingNumber__c",
        "OrderNumber__c",
        "CurrentGenerators__c",
        "MainCompetitors__c",
    ],
}


def validate_curated_fields() -> None:
    """Validate curated field configuration for incremental extraction."""
    required_fields = {"Id", "SystemModstamp"}
    for sf_object, fields in CURATED_FIELDS.items():
        missing_fields = required_fields - set(fields)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"{sf_object} is missing required fields: {missing}")


def get_incremental_start(
    watermark: datetime | None,
    lookback_minutes: int = WATERMARK_LOOKBACK_MINUTES,
) -> datetime | None:
    """Return incremental start timestamp with overlap applied."""
    if watermark is None:
        return None
    return watermark - timedelta(minutes=lookback_minutes)


def sf_datetime_literal(value: datetime) -> str:
    """Format datetime for SOQL datetime literals."""
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_incremental_query(sf_object: str, watermark: datetime | None) -> str:
    """Build deterministic incremental SOQL query from curated fields."""
    fields = CURATED_FIELDS[sf_object]
    return build_incremental_query_with_fields(
        sf_object=sf_object,
        selected_fields=fields,
        watermark=watermark,
    )


def build_incremental_query_with_fields(
    sf_object: str,
    selected_fields: list[str],
    watermark: datetime | None,
) -> str:
    """Build deterministic incremental SOQL query from selected fields."""
    query = f"SELECT {', '.join(selected_fields)} FROM {sf_object}"

    incremental_start = get_incremental_start(watermark)
    if incremental_start is not None:
        query += f" WHERE SystemModstamp > {sf_datetime_literal(incremental_start)}"

    query += " ORDER BY SystemModstamp, Id"
    return query


def get_available_object_fields(sf_conn, sf_object: str) -> set[str]:
    """Return available field names for a Salesforce object via describe metadata."""
    describe = getattr(sf_conn, sf_object).describe()
    return {field["name"] for field in describe.get("fields", []) if "name" in field}


def select_schema_compatible_fields(
    sf_object: str,
    available_fields: set[str],
    required_fields: tuple[str, str] = ("Id", "SystemModstamp"),
) -> tuple[list[str], list[str]]:
    """Select schema-compatible curated fields while preserving curated order."""
    curated_fields = CURATED_FIELDS[sf_object]
    selected = [field for field in curated_fields if field in available_fields]
    skipped = [field for field in curated_fields if field not in available_fields]

    missing_required = [field for field in required_fields if field not in selected]
    if missing_required:
        missing_str = ", ".join(missing_required)
        raise ValueError(
            f"{sf_object} missing required fields after schema filtering: {missing_str}"
        )

    return selected, skipped


def parse_salesforce_datetime(value: str) -> datetime:
    """Parse Salesforce datetime values into timezone-aware UTC datetimes."""
    normalized = value
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+0000"
    if len(normalized) >= 5 and normalized[-5] in {"+", "-"} and normalized[-3] != ":":
        normalized = normalized[:-2] + ":" + normalized[-2:]
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def next_watermark(
    current: datetime | None,
    records: list[dict],
    now_utc: datetime,
) -> datetime:
    """Compute next per-object watermark from extracted records."""
    if records:
        values = [
            parse_salesforce_datetime(record["SystemModstamp"])
            for record in records
            if record.get("SystemModstamp")
        ]
        if values:
            return max(values)
    if current is None:
        return now_utc
    return current


validate_curated_fields()

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
        pg_hook.run(
            """
            CREATE SCHEMA IF NOT EXISTS bronze;

            CREATE TABLE IF NOT EXISTS bronze.salesforce_watermarks (
                sf_object VARCHAR(255) PRIMARY KEY,
                last_systemmodstamp TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );
            """
        )

    @task(executor_config=executor_config)
    def extract_salesforce_to_postgres(sf_object: str, table_name: str, **context):
        """Extract Salesforce object data directly to PostgreSQL."""
        import json

        import pandas as pd
        from airflow.providers.postgres.hooks.postgres import PostgresHook
        from airflow.providers.salesforce.hooks.salesforce import SalesforceHook

        sf_hook = SalesforceHook(salesforce_conn_id=salesforce_conn_id)
        pg_hook = PostgresHook(postgres_conn_id=postgres_conn_id)
        logger = logging.getLogger(__name__)

        def get_watermark(sf_object: str) -> datetime | None:
            records = pg_hook.get_records(
                sql="""
                SELECT last_systemmodstamp
                FROM bronze.salesforce_watermarks
                WHERE sf_object = %s
                """,
                parameters=(sf_object,),
            )
            if not records:
                return None
            return records[0][0]

        def upsert_watermark(sf_object: str, watermark: datetime) -> None:
            pg_hook.run(
                sql="""
                INSERT INTO bronze.salesforce_watermarks (sf_object, last_systemmodstamp, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (sf_object)
                DO UPDATE SET
                    last_systemmodstamp = EXCLUDED.last_systemmodstamp,
                    updated_at = NOW()
                """,
                parameters=(sf_object, watermark),
            )

        # Query Salesforce incrementally
        sf_conn = sf_hook.get_conn()
        current_watermark = get_watermark(sf_object)
        available_fields = get_available_object_fields(sf_conn, sf_object)
        selected_fields, skipped_fields = select_schema_compatible_fields(
            sf_object=sf_object,
            available_fields=available_fields,
        )
        if skipped_fields:
            logger.warning(
                "Skipping unavailable curated Salesforce fields for %s: %s",
                sf_object,
                ", ".join(skipped_fields),
            )
        logger.info(
            "Using schema-compatible curated Salesforce fields for %s: %s",
            sf_object,
            ", ".join(selected_fields),
        )

        query = build_incremental_query_with_fields(
            sf_object=sf_object,
            selected_fields=selected_fields,
            watermark=current_watermark,
        )
        result = sf_conn.query_all(query)

        records = result["records"]
        planned_watermark = next_watermark(
            current=current_watermark,
            records=records,
            now_utc=datetime.now(timezone.utc),
        )

        # Ensure target table exists even when no records are returned
        all_columns = CURATED_FIELDS[sf_object] + ["extracted_at", "dag_run_id"]
        columns_sql = []
        for col in all_columns:
            if col == "extracted_at":
                columns_sql.append(f'"{col}" TIMESTAMP WITH TIME ZONE')
            elif col == "dag_run_id":
                columns_sql.append(f'"{col}" VARCHAR(255)')
            else:
                columns_sql.append(f'"{col}" TEXT')

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS bronze.{table_name} (
            {", ".join(columns_sql)}
        );
        """
        pg_hook.run(create_table_sql)

        if not records:
            upsert_watermark(sf_object, planned_watermark)
            print(f"No records found for {sf_object}")
            return

        # Process records
        clean_records = []
        for record in records:
            # Remove Salesforce metadata
            record.pop("attributes", None)
            # Convert None values and handle nested objects
            clean_record = {}
            for key, value in record.items():
                if isinstance(value, dict):
                    clean_record[key] = json.dumps(value)
                else:
                    clean_record[key] = value
            clean_records.append(clean_record)

        # Convert to DataFrame
        df = pd.DataFrame(clean_records)

        # Ensure all curated fields exist in the frame for stable writes
        for field in CURATED_FIELDS[sf_object]:
            if field not in df.columns:
                df[field] = None
        df = df[CURATED_FIELDS[sf_object]]

        # Add audit columns
        df["extracted_at"] = datetime.now(timezone.utc)
        df["dag_run_id"] = context["dag_run"].run_id

        # Idempotent upsert semantics through stage + delete/insert by Id
        stage_table = f"_{table_name}_staging"
        df.to_sql(
            name=stage_table,
            con=pg_hook.get_sqlalchemy_engine(),
            schema="bronze",
            if_exists="replace",
            index=False,
            method="multi",
        )

        quoted_columns = ", ".join(f'"{col}"' for col in df.columns)
        pg_hook.run(
            f"""
            DELETE FROM bronze.{table_name} AS target
            USING bronze.{stage_table} AS stage
            WHERE target."Id" = stage."Id";

            INSERT INTO bronze.{table_name} ({quoted_columns})
            SELECT {quoted_columns}
            FROM bronze.{stage_table};

            DROP TABLE IF EXISTS bronze.{stage_table};
            """
        )

        upsert_watermark(sf_object, planned_watermark)

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

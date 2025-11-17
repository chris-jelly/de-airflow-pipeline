from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.salesforce.hooks.salesforce import SalesforceHook
from airflow.models import Variable
import pandas as pd
import json
import os

# Get environment (you can set this as an Airflow Variable)
env = Variable.get("environment", default_var="dev")  # or "prod"

# Use environment-specific connections
postgres_conn_id = f"warehouse_postgres_{env}"
salesforce_conn_id = f"salesforce_{env}"

# KubernetesExecutor configuration - specify custom image for this DAG
# This allows each DAG to use its own container with only the dependencies it needs
executor_config = {
    "pod_override": {
        "spec": {
            "containers": [
                {
                    "name": "base",
                    "image": "ghcr.io/chris-jelly/de-airflow-pipeline:salesforce-latest",
                }
            ]
        }
    }
}

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'executor_config': executor_config,  # Apply to all tasks in this DAG
}

dag = DAG(
    'salesforce_extraction',
    default_args=default_args,
    description='Extract Salesforce data to PostgreSQL bronze layer',
    schedule_interval='@daily',
    catchup=False,
    max_active_runs=1,
)

def extract_salesforce_to_postgres(sf_object: str, table_name: str, **context):
    """Extract Salesforce object data directly to PostgreSQL."""
    
    # Access environment-specific variables
    postgres_host = os.getenv(f"POSTGRES_HOST_{env.upper()}")
    postgres_database = os.getenv(f"POSTGRES_DATABASE_{env.upper()}")
    postgres_user = os.getenv(f"POSTGRES_USER_{env.upper()}")
    postgres_password = os.getenv(f"POSTGRES_PASSWORD_{env.upper()}")
    postgres_port = int(os.getenv(f"POSTGRES_PORT_{env.upper()}", '5432'))
    
    salesforce_username = os.getenv(f"SALESFORCE_USERNAME_{env.upper()}")
    salesforce_password = os.getenv(f"SALESFORCE_PASSWORD_{env.upper()}")
    salesforce_security_token = os.getenv(f"SALESFORCE_SECURITY_TOKEN_{env.upper()}")
    salesforce_domain = os.getenv(f"SALESFORCE_DOMAIN_{env.upper()}", 'login')
    
    # Get hooks using environment-specific variables
    sf_hook = SalesforceHook(
        username=salesforce_username,
        password=salesforce_password,
        security_token=salesforce_security_token,
        domain=salesforce_domain
    )
    pg_hook = PostgresHook(
        host=postgres_host,
        database=postgres_database,
        login=postgres_user,
        password=postgres_password,
        port=postgres_port
    )
    
    # Query Salesforce
    sf_conn = sf_hook.get_conn()
    query = f"SELECT * FROM {sf_object}"
    result = sf_conn.query_all(query)
    
    if not result['records']:
        print(f"No records found for {sf_object}")
        return
    
    # Process records
    records = []
    for record in result['records']:
        # Remove Salesforce metadata
        record.pop('attributes', None)
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
    df['extracted_at'] = datetime.utcnow()
    df['dag_run_id'] = context['dag_run'].run_id
    
    # Generate CREATE TABLE statement
    columns_sql = []
    for col in df.columns:
        if col in ['extracted_at']:
            columns_sql.append(f'"{col}" TIMESTAMP WITH TIME ZONE')
        elif col in ['dag_run_id']:
            columns_sql.append(f'"{col}" VARCHAR(255)')
        else:
            columns_sql.append(f'"{col}" TEXT')
    
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS bronze.{table_name} (
        {', '.join(columns_sql)}
    );
    """
    
    # Execute CREATE TABLE
    pg_hook.run(create_table_sql)
    
    # Insert data
    df.to_sql(
        name=table_name,
        con=pg_hook.get_sqlalchemy_engine(),
        schema='bronze',
        if_exists='append',
        index=False,
        method='multi'
    )
    
    print(f"Successfully loaded {len(df)} records to bronze.{table_name}")

# Create bronze schema
def create_bronze_schema():
    # Access environment-specific variables
    postgres_host = os.getenv(f"POSTGRES_HOST_{env.upper()}")
    postgres_database = os.getenv(f"POSTGRES_DATABASE_{env.upper()}")
    postgres_user = os.getenv(f"POSTGRES_USER_{env.upper()}")
    postgres_password = os.getenv(f"POSTGRES_PASSWORD_{env.upper()}")
    postgres_port = int(os.getenv(f"POSTGRES_PORT_{env.upper()}", '5432'))
    
    pg_hook = PostgresHook(
        host=postgres_host,
        database=postgres_database,
        login=postgres_user,
        password=postgres_password,
        port=postgres_port
    )
    pg_hook.run("CREATE SCHEMA IF NOT EXISTS bronze;")

create_schema_task = PythonOperator(
    task_id='create_bronze_schema',
    python_callable=create_bronze_schema,
    dag=dag,
)

# Extract Accounts
extract_accounts_task = PythonOperator(
    task_id='extract_accounts',
    python_callable=extract_salesforce_to_postgres,
    op_kwargs={
        'sf_object': 'Account',
        'table_name': 'accounts'
    },
    dag=dag,
)

# Extract Opportunities
extract_opportunities_task = PythonOperator(
    task_id='extract_opportunities',
    python_callable=extract_salesforce_to_postgres,
    op_kwargs={
        'sf_object': 'Opportunity',
        'table_name': 'opportunities'
    },
    dag=dag,
)

# Extract Contacts
extract_contacts_task = PythonOperator(
    task_id='extract_contacts',
    python_callable=extract_salesforce_to_postgres,
    op_kwargs={
        'sf_object': 'Contact',
        'table_name': 'contacts'
    },
    dag=dag,
)

# Set dependencies
create_schema_task >> [extract_accounts_task, extract_opportunities_task, extract_contacts_task]
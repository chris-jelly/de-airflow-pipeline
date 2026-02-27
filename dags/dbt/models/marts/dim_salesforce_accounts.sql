select
    account_id,
    account_name,
    account_number,
    account_type,
    industry,
    annual_revenue,
    number_of_employees,
    billing_city,
    billing_state,
    billing_country,
    is_active,
    systemmodstamp as source_last_modified_at,
    extracted_at as raw_extracted_at
from {{ ref('int_salesforce_current_accounts') }}

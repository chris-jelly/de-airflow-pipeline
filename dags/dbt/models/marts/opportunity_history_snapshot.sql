{{
    config(
        materialized='incremental',
        unique_key=['opportunity_id', 'snapshot_date'],
        incremental_strategy='delete+insert'
    )
}}

select
    opportunity_id,
    current_date as snapshot_date,
    stage_name,
    amount,
    probability,
    close_date,
    source_last_modified_at
from {{ ref('fct_salesforce_opportunities') }}

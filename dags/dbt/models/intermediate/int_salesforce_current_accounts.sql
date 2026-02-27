{{
    config(
        materialized='incremental',
        unique_key='account_id',
        incremental_strategy='delete+insert'
    )
}}

with ranked as (
    select
        account_id,
        account_name,
        account_number,
        account_type,
        industry,
        annual_revenue,
        number_of_employees,
        website,
        phone,
        owner_id,
        parent_account_id,
        billing_city,
        billing_state,
        billing_country,
        shipping_city,
        shipping_state,
        shipping_country,
        is_active,
        systemmodstamp,
        extracted_at,
        row_number() over (
            partition by account_id
            order by systemmodstamp desc nulls last, extracted_at desc
        ) as row_priority
    from {{ ref('stg_salesforce_accounts') }}
    where coalesce(is_deleted, false) = false
    {% if is_incremental() %}
      and systemmodstamp >= (
          select coalesce(max(systemmodstamp), '1900-01-01'::timestamptz)
          from {{ this }}
      )
    {% endif %}
)
select *
from ranked
where row_priority = 1

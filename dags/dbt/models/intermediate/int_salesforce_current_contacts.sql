{{
    config(
        materialized='incremental',
        unique_key='contact_id',
        incremental_strategy='delete+insert'
    )
}}

with ranked as (
    select
        contact_id,
        account_id,
        first_name,
        last_name,
        full_name,
        email,
        phone,
        mobile_phone,
        title,
        department,
        lead_source,
        owner_id,
        systemmodstamp,
        extracted_at,
        row_number() over (
            partition by contact_id
            order by systemmodstamp desc nulls last, extracted_at desc
        ) as row_priority
    from {{ ref('stg_salesforce_contacts') }}
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

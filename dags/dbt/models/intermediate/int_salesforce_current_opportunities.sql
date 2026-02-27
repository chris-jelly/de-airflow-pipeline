{{
    config(
        materialized='incremental',
        unique_key='opportunity_id',
        incremental_strategy='delete+insert'
    )
}}

with ranked as (
    select
        opportunity_id,
        account_id,
        opportunity_name,
        stage_name,
        amount,
        probability,
        close_date,
        opportunity_type,
        forecast_category_name,
        is_closed,
        is_won,
        lead_source,
        next_step,
        owner_id,
        currency_iso_code,
        systemmodstamp,
        extracted_at,
        row_number() over (
            partition by opportunity_id
            order by systemmodstamp desc nulls last, extracted_at desc
        ) as row_priority
    from {{ ref('stg_salesforce_opportunities') }}
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

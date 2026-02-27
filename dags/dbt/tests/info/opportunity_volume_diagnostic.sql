{{ config(severity='warn', tags=['info', 'monitor-only']) }}

with counts as (
    select
        date_trunc('day', coalesce(close_date::timestamp, now())) as business_day,
        count(*) as opportunities
    from {{ ref('fct_salesforce_opportunities') }}
    group by 1
)
select *
from counts
where opportunities = 0

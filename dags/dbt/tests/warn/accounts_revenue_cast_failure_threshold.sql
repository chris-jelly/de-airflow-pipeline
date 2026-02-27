{{ config(severity='warn', tags=['warn', 'cast-failure']) }}

with raw_counts as (
    select count(*) as raw_populated
    from raw_salesforce.accounts
    where nullif("AnnualRevenue", '') is not null
),
typed_counts as (
    select count(*) as typed_populated
    from {{ ref('stg_salesforce_accounts') }}
    where annual_revenue is not null
),
stats as (
    select
        raw_populated,
        typed_populated,
        case
            when raw_populated = 0 then 0
            else 1 - (typed_populated::numeric / raw_populated::numeric)
        end as failure_ratio
    from raw_counts
    cross join typed_counts
)
select *
from stats
where failure_ratio > 0.05

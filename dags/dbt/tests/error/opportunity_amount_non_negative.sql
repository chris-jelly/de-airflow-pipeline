{{ config(severity='error', tags=['error', 'critical']) }}

select
    opportunity_id,
    amount
from {{ ref('fct_salesforce_opportunities') }}
where amount is not null
  and amount < 0

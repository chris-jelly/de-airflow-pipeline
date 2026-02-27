{{ config(severity='warn', tags=['warn', 'drift']) }}

select
    opportunity_id,
    stage_name
from {{ ref('fct_salesforce_opportunities') }}
where stage_name is not null
  and stage_name not in (
      'Prospecting',
      'Qualification',
      'Needs Analysis',
      'Value Proposition',
      'Id. Decision Makers',
      'Proposal/Price Quote',
      'Negotiation/Review',
      'Closed Won',
      'Closed Lost'
  )

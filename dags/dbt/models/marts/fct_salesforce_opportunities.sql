select
    opp.opportunity_id,
    opp.account_id,
    acc.account_name,
    opp.opportunity_name,
    opp.stage_name,
    opp.amount,
    opp.probability,
    opp.close_date,
    opp.opportunity_type,
    opp.is_closed,
    opp.is_won,
    opp.currency_iso_code,
    opp.systemmodstamp as source_last_modified_at,
    opp.extracted_at as raw_extracted_at
from {{ ref('int_salesforce_current_opportunities') }} as opp
left join {{ ref('dim_salesforce_accounts') }} as acc
    on opp.account_id = acc.account_id

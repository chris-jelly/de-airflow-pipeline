{{ config(severity='error', tags=['error', 'critical']) }}

select
    opportunity_id,
    snapshot_date,
    count(*) as record_count
from {{ ref('opportunity_history_snapshot') }}
group by 1, 2
having count(*) > 1

{{ config(severity='warn', tags=['warn', 'freshness']) }}

with last_extract as (
    select max(extracted_at) as max_extracted_at
    from raw_salesforce.opportunities
)
select max_extracted_at
from last_extract
where max_extracted_at is null
   or max_extracted_at < now() - interval '7 day'

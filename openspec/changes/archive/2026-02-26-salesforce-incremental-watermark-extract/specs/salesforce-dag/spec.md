## MODIFIED Requirements

### Requirement: Extraction logic unchanged

The Salesforce extraction logic SHALL use curated explicit field lists and watermark-based incremental queries by `SystemModstamp`, while continuing to extract `Account`, `Opportunity`, and `Contact` into bronze tables.

#### Scenario: Same Salesforce objects extracted

- **WHEN** the DAG executes
- **THEN** it SHALL extract `Account`, `Opportunity`, and `Contact` objects to `bronze.accounts`, `bronze.opportunities`, and `bronze.contacts` tables respectively

#### Scenario: Incremental extraction query behavior

- **WHEN** the extraction task queries Salesforce
- **THEN** it SHALL use an explicit curated field list per object and SHALL apply watermark filtering by `SystemModstamp` instead of querying all historical rows on every run

#### Scenario: Audit columns present

- **WHEN** records are written to Postgres
- **THEN** each record SHALL include `extracted_at` (timezone-aware timestamp) and `dag_run_id` columns

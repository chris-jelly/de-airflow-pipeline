## ADDED Requirements

### Requirement: Curated field selection for Salesforce extraction
The extraction process SHALL query `Account`, `Contact`, and `Opportunity` using explicit curated field lists that are filtered to fields available in the connected org schema.

#### Scenario: Query uses explicit schema-compatible fields
- **WHEN** the DAG builds a SOQL query for an object
- **THEN** it SHALL generate `SELECT <explicit field list> FROM <object>` using curated fields that exist on that object and SHALL NOT generate `SELECT *`

#### Scenario: Curated list includes required change-tracking fields
- **WHEN** curated fields are configured for `Account`, `Contact`, and `Opportunity`
- **THEN** each object field list SHALL include `Id` and `SystemModstamp`

#### Scenario: Required tracking fields are validated before query
- **WHEN** field compatibility filtering is applied to an object's curated list
- **THEN** `Id` and `SystemModstamp` SHALL remain in the final selected field list and the task SHALL fail fast with an actionable error if either field is unavailable

### Requirement: Watermark-based incremental extraction
The extraction process SHALL pull only records newer than the persisted per-object watermark using `SystemModstamp`.

#### Scenario: Incremental filter applied
- **WHEN** an extraction run starts for an object with an existing watermark
- **THEN** the SOQL query SHALL include a `SystemModstamp` filter that limits results to records newer than that object's watermark

#### Scenario: Initial run without prior watermark
- **WHEN** an extraction run starts for an object without an existing watermark
- **THEN** the DAG SHALL perform an initial bootstrap extract and persist a watermark for subsequent incremental runs

### Requirement: Deterministic and retry-safe incremental ordering
Incremental results SHALL be retrieved in deterministic order and loaded with idempotent semantics so retries do not create duplicate final state.

#### Scenario: Deterministic ordering
- **WHEN** an incremental SOQL query is executed
- **THEN** it SHALL order by `SystemModstamp` and `Id`

#### Scenario: Retry-safe rerun
- **WHEN** the same incremental window is processed again due to retry or rerun
- **THEN** the load outcome SHALL remain idempotent for each Salesforce record `Id`

### Requirement: Delete handling deferred
This capability SHALL exclude Salesforce hard-delete capture in this change.

#### Scenario: In-scope extraction behavior
- **WHEN** the incremental extraction is implemented
- **THEN** it SHALL process inserts and updates only, and SHALL defer delete strategy to a future change

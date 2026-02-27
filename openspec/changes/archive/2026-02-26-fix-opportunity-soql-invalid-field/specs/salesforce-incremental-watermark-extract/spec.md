## MODIFIED Requirements

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

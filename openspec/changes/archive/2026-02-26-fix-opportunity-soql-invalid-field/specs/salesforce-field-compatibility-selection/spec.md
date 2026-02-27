## ADDED Requirements

### Requirement: Schema-compatible curated field selection
The extraction process SHALL build each Salesforce object query from curated fields that exist in the connected org's object schema.

#### Scenario: Optional missing fields are excluded from query
- **WHEN** curated fields for an object include fields that are not present in that object's describe metadata
- **THEN** the generated SOQL SHALL exclude those missing fields and continue extraction with the remaining valid curated fields

#### Scenario: Query remains explicit
- **WHEN** the query is generated after schema compatibility filtering
- **THEN** it SHALL use an explicit `SELECT <field list> FROM <object>` field list and SHALL NOT use wildcard selection

### Requirement: Field compatibility observability
The extraction process SHALL record field compatibility decisions for each object during query generation.

#### Scenario: Skipped fields are logged
- **WHEN** one or more curated fields are excluded because they are unavailable in the connected org
- **THEN** the task SHALL log the object name and the skipped field names in a warning-level message

#### Scenario: Selected fields are logged
- **WHEN** a schema-compatible query field list is finalized
- **THEN** the task SHALL log the object name and selected field names before executing the SOQL query

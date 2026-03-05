## ADDED Requirements

### Requirement: Canonical modeled schema boundaries
The system SHALL materialize Salesforce dbt modeled layers into canonical warehouse schemas `staging`, `intermediate`, and `marts`.

#### Scenario: Staging models land in canonical staging schema
- **WHEN** Salesforce dbt staging models are built
- **THEN** they SHALL materialize in the `staging` schema

#### Scenario: Intermediate models land in canonical intermediate schema
- **WHEN** Salesforce dbt intermediate models are built
- **THEN** they SHALL materialize in the `intermediate` schema

#### Scenario: Marts models land in canonical marts schema
- **WHEN** Salesforce dbt marts models are built
- **THEN** they SHALL materialize in the `marts` schema

### Requirement: Prefixed modeled schemas are not used in single-environment deployment
The system SHALL NOT treat prefixed modeled schemas (for example `staging_staging`, `staging_intermediate`, `staging_marts`) as canonical outputs in the current single-environment deployment.

#### Scenario: Canonical schema discovery
- **WHEN** operators inspect warehouse schemas for modeled outputs
- **THEN** the authoritative modeled layer outputs SHALL be in `staging`, `intermediate`, and `marts`

## ADDED Requirements

### Requirement: Typed Salesforce staging models
The system SHALL provide dbt staging models for Salesforce `accounts`, `contacts`, and `opportunities` that normalize raw text fields into explicit typed columns.

#### Scenario: Accounts staging typing
- **WHEN** the accounts staging model is built from raw Salesforce landing data
- **THEN** it SHALL cast configured account numeric, boolean, date, and timestamp fields into target SQL types while preserving source identifiers and text attributes

#### Scenario: Contacts staging typing
- **WHEN** the contacts staging model is built from raw Salesforce landing data
- **THEN** it SHALL cast configured contact boolean and timestamp fields into target SQL types while preserving source identifiers and text attributes

#### Scenario: Opportunities staging typing
- **WHEN** the opportunities staging model is built from raw Salesforce landing data
- **THEN** it SHALL cast configured opportunity numeric, boolean, date, and timestamp fields into target SQL types while preserving source identifiers and text attributes

### Requirement: Incremental change capture based on technical update time
Salesforce transformation logic SHALL use `SystemModstamp` as the technical change driver for incremental processing of mutable entities.

#### Scenario: Late update to old business date record
- **WHEN** a Salesforce record is updated after its business date period has passed
- **THEN** incremental transformation logic SHALL still process the record based on newer `SystemModstamp`

#### Scenario: Incremental filters avoid business-date-only cutoffs
- **WHEN** transformation models select changed rows incrementally
- **THEN** they SHALL NOT rely solely on business event dates such as `CloseDate`

### Requirement: Current-state upsert semantics for mutable models
Models that represent current-state Salesforce entities SHALL use unique-key-based incremental semantics to avoid duplicate final state across reruns and retries.

#### Scenario: Retry of same change window
- **WHEN** the same incremental change window is processed more than once
- **THEN** current-state model outputs SHALL remain unique at entity grain and reflect latest values

#### Scenario: Existing entity receives updated attributes
- **WHEN** a known entity key appears with changed attributes in a new run
- **THEN** the model output SHALL update current-state values for that key instead of appending duplicate active rows

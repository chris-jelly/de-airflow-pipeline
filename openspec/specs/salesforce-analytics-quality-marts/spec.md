## ADDED Requirements

### Requirement: Severity-tiered dbt validation policy
The Salesforce transformation capability SHALL define and apply a severity-tiered validation policy with `error`, `warn`, and `info` levels.

#### Scenario: Contract-breaking quality failures
- **WHEN** critical structural validations fail (for example key nullability, key uniqueness, required relationship integrity, or critical numeric bounds)
- **THEN** validation severity SHALL be treated as `error` and the transformation run SHALL fail

#### Scenario: Non-critical drift conditions
- **WHEN** non-critical quality checks fail (for example accepted-values drift, soft freshness breaches, or cast-failure thresholds)
- **THEN** validation severity SHALL be treated as `warn` and the run SHALL surface warnings without failing by default

#### Scenario: Informational diagnostics
- **WHEN** monitor-only diagnostics are evaluated
- **THEN** they SHALL be surfaced as `info` signals for observability without affecting run success state

### Requirement: Query-ready marts for downstream analytics
The transformation capability SHALL provide marts that support downstream analytical consumption of Salesforce account and opportunity data.

#### Scenario: Account analytics dimension is available
- **WHEN** marts are built
- **THEN** a query-ready account dimension output SHALL be available with stable keys and business attributes suitable for filtering and grouping

#### Scenario: Opportunity analytics fact is available
- **WHEN** marts are built
- **THEN** a query-ready opportunity fact output SHALL be available with measures and dimensions needed for pipeline analysis

### Requirement: Lightweight opportunity history output
The transformation capability SHALL provide a lightweight opportunity history pattern that captures temporal changes without requiring full SCD2 across all entities.

#### Scenario: Snapshot grain is enforced
- **WHEN** opportunity history data is produced
- **THEN** each record SHALL be uniquely identifiable by opportunity key and snapshot grain (for example snapshot date or run scope)

#### Scenario: Historical trend analysis is possible
- **WHEN** multiple history snapshots exist
- **THEN** the history output SHALL support analysis of stage and amount movement over time

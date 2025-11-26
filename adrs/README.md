# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records documenting significant architectural decisions made in this project.

## ADR Format

Each ADR follows this structure:
- **Status**: Proposed, Accepted, Rejected, Deprecated, Superseded
- **Context**: What is the issue we're facing?
- **Decision**: What decision did we make?
- **Consequences**: What are the trade-offs?

## Index

- [ADR-001: Per-DAG Container Images](001-per-dag-container-images.md) - Use separate container images for each DAG type
- [ADR-002: Pod-Level Secret Mounting](002-pod-level-secret-mounting.md) - Mount secrets per-DAG via executor_config
- [ADR-003: External Secrets Operator](003-external-secrets-operator.md) - Use ESO to sync secrets from Azure Key Vault
- [ADR-004: Secret Management Alternatives](004-secret-management-alternatives.md) - Comparison of different secret management approaches

## Creating New ADRs

When making a significant architectural decision:

1. Copy the template below
2. Create a new file: `NNN-title-in-kebab-case.md`
3. Fill out all sections
4. Update this index
5. Commit with the code changes

### ADR Template

```markdown
# ADR-NNN: Title

**Status**: Proposed | Accepted | Rejected | Deprecated | Superseded

**Date**: YYYY-MM-DD

**Deciders**: [list of people involved]

## Context

What is the issue that we're seeing that is motivating this decision or change?

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or more difficult to do because of this change?

### Positive
- [positive consequence]

### Negative
- [negative consequence]

### Neutral
- [neutral consequence]

## Alternatives Considered

### Alternative 1
- Description
- Pros/Cons
- Why not chosen

### Alternative 2
- Description
- Pros/Cons
- Why not chosen
```

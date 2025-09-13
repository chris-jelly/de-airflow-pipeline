# ADR-001: CI/CD Pipeline Architecture for Airflow Data Pipeline

## Status
Accepted

## Context
The de-airflow-pipeline project needs a robust CI/CD pipeline to ensure code quality, automate testing, and provide secure deployment mechanisms. The project is an Airflow-based data engineering pipeline that extracts data from Salesforce and loads it into PostgreSQL for a Kubernetes-based deployment.

## Decision
We will implement a comprehensive CI/CD pipeline using GitHub Actions, following patterns established in the devops-study-app project but adapted for Airflow and data engineering workflows.

### Architecture Components

#### 1. Testing and Quality Assurance (`.github/workflows/airflow-tests.yaml`)
- **Path-based filtering**: Only run tests when relevant files change (dags/, de_airflow_pipeline/, tests/, configs)
- **UV package manager**: Use UV for fast Python dependency management and environment setup
- **Multi-layered testing**:
  - Ruff linting and formatting validation
  - DAG syntax validation using Python compilation
  - DAG import testing to ensure all dependencies load correctly
  - pytest execution with coverage reporting (70% minimum threshold)
  - Docker image building and Trivy security scanning
- **PR Integration**: Automated coverage reports as PR comments using sticky comments

#### 2. Container Registry and Deployment (`.github/workflows/docker-build-push.yaml`)
- **Trigger**: Git tags matching `v*` pattern
- **Registry**: GitHub Container Registry (ghcr.io) for seamless integration
- **Security**: Trivy vulnerability scanning with SARIF upload to GitHub Security tab
- **Optimization**: Docker Buildx with GitHub Actions cache for faster builds
- **Versioning**: Both semantic version tags and `latest` tag support

#### 3. Release Management (`.github/workflows/release-please.yaml`)
- **Automation**: Release Please for conventional commit-based releases
- **Configuration**: Single-package Python project setup
- **Integration**: Automatic changelog generation and version bumping
- **Trigger**: Push to main branch initiates release candidate creation

#### 4. Development Environment Enhancement
- **Dependencies**: Added pytest-cov for coverage reporting
- **Configuration**: Comprehensive ruff, pytest, and coverage settings
- **Standards**: Line length 120, Python 3.9+ target, security-focused linting rules

#### 5. Comprehensive Test Suite
- **DAG Integrity Tests**: Validate DAG structure, imports, and Airflow-specific requirements
- **Connection Tests**: Mock and validate environment variable configurations for Salesforce and PostgreSQL
- **Import Tests**: Ensure all dependencies and packages can be imported correctly

## Rationale

### Why GitHub Actions over alternatives?
- **Native integration**: Seamless with GitHub repository and container registry
- **Cost-effective**: Free for public repositories, reasonable pricing for private
- **Ecosystem**: Rich marketplace of actions and integrations
- **Security**: Built-in secret management and security scanning integration

### Why Release Please?
- **Automation**: Reduces manual release management overhead
- **Consistency**: Enforces conventional commit standards
- **Transparency**: Automatic changelog generation improves project documentation
- **Integration**: Seamless tag creation triggers Docker builds

### Why Trivy for security scanning?
- **Comprehensive**: Scans both OS packages and application dependencies
- **Integration**: Native GitHub Security tab integration
- **Performance**: Fast scanning with caching support
- **Open source**: No vendor lock-in, community-supported

### Why path-based filtering?
- **Efficiency**: Reduces unnecessary CI runs, saving compute resources
- **Speed**: Faster feedback cycles for developers
- **Cost optimization**: Minimizes GitHub Actions minute consumption

## Consequences

### Positive
- **Automated quality gates**: Prevent low-quality code from reaching main branch
- **Security-first approach**: Vulnerability scanning at multiple stages
- **Developer experience**: Fast feedback with comprehensive test coverage
- **Deployment automation**: Consistent, repeatable container builds
- **Documentation**: Self-documenting releases with automatic changelogs

### Negative
- **Complexity**: Multiple workflow files require maintenance
- **Dependencies**: Relies on external actions that may change or become unavailable
- **Learning curve**: Team needs to understand conventional commits and release process

### Risks and Mitigations
- **Risk**: GitHub Actions outage affects deployments
  - *Mitigation*: Local development scripts mirror CI processes
- **Risk**: Third-party actions introduce vulnerabilities
  - *Mitigation*: Pin action versions and regularly audit dependencies
- **Risk**: Secrets exposure in CI logs
  - *Mitigation*: Use GitHub secrets, never log sensitive information

## Implementation Notes

### Airflow-Specific Adaptations
1. **DAG validation**: Custom Python compilation checks for DAG syntax
2. **Environment variables**: Testing strategy for connection configurations
3. **Import validation**: Ensure Airflow providers and custom packages load correctly
4. **Container considerations**: Airflow-optimized Docker build process

### Security Considerations
1. **Least privilege**: GitHub Actions permissions follow minimal access principle
2. **Secret scanning**: Environment variables tested without exposing values
3. **Vulnerability management**: Multi-stage security scanning (code, dependencies, containers)
4. **Container security**: Base image security scanning and updates

### Monitoring and Observability
1. **Coverage tracking**: Minimum 70% test coverage with trend monitoring
2. **Build metrics**: Track build times, success rates, and failure patterns
3. **Security alerts**: Automated notifications for vulnerability discoveries
4. **Deployment tracking**: Container registry metrics and usage patterns

## Alternatives Considered

### GitLab CI
- **Pros**: Integrated GitLab ecosystem, powerful pipeline features
- **Cons**: Would require repository migration, additional learning curve

### Jenkins
- **Pros**: Highly customizable, on-premise deployment option
- **Cons**: Infrastructure overhead, maintenance burden, slower setup

### CircleCI
- **Pros**: Good performance, Docker-first approach
- **Cons**: Additional service dependency, cost for private repositories

## Future Considerations
- **Multi-environment deployments**: Extend pipeline for staging/production environments
- **Integration testing**: Add database integration tests with test containers
- **Performance testing**: Benchmark DAG execution times and resource usage
- **Compliance scanning**: Add data governance and compliance validation steps
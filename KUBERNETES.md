# Kubernetes Deployment Guide

This document describes how to use the containerized Airflow pipeline with KubernetesExecutor.

## Container Image

The project automatically builds and publishes a Docker container to GitHub Container Registry (GHCR) on every push to main/develop branches and on version tags.

### Image Location

```
ghcr.io/<owner>/de-airflow-pipeline:<tag>
```

Available tags:
- `latest` - Latest build from main branch
- `main` - Latest build from main branch
- `develop` - Latest build from develop branch
- `v*` - Semantic version tags (e.g., `v1.0.0`, `v1.0`, `v1`)
- `<branch>-<sha>` - Specific commit SHA from a branch

### Building Locally

To build the container locally:

```bash
docker build -t de-airflow-pipeline:local .
```

The Dockerfile uses UV for dependency management, ensuring fast and reproducible builds.

## Kubernetes Configuration

### Prerequisites

1. Airflow installed with KubernetesExecutor
2. Kubernetes cluster access
3. Access to pull images from GHCR (may require authentication for private repos)

### Image Pull Secret (for private repositories)

If your repository is private, create an image pull secret:

```bash
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<github-token> \
  --namespace=airflow
```

### Airflow Configuration

Configure your Airflow deployment to use the container image for KubernetesExecutor:

#### Option 1: Helm Values (Recommended)

If using the official Airflow Helm chart:

```yaml
# values.yaml
images:
  airflow:
    repository: ghcr.io/<owner>/de-airflow-pipeline
    tag: latest
    pullPolicy: Always

# For private repos
imagePullSecrets:
  - name: ghcr-secret

executor: KubernetesExecutor

env:
  # Salesforce credentials
  - name: SALESFORCE_USERNAME
    valueFrom:
      secretKeyRef:
        name: salesforce-credentials
        key: username
  - name: SALESFORCE_PASSWORD
    valueFrom:
      secretKeyRef:
        name: salesforce-credentials
        key: password
  - name: SALESFORCE_SECURITY_TOKEN
    valueFrom:
      secretKeyRef:
        name: salesforce-credentials
        key: security_token
  - name: SALESFORCE_DOMAIN
    value: "login"

  # PostgreSQL credentials
  - name: POSTGRES_HOST
    valueFrom:
      secretKeyRef:
        name: postgres-credentials
        key: host
  - name: POSTGRES_DATABASE
    valueFrom:
      secretKeyRef:
        name: postgres-credentials
        key: database
  - name: POSTGRES_USER
    valueFrom:
      secretKeyRef:
        name: postgres-credentials
        key: username
  - name: POSTGRES_PASSWORD
    valueFrom:
      secretKeyRef:
        name: postgres-credentials
        key: password
  - name: POSTGRES_PORT
    value: "5432"
```

#### Option 2: airflow.cfg

```ini
[kubernetes]
worker_container_repository = ghcr.io/<owner>/de-airflow-pipeline
worker_container_tag = latest
delete_worker_pods = True
delete_worker_pods_on_failure = False

[kubernetes_environment_variables]
SALESFORCE_USERNAME = {{ salesforce_username }}
SALESFORCE_PASSWORD = {{ salesforce_password }}
SALESFORCE_SECURITY_TOKEN = {{ salesforce_token }}
POSTGRES_HOST = {{ postgres_host }}
POSTGRES_DATABASE = {{ postgres_database }}
POSTGRES_USER = {{ postgres_user }}
POSTGRES_PASSWORD = {{ postgres_password }}
```

### Creating Kubernetes Secrets

Create secrets for your credentials:

```bash
# Salesforce credentials
kubectl create secret generic salesforce-credentials \
  --from-literal=username='your-username' \
  --from-literal=password='your-password' \
  --from-literal=security_token='your-token' \
  --namespace=airflow

# PostgreSQL credentials
kubectl create secret generic postgres-credentials \
  --from-literal=host='postgres.example.com' \
  --from-literal=database='your-database' \
  --from-literal=username='your-username' \
  --from-literal=password='your-password' \
  --namespace=airflow
```

## Container Details

### UV-Based Dependency Installation

The container uses UV for dependency management, which provides:
- **Fast installations**: UV is significantly faster than pip
- **Reproducible builds**: Uses `uv.lock` for exact dependency versions
- **Efficient caching**: Better layer caching in Docker builds

### Directory Structure

```
/opt/airflow/
├── dags/                          # DAG files
│   └── salesforce_extraction_dag.py
├── scripts/                       # Utility scripts
├── pyproject.toml                 # Project metadata and dependencies
└── uv.lock                        # Locked dependencies
```

### Environment Variables

The container expects the following environment variables:

**Required:**
- `SALESFORCE_USERNAME` - Salesforce username
- `SALESFORCE_PASSWORD` - Salesforce password
- `SALESFORCE_SECURITY_TOKEN` - Salesforce security token
- `POSTGRES_HOST` - PostgreSQL host
- `POSTGRES_DATABASE` - PostgreSQL database name
- `POSTGRES_USER` - PostgreSQL username
- `POSTGRES_PASSWORD` - PostgreSQL password

**Optional:**
- `SALESFORCE_DOMAIN` - Salesforce domain (default: 'login')
- `POSTGRES_PORT` - PostgreSQL port (default: 5432)

## Deployment Workflow

1. **Code Changes**: Push code to repository
2. **CI/CD**: GitHub Actions automatically builds and pushes the container
3. **Tag Release**: Create a version tag for production releases
4. **Update Kubernetes**: Update Helm values or configuration to use new tag
5. **Deploy**: Apply Kubernetes changes

### Automatic Updates

For development environments, use the `latest` or `develop` tag with `imagePullPolicy: Always` to automatically pull new images.

For production, use specific version tags (e.g., `v1.0.0`) and control updates explicitly.

## Troubleshooting

### Image Pull Failures

```bash
# Check if secret exists
kubectl get secret ghcr-secret -n airflow

# Verify image exists
docker pull ghcr.io/<owner>/de-airflow-pipeline:latest
```

### Pod Failures

```bash
# Check pod logs
kubectl logs -n airflow <pod-name>

# Describe pod for events
kubectl describe pod -n airflow <pod-name>

# Check environment variables
kubectl exec -n airflow <pod-name> -- env | grep -E "(SALESFORCE|POSTGRES)"
```

### DAG Import Errors

```bash
# Check if DAGs are in the container
kubectl exec -n airflow <scheduler-pod> -- ls -la /opt/airflow/dags/

# Test DAG syntax
kubectl exec -n airflow <scheduler-pod> -- python -m py_compile /opt/airflow/dags/salesforce_extraction_dag.py
```

## Local Testing

Test the container locally before deploying to Kubernetes:

```bash
# Build the container
docker build -t de-airflow-pipeline:test .

# Run with environment variables
docker run -it --rm \
  -e SALESFORCE_USERNAME=test \
  -e SALESFORCE_PASSWORD=test \
  -e SALESFORCE_SECURITY_TOKEN=test \
  -e POSTGRES_HOST=localhost \
  -e POSTGRES_DATABASE=test \
  -e POSTGRES_USER=test \
  -e POSTGRES_PASSWORD=test \
  de-airflow-pipeline:test \
  bash

# Inside container, test DAG
python -m py_compile /opt/airflow/dags/salesforce_extraction_dag.py
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/build-and-push-container.yml`) automatically:

1. Builds the Docker image using UV for dependency installation
2. Pushes to GHCR with appropriate tags
3. Creates build attestations for security
4. Uses layer caching for faster builds

The workflow triggers on:
- Pushes to `main` or `develop` branches
- Version tags (`v*`)
- Pull requests (build only, no push)
- Manual workflow dispatch

## Security Considerations

1. **Secrets**: Never hardcode credentials in the container or code
2. **Image Scanning**: Consider adding image scanning to the CI/CD pipeline
3. **RBAC**: Use Kubernetes RBAC to restrict pod permissions
4. **Network Policies**: Implement network policies to control egress/ingress
5. **Image Pull Policy**: Use specific tags in production, not `latest`

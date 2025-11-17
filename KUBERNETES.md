# Kubernetes Deployment Guide

This document describes how to use the containerized Airflow pipeline with KubernetesExecutor.

## Multi-Image Strategy

This project uses a **per-DAG image strategy** where each DAG (or group of DAGs) has its own optimized container image containing only the dependencies it needs.

### Why Per-DAG Images?

- **Smaller images**: Executor pods only download what they need
- **Faster startup**: Less to install and initialize
- **Isolation**: No dependency conflicts between different DAG types
- **Cost efficiency**: Reduced network transfer and storage costs

See `CONTAINER_STRATEGY.md` for detailed information on the multi-image approach.

## Container Images

The project automatically builds and publishes multiple Docker containers to GitHub Container Registry (GHCR) on every push to main/develop branches and on version tags.

### Image Locations

```
ghcr.io/chris-jelly/de-airflow-pipeline:<dag-type>-<version>
```

**Current Images:**
- `ghcr.io/chris-jelly/de-airflow-pipeline:salesforce-latest` - Salesforce extraction DAG
- `ghcr.io/chris-jelly/de-airflow-pipeline:salesforce-v1.0.0` - Versioned Salesforce image

**Tag Patterns:**
- `<dag-type>-latest` - Latest build from main branch for specific DAG type
- `<dag-type>-main` - Latest build from main branch
- `<dag-type>-develop` - Latest build from develop branch
- `<dag-type>-v*` - Semantic version tags (e.g., `salesforce-v1.0.0`)

### Building Locally

To build a specific DAG image locally:

```bash
# Build salesforce image
docker build -f Dockerfile.salesforce -t de-airflow-pipeline:salesforce-local .

# Build future images
docker build -f Dockerfile.<dag-type> -t de-airflow-pipeline:<dag-type>-local .
```

Each Dockerfile uses UV for dependency management, ensuring fast and reproducible builds.

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

**IMPORTANT**: Core Airflow components (webserver, scheduler, triggerer) use the default Apache Airflow image. **Only executor pods (workers) use your custom per-DAG images**, which are specified in each DAG's code via `executor_config`.

#### Helm Values Configuration (Recommended)

If using the official Airflow Helm chart:

```yaml
# values.yaml
images:
  airflow:
    # Core components use official Airflow image
    repository: apache/airflow
    tag: 2.8.1-python3.11
    pullPolicy: IfNotPresent

# For private repos (needed to pull your custom DAG images)
imagePullSecrets:
  - name: ghcr-secret

executor: KubernetesExecutor

# Environment variables available to all pods
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

### How DAGs Specify Their Images

Each DAG specifies which container image to use via `executor_config` in the DAG definition. This allows different DAGs to use different images with different dependencies.

Example from `salesforce_extraction_dag.py`:

```python
# KubernetesExecutor configuration - specify custom image for this DAG
executor_config = {
    "pod_override": {
        "spec": {
            "containers": [
                {
                    "name": "base",
                    "image": "ghcr.io/chris-jelly/de-airflow-pipeline:salesforce-latest",
                }
            ]
        }
    }
}

default_args = {
    'owner': 'data-team',
    # ... other args ...
    'executor_config': executor_config,  # Apply to all tasks in this DAG
}

dag = DAG(
    'salesforce_extraction',
    default_args=default_args,
    # ... other dag args ...
)
```

You can also override at the task level:

```python
task = PythonOperator(
    task_id='my_task',
    python_callable=my_function,
    executor_config={
        "pod_override": {
            "spec": {
                "containers": [{
                    "name": "base",
                    "image": "ghcr.io/chris-jelly/de-airflow-pipeline:custom-latest",
                }]
            }
        }
    },
    dag=dag,
)
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

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

# SECURITY NOTE: Do NOT put data source credentials in global env vars!
# Instead, mount secrets per-DAG using executor_config (see below)
# Only put truly global, non-sensitive config here if needed
env: []
```

**Security Best Practice**: Secrets are mounted **per-DAG** using `executor_config`, not globally. This ensures:
- Scheduler/webserver don't have access to data credentials (principle of least privilege)
- Each DAG only gets the secrets it needs
- Different DAGs can't access each other's credentials

### How DAGs Specify Images and Secrets (Secure Approach)

Each DAG specifies **both** its container image **and** secrets via `executor_config`. This ensures secrets are only available to the specific pods that need them.

Example from `salesforce_extraction_dag.py`:

```python
# KubernetesExecutor configuration - specify custom image AND secrets for this DAG
# SECURITY: Secrets are mounted ONLY in executor pods for this DAG, not globally
executor_config = {
    "pod_override": {
        "spec": {
            "containers": [
                {
                    "name": "base",
                    "image": "ghcr.io/chris-jelly/de-airflow-pipeline:salesforce-latest",
                    # Mount secrets as environment variables ONLY for this DAG's pods
                    "env": [
                        {
                            "name": "SALESFORCE_USERNAME",
                            "valueFrom": {
                                "secretKeyRef": {
                                    "name": "salesforce-credentials",
                                    "key": "username"
                                }
                            }
                        },
                        {
                            "name": "SALESFORCE_PASSWORD",
                            "valueFrom": {
                                "secretKeyRef": {
                                    "name": "salesforce-credentials",
                                    "key": "password"
                                }
                            }
                        },
                        {
                            "name": "SALESFORCE_SECURITY_TOKEN",
                            "valueFrom": {
                                "secretKeyRef": {
                                    "name": "salesforce-credentials",
                                    "key": "security_token"
                                }
                            }
                        },
                        {
                            "name": "SALESFORCE_DOMAIN",
                            "value": "login"
                        },
                        # PostgreSQL credentials
                        {
                            "name": "POSTGRES_HOST",
                            "valueFrom": {
                                "secretKeyRef": {
                                    "name": "postgres-credentials",
                                    "key": "host"
                                }
                            }
                        },
                        # ... other PostgreSQL env vars ...
                    ]
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
```

**Benefits of this approach:**
1. **Least Privilege**: Scheduler/webserver don't get data credentials
2. **Isolation**: Each DAG only gets its own secrets
3. **Auditable**: Clear which DAG accesses which credentials
4. **Secure**: Secrets never in code, logs, or Airflow UI

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

## Advanced Security Options

### Option 1: Pod-Level Secrets (Implemented - Recommended)

**What we use**: Secrets mounted per-DAG via `executor_config`

**Pros**:
- Simple to implement and understand
- Clear visibility of which DAG uses which credentials
- No additional infrastructure required
- Works with standard Kubernetes secrets

**Cons**:
- Secrets still stored in etcd (encrypt etcd at rest!)
- Manual secret creation and rotation

### Option 2: Airflow Secrets Backend

Use Airflow's built-in secrets backend to pull from external systems:

```python
# In airflow.cfg or Helm values
[secrets]
backend = airflow.providers.google.cloud.secrets.secret_manager.CloudSecretManagerBackend
backend_kwargs = {"project_id": "your-project"}
```

Supported backends:
- **AWS Secrets Manager**
- **Google Cloud Secret Manager**
- **HashiCorp Vault**
- **Azure Key Vault**

**Pros**:
- Centralized secret management
- Automatic rotation support
- Audit logging built-in
- No secrets in Kubernetes

**Cons**:
- Requires additional infrastructure
- Cost for external secret service
- More complex setup

### Option 3: CSI Secret Driver (Most Secure)

Mount secrets from external providers directly into pods using Kubernetes CSI drivers:

```yaml
# In executor_config
volumes:
  - name: secrets-store
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: "salesforce-secrets"
volumeMounts:
  - name: secrets-store
    mountPath: "/mnt/secrets"
    readOnly: true
```

**Pros**:
- Secrets never stored in Kubernetes
- Automatic rotation
- Strong audit trail
- Works with any CSI provider (Vault, AWS, GCP, Azure)

**Cons**:
- Most complex to set up
- Requires CSI driver installation
- Platform-specific configuration

### Option 4: Workload Identity (Cloud Provider)

Use cloud provider workload identity to eliminate static credentials:

**AWS (IRSA)**:
```yaml
# Service account with IAM role
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789:role/airflow-salesforce
```

**GCP (Workload Identity)**:
```yaml
serviceAccount:
  annotations:
    iam.gke.io/gcp-service-account: airflow@project.iam.gserviceaccount.com
```

**Pros**:
- No static credentials to manage
- Automatic rotation handled by cloud provider
- Native cloud integration
- Fine-grained IAM permissions

**Cons**:
- Cloud-specific
- Doesn't work for third-party services like Salesforce
- Requires cloud provider setup

## Security Recommendations

### Minimum (What We Implement)
✅ Per-DAG secret mounting via `executor_config`
✅ Kubernetes secrets with RBAC
✅ Secrets never in code or logs
✅ Principle of least privilege

### Recommended for Production
✅ All of the above, plus:
✅ Encrypt Kubernetes etcd at rest
✅ Use external secrets backend (Vault, AWS Secrets Manager, etc.)
✅ Enable audit logging
✅ Implement secret rotation policies
✅ Use network policies to restrict pod communication

### Enterprise/Highly Sensitive
✅ All of the above, plus:
✅ CSI secret driver with HSM-backed secrets
✅ Workload identity where possible
✅ Runtime secret scanning
✅ Secrets never touch disk (memory-only mounts)
✅ Service mesh for mTLS between services

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

Environment variables are **mounted per-pod** via `executor_config` in each DAG, not globally.

**For Salesforce DAG (`salesforce_extraction_dag.py`):**
- `SALESFORCE_USERNAME` - Salesforce username (from secret)
- `SALESFORCE_PASSWORD` - Salesforce password (from secret)
- `SALESFORCE_SECURITY_TOKEN` - Salesforce security token (from secret)
- `SALESFORCE_DOMAIN` - Salesforce domain (default: 'login')
- `POSTGRES_HOST` - PostgreSQL host (from secret)
- `POSTGRES_DATABASE` - PostgreSQL database name (from secret)
- `POSTGRES_USER` - PostgreSQL username (from secret)
- `POSTGRES_PASSWORD` - PostgreSQL password (from secret)
- `POSTGRES_PORT` - PostgreSQL port (default: 5432)

These are defined in the DAG's `executor_config` and only available to that DAG's executor pods.

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

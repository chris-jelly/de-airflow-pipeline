# Container Image Strategy

This project uses a **multi-image strategy** where each DAG (or group of related DAGs) gets its own optimized container image containing only the dependencies it needs.

## Why Multiple Images?

1. **Smaller Images**: Each executor pod only downloads what it needs
2. **Faster Startup**: Less to download and install
3. **Better Isolation**: Dependency conflicts are eliminated
4. **Cost Efficiency**: Smaller images = less network transfer and storage

## Image Naming Convention

Each DAG type gets its own package in GHCR for better visibility and organization:

```
ghcr.io/<owner>/de-airflow-pipeline-<dag-type>:<version>
```

Examples:
- `ghcr.io/chris-jelly/de-airflow-pipeline-salesforce:latest`
- `ghcr.io/chris-jelly/de-airflow-pipeline-salesforce:v1.0.0`
- `ghcr.io/chris-jelly/de-airflow-pipeline-dbt:latest` (future)
- `ghcr.io/chris-jelly/de-airflow-pipeline-api:latest` (future)

**Benefits of separate packages:**
- Clear visibility in GHCR UI - each DAG type appears as its own package
- Easier to manage permissions per DAG type
- Simpler tag naming (just `latest`, `v1.0.0` instead of `salesforce-latest`)
- Better organization when you have many DAG types

## Current Images

### salesforce
**Purpose**: Salesforce to PostgreSQL extraction
**File**: `Dockerfile.salesforce`
**Dependencies**: `pyproject.salesforce.toml`
**DAGs**: `salesforce_extraction_dag.py`

## Adding a New Image

To create a new optimized image for a different DAG:

### 1. Create DAG-Specific Dependencies

Create `pyproject.<dag-type>.toml`:

```toml
# Note: No [build-system] section needed - we only use this for dependency management
[project]
name = "de-airflow-pipeline-<dag-type>"
version = "0.1.0"
description = "<dag-type> specific dependencies"
requires-python = ">=3.9"
dependencies = [
    # Only the dependencies this DAG needs
    "apache-airflow-providers-<provider>==x.x.x",
    "some-other-library==x.x.x",
]
```

### 2. Create DAG-Specific Dockerfile

Create `Dockerfile.<dag-type>`:

```dockerfile
FROM apache/airflow:3.1.5-python3.13

USER root
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN mkdir -p /opt/airflow/dags

WORKDIR /opt/airflow

# Copy DAG-specific dependencies
COPY --chown=airflow:root pyproject.<dag-type>.toml ./pyproject.toml

# Install dependencies as root (--system requires root permissions)
RUN uv pip install --system -r pyproject.toml

# Switch to airflow user for runtime
USER airflow

# Copy DAGs and scripts
COPY --chown=airflow:root dags/ /opt/airflow/dags/
COPY --chown=airflow:root scripts/ /opt/airflow/scripts/

ENV PYTHONPATH="/opt/airflow"
```

### 3. Update GitHub Actions Workflow

Add your new image to `.github/workflows/build-and-push-container.yml` in the matrix strategy (see the workflow for current configuration).

### 4. Configure DAG to Use the Image

In your DAG file, add executor_config:

```python
executor_config = {
    "pod_override": {
        "spec": {
            "containers": [
                {
                    "name": "base",
                    "image": "ghcr.io/chris-jelly/de-airflow-pipeline-<dag-type>:latest",
                }
            ]
        }
    }
}

default_args = {
    # ... other args ...
    'executor_config': executor_config,
}
```

## Core Airflow Components

The core Airflow components (webserver, scheduler, triggerer) should use the **default Apache Airflow image** from Docker Hub. Only the executor pods (workers) use your custom images.

### Helm Configuration

```yaml
# values.yaml
images:
  airflow:
    # Core components use official Airflow image
    repository: apache/airflow
    tag: 3.1.5-python3.13
    pullPolicy: IfNotPresent

# Executor pods will use DAG-specific images via executor_config
executor: KubernetesExecutor

# For private repos, add pull secrets
imagePullSecrets:
  - name: ghcr-secret
```

## Dependency Management Best Practices

1. **Pin Versions**: Always pin exact versions in pyproject.toml files
2. **Minimal Dependencies**: Only include what the DAG actually needs
3. **Provider Packages**: Use specific provider packages instead of installing all extras
4. **Test Locally**: Build and test images locally before pushing

```bash
# Build a specific image
docker build -f Dockerfile.salesforce -t de-airflow-pipeline:salesforce-test .

# Test the image
docker run -it --rm de-airflow-pipeline:salesforce-test bash

# Inside container, verify dependencies
uv pip list | grep airflow
```

## Shared Dependencies

If multiple DAGs share the same dependencies, you can:

1. **Group them** into a single image (e.g., `all-salesforce-dags`)
2. **Create a base image** with common dependencies, then layer DAG-specific ones

Example base image pattern:

```dockerfile
# Dockerfile.base - shared dependencies
FROM apache/airflow:3.1.5-python3.13
# ... install common deps ...

# Dockerfile.salesforce
FROM ghcr.io/chris-jelly/de-airflow-pipeline:base-latest
# ... install salesforce-specific deps ...
```

## Build Matrix Strategy

The GitHub Actions workflow uses a matrix strategy to build all images in parallel:

```yaml
strategy:
  matrix:
    include:
      - name: salesforce
        dockerfile: Dockerfile.salesforce
        dependencies: pyproject.salesforce.toml
      - name: dbt
        dockerfile: Dockerfile.dbt
        dependencies: pyproject.dbt.toml
```

This allows you to:
- Build all images in one workflow run
- Tag them appropriately with the DAG type
- Maintain them independently

## Image Size Optimization Tips

1. **Multi-stage builds**: Use multi-stage builds to reduce final image size
2. **Layer caching**: Order Dockerfile commands from least to most frequently changed
3. **Cleanup**: Remove build artifacts and cached files
4. **Base image choice**: Use slim Python images when possible

## Troubleshooting

### Image Not Found

If Airflow can't find your image:
1. Verify it was published: Check GHCR packages in your repository
2. Check image pull secret: `kubectl get secret ghcr-secret -n airflow`
3. Verify the image name in executor_config matches the published name

### Dependency Conflicts

If you see dependency conflicts:
1. Check the pyproject.toml for the DAG type
2. Rebuild with `uv sync --no-dev` to see errors
3. Use `uv tree` to visualize dependency tree

### Pod Failures

```bash
# Check which image the pod is using
kubectl describe pod <pod-name> -n airflow | grep Image

# Check for pull errors
kubectl describe pod <pod-name> -n airflow | grep -A 10 Events
```

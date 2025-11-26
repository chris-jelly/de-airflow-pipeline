# ADR-001: Per-DAG Container Images

**Status**: Accepted

**Date**: 2025-11-26

**Deciders**: Engineering Team

## Context

When running Airflow with KubernetesExecutor, executor pods need access to DAG code and dependencies. We need to decide on a container image strategy:

1. Single monolithic image with all dependencies for all DAGs
2. Separate optimized images per DAG (or DAG group)
3. Base image + dynamic dependency installation

The main concerns are:
- Image size and download times
- Build complexity and CI/CD overhead
- Dependency isolation between different DAG types
- Cost (storage, network transfer)

## Decision

We will use **separate container images per DAG type**, with each image containing only the dependencies needed for that specific DAG.

**Implementation:**
- Each DAG type gets its own `Dockerfile.<dag-type>` and `pyproject.<dag-type>.toml`
- DAGs specify their image in `executor_config`
- Core Airflow components (scheduler, webserver) use the default Apache Airflow image
- GitHub Actions builds all images in parallel using matrix strategy
- Images are tagged as: `ghcr.io/owner/repo:<dag-type>-<version>`

## Consequences

### Positive
- **Smaller executor pods**: Only download what's needed (e.g., Salesforce DAG doesn't get dbt dependencies)
- **Faster startup**: Less to download and install
- **Better isolation**: No dependency conflicts between DAG types
- **Cost efficiency**: Reduced network transfer and storage costs
- **Security**: Smaller attack surface per pod

### Negative
- **More Dockerfiles to maintain**: Each DAG type needs its own Dockerfile
- **CI/CD complexity**: Need matrix builds for multiple images
- **Initial setup overhead**: More upfront work to separate dependencies

### Neutral
- **Tagging strategy**: Requires clear naming convention for images
- **Documentation**: Need to document which DAG uses which image

## Alternatives Considered

### Alternative 1: Single Monolithic Image

**Description**: One Dockerfile with all dependencies for all DAGs

**Pros**:
- Simple: Only one Dockerfile and pyproject.toml
- Easy CI/CD: Single image build

**Cons**:
- Large images (1GB+) with dependencies never used by most pods
- Slow pod startup due to download time
- Dependency conflicts between different DAG requirements
- Higher costs (network, storage)

**Why not chosen**: Doesn't scale well as more DAG types are added. The first DAG might be fine, but adding API extraction, dbt transformations, ML pipelines, etc. would create a massive image.

### Alternative 2: Dynamic Dependency Installation

**Description**: Minimal base image, install dependencies at runtime per task

**Pros**:
- Smallest base image
- Ultimate flexibility

**Cons**:
- Slow task startup (install deps on every run)
- Non-deterministic (dependency versions could change)
- Network required during task execution
- More complex error handling

**Why not chosen**: Too slow and unreliable for production use. Tasks would spend significant time installing dependencies before doing actual work.

### Alternative 3: Base + Layer Images

**Description**: Common base image with shared dependencies, then layer DAG-specific deps on top

**Pros**:
- Share common dependencies
- Layer caching benefits

**Cons**:
- More complex build process
- Need to maintain base image separately
- Still requires multiple images

**Why not chosen**: Adds complexity without significant benefits given UV's fast dependency resolution. The overhead of multiple completely separate images is acceptable, and this approach can be revisited later if needed.

## Implementation Notes

Example DAG configuration:

```python
executor_config = {
    "pod_override": {
        "spec": {
            "containers": [{
                "name": "base",
                "image": "ghcr.io/chris-jelly/de-airflow-pipeline:salesforce-latest",
            }]
        }
    }
}
```

See `CONTAINER_STRATEGY.md` for detailed implementation guide.

# Local Airflow Development with k3d

This directory contains a complete local Kubernetes development environment for Airflow using k3d. It provides full parity with production KubernetesExecutor behavior, including pod spawning and Kubernetes secret mounting.

## Architecture

```
k3d Cluster "airflow-dev"
├── Local Registry (k3d-registry.localhost:5111)
├── Namespace: airflow
│   ├── Airflow Webserver + Scheduler (via Helm)
│   ├── PostgreSQL (Airflow metadata - via Helm)
│   ├── PostgreSQL (Target bronze layer - StatefulSet)
│   ├── Secrets: salesforce-credentials, postgres-credentials
│   └── Executor Pods (custom DAG images)
└── Volume Mount: ./dags → /dags (live DAG editing)
```

### Key Features

- **Production Parity**: Uses KubernetesExecutor just like production
- **Live DAG Editing**: DAGs mounted from host filesystem - no restarts needed
- **Local Registry**: Build and load DAG images without pushing to remote registry
- **Isolated Secrets**: Kubernetes secrets mounted per-DAG for security testing
- **Separate Databases**: Airflow metadata DB separate from target data warehouse
- **Fast Iteration**: Rebuild DAG images and see changes immediately

## Prerequisites

Install the following tools:

- **Docker Desktop** (or compatible Docker runtime)
- **k3d** v5.6+: `brew install k3d` or see [k3d installation](https://k3d.io/#installation)
- **kubectl**: `brew install kubectl`
- **Helm** v3+: `brew install helm`
- **Salesforce OAuth credentials** (Consumer Key + Secret from Connected App)

Verify installation:

```bash
k3d version
kubectl version --client
helm version
docker --version
```

## Quick Start

### One-Command Setup

```bash
cd k3d/scripts
./full-setup.sh
```

This will:
1. Create the k3d cluster with local registry
2. Interactively prompt for Salesforce and PostgreSQL credentials
3. Build and load the Salesforce DAG image to local registry
4. Deploy Airflow via Helm

Access Airflow UI:
- **URL**: http://localhost:30080
- **Username**: `admin`
- **Password**: `admin`

## Step-by-Step Setup

If you prefer manual control over each step:

### 1. Create k3d Cluster

```bash
./scripts/cluster-create.sh
```

This creates:
- 1 server + 2 agent nodes
- Local registry at `k3d-registry.localhost:5111`
- NodePort 30080 for Airflow UI
- Volume mount for live DAG editing

### 2. Setup Kubernetes Secrets

```bash
./scripts/secrets-setup.sh
```

This interactively creates:
- `salesforce-credentials`: OAuth consumer key/secret
- `postgres-credentials`: Target database connection info

For local development, use these PostgreSQL defaults:
- Host: `postgres-target.airflow.svc.cluster.local`
- Database: `warehouse`
- Username: `airflow`
- Password: `airflow123`

### 3. Build and Load DAG Images

```bash
./scripts/image-load.sh
```

This builds the Salesforce DAG Docker image and pushes it to the local k3d registry.

### 4. Deploy Airflow

```bash
./scripts/deploy-airflow.sh
```

This deploys Airflow via Helm with:
- KubernetesExecutor
- Airflow 2.8.1
- Minimal components (no flower, triggerer, etc.)
- DAGs mounted from host filesystem

### 5. Verify Installation

```bash
# Check all pods are running
kubectl get pods -n airflow

# Should see:
# - airflow-postgresql-0
# - airflow-scheduler-*
# - airflow-webserver-*
# - postgres-target-0

# View scheduler logs
kubectl logs -n airflow -l component=scheduler --tail=50 -f
```

## Development Workflow

### Editing DAGs

DAGs are mounted from your local `dags/` directory. Changes are picked up automatically:

1. Edit `dags/salesforce/salesforce_extraction_dag.py`
2. Wait for scheduler to detect changes (~30 seconds)
3. Refresh Airflow UI to see updated DAG

No restart required!

### Rebuilding DAG Images

When you change Python dependencies or task code:

```bash
cd k3d/scripts
./image-load.sh
```

This rebuilds and pushes the DAG image to the local registry. New DAG runs will use the updated image.

### Viewing Logs

```bash
# Scheduler logs
kubectl logs -n airflow -l component=scheduler --tail=50 -f

# Webserver logs
kubectl logs -n airflow -l component=webserver --tail=50 -f

# Worker pod logs (specific DAG run)
kubectl logs -n airflow <pod-name>

# Target PostgreSQL logs
kubectl logs -n airflow postgres-target-0
```

### Accessing Target Database

Connect to the target PostgreSQL database:

```bash
# Port forward PostgreSQL
kubectl port-forward -n airflow svc/postgres-target 5432:5432

# Connect with psql (in another terminal)
psql -h localhost -U airflow -d warehouse
# Password: airflow123

# Or use any PostgreSQL client
# Host: localhost
# Port: 5432
# Database: warehouse
# User: airflow
# Password: airflow123
```

### Testing DAGs

```bash
# From project root
cd dags/salesforce
uv sync
uv run pytest

# Or test DAG syntax
uv run python -m py_compile salesforce_extraction_dag.py
```

## Cleanup and Troubleshooting

### Delete Everything

```bash
cd k3d/scripts
./cluster-delete.sh
```

This removes the cluster, registry, and all volumes.

### Restart Airflow

```bash
# Restart scheduler
kubectl rollout restart deployment airflow-scheduler -n airflow

# Restart webserver
kubectl rollout restart deployment airflow-webserver -n airflow
```

### Common Issues

#### Pods stuck in Pending

```bash
kubectl describe pod <pod-name> -n airflow
```

Common causes:
- Insufficient resources (increase Docker Desktop memory)
- Image pull errors (check registry is running)
- Secret not found (verify secrets exist: `kubectl get secrets -n airflow`)

#### DAG image not updating

```bash
# Verify image was pushed
docker pull k3d-registry.localhost:5111/de-airflow-pipeline-salesforce:latest

# Check scheduler environment variable
kubectl get deployment airflow-scheduler -n airflow -o yaml | grep SALESFORCE_DAG_IMAGE

# Restart scheduler to pick up new image
kubectl rollout restart deployment airflow-scheduler -n airflow
```

#### UI not accessible

```bash
# Check NodePort mapping
kubectl get svc -n airflow airflow-webserver

# Should show NodePort 30080
# If not, check k3d/values-airflow.yaml

# Alternative: Use port-forward
./scripts/port-forward.sh
# Access on http://localhost:8080
```

#### Secrets not found

```bash
# List secrets
kubectl get secrets -n airflow

# Should see:
# - salesforce-credentials
# - postgres-credentials

# Recreate if missing
./scripts/secrets-setup.sh
```

#### Target PostgreSQL not starting

```bash
# Check logs
kubectl logs -n airflow postgres-target-0

# Check PVC
kubectl get pvc -n airflow

# Delete and recreate
kubectl delete -f manifests/postgres-target.yaml
kubectl apply -f manifests/postgres-target.yaml
```

## Configuration Files

| File | Purpose |
|------|---------|
| `cluster-config.yaml` | k3d cluster configuration |
| `values-airflow.yaml` | Helm chart values for Airflow |
| `manifests/namespace.yaml` | Kubernetes namespace |
| `manifests/postgres-target.yaml` | Target PostgreSQL StatefulSet |
| `manifests/secrets/*.template` | Secret templates |

## Scripts

| Script | Description |
|--------|-------------|
| `cluster-create.sh` | Create k3d cluster |
| `cluster-delete.sh` | Delete cluster and cleanup |
| `secrets-setup.sh` | Interactive secret creation |
| `image-load.sh` | Build and load DAG images |
| `deploy-airflow.sh` | Deploy Airflow via Helm |
| `port-forward.sh` | Port forward UI (alternative access) |
| `full-setup.sh` | One-command full setup |

## How It Works

### Local vs Production Images

The DAG uses an environment variable to switch between local and production images:

```python
# dags/salesforce/salesforce_extraction_dag.py:31
image=os.getenv(
    "SALESFORCE_DAG_IMAGE",
    "ghcr.io/chris-jelly/de-airflow-pipeline-salesforce:latest"
)
```

- **Local**: `SALESFORCE_DAG_IMAGE` set to `k3d-registry.localhost:5111/de-airflow-pipeline-salesforce:latest`
- **Production**: Uses GHCR image as fallback

### Secret Mounting

Secrets are mounted per-DAG using `executor_config`:

```python
executor_config = {
    "pod_override": k8s.V1Pod(
        spec=k8s.V1PodSpec(
            containers=[
                k8s.V1Container(
                    env=[
                        k8s.V1EnvVar(
                            name="SALESFORCE_CONSUMER_KEY",
                            value_from=k8s.V1EnvVarSource(
                                secret_key_ref=k8s.V1SecretKeySelector(
                                    name="salesforce-credentials",
                                    key="consumer_key"
                                )
                            )
                        ),
                        # ...
                    ]
                )
            ]
        )
    )
}
```

This ensures:
- Scheduler/webserver don't have access to credentials
- Each DAG only gets the secrets it needs
- Production parity for security testing

## Next Steps

- Add more DAG types (follow the per-DAG pattern)
- Integrate with dbt for silver/gold layers
- Add monitoring with Prometheus/Grafana
- Configure email alerts

## Resources

- [k3d Documentation](https://k3d.io/)
- [Airflow Helm Chart](https://airflow.apache.org/docs/helm-chart/)
- [KubernetesExecutor Guide](https://airflow.apache.org/docs/apache-airflow/stable/executor/kubernetes.html)

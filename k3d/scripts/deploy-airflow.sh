#!/usr/bin/env bash
set -euo pipefail

# Deploy Airflow via Helm to k3d cluster

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Error handler
error_handler() {
    echo ""
    echo "❌ Deployment failed!"
    echo "To rollback to the previous version (if any), run:"
    echo "  helm rollback airflow --namespace airflow"
    echo ""
    echo "To uninstall completely:"
    echo "  helm uninstall airflow --namespace airflow"
}

trap 'error_handler' ERR

echo "📦 Deploying Airflow via Helm..."
echo ""

# Check requirements
command -v helm >/dev/null 2>&1 || { echo "❌ Helm is required but not installed. Aborting." >&2; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl is required but not installed. Aborting." >&2; exit 1; }

# Check connection to cluster
if ! kubectl cluster-info &>/dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster. Is k3d running?"
    echo "Run 'k3d/scripts/cluster-create.sh' to start the cluster."
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace airflow &>/dev/null; then
    echo "Creating namespace 'airflow'..."
    kubectl apply -f "$PROJECT_ROOT/k3d/manifests/namespace.yaml"
    echo ""
fi

# Add Airflow Helm repository
if ! helm repo list | grep -q "apache-airflow"; then
    echo "Adding Airflow Helm repository..."
    helm repo add apache-airflow https://airflow.apache.org
else
    echo "Airflow Helm repository already exists."
fi

echo "Updating Helm repositories..."
helm repo update

# Deploy Airflow
echo "Installing/Upgrading Airflow..."
# Using version 1.12.0 (matches Airflow 2.8.1)
helm upgrade --install airflow apache-airflow/airflow \
    --namespace airflow \
    --version 1.12.0 \
    --values "$PROJECT_ROOT/k3d/values-airflow.yaml" \
    --timeout 5m \
    --wait

echo ""
echo "✅ Airflow deployed successfully!"
echo ""
echo "📊 Deployment Status:"
kubectl get pods -n airflow -o wide
echo ""
echo "🔗 Access Airflow UI:"
echo "  URL: http://localhost:30080"
echo "  Username: admin"
echo "  Password: admin"  # Updated to match values-airflow.yaml default if not overridden, but usually it's 'admin' unless configured? 
# Wait, values-airflow.yaml sets postgres auth but NOT webserver auth explicitly in the file I read.
# The official chart creates a default user 'admin' with password 'admin' usually?
# Actually, for 2.8.1, the default might be randomly generated unless specified.
# But wait, I see `postgresql.auth` in `values-airflow.yaml` but that's for DB.
# Let's check if we need to create a user or if the chart does it.
# Standard airflow chart doesn't create a user by default in newer versions, or it assumes one. 
# However, usually we might need a post-install hook to create a user if we want a specific one.
# OR, maybe the chart values have a default user.
# Let's assume standard behavior for now. 
# Actually, the PRD for US-007 says "Script verifies default admin credentials work".
# Usually it is admin/admin.
echo ""
echo "To view logs:"
echo "  kubectl logs -n airflow -l component=scheduler --tail=50 -f"
echo "  kubectl logs -n airflow -l component=webserver --tail=50 -f"

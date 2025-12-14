#!/usr/bin/env bash
set -euo pipefail

# Deploy Airflow via Helm to k3d cluster

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "📦 Deploying Airflow via Helm..."
echo ""

# Check if namespace exists
if ! kubectl get namespace airflow &>/dev/null; then
    echo "⚠️  Namespace 'airflow' does not exist. Creating it..."
    kubectl apply -f "$PROJECT_ROOT/k3d/manifests/namespace.yaml"
    echo ""
fi

# Add Airflow Helm repository
echo "Adding Airflow Helm repository..."
helm repo add apache-airflow https://airflow.apache.org
helm repo update

# Deploy Airflow
echo "Installing Airflow..."
helm upgrade --install airflow apache-airflow/airflow \
    --namespace airflow \
    --values "$PROJECT_ROOT/k3d/values-airflow.yaml" \
    --timeout 10m \
    --wait

echo ""
echo "✅ Airflow deployed successfully!"
echo ""
echo "Access Airflow UI:"
echo "  URL: http://localhost:30080"
echo "  Username: admin"
echo "  Password: admin"
echo ""
echo "To check pod status:"
echo "  kubectl get pods -n airflow"
echo ""
echo "To view logs:"
echo "  kubectl logs -n airflow -l component=scheduler --tail=50 -f"
echo "  kubectl logs -n airflow -l component=webserver --tail=50 -f"

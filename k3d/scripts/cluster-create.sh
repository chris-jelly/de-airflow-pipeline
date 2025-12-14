#!/usr/bin/env bash
set -euo pipefail

# Create k3d cluster for local Airflow development

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🚀 Creating k3d cluster 'airflow-dev'..."

# Check if cluster already exists
if k3d cluster list | grep -q "airflow-dev"; then
    echo "⚠️  Cluster 'airflow-dev' already exists. Delete it first with:"
    echo "   ./cluster-delete.sh"
    exit 1
fi

# Create cluster with configuration
cd "$PROJECT_ROOT"
k3d cluster create --config k3d/cluster-config.yaml

echo "✅ Cluster created successfully!"
echo ""
echo "Next steps:"
echo "  1. Create namespace: kubectl apply -f k3d/manifests/namespace.yaml"
echo "  2. Setup secrets: ./k3d/scripts/secrets-setup.sh"
echo "  3. Deploy Airflow: ./k3d/scripts/deploy-airflow.sh"
echo ""
echo "Or run the full setup: ./k3d/scripts/full-setup.sh"

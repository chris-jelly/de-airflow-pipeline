#!/usr/bin/env bash
set -euo pipefail

# Delete k3d cluster and local registry

echo "🗑️  Deleting k3d cluster 'airflow-dev'..."

# Check if cluster exists
if ! k3d cluster list | grep -q "airflow-dev"; then
    echo "⚠️  Cluster 'airflow-dev' does not exist"
    exit 0
fi

# Delete cluster (this also removes the registry)
k3d cluster delete airflow-dev

echo "✅ Cluster deleted successfully!"
echo ""
echo "To recreate the cluster, run: ./cluster-create.sh"

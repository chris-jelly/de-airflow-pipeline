#!/usr/bin/env bash
set -euo pipefail

# One-command full setup for local k3d Airflow development

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Full k3d Airflow Development Environment Setup"
echo "=================================================="
echo ""
echo "This will:"
echo "  1. Create k3d cluster"
echo "  2. Setup Kubernetes secrets"
echo "  3. Build and load DAG images"
echo "  4. Deploy Airflow via Helm"
echo ""
read -rp "Continue? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi
echo ""

# Step 1: Create cluster
echo "=== Step 1/4: Creating k3d cluster ==="
"$SCRIPT_DIR/cluster-create.sh"
echo ""

# Step 2: Setup secrets
echo "=== Step 2/4: Setting up secrets ==="
"$SCRIPT_DIR/secrets-setup.sh"
echo ""

# Step 3: Build and load images
echo "=== Step 3/4: Building and loading DAG images ==="
"$SCRIPT_DIR/image-load.sh"
echo ""

# Step 4: Deploy Airflow
echo "=== Step 4/4: Deploying Airflow ==="
"$SCRIPT_DIR/deploy-airflow.sh"
echo ""

echo "🎉 Setup complete!"
echo ""
echo "Access Airflow UI:"
echo "  URL: http://localhost:30080"
echo "  Username: admin"
echo "  Password: admin"
echo ""
echo "Useful commands:"
echo "  Check pods: kubectl get pods -n airflow"
echo "  View scheduler logs: kubectl logs -n airflow -l component=scheduler --tail=50 -f"
echo "  Rebuild DAG image: ./k3d/scripts/image-load.sh"
echo "  Delete cluster: ./k3d/scripts/cluster-delete.sh"

#!/usr/bin/env bash
set -euo pipefail

# Build and load DAG images to local k3d registry

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REGISTRY="k3d-registry.localhost:5111"

echo "🐳 Building and loading DAG images to local registry..."
echo ""

# Build salesforce DAG image
echo "Building salesforce DAG image..."
cd "$PROJECT_ROOT"
docker build -f dags/salesforce/Dockerfile -t de-airflow-pipeline-salesforce:latest .

# Tag for local registry
docker tag de-airflow-pipeline-salesforce:latest "$REGISTRY/de-airflow-pipeline-salesforce:latest"

# Push to local registry
echo "Pushing to local registry $REGISTRY..."
docker push "$REGISTRY/de-airflow-pipeline-salesforce:latest"

echo ""
echo "✅ Image loaded successfully!"
echo ""
echo "Image available at: $REGISTRY/de-airflow-pipeline-salesforce:latest"
echo ""
echo "To verify, run:"
echo "  docker pull $REGISTRY/de-airflow-pipeline-salesforce:latest"

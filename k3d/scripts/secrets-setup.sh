#!/usr/bin/env bash
set -euo pipefail

# Interactive script to create Kubernetes secrets for local Airflow development

echo "🔐 Setting up Kubernetes secrets for Airflow..."
echo ""
echo "This script will create the following secrets in the 'airflow' namespace:"
echo "  - salesforce-credentials"
echo "  - postgres-credentials"
echo ""

# Check if namespace exists
if ! kubectl get namespace airflow &>/dev/null; then
    echo "⚠️  Namespace 'airflow' does not exist. Creating it..."
    kubectl apply -f k3d/manifests/namespace.yaml
    echo ""
fi

# --- Salesforce Credentials ---
echo "=== Salesforce OAuth Credentials ==="
echo ""
read -rp "Enter Salesforce Consumer Key: " sf_consumer_key
read -rsp "Enter Salesforce Consumer Secret: " sf_consumer_secret
echo ""
echo ""

# Create salesforce-credentials secret
kubectl delete secret salesforce-credentials -n airflow 2>/dev/null || true
kubectl create secret generic salesforce-credentials \
    --namespace=airflow \
    --from-literal=consumer_key="$sf_consumer_key" \
    --from-literal=consumer_secret="$sf_consumer_secret"

echo "✅ Created salesforce-credentials secret"
echo ""

# --- PostgreSQL Credentials ---
echo "=== PostgreSQL Target Database Credentials ==="
echo ""
echo "For local k3d development, use these defaults:"
echo "  Host: postgres-target.airflow.svc.cluster.local"
echo "  Database: warehouse"
echo "  Username: airflow"
echo "  Password: airflow123"
echo ""
read -rp "PostgreSQL Host [postgres-target.airflow.svc.cluster.local]: " pg_host
pg_host="${pg_host:-postgres-target.airflow.svc.cluster.local}"

read -rp "PostgreSQL Database [warehouse]: " pg_database
pg_database="${pg_database:-warehouse}"

read -rp "PostgreSQL Username [airflow]: " pg_username
pg_username="${pg_username:-airflow}"

read -rsp "PostgreSQL Password [airflow123]: " pg_password
pg_password="${pg_password:-airflow123}"
echo ""
echo ""

# Create postgres-credentials secret
kubectl delete secret postgres-credentials -n airflow 2>/dev/null || true
kubectl create secret generic postgres-credentials \
    --namespace=airflow \
    --from-literal=host="$pg_host" \
    --from-literal=database="$pg_database" \
    --from-literal=username="$pg_username" \
    --from-literal=password="$pg_password"

echo "✅ Created postgres-credentials secret"
echo ""

# Deploy target PostgreSQL
echo "📦 Deploying target PostgreSQL database..."
kubectl apply -f k3d/manifests/postgres-target.yaml

echo ""
echo "✅ All secrets created successfully!"
echo ""
echo "Next step: Deploy Airflow with ./k3d/scripts/deploy-airflow.sh"

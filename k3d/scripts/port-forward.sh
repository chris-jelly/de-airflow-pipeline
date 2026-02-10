#!/usr/bin/env bash
set -euo pipefail

# Port forward Airflow webserver UI
# Note: With NodePort configuration, this is optional - UI is already accessible on localhost:30080

echo "🌐 Port forwarding Airflow webserver..."
echo ""
echo "Note: With NodePort, the UI is already accessible at http://localhost:30080"
echo "This script provides an alternative using kubectl port-forward on port 8080"
echo ""

# Wait for webserver pod to be ready
echo "Waiting for Airflow webserver to be ready..."
kubectl wait --for=condition=ready pod \
    -l component=webserver \
    -n airflow \
    --timeout=300s

# Port forward
echo "Forwarding port 8080 to Airflow webserver..."
echo ""
echo "Access Airflow UI at: http://localhost:8080"
echo "Username: admin"
echo "Password: admin"
echo ""
echo "Press Ctrl+C to stop port forwarding"
echo ""

kubectl port-forward -n airflow svc/airflow-webserver 8080:8080

#!/bin/bash
set -euo pipefail

# US-007: Verify Airflow UI and DAG discovery
# This script validates that Airflow components are running and the UI is accessible.

LOG_FILE="airflow-verify-$(date +%s).log"

log() {
    local msg="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $msg" | tee -a "$LOG_FILE"
}

error() {
    local msg="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $msg" | tee -a "$LOG_FILE"
    exit 1
}

# 1. Check prerequisites
log "Checking prerequisites..."
if ! command -v curl &> /dev/null; then
    error "curl is required but not installed."
fi
if ! command -v jq &> /dev/null; then
    error "jq is required but not installed."
fi

# 2. Check Pod Readiness
log "Checking Airflow Pod status..."
NAMESPACE="airflow"

check_pod() {
    local component="$1"
    local selector="$2"
    
    log "Checking $component pod..."
    # Get pod name
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l "$selector" -o jsonpath="{.items[0].metadata.name}" 2>/dev/null || echo "")
    
    if [ -z "$pod_name" ]; then
        error "$component pod not found (selector: $selector)"
    fi
    
    # Check if ready
    local ready=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath="{.status.containerStatuses[0].ready}")
    
    if [ "$ready" != "true" ]; then
        error "$component pod is not ready."
    fi
    log "$component pod is Ready: $pod_name"
}

check_pod "Scheduler" "component=scheduler"
check_pod "Webserver" "component=webserver"
# Triggerer is optional depending on chart, but we saw it running earlier
check_pod "Triggerer" "component=triggerer"

# Note: No worker pods in KubernetesExecutor until tasks run.

# 3. Check UI Accessibility
log "Checking Airflow UI accessibility..."
UI_URL="http://localhost:30080"
HEALTH_ENDPOINT="$UI_URL/health"

if curl -s --head --fail "$HEALTH_ENDPOINT" > /dev/null; then
    log "Airflow UI health check passed: $HEALTH_ENDPOINT"
else
    error "Airflow UI health check failed. Ensure port 30080 is accessible."
fi

# 4. Verify API and DAG discovery
log "Verifying DAG discovery via API..."
# Default credentials created by the chart
USER="admin"
PASS="admin"

# Get DAGs list
# Use -u user:pass for Basic Auth
DAGS_JSON=$(curl -s -u "$USER:$PASS" "$UI_URL/api/v1/dags")

# Check if curl failed (e.g. 401 Unauthorized or 404)
if [[ -z "$DAGS_JSON" ]]; then
    error "Failed to retrieve DAGs from API."
fi

# Check for unauthorized or error response
if echo "$DAGS_JSON" | grep -q "\"title\": \"Unauthorized\""; then
    error "Authentication failed for user '$USER'. Default credentials might be different."
fi

# Count DAGs
DAG_COUNT=$(echo "$DAGS_JSON" | jq '.total_entries')

log "Found $DAG_COUNT DAGs loaded."

if [ "$DAG_COUNT" -lt 1 ]; then
    error "No DAGs found. Expected at least 'salesforce' DAG."
fi

# Check for specific DAGs (e.g., salesforce_extraction)
# Assuming the file names in dags/salesforce result in a DAG id.
# Usually defaults to file name or defined in DAG object.
# Let's check for 'salesforce' in the output.
if echo "$DAGS_JSON" | jq -e '.dags[] | select(.dag_id | contains("salesforce"))' > /dev/null; then
    log "Salesforce DAG found."
else
    log "WARNING: Salesforce DAG not found in the list. Current DAGs:"
    echo "$DAGS_JSON" | jq -r '.dags[].dag_id' | tee -a "$LOG_FILE"
    # Failing strictly as per AC "returns loaded DAGs from dags/ directory"
    error "Expected Salesforce DAG not loaded."
fi

log "US-007 Verification Complete: Airflow UI is accessible and DAGs are discovered."
log "You can access the UI at: $UI_URL"
log "Credentials: $USER / $PASS"

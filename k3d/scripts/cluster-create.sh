#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Determine script directory and repo root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CONFIG_FILE="$REPO_ROOT/k3d/cluster-config.yaml"
CLUSTER_NAME="airflow-dev"

# Validate tools
if ! command -v k3d &> /dev/null; then
    error "k3d not found. Please install k3d."
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    error "kubectl not found. Please install kubectl."
    exit 1
fi

# Check for config file
if [ ! -f "$CONFIG_FILE" ]; then
    error "Configuration file not found at $CONFIG_FILE"
    exit 1
fi

# Check if cluster exists
if k3d cluster list | grep -q "^$CLUSTER_NAME"; then
    log "Cluster '$CLUSTER_NAME' already exists."
else
    log "Creating cluster '$CLUSTER_NAME' using config $CONFIG_FILE..."
    # We need to run this from the repo root or use absolute paths in config?
    # k3d config resolves paths relative to the config file usually, or CWD.
    # The config has `volume: ${PWD}/dags:/dags`. If we run from elsewhere, PWD might be wrong.
    # So we should cd to REPO_ROOT.
    
    cd "$REPO_ROOT"
    if k3d cluster create --config "$CONFIG_FILE"; then
        log "Cluster created successfully."
    else
        error "Failed to create cluster."
        exit 1
    fi
    cd - > /dev/null
fi

# Post-creation validation

# 1. Check Cluster Info / Context
log "Verifying cluster context..."
# Update kubeconfig to be sure
k3d kubeconfig merge "$CLUSTER_NAME" --kubeconfig-switch-context > /dev/null 2>&1 || true

CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || true)
if [[ "$CURRENT_CONTEXT" == "k3d-$CLUSTER_NAME" ]]; then
    log "Current context is set to 'k3d-$CLUSTER_NAME'."
else
    warn "Current context is '$CURRENT_CONTEXT', expected 'k3d-$CLUSTER_NAME'."
    log "Switching context..."
    kubectl config use-context "k3d-$CLUSTER_NAME" || true
fi

# 2. Check Nodes are Ready
log "Waiting for nodes to be Ready..."
# Wait up to 60 seconds for nodes to be ready
RETRIES=12
READY=0
for i in $(seq 1 $RETRIES); do
    # Check if we can talk to the cluster first
    if ! kubectl get nodes &> /dev/null; then
        warn "Unable to contact cluster. Retrying..."
        sleep 5
        continue
    fi

    NOT_READY_COUNT=$(kubectl get nodes --no-headers | grep -v "Ready" | wc -l || true)
    if [ "$NOT_READY_COUNT" -eq "0" ]; then
        READY=1
        break
    fi
    log "Waiting for nodes... ($i/$RETRIES)"
    sleep 5
done

if [ "$READY" -eq "1" ]; then
    log "All nodes are Ready."
    kubectl get nodes
else
    error "Nodes did not become Ready in time."
    kubectl get nodes
    exit 1
fi

# 3. Check Registry Access
# Get registry port from config if possible, or assume 5111 based on known config
REGISTRY_PORT=$(grep "hostPort" "$CONFIG_FILE" | head -n1 | awk -F'"' '{print $2}')
if [ -z "$REGISTRY_PORT" ]; then
    # Try finding without quotes or fallback
    REGISTRY_PORT=$(grep "hostPort" "$CONFIG_FILE" | head -n1 | awk '{print $2}')
fi

if [ -z "$REGISTRY_PORT" ]; then
    warn "Could not determine registry port from config. Assuming 5111."
    REGISTRY_PORT="5111"
fi

log "Verifying registry access on port $REGISTRY_PORT..."
REGISTRY_READY=0
for i in {1..5}; do
    if curl -s "http://localhost:$REGISTRY_PORT/v2/" > /dev/null; then
        log "Registry is accessible at localhost:$REGISTRY_PORT"
        REGISTRY_READY=1
        break
    else
        warn "Waiting for registry at localhost:$REGISTRY_PORT... ($i/5)"
        sleep 3
    fi
done

if [ "$REGISTRY_READY" -eq "0" ]; then
    error "Registry validation failed. Could not connect to http://localhost:$REGISTRY_PORT/v2/"
    exit 1
fi

log "Cluster $CLUSTER_NAME is ready and verified!"

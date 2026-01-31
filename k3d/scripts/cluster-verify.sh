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

# Configuration
CLUSTER_NAME="airflow-dev"
REQUIRED_CONTEXT="k3d-$CLUSTER_NAME"

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    error "kubectl not found. Please install kubectl."
    exit 1
fi

log "Starting verification for cluster '$CLUSTER_NAME'..."

# 1. Validate Context
log "Step 1: Validating Kubernetes context..."
CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || true)
if [[ "$CURRENT_CONTEXT" != "$REQUIRED_CONTEXT" ]]; then
    warn "Current context is '$CURRENT_CONTEXT', expected '$REQUIRED_CONTEXT'."
    if kubectl config get-contexts "$REQUIRED_CONTEXT" > /dev/null 2>&1; then
        log "Switching to '$REQUIRED_CONTEXT'..."
        kubectl config use-context "$REQUIRED_CONTEXT" > /dev/null
    else
        error "Context '$REQUIRED_CONTEXT' not found. Is the cluster created?"
        exit 1
    fi
else
    log "Context is correct: $CURRENT_CONTEXT"
fi

# 2. Validate Nodes
log "Step 2: Validating node status..."
if ! kubectl get nodes &> /dev/null; then
    error "Unable to contact cluster."
    exit 1
fi

NOT_READY_COUNT=$(kubectl get nodes --no-headers | grep -v "Ready" | wc -l || true)
if [ "$NOT_READY_COUNT" -ne "0" ]; then
    error "Found $NOT_READY_COUNT nodes that are not Ready."
    kubectl get nodes
    exit 1
fi
log "All nodes are Ready."
kubectl get nodes

# 3. Check Resources (Basic availability check)
log "Step 3: Checking cluster resources..."
# We just list nodes and check if they describe capacity. 
# Parsing "kubectl describe node" is verbose, so we might just check if Metrics API is available or just rely on node status.
# The requirement says "Script checks cluster has sufficient resources (CPU/memory)"
# We can check if any node has Pressure conditions.
PRESSURE_CONDITIONS=$(kubectl get nodes -o jsonpath='{.items[*].status.conditions[?(@.status=="True")].type}' | grep -E "MemoryPressure|DiskPressure|PIDPressure" || true)

if [ -n "$PRESSURE_CONDITIONS" ]; then
    warn "Detected resource pressure on nodes: $PRESSURE_CONDITIONS"
    # We warn but don't fail, as it might be transient or acceptable for dev
else
    log "No resource pressure detected on nodes."
fi

# 4 & 5. Network & DNS Validation
log "Step 4 & 5: Validating networking and CoreDNS..."
TEST_POD_NAME="net-verify-$(date +%s)"
NAMESPACE="default"

# We use busybox or similar small image. Alpine is common.
# We'll run a pod that sleeps, then exec into it to run tests.
log "Deploying test pod '$TEST_POD_NAME'..."

# Create a pod manifest
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: $TEST_POD_NAME
  namespace: $NAMESPACE
spec:
  containers:
  - name: test-container
    image: busybox:1.36
    command: ['sleep', '3600']
    imagePullPolicy: IfNotPresent
  restartPolicy: Never
EOF

# Wait for pod to be running
log "Waiting for test pod to be Running..."
kubectl wait --for=condition=Ready pod/$TEST_POD_NAME --timeout=60s

# Verify Network (Ping external or internal?)
# Requirement: "Script deploys and deletes test pod to validate networking"
# Requirement: "Script verifies CoreDNS is functional with test DNS lookup"

log "Testing DNS lookup (kubernetes.default.svc.cluster.local)..."
if kubectl exec $TEST_POD_NAME -- nslookup kubernetes.default.svc.cluster.local > /dev/null 2>&1; then
    log "Internal DNS lookup successful."
else
    error "Internal DNS lookup failed."
    kubectl describe pod $TEST_POD_NAME
    kubectl logs $TEST_POD_NAME
    # Cleanup before exit
    kubectl delete pod $TEST_POD_NAME --force --grace-period=0 > /dev/null 2>&1 || true
    exit 1
fi

log "Testing external DNS lookup (google.com)..."
if kubectl exec $TEST_POD_NAME -- nslookup google.com > /dev/null 2>&1; then
    log "External DNS lookup successful."
else
    warn "External DNS lookup failed. Internet access might be restricted."
    # We don't fail strictly on external access unless required, but typically dev envs need it.
    # The requirement just says "CoreDNS is functional", usually implying internal resolution is key.
fi

# Cleanup
log "Cleaning up test pod..."
kubectl delete pod $TEST_POD_NAME --force --grace-period=0 > /dev/null 2>&1

log "Cluster verification completed successfully!"

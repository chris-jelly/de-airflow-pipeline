#!/bin/bash
set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Check arguments
if [ "$#" -lt 1 ]; then
    error "Usage: $0 <dag_type> [dag_type...]"
    error "Example: $0 salesforce"
    exit 1
fi

# Directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
REGISTRY_PORT="5111"
REGISTRY_HOST="localhost"

# Check if k3d registry is running
if ! curl -s "http://$REGISTRY_HOST:$REGISTRY_PORT/v2/" > /dev/null; then
    warn "Registry not accessible at $REGISTRY_HOST:$REGISTRY_PORT"
    warn "Ensure the cluster is running: k3d/scripts/cluster-create.sh"
    # We fail because pushing is required
    error "Cannot push to registry. Aborting."
    exit 1
fi

cd "$REPO_ROOT"

for DAG_TYPE in "$@"; do
    DAG_DIR="dags/$DAG_TYPE"
    DOCKERFILE="$DAG_DIR/Dockerfile"

    if [ ! -d "$DAG_DIR" ]; then
        error "DAG directory '$DAG_DIR' not found."
        continue
    fi

    if [ ! -f "$DOCKERFILE" ]; then
        error "Dockerfile not found at '$DOCKERFILE'."
        continue
    fi

    # Image tag: localhost:5111/de-airflow-pipeline-{type}:local
    # Note: PRD mentioned localhost:30080 but that is the Airflow UI.
    # We use the correct registry port 5111.
    IMAGE_TAG="$REGISTRY_HOST:$REGISTRY_PORT/de-airflow-pipeline-${DAG_TYPE}:local"

    log "Building image for '$DAG_TYPE'..."
    log "Context: $REPO_ROOT"
    log "Dockerfile: $DOCKERFILE"
    
    # Build
    # We use --pull to ensure we have the latest base image if possible
    if docker build -t "$IMAGE_TAG" -f "$DOCKERFILE" .; then
        log "Build successful."
    else
        error "Build failed for $DAG_TYPE."
        exit 1
    fi

    log "Pushing image to registry: $IMAGE_TAG..."
    if docker push "$IMAGE_TAG"; then
        log "Push successful."
    else
        error "Push failed. Is the registry running?"
        exit 1
    fi
done

# Validation
log "Verifying images in registry..."
CATALOG=$(curl -s "http://$REGISTRY_HOST:$REGISTRY_PORT/v2/_catalog")
log "Registry catalog: $CATALOG"

for DAG_TYPE in "$@"; do
    # The registry usually returns names without the host prefix
    # e.g. "de-airflow-pipeline-salesforce"
    EXPECTED_NAME="de-airflow-pipeline-${DAG_TYPE}"
    
    # Check if the catalog contains the repo name
    if echo "$CATALOG" | grep -q "$EXPECTED_NAME"; then
        log "Image '$EXPECTED_NAME' found in registry."
    else
        error "Image '$EXPECTED_NAME' NOT found in registry catalog."
        exit 1
    fi
done

log "All images processed successfully."

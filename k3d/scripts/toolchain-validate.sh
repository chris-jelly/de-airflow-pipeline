#!/bin/bash
set -e

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

version_ge() {
    # Returns 0 if $1 >= $2, 1 otherwise
    # Uses sort -V for version comparison
    if [ "$(printf '%s\n%s' "$2" "$1" | sort -V | head -n1)" = "$2" ]; then
        return 0
    else
        return 1
    fi
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        error "$1 is not installed or not in PATH."
        return 1
    fi
    log "$1 is installed."
    return 0
}

FAILED=0

echo "Starting Toolchain Validation..."

# 1. Check commands existence
check_command "k3d" || FAILED=1
check_command "kubectl" || FAILED=1
check_command "helm" || FAILED=1

if [ $FAILED -ne 0 ]; then
    error "Missing required tools. Please install k3d, kubectl, and helm."
    exit 1
fi

# 2. Check k3d version (v5.0+)
K3D_MIN="5.0.0"
K3D_VER=$(k3d --version | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | head -n1 | sed 's/v//')
if [ -z "$K3D_VER" ]; then
    warn "Could not determine k3d version."
else
    if version_ge "$K3D_VER" "$K3D_MIN"; then
        log "k3d version $K3D_VER satisfies minimum $K3D_MIN"
    else
        error "k3d version $K3D_VER is older than minimum $K3D_MIN"
        FAILED=1
    fi
fi

# 3. Check kubectl version (v1.25+)
KUBECTL_MIN="1.25.0"
# Try json output first, fallback to short
KUBECTL_VER=$(kubectl version --client --output=json 2>/dev/null | grep -o '"gitVersion": "[^"]*"' | cut -d'"' -f4 | sed 's/v//')
if [ -z "$KUBECTL_VER" ]; then
    KUBECTL_VER=$(kubectl version --client --short 2>/dev/null | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | sed 's/v//')
fi

if [ -z "$KUBECTL_VER" ]; then
    warn "Could not determine kubectl version."
else
    if version_ge "$KUBECTL_VER" "$KUBECTL_MIN"; then
        log "kubectl version $KUBECTL_VER satisfies minimum $KUBECTL_MIN"
    else
        error "kubectl version $KUBECTL_VER is older than minimum $KUBECTL_MIN"
        FAILED=1
    fi
fi

# 4. Check helm version (v3.0+)
HELM_MIN="3.0.0"
HELM_VER=$(helm version --short 2>/dev/null | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | sed 's/v//')

if [ -z "$HELM_VER" ]; then
    warn "Could not determine helm version."
else
    if version_ge "$HELM_VER" "$HELM_MIN"; then
        log "helm version $HELM_VER satisfies minimum $HELM_MIN"
    else
        error "helm version $HELM_VER is older than minimum $HELM_MIN"
        FAILED=1
    fi
fi

# 5. Check configuration files
# Get repo root relative to this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CONFIG_FILE="$REPO_ROOT/k3d/cluster-config.yaml"

if [ ! -f "$CONFIG_FILE" ]; then
    error "Cluster config not found at $CONFIG_FILE"
    FAILED=1
else
    log "Cluster config found at $CONFIG_FILE"
fi

if [ $FAILED -ne 0 ]; then
    error "Validation failed. Please fix the issues above."
    exit 1
else
    log "Toolchain validation passed!"
    exit 0
fi

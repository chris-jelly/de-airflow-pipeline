# Dev Container Setup

This directory contains the dev container configuration for the de-airflow-pipeline project.

## What's Included

- **Ubuntu 24.04** base devcontainer image
- **mise** - Manages all development tools (see `mise.toml` for the full list)
- **Docker-in-Docker** - Required for k3d Kubernetes clusters
- **SSH keys** - Mounted read-only from host for seamless git operations

### Tools (via mise)

| Tool | Purpose |
|------|---------|
| `uv` | Python package manager |
| `claude` | Claude Code CLI |
| `helm` | Kubernetes package manager |
| `kubectl` | Kubernetes CLI |
| `k3d` | Lightweight Kubernetes (k3s in Docker) |
| `k9s` | Kubernetes TUI |
| `jq` | JSON processor |
| `pre-commit` | Git hook framework |

## How to Use

### Prerequisites (on your local machine)

- [Docker Desktop](https://www.docker.com/products/docker-desktop) or compatible container runtime
- A dev container client ([DevPod](https://devpod.sh/), VS Code + Dev Containers extension, or CLI)

### Opening the Container

Using DevPod:

```bash
devpod up .
```

Using VS Code:

1. Open this project in VS Code
2. Command Palette > "Dev Containers: Reopen in Container"

### First Time Setup

The container automatically runs `scripts/setup` on creation, which:

1. Trusts the `mise.toml` configuration
2. Installs all tools defined in `mise.toml`

When you `cd` into the project (triggering mise's `enter` hook), `scripts/setup_project` also:

1. Installs `commitizen` via `uv tool`
2. Configures git settings
3. Installs pre-commit hooks

### Daily Development

```bash
# Work on a specific DAG
cd dags/salesforce
uv sync

# Run tests
uv run pytest

# Code quality
uv run ruff format .
uv run ruff check .

# Kubernetes (requires docker-in-docker)
k3d cluster create
kubectl apply -f k3d/manifests/
```

### SSH Keys

Your SSH keys are mounted read-only from `~/.ssh`, so git operations (push, pull, clone) work seamlessly with GitHub without additional authentication setup.

### Rebuilding the Container

If you modify `.devcontainer/devcontainer.json` or `.devcontainer/Dockerfile`:

```bash
# DevPod
devpod up . --recreate

# VS Code
# Command Palette > "Dev Containers: Rebuild Container"
```

## Architecture

```
.devcontainer/
  devcontainer.json   # Container config, features, mounts
  Dockerfile          # Ubuntu 24.04 + mise installation
scripts/
  setup               # postCreateCommand: mise trust + install
  setup_project       # mise enter hook: commitizen, pre-commit, git config
mise.toml             # Tool definitions and hooks
```

## Troubleshooting

**Container won't build:**
- Ensure Docker is running
- Check Docker has enough memory allocated (recommend 4GB+)

**Tools not available:**
- Run `mise install` manually
- Check `mise doctor` for diagnostics

**k3d/Docker issues:**
- Docker-in-Docker must be enabled (it is by default in this config)
- If k3d fails, try `docker info` to verify the Docker daemon is running

**Pre-commit hooks not installed:**
- Run `pre-commit install && pre-commit install --hook-type commit-msg`

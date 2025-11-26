# ADR-002: Pod-Level Secret Mounting

**Status**: Accepted

**Date**: 2025-11-26

**Deciders**: Engineering Team

## Context

Airflow tasks need access to credentials for external systems (Salesforce, databases, APIs). We need to decide how to provide these secrets securely:

1. Global environment variables (available to all pods)
2. Per-DAG secret mounting via `executor_config`
3. Airflow Connections (stored in Airflow metadata DB)
4. Direct credential files in containers

The main security concerns are:
- Principle of least privilege
- Preventing credential leakage
- Audit trail and compliance
- Ease of rotation and management

## Decision

We will use **per-DAG secret mounting via `executor_config`**, where each DAG explicitly declares which secrets it needs and mounts them only in its executor pods.

**Implementation:**
- Secrets are Kubernetes `Secret` resources (managed by External Secrets Operator)
- DAGs reference secrets in their `executor_config.pod_override.spec.containers[].env`
- Core Airflow components (scheduler, webserver, triggerer) do NOT receive data credentials
- Each DAG only gets the specific secrets it needs

## Consequences

### Positive
- **Least privilege**: Scheduler/webserver don't get data access credentials
- **Better isolation**: Each DAG only gets its own secrets
- **Clear audit trail**: Explicitly documented which DAG needs which credentials
- **Reduced attack surface**: Compromised scheduler/webserver can't access data
- **Compliance friendly**: Easy to demonstrate and prove least privilege
- **No credential leakage**: Secrets never appear in Airflow UI, logs, or metadata DB

### Negative
- **More verbose**: Each DAG needs to declare its secrets explicitly
- **Duplication**: Similar secret declarations across DAGs (can be templated)
- **Initial setup**: Requires understanding of Kubernetes pod specs

### Neutral
- **Works with standard K8s secrets**: Compatible with any secret management system
- **DAG-level granularity**: Can't easily share secrets across some tasks but not others in same DAG

## Alternatives Considered

### Alternative 1: Global Environment Variables

**Description**: Mount secrets as environment variables in Helm values, available to all Airflow pods

```yaml
env:
  - name: SALESFORCE_PASSWORD
    valueFrom:
      secretKeyRef: ...
```

**Pros**:
- Simple configuration
- Works immediately for all pods
- No per-DAG configuration needed

**Cons**:
- Violates principle of least privilege
- Scheduler/webserver get credentials they don't need
- All DAGs get all secrets (Salesforce DAG gets API credentials, etc.)
- Difficult to audit who accesses what
- Larger attack surface

**Why not chosen**: Not secure for production use. If the webserver or scheduler is compromised, attacker gets all data access credentials.

### Alternative 2: Airflow Connections

**Description**: Store credentials in Airflow metadata database, retrieve via Airflow Hooks

**Pros**:
- Native Airflow approach
- UI for managing connections
- Works across different executors

**Cons**:
- Credentials stored in Airflow metadata DB (additional place to secure)
- Visible in Airflow UI (even if masked, still a risk)
- All Airflow components need DB access with connection data
- Harder to integrate with external secret management (ESO, Vault)
- Rotation requires Airflow restart or API calls

**Why not chosen**: Doesn't integrate well with our External Secrets Operator approach, and storing credentials in another database isn't ideal when we already have Azure Key Vault.

### Alternative 3: Airflow Secrets Backend

**Description**: Configure Airflow to pull secrets from external backend (Vault, AWS Secrets Manager)

```python
[secrets]
backend = airflow.providers.hashicorp.secrets.vault.VaultBackend
backend_kwargs = {"url": "https://vault:8200", ...}
```

**Pros**:
- Direct integration with secret management systems
- Automatic rotation support
- Centralized secret management
- No secrets in Kubernetes

**Cons**:
- All Airflow components need access to secret backend
- Doesn't solve the least privilege issue (scheduler still gets secrets)
- More complex configuration
- Requires network calls during task execution

**Why not chosen**: Doesn't provide better security than our ESO + pod-level mounting approach, and adds complexity. We already have ESO syncing from Azure Key Vault, so adding another integration point isn't beneficial.

### Alternative 4: CSI Secret Driver

**Description**: Mount secrets from external provider directly into pods using CSI drivers

```yaml
volumes:
  - name: secrets-store
    csi:
      driver: secrets-store.csi.k8s.io
      ...
```

**Pros**:
- Secrets never stored in Kubernetes etcd
- Automatic rotation
- Strong audit trail in external system

**Cons**:
- Most complex to set up
- Requires CSI driver installation and configuration
- Platform-specific configuration
- Harder to debug

**Why not chosen**: Adds significant complexity. Our ESO approach already syncs from Azure Key Vault with rotation support. If we need CSI-level security in the future, we can migrate to it, but the current approach meets our security requirements.

## Implementation Notes

Example DAG configuration:

```python
executor_config = {
    "pod_override": {
        "spec": {
            "containers": [{
                "name": "base",
                "image": "ghcr.io/owner/repo:salesforce-latest",
                "env": [
                    {
                        "name": "SALESFORCE_USERNAME",
                        "valueFrom": {
                            "secretKeyRef": {
                                "name": "salesforce-credentials",
                                "key": "username"
                            }
                        }
                    },
                    # ... other secrets ...
                ]
            }]
        }
    }
}
```

See `KUBERNETES.md` for complete examples.

## Future Considerations

If security requirements increase, we could:
- Migrate to CSI secret driver for memory-only secret mounting
- Use workload identity for cloud service credentials (PostgreSQL, etc.)
- Implement secret rotation monitoring and alerting
- Add runtime secret scanning in pods
